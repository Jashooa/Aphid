import datetime
import logging

import discord

from utils import formatting

log = logging.getLogger(__name__)


class ServerLog:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 'server-logs'
        self.ignored_channels = [
            'server-logs',
            'admin-stuff',
            'bot-test-stuff'
        ]

    async def on_message_delete(self, message):
        if message.guild is None:
            return

        if message.guild.id != self.bot.guild_id:
            return

        if message.author.bot:
            return

        for channel in self.ignored_channels:
            if message.channel.name == channel:
                return

        member = message.author
        channel = message.channel

        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name='Message Deleted', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {member}'

        embed.add_field(name='Channel', value=channel.mention, inline=False)
        embed.add_field(name='Message', value=formatting.truncate(message.content, 512) if message.content != '' else 'None')

        for attachment in message.attachments:
            embed.add_field(name='Attachment', value=attachment.proxy_url)

        embed.set_footer(text=f'ID: {member.id}')
        embed.timestamp = datetime.datetime.utcnow()

        channel = discord.utils.get(message.guild.channels, name=self.log_channel)
        await channel.send(embed=embed)

    async def on_message_edit(self, before, after):
        message = after
        if message.guild is None:
            return

        if message.guild.id != self.bot.guild_id:
            return

        if message.author.bot:
            return

        for channel in self.ignored_channels:
            if message.channel.name == channel:
                return

        if before.content == after.content:
            return

        member = message.author
        channel = message.channel

        embed = discord.Embed(colour=discord.Colour.orange())
        embed.set_author(name='Message Edited', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {member}'

        embed.add_field(name='Channel', value=channel.mention, inline=False)
        embed.add_field(name='Before', value=formatting.truncate(before.content, 512) if before.content != '' else 'None', inline=False)
        embed.add_field(name='After', value=formatting.truncate(after.content, 512) if after.content != '' else 'None', inline=False)

        embed.set_footer(text=f'ID: {member.id}')
        embed.timestamp = datetime.datetime.utcnow()

        channel = discord.utils.get(message.guild.channels, name=self.log_channel)
        await channel.send(embed=embed)

    async def on_member_update(self, before, after):
        member = after
        if member.guild is None:
            return

        if member.guild.id != self.bot.guild_id:
            return

        if before.nick != after.nick:
            embed = discord.Embed(colour=discord.Colour.blue())
            embed.set_author(name='Nickname Changed', icon_url=member.avatar_url)
            embed.description = f'{member.mention} {str(member)}'

            embed.add_field(name='Before', value=before.nick, inline=False)
            embed.add_field(name='After', value=after.nick, inline=False)

            embed.set_footer(text=f'ID: {member.id}')
            embed.timestamp = datetime.datetime.utcnow()

            channel = discord.utils.get(member.guild.channels, name=self.log_channel)
            await channel.send(embed=embed)

        if before.name != after.name:
            embed = discord.Embed(colour=discord.Colour.dark_blue())
            embed.set_author(name='Username Changed', icon_url=member.avatar_url)
            embed.description = f'{member.mention} {str(member)}'

            embed.add_field(name='Before', value=str(before), inline=False)
            embed.add_field(name='After', value=after, inline=False)

            embed.set_footer(text=f'ID: {member.id}')
            embed.timestamp = datetime.datetime.utcnow()

            channel = discord.utils.get(member.guild.channels, name=self.log_channel)
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(ServerLog(bot))
