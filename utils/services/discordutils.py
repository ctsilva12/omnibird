
from languages import l
import discord
import warnings
import traceback
import db
import utils.pure.formatting as formatting
import utils.pure.parsing as parsing

async def sanitize_quantity(ctx, quantity : int|None|str, allow_zero=False):
    if (quantity == None):
            await ctx.send(l.text("quantity", "none"))
            return None
    
    min_quantity = 1
    if allow_zero: min_quantity -= 1
    try:
        quantity = int(quantity)
        if quantity < min_quantity:
            raise ValueError
    except (ValueError, TypeError):
        await ctx.send(l.text("quantity", "invalid"))
        return None
    return quantity


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
    
async def sync_emojis(bot):
    mfw_rows = await db.fetch_all("SELECT id from mfws")
    # set
    current_mfws = {row[0] for row in mfw_rows}
    insert_data = []
    new_mfws = []
    current_emojis = set()
    guild_rows = await db.fetch_all("SELECT id from guilds", cache=True)
    for guild in guild_rows:
        guild_id = guild[0]
        guild = bot.get_guild(guild_id)
        if not guild:
            warnings.warn(f"Failed to find guild {guild_id}. Make sure the bot is in the guild", stacklevel=2)
            continue
        for emoji in guild.emojis:
            current_emojis.add(emoji.id)
            if emoji.id not in current_mfws: 
                new_mfws.append((emoji.id, emoji.name))
            insert_data.append((emoji.id, emoji.name, 0, guild_id, getattr(emoji, "animated", False)))

    deleted_emojis = current_mfws - current_emojis
    if deleted_emojis:
        deleted_mfws_rows = await db.fetch_all(
            "SELECT id, name FROM mfws WHERE id IN %s",
            (tuple(deleted_emojis),)
        )
        deleted_mfws_dict = {row[0]: row[1] for row in deleted_mfws_rows}
        mfws_in_inventory = await db.fetch_all(
            "SELECT id, name FROM mfws WHERE id IN %s AND id IN (SELECT mfw_id FROM inventory)",
            (tuple(deleted_emojis),)
        )
        safe_to_delete = deleted_emojis - {row[0] for row in mfws_in_inventory}
        if safe_to_delete:
            placeholders = ", ".join(["%s"] * len(safe_to_delete))
            await db.execute(
                f"DELETE FROM mfws WHERE id IN ({placeholders})",
                (tuple(safe_to_delete),)
            )

        deleted_names = [deleted_mfws_dict[i] for i in deleted_emojis if i in deleted_mfws_dict]
        print(f"Deleted emojis since last sync: {', '.join(deleted_names)}")

        if mfws_in_inventory:
            print(f"Could not delete the following mfws still in inventory: ({', '.join(mfw[1] for mfw in mfws_in_inventory)})")

    if not insert_data: return
    try:
        query = """
            INSERT INTO mfws (id, name, rarity_id, guild_id, is_animated)
            VALUES (%s, %s, %s, %s, %s)
            AS new
            ON DUPLICATE KEY UPDATE name = new.name, id = new.id
        """
        await db.execute(query, insert_data)
    except Exception:
        warnings.warn(f"Failed to sync emojis")
        traceback.print_exc()
    if new_mfws:
        print(f"Remember to set a rarity for ({', '.join(mfw[1] for mfw in new_mfws)}) with setrarity!")

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
    mfws = parsing.parse_mfw_values(" ".join(values))
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
    emoji_text = formatting.join_with_and(emojis)

    return items, inventory_map, guilds, emoji_text