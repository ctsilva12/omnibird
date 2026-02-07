
import discord
import utils.services.dbutils as dbutils
import utils.services.discordutils as discordutils
import db
import utils.pure.formatting as formatting
from languages import l

c = "check"
async def check(self, ctx, user: discord.User | None = None, *values: str):
    if user is None:
        user = ctx.author
        assert user is not None
    try:
        mfws, _, _, _ = await discordutils.parse_and_validate_mfws(self.bot, None, *values, check_ownership=False)
    except ValueError as e:
        await ctx.send(str(e))
        return e
    
    results = None

    placeholders = dbutils.generate_placeholders(mfws)
    query = f"""SELECT m.id, m.name, IFNULL(i.quantity,0), m.is_animated FROM mfws m
        LEFT JOIN inventory i ON i.mfw_id = m.id AND i.user_id = %s
    WHERE m.id in ({placeholders})
    ORDER BY i.quantity DESC, m.name ASC"""
    params = tuple([user.id] + [mfw[0] for mfw in mfws])
    async with db.transaction() as cur:
        await cur.execute(query, params)
        results = await cur.fetchall()
    
    owned_mfws = []
    unowned_mfws = []
    for mfw_id, name, quantity, is_animated in results:
        emoji = formatting.make_emoji(mfw_id, name, is_animated)
        if quantity > 0:
            owned_mfws.append(f"{emoji} (x{quantity})")
        else:
            unowned_mfws.append(emoji)

    lines = [l.text(c, "user_has", mention=user.mention)]
    if owned_mfws:
        lines.append(f":white_check_mark:: {formatting.join_with_and(owned_mfws)}")
    if unowned_mfws:
        lines.append(f":x:: {formatting.join_with_and(unowned_mfws)}")

    message = "\n".join(lines)

    for chunk in formatting.chunk_string(message, seps=("\n", ",")):
        await ctx.send(chunk, allowed_mentions=discord.AllowedMentions.none())
    

