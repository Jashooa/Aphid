import asyncio
import datetime
import io
import logging
import textwrap
import time
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext import commands

from utils import formatting

log = logging.getLogger(__name__)


class Owner:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    @commands.command(hidden=True)
    @commands.is_owner()
    async def kill(self, ctx):
        await ctx.send('i am die')
        await self.bot.logout()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def ping(self, ctx):
        recv_time = ctx.message.created_at
        message_content = '...'

        task = asyncio.ensure_future(ctx.bot.wait_for(
            'message', timeout=15,
            check=lambda m: (m.author == ctx.bot.user and m.content == message_content)
        ))

        now = datetime.datetime.utcnow()
        sent_message = await ctx.send(message_content)
        await task
        rtt_time = datetime.datetime.utcnow()

        m2m = f'{(sent_message.created_at - recv_time).total_seconds() * 1000:.2f}ms'
        rtt = f'{(rtt_time - now).total_seconds() * 1000:.2f}ms'

        embed = discord.Embed(title='Ping Response', colour=discord.Colour.green())
        embed.add_field(name='M2M', value=m2m)
        embed.add_field(name='RTT', value=rtt)

        await sent_message.edit(content=None, embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, module: str):
        try:
            self.bot.load_extension(module)
        except Exception as ex:
            log.exception(f'Error loading module {module}: {type(ex).__name__} - {ex}')
            await ctx.send(f'Error loading module {module}: {type(ex).__name__} - {ex}')
        else:
            await ctx.send(f'Module `{module}` has been loaded.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, module: str):
        try:
            self.bot.unload_extension(module)
        except Exception as ex:
            log.exception(f'Error unloading module {module}: {type(ex).__name__} - {ex}')
            await ctx.send(f'Error unloading module {module}: {type(ex).__name__} - {ex}')
        else:
            await ctx.send(f'Module `{module}` has been unloaded.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, module: str):
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as ex:
            log.exception(f'Error reloading module {module}: {type(ex).__name__} - {ex}')
            await ctx.send(f'Error reloading module {module}: {type(ex).__name__} - {ex}')
        else:
            await ctx.send(f'Module `{module}` has been reloaded.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reloadall(self, ctx):
        modules = []

        for module in self.bot.initial_extensions:
            modules.append(module)
        modules.remove('cogs.owner')

        for module in modules:
            try:
                self.bot.unload_extension(module)
                self.bot.load_extension(module)
            except Exception as ex:
                log.exception(f'Error reloading module {module}: {type(ex).__name__} - {ex}')
                await ctx.send(f'Error reloading module {module}: {type(ex).__name__} - {ex}')

        await ctx.send('All modules have been reloaded.')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, body: str):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        async with ctx.channel.typing():
            env.update(globals())

            body = formatting.cleanup_code(body)
            stdout = io.StringIO()

            to_compile = f'async def func():\n{textwrap.indent(body, "    ")}'

            try:
                exec(to_compile, env)
            except Exception as e:
                return await ctx.send(formatting.codeblock(f'{e.__class__.__name__}: {e}', lang='py'))

            func = env['func']
            try:
                with redirect_stdout(stdout):
                    ret = await func()
            except Exception as e:
                value = stdout.getvalue()
                await ctx.send(formatting.codeblock(f'{value}{e}', lang='py'))
            else:
                value = stdout.getvalue()

                if ret is None:
                    if value:
                        await ctx.send(formatting.codeblock(value, lang='py'))
                else:
                    self._last_result = ret
                    await ctx.send(formatting.codeblock(f'{value}{ret}', lang='py'))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sql(self, ctx, *, query: str):
        query = formatting.cleanup_code(query)

        is_multistatement = query.count(';') > 1
        if is_multistatement:
            strategy = self.bot.pool.execute
        else:
            strategy = self.bot.pool.fetch

        try:
            start = time.perf_counter()
            results = await strategy(query)
            dt = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(formatting.codeblock(traceback.format_exc(), lang='py'))

        rows = len(results)
        if is_multistatement or rows == 0:
            return await ctx.send(formatting.codeblock(f'{dt:.2f}ms: {results}'))

        headers = list(results[0].keys())
        table = formatting.TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()

        fmt = f'{formatting.codeblock(render)}\n*Returned {formatting.pluralise(row=rows)} in {dt:.2f}ms*'
        if len(fmt) > 2000:
            fp = io.BytesIO(fmt.encode('utf-8'))
            await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
        else:
            await ctx.send(fmt)


def setup(bot):
    bot.add_cog(Owner(bot))
