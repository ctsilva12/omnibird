import discord
from languages import l
import utils.services.discordutils as discordutils
import utils.services.dbutils as dbutils
import db

async def transfer(self, ctx, user: discord.Member | None = None, *values: str):
    if not isinstance(user, discord.Member):
        await ctx.send(l.text("transfer", "no_target"))
        return
    if user.id == ctx.author.id:
        await ctx.send(l.text("transfer", "self_target"))
        return

    if not values:
        await ctx.send(l.text("transfer", "no_values"))
        return
    
    async with db.transaction() as cur:
        try:
            mfws_to_transfer, inventory_map, guilds, emojis = await discordutils.parse_and_validate_mfws(self.bot, ctx.author, *values, cur=cur)
        except ValueError as e:
            await ctx.send(str(e))
            return

        if not mfws_to_transfer:
            await ctx.send(l.text("transfer", "nothing_to_transfer"))
            return
               
        qty_case_sql, params, ids, in_placeholders = dbutils.build_qty_case_sql(mfws_to_transfer)

        update_sql = f"""
            UPDATE inventory i
            SET i.quantity = {qty_case_sql}
            WHERE i.user_id = %s AND i.mfw_id IN ({in_placeholders})
        """
        
        params.append(ctx.author.id)
        params.extend(ids)

        await cur.execute(update_sql, tuple(params))

        # --- Single multi-row INSERT to add quantities to recipient (ON DUPLICATE KEY UPDATE) ---
        insert_values = []
        insert_params = []
        for mfw_id, qty, *_ in mfws_to_transfer:
            insert_values.append("(%s, %s, %s)")
            insert_params.extend((user.id, mfw_id, qty))

        insert_sql = f"""
            INSERT INTO inventory(user_id, mfw_id, quantity)
            VALUES {', '.join(insert_values)} AS new
            ON DUPLICATE KEY UPDATE inventory.quantity = inventory.quantity + new.quantity
        """
        await cur.execute(insert_sql, tuple(insert_params))
        await dbutils.cleanup_inventory(ctx.author.id, cur=cur)
    
        await ctx.send(l.text("transfer", "success", user_mention=user.mention, emojis=emojis, author_mention=ctx.author.mention))