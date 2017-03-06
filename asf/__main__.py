import logging
from tempfile import TemporaryDirectory

import morepath

from redis import StrictRedis

import transaction

from waitress import serve

import ZODB
import zodburi

from .config import config, load_config
from .app import App
from .model import RootDocument
from .static import get_static


def run():
    load_config()
    log = logging.getLogger(__name__)
    db_uri = config['db_uri'].get()

    # The morepath scan code
    morepath.autoscan()

    # Get storage from config
    log.debug('Accessing zodb: %s', db_uri)
    storage_factory, dbkw = zodburi.resolve_uri(db_uri)
    storage = storage_factory()

    # Create database and get root.
    db = ZODB.DB(storage, **dbkw).open()
    root = db.root()
    if 'root' not in root:
        root['root'] = RootDocument()
        transaction.commit()
    root = root['root']
    log.debug('Root id %s', root.id)

    # Redis connection
    r = StrictRedis.from_url(config['redis_uri'].get())
    # Test that we can connect tot the redis instance.
    r.ping()

    app = App(root, r)

    # Create temporary directory, and leaf it till app is closed.
    with TemporaryDirectory() as tempdir:
        log.debug('Created temporary directory %s.', tempdir)
        app = get_static(app, tempdir)

        log.debug('Starting rest api.')
        serve(app, host=config['host'].get(), port=config['port'].get(int),
              url_scheme=config['url_scheme'].get())


if __name__ == '__main__':  #pragma: no cover
    run()
