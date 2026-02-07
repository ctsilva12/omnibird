import discord
from discord.ext import commands
import random
import db
from languages import l
from . import economy
from utils.decorators import no_bots

c = "commands"
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name=l.text(c, "balance"), description=l.text("balance", "description"))
    @no_bots
    async def balance_cmd(self, ctx, user: discord.Member|None = None):
        await economy.balance(self, ctx, user)

    @commands.command(name=l.text(c, "give"), description=l.text("give", "description"))
    @no_bots
    async def give_cmd(self, ctx, user: discord.Member|None = None, amount: int|None = None):
        await economy.give(self, ctx, user, amount)

    @commands.command(name=l.text(c, "leaderboard"), description=l.text("leaderboard", "description"))
    async def show_leaderboard(self, ctx, index: str|int|None):
        await economy.leaderboard(self, ctx, index)
    

async def setup(bot):
    await bot.add_cog(Economy(bot))