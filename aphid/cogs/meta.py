import logging

import discord
from discord.ext import commands

from utils import checks
from utils.paginator import HelpPaginator

log = logging.getLogger(__name__)


class Meta:
    """Commands related to the bot itself."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    @commands.is_owner()
    async def _help(self, ctx, *, command: str = None):
        """Shows help about a command or the bot"""

        if command is None:
            p = await HelpPaginator.from_bot(ctx)
        else:
            entity = self.bot.get_cog(command) or self.bot.get_command(command)

            if entity is None:
                clean = command.replace('@', '@\u200b')
                return await ctx.send(f'Command or category "{clean}" not found.')
            elif isinstance(entity, commands.Command):
                p = await HelpPaginator.from_command(ctx, entity)
            else:
                p = await HelpPaginator.from_cog(ctx, entity)

        await p.paginate()

    @commands.command()
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.bot_has_permissions(manage_messages=True)
    async def say(self, ctx, *, message: str):
        """Make the bot say a message."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        await ctx.send(message)


def setup(bot):
    bot.add_cog(Meta(bot))
