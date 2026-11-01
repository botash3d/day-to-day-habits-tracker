from functools import lru_cache
from typing import Literal, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# A production SECRET_KEY containing any of these was copied from an example file.
_PLACEHOLDER_MARKERS = (
    "placeholder",
    "change-me",
    "changeme",
    "replace-me",
    "your_key",
    "example",
)


# libpq options that asyncpg does not understand.
_UNSUPPORTED_QUERY_KEYS = {"channel_binding"}


def normalize_database_url(url: str) -> str:
    """Turn a hosting provider's Postgres URL into one SQLAlchemy + asyncpg accepts."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix) :]
            break
    if not url.startswith("postgresql+asyncpg://"):
        return url  # e.g. sqlite in tests

    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in _UNSUPPORTED_QUERY_KEYS:
            continue
        query.append(("ssl" if key == "sslmode" else key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "My App"
    environment: Literal["local", "test", "production"] = "local"
    database_url: str
    cors_origins: list[str] = Field(default_factory=list)

    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    rate_limit_enabled: bool = True
    # How many reverse proxies sit in front of the app (0 = none, use the socket IP).
    trusted_proxy_count: int = Field(default=0, ge=0, le=5)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("database_url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def check_production_settings(self) -> Self:
        if not self.is_production:
            return self
        lowered = self.secret_key.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_MARKERS) or len(
            set(self.secret_key)
        ) < 10:
            raise ValueError(
                "SECRET_KEY looks like a placeholder. Generate a random one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS must list your real frontend address, not '*'."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()