import asyncio
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
        self.client = None

    def start(self, url, origin, **kwargs):
        client = websockets.connect(url, loop=self._loop, origin=origin,
                                    **kwargs)
        self.client = self._loop.run_until_complete(client)
        return self.client

    def __call__(self, *args, **kwargs):
        return self.start(*args, **kwargs)

    def stop(self):
        if not self.client:  # pragma: no cover
            return
        self._loop.run_until_complete(self.client.close())
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self.client.worker_task, timeout=1,
                                 loop=self._loop)
            )
        except asyncio.TimeoutError:  # pragma: no cover
            pytest.fail('Client failed to stop')


@pytest.fixture
def client(event_loop):
    client = Client(loop=event_loop)
    yield client
    client.stop()


class Server:
    def __init__(self, *, loop=None):
        self._loop = loop
        if not self._loop:  # pragma: no cover
            self._loop = asyncio.get_event_loop()
        self.server = None

    def start(self, host, port, pubsub_class, **kwargs):
        handler = websocket.handler_factory(pubsub_class, loop=self._loop,
                                            **kwargs)
        server = websockets.serve(handler, host=host, port=port,
                                  loop=self._loop)
        self.server = self._loop.run_until_complete(server)
        return self.server

    def __call__(self, *args, **kwargs):
        return self.start(*args, **kwargs)

    def stop(self):
        if not self.server:  # pragma: no cover
            return
        self.server.close()
        try:
            self._loop.run_until_complete(
                asyncio.wait_for(self.server.wait_closed(), timeout=1,
                                 loop=self._loop)
            )
        except asyncio.TimeoutError:  # pragma: no cover
            pytest.fail('Server failed to stop')


@pytest.fixture
def server(event_loop):
    server = Server(loop=event_loop)
    # TODO error logs in this part should result in a failure.
    yield server
    server.stop()


class MockPubSub(object):
    def __init__(self, loop=None, *args, **kwargs):
        self._loop = loop
        pass

    def subscribe(self, path):
        print(path)

    def unsubscribe(self, path=None):
        pass

    async def listen(self):
        await asyncio.sleep(1, loop=self._loop)
        return {'type': '',
                'channel': b''}


class TestWebSocketHandler:

    host = 'localhost'
    port = 5010

    @property
    def origin(self):
        return 'http://{}:{}'.format(self.host, self.port)

    @pytest.fixture(autouse=True)
    def mock_is_valid_path(self, config, requests_mocker):
        config['host'] = self.host
        config['port'] = self.port
        matcher = re.compile(r'^{}'.format(self.origin))
        requests_mocker.get(matcher)

    def test_connect(self, unused_tcp_port, client, server):
        host = 'localhost'
        url = 'ws://{}:{}/api'.format(host, unused_tcp_port)
        server = server(host, unused_tcp_port, MockPubSub)
        client = client(url, origin=self.origin)
        assert client.open

    @pytest.mark.parametrize('path', [
        'path/',
        'path',
        'path/ws',
        'path/ws/',
        'path/hello/ws/',
        'path/hello/ws',
        'path/hello/',
        'path/hello',
    ])
    def test_connect_with_path(self, unused_tcp_port, client, server, path):
        host = 'localhost'
        url = 'ws://{}:{}/api/{}'.format(host, unused_tcp_port, path)
        server = server(host, unused_tcp_port, MockPubSub)
        client = client(url, origin=self.origin)
        assert client.open

    # Test failing paths should close client
    # Test that subscribe, unsubscribe and listen work.
