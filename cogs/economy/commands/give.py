import discord
import utils.services.dbutils as dbutils
import db
import utils.services.discordutils as discordutils
from languages import l

async def give(self, ctx, user: discord.Member|None = None, amount: int|None = None):
    if not isinstance(user, discord.Member):
        await ctx.send(l.text("give", "no_target"))
        return
    if (user.id == ctx.author.id):
        await ctx.send(l.text("give", "giving_money_to_self"))
        return
    
    quantity = await discordutils.sanitize_quantity(ctx, amount)
    if (quantity is None): return
    async with db.transaction() as cur:
        info = await dbutils.get_user_info(ctx.author.id, cur=cur, for_update=True)
        if (quantity > info["coins"]):
            await ctx.send(l.text("give", "insufficient_coins", coins=info["coins"]))
            return
        
        target_info = await dbutils.get_user_info(user.id, cur=cur, for_update=True)
        target_info["coins"] += quantity
        await cur.execute("""
        UPDATE users AS u
        SET coins = CASE 
            WHEN u.id = %s THEN coins - %s
            WHEN u.id = %s THEN coins + %s
            ELSE coins
        END
        WHERE u.id IN (%s, %s);
        """, (ctx.author.id, quantity, user.id, quantity, ctx.author.id, user.id)) 
        await ctx.send(l.text("give", "success", mention=user.mention, coins=target_info["coins"]), allowed_mentions=discord.AllowedMentions.none())