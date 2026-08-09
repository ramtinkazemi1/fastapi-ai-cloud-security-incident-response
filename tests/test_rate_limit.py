"""Tests for the intentionally small in-memory rate limiter."""

import pytest

from app.core.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_rejects_requests_after_window_limit() -> None:
    """A client receives retry guidance after exceeding its allowance."""
    limiter = RateLimiter(requests=2, window_seconds=60)

    assert await limiter.retry_after("client") is None
    assert await limiter.retry_after("client") is None
    assert await limiter.retry_after("client") is not None
