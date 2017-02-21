import argparse
from logging.config import dictConfig
import logging

import confuse

template = {
    'port': int,
    'host': str,
    'db_uri': str,
    'redis_uri': str,
    'websocket': {'port': int,
                  'host': str},
    'log': {'version': int}
}

config = confuse.LazyConfig('ASF', __name__)


def load_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='App config.')

    args = parser.parse_args()
    if args.config:
        config.set_file(args.config)

    # Validate config.
    config.get(template)
    dictConfig(config['log'].get())
    log = logging.getLogger(__name__)
    log.debug('Loaded config')


if __name__ == '__main__':
    load_config()
