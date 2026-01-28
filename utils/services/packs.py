import discord
from languages import l
import db
from aiomysql import Cursor
import random
from typing import Any
import utils.pure.formatting as formatting
import utils.services.dbutils as dbutils

async def get_mfws_from_pack(pack_id : int, cur, num : int = 1) -> list[dict[str, Any]]:
    if (num < 1):
        raise ValueError("num must be >=1")
    
    row = await db.fetch_one("SELECT payload, filter_type FROM packs WHERE id = %s", (pack_id,), cache=True)
    payload_list = row[0].get("mfw_list", []) if row and row[0] else []
    filter_type = row[1] if row and row[1] else None
    
    pack_rarities = await db.fetch_all("SELECT p.rarity_id, p.chance, r.name FROM pack_rarities p INNER JOIN rarities r ON p.rarity_id = r.id WHERE pack_id = %s", (pack_id,), cache=True)
    if (not pack_rarities):
        raise ValueError(f"no rarities configured for pack {pack_id}")

    ids = []
    weights = []
    for rarity_id, chance, rarity_name in pack_rarities:
        if chance is None:
            continue
        ids.append(rarity_id)
        weights.append(float(chance))

    if not ids:
        raise ValueError(f"No rarity chances for pack {pack_id}")
    
    chosen_rarities = random.choices(ids, weights=weights, k=num)
    
    results = []
    for rarity_id in chosen_rarities:
        query = "SELECT id, name, guild_id FROM mfws WHERE rarity_id = %s"
        params = [rarity_id]
        if filter_type is not None and payload_list:
            query += f" AND name {"NOT" if filter_type == "blacklist" else ""} IN %s"
            params.append(tuple(payload_list))
        rarity_mfws = await db.fetch_all(query, tuple(params), cache=True)
        if not rarity_mfws:
            raise ValueError(f"no mfws available for rarity {rarity_id} after applying {filter_type} filter")
        
        mfw_id, mfw_name, mfw_guild = random.choice(rarity_mfws)
        rarity_name = next(r[2] for r in pack_rarities if r[0] == rarity_id)
        results.append({"id": mfw_id, 
        "guild": mfw_guild,
        "name": mfw_name,
        "rarity_name": rarity_name, 
        "rarity_id": rarity_id})

    return results

async def open_pack(
    *,
    bot,
    user,
    pack_id: int,
    cur : Cursor,
    amount: int = 1,
    harvest_messages: list[str]|None = None,
) -> str:
    if harvest_messages is None:
        harvest_messages = l.text_all("harvest_messages")
    mfws = await get_mfws_from_pack(pack_id, cur, amount)
    new_mfws = await dbutils.insert_inventory(user.id, [mfw["id"] for mfw in mfws], cur)
    parts = []
    harvest_message = random.choice(harvest_messages)
    prefix = l.text("harvest", "prefix", mention=user.mention)
    is_new = False
    for mfw in mfws:
        is_new = mfw["id"] in new_mfws
        guild = bot.get_guild(mfw["guild"])
        emoji = (
            discord.utils.get(guild.emojis, name=mfw["name"])
            if guild else None
        )
        rarity_name = f"**{mfw["rarity_name"]}**" if (is_new) else mfw["rarity_name"]

        if emoji:
            item = f"{emoji} ({rarity_name})"
        else:
            item = f"{mfw["name"]} ({rarity_name})"
            
        print(f"{mfw["name"]} ({rarity_name}) {"(new)" if is_new else "(old)"}")
        parts.append(item)

    message = prefix + formatting.join_with_and(parts) + harvest_message
    if is_new and len(mfws) == 1: message += f" {l.text("harvest", "new_mfw")}"
    return message