import db
import utils.services.discordutils as discordutils

async def addguild(self, ctx, guild_id : int|None = None):
    if guild_id is None: 
        if ctx.guild is not None: 
            guild_id = ctx.guild.id
        else:
            await ctx.send("no guild")
            return
    guild = self.bot.get_guild(guild_id)
    if not guild:
        await ctx.send("guild doesn't exist")
        return
    try:
        await db.execute("INSERT INTO guilds(id, name) VALUES(%s, %s) AS new ON DUPLICATE KEY UPDATE id = new.id", (guild.id, f"{guild.name}cord"))
        await ctx.send(f"Welcome to the club, {guild.name}cord!")
        await discordutils.sync_emojis(self.bot)
    except Exception as e:
        await ctx.send("Something went wrong!")
        print(e)