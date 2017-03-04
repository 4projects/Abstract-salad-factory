import logging

import pytest


@pytest.fixture()
def config():
    from abstract_salad_bar.config import config
    config.clear()
    config.read(user=False)
    return config


@pytest.fixture()
def requests_mocker():
    import requests_mock
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture(scope='session')
def pifpaf_redis():
    try:
        from pifpaf.drivers.redis import RedisDriver
    except ImportError:
        pytest.skip('Failed to load pifpaf redis driver.')
    # Set pifpaf log to at INFO, as it is very spammy at DEBUG.
    from pifpaf.drivers import LOG
    LOG.setLevel(logging.INFO)
    from pytest_asyncio.plugin import unused_tcp_port
    port = unused_tcp_port()
    # start redis server
    pifpaf = RedisDriver(port)
    pifpaf.setUp()
    yield pifpaf
    pifpaf.cleanUp()


@pytest.fixture
def args():
    import sys
    # Save original arguments.
    old_args = sys.argv[:]
    # Remove all but the process name from the arguments.
    sys.argv = sys.argv[:1]
    # Yield the sys.argv, so it is editable by the test.
    yield sys.argv
    # Reset sys.argv to its original value.
    sys.argv = old_args
