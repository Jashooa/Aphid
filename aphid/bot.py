import datetime
import logging
import traceback

import aiohttp
import discord
from discord.ext import commands

from utils import formatting

log = logging.getLogger(__name__)

initial_extensions = [
    'cogs.ants',
    'cogs.autorole',
    'cogs.joinleavelog',
    'cogs.lobby',
    'cogs.meta',
    'cogs.moderation',
    'cogs.owner',
    'cogs.serverlog',
    'cogs.stickymessage',
    'cogs.temprole',
    'cogs.timers',
    'cogs.voicelog'
]


class AphidBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, pm_help=None, help_attrs=dict(hidden=True))

        self.pool = kwargs.pop('pool')
        self.guild_id = int(kwargs.pop('guild_id'))
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.initial_extensions = initial_extensions

        self.remove_command('help')

        self.loop.set_exception_handler(self.async_exception_handler)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as ex:
                log.warning(f'Failed to load extension {extension} {ex}.')

    async def close(self):
        await super().close()
        await self.session.close()

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        log.info(f'Ready: {self.user} (ID: {self.user.id})')

        if self.owner_id is None:
            app = await self.application_info()
            self.owner_id = app.owner.id

    async def on_error(self, event, *args, **kwargs):
        await self.wait_until_ready()
        if self.owner_id is None:
            app = await self.application_info()
            self.owner_id = app.owner.id

        embed = discord.Embed(title='Error', colour=discord.Colour.red())
        embed.add_field(name='Event', value=event)
        description = traceback.format_exc()
        description = formatting.truncate(description, 2000)
        embed.description = formatting.codeblock(description, lang='py')
        embed.timestamp = datetime.datetime.utcnow()

        owner = await self.get_user_info(self.owner_id)
        await owner.send(embed=embed)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.BadArgument):
            await ctx.send(error)

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(error)

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send('This command is disabled and cannot be used.')

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f'This command is on cooldown. Please retry in {error.retry_after:.0f}s.')

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'Missing parameter: {error.param.name}.')

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f'You are missing permissions: {", ".join(error.missing_perms)}.')

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f'I am missing permissions: {", ".join(error.missing_perms)}.')

        elif isinstance(error, commands.CommandInvokeError):
            trace = ''.join(traceback.format_exception(type(error.original), error.original, error.original.__traceback__))

            log.error(f'Error in command {ctx.command.qualified_name}:')
            log.error(trace)

            embed = discord.Embed(title='Command Error', colour=discord.Colour.red())
            embed.add_field(name='Command', value=ctx.command.qualified_name)
            embed.add_field(name='User', value=str(ctx.author))
            embed.add_field(name='Message', value=formatting.truncate(ctx.message.content, 512) if ctx.message.content != '' else 'None')
            description = formatting.codeblock(trace, lang='py')
            embed.description = formatting.truncate(description, 2000)
            embed.timestamp = datetime.datetime.utcnow()

            owner = await self.get_user_info(self.owner_id)
            await owner.send(embed=embed)

            try:
                await ctx.author.send(f'{ctx.author.mention}, that command just broke me 😮. An error report has been sent to {self.get_user(self.owner_id).name} and a fix will follow shortly 👍.')
            except discord.errors.Forbidden:
                pass

    def async_exception_handler(self, loop, context):
        self.loop.create_task(self.send_async_error(loop, context))

    async def send_async_error(self, loop, context):
        await self.wait_until_ready()
        if self.owner_id is None:
            app = await self.application_info()
            self.owner_id = app.owner.id

        embed = discord.Embed(title='Async Error', colour=discord.Colour.red())
        if 'message' in context:
            embed.add_field(name='Message', value=context['message'])
        error = context['exception']
        description = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        description = formatting.truncate(description, 2000)
        embed.description = formatting.codeblock(description, lang='py')
        embed.timestamp = datetime.datetime.utcnow()

        owner = await self.get_user_info(self.owner_id)
        await owner.send(embed=embed)
