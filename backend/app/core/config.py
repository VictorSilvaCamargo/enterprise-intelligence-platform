"""Centralized application configuration loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Strongly typed application settings for Stage 1 foundation."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Enterprise Intelligence Platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API & Security
    api_v1_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # PostgreSQL
    postgres_user: str = "eip_user"
    postgres_password: str = "change_me_local_dev_only"
    postgres_db: str = "eip_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_connect_timeout: float = 3.0

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_url_override: str | None = Field(default=None, validation_alias="REDIS_URL")
    redis_socket_timeout: float = 3.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Accept either a JSON list or a comma-separated string of origins."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        raise ValueError("CORS_ORIGINS must be a list or comma-separated string.")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log levels and validate standard Python logging names."""
        normalized = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return normalized

    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy async connection URL without logging secrets."""
        if self.database_url_override:
            return self.database_url_override
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )
        return url.render_as_string(hide_password=False)

    @property
    def safe_database_target(self) -> str:
        """Return a credential-free PostgreSQL target identifier for logs."""
        if self.database_url_override:
            return "custom DATABASE_URL"
        return f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def safe_redis_target(self) -> str:
        """Return a credential-free Redis target identifier for logs."""
        if self.redis_url_override:
            return "custom REDIS_URL"
        return f"{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
