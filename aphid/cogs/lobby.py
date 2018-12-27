import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class Lobby:
    """Server lobby management commands."""

    def __init__(self, bot):
        self.bot = bot
        self.lobby_channel = 'lobby'
        self.welcome_channel = 'general'
        self.verified_role = 'Ant'
        self.welcome_role = 'Welcome'

    async def on_message(self, message):
        if message.guild is None:
            return

        if message.guild.id != self.bot.guild_id:
            return

        if message.channel.name != self.lobby_channel:
            return

        if message.author == self.bot.user:
            return

        try:
            await message.delete()
        except discord.errors.NotFound:
            pass

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def verify(self, ctx):
        if ctx.channel.name != self.lobby_channel:
            return

        if len(ctx.author.roles) > 1:
            role = discord.utils.get(ctx.guild.roles, name=self.verified_role)
            await ctx.author.add_roles(role, reason='Verification')
        else:
            role = discord.utils.get(ctx.guild.roles, name=self.verified_role)
            await ctx.author.add_roles(role, reason='Verification')

            welcome_channel = discord.utils.get(ctx.guild.channels, name=self.welcome_channel)
            welcome_role = discord.utils.get(ctx.guild.roles, name=self.welcome_role)
            await welcome_channel.send(f'{ctx.author.mention}, {welcome_role.mention} to **{ctx.guild.name}**!')

    @commands.group(name='antiraid', invoke_without_command=True)
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def antiraid(self, ctx):
        """Enable antiraid to prevent new users from accessing the rest of the server."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        channel = discord.utils.get(ctx.guild.channels, name=self.lobby_channel)

        overwrite = dict(channel.overwrites)[ctx.guild.default_role]
        overwrite.send_messages = False

        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason='AntiRaid Enabled')
        await ctx.send('AntiRaid enabled.')

    @antiraid.command(name='off')
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def antiraid_off(self, ctx):
        """Disable antiraid."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        channel = discord.utils.get(ctx.guild.channels, name=self.lobby_channel)

        overwrite = dict(channel.overwrites)[ctx.guild.default_role]
        overwrite.send_messages = True

        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason='AntiRaid Disabled')
        await ctx.send('AntiRaid disabled.')


def setup(bot):
    bot.add_cog(Lobby(bot))
