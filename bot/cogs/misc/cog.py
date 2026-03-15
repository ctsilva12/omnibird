import discord
from discord.ext import commands
from languages import l
from . import misc

c = "commands"
class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    d = "ping"
    @commands.hybrid_command(name=l.text(c, d), description=l.text(d, "description"))
    async def ping(self, ctx):
        await misc.ping(self, ctx)

    d = "jumbo"
    @commands.hybrid_command(name=l.text(c, d), description=l.text(d, "description"))
    @discord.app_commands.describe(mfw=l.text(d, "param_mfw"))
    async def jumbo_cmd(self, ctx, mfw: str):
        await misc.jumbo(self, ctx, mfw)



async def setup(bot):
    await bot.add_cog(Misc(bot))