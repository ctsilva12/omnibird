from discord.ext import commands
from utils.services.dbutils import get_admins
import functools
from languages import l

def is_admin():
    async def predicate(ctx: commands.Context) -> bool:
        admin_ids = await get_admins()
        return ctx.author.id in admin_ids
    return commands.check(predicate)

def no_bots(func):
    @functools.wraps(func)
    async def wrapper(self, ctx, other_user=None, *args, **kwargs):
        if other_user and other_user.bot:
            await ctx.send(l.text("bot_not_allowed"))
            return
        return await func(self, ctx, other_user, *args, **kwargs)
    return wrapper