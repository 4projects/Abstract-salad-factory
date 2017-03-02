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
