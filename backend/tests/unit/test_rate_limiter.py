"""Unit tests for the in-memory rate limiter used in tests/local runs."""
import time

from app.modules.identity.infrastructure.rate_limiter import InMemoryRateLimiter


async def test_allows_requests_within_limit():
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        assert await limiter.hit("k", limit=5, window_seconds=60) is True


async def test_blocks_once_limit_exceeded():
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        await limiter.hit("k", limit=5, window_seconds=60)
    assert await limiter.hit("k", limit=5, window_seconds=60) is False


async def test_keys_are_independent():
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        await limiter.hit("a", limit=3, window_seconds=60)
    assert await limiter.hit("a", limit=3, window_seconds=60) is False
    assert await limiter.hit("b", limit=3, window_seconds=60) is True


async def test_window_slides_and_allows_again(monkeypatch):
    limiter = InMemoryRateLimiter()
    now = time.monotonic()
    ticks = iter([now, now, now + 61])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks, now + 61))

    assert await limiter.hit("k", limit=2, window_seconds=60) is True
    assert await limiter.hit("k", limit=2, window_seconds=60) is True
    assert await limiter.hit("k", limit=2, window_seconds=60) is True
