import discord
from discord.ext import commands
import random
import db
import helpers
import os
from languages import l


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='grant', description=l.text("grant", "description"), hidden=True)
    async def grant_mfw(self, ctx, target : discord.Member|None = None, *values : str):
        ADMINS = await helpers.get_admins()
        if (ctx.author.id not in ADMINS):
            await ctx.send(l.text("grant", "not_admin"))
            return
        if not isinstance(target, discord.Member):
            await ctx.send(l.text("grant", "no_target"))
            return
        if not values:
            await ctx.send(l.text("grant", "no_values"))
            return
        for value in values:
            try:
                mfw_id = await db.fetch_one("SELECT id FROM mfws WHERE name = %s", value)
                await db.execute("INSERT INTO inventory (user_id, mfw_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE quantity = quantity + 1", target.id, mfw_id)
            except: 
                await ctx.send(l.text("grant", "fail", value=value))
        await ctx.send(l.text("grant", "success"))
            


async def setup(bot):
    await bot.add_cog(Admin(bot))