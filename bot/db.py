from typing import AsyncIterator
import aiomysql
from aiomysql import Cursor
import asyncio
import json
import time
from typing import Any, Sequence, Optional, overload, List, Tuple, Literal, Callable, TypeVar, Awaitable
from contextlib import asynccontextmanager
import os
from utils.services.MemoryCache import db_cache

_pool = None

async def init_pool():
    global _pool
    if _pool is None:
        timeout = 60
        delay = 0.5
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            try:
                test_conn = await aiomysql.connect(
                    host=os.getenv("DB_HOST") or "localhost",
                    user=os.getenv("DB_USER") or "root",
                    password=os.getenv("DB_PASSWORD") or "example",
                    db=os.getenv("DB"),
                )
                async with test_conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema=%s AND table_name=%s",
                        (os.getenv("DB"), "mfws")
                    )
                    if (await cur.fetchone())[0]:
                        await test_conn.ensure_closed()
                        break
                await test_conn.ensure_closed()
            except Exception:
                pass
            if asyncio.get_event_loop().time() > deadline:
                raise RuntimeError("DB not ready or required table missing after timeout")
            await asyncio.sleep(delay)

        _pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB"),
            minsize=1,
            maxsize=10
        )
    return _pool

@asynccontextmanager
async def get_cursor() -> AsyncIterator[Cursor]:
    pool = await init_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            yield cursor

T = TypeVar("T")
CursorHandler = Callable[
    ["Cursor"],
    Awaitable[T]
]
@overload
async def _fetch(
    query: str, *values: Any, fetch_type: Literal["one"], cache: bool = False, ttl: int = 300, cur : Cursor | None = None
) -> Optional[Tuple[Any, ...]]: ...
@overload
async def _fetch(
    query: str, *values: Any, fetch_type: Literal["all"], cache: bool = False, ttl: int = 300, cur : Cursor | None = None
) -> List[Tuple[Any, ...]]: ...
async def _fetch(
    query: str, *values: Any, fetch_type: str, cache: bool = False, ttl: int = 300, cur : Cursor | None = None
) -> Optional[Tuple[Any, ...]] | List[Tuple[Any, ...]]:
    flat_values = _flatten_values(values)
    if cur is not None:
        if cache: raise ValueError(f"cache not compatible with transaction on query {query}")
        if flat_values: await cur.execute(query, flat_values)
        else: await cur.execute(query)
        if (fetch_type == "one"): rows = await cur.fetchone()
        else: rows = await cur.fetchall()
    else:    
        cache_key = None
        if (cache):
            cache_key = f"{query}_{fetch_type}:{json.dumps(flat_values, sort_keys=True, ensure_ascii=False)}"
            cached = db_cache.get(cache_key)
            if (cached is not None):
                return cached
        pool = await init_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if flat_values: await cursor.execute(query, flat_values)
                else: await cursor.execute(query) 

                if (fetch_type == "one"): 
                    rows = await cursor.fetchone()
                else: rows = await cursor.fetchall()
                if (cache):
                    await db_cache.set(cache_key, rows, ttl)
                    
    return (rows or None) if fetch_type == "one" else (rows or [])

async def fetch_one(query: str, *values: Any, cache: bool = False, ttl: int = 300, cur : Cursor | None = None) -> Optional[tuple]:
    return await _fetch(query, *values, fetch_type="one", cache=cache, ttl=ttl, cur=cur)

async def fetch_all(query: str, *values: Any, cache : bool = False, ttl : int = 300, cur : Cursor | None = None) -> list[tuple]:
    return await _fetch(query, *values, fetch_type="all", cache=cache, ttl=ttl, cur=cur)

async def execute(query: str, *values: Any, cur: Cursor | None = None) -> int:
    flat_values = _flatten_values(values)

    def is_executemany(vals):
        return (
            isinstance(vals, (list, tuple)) and
            vals and
            all(isinstance(v, (list, tuple)) for v in vals)
        )

    if cur is not None:
        if not flat_values:
            await cur.execute(query)
        elif is_executemany(values[0]):
            await cur.executemany(query, values[0])
        else:
            await cur.execute(query, flat_values)
        return cur.rowcount

    pool = await init_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if not flat_values:
                await cursor.execute(query)
            elif is_executemany(values[0]):
                await cursor.executemany(query, values[0])
            else:
                await cursor.execute(query, flat_values)
            await conn.commit()
            return cursor.rowcount

# USE FOR ANYTHING THAT INVOLVES CURRENCY/ACTIONS THAT NEED TO BE REVERTED IF SOMETHING BREAKS LATER
@asynccontextmanager
async def transaction() -> AsyncIterator[Cursor]:
    pool = await init_pool()
    async with pool.acquire() as conn:
        try:
            await conn.begin()
            async with conn.cursor() as cursor:
                yield cursor
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

def _flatten_values(values: tuple[Any, ...]) -> Sequence[Any]:
    if not values:
        return ()
    if len(values) == 1 and isinstance(values[0], (tuple, list)):
        return values[0]
    return values