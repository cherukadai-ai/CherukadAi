"""Rate limiters: Redis fixed-window (production) and in-memory sliding-window (tests)."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from redis.asyncio import Redis

from app.modules.identity.domain.ports import RateLimiter

_KEY_PREFIX = "identity:ratelimit:"


class RedisRateLimiter(RateLimiter):
    """Fixed-window counter backed by Redis INCR/EXPIRE."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        redis_key = _KEY_PREFIX + key
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, window_seconds)
        return count <= limit


class InMemoryRateLimiter(RateLimiter):
    """Sliding-window limiter for tests and single-process local runs."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True
