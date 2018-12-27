import datetime
import logging

import discord
from discord.ext import commands

from utils import checks, converters, formatting, time
from utils.paginator import Pages

log = logging.getLogger(__name__)


class Moderation:
    """Server moderation commands."""

    def __init__(self, bot):
        self.bot = bot
        self.log_channel = 'mod-logs'
        self.mute_role = 'Muted'
        self.protected_roles = [
            'Queen',
            'Inquiline',
            'Alate'
        ]

    async def on_member_join(self, member):
        if member.guild is None:
            return

        if member.guild.id != self.bot.guild_id:
            return

        query = 'SELECT * FROM mod_tempactions WHERE user_id = $1;'
        record = await self.bot.pool.fetchrow(query, member.id)

        if record is not None:
            role = discord.utils.get(member.guild.roles, name=self.mute_role)
            await member.add_roles(role, reason='Tempmute Reapplication')

    async def log_action(self, guild: discord.Guild, action: str, member: discord.Member, moderator: discord.Member, issued: datetime.datetime, *, duration: time.ShortTime = None, reason: str = None):
        query = 'INSERT INTO mod_cases (action, user_id, mod_id, issued, duration, reason) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;'

        duration = duration.delta if duration is not None else duration

        record = await self.bot.pool.fetchrow(query, action, member.id, moderator.id, issued, duration, reason)

        embed = discord.Embed()

        if action == 'warn':
            embed.colour = discord.Colour.gold()
        elif action == 'mute' or action == 'tempmute':
            embed.colour = discord.Colour.orange()
        elif action == 'kick':
            embed.colour = discord.Colour.dark_orange()
        elif action == 'ban' or action == 'tempban':
            embed.colour = discord.Colour.red()
        elif action == 'unmute' or action == 'unban':
            embed.colour = discord.Colour.blue()

        embed.set_author(name=action.capitalize(), icon_url=member.avatar_url)
        embed.description = f'{member.mention} {member}'

        embed.add_field(name='Moderator', value=f'{moderator.mention} {moderator}', inline=False)

        if duration is not None:
            embed.add_field(name='Duration', value=time.human_timedelta(duration), inline=False)

        embed.add_field(name='Reason', value=formatting.truncate(reason, 512) if reason is not None else 'None')

        embed.set_footer(text=f'Case #{record["id"]} • ID: {member.id}')
        embed.timestamp = issued

        channel = discord.utils.get(guild.channels, name=self.log_channel)
        await channel.send(embed=embed)

    async def temp_action(self, action: str, member: discord.Member, duration: time.ShortTime):
        timers = self.bot.get_cog('Timers')
        if timers is None:
            return

        query = 'SELECT * FROM mod_tempactions WHERE user_id = $1 AND action = $2'
        record = await self.bot.pool.fetchrow(query, member.id, action)

        if record is None:
            timer = await timers.create_timer(action, duration.datetime)

            query = 'INSERT INTO mod_tempactions (user_id, action, timer_id) VALUES ($1, $2, $3);'
            await self.bot.pool.execute(query, member.id, action, timer.id)
        else:
            await timers.update_timer(record['timer_id'], duration.datetime)

    async def on_tempmute_timer_complete(self, timer):
        query = 'SELECT * FROM mod_tempactions WHERE timer_id = ($1);'
        record = await self.bot.pool.fetchrow(query, timer.id)

        timers = self.bot.get_cog('Timers')
        if timers is None:
            return
        await timers.remove_timer(timer.id)

        if record is not None:
            guild = self.bot.get_guild(self.bot.guild_id)
            if guild is None:
                return

            member = guild.get_member(record['user_id'])
            if member is None:
                return

            reason = 'Tempmute Expiration'
            await self.log_action(guild, 'unmute', member, self.bot.user, datetime.datetime.utcnow(), reason=reason)

            try:
                await member.send(f'You have been unmuted in **{guild.name}**.\n**Reason:** {reason}')
            except discord.errors.Forbidden:
                pass

            role = discord.utils.get(guild.roles, name=self.mute_role)
            await member.remove_roles(role, reason=reason)

    async def on_tempban_timer_complete(self, timer):
        query = 'SELECT * FROM mod_tempactions WHERE timer_id = ($1);'
        record = await self.bot.pool.fetchrow(query, timer.id)

        timers = self.bot.get_cog('Timers')
        if timers is None:
            return
        await timers.remove_timer(timer.id)

        if record is not None:
            guild = self.bot.get_guild(self.bot.guild_id)
            if guild is None:
                return

            user = await self.bot.get_user_info(record['user_id'])
            if user is None:
                return

            reason = 'Tempban Expiration'
            await self.log_action(guild, 'unban', user, self.bot.user, datetime.datetime.utcnow(), reason=reason)

            await guild.unban(user, reason=reason)

    @commands.command()
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if checks.has_any_role(member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        await self.log_action(ctx.guild, 'warn', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        try:
            await member.send(f'You have been warned in **{ctx.guild.name}**.\n**Reason:** {reason}')
        except discord.errors.Forbidden:
            pass

        await ctx.send(f'{member.mention} has been warned.\n**Reason:** {reason}')

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def tempmute(self, ctx, member: discord.Member, duration: time.ShortTime, *, reason: str = None):
        """Temporarily mute a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if checks.has_any_role(member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        await self.temp_action('tempmute', member, duration)

        await self.log_action(ctx.guild, 'tempmute', member, ctx.author, datetime.datetime.utcnow(), duration=duration, reason=reason)

        try:
            await member.send(f'You have been temporarily muted in **{ctx.guild.name}** for {time.human_timedelta(duration.delta)}.\n**Reason:** {reason}')
        except discord.errors.Forbidden:
            pass

        role = discord.utils.get(ctx.guild.roles, name=self.mute_role)
        await member.add_roles(role, reason=reason)

        await ctx.send(f'{member.mention} has been temporarily muted for {time.human_timedelta(duration.delta)}.\n**Reason:** {reason}')

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def mute(self, ctx, member: discord.Member, *, reason: str = None):
        """Mute a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if checks.has_any_role(member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        query = 'SELECT timer_id FROM mod_tempactions WHERE user_id = $1 AND action = $2;'
        record = await self.bot.pool.fetchrow(query, member.id, 'tempmute')

        if record is not None:
            timer_id = record['timer_id']

            timers = self.bot.get_cog('Timers')
            if timers is None:
                return await ctx.send('Timers module is not loaded.')
            else:
                await timers.remove_timer(timer_id)

        await self.log_action(ctx.guild, 'mute', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        try:
            await member.send(f'You have been muted in **{ctx.guild.name}**.\n**Reason:** {reason}')
        except discord.errors.Forbidden:
            pass

        role = discord.utils.get(ctx.guild.roles, name=self.mute_role)
        await member.add_roles(role, reason=reason)

        await ctx.send(f'{member.mention} has been muted.\n**Reason:** {reason}')

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member, *, reason: str = None):
        """Unmute a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if checks.has_any_role(member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        query = 'SELECT timer_id FROM mod_tempactions WHERE user_id = $1 AND action = $2;'
        record = await self.bot.pool.fetchrow(query, member.id, 'tempmute')

        if record is not None:
            timer_id = record['timer_id']

            timers = self.bot.get_cog('Timers')
            if timers is None:
                return await ctx.send('Timers module is not loaded.')
            else:
                await timers.remove_timer(timer_id)

        await self.log_action(ctx.guild, 'unmute', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        try:
            await member.send(f'You have been unmuted in **{ctx.guild.name}**.\n**Reason:** {reason}')
        except discord.errors.Forbidden:
            pass

        role = discord.utils.get(ctx.guild.roles, name=self.mute_role)
        await member.remove_roles(role, reason=reason)

        await ctx.send(f'{member.mention} has been unmuted.\n**Reason:** {reason}')

    @commands.command(description='Kick a user')
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kick a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        if checks.has_any_role(member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        await self.log_action(ctx.guild, 'kick', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        try:
            await member.send(f'You have been kicked from **{ctx.guild.name}**.\n**Reason:** {reason}')
        except discord.errors.Forbidden:
            pass

        await ctx.send(f'{member.mention} has been kicked.\n**Reason:** {reason}')

        await member.kick(reason=reason)

    @commands.command(description='Temporarily ban a user')
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def tempban(self, ctx, member: converters.UserConverter, duration: time.ShortTime, *, reason: str = None):
        """Temporarily ban a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        guild_member = ctx.guild.get_member(member.id)

        if guild_member is not None and checks.has_any_role(guild_member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        await self.temp_action('tempban', member, duration)

        await self.log_action(ctx.guild, 'tempban', member, ctx.author, datetime.datetime.utcnow(), duration=duration, reason=reason)

        if guild_member is not None:
            try:
                await member.send(f'You have been temporarily banned from **{ctx.guild.name}** for {time.human_timedelta(duration.delta)}.\n**Reason:** {reason}')
            except discord.errors.Forbidden:
                pass

        await ctx.send(f'{member.mention} has been temporarily banned for {time.human_timedelta(duration.delta)}.\n**Reason:** {reason}')

        await ctx.guild.ban(member, reason=reason, delete_message_days=0)

    @commands.command(description='Ban a user')
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def ban(self, ctx, member: converters.UserConverter, *, reason: str = None):
        """Ban a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        guild_member = ctx.guild.get_member(member.id)

        if guild_member is not None and checks.has_any_role(guild_member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        query = 'SELECT timer_id FROM mod_tempactions WHERE user_id = $1 AND action = $2;'
        record = await self.bot.pool.fetchrow(query, member.id, 'tempban')

        if record is not None:
            timer_id = record['timer_id']

            timers = self.bot.get_cog('Timers')
            if timers is None:
                return await ctx.send('Timers module is not loaded.')
            else:
                await timers.remove_timer(timer_id)

        await self.log_action(ctx.guild, 'ban', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        if guild_member is not None:
            try:
                await member.send(f'You have been banned from **{ctx.guild.name}**.\n**Reason:** {reason}')
            except discord.errors.Forbidden:
                pass

        await ctx.send(f'{member.mention} has been banned.\n**Reason:** {reason}')

        await ctx.guild.ban(member, reason=reason, delete_message_days=0)

    @commands.command(description='Unban a user')
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def unban(self, ctx, member: converters.UserConverter, *, reason: str = None):
        """Unban a member."""

        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass

        guild_member = ctx.guild.get_member(member.id)

        if guild_member is not None and checks.has_any_role(guild_member, *self.protected_roles):
            return await ctx.send(f'That member has a protected role.')

        if await self.bot.is_owner(member):
            return

        if await ctx.guild.get_ban(member) is None:
            return await ctx.send(f'That member is not banned.')

        query = "SELECT timer_id FROM mod_tempactions WHERE user_id = $1 AND action = $2;"
        record = await self.bot.pool.fetchrow(query, member.id, 'tempban')

        if record is not None:
            timer_id = record['timer_id']

            timers = self.bot.get_cog('Timers')
            if timers is None:
                return await ctx.send('Timers module is not loaded.')
            else:
                await timers.remove_timer(timer_id)

        await self.log_action(ctx.guild, 'unban', member, ctx.author, datetime.datetime.utcnow(), reason=reason)

        await ctx.guild.unban(member, reason=reason)

    @commands.group(name='case', description='View a mod case', invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def case(self, ctx, case: int):
        """View a mod case."""

        query = 'SELECT * FROM mod_cases WHERE id = $1;'
        record = await self.bot.pool.fetchrow(query, case)

        if record is None:
            return await ctx.send(f'Case #{case} not found.')

        action = record['action']
        user_id = record['user_id']
        mod_id = record['mod_id']
        issued = record['issued']
        duration = record['duration']
        reason = record['reason']

        member = ctx.guild.get_member(user_id) or await self.bot.get_user_info(user_id)

        moderator = ctx.guild.get_member(mod_id)

        embed = discord.Embed()

        if action == 'warn':
            embed.colour = discord.Colour.gold()
        elif action == 'mute' or action == 'tempmute':
            embed.colour = discord.Colour.orange()
        elif action == 'kick':
            embed.colour = discord.Colour.dark_orange()
        elif action == 'ban' or action == 'tempban':
            embed.colour = discord.Colour.red()
        elif action == 'unmute' or action == 'unban':
            embed.colour = discord.Colour.blue()

        embed.set_author(name=f'{action.capitalize()}', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {member}'

        embed.add_field(name='Moderator', value=f'{moderator.mention} {moderator}', inline=False)

        if duration is not None:
            embed.add_field(name='Duration', value=time.human_timedelta(duration), inline=False)

        embed.add_field(name='Reason', value=formatting.truncate(reason, 512) if reason is not None else 'None')

        embed.set_footer(text=f'Case #{record["id"]} • ID: {member.id}')
        embed.timestamp = issued

        await ctx.send(embed=embed)

    @case.command(name='update', description='Update a mod case')
    @commands.bot_has_permissions(embed_links=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def case_update(self, ctx, case: int, *, reason: str):
        """Update a mod case."""

        query = 'UPDATE mod_cases SET reason = $1 WHERE id = $2 RETURNING *;'
        record = await self.bot.pool.fetchrow(query, reason, case)

        if record is None:
            return await ctx.send(f'Case #{case} not found.')

        action = record['action']
        user_id = record['user_id']
        mod_id = record['mod_id']
        issued = record['issued']
        duration = record['duration']
        reason = record['reason']

        member = ctx.guild.get_member(user_id) or await self.bot.get_user_info(user_id)

        moderator = ctx.guild.get_member(mod_id)

        embed = discord.Embed()

        if action == 'warn':
            embed.colour = discord.Colour.gold()
        elif action == 'mute' or action == 'tempmute':
            embed.colour = discord.Colour.orange()
        elif action == 'kick':
            embed.colour = discord.Colour.dark_orange()
        elif action == 'ban' or action == 'tempban':
            embed.colour = discord.Colour.red()
        elif action == 'unmute' or action == 'unban':
            embed.colour = discord.Colour.blue()

        embed.set_author(name=f'{action.capitalize()} • Update', icon_url=member.avatar_url)
        embed.description = f'{member.mention} {member}'

        embed.add_field(name='Moderator', value=f'{moderator.mention} {moderator}', inline=False)

        if duration is not None:
            embed.add_field(name='Duration', value=time.human_timedelta(duration), inline=False)

        embed.add_field(name='Reason', value=formatting.truncate(reason, 512) if reason is not None else 'None')

        embed.set_footer(text=f'Case #{record["id"]} • ID: {member.id}')
        embed.timestamp = issued

        channel = discord.utils.get(ctx.guild.channels, name=self.log_channel)
        await channel.send(embed=embed)

    @case.command(name='pardon', description='Pardon a mod case')
    # @commands.bot_has_permissions(ban_members=True, manage_roles=True, embed_links=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def case_pardon(self, ctx, case: int):
        """Pardon a mod case."""

        query = 'DELETE FROM mod_cases WHERE id = $1 RETURNING *;'
        record = await self.bot.pool.fetchrow(query, case)

        if record is None:
            return await ctx.send(f'Case #{case} not found.')

        '''action = record['action']
        user_id = record['user_id']

        member = ctx.guild.get_member(user_id) or await self.bot.get_user_info(user_id)

        if action == 'tempmute' or action == 'tempban':
            query = 'SELECT timer_id FROM mod_tempactions WHERE user_id = $1 AND action = $2;'
            record = await self.bot.pool.fetchrow(query, user_id, action)

            if record is not None:
                timer_id = record['timer_id']

                timers = self.bot.get_cog('Timers')
                if timers is None:
                    return await ctx.send('Timers module is not loaded.')
                else:
                    await timers.remove_timer(timer_id)

        if action == 'mute' or action == 'tempmute':
            role = discord.utils.get(ctx.guild.roles, name=self.mute_role)
            await member.remove_roles(role, reason='Pardon')

        if action == 'ban' or action == 'tempban':
            await ctx.guild.unban(member, reason='Pardon')'''

        await ctx.send(f'Case #{case} has been pardoned.')

    @commands.command(description='View all mod cases for a user')
    @commands.bot_has_permissions(embed_links=True)
    @commands.has_any_role('Queen', 'Inquiline', 'Alate')
    @commands.guild_only()
    async def cases(self, ctx, member: converters.UserConverter):
        """View all mod cases for a member."""

        query = 'SELECT * FROM mod_cases WHERE user_id = $1 ORDER BY issued DESC;'
        records = await self.bot.pool.fetch(query, member.id)

        if len(records) == 0:
            return await ctx.send("None found.")

        entries = []
        for record in records:
            id = record['id']
            action = record['action']
            issued = time.human_timedelta(datetime.datetime.utcnow() - record['issued'], largest_only=True)
            duration = record['duration']
            duration = time.human_timedelta(duration) if duration is not None else None
            reason = record['reason']

            if duration is None:
                entries.append(f'#{id} • *{action.capitalize()}* • {reason} • {issued} ago')
            else:
                entries.append(f'#{id} • *{action.capitalize()}* ({duration}) • {reason} • {issued} ago')

        p = Pages(ctx, entries=entries)
        p.embed.set_author(name=f'{member} Cases', icon_url=member.avatar_url)
        p.embed.colour = discord.Colour.red()
        await p.paginate()


def setup(bot):
    bot.add_cog(Moderation(bot))
