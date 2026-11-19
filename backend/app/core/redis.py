"""Async Redis client management and connectivity health probes."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter

from fastapi import Request
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisManager:
    """Encapsulates the async Redis client lifecycle and health verification."""

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str = "",
        redis_url: str | None = None,
        socket_timeout: float = 3.0,
    ) -> None:
        self._socket_timeout = socket_timeout
        if redis_url:
            self._client: Redis = Redis.from_url(
                redis_url,
                socket_connect_timeout=socket_timeout,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )
        else:
            self._client = Redis(
                host=host,
                port=port,
                db=db,
                password=password or None,
                socket_connect_timeout=socket_timeout,
                socket_timeout=socket_timeout,
                decode_responses=True,
            )

    @property
    def client(self) -> Redis:
        """Return the managed async Redis client."""
        return self._client

    async def check_health(self) -> tuple[bool, float, str]:
        """Run a PING check against Redis with bounded timeout."""
        started = perf_counter()
        try:
            async with asyncio.timeout(self._socket_timeout):
                pong = await self._client.ping()
            latency_ms = round((perf_counter() - started) * 1000, 2)
            if pong:
                return True, latency_ms, "Connected"
            return False, latency_ms, "Unexpected PING response"
        except Exception as exc:
            latency_ms = round((perf_counter() - started) * 1000, 2)
            logger.warning("Redis readiness check failed: %s", type(exc).__name__)
            return False, latency_ms, f"Connection failed ({type(exc).__name__})"

    async def close(self) -> None:
        """Close the async Redis client and connection pool."""
        await self._client.aclose()


def get_redis_client(request: Request) -> Redis:
    """FastAPI dependency returning the managed Redis client for future modules."""
    redis_manager: RedisManager = request.app.state.redis_manager
    return redis_manager.client
