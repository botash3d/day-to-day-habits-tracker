import pytest

from app.core.config import normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        (
            "postgresql://u:p@h/db?sslmode=require",
            "postgresql+asyncpg://u:p@h/db?ssl=require",
        ),
        (
            "postgresql://u:p@h/db?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@h/db?ssl=require",
        ),
        (
            "postgresql+asyncpg://u:p@h/db?ssl=require",
            "postgresql+asyncpg://u:p@h/db?ssl=require",
        ),
        ("sqlite+aiosqlite:///:memory:", "sqlite+aiosqlite:///:memory:"),
    ],
)
def test_normalize_database_url(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected