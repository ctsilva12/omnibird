import discord
from languages import l
import db

async def leaderboard(self, ctx):
        leaderboard = await db.fetch_all("SELECT id, coins FROM users ORDER BY coins DESC LIMIT 10")
        description = ""
        for index, row in enumerate(leaderboard, start=1):
            user_id = row[0]
            coins = row[1]
            description += l.text("leaderboard", "line", index=index, user_id=user_id, coins=coins)

        embed = discord.Embed(
            title=l.text("leaderboard", "title"),
            description=description,
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)