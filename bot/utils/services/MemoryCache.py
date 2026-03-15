import asyncio
import time

class MemoryCache:
    def __init__(self, default_ttl=300):
        self._cache = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self.started = False
    
    def _now(self):
        return time.monotonic()
    
    async def _background_evict_expired(self, interval=60):
        while True:
            await asyncio.sleep(interval)
            await self.clear_expired()

    async def set(self, key, value, ttl=None):
        ttl = ttl or self._default_ttl
        expire = self._now() + ttl
        async with self._lock:
            self._cache[key] = (value, expire)

    def get(self, key):
        val = self._cache.get(key)
        if val:
            value, expire = val
            if self._now() < expire:
                return value
            else: self._cache.pop(key, None)
        return None
    
    async def clear(self, key=None):
        async with self._lock:
            if key: self._cache.pop(key, None)
            else: self._cache.clear()

    async def clear_expired(self):
        async with self._lock:
            expired = [
                k for k, (_, exp) in self._cache.items()
                if self._now() > exp
            ]
            for k in expired:
                del self._cache[k]

db_cache = MemoryCache()
async def init_cache_cleanup(interval=60):
    if not db_cache.started:
        db_cache.started = True
        asyncio.create_task(db_cache._background_evict_expired(interval))