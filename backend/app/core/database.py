"""Async SQLAlchemy engine management and PostgreSQL connectivity checks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from time import perf_counter

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Encapsulates the SQLAlchemy async engine, session factory, and health probes."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_size: int = 5,
        max_overflow: int = 10,
        connect_timeout: float = 3.0,
        echo: bool = False,
    ) -> None:
        self._connect_timeout = connect_timeout
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=echo,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Return the underlying SQLAlchemy async engine."""
        return self._engine

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an AsyncSession and ensure proper cleanup."""
        async with self._session_factory() as db_session:
            yield db_session

    async def check_health(self) -> tuple[bool, float, str]:
        """Execute a lightweight SELECT 1 probe with bounded timeout."""
        started = perf_counter()
        try:
            async with asyncio.timeout(self._connect_timeout):
                async with self._engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            latency_ms = round((perf_counter() - started) * 1000, 2)
            return True, latency_ms, "Connected"
        except Exception as exc:
            latency_ms = round((perf_counter() - started) * 1000, 2)
            logger.warning("PostgreSQL readiness check failed: %s", type(exc).__name__)
            return False, latency_ms, f"Connection failed ({type(exc).__name__})"

    async def close(self) -> None:
        """Dispose all pooled database connections during application shutdown."""
        await self._engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped AsyncSession for future module routers."""
    db_manager: DatabaseManager = request.app.state.db_manager
    async for db_session in db_manager.session():
        yield db_session
