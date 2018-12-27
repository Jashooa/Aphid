import logging

import discord

log = logging.getLogger(__name__)


class AutoRole:
    def __init__(self, bot):
        self.bot = bot
        self.role_name = 'Egg'
        self.lobby_channel = 'lobby'
        self.verified_role = 'Ant'

    async def on_message(self, message):
        if message.guild is None:
            return

        if message.guild.id != self.bot.guild_id:
            return

        if message.channel.name == self.lobby_channel:
            return

        if message.author.bot:
            return

        member = message.author

        roles = member.roles
        verified_role = discord.utils.get(message.guild.roles, name=self.verified_role)

        if verified_role in roles:
            roles.remove(verified_role)

        if len(roles) > 1:
            return

        role = discord.utils.get(message.guild.roles, name=self.role_name)

        await member.add_roles(role, reason='AutoRole')


def setup(bot):
    bot.add_cog(AutoRole(bot))
