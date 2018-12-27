import asyncio
import datetime
import logging

import asyncpg
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# Stolen and modified from https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/reminder.py


class Timer:
    """Function class to provide timers."""

    __slots__ = ('id', 'event', 'expires')

    def __init__(self, *, record):
        self.id = record['id']
        self.event = record['event']
        self.expires = record['expires']

    @classmethod
    def temporary(cls, *, event, expires):
        pseudo = {
            'id': None,
            'event': event,
            'expires': expires
        }
        return cls(record=pseudo)

    def __eq__(self, other):
        try:
            return self.id == other.id
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f'<Timer id={self.id} event={self.event} expires={self.expires}>'


class Timers:
    def __init__(self, bot):
        self.bot = bot
        self._have_data = asyncio.Event(loop=bot.loop)
        self._current_timer = None
        self._task = bot.loop.create_task(self.wait_for_timer())
        self._timer_done = {}

    def __unload(self):
        self._have_data.clear()
        self._current_timer = None
        self._task.cancel()

    @commands.command(hidden=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_owner()
    async def timers(self, ctx):
        """List all timers."""

        query = 'SELECT * FROM timers ORDER BY expires LIMIT 10;'
        records = await self.bot.pool.fetch(query)

        if len(records) == 0:
            return await ctx.send('No timers.')
        else:
            embed = discord.Embed(title='Timers', colour=discord.Colour.green())

            timers = ''
            for record in records:
                timers += f'id: {record["id"]} event: {record["event"]} expires: {record["expires"]}\n'
            embed.add_field(name='Current Timer', value=self._current_timer)
            embed.add_field(name='Next 10', value=timers)

            await ctx.send(embed=embed)

    def reset(self):
        self._have_data.clear()
        self._current_timer = None
        self._task.cancel()
        self._task = self.bot.loop.create_task(self.wait_for_timer())

    async def get_active_timer(self, *, days=7):
        try:
            query = "SELECT * FROM timers WHERE expires < (now() at time zone 'utc' + $1::interval) ORDER BY expires LIMIT 1;"
            record = await self.bot.pool.fetchrow(query, datetime.timedelta(days=days))

            return Timer(record=record) if record else None
        except asyncio.CancelledError:
            pass

    async def wait_for_timer(self, *, days=7):
        try:
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                timer = self._current_timer = await self.get_active_timer(days=days)

                if timer is None:
                    self._have_data.clear()

                    try:
                        await asyncio.wait_for(self._have_data.wait(), 86400 * days)
                    except asyncio.TimeoutError:
                        pass
                else:
                    now = datetime.datetime.utcnow()

                    if timer.expires >= now:
                        to_sleep = (timer.expires - now).total_seconds()
                        await asyncio.sleep(to_sleep)

                    await self.call_timer(timer)
        except asyncio.CancelledError:
            pass
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.wait_for_timer())
        except Exception as ex:
            self.bot.loop.call_exception_handler({'exception': ex})

    async def call_timer(self, timer):
        try:
            if timer.id in self._timer_done:
                return

            self._timer_done[timer.id] = asyncio.Event(loop=self.bot.loop)

            event_name = f'{timer.event}_timer_complete'
            self.bot.dispatch(event_name, timer)

            await self._timer_done[timer.id].wait()
            del self._timer_done[timer.id]
        except asyncio.CancelledError:
            pass

    async def create_timer(self, event, expires):
        now = datetime.datetime.utcnow()
        timer = Timer.temporary(event=event, expires=expires)
        delta = (expires - now).total_seconds()

        query = 'INSERT INTO timers (event, expires) VALUES ($1, $2) RETURNING id;'
        record = await self.bot.pool.fetchrow(query, event, expires)
        timer.id = record[0]

        if delta <= (86400 * 7):
            self._have_data.set()

        if self._current_timer and expires < self._current_timer.expires:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.wait_for_timer())

        return timer

    async def remove_timer(self, id):
        query = 'DELETE FROM timers WHERE id = $1;'
        await self.bot.pool.execute(query, id)
        if id in self._timer_done:
            self._timer_done[id].set()
        else:
            self.reset()

    async def update_timer(self, id, duration, *, extend=False):
        if extend:
            query = 'UPDATE timers SET expires = (expires + $1::interval) WHERE id = $2;'
            await self.bot.pool.execute(query, datetime.delta, id)
        else:
            query = 'UPDATE timers SET expires = $1 WHERE id = $2;'
            await self.bot.pool.execute(query, duration.datetime, id)
        self.reset()


def setup(bot):
    bot.add_cog(Timers(bot))
