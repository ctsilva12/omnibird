
import discord
import utils.services.dbutils as dbutils
import db
from languages import l

async def setadmin(self, ctx, target: discord.User|None = None):
    if target is None:
        target = ctx.author
    async with db.transaction() as cur:
        new_status: bool = not ((await dbutils.get_user_info(ctx.author.id, cur=cur, for_update=True))["is_admin"])
        await db.execute("UPDATE users SET is_admin = %s WHERE id = %s", (new_status, target.id), cur=cur) # type: ignore
        message = "is_now_an_admin" if new_status else "is_no_longer_an_admin"
        await ctx.send(l.text("setadmin", message))