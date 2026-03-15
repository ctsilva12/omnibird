
from utils.services.MemoryCache import db_cache

async def clearcache(self, ctx):
    await db_cache.clear()
    await ctx.send("cache cleared")