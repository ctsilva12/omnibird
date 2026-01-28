import os
import sys

async def restart(self, ctx):
    await ctx.send("Restarting...")
    await ctx.bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)