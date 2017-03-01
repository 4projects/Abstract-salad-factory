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

    async def listen(self):
        """Listen for a message in async."""
        while True:
            message = super().get_message()
            if message:
                return message
            # Async sleep before next check.
            await asyncio.sleep(0.1)


def handler_factory(pubsub_class, *args, **kwargs):
    """Create a async handler for the websocket server.

    This allows for setting the pubsub class (usefull for testing).
    """
    log = logging.getLogger(__name__)

    async def handler(websocket, path):
        """Async websocket handler."""
        log.debug('Creating new websocket.')
        pubsub = pubsub_class(*args, **kwargs)
        with WebSocketHandler(websocket, path, pubsub) as self:
            await self.handle()

    return handler


class WebSocketHandler(object):
    """WebSocket handler.

    One is created for every websocket connection.
    """

    functions = ('ls', 'subscribe', 'unsubscribe')

    def __init__(self, websocket, path, pubsub):
        self.log = logging.getLogger(__name__)
        self.log.debug('init')
        self.log.debug('websocket path: %s', path)
        self.websocket = websocket
        self.subscriptions = set()
        # Redis connect, make sure we have a pool.
        self.pubsub = pubsub
        path = path.rstrip('/')
        if path.endswith('/ws'):
            path = path[:-3]
        if not is_valid_app_path(path):
            # If path is invalid, close connection.
            websocket.close(4000, 'Invalid path.')
        if path:
            asyncio.ensure_future(
                self.subscribe({'path': path})
            )
        self.log.debug('init done')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.pubsub.unsubscribe()
        except Exception as e:
            self.log.Exception('Clean-up failed: %s', e)
        if exc_val:
            self.log.Exception('Websocket handling failed: %s', exc_val,
                               exc_info=(exc_type, exc_val, exc_tb))

    async def handle(self):
        self.log.debug('handlingen')
        while True:
            listener_task = asyncio.ensure_future(self.websocket.recv())
            producer_task = asyncio.ensure_future(self.producer())
            # Wait for any of the tasks to be done.
            await asyncio.wait(
                [
                    listener_task,
                    producer_task
                ],
                return_when=asyncio.FIRST_COMPLETED)
            # If they are done or cancelled, cancel() returns False
            if not listener_task.cancel():
                try:
                    await self.consumer(listener_task.result())
                except CancelledError:
                    # Do nothing if task has been cancelled.
                    pass

            if not producer_task.cancel():
                try:
                    producer_task.result()
                except CancelledError:
                    pass

    async def consumer(self, message):
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
        path = parse_path(message['path'])
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
        path = parse_path(message['path'])
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


def parse_path(path):
    """Only return the path part of an url."""
    # TODO this will not really work yet if link does not
    # start with http(s)//.
    url = parse.urlparse(path)
    return url.path


def is_valid_app_path(path):
    """Check that the path is a existing app path."""
    # Path must start with 'api'.
    log = logging.getLogger(__name__)
    log.debug('Testing path %r', path)
    if path.lstrip('/').startswith('/api'):
        url = 'http://{host}:{port}/{path}'.format(host=config['host'].get(),
                                                   port=config['port'].get(),
                                                   path=path.lstrip('/'))
        # Use a local connection to try and connect to this url.
        response = requests.get(url)
        # If connection is succesful (status code lower than 400 or higher
        # than 599 return True.
        return not 400 <= response.status_code < 600
    return False


def run():
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
    # Set redis pool as the PubSub class redis pool.
    handler = handler_factory(AsyncPubSub, connection_pool=redis_pool)
    start_server = websockets.serve(handler, host=host, port=port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    print('Started Websocket server at {}:{}'.format(host, port))
    log.debug('started websocket server')
    loop.run_forever()
    loop.stop()


if __name__ == '__main__':
    run()
