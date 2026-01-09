import re
from aiomysql import Cursor
import db
import discord
from discord.ext import commands
from datetime import datetime
import random
from typing import List, Dict, Any, Tuple
from utils.harvest_messages import HARVEST_MESSAGES
from languages import l

# todo: organize all these functions into different files
async def get_admins(cache=True) -> list[int]:
    rows = await db.fetch_all("SELECT id from users WHERE admin = TRUE", cache=cache)
    ADMINS = [row[0] for row in rows]
    return ADMINS

def join_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {l.text("and")} {items[1]}"
    return ", ".join(items[:-1]) + f" {l.text("and")} {items[-1]}"

def mfw_emoji(id : int, name : str, is_animated=False) -> str:
    if is_animated:
        return f"<a:{name}:{id}>"
    else: return f"<:{name}:{id}>"

async def get_user_info(
    user_id: int,
    cur: Cursor | None = None,
    for_update: bool = False
) -> dict:
    """
    Fetch user info.
    - for_update=True requires cur (inside a transaction).
    """
    if for_update and cur is None:
        raise ValueError("Cannot use FOR UPDATE without an existing transaction cursor.")

    # Determine query
    query = "SELECT * FROM users WHERE id = %s"
    if for_update:
        query += " FOR UPDATE"

    # Execute
    if cur:
        await cur.execute(query, (user_id,))
        row = await cur.fetchone()
    else:
        row = await db.fetch_one(query, user_id)
    if row is None:
        if cur:
            await cur.execute("INSERT INTO users (id) VALUES (%s)", (user_id,))
            await cur.execute(query, (user_id,))
            row = await cur.fetchone()
        else:
            await db.execute("INSERT INTO users (id) VALUES (%s)", (user_id,))
            row = await db.fetch_one(query, user_id)

        if row is None:
            raise RuntimeError(f"Failed to create user {user_id}.")

    return {
        "id": row[0],
        "create_time": row[1],
        "last_harvest": row[2],
        "coins": row[3],
        "reminder": row[4],
        "reminder_at": row[5],
        "last_harvest_channel": row[6]
    }

async def sanitize_quantity(ctx, quantity : int|None|str):
    if (quantity == None):
            await ctx.send(l.text("quantity", "none"))
            return None
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await ctx.send(l.text("quantity", "invalid"))
        return None
    return quantity

from datetime import timedelta
def format_duration(delta):
    """
    Converts a timedelta or seconds into a human-readable string.
    """
    if isinstance(delta, timedelta):
        total_seconds = int(delta.total_seconds())
    else:
        total_seconds = int(delta)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} {l.text("days") if days != 1 else l.text("day")}")
    if hours > 0:
        parts.append(f"{hours} {l.text("hours") if hours != 1 else l.text("hour")}")
    if minutes > 0:
        parts.append(f"{minutes} {l.text("minutes") if minutes != 1 else l.text("minute")}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} {l.text("seconds") if seconds != 1 else l.text("second")}")

    return join_with_and(parts)

async def get_username(bot, user_id: int) -> str | None:
    """
    Returns the username for a given user ID.
    Tries cache first, then falls back to fetching from API.
    Returns None if the user cannot be found.
    """
    user = bot.get_user(user_id)
    if user:
        return user.name

    try:
        user = await bot.fetch_user(user_id)
        return user.name
    except discord.NotFound:
        return None 
    except discord.HTTPException as e:
        print(f"Failed to fetch user: {e}")
        return None

async def open_pack(pack_id : int, num : int = 1) -> List[Dict[str, Any]]:
    if (num < 1):
        raise ValueError("num must be >=1")
    
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
        rarity_mfws = await db.fetch_all("SELECT id, name, guild_id FROM mfws WHERE rarity_id = %s", (rarity_id,), cache=True)
        mfw_id, mfw_name, mfw_guild = random.choice(rarity_mfws)
        rarity_name = next(r[2] for r in pack_rarities if r[0] == rarity_id)
        results.append({"id": mfw_id, 
        "guild": mfw_guild,
        "name": mfw_name,
        "rarity_name": rarity_name, 
        "rarity_id": rarity_id})

    return results

async def open_pack_and_build_message(
    *,
    bot,
    user,
    pack_id: int,
    amount: int = 1,
    harvest_messages: list[str]|None = None,
) -> str:
    if harvest_messages is None:
        harvest_messages = HARVEST_MESSAGES
    mfws = await open_pack(pack_id, amount)
    parts = []
    harvest_message = random.choice(harvest_messages)
    prefix = l.text("harvest", "prefix", mention=user.mention)
    is_new = False
    for mfw in mfws:
        result = await db.execute(
            """
            INSERT INTO inventory (user_id, mfw_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + 1
            """,
            (user.id, mfw["id"])
        )
        is_new = result == 1
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
            

        print(result)
        parts.append(item)

    message = prefix + join_with_and(parts) + harvest_message
    if is_new and len(mfws) == 1: message += f" {l.text("harvest", "new_mfw")}"
    return message

def canonical(name: str) -> str:
    return name.strip().replace(":", "")

async def parse_mfw_values(input_str: str):
    items = []

    input_str = input_str.replace(":", "")
    for part in input_str.split(","):
        tokens = part.strip().split()
        if not tokens:
            continue
        name = None
        quantity = 1
        if len(tokens) == 1:
            name = tokens[0]
            items.append((name, quantity))
            continue
        elif len(tokens) > 2:
            raise ValueError
        try:
            quantity = int(tokens[0])
            name = tokens[-1]
        except ValueError:
            name = tokens[0]
            try:
                quantity = int(tokens[1])
            except ValueError:
                quantity = 1

        if (name is None):
            raise ValueError
        items.append((name, quantity))
    return items

async def parse_and_validate_mfws(bot, user, *values: str):
    """
    Parses values (strings) into (name, qty) pairs, validates that `user`
    owns each item in sufficient quantity, and returns:
      - items: List[ (mfw_id, qty, guild_id, name) ]
      - inventory_map: dict[name] -> row tuple
      - guilds: dict[guild_id] -> Guild
      - emojis: list[str] human-readable pieces like "2 <:kfw:...>"
    Raises ValueError with user-facing messages on validation failure.
    """
    mfws = await parse_mfw_values(" ".join(values))
    if not mfws:
        raise ValueError("No valid mfws provided")

    mfw_names = [mfw_name for mfw_name, _ in mfws]
    rows = await db.fetch_all("""
        SELECT i.mfw_id, m.guild_id, i.quantity, m.rarity_id, m.name
        FROM inventory i
        INNER JOIN mfws m ON i.mfw_id = m.id
        WHERE i.user_id = %s AND m.name IN %s
    """, (user.id, tuple(mfw_names)))

    inventory_map = {row[4]: row for row in rows}
    guilds = {row[1]: bot.get_guild(row[1]) for row in rows}

    items = []
    emojis = []

    for mfw_name, quantity in mfws:
        if mfw_name not in inventory_map:
            raise ValueError(l.text("parse", "no_mfw", mfw_name=mfw_name))

        mfw_id, guild_id, owned_quantity, _, _ = inventory_map[mfw_name]

        if quantity <= 0:
            raise ValueError(l.text("parse", "invalid_quantity"))
        if quantity > owned_quantity:
            guild = guilds.get(guild_id)
            emoji = discord.utils.get(guild.emojis, name=mfw_name) if guild else mfw_name
            raise ValueError(l.text("parse", "more_than_they_have", owned_quantity=owned_quantity, emoji=emoji))

        items.append((mfw_id, quantity, guild_id, mfw_name))

        guild = guilds.get(guild_id)
        emoji = discord.utils.get(guild.emojis, name=mfw_name) if guild else mfw_name
        emojis.append(f"{quantity if quantity > 1 else 'a'} {emoji}")
    emoji_text = join_with_and(emojis)

    return items, inventory_map, guilds, emoji_text

    
def build_qty_case_sql(items: List[Tuple[int, int, int, str]]):
    """
    Given items: [(mfw_id, qty, guild_id, name), ...]
    Returns:
      - qty_case_sql: "CASE WHEN ... THEN GREATEST(i.quantity - %s, 0) ... ELSE i.quantity END"
      - params: list of params for the CASE (in proper order)
      - ids: list of mfw_ids (for IN placeholders)
      - in_placeholders: string like "%s, %s, %s"
    """
    case_clauses = []
    params = []
    ids = []
    for mfw_id, qty, *_ in items:
        case_clauses.append("WHEN i.mfw_id = %s THEN GREATEST(i.quantity - %s, 0)")
        params.extend((mfw_id, qty))
        ids.append(mfw_id)

    if not case_clauses:
        # Defensive: shouldn't happen if caller validated
        qty_case_sql = "i.quantity"
    else:
        qty_case_sql = "CASE " + " ".join(case_clauses) + " ELSE i.quantity END"

    in_placeholders = ", ".join(["%s"] * len(ids)) if ids else ""

    return qty_case_sql, params, ids, in_placeholders
    
async def cleanup_inventory(user_id=None):
    if user_id is None: await db.execute("DELETE FROM inventory WHERE quantity <= 0")
    else: await db.execute("DELETE FROM inventory WHERE user_id = %s AND quantity <= 0", (user_id,))

def chunk_by_length(items, max_len=1024, sep=", "):
    chunks = []
    current = ""

    for item in items:
        candidate = item if not current else current + sep + item
        if len(candidate) > max_len:
            chunks.append(current)
            current = item
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks

def chunk_string_by_length(string: str, max_len=3000, sep="\n") -> list[str]:
    chunks = []
    line = []
    total_length = 0

    for substring in string.split(sep):
        while substring:
            space_left = max_len - total_length
            piece = substring[:space_left]
            line.append(piece)
            total_length += len(piece)
            substring = substring[space_left:]
            if total_length >= max_len:
                chunks.append(sep.join(line))
                line.clear()
                total_length = 0

    if line:
        chunks.append(sep.join(line))

    return chunks


async def check_if_mfw_exists(mfw_name : str) -> Dict[str, Any] | None:
    result = await db.fetch_one("SELECT id, guild_id, rarity_id, name, is_animated FROM mfws WHERE name = %s", (mfw_name,))
    if (result is None): return None
    return {
        "id": result[0],
        "guild": result[1],
        "rarity_id": result[2],
        "name": result[3],
        "is_animated": result[4]
    }