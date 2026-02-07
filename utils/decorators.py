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

def max_bet(max_amount: int):
    async def predicate(ctx: commands.Context):
        bet = ctx.kwargs.get("bet")
        print(ctx.kwargs)

        if bet is None:
            await ctx.send(l.text("quantity", "none"))
            return False

        if bet > max_amount:
            await ctx.send(l.text("quantity", "none"))
            return False

        return True

    return commands.check(predicate)