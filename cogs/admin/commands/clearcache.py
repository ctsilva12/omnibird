
import db

async def clearcache(self, ctx):
    db.clear_cache()
    await ctx.send("cache cleared")