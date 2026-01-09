import discord
from discord.ext import commands
import random
import db
import helpers
from utils.symbols import COIN_ICON
from languages import l

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='balance', description=l.text("balance", "description"))
    async def show_balance(self, ctx, user: discord.Member|None = None):
        target = user or ctx.author
        info = await helpers.get_user_info(target.id)
        coins = info["coins"]
        await ctx.send(l.text("balance", "message", mention=target.mention, coins=coins), allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name='give', description=l.text("give", "description"))
    async def give_cash(self, ctx, user: discord.Member|None = None, amount: int|None = None):
        if not isinstance(user, discord.Member):
            await ctx.send(l.text("give", "no_target"))
            return
        if (user.id == ctx.author.id):
            await ctx.send(l.text("give", "giving_money_to_self"))
            return
        
        quantity = await helpers.sanitize_quantity(ctx, amount)
        if (quantity is None): return
        async with db.transaction() as cur:
            info = await helpers.get_user_info(ctx.author.id, cur=cur, for_update=True)
            if (quantity > info["coins"]):
                await ctx.send(l.text("give", "insufficient_coins", coins=info["coins"]))
                return
            
            target_info = await helpers.get_user_info(user.id, cur=cur, for_update=True)
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

    @commands.command(name='leaderboard', description=l.text("leaderboard", "description"))
    async def show_leaderboard(self, ctx):
        leaderboard = await db.fetch_all("SELECT id, coins FROM users ORDER BY coins DESC LIMIT 10")
        description = ""
        for index, row in enumerate(leaderboard, start=1):
            user_id = row[0]
            coins = row[1]
            description += f"**{index}.** <@{user_id}> - {coins} {COIN_ICON}\n"

        embed = discord.Embed(
            title=l.text("leaderboard", "title"),
            description=description,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))