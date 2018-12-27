import logging
import asyncpg

log = logging.getLogger(__name__)

# TODO: shit is messy af


class Database:
    def __init__(self, host, user, password, database, loop):
        self.loop = loop
        self.dsn = f'postgres://{user}:{password}@{host}/{database}'

    async def create_pool(self):
        pool = await asyncpg.create_pool(self.dsn)
        return pool
