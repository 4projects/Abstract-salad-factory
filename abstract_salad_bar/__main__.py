import logging

import morepath
import webob
from webob.static import DirectoryApp

from .app import App
from .static import get_static


def run():
    logging.basicConfig(level=logging.DEBUG)
    morepath.autoscan()

    app = get_static(App())

    morepath.run(app)


if __name__ == '__main__':
    run()
