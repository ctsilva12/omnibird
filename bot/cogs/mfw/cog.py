import discord
from discord.ext import commands
import db
from datetime import datetime
import asyncio
from languages import l
from functools import partial
from . import mfw
import utils.services.discord.discordutils as discordutils
from utils.services.discord.decorators import no_bots

c = "commands"
class Mfw(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_reminders: dict[int, asyncio.Task] = {}
        self.loader_task = self.bot.loop.create_task(self.load_pending_reminders())
        self.MAX_MFWS_PER_PAGE = 150

    async def schedule_harvest_reminder(self, user_id, reminder_at, last_harvest_channel):
        delay = (reminder_at - datetime.now()).total_seconds()
        if (delay > 0): await asyncio.sleep(delay)
        await db.execute("UPDATE users SET reminder_at = NULL WHERE id = %s", (user_id,))
        channel = self.bot.get_channel(last_harvest_channel)
        if channel:
            await channel.send(l.text("reminder", "ready", mention=f"<@{user_id}>"))

    async def load_pending_reminders(self):
        await self.bot.wait_until_ready()
        rows = await db.fetch_all("SELECT id, reminder_at, last_harvest_channel FROM users WHERE reminder = TRUE AND reminder_at IS NOT NULL")
        for user_id, reminder_at, last_harvest_channel in rows:
            print(f"Setting reminder for {await discordutils.get_username(self.bot, user_id)} at {reminder_at}")
            task = asyncio.create_task(self.schedule_harvest_reminder(user_id, reminder_at, last_harvest_channel))
            task.add_done_callback(partial(lambda uid, t: self.pending_reminders.pop(uid, None), user_id))
            self.pending_reminders[user_id] = task

    async def cog_unload(self):
        if self.loader_task and not self.loader_task.done():
            self.loader_task.cancel()
        for task in list(self.pending_reminders.values()):
            if not task.done():
                task.cancel()
        self.pending_reminders.clear()

    @commands.hybrid_command(name=l.text(c, "harvest"), description=l.text("harvest", "description"))
    async def harvest_cmd(self, ctx):
        await mfw.harvest(self, ctx)
       
    d = "reminder"
    @commands.hybrid_command(name=l.text(c, d), description=l.text(d, "description"))
    @discord.app_commands.describe(choice=l.text(d, "param_choice"))
    async def reminder_cmd(self, ctx, choice : str|None = None):
        await mfw.reminder(self, ctx, choice)

    @commands.command(name=l.text(c, "inventory"), description=l.text("inventory", "description")) 
    @no_bots
    async def inventory_cmd(self, ctx, user: discord.Member | None = None, requested_page : int|None = None):
        await mfw.inventory(self, ctx, user, requested_page)

    @commands.command(name=l.text(c, "almanac"), description=l.text("almanac", "description")) 
    @no_bots
    async def almanac_cmd(self, ctx, user: discord.Member | None = None, requested_page : int|str|None = None):
        await mfw.almanac(self, ctx, user, requested_page)

    @commands.command(name=l.text(c, "transfer"), description=l.text("transfer", "description"))
    @no_bots
    async def transfer_cmd(self, ctx, user: discord.Member | None = None, *values: str):
        await mfw.transfer(self, ctx, user, *values)

    d = "sell"
    @commands.hybrid_command(name=l.text(c, d), description=l.text(d, "description"))
    @discord.app_commands.describe(values=l.text(d, "param_values"))
    async def sell_cmd(self, ctx, *, values: str|None = None):
        vals = values.split() if values else []
        await mfw.sell(self, ctx, *vals)
        
    @commands.command(name=l.text(c, "selldupes"), description=l.text("selldupes", "description"))
    async def selldupes_cmd(self, ctx, *, exclude: str|None = None):
        vals = exclude.split() if exclude else []
        await mfw.selldupes(self, ctx, *vals)

    d = "trade"
    @commands.hybrid_command(name=l.text(c, d), description=l.text(d, "description"))
    @discord.app_commands.describe(user=l.text(d, "param_user"))
    @no_bots
    async def trade_cmd(self, ctx, user: discord.User|None = None):
        await mfw.trade(self, ctx, user)

    d = "check"
    @commands.hybrid_command(
    name=l.text(c, d),
    description=l.text(d, "description")
    )
    @discord.app_commands.describe(
        user=l.text(d, "param_user"),
        values=l.text(d, "param_values")
    )
    @no_bots
    async def check_cmd(self, ctx, user: discord.User | None = None, *, values: str):
        vals = values.split() if values else []
        await mfw.check(self, ctx, user, *vals)
    

async def setup(bot):
    await bot.add_cog(Mfw(bot))