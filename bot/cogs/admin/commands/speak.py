
import discord
from discord.ext import commands
import asyncio

async def speak(self, ctx: commands.Context, channel_id, message: str):
    try:
        # Link form
        if isinstance(channel_id, str) and '/' in channel_id:
            channel_id = channel_id.rsplit('/', 1)[-1]
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        channel_id = ctx.channel.id

    channel: discord.abc.Messageable = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)

    if channel is None:
        await ctx.send("Something went wrong!")
        return
    
    files = [await att.to_file() for att in ctx.message.attachments]
    if message or files: 
        await channel.send(content=message, files=files)
    
    if ctx.message: 
        if ctx.message.guild is not None:
            has_perm = ctx.message.channel.permissions_for(ctx.message.guild.me).manage_messages
            if has_perm:
                try: await ctx.message.delete()
                except discord.HTTPException: pass

    