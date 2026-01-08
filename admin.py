import discord
from discord.ext import commands
import random
import db
import helpers
import os
from languages import text
# to move this to database eventually
ADMINS = [os.getenv("ADMIN")]

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='grant', description=text("grant", "description"))
    async def grant_mfw(self, ctx, target : discord.Member|None = None, *values : str):
        if (ctx.author.id not in ADMINS):
            await ctx.send(text("grant", "not_admin"))
            return
        if not isinstance(target, discord.Member):
            await ctx.send(text("grant", "no_target"))
            return
        if not values:
            await ctx.send(text("grant", "no_values"))
            return
        for value in values:
            try:
                mfw_id = await db.fetch_one("SELECT id FROM mfws WHERE name = %s", value)
                await db.execute("INSERT INTO inventory (user_id, mfw_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE quantity = quantity + 1", target.id, mfw_id)
            except: 
                await ctx.send(text("grant", "fail", value=value))
        await ctx.send(text("grant", "success"))
            


async def setup(bot):
    await bot.add_cog(Admin(bot))