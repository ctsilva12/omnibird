import os
import sys
from languages import l

async def restart(self, ctx):
    await ctx.send(l.text("restarting"))
    await ctx.bot.close()
    os.execv(sys.executable, [sys.executable] + sys.argv)