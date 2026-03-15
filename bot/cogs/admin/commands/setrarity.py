import db

async def setrarity(self, ctx, mfw_name : str|None, new_rarity_id : int|None):
    if (mfw_name is None):
        await ctx.send("Error: mfw_name is None")
        return
    if (new_rarity_id is None):
        await ctx.send("Error: new_rarity_id is None")
        return

    rarities = await db.fetch_all("SELECT * FROM rarities", cache=True, ttl=9999)
    rarity_map = {r[0]: r[1] for r in rarities}
    rarity_map[0] = "Unused"
    if new_rarity_id not in rarity_map:
        await ctx.send(f"Error: invalid new_rarity_id. Valid ids: {rarity_map}")
        return
    
    row_count = await db.execute("UPDATE mfws SET rarity_id = %s, enabled = TRUE WHERE name = %s", (new_rarity_id, mfw_name))
    if row_count == 0:
        await ctx.send(f"Error: {mfw_name} does not exist")
    else:
        await ctx.send(f"{mfw_name} successfully changed to {rarity_map[new_rarity_id]}!")