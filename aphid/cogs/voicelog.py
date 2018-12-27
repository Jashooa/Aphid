import datetime
import logging

import discord

log = logging.getLogger(__name__)


class ServerLog:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 'voice-logs'

    async def on_voice_state_update(self, member, before, after):
        if member.guild is None:
            return

        if member.guild.id != self.bot.guild_id:
            return

        if before.channel is None and after.channel is not None:
            # joined voice
            embed = discord.Embed(colour=discord.Colour.teal())
            embed.set_author(name='Voice Joined', icon_url=member.avatar_url)
            embed.description = f'{member.mention} {str(member)}'

            embed.add_field(name='Channel', value=after.channel.name, inline=False)

            embed.set_footer(text=f'ID: {member.id}')
            embed.timestamp = datetime.datetime.utcnow()

            channel = discord.utils.get(member.guild.channels, name=self.log_channel)
            await channel.send(embed=embed)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            # changed channel
            embed = discord.Embed(colour=discord.Colour.teal())
            embed.set_author(name='Voice Switched', icon_url=member.avatar_url)
            embed.description = f'{member.mention} {str(member)}'

            embed.add_field(name='Before', value=before.channel.name, inline=False)
            embed.add_field(name='After', value=after.channel.name, inline=False)

            embed.set_footer(text=f'ID: {member.id}')
            embed.timestamp = datetime.datetime.utcnow()

            channel = discord.utils.get(member.guild.channels, name=self.log_channel)
            await channel.send(embed=embed)
        elif before.channel is not None and after.channel is None:
            # left voice
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.set_author(name='Voice Left', icon_url=member.avatar_url)
            embed.description = f'{member.mention} {str(member)}'

            embed.add_field(name='Channel', value=before.channel.name, inline=False)

            embed.set_footer(text=f'ID: {member.id}')
            embed.timestamp = datetime.datetime.utcnow()

            channel = discord.utils.get(member.guild.channels, name=self.log_channel)
            await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(ServerLog(bot))
