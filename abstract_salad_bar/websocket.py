import asyncio
from concurrent.futures import CancelledError
import json
import logging
from urllib import parse

import redis

import websockets

from .config import config, load_config


class PubSub(object):

    _redis_pool = None
    functions = ('ls', 'subscribe', 'unsubscribe')
    log = None

    def __init__(self, websocket, path):
        if not self.log:
            self.log = logging.getLogger(__name__)
        self.log.debug('init')
        self.log.debug('websocket path: %s', path)
        self.websocket = websocket
        self.subscriptions = set()
        # Redis connect, make sure we have a pool.
        self._redis = redis.StrictRedis(
            connection_pool=self.get_redis_pool()
        )
        self.p = self._redis.pubsub()
        path = path.rstrip('/')
        if path.endswith('/ws'):
            path = path[:-3]
        if path:
            asyncio.ensure_future(
                self.subscribe({'path': path})
            )
        self.log.debug('init done')

    @classmethod
    def get_redis_pool(cls):
        """Create and reuse a redis pool."""
        if cls._redis_pool is None:
            cls._redis_pool = redis.ConnectionPool.from_url(
                config['redis_uri'].get()
            )
        return cls._redis_pool

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.p.unsubscribe()
        except Exception as e:
            self.log.Exception('Clean-up failed: %s', e)
        if exc_val:
            self.log.Exception('Websocket handling failed: %s', exc_val,
                               exc_info=(exc_type, exc_val, exc_tb))

    @classmethod
    async def create(cls, websocket, path):
        cls.log = logging.getLogger(__name__)
        cls.log.debug('Creating new websocket.')
        with cls(websocket, path) as self:
            await self.handle()

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
            self.log.debug('Subscribing to path: %s', path)
            # TODO check that path really exists.
            self.p.subscribe(path)
            self.subscriptions.add(path)
        else:
            await self.websocket.send(json.dumps(
                {'error': 'Already subscribed to path: {}'.format(path)}
            ))

    async def unsubscribe(self, message):
        path = parse_path(message['path'])
        if path in self.subscriptions:
            self.p.unsubscribe(path)
            self.subscriptions.remove(path)
        else:
            await self.websocket.send(json.dumps(
                {'error': 'Not subscribed to path: {}'.format(path)}
            ))

    async def get_redis_message(self):
        while True:
            message = self.p.get_message()
            if message:
                return message
            await asyncio.sleep(0.1)

    async def producer(self):
        message = await self.get_redis_message()
        self.log.debug('the message %s', message)
        function = message['type']
        response = {'function': function,
                    'path': message['channel'].decode('utf-8')}
        if function == 'message':
            data = json.loads(message['data'])
            response.update({'data': data['data'],
                             'type': data['type']})
        await self.websocket.send(json.dumps(response))


def parse_path(path):
    """Only return the path part of an url."""
    # TODO this will not really work yet if link does not
    # start with http(s)//.
    url = parse.urlparse(path)
    return url.path


def run():
    load_config()
    log = logging.getLogger(__name__)
    host = config['websocket']['host'].get()
    port = config['websocket']['port'].get()
    # Test that we can connect to redis.
    redis.StrictRedis(connection_pool=PubSub.get_redis_pool()).get(None)
    start_server = websockets.serve(PubSub.create, host=host, port=port)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    print('Started Websocket server at {}:{}'.format(host, port))
    log.debug('started websocket server')
    loop.run_forever()
    loop.stop()


if __name__ == '__main__':
    run()
