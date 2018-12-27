import functools
import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


def has_any_role(member: discord.Member, *names):
    getter = functools.partial(discord.utils.get, member.roles)
    return any(getter(name=name) is not None for name in names)


def not_role(name):
    def predicate(ctx):
        if not isinstance(ctx.channel, discord.abc.GuildChannel):
            return False

        role = discord.utils.get(ctx.author.roles, name=name)
        return role is None

    return commands.check(predicate)


def is_any_channel(*names):
    def predicate(ctx):
        if not isinstance(ctx.channel, discord.abc.GuildChannel):
            return False

        return ctx.channel.name in names

    return commands.check(predicate)


def pm_only():
    """A :func:`.check` that indicates this command must only be used in a
    guild context only. Basically, no private messages are allowed when
    using the command.
    This check raises a special exception, :exc:`.NoPrivateMessage`
    that is derived from :exc:`.CheckFailure`.
    """

    def predicate(ctx):
        return ctx.guild is not None

    return commands.check(predicate)
