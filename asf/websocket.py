import asyncio
from asyncio.futures import CancelledError
import json
import logging
from urllib import parse

import aredis
from aredis.pubsub import PubSub

import requests

import websockets

from .config import config, load_config


def handler_factory(pubsub, *, loop=None):
    """Create a async handler for the websocket server.

    This allows for setting the pubsub class (usefull for testing).
    """
    log = logging.getLogger(__name__)

    async def handler(websocket, path):
        """Async websocket handler."""
        log.debug('Creating new websocket.')
        with WebSocketHandler(websocket, path, pubsub, loop=loop) as self:
            await self.handle()

    return handler


class WebSocketHandler(object):
    """WebSocket handler.

    One is created for every websocket connection.
    """

    functions = ('ls', 'subscribe', 'unsubscribe')

    def __init__(self, websocket, path, pubsub, *, loop=None):
        self.log = logging.getLogger(__name__)
        self.log.debug('init')
        self._loop = loop
        self.log.debug('websocket path: %s', path)
        self.websocket = websocket
        self.log.debug('Websocket headers: %s',
                       self.websocket.request_headers)
        self.origin = self.websocket.request_headers['origin'] or ''
        self.log.debug('Origin: %r', self.origin)
        self.subscriptions = set()
        # A lock wich will lock till for ever. Used to have the producer
        # in waiting state if no message was recieved from redis server.
        self._lock = self._loop.create_future()
        self.tasks = []
        # Redis connect, make sure we have a pool.
        self.pubsub = pubsub
        path = path.rstrip('/')
        if path.endswith('/ws'):
            path = path[:-3]
        if not is_valid_app_path(path):
            # If path is invalid, close connection.
            self.log.debug('Invalid path closing connection.')
            asyncio.ensure_future(websocket.close(4004, 'Invalid path'),
                                  loop=self._loop)
            return
        # Don't try to subscribe to the main '/api' url.
        if path != '/api':
            asyncio.ensure_future(
                self.subscribe({'path': path}),
                loop=self._loop
            )
        self.log.debug('init done')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean-up.
        try:
            # Close lock.
            self._lock.set_result(None)
            # Cancel all tasks.
            [t.cancel() for t in self.tasks]
            # Unsubscribe to all subscriptions.
            asyncio.wait_for(
                asyncio.ensure_future(
                    self.pubsub.unsubscribe(), loop=self._loop
                ),
                None, loop=self._loop
            )
        except Exception as e:  # pragma: no cover
            self.log.exception('Clean-up failed: %s', e)
        if exc_type:
            if issubclass(exc_type,
                          (CancelledError, websockets.ConnectionClosed)):
                # We can ignore CancelledError and ConnectionClosed errors.
                self.log.debug('Handling exited with: %s', exc_val,
                               exc_info=(exc_type, exc_val, exc_tb))
                return True
            else:  # pragma: no cover
                self.log.exception('Websocket handling failed: %s', exc_type,
                                   exc_info=(exc_type, exc_val, exc_tb))

    async def handle(self):
        self.log.debug('handlingen')
        while True:
            self.tasks.append(asyncio.ensure_future(self.consumer(),
                                                    loop=self._loop))
            self.tasks.append(asyncio.ensure_future(self.producer(),
                                                    loop=self._loop))
            # Wait for any of the tasks to be done.
            done, pending = await asyncio.wait(
                self.tasks,
                loop=self._loop,
                return_when=asyncio.FIRST_COMPLETED)
            self.log.debug('Done tasks: %s.', done)
            self.log.debug('Pending tasks: %s.', pending)
            for task in done:
                try:
                    func, message = task.result()
                except CancelledError:
                    continue
                self.log.debug('running function %s on message %s',
                               func, message)
                await func(message)
            for task in pending:
                task.cancel()
            self.tasks = []

    async def consumer(self):
        message = await self.websocket.recv()
        self.log.debug('Got message from client: %s', message)
        return self._consumer, message

    async def _consumer(self, message):
        self.log.debug('Running consumer on message %s', message)
        try:
            message = json.loads(message)
        except Exception:
            await self.websocket.send(json.dumps(
                {'error': 'Message is not json loadable.'}
            ))
            return
        if not hasattr(message, 'get'):
            await self.websocket.send(json.dumps(
                {'error': 'Message must be a dict.'}
            ))
            return
        function = message.get('function')
        if function not in self.functions:
            await self.websocket.send(json.dumps(
                {'error': 'Message function must be one of: {}.'.
                 format(', '.join(self.functions))}
            ))
            return
        self.log.debug('Running function %s', function)
        if function in ('subscribe', 'unsubscribe'):
            if 'path' not in message:
                await self.websocket.send(json.dumps(
                    {'error': 'Message missing path.'}
                ))
                return
        await getattr(self, function)(message)

    async def ls(self, message):
        message = {'function': 'ls',
                   'paths': sorted(self.subscriptions)}
        await self.websocket.send(json.dumps(message))

    async def subscribe(self, message):
        # redis subscribe
        path = message['path']
        path = parse_path(path, self.origin)
        if path not in self.subscriptions:
            if not is_valid_app_path(path):
                # If path is not valid, send en error message and
                # do not subscribe to it.
                await self.websocket.send(json.dumps(
                    {'error': 'Invalid path: {}'.format(path)}
                ))
                return
            self.log.debug('Subscribing to path: %s', path)
            await self.pubsub.subscribe(path)
            self.subscriptions.add(path)
            # self._subscriber.set_result(None)
        else:
            await self.websocket.send(json.dumps(
                {'function': 'subscribe',
                 'error': 'Already subscribed to path: {}'.format(path)}
            ))

    async def unsubscribe(self, message):
        path = message['path']
        path = parse_path(path, self.origin)
        if path in self.subscriptions:
            await self.pubsub.unsubscribe(path)
            self.subscriptions.remove(path)
        else:
            await self.websocket.send(json.dumps(
                {'function': 'unsubscribe',
                 'error': 'Not subscribed to path: {}'.format(path)}
            ))

    async def producer(self):
        message = await self.pubsub.listen()
        if not message:
            # Not subscribed yet, just lock till a task is done.
            await self._lock
        self.log.debug('Message from redis server: %r', message)
        return self._producer, message

    async def _producer(self, message):
        r_message = message
        self.log.debug('Running producer on message %s', message)
        function = r_message['type']
        w_message = {'function': function,
                     'path': r_message['channel'].decode('utf-8')}
        if function == 'message':
            data = json.loads(r_message['data'].decode('utf-8'))
            w_message.update({'data': data['data'],
                             'type': data['type']})
        self.log.debug('Message send over websocket: %s',
                       w_message)
        await self.websocket.send(json.dumps(w_message))


def parse_path(path, origin):
    """Only return the path part of an url.

    Path may be only the path part of the url or an url starting with
    origin.
    All paths are returned as an absolute path. Any ending slashes are
    removed.
    """
    log = logging.getLogger(__name__)
    origin = parse.urlparse(origin)
    log.debug('url parse origin: %r', origin)
    # Remove any slashes at the start and end of the path.
    path = path.strip('/')
    # Define the scheme.
    scheme = '{}://'.format(origin.scheme)
    # Add the scheme and netloc to the path if it did not contain it already.
    if not path.startswith(scheme):
        if not path.startswith(origin.netloc):
            path = '{}/{}'.format(origin.netloc, path)
        path = '{}{}'.format(scheme, path)
    # Now get the path part of the url, and again strip any slashes.
    path = parse.urlparse(path).path.strip('/')
    # Readd a slash at the beginning.
    path = '/{}'.format(path)
    return path


def is_valid_app_path(path):
    """Check that the path is a existing app path.

    App paths shoud always start with "api" and should not return an
    http error status.
    """
    # Path must start with 'api'.
    log = logging.getLogger(__name__)
    log.debug('Testing path %r', path)
    if path.lstrip('/').startswith('api'):
        url = 'http://{host}:{port}/{path}'.format(host=config['host'].get(),
                                                   port=config['port'].get(),
                                                   path=path.lstrip('/'))
        # Use a local connection to try and connect to this url.
        response = requests.get(url)
        # If connection is succesful (status code lower than 400 or higher
        # than 599 return True.
        return not 400 <= response.status_code < 600
    else:
        log.debug('Path must start with "api" to be valid.')
    return False


def setup(loop):
    load_config()
    host = config['websocket']['host'].get()
    port = config['websocket']['port'].get()
    # Create redis client
    redis_client = aredis.StrictRedis.from_url(config['redis_uri'].get())
    # Test that we can connect to redis.
    redis_test = asyncio.ensure_future(redis_client.ping(), loop=loop)
    handler = handler_factory(redis_client.pubsub(), loop=loop)
    server = websockets.serve(handler, host=host, port=port, loop=loop)

    loop.run_until_complete(server)
    # Raises an ConnectionError if we could not connect to the redis server.
    redis_test.result()
    print('Started Websocket server at {}:{}'.format(host, port))


def run():  # pragma: no cover
    log = logging.getLogger(__name__)
    log.debug('Getting default event loop')
    loop = asyncio.get_event_loop()
    setup(loop)
    log.debug('Running websocket server')
    loop.run_forever()
    loop.stop()


if __name__ == '__main__':  # pragma: no cover
    run()
