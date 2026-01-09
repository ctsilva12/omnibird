import os
import asyncio
import importlib
import importlib.util
import traceback
from typing import Dict, Optional
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import responses
import db
from languages import l, locale_reloader
import random
from helpers import get_admins

load_dotenv()
COGS = ["mfw", "economy", "gambling", "admin", "shop", "maths"]
GUILDS_FOR_EMOJIS : list[int] = [1457482751723700444]
BOT_TOKEN = "BOT_TOKEN"
PROD = os.getenv("PROD", "0").lower() in ("1", "true", "yes")


class HotReloader:
    """
    Lightweight file-watcher that polls modification times and reloads changed extensions.
    Works without external deps (no watchdog). Reasonable for development.
    """
    def __init__(self, bot: commands.Bot, extensions: list[str], poll_interval: float = 2.0):
        self.bot = bot
        self.extensions = extensions
        self.poll_interval = poll_interval
        self._mtimes: Dict[str, Optional[float]] = {}
        for ext in extensions:
            spec = importlib.util.find_spec(ext)
            path = spec.origin if spec and spec.origin else (ext.replace(".", os.sep) + ".py")
            try:
                self._mtimes[ext] = os.path.getmtime(path)
            except OSError:
                self._mtimes[ext] = None
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    async def _loop(self):
        while not self._stopping:
            await asyncio.sleep(self.poll_interval)
            for ext in list(self.extensions):
                spec = importlib.util.find_spec(ext)
                path = spec.origin if spec and spec.origin else (ext.replace(".", os.sep) + ".py")
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    mtime = None
                prev = self._mtimes.get(ext)
                if prev is None and mtime is not None:
                    # now exists -> treat as change (load if not loaded)
                    await self._reload_extension_safe(ext)
                    self._mtimes[ext] = mtime
                elif prev is not None and mtime is not None and mtime > prev:
                    await self._reload_extension_safe(ext)
                    self._mtimes[ext] = mtime
                # if file deleted (mtime is None) we ignore
        # loop ends

    async def _reload_extension_safe(self, ext: str):
        try:
            if ext in self.bot.extensions:
                await self.bot.reload_extension(ext)
                print(f"[hot-reload] reloaded extension: {ext}")
            else:
                await self.bot.load_extension(ext)
                print(f"[hot-reload] loaded new extension: {ext}")
        except Exception:
            print(f"[hot-reload] failed to reload {ext}")
            traceback.print_exc()

    def start(self):
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop())

    def stop(self):
        self._stopping = True
        if self._task:
            self._task.cancel()


class Omnibird(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="o!", intents=intents)
        self.hot_reloader: Optional[HotReloader] = None
        self._ready_once = False

    async def setup_hook(self):
        for cog in COGS:
            try:
                await self.load_extension(cog)
            except Exception:
                print(f"Failed loading {cog}")
                traceback.print_exc()

        if not PROD:
            self.hot_reloader = HotReloader(self, COGS)
            self.hot_reloader.start()
            locale_reloader.start()
            print("PROD=false, hotreloader enabled")

    async def on_ready(self):
        if not self._ready_once:
            self._ready_once = True
            print(f"{self.user} is now online! (on_ready)")
            for guild_id in GUILDS_FOR_EMOJIS:
                guild = self.get_guild(guild_id)
                if guild:
                    try:
                        for emoji in guild.emojis:
                            await db.execute(
                                "INSERT INTO mfws (id, name, rarity_id, guild_id, is_animated) "
                                "VALUES (%s, %s, %s, %s, %s) AS new ON DUPLICATE KEY UPDATE name = new.name",
                                (emoji.id, emoji.name, 0, guild_id, getattr(emoji, "animated", False))
                            )
                    except Exception:
                        print("Failed to sync emojis")
                        traceback.print_exc()

    async def send_message(self, message, user_message, is_private=False):
        try:
            response = responses.get_response(user_message)
            if response is None:
                return
            if is_private:
                await message.author.send(response)
            else:
                await message.channel.send(response)
        except Exception:
            print("send_message failed")
            traceback.print_exc()

    async def close(self):
        if self.hot_reloader:
            self.hot_reloader.stop()
        await super().close()


bot = Omnibird()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    username = str(message.author)
    channel = str(message.channel)
    user_message = str(message.content)

    print(f'{username} said: "{user_message}" ({channel})')

    await bot.process_commands(message)
    await bot.send_message(message, user_message, False)


@bot.command(name="quote", description=l.text("quote", "description"))
async def get_random_quote(ctx):
    quote = random.choice(responses.quotes)
    await ctx.send(quote)
    print(f"The following message was successfully sent: {quote}")


# ADMIN ONLY
@bot.command(name="reload", hidden=True)
async def cmd_reload(ctx, *, extension: str|None = None):
    ADMINS = await get_admins()
    if ctx.author.id not in ADMINS:
        return
    targets = COGS if extension is None else [extension]
    reloaded = []
    failed = []
    reload_locale = True if extension is None else False
    for ext in targets:
        if ext == "locale":
            reload_locale = True
            continue
        try:
            if ext in bot.extensions:
                await bot.reload_extension(ext)
            else:
                await bot.load_extension(ext)
            reloaded.append(ext)
        except Exception:
            failed.append(ext)
            traceback.print_exc()
    
    if reload_locale:
        try:
            l.load_all()
            reloaded.append("locale")
        except Exception:
            failed.append("locale")
            traceback.print_exc()
    await ctx.author.send(f"reloaded: {reloaded}, failed: {failed}")


def run_discord_bot():
    TOKEN = os.getenv(BOT_TOKEN)
    if TOKEN is None:
        raise ValueError("Token not set in environment variable BOT_TOKEN")
    bot.run(TOKEN)


if __name__ == "__main__":
    run_discord_bot()