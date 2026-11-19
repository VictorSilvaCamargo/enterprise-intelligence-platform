"""Generic repository contract establishing clean persistence boundaries."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class BaseRepository[ModelT: Base]:
    """Base async repository providing a shared session boundary for future modules."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Expose the scoped async database session to subclasses."""
        return self._session
