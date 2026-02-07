import utils.services.packs as packs
import utils.services.dbutils as dbutils
import utils.pure.formatting as formatting
from datetime import datetime, timedelta
import db
from functools import partial
import asyncio
from languages import l

async def harvest(self, ctx):
        COOLDOWN_IN_SECONDS = 600
        now = datetime.now()
        reminder_at = now + timedelta(seconds=COOLDOWN_IN_SECONDS)
        async with db.transaction() as cur:
            info = await dbutils.get_user_info(ctx.author.id, cur=cur, for_update=True)
            #TODO rarity -1 accelerates harvest speed by 25%
            """
            cur.execute("SELECT i.mfw_id, COUNT(*) from inventory" \
            "INNER JOIN mfws m on i.mfw_id = m.mfw_id" \
            "INNER JOIN rarities r ON m.rarity_id = r.id" \
            "WHERE m.rarity_id = -1" \
            "GROUP BY i.mfw_id")
            """
            # 1 = row found
            await cur.execute("""UPDATE users
            SET last_harvest = %s, reminder_at = %s, last_harvest_channel = %s
            WHERE id = %s
            AND (
                last_harvest IS NULL OR
                TIMESTAMPDIFF(SECOND, last_harvest, %s) >= %s)
            """, (now, reminder_at, ctx.channel.id, ctx.author.id, now, COOLDOWN_IN_SECONDS))
            free = cur.rowcount == 1

            if (free):
                if (info["reminder"]):
                    task = asyncio.create_task(self.schedule_harvest_reminder(ctx.author.id, reminder_at, ctx.channel.id))
                    self.pending_reminders[ctx.author.id] = task
                    task.add_done_callback(partial(lambda uid, t: self.pending_reminders.pop(uid, None), ctx.author.id))
            else:
                row = await db.fetch_one("SELECT price FROM shop WHERE locale_id = %s", ("harvest",), cache=True)
                PRICE = row[0] if row is not None else 100
                secs_since = (now - info["last_harvest"]).total_seconds()
                remaining = max(0, COOLDOWN_IN_SECONDS - int(secs_since))
                time = formatting.format_duration(remaining)
                await ctx.send(l.text("harvest", "next_free_harvest", time=time, coins=PRICE, yes=l.text("yes"), no=l.text("no")))
                
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=30) 
                except asyncio.TimeoutError:
                    await ctx.send(l.text("harvest", "timeout"))
                    return

                if msg.content.lower() not in (l.text("yes")[0], l.text("yes")):
                    return
                
                if (info["coins"] < PRICE):
                    await ctx.send(l.text("harvest", "insufficient_coins", coins=PRICE))
                    return
                
                await cur.execute("UPDATE users SET coins = coins - %s WHERE id = %s", (PRICE, ctx.author.id,))
                
            # 1 = Normal Harvest
            message = await packs.open_pack(
                bot=self.bot, user=ctx.author, pack_id=1, amount=1, cur=cur
            )
            await ctx.send(message)