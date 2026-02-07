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
from utils.services.discordutils import sync_emojis
from utils.services.dbutils import get_admins
from utils.decorators import is_admin
from pathlib import Path
from utils.misc import discover_cogs

load_dotenv()
BOT_TOKEN = "BOT_TOKEN"
PROD = os.getenv("PROD", "0").lower() in ("1", "true", "yes")


class HotReloader:
    def __init__(self, bot: commands.Bot, extensions: list[str], poll_interval: float = 2.0):
        self.bot = bot
        self.extensions = extensions
        self.poll_interval = poll_interval
        self.cog_index = discover_cogs()
        self._mtimes: Dict[str, Optional[float]] = {}
        for ext in self.cog_index.values():
            module_path = Path(ext.replace(".", os.sep) + ".py")
            path = module_path if module_path.exists() else None
            try:
                if path is not None: self._mtimes[ext] = os.path.getmtime(path)
                else: continue
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
                    await self._reload_extension_safe(ext)
                    self._mtimes[ext] = mtime
                elif prev is not None and mtime is not None and mtime > prev:
                    await self._reload_extension_safe(ext)
                    self._mtimes[ext] = mtime

    async def _reload_extension_safe(self, ext: str):
        try:
            if ext in self.bot.extensions:
                await self.bot.reload_extension(f"cogs.{ext}")
                print(f"[hot-reload] reloaded extension: {ext}")
            else:
                await self.bot.load_extension(f"cogs.{ext}")
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
        self.cog_index: dict[str, str] = discover_cogs()

    async def setup_hook(self):
        for ext in self.cog_index.values():
            try:
                await self.load_extension(ext)
            except Exception:
                print(f"Failed loading {ext}")
                traceback.print_exc()

        if not PROD:
            self.hot_reloader = HotReloader(self, list(self.cog_index.values()))
            self.hot_reloader.start()
            locale_reloader.start()
            print("PROD=false, hotreloader enabled")

    async def on_ready(self):
        if not self._ready_once:
            self._ready_once = True
            print(f"{self.user} is now online! (on_ready)")
            await sync_emojis(bot)

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

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply(l.text("command_doesnt_exist"))

@bot.command(name="quote", description=l.text("quote", "description"))
async def get_random_quote(ctx):
    quote = random.choice(responses.quotes)
    await ctx.send(quote)
    print(f"The following message was successfully sent: {quote}")

@bot.command(name="reload", hidden=True)
@is_admin()
async def cmd_reload(ctx, *, extension: str | None = None):
    reload_map = {}
    cog_index = getattr(bot, "cog_index", None)
    if cog_index is None:
        return
    for folder, ext_path in cog_index.items():
        reload_map[folder] = ext_path

    reload_map["locale"] = lambda: l.load_all()
    reload_map["emojis"] = lambda: sync_emojis(bot)

    if extension is None:
        targets = list(reload_map.keys())
    else:
        name = extension.strip()
        if name in reload_map:
            targets = [name]
        elif name.startswith("cogs.") or name.endswith(".cog"):
            matched_key = next((k for k, v in reload_map.items() if v == name), None)
            targets = [matched_key or name]
        else:
            targets = [name]

    reloaded = []
    failed = []

    for key in targets:
        if key in reload_map:
            item = reload_map[key]
            display = key
        elif isinstance(key, str) and (key.startswith("cogs.") or key.endswith(".cog")):
            item = key
            display = key
        else:
            failed.append(key)
            continue

        try:
            if isinstance(item, str):
                ext_path = item
                if ext_path in bot.extensions:
                    await bot.reload_extension(ext_path)
                else:
                    await bot.load_extension(ext_path)
                reloaded.append(display)
            else:
                result = item()
                if asyncio.iscoroutine(result):
                    await result
                reloaded.append(display)
        except Exception:
            failed.append(display)
            traceback.print_exc()

    await ctx.send(f"reloaded: {reloaded}\nfailed: {failed}")


def run_discord_bot():
    TOKEN = os.getenv(BOT_TOKEN)
    if TOKEN is None:
        raise ValueError("Token not set in environment variable BOT_TOKEN")
    bot.run(TOKEN)


if __name__ == "__main__":
    run_discord_bot()