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

    @commands.command(name='clearcache', description="clear in-memory cache", hidden=True)
    async def reset_cache(self, ctx):
        ADMINS = await helpers.get_admins()
        if ctx.author.id not in ADMINS:
            return
        
        db.clear_cache()
        await ctx.send("cache cleared")

    @commands.command(name='setrarity', description="change rarity of a mfw", hidden=True)
    async def assign_rarity(self, ctx, mfw_name : str|None, new_rarity_id : int|None):
        ADMINS = await helpers.get_admins()
        if ctx.author.id not in ADMINS:
            return
        
        if (mfw_name is None):
            await ctx.send("Error: mfw_name is None")
            return
        if (new_rarity_id is None):
            await ctx.send("Error: new_rarity_id is None")
            return

        rarities = await db.fetch_all("SELECT * FROM rarities", cache=True, ttl=9999)
        rarity_map = {r[0]: r[1] for r in rarities}
        rarity_map[0] = "Unused"
        if new_rarity_id not in rarity_map:
            await ctx.send(f"Error: invalid new_rarity_id. Valid ids: {rarity_map}")
            return
        
        row_count = await db.execute("UPDATE mfws SET rarity_id = %s WHERE name = %s", (new_rarity_id, mfw_name))
        if row_count == 0:
            await ctx.send(f"Error: {mfw_name} does not exist")
        else:
            await ctx.send(f"{mfw_name} successfully changed to {rarity_map[new_rarity_id]}!")


async def setup(bot):
    await bot.add_cog(Admin(bot))