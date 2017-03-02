import asyncio
from concurrent.futures import CancelledError
import json
import logging
from urllib import parse

import redis
from redis.client import PubSub

import requests

import websockets

from .config import config, load_config


class AsyncPubSub(PubSub):
    """Adds an async listener to the default redis PubSub."""

    def __init__(self, *, loop=None, **kwargs):
        self._loop = loop
        super().__init__(**kwargs)

    async def listen(self):
        """Listen for a message in async."""
        while True:
            message = super().get_message()
            if message:
                return message
            # Async sleep before next check.
            await asyncio.sleep(0.1, loop=self._loop)


def handler_factory(pubsub_class, *, loop=None, **kwargs):
    """Create a async handler for the websocket server.

    This allows for setting the pubsub class (usefull for testing).
    """
    log = logging.getLogger(__name__)

    async def handler(websocket, path):
        """Async websocket handler."""
        log.debug('Creating new websocket.')
        pubsub = pubsub_class(loop=loop, **kwargs)
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
        # Redis connect, make sure we have a pool.
        self.pubsub = pubsub
        path = path.rstrip('/')
        if path.endswith('/ws'):
            path = path[:-3]
        if not is_valid_app_path(path):
            # If path is invalid, close connection.
            self.log.debug('Invalid path closing connection.')
            asyncio.ensure_future(websocket.close(4000, 'Invalid path.'),
                                  loop=self._loop)
        if path:
            asyncio.ensure_future(
                self.subscribe({'path': path}),
                loop=self._loop
            )
        self.log.debug('init done')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.pubsub.unsubscribe()
        except Exception as e:  # pragma: no cover
            self.log.exception('Clean-up failed: %s', e)
        if exc_val:  # pragma: no cover
            self.log.exception('Websocket handling failed: %s', exc_val,
                               exc_info=(exc_type, exc_val, exc_tb))

    async def handle(self):
        self.log.debug('handlingen')
        try:
            while True:
                tasks = []
                tasks.append(asyncio.ensure_future(self.consumer(),
                                                   loop=self._loop))
                tasks.append(asyncio.ensure_future(self.producer(),
                                                   loop=self._loop))
                # Wait for any of the tasks to be done.
                done, pending = await asyncio.wait(
                    tasks,
                    loop=self._loop,
                    return_when=asyncio.FIRST_COMPLETED)
                for task in tasks:
                    # If they are done or cancelled, cancel() returns False
                    if not task.cancel():
                        task.result()
        except (CancelledError, websockets.ConnectionClosed) as e:
            self.log.debug('Handling exited with: %s', e, exc_info=True)
        finally:
            for task in tasks:
                task.cancel()

    async def consumer(self):
        message = await self.websocket.recv()
        self.log.debug('Got message from client: %s', message)
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
                {'error': 'function must be one of: {}.'.
                 format(', '.join(self.functions))}
            ))
            return
        self.log.debug('Running function %s', function)
        await getattr(self, function)(message)

    async def ls(self, message):
        await self.websocket.send(json.dumps(sorted(self.subscriptions)))

    async def subscribe(self, message):
        # redis subscribe
        path = parse_path(message['path'], self.origin)
        if path not in self.subscriptions:
            if not is_valid_app_path(path):
                # If path is not valid, send en error message and
                # do not subscribe to it.
                await self.websocket.send(json.dumps(
                    {'error': 'Invalid path: {}'.format(path)}
                ))
                return
            self.log.debug('Subscribing to path: %s', path)
            self.pubsub.subscribe(path)
            self.subscriptions.add(path)
        else:
            await self.websocket.send(json.dumps(
                {'error': 'Already subscribed to path: {}'.format(path)}
            ))

    async def unsubscribe(self, message):
        path = parse_path(message['path'], self.origin)
        if path in self.subscriptions:
            self.pubsub.unsubscribe(path)
            self.subscriptions.remove(path)
        else:
            await self.websocket.send(json.dumps(
                {'error': 'Not subscribed to path: {}'.format(path)}
            ))

    async def producer(self):
        r_message = await self.pubsub.listen()
        self.log.debug('Message from redis server: %s', r_message)
        function = r_message['type']
        w_message = {'function': function,
                     'path': r_message['channel'].decode('utf-8')}
        if function == 'message':
            data = json.loads(r_message['data'].decode('utf-8'))
            w_message.update({'data': data['data'],
                             'type': data['type']})
        self.log.debug('Message send over webscoket: %s',
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


def run():  # pragma: no cover
    load_config()
    log = logging.getLogger(__name__)
    host = config['websocket']['host'].get()
    port = config['websocket']['port'].get()
    # Create redis pool
    redis_pool = redis.ConnectionPool.from_url(
        config['redis_uri'].get()
    )
    # Test that we can connect to redis.
    redis.StrictRedis(connection_pool=redis_pool).ping()
    loop = asyncio.get_event_loop()
    # Set redis pool as the PubSub class redis pool.
    handler = handler_factory(AsyncPubSub, loop=loop,
                              connection_pool=redis_pool)
    server = websockets.serve(handler, host=host, port=port)

    loop.run_until_complete(server)
    print('Started Websocket server at {}:{}'.format(host, port))
    log.debug('started websocket server')
    loop.run_forever()
    loop.stop()


if __name__ == '__main__':  # pragma: no cover
    run()
