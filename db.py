from typing import AsyncIterator
import aiomysql
from aiomysql import Cursor
import asyncio
import json
import time
from typing import Any, Sequence, Optional, overload, List, Tuple, Literal
from contextlib import asynccontextmanager
import os

_pool = None

async def init_pool():
    global _pool
    if _pool is None:
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


_cache = {}

async def set_cache(key, value, ttl=300):
    loop = asyncio.get_event_loop()
    _cache[key] = (value, loop.time() + ttl)

async def get_cache(key):
    val = _cache.get(key)
    loop = asyncio.get_event_loop()
    if val:
        value, expire = val
        if loop.time() < expire:
            return value
        else:
            del _cache[key]
    return None

@overload
async def _fetch(
    query: str, *values: Any, fetch_type: Literal["one"], cache: bool = False, ttl: int = 300
) -> Optional[Tuple[Any, ...]]: ...
@overload
async def _fetch(
    query: str, *values: Any, fetch_type: Literal["all"], cache: bool = False, ttl: int = 300
) -> List[Tuple[Any, ...]]: ...
async def _fetch(
    query: str, *values: Any, fetch_type: str, cache: bool = False, ttl: int = 300
) -> Optional[Tuple[Any, ...]] | List[Tuple[Any, ...]]:
    flat_values = _flatten_values(values)
    cache_key = None
    if (cache):
        cache_key = f"{query}_{fetch_type}:{json.dumps(flat_values, sort_keys=True, ensure_ascii=False)}"
        cached = await get_cache(cache_key)
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
                await set_cache(cache_key, rows, ttl)
            return (rows or None) if fetch_type == "one" else (rows or [])

async def fetch_one(query: str, *values: Any, cache: bool = False, ttl: int = 300) -> Optional[tuple]:
    return await _fetch(query, *values, fetch_type="one", cache=cache, ttl=ttl)

async def fetch_all(query: str, *values: Any, cache : bool = False, ttl : int = 300) -> list[tuple]:
    return await _fetch(query, *values, fetch_type="all", cache=cache, ttl=ttl)

async def execute(query: str, *values: Any) -> int:
    pool = await init_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            flat_values = _flatten_values(values)
            if not flat_values:
                await cursor.execute(query)
            else:
                await cursor.execute(query, flat_values)
            await conn.commit()
            return cursor.rowcount

# USE FOR ANYTHING THAT INVOLVES CURRENCY/ACTIONS THAT NEED TO BE REVERTED IF SOMETHING BREAKS LATER
@asynccontextmanager
async def transaction():
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