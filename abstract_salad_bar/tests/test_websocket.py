import asyncio
from functools import partial
import json
import logging
import re

import pytest

import websockets

from abstract_salad_bar import websocket


@pytest.mark.parametrize('path, status_code, result', [
    ('api/hello', 200, True),
    ('/api/hello', 200, True),
    ('///api/hello', 200, True),
    ('/api/hello/bye', 200, True),
    ('/api/hello/', 200, True),
    ('/api/hello', 400, False),
    ('/api/hello', 403, False),
    ('/api/hello', 500, False),
    ('/api/hello', 404, False),
    ('/api/hello', 600, True),
    ('/api/hello', 302, True),
    ('/hello', 200, False),
])
def test_is_valid_app_path(config, requests_mocker,
                           path, status_code, result):
    host = '127.0.0.1'
    port = 5002
    config['host'] = host
    config['port'] = port
    requests_mocker.get('http://{}:{}/{}'.format(host, port, path.lstrip('/')),
                        status_code=status_code)
    assert(websocket.is_valid_app_path(path) is result)


@pytest.mark.parametrize('in_path, origin, out_path', [
    ('path', 'http://localhost:5000', '/path'),
    ('/path', 'http://localhost:5000', '/path'),
    ('http://example.com/path', 'http://example.com', '/path'),
    ('http://example.com/', 'http://example.com', '/'),
    ('https://example.com/path', 'https://example.com', '/path'),
    ('https://www.example.com/path', 'https://example.com', '/path'),
    ('/path/hello', 'http://localhost:5000', '/path/hello'),
    ('/path/hello/', 'http://localhost:5000', '/path/hello'),
    ('/path/hello?bye', 'http://localhost:5000', '/path/hello'),
    ('/path/hello/?bye', 'http://localhost:5000', '/path/hello'),
    ('/path/hello/#bye', 'http://localhost:5000', '/path/hello'),
    ('/path/hello#bye', 'http://localhost:5000', '/path/hello'),
    ('asf.pietpiet.net/path', 'http://asf.pietpiet.net', '/path'),
    ('http://asf.pietpiet.net/path', 'http://asf.pietpiet.net', '/path'),
    ('http://127.0.0.1:5000/path', 'http://127.0.0.1:5000', '/path'),
    ('127.0.0.1:5000/path', 'http://127.0.0.1:5000', '/path'),
])
def test_parse_path(in_path, origin, out_path):
    assert(websocket.parse_path(in_path, origin=origin) == out_path)


class Client:
    def __init__(self, *, loop=None):
        self._loop = loop
        if not self._loop:  # pragma: no cover
            self._loop = asyncio.get_event_loop()
        self._running = False

    def start(self, url, origin, **kwargs):
        if self._running:  # pragma: no cover
            return
        self._running = True
        client = websockets.connect(url, loop=self._loop, origin=origin,
                                    **kwargs)
        self.client = self._loop.run_until_complete(client)
        return self

    def sync_ping(self, data=None, *, timeout=1):
        return self._loop.run_until_complete(
            asyncio.wait_for(self.ping(data), timeout,
                             loop=self._loop)
        )

    async def ping(self, data=None):
        return await self.client.ping(data)

    def sync_send(self, message, *, timeout=1):
        return self._loop.run_until_complete(
            asyncio.wait_for(self.send(message), timeout,
                             loop=self._loop)
        )

    def sync_recv(self, *, timeout=1):
        return self._loop.run_until_complete(
            asyncio.wait_for(self.recv(), timeout,
                             loop=self._loop)
        )

    async def send(self, message):
        return await self.client.send(message)

    async def recv(self):
        return await self.client.recv()

    @property
    def open(self):
        if not self._running:  # pragma: no cover
            return False
        return self.client.open

    def __call__(self, *args, **kwargs):  # pragma: no cover
        return self.start(*args, **kwargs)

    def stop(self):
        if not self._running:  # pragma: no cover
            return
        self._loop.run_until_complete(self.client.close())
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self.client.worker_task, timeout=1,
                                 loop=self._loop)
            )
        except asyncio.TimeoutError:  # pragma: no cover
            pytest.fail('Client failed to stop.')
        finally:
            self._running = False


@pytest.fixture
def client(event_loop, unused_tcp_port):
    url = 'ws://{}:{}/'.format('localhost', unused_tcp_port)
    client = Client(loop=event_loop)

    def get_client(path='api', *, origin, **kwargs):
        return client.start('{}{}'.format(url, path.lstrip('/')),
                            origin, **kwargs)
    yield get_client
    try:
        client.stop()
    except websockets.ConnectionClosed as e:  # pragma: no cover
        # The server closed the connection unexpectedly, test has failed.
        pytest.fail('Server closed connection unexpectedly. Check logging '
                    'for error message.\n{}'.format(e))


class Server:
    def __init__(self, *, loop=None):
        self._loop = loop
        if not self._loop:  # pragma: no cover
            self._loop = asyncio.get_event_loop()
        self._running = False

    def start(self, host, port, pubsub_class, **kwargs):
        self._running = True
        pubsub_kwargs = kwargs
        pubsub_kwargs['loop'] = self._loop
        print(pubsub_kwargs)
        handler = websocket.handler_factory(pubsub_class, pubsub_kwargs,
                                            loop=self._loop)
        server = websockets.serve(handler, host=host, port=port,
                                  loop=self._loop)
        self.server = self._loop.run_until_complete(server)
        self.pubsub = handler._pubsub
        return self

    def __call__(self, *args, **kwargs):  # pragma: no cover
        return self.start(*args, **kwargs)

    def stop(self):
        if not self._running:  # pragma: no cover
            return
        self.server.close()
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self.server.wait_closed(), timeout=1,
                                 loop=self._loop)
            )
            # task.result()
        except asyncio.TimeoutError:  # pragma: no cover
            pytest.fail('Server failed to stop')
        finally:
            self._running = False


@pytest.fixture
def server(event_loop, unused_tcp_port):
    server = Server(loop=event_loop)
    yield partial(server.start, 'localhost', unused_tcp_port)
    server.stop()


class MockAsyncPubSub(object):
    def __init__(self, *, loop=None, **kwargs):
        self._loop = loop
        self._internal_queue = asyncio.Queue(loop=self._loop)
        # This queue is can be used to get values by external programs.
        self.queue = asyncio.Queue(loop=self._loop)

    async def subscribe(self, path):
        print('Mock subscribing to :', path)
        message = {'type': 'subscribe',
                   'channel': path.encode('utf-8')}
        await self.queue.put(message)
        await self._internal_queue.put(message)

    async def unsubscribe(self, path=None):
        if not path:
            path = 'ALL'
        print('Mock unsubscribing to :', path)
        message = {'type': 'unsubscribe',
                   'channel': path.encode('utf-8')}
        await self.queue.put(message)
        await self._internal_queue.put(message)

    def send_message(self, message):
        self._internal_queue.put_nowait(message)

    async def listen(self):
        message = await self._internal_queue.get()
        print('Mock listener got message:', message)
        return message


class TestWebSocketHandler:

    host = 'localhost'
    origin_port = 5010

    @property
    def origin(self):
        return 'http://{}:{}'.format(self.host, self.origin_port)

    @pytest.fixture(autouse=True)
    def mock_is_valid_path(self, config, requests_mocker):
        config['host'] = self.host
        config['port'] = self.origin_port
        matcher = re.compile(r'^{}'.format(self.origin))
        requests_mocker.get(matcher)

    def test_connect(self,  client, server):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        assert client.open

    @pytest.mark.parametrize('path', [
        'api/path/',
        'api/path',
        'api/path/ws',
        'api/path/ws/',
        'api/path/hello/ws/',
        'api/path/hello/ws',
        'api/path/hello/',
        'api/path/hello',
    ])
    def test_connect_with_path(self, unused_tcp_port, client, server, path):
        server = server(MockAsyncPubSub)
        client = client(path, origin=self.origin)
        assert client.open

    @pytest.mark.parametrize('path, expected', [
        ('api/here', '/api/here'),
        ('api/here/', '/api/here'),
        ('/api/here/', '/api/here'),
        ('api/nowhere', '/api/nowhere'),
        ('api/nowhere/ws', '/api/nowhere/ws'),
    ])
    def test_subscribe_ls_unsubscribe(self, client, server, path, expected):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        tests = [
            ('subscribe', {'path': expected}),
            ('subscribe', {'error':
                           'Already subscribed to path: {}'.format(expected)}),
            ('ls', {'paths': [expected]}),
            ('unsubscribe', {'path': expected}),
            ('ls', {'paths': []}),
            ('unsubscribe', {'error':
                             'Not subscribed to path: {}'.format(expected)}),
            ('subscribe', {'path': expected}),
        ]
        for function, expected in tests:
            message = {'function': function,
                       'path': path}
            message = json.dumps(message)
            client.sync_send(message)
            result = client.sync_recv()
            result = json.loads(result)
            assert result.pop('function') == function
            assert result == expected

    @pytest.mark.parametrize('data', [
        'hello',
    ])
    def test_listen_for_message(self, client, server, data):
        function = 'message'
        type_ = 'CREATE'
        path = '/a/path/s'
        dt = json.dumps({'data': data, 'type': type_}).\
            encode('utf-8')
        m = {'channel': path.encode('utf-8'), 'type': function,
             'data': dt}
        server = server(MockAsyncPubSub)
        client = client('api', origin=self.origin)
        server.pubsub.send_message(m)
        result = client.sync_recv()
        result = json.loads(result)
        assert result['function'] == function
        assert result['path'] == path
        assert result['type'] == type_
        assert result['data'] == data

    def test_subscribe_invalid_path(self, client, server):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        path = '/invalid'
        message = {'function': 'subscribe',
                   'path': path}
        message = json.dumps(message)
        client.sync_send(message)
        result = client.sync_recv()
        result = json.loads(result)
        assert result == {'error': 'Invalid path: {}'.format(path)}

    @pytest.mark.parametrize('message, error', [
        (json.dumps({'function': 'wrong'}),
         'Message function must be one of: {}.'.
         format(', '.join(websocket.WebSocketHandler.functions))),
        (json.dumps({}), 'Message function must be one of: {}.'.
         format(', '.join(websocket.WebSocketHandler.functions))),
        (json.dumps([]), 'Message must be a dict.'),
        ('not json', 'Message is not json loadable.'),
        (json.dumps({'function': 'subscribe'}), 'Message missing path.'),

    ])
    def test_consumer_errors(self, client, server, message, error):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        client.sync_send(message)
        result = client.sync_recv()
        result = json.loads(result)
        assert result['error'] == error

    def test_init_with_invalid_path(self, client, server):
        path = '/invalid/path'
        server = server(MockAsyncPubSub)
        client = client(path, origin=self.origin)
        assert not client.open
        with pytest.raises(websockets.ConnectionClosed) as excinfo:
            client.sync_ping()
        exc = excinfo.value
        assert exc.code == 4004
        assert exc.reason == 'Invalid path'

    def test_unsubscribe_on_close(self, client, server):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        server.stop()
        message = server.pubsub.queue.get_nowait()
        assert message == {'type': 'unsubscribe', 'channel': b'ALL'}

    def test_listen_empty_message(self, client, server):
        server = server(MockAsyncPubSub)
        client = client(origin=self.origin)
        server.pubsub.send_message(None)
        with pytest.raises(asyncio.TimeoutError):
            client.sync_recv(timeout=0.2)
