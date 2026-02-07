import discord
from languages import l
import db
from aiomysql import Cursor
import asyncio
import random
from typing import Any
import utils.pure.formatting as formatting
import utils.services.dbutils as dbutils
import json
from ..packs.definition import PackConfig, compile_filters, parse_payload, apply_filters, compute_weights, weighted_sample

async def fetch_eligible_mfws(pack: PackConfig):
    where, params = compile_filters(pack.global_filters)
    columns = ["id", "name", "rarity_id", "guild_id", "is_animated"]

    query = f"""
        SELECT {", ".join(columns)}
        FROM mfws
        WHERE enabled = TRUE
        {f"AND {where}" if where else ""}
    """
    rows = await db.fetch_all(query, params, cache=True)
    items = [dict(zip(columns, row)) for row in rows]
    return items

async def get_mfws_from_pack(pack_id : int, num : int = 1):
    if (num < 1):
        raise ValueError("num must be >=1")
    
    rows = await db.fetch_one("SELECT payload FROM packs where id = %s", (pack_id,), cache=True)
    if rows is None: raise ValueError(f"pack {pack_id} has no payload")
    payload = json.loads(rows[0])
    pack: PackConfig = parse_payload(payload)
    pool = await fetch_eligible_mfws(pack)
    return await asyncio.to_thread(_resolve_pack_sync, pack, pool, num)

def _resolve_pack_sync(pack: PackConfig, pool: list[dict[str, Any]], num: int):
    results = []
    for _ in range(num):
        selected_ids_global = set()
        mfws_for_roll = []

        for slot in pack.slots:
            slot_pool = apply_filters(pool, slot.filters or [])
            per_rarity = slot.per_rarity_filters or {}

            weights = compute_weights(slot_pool, slot.item_weights, slot.rarity_weights)

            if not pack.duplication.allow_duplicates_across_slots:
                filtered_pairs = [(it, w) for it, w in zip(slot_pool, weights) if it["id"] not in selected_ids_global]
                if not filtered_pairs:
                    if pack.post_processing.on_empty == "fallback_to_pool":
                        filtered_pairs = list(zip(slot_pool, weights))
                    else:
                        raise ValueError(f"slot '{slot.name}' has no eligible items after duplication filtering")
                slot_pool, weights = zip(*filtered_pairs) if filtered_pairs else ([], [])
            
            k = slot.rolls
            distinct = slot.selection.distinct_within_slot
            chosen = weighted_sample(slot_pool, weights, k, distinct)
            final_chosen = []
            for it in chosen:
                rar_key = str(it.get("rarity_id"))
                extra_filters = per_rarity.get(rar_key, [])
                if extra_filters:
                    if apply_filters([it], extra_filters):
                        final_chosen.append(it)
                    else:
                        repl_candidates = apply_filters(slot_pool, extra_filters)
                        repl_candidates = [c for c in repl_candidates if c["id"] not in selected_ids_global and c not in final_chosen]
                        if repl_candidates:
                            final_chosen.append(random.choice(repl_candidates))
                        else:
                            if pack.post_processing.on_empty == "raise_error":
                                raise ValueError(f"no candidate for rarity-specific constraints in slot '{slot.name}'")
                else:
                    final_chosen.append(it)

            for it in final_chosen:
                selected_ids_global.add(it["id"])
            mfws_for_roll.extend(final_chosen)
        results.extend(mfws_for_roll)

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

    mfws = await get_mfws_from_pack(pack_id, amount)
    new_mfws = set(await dbutils.insert_inventory(user.id, [mfw["id"] for mfw in mfws], cur))
    parts = []
    harvest_message = random.choice(harvest_messages)
    prefix = l.text("harvest", "prefix", mention=user.mention)
    is_new = False
    for mfw in mfws:
        is_new = mfw["id"] in new_mfws
        guild = bot.get_guild(mfw["guild_id"])
        rarity_name = l.text("rarities", f"{mfw["rarity_id"]}")
        emoji = (
            discord.utils.get(guild.emojis, name=mfw["name"])
            if guild else None
        )
        rarity_name = f"**{rarity_name}**" if is_new else rarity_name

        if emoji:
            item = f"{emoji} ({rarity_name})"
        else:
            item = f"{mfw["name"]} ({rarity_name})"
            
        print(f"{mfw["name"]} ({rarity_name}) {"(new)" if is_new else "(old)"}")
        parts.append(item)
        if is_new: new_mfws.discard(mfw["id"])

    message = prefix + formatting.join_with_and(parts) + harvest_message
    if is_new and len(mfws) == 1: message += f" {l.text("harvest", "new_mfw")}"
    return message
