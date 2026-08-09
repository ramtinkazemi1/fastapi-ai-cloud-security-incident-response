"""Small in-memory fixed-window rate limiter."""

import asyncio
from dataclasses import dataclass
from time import monotonic


@dataclass
class Window:
    """Request count and start time for one client window."""

    started_at: float
    count: int = 0


class RateLimiter:
    """Bound API traffic without introducing Redis into this small project."""

    def __init__(self, *, requests: int, window_seconds: int) -> None:
        self._requests = requests
        self._window_seconds = window_seconds
        self._windows: dict[str, Window] = {}
        self._lock = asyncio.Lock()

    async def retry_after(self, client: str) -> int | None:
        """Count a request and return retry seconds when the limit is exceeded."""
        now = monotonic()
        async with self._lock:
            window = self._windows.get(client)
            if window is None or now - window.started_at >= self._window_seconds:
                self._windows[client] = Window(started_at=now, count=1)
                return None

            window.count += 1
            if window.count <= self._requests:
                return None

            remaining = self._window_seconds - (now - window.started_at)
            return max(1, round(remaining))
