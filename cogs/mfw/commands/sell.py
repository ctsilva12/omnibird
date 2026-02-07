import db
import utils.services.discordutils as discordutils
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
                if info["price"]:
                    message_array.append(f"{info['rarity']}: {info['price']} {l.text("_symbols", "coin_icon")}")
            await ctx.send(
                f"{l.text("sell", "info")}\n"
                + "\n".join(message_array)
            )
            return

        try:
            mfws, inventory_map, guilds, emojis = await discordutils.parse_and_validate_mfws(self.bot, ctx.author, *values)
        except ValueError as e:
            await ctx.send(str(e))
            return

        if not mfws:
            await ctx.send(l.text("transfer", "no_values"))
            return
        
        
        async with db.transaction() as cur:
            mfw_ids = [mfw[0] for mfw in mfws]
            placeholders = dbutils.generate_placeholders(mfw_ids)
            update_sql = f"""
                UPDATE users u
                JOIN (
                    SELECT i.user_id, COALESCE(SUM((i.quantity - 1) * ROUND(r.price / 2)), 0) AS earned
                    FROM inventory i
                    JOIN mfws m ON i.mfw_id = m.id
                    JOIN rarities r ON r.id = m.rarity_id
                    WHERE i.user_id = %s AND mfw_id in ({placeholders})
                    GROUP BY i.user_id
                ) sub ON u.id = sub.user_id
                SET u.coins = u.coins + sub.earned
                WHERE u.id = %s
                """
            params = [ctx.author.id] + mfw_ids + [ctx.author.id]
            await cur.execute(update_sql, tuple(params))
            
            await cur.execute(
            f"""UPDATE inventory
            SET quantity = quantity - 1
            WHERE user_id = %s AND mfw_id in ({placeholders})""", tuple([ctx.author.id] + mfw_ids))
            await dbutils.cleanup_inventory(ctx.author.id, cur=cur)
            await cur.execute("SELECT coins FROM users WHERE id = %s", (ctx.author.id,))
            new_coins_row = await cur.fetchone()
            new_coins = new_coins_row[0] if new_coins_row else 0
            await ctx.send(l.text("sell", "success", mention=ctx.author.mention, new_coins=new_coins, emojis=emojis))