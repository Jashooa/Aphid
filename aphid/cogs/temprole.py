import logging

import discord
from discord.ext import commands

from utils import time
from utils.paginator import Pages

log = logging.getLogger(__name__)


class TempRole:
    """For managing temporary roles for users."""

    def __init__(self, bot):
        self.bot = bot

    async def on_temprole_timer_complete(self, timer):
        query = 'SELECT * FROM temproles WHERE timer_id = ($1);'
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

            role = discord.utils.get(guild.roles, id=record['role_id'])
            if role is None:
                return

            try:
                await member.send(f'Your role of **{role.name}** has expired.')
            except discord.errors.Forbidden:
                pass

            await member.remove_roles(role, reason='Temprole Expiration')

    @commands.group()
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole(self, ctx):
        pass

    @temprole.command(name='list', description='Lists temporary roles')
    @commands.bot_has_permissions(embed_links=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_list(self, ctx, member: discord.Member=None):
        """Lists temporary roles."""

        if member is None:
            query = 'SELECT * FROM temproles INNER JOIN timers ON temproles.timer_id = timers.id ORDER BY timers.expires;'
            records = await self.bot.pool.fetch(query)
        else:
            query = 'SELECT * FROM temproles INNER JOIN timers ON temproles.timer_id = timers.id WHERE user_id = $1 ORDER BY timers.expires;'
            records = await self.bot.pool.fetch(query, member.id)

        if len(records) == 0:
            return await ctx.send('No temporary roles to list.')

        # embed = discord.Embed(title='Temprole List', colour=discord.Colour.green())

        # embed.description = ''
        entries = []
        for record in records:
            user = discord.utils.get(ctx.guild.members, id=record['user_id'])
            role = discord.utils.get(ctx.guild.roles, id=record['role_id'])
            expires = record['expires'].isoformat(timespec='minutes')

            # embed.description = embed.description + f'**{user}** {role} **Expires:** {expires} UTC\n'
            entries.append(f'**{user}** {role} **Expires:** {expires} UTC')

        p = Pages(ctx, entries=entries)
        p.embed.set_author(name='Temprole List')
        p.embed.colour = discord.Colour.green()
        await p.paginate()

        # await ctx.send(embed=embed)

    @temprole.command(name='add')
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_add(self, ctx, member: discord.Member, duration: time.ShortTime, *, role: discord.Role):
        """Add a temporary role to a member."""

        timers = self.bot.get_cog('Timers')
        if timers is None:
            return await ctx.send('Timers module is not loaded.')

        query = 'SELECT * FROM temprole_whitelist;'
        records = await self.bot.pool.fetch(query)

        roles = []
        for record in records:
            roles.append(record['role_id'])

        if role.id not in roles:
            return await ctx.send(f'{role.name} not whitelisted.')

        query = 'SELECT * FROM temproles WHERE user_id = $1 AND role_id = $2'
        record = await self.bot.pool.fetchrow(query, member.id, role.id)
        # Doesn't already exist
        if record is None:
            # Create timer
            timer = await timers.create_timer('temprole', duration.datetime)

            # Add to database
            query = 'INSERT INTO temproles (user_id, role_id, timer_id) VALUES ($1, $2, $3);'
            await self.bot.pool.execute(query, member.id, role.id, timer.id)

            await member.add_roles(role, reason='Temprole Add')

            await ctx.send(f'{member.mention} given role {role.name} for {time.human_timedelta(duration.delta)}.')
        else:
            await timers.update_timer(record['timer_id'], duration, extend=True)

            await ctx.send(f'{member.mention} extended role {role.name} for {time.human_timedelta(duration.delta)}.')

    @temprole.command(name='remove', description='Remove a temporary role from someone')
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_remove(self, ctx, member: discord.Member, *, role: discord.Role):
        """Remove a temporary role from a member."""

        query = 'SELECT timer_id FROM temproles WHERE user_id = $1 AND role_id = $2;'
        record = await self.bot.pool.fetchrow(query, member.id, role.id)

        timer_id = record['timer_id']

        timers = self.bot.get_cog('Timers')
        if timers is None:
            return await ctx.send('Timers module is not loaded.')
        else:
            await timers.remove_timer(timer_id)

        await member.remove_roles(role, reason='Temprole Remove')

        await ctx.send(f'Removed role {role.name} from {member.mention}.')

    @temprole.group(name='whitelist', description='Lists temporary role whitelist', invoke_without_command=True)
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_whitelist(self, ctx):
        """List roles in the temporary role whitelist."""

        query = 'SELECT * FROM temprole_whitelist;'
        records = await self.bot.pool.fetch(query)

        if len(records) == 0:
            return await ctx.send('Whitelist Empty')
        else:
            embed = discord.Embed(title='Temprole Whitelist', colour=discord.Colour.green())
            roles = []
            for record in records:
                roles.append(discord.utils.get(ctx.guild.roles, id=record['role_id']).name)

            roles.sort()

            embed.description = ''
            for role in roles:
                embed.description = embed.description + role + '\n'

            await ctx.send(embed=embed)

    @temprole_whitelist.command(name='add', description='Add a temporary role to the whitelist')
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_whitelist_add(self, ctx, *, role: discord.Role):
        """Add a role to the temporary role whitelist."""

        query = 'INSERT INTO temprole_whitelist (role_id) VALUES ($1);'
        await self.bot.pool.execute(query, role.id)

        await ctx.send(f'Added role {role.name} to whitelist.')

    @temprole_whitelist.command(name='remove', description='Remove a temporary role from the whitelist')
    @commands.has_any_role('Queen', 'Inquiline')
    @commands.guild_only()
    async def temprole_whitelist_remove(self, ctx, *, role: discord.Role):
        """Remove a role from the temporary role whitelist."""

        query = 'DELETE FROM temprole_whitelist WHERE role_id = $1;'
        await self.bot.pool.execute(query, role.id)

        await ctx.send(f'Removed role {role.name} from whitelist.')


def setup(bot):
    bot.add_cog(TempRole(bot))
