import asyncio
import logging

from bot import AphidBot
from utils import config, database


fmt = '[%(asctime)s.%(msecs)03d] %(levelname).1s (%(name)s) %(message)s'
datefmt = '%H:%M:%S'
logging.basicConfig(level=logging.INFO, format=fmt, datefmt=datefmt)

log = logging.getLogger(__name__)


def run():
    loop = asyncio.get_event_loop()
    db = database.Database(
        host=config.cfg['database']['host'],
        user=config.cfg['database']['user'],
        password=config.cfg['database']['password'],
        database=config.cfg['database']['database'],
        loop=loop
    )

    try:
        pool = loop.run_until_complete(db.create_pool())
    except Exception:
        log.exception('Could not set up PostgreSQL. Exiting.')
        return

    bot = AphidBot(command_prefix=config.cfg['bot']['prefix'], guild_id=config.cfg['bot']['guild'], loop=loop, pool=pool)

    log.info('Starting bot')

    try:
        bot.run(config.cfg['bot']['token'], reconnect=True)
    except Exception:
        log.exception('Encountered fatal exception')

    log.info('Closing event loop')
    loop.close()


if __name__ == '__main__':
    run()
