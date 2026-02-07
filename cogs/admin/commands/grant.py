import discord
from languages import l
import db
import utils.services.dbutils as dbutils
import utils.services.discordutils as discordutils

async def grant(self, ctx, target : discord.Member|None = None, *values : str):
    target = target or ctx.author
    if not isinstance(target, discord.Member):
        await ctx.send(l.text("grant", "no_target"))
        return
    if not values:
        await ctx.send(l.text("grant", "no_values"))
        return
    try:
        mfws_to_transfer, inventory_map, guilds, emojis = await discordutils.parse_and_validate_mfws(self.bot, ctx.author, *values, check_ownership=False)
    except ValueError as e:
        await ctx.send(str(e))
        return

    if not mfws_to_transfer:
        await ctx.send(l.text("transfer", "nothing_to_transfer"))
        return
    
    async with db.transaction() as cur:
        await dbutils.get_user_info(target.id, cur=cur, for_update=True)
        insert_values = []
        insert_params = []
        for mfw_id, qty, _, _, _ in mfws_to_transfer:
            insert_values.append("(%s, %s, %s)")
            insert_params.extend((target.id, mfw_id, qty))

        insert_sql = f"""
            INSERT INTO inventory(user_id, mfw_id, quantity)
            VALUES {', '.join(insert_values)} AS new
            ON DUPLICATE KEY UPDATE inventory.quantity = inventory.quantity + new.quantity
        """
        await cur.execute(insert_sql, tuple(insert_params))
        await ctx.send(l.text("transfer", "success", user_mention=target.mention, emojis=emojis, author_mention=ctx.author.mention))