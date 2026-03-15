import random
import discord
from discord.ext import commands
import time
import asyncio

ENTRY_FEE = 250
BASE_REWARD = 1000
PENALTY_RATE = 1/3
MAX_ATTEMPTS = 10
TIMEOUT = 60
#TODO FINISH THIS

def guess_temperature(goal: int, guess: int) -> str:
    diff = abs(goal - guess)
    match diff:
        case n if n == 0: 
            return "victory"
        case n if n <= 5: 
            return "very_warm"
        case n if n <= 15: return "warm"
        case n if n <= 30: return "cold"
        case n if n <= 50: return "very_cold"
        case _: return "impossible"

async def guessnumber(self, ctx: commands.Context):
    goal = random.randint(1, 100)
    await ctx.send(f"{ctx.author.id}, You placed 250 :coin_icon: on the line to get a chance to earn 1000 :coin_icon:! Each wrong attempt will cause your reward to get shrunken by 33% incrementally.")
    def check(m):
        return m.channel == ctx.channel and m.author.id == ctx.author.id
    
    deadline = time.monotonic() + TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        try:
            await self.bot.wait_for("message", check=check, timeout=remaining)
        except asyncio.TimeoutError:
            await ctx.send("loss")

    