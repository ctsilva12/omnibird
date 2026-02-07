import db
from aiomysql import Cursor
from typing import Any



async def get_admins(cache=True) -> list[int]:
    rows = await db.fetch_all("SELECT id from users WHERE is_admin = TRUE", cache=cache)
    ADMINS = [row[0] for row in rows]
    return ADMINS

def generate_placeholders(items : list[Any]) -> str:
    return ", ".join(["%s"] * len(items)) if items else ""

async def insert_inventory(user_id: int, mfws: list[int], cur: Cursor) -> list[int]:
    """returns new entries"""
    if not mfws:
        return []
    
    await cur.execute(
    "SELECT mfw_id FROM inventory WHERE user_id = %s AND mfw_id IN %s", (user_id, tuple(mfws)))
    existing = await cur.fetchall()
    existing_ids = {row[0] for row in existing}
    new_ids = [mfw for mfw in mfws if mfw not in existing_ids]

    values = [(user_id, mfw_id) for mfw_id in mfws]
    placeholders = ", ".join(["(%s, %s)"] * len(values))
    query = f"INSERT INTO inventory (user_id, mfw_id) VALUES {placeholders} ON DUPLICATE KEY UPDATE quantity = quantity + 1"
    flattened = [item for tup in values for item in tup]

    await cur.execute(query, tuple(flattened))
    return new_ids

async def cleanup_inventory(user_id=None, cur: Cursor|None = None):
    if user_id is None: await db.execute("DELETE FROM inventory WHERE quantity <= 0", cur=cur)
    else: await db.execute("DELETE FROM inventory WHERE user_id = %s AND quantity <= 0", (user_id,), cur=cur)


async def check_if_mfw_exists(mfw_name : str) -> dict[str, Any] | None:
    result = await db.fetch_one("SELECT id, guild_id, rarity_id, name, is_animated FROM mfws WHERE name = %s", (mfw_name,))
    if (result is None): return None
    return {
        "id": result[0],
        "guild": result[1],
        "rarity_id": result[2],
        "name": result[3],
        "is_animated": result[4]
    }

async def get_user_info(
    user_id: int,
    cur: Cursor | None = None,
    for_update: bool = False
) -> dict:
    """
    returns id, create_time, last_harvest, coins, reminder, reminder_at, last_harvest_channel.
    creates user if it doesnt exist
"""
    if for_update and cur is None:
        raise ValueError("for_update=True requires a transaction cursor")

    insert_sql = """
        INSERT INTO users (id)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE id = id
    """

    select_sql = """
        SELECT
            id,
            create_time,
            last_harvest,
            coins,
            reminder,
            reminder_at,
            last_harvest_channel
        FROM users
        WHERE id = %s
    """
    if for_update:
        select_sql += " FOR UPDATE"

    try:
        if cur is not None:
            await cur.execute(insert_sql, (user_id,))
            await cur.execute(select_sql, (user_id,))
            row = await cur.fetchone()
        else:
            async with db.transaction() as tx_cur:
                await tx_cur.execute(insert_sql, (user_id,))
                await tx_cur.execute(select_sql, (user_id,))
                row = await tx_cur.fetchone()

    except Exception as exc:
        raise RuntimeError(f"DB error while fetching/creating user {user_id}: {exc}") from exc

    return {
        "id": row[0],
        "create_time": row[1],
        "last_harvest": row[2],
        "coins": row[3],
        "reminder": row[4],
        "reminder_at": row[5],
        "last_harvest_channel": row[6],
    }

def build_qty_case_sql(items: list[tuple[int, int, int, str, int]]):
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
        # shouldn't happen
        qty_case_sql = "i.quantity"
    else:
        qty_case_sql = "CASE " + " ".join(case_clauses) + " ELSE i.quantity END"

    in_placeholders = ", ".join(["%s"] * len(ids)) if ids else ""

    return qty_case_sql, params, ids, in_placeholders

async def validate_mfws_by_id(
    *,
    cur,
    user_id: int,
    mfws: list[tuple], #(mfw_id, quantity, ...)
):
    if not mfws:
        return

    ids = [mfw_id for mfw_id, *_ in mfws]

    await cur.execute(
        f"""
        SELECT mfw_id, quantity
        FROM inventory
        WHERE user_id = %s AND mfw_id IN ({','.join(['%s'] * len(ids))})
        FOR UPDATE
        """,
        (user_id, *ids),
    )

    rows = await cur.fetchall()
    owned = {mfw_id: qty for mfw_id, qty in rows}

    for mfw_id, qty, *_ in mfws:
        if qty <= 0:
            raise ValueError("Invalid quantity!")

        if owned.get(mfw_id, 0) < qty:
            raise ValueError(
                f"<@{user_id}> tried to trade {qty} of mfw {mfw_id} "
                f"but only owns {owned.get(mfw_id, 0)}!"
            )
