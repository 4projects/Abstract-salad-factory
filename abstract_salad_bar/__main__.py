import logging
from tempfile import TemporaryDirectory

import morepath

from .app import App
from .static import get_static

log = logging.getLogger(__name__)


def run():
    logging.basicConfig(level=logging.DEBUG)
    morepath.autoscan()

    with TemporaryDirectory() as tempdir:
        log.debug('Created temporary directory %s.', tempdir)
        app = get_static(App(), tempdir)

        morepath.run(app)


if __name__ == '__main__':
    run()
