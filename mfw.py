from typing import Any, Dict, List
import discord
from discord.ext import commands
import random
import db
import helpers
from datetime import datetime, timedelta
import asyncio
from utils.harvest_messages import HARVEST_MESSAGES
from utils.Pagination import Pagination
from utils.symbols import COIN_ICON
from languages import l

class MfwCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.load_pending_reminders())
        self.MAX_MFWS_PER_PAGE = 150

    async def load_pending_reminders(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        rows = await db.fetch_all("SELECT id, reminder_at, last_harvest_channel FROM users WHERE reminder = TRUE")
        for user_id, reminder_at, last_harvest_channel in rows:
            if (reminder_at is not None):
                print(f"Setting reminder for {await helpers.get_username(self.bot, user_id)} at {reminder_at}")
                asyncio.create_task(self.schedule_harvest_reminder(user_id, reminder_at, last_harvest_channel))

    @commands.command(name='harvest', description=l.text("harvest", "description"))
    async def get_mfw(self, ctx):
        COOLDOWN_IN_SECONDS = 600
        now = datetime.now()
        info = await helpers.get_user_info(ctx.author.id)
        if (info["last_harvest"] is None):
            free = True
            secs_since = 0
        else:
            delta = now - info["last_harvest"]
            secs_since = delta.total_seconds()
            print(secs_since)
            free = secs_since >= COOLDOWN_IN_SECONDS
        if (not free):
            time = helpers.format_duration(COOLDOWN_IN_SECONDS-secs_since)
            await ctx.send(l.text("harvest", "next_free_harvest", time=time, coins=50, yes=l.text("yes"), no=l.text("no")))
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30) 
            except asyncio.TimeoutError:
                await ctx.send(l.text("harvest", "timeout"))
                return

            if msg.content.lower() != l.text("yes")[0]:
                return
            
            if (info["coins"] < 50):
                await ctx.send(l.text("harvest", "insufficient_coins", coins=50))
                return
        # 1 = Normal Harvest
        message = await helpers.open_pack_and_build_message(
            bot=self.bot, user=ctx.author, pack_id=1, amount=1
        )
        if (free): 
            reminder_at = now + timedelta(seconds=COOLDOWN_IN_SECONDS)
            await db.execute("UPDATE users SET last_harvest = %s, reminder_at = %s, last_harvest_channel = %s WHERE id = %s", (now, reminder_at, ctx.channel.id, ctx.author.id))
            if (info["reminder"]): asyncio.create_task(self.schedule_harvest_reminder(ctx.author.id, reminder_at, ctx.channel.id))
        else: await db.execute("UPDATE users SET coins = coins - 50 WHERE id = %s", (ctx.author.id,))

        await ctx.send(message)
       
    
    async def schedule_harvest_reminder(self, user_id, reminder_at, last_harvest_channel):
        delay = (reminder_at - datetime.now()).total_seconds()
        if (delay > 0): await asyncio.sleep(delay)
        reminder = await db.fetch_one("SELECT reminder FROM users WHERE id = %s", (user_id))
        if (reminder is None or reminder[0] == False):
            return
        channel = self.bot.get_channel(last_harvest_channel)
        await db.execute("UPDATE users SET reminder_at = NULL WHERE id = %s", (user_id,))
        if channel:
            await channel.send(l.text("reminder", "ready", mention=f"<@{user_id}>"))

    
    @commands.command(name='reminder', description=l.text("reminder", "description"))
    async def set_reminder(self, ctx, choice : str|None = None):
        info = await helpers.get_user_info(ctx.author.id)
        if (choice != None):
            choice = choice.lower().strip()
            if (choice == l.text("enable")): toggle = True
            elif (choice == l.text("disable")): toggle = False
            else: 
                await ctx.send(l.text("invalid_choice"))
                return
        else:
            toggle = not info["reminder"]
        
        if (toggle != info["reminder"]): await db.execute("UPDATE users SET reminder = %s WHERE id = %s", (toggle, ctx.author.id))
        if toggle == True:
            now = datetime.now()
            if (info["reminder_at"] is not None and info["reminder_at"] > now): 
                asyncio.create_task(self.schedule_harvest_reminder(ctx.author.id, info["reminder_at"], info["last_harvest_channel"]))

        option = l.text("enabled") if toggle == True else l.text("disabled")
        await ctx.send(l.text("reminder", "changed", option=option))

    @commands.command(name='inventory', description=l.text("inventory", "description")) 
    async def inventory(self, ctx, user: discord.Member | None = None):
        target = user or ctx.author

        owned_mfws = await db.fetch_all("""
            SELECT i.mfw_id, i.quantity, m.guild_id, m.name, m.rarity_id
            FROM inventory i
            INNER JOIN mfws m ON i.mfw_id = m.id
            INNER JOIN rarities r on m.rarity_id = r.id
            WHERE i.user_id = %s
            ORDER BY m.rarity_id DESC, i.quantity DESC, m.name ASC
        """, (target.id,))

        if not owned_mfws:
            await ctx.send(l.text("inventory", "no_mfws", name=target.display_name))
            return
        
        all_mfws = await db.fetch_all("SELECT * FROM mfws", cache=True)
        rarities = await db.fetch_all("SELECT * FROM rarities", cache=True, ttl=9999)
        rarity_map = {r[0]: r[1] for r in rarities}
        rarity_map[0] = l.text("unknown").capitalize()

        total_global = 0
        global_totals = {r[0]: 0 for r in rarities}
        for _, _, _, rarity_id, *_ in all_mfws:
            if rarity_id in global_totals:
                global_totals[rarity_id] += 1
                total_global += 1

        
        entries: List[Dict[str, Any]] = []
        total_user = 0
        user_totals = {r[0]: 0 for r in rarities}
        for mfw_id, quantity, guild_id, name, rarity_id in owned_mfws:
            guild = self.bot.get_guild(guild_id) if guild_id else None
            emoji = None
            if guild:
                try:
                    emoji = discord.utils.get(guild.emojis, name=name)
                except Exception:
                    emoji = None
            display = f"{emoji} (x{quantity})" if emoji else f":{name}: (x{quantity})"
            user_totals[rarity_id] += 1
            entries.append({"rarity_id": rarity_id, "text": display})
            total_user += 1

        async def get_inventory_page(page : int):
            total_pages = Pagination.compute_total_pages(len(entries), self.MAX_MFWS_PER_PAGE)
            if total_pages <= 0:
                e = discord.Embed(
                    title=l.text("inventory", "title", name=target.display_name),
                    description=l.text("inventory", "no_mfws", name=target.display_name),
                    color=discord.Color.gold()
                )
                e.set_footer(text=f"0/{total_global} • {l.text("page", page=0, total_pages=0)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
                return e, 0
            
            page = max(1, min(page, total_pages))
            start = (page - 1) * self.MAX_MFWS_PER_PAGE
            end = start + self.MAX_MFWS_PER_PAGE
            page_slice = entries[start:end]

            embed = discord.Embed(
                title=l.text("inventory", "title", name=target.display_name),
                colour=discord.Color.gold()
            )

            grouped_on_page: Dict[int, List[str]] = {}
            for item in page_slice:
                rid = item["rarity_id"] or 0
                grouped_on_page.setdefault(rid, []).append(item["text"])

            for rarity_id in sorted(grouped_on_page.keys(), reverse=True):
                lines = grouped_on_page[rarity_id]
                chunks = helpers.chunk_by_length(lines) or [""]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        name = f"{rarity_map.get(rarity_id, l.text("unknown").capitalize())} ({user_totals.get(rarity_id, 0)}/{global_totals.get(rarity_id, 0)})"
                    else: name = ""
                    embed.add_field(name=name, value=chunk, inline=False)
            embed.set_footer(text=f"{total_user}/{total_global} • {l.text("page", page=page, total_pages=total_pages)}", icon_url="https://cdn.discordapp.com/emojis/1425964337377443840.webp")
            return embed, total_pages

        paginator = Pagination(ctx, get_inventory_page)
        await paginator.navigate()
    @commands.command(name='transfer', description=l.text("transfer", "description"))
    async def transfer_mfw(self, ctx, user: discord.Member | None = None, *values: str):
        if not isinstance(user, discord.Member):
            await ctx.send(l.text("transfer", "no_target"))
            return
        if user.id == ctx.author.id:
            await ctx.send(l.text("transfer", "self_target"))
            return

        if not values:
            await ctx.send(l.text("transfer", "no_values"))
            return

        try:
            mfws_to_transfer, inventory_map, guilds, emojis = await helpers.parse_and_validate_mfws(self.bot, ctx.author, *values)
        except ValueError as e:
            await ctx.send(str(e))
            return

        if not mfws_to_transfer:
            await ctx.send(l.text("transfer", "nothing_to_transfer"))
            return
        
        await helpers.get_user_info(user.id) # Create user if it doesn't exist

        # --- Single batched UPDATE to subtract quantities from giver using CASE ---
        qty_case_sql, params, ids, in_placeholders = helpers.build_qty_case_sql(mfws_to_transfer)

        update_sql = f"""
            UPDATE inventory i
            SET i.quantity = {qty_case_sql}
            WHERE i.user_id = %s AND i.mfw_id IN ({in_placeholders})
        """
        # ORDER: all CASE params..., giver_id, <each id for IN (...)>
        params.append(ctx.author.id)
        params.extend(ids)

        await db.execute(update_sql, tuple(params))

        # --- Single multi-row INSERT to add quantities to recipient (ON DUPLICATE KEY UPDATE) ---
        insert_values = []
        insert_params = []
        for mfw_id, qty, _, _ in mfws_to_transfer:
            insert_values.append("(%s, %s, %s)")
            insert_params.extend((user.id, mfw_id, qty))

        insert_sql = f"""
            INSERT INTO inventory(user_id, mfw_id, quantity)
            VALUES {', '.join(insert_values)} AS new
            ON DUPLICATE KEY UPDATE inventory.quantity = inventory.quantity + new.quantity
        """
        await db.execute(insert_sql, tuple(insert_params))

        await helpers.cleanup_inventory(ctx.author.id)

       
        await ctx.send(l.text("transfer", "success", user_mention=user.mention, emojis=emojis, author_mention=ctx.author.mention))


    @commands.command(name='sell', description='sell mfws for money')
    async def sell_mfw(self, ctx, *values: str):
        rarities = await db.fetch_all("SELECT * FROM rarities", cache=True)
        rarity_map = {
            r[0]: {"rarity": r[1], "price": (r[2] // 2) if r[2] is not None else None}
            for r in rarities
        }

        if not values:
            message_array = [""]
            for info in rarity_map.values():
                if info["price"]:
                    message_array.append(f"{info['rarity']}: {info['price']} {COIN_ICON}")
            await ctx.send(
                f"{l.text("sell", "info")}\n"
                + "\n".join(message_array)
            )
            return

        try:
            parsed_items, inventory_map, guilds, emojis = await helpers.parse_and_validate_mfws(self.bot, ctx.author, *values)
        except ValueError as e:
            await ctx.send(str(e))
            return

        if not parsed_items:
            await ctx.send(l.text("transfer", "no_values"))
            return

        # Build the sell list and compute amounts
        mfws_to_sell = []  # (mfw_id, qty, amount)
        total_sell_value = 0
        sell_emojis = []

        for mfw_id, qty, guild_id, mfw_name in parsed_items:
            # rarity_id is available in inventory_map
            row = inventory_map[mfw_name]
            _, _, _, rarity_id, _ = row
            price = rarity_map.get(rarity_id, {}).get("price", 0)
            amount = price * qty
            total_sell_value += amount
            mfws_to_sell.append((mfw_id, qty, amount))

            guild = guilds.get(guild_id)
            emoji = discord.utils.get(guild.emojis, name=mfw_name) if guild else mfw_name
            sell_emojis.append(f"{qty if qty > 1 else 'a'} {emoji}")

        if not mfws_to_sell:
            await ctx.send("Nothing to sell.")
            return

        # --- Build single UPDATE that updates quantities via CASE and adds total coins once ---
        qty_case_sql, params, ids, in_placeholders = helpers.build_qty_case_sql(mfws_to_sell)

        # ORDER REQUIRED BY QUERY: [CASE params...], total_sell_value, user_id, <each id for IN (...)>
        params.append(total_sell_value)   # for u.coins = u.coins + %s
        params.append(ctx.author.id)      # for WHERE i.user_id = %s
        params.extend(ids)

        update_sql = f"""
            UPDATE inventory i
            JOIN users u ON u.id = i.user_id
            SET
                i.quantity = {qty_case_sql},
                u.coins = u.coins + %s
            WHERE i.user_id = %s AND i.mfw_id IN ({in_placeholders})
        """

        await db.execute(update_sql, tuple(params))

        await helpers.cleanup_inventory(ctx.author.id)

        # Fetch the updated coins to report back (precise value)
        new_coins_row = await db.fetch_one("SELECT coins FROM users WHERE id = %s", (ctx.author.id,))
        new_coins = new_coins_row[0] if new_coins_row else None

        await ctx.send(l.text("sell", "success", mention=ctx.author.mention, new_coins=new_coins, emojis=emojis))
        
    @commands.command(name='selldupes', description=l.text("selldupes", "description"))
    async def sell_dupes(self, ctx, *values: str):
        async with db.transaction() as cur:
            before_coins = (await helpers.get_user_info(ctx.author.id, cur=cur, for_update=True))["coins"]
            mfws_to_exclude = []
            if values:
                try:
                    mfws_to_exclude, _, _, _ = await helpers.parse_and_validate_mfws(self.bot, ctx.author, *values)
                    mfws_to_exclude = [int(mfw[0]) for mfw in mfws_to_exclude]
                except ValueError as e:
                    await ctx.send(e)
                    return
            if mfws_to_exclude:
                placeholders = ", ".join(["%s"] * len(mfws_to_exclude))
                inner_in = f"AND i.mfw_id NOT IN ({placeholders})"
            else:
                inner_in = ""
                placeholders = ""

            update_sql = f"""
            UPDATE users u
            JOIN (
                SELECT i.user_id, COALESCE(SUM((i.quantity - 1) * ROUND(r.price / 2)), 0) AS earned
                FROM inventory i
                JOIN mfws m ON i.mfw_id = m.id
                JOIN rarities r ON r.id = m.rarity_id
                WHERE i.quantity > 1 AND i.user_id = %s
                {inner_in}
                GROUP BY i.user_id
            ) sub ON u.id = sub.user_id
            SET u.coins = u.coins + sub.earned
            WHERE u.id = %s
            """
            # Parameter order: inner i.user_id, then excluded ids (if any), then outer u.id
            params = [ctx.author.id] + mfws_to_exclude + [ctx.author.id]

            await cur.execute(update_sql, tuple(params))

            # update inventory quantities
            if mfws_to_exclude:
                delete_in = f"AND mfw_id NOT IN ({placeholders})"
                params2 = [ctx.author.id] + mfws_to_exclude
            else:
                delete_in = ""
                params2 = [ctx.author.id]

            delete_sql = f"""
            UPDATE inventory
            SET quantity = 1
            WHERE user_id = %s
            {delete_in}
            """
            await cur.execute(delete_sql, tuple(params2))

            new = await helpers.get_user_info(ctx.author.id, cur=cur)
            new_coins = new["coins"] if new and new.get("coins") is not None else 0
            earned = int(new_coins) - int(before_coins)

            if earned != 0:
                await ctx.send(l.text("selldupes", "success", new_coins=new_coins, earned=earned))
            else:
                await ctx.send(l.text("selldupes", "no_dupes"))
"""
    @commands.command(name='trade', description=l.text("trade", "description"))
    async def trade_mfws(self, ctx, user: discord.Member | None = None, *values: str):
        if not isinstance(user, discord.Member):
            await ctx.send(l.text("transfer", "no_target"))
            return
        if user.id == ctx.author.id:
            await ctx.send(l.text("transfer", "self_target"))
            return

        if not values:
            await ctx.send(l.text("transfer", "no_values"))
            return
"""

async def setup(bot):
    await bot.add_cog(MfwCommands(bot))