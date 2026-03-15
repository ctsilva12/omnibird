import os
import sys
from languages import l
from utils.misc import get_env_var

IN_DOCKER: bool = get_env_var("RUNNING_IN_DOCKER")

async def restart(self, ctx):
    await ctx.send(l.text("restarting"))
    await ctx.bot.close()
    if not IN_DOCKER: os.execv(sys.executable, [sys.executable] + sys.argv)