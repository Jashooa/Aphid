import sys
import json
import os
import logging

log = logging.getLogger(__name__)

# TODO: shit is messy af

CONFIG_FILE = 'config.json'


def verify_config():
    if os.path.isfile(CONFIG_FILE) is False:
        log.critical('config.json does not exist in root folder.')
        return False

    with open(CONFIG_FILE, 'r') as cfgRead:
        try:
            json.load(cfgRead)
            return True
        except ValueError as e:
            log.critical(f'config.json is not formatted properly {e}')
            return False


def start_config():
    global cfg
    if verify_config():
        with open(CONFIG_FILE, 'r') as cfgFile:
            cfg = json.load(cfgFile)
            return True
    else:
        log.critical('Unable to start bot. Unrecoverable error in loading configuration file.')
        sys.exit(0)


def reload_config():
    global cfg
    if verify_config():
        del cfg
        with open(CONFIG_FILE, 'r') as cfgFile:
            cfg = json.load(cfgFile)
            return True


start_config()
