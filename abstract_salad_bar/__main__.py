import logging
from tempfile import TemporaryDirectory

import morepath

import transaction

import ZODB
import zodburi

from .app import App
from .model import Root
from .static import get_static

log = logging.getLogger(__name__)


def run():
    # Initialize logging
    logging.basicConfig(level=logging.DEBUG)

    # The morepath scan code
    morepath.autoscan()

    # Get storage from config
    uri = 'memory://'
    storage_factory, dbkw = zodburi.resolve_uri(uri)
    storage = storage_factory()

    # Create database and get root.
    db = ZODB.DB(storage, **dbkw).open()
    root = db.root()
    if 'root' not in root:
        root['root'] = Root()
        transaction.commit()
    root = root['root']
    log.debug('Root id %s', root.id)

    # Initialize app.
    app = App(root)

    # Create temporary directory, and leaf it till app is closed.
    with TemporaryDirectory() as tempdir:
        log.debug('Created temporary directory %s.', tempdir)
        app = get_static(app, tempdir)

        morepath.run(app)


if __name__ == '__main__':
    run()
