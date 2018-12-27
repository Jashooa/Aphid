import asyncio
import datetime
import logging

import discord

from utils import time

log = logging.getLogger(__name__)


class JoinLeaveLog:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 'join-leave-logs'
        self._invite_cache = []
        self._task = bot.loop.create_task(self.cache_update())

    def __unload(self):
        self._task.cancel()

    async def get_invites(self):
        guild = self.bot.get_guild(self.bot.guild_id)
        invites = await guild.invites()
        return invites

    async def cache_update(self):
        try:
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                self._invite_cache = await self.get_invites()
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            self.bot.loop.call_exception_handler({'exception': ex})

    async def attempt_invite_source(self):
        invites = await self.get_invites()

        found_invite = None

        for invite in invites:
            for cached_invite in self._invite_cache:
                if invite.code == cached_invite.code:
                    if invite.uses != cached_invite.uses:
                        found_invite = invite
                        break

        self._invite_cache = await self.get_invites()
        return found_invite

    async def on_member_join(self, member):
        if member.guild.id != self.bot.guild_id:
            return

        embed = discord.Embed(colour=discord.Colour.green())
        embed.set_author(name='Member Joined', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {str(member)}'

        age = datetime.datetime.utcnow() - member.created_at
        if age <= datetime.timedelta(days=7):
            embed.add_field(name='New Account', value=f'Created {time.human_timedelta(age)} ago.', inline=False)

        invite = await self.attempt_invite_source()
        if invite is not None:
            embed.add_field(name='Invite', value=f'{invite.code}', inline=False)
            inviter = f'{str(invite.inviter)} (ID: {invite.inviter.id})' if invite.inviter is not None else 'None'
            embed.add_field(name='Invite Creator', value=inviter, inline=False)

        embed.set_footer(text=f'ID: {member.id}')
        embed.timestamp = member.joined_at

        channel = discord.utils.get(member.guild.channels, name=self.log_channel)
        await channel.send(embed=embed)

    async def on_member_remove(self, member):
        if member.guild.id != self.bot.guild_id:
            return

        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name='Member Left', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {str(member)}'

        embed.set_footer(text=f'ID: {member.id}')
        embed.timestamp = datetime.datetime.utcnow()

        channel = discord.utils.get(member.guild.channels, name=self.log_channel)
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(JoinLeaveLog(bot))
