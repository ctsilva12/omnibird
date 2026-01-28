import discord
from discord.ext import commands
from . import admin
from languages import l
from utils.decorators import is_admin

# todo: move all this text to locale
c = "admin"
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='grant', description=l.text("grant", "description"), hidden=True)
    @is_admin()
    async def grant(self, ctx, target : discord.Member|None = None, *values : str):
        await admin.grant(self, ctx, target, *values)

    @commands.command(name='restart', hidden=True)
    @is_admin()
    async def restart_cmd(self, ctx):
        await admin.restart(self, ctx)

    @commands.command(name='clearcache', description="clear in-memory cache", hidden=True)
    @is_admin()
    async def clearcache_cmd(self, ctx):
        await admin.clearcache(self, ctx)
        
    @commands.command(name='setrarity', description="change rarity of a mfw", hidden=True)
    @is_admin()
    async def setrarity_cmd(self, ctx, mfw_name : str|None, new_rarity_id : int|None):
        await admin.setrarity(self, ctx, mfw_name, new_rarity_id)

    @commands.command(name='addguild', description="add a new guild for emojis", hidden=True)
    @is_admin()
    async def addguild_cmd(self, ctx, guild_id : int|None = None):
        await admin.addguild(self, ctx, guild_id)

async def setup(bot):
    await bot.add_cog(Admin(bot))