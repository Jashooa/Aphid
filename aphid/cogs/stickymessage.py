import asyncio
import logging

import discord
from discord.ext import commands

from utils import time

log = logging.getLogger(__name__)


class StickyMessageCache:
    __slots__ = ('channel_id', 'last_message', 'delay', 'image_only', 'content')

    def __init__(self, data):
        self.channel_id = data['channel_id']
        self.last_message = data['last_message']
        self.delay = data['delay']
        self.image_only = data['image_only']
        self.content = data['content']


class StickyMessage:
    """For creating messages that'll sticky at the bottom."""

    def __init__(self, bot):
        self.bot = bot
        self._stickymessage_cache = {}
        self._locks = {}
        bot.loop.create_task(self.init_stickymessage_cache())

    async def on_message(self, message):
        if message.guild is None:
            return

        if message.guild.id != self.bot.guild_id:
            return

        if message.author == self.bot.user:
            return

        entry = await self.get_stickymessage_cache(message.channel.id)
        if entry is None:
            return

        if message.content.startswith(f'{self.bot.command_prefix}stickymessage'):
            return

        if message.channel.id in self._locks:
            return

        if entry.image_only:
            try:
                await self.bot.wait_for('message', timeout=entry.delay, check=lambda m: (m.channel == message.channel and m.author != self.bot.user and len(m.attachments) > 0))
            except asyncio.TimeoutError:
                if len(message.attachments) == 0:
                    return
            else:
                return
        else:
            try:
                await self.bot.wait_for('message', timeout=entry.delay, check=lambda m: (m.channel == message.channel and m.author != self.bot.user))
            except asyncio.TimeoutError:
                pass
            else:
                return

        self._locks[message.channel.id] = True

        try:
            last_message = await message.channel.get_message(entry.last_message)
            await last_message.delete()
        except discord.errors.NotFound:
            pass

        new_message = await message.channel.send(entry.content)

        query = 'UPDATE stickymessages SET last_message = $1 WHERE channel_id = $2 RETURNING *;'
        record = await self.bot.pool.fetchrow(query, new_message.id, message.channel.id)
        cache = StickyMessageCache(record)
        self._stickymessage_cache[message.channel.id] = cache

        try:
            del self._locks[message.channel.id]
        except Exception:
            pass

    async def init_stickymessage_cache(self):
        try:
            await self.bot.wait_until_ready()

            query = 'SELECT * FROM stickymessages;'
            records = await self.bot.pool.fetch(query)

            for record in records:
                cache = StickyMessageCache(record)
                self._stickymessage_cache[record['channel_id']] = cache
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            self.bot.loop.call_exception_handler({'exception': ex})

    async def get_stickymessage_cache(self, channel_id):
        try:
            return self._stickymessage_cache[channel_id]
        except KeyError:
            pass

        query = 'SELECT * FROM stickymessages WHERE channel_id = $1;'
        record = await self.bot.pool.fetchrow(query, channel_id)

        if record is None:
            return None

        cache = StickyMessageCache(record)
        self._stickymessage_cache[channel_id] = cache
        return cache

    async def set_stickymessage(self, ctx, delay: time.ShortTime, image_only: bool, message: str):
        entry = await self.get_stickymessage_cache(ctx.channel.id)

        if entry is not None:
            try:
                last_message = await ctx.channel.get_message(entry.last_message)
                await last_message.delete()
            except discord.errors.NotFound:
                pass

        new_message = await ctx.send(message)

        query = 'INSERT INTO stickymessages (channel_id, last_message, delay, image_only, content) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (channel_id) DO UPDATE SET last_message = $2, delay = $3, image_only = $4, content = $5 RETURNING *;'
        record = await self.bot.pool.fetchrow(query, ctx.channel.id, new_message.id, float(delay.delta.total_seconds()), image_only, message)
        cache = StickyMessageCache(record)
        self._stickymessage_cache[ctx.channel.id] = cache

    @commands.group(name='stickymessage', invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def stickymessage(self, ctx):
        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

    @stickymessage.command(name='set', description='Set a sticky message for the current channel.')
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def stickymessage_set(self, ctx, delay: time.ShortTime, *, message: str):
        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        await self.set_stickymessage(ctx, delay, False, message)

    @stickymessage.command(name='imageset')
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def stickymessage_imageset(self, ctx, delay: time.ShortTime, *, message: str):
        """Set a sticky message for the current channel that replies only to images."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        await self.set_stickymessage(ctx, delay, True, message)

    @stickymessage.command(name='unset')
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def stickymessage_unset(self, ctx):
        """Unset a sticky message for the current channel."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if ctx.channel.id in self._stickymessage_cache:
            del self._stickymessage_cache[ctx.channel.id]

        query = 'DELETE FROM stickymessages WHERE channel_id = $1 RETURNING last_message;'
        record = await self.bot.pool.fetchrow(query, ctx.channel.id)

        if record is not None:
            try:
                message = await ctx.channel.get_message(record[0])
                await message.delete()
            except discord.errors.NotFound:
                pass


def setup(bot):
    bot.add_cog(StickyMessage(bot))
