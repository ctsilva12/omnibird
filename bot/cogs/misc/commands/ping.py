from languages import l
import time

c = "ping"
async def ping(self, ctx):
    start = time.perf_counter_ns()
    message = await ctx.send(l.text(c, "pong"))
    response_time = (time.perf_counter_ns() - start)
    response_time = round((response_time / 1_000_000), 2)
    api_latency = round(ctx.bot.latency * 1000, 2)
    await message.edit(content=l.text(c, "pong_done", response_time=response_time, api_latency=api_latency))
