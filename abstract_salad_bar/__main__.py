import logging

import morepath
from .app import App


def run():
    logging.basicConfig(level=logging.DEBUG)
    morepath.autoscan()
    app = App()
    # uri = app.settings.db.uri
    morepath.run(app)


if __name__ == '__main__':
    run()
