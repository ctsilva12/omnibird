import db
import utils.services.discord.discordutils as discordutils
import discord
import utils.services.dbutils as dbutils
from languages import l
from aiomysql import Cursor

async def sell(self, ctx, *values: str):
    if not values:
        rarities = await db.fetch_all("SELECT * FROM rarities", cache=True)
        rarity_map = {
            r[0]: {"rarity": r[1], "price": (r[2] // 2) if r[2] is not None else None}
            for r in rarities
        }
        message_array = [""]
        for info in rarity_map.values():
            if info["price"] is not None:
                message_array.append(f"{info['rarity']}: {info['price']} {l.text('_symbols', 'coin_icon')}")
        await ctx.send(
            f"{l.text('sell', 'info')}\n"
            + "\n".join(message_array)
        )
        return

    # Single transaction for the whole operation
    async with db.transaction() as cur:
        try:
            # parse & validate input (this may raise ValueError which we handle)
            mfws, inventory_map, guilds, emojis = await discordutils.parse_and_validate_mfws(
                self.bot, ctx.author, *values, cur=cur
            )
        except ValueError as e:
            await ctx.send(str(e))
            return

        if not mfws:
            await ctx.send(l.text("transfer", "no_values"))
            return

        # Build small derived table (vals) with (mfw_id, qty_to_sell)
        values_select = " UNION ALL ".join(["SELECT %s AS mfw_id, %s AS qty_to_sell"] * len(mfws))
        vals_params = []
        for mfw_id, qty, *_ in mfws:
            vals_params.extend([mfw_id, qty])

        sql_inventory = f"""
            UPDATE inventory i
            JOIN (
                {values_select}
            ) AS vals ON i.mfw_id = vals.mfw_id
            SET i.quantity = GREATEST(i.quantity - vals.qty_to_sell, 0)
            WHERE i.user_id = %s
        """
        inv_params = vals_params + [ctx.author.id]
        await cur.execute(sql_inventory, tuple(inv_params))

        update_sql = f"""
            UPDATE users u
            JOIN (
                SELECT i.user_id,
                       COALESCE(SUM(vals.qty_to_sell * ROUND(r.price / 2)), 0) AS earned
                FROM inventory i
                JOIN (
                    {values_select}
                ) vals ON vals.mfw_id = i.mfw_id
                JOIN mfws m ON m.id = i.mfw_id
                JOIN rarities r ON r.id = m.rarity_id
                WHERE i.user_id = %s
                GROUP BY i.user_id
            ) sub ON u.id = sub.user_id
            SET u.coins = u.coins + sub.earned
            WHERE u.id = %s
        """
        upd_params = vals_params + [ctx.author.id, ctx.author.id]
        await cur.execute(update_sql, tuple(upd_params))
        await dbutils.cleanup_inventory(ctx.author.id, cur=cur)
        await cur.execute("SELECT coins FROM users WHERE id = %s", (ctx.author.id,))
        new_coins_row = await cur.fetchone()
        new_coins = new_coins_row[0] if new_coins_row else 0
        await ctx.send(l.text("sell", "success", mention=ctx.author.mention, new_coins=new_coins, emojis=emojis))
