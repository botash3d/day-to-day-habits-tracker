"""In-memory rate limiting for the auth endpoints.

Counters live in this process only: they reset on restart and are not shared
between worker processes. That is fine for a single-instance deployment.
"""

import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

# Guards memory if someone floods the server with different keys.
_MAX_KEYS = 10_000


def _wait_text(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    return f"{math.ceil(seconds / 60)} minutes"


class RateLimiter:
    """Allows `limit` recorded events per key within a sliding time window."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float] | None:
        hits = self._hits.get(key)
        if hits is None:
            return None
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return None
        return hits

    def check(self, key: str) -> None:
        """Raise 429 if the key is already at its limit. Records nothing."""
        now = self._clock()
        hits = self._recent(key, now)
        if hits is not None and len(hits) >= self.limit:
            retry = max(1, math.ceil(hits[0] + self.window - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {_wait_text(retry)}.",
                headers={"Retry-After": str(retry)},
            )

    def record(self, key: str) -> None:
        now = self._clock()
        hits = self._recent(key, now)
        if hits is None:
            hits = self._hits.setdefault(key, deque())
        hits.append(now)
        if len(self._hits) > _MAX_KEYS:
            for stale in list(self._hits):
                self._recent(stale, now)

    def hit(self, key: str) -> None:
        """Check the limit, then count this event."""
        self.check(key)
        self.record(key)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


# Tune these numbers to taste. Students on one school or institute network share
# an IP address, so the per-IP limits are deliberately generous.
login_ip_limiter = RateLimiter(limit=20, window_seconds=60)
login_failure_limiter = RateLimiter(limit=8, window_seconds=15 * 60)
signup_ip_limiter = RateLimiter(limit=20, window_seconds=60 * 60)


def reset_all() -> None:
    for limiter in (login_ip_limiter, login_failure_limiter, signup_ip_limiter):
        limiter.reset()


def _enabled() -> bool:
    return get_settings().rate_limit_enabled


def client_ip(request: Request) -> str:
    """The caller's IP address.

    Behind a reverse proxy the socket address is the proxy's, so with
    TRUSTED_PROXY_COUNT=N we read the Nth entry from the right of
    X-Forwarded-For. Entries further left can be forged by the client.
    """
    count = get_settings().trusted_proxy_count
    if count > 0:
        parts = [
            p.strip()
            for p in request.headers.get("x-forwarded-for", "").split(",")
            if p.strip()
        ]
        if len(parts) >= count:
            return parts[-count]
    return request.client.host if request.client else "unknown"


async def limit_login_by_ip(request: Request) -> None:
    if _enabled():
        login_ip_limiter.hit(client_ip(request))


async def limit_signup_by_ip(request: Request) -> None:
    if _enabled():
        signup_ip_limiter.hit(client_ip(request))


# Failed logins are counted per email. Unknown emails are counted too, so the
# response never reveals whether an account exists.
def check_login_failures(email: str) -> None:
    if _enabled():
        login_failure_limiter.check(email)


def record_login_failure(email: str) -> None:
    if _enabled():
        login_failure_limiter.record(email)


def clear_login_failures(email: str) -> None:
    if _enabled():
        login_failure_limiter.reset(email)