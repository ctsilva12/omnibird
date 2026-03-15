import db
import discord
import utils.services.dbutils as dbutils
from languages import l

async def balance(self, ctx, user: discord.Member|None = None):
    target = user or ctx.author
    async with db.transaction() as cur:
        info = await dbutils.get_user_info(target.id, cur=cur)
        coins = info["coins"]
        await ctx.send(l.text("balance", "message", mention=target.mention, coins=coins))