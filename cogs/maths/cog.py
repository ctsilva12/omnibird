import discord
from discord.ext import commands
from languages import l
from . import maths

c = "commands"
class Math(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.users_in_math_problems : list[int] = []

    async def cog_unload(self):
        self.users_in_math_problems.clear()
    
    @commands.command(name=l.text(c, "math"), description=l.text("math", "description"))
    async def math_cmd(self, ctx, other_user: discord.Member|None = None):
        await maths.math(self, ctx, other_user)

async def setup(bot):
    await bot.add_cog(Math(bot))