import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimiter, client_ip

pytestmark = pytest.mark.asyncio

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
PASSWORD = "a-strong-passphrase"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def rate_limits_on(monkeypatch):
    # The suite runs with limits off; these tests turn them on.
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    rate_limit.reset_all()
    yield
    rate_limit.reset_all()


async def sign_up(client, email: str) -> None:
    response = await client.post(
        SIGNUP, json={"email": email, "password": PASSWORD, "full_name": "Test User"}
    )
    assert response.status_code == 201


def credentials(email: str, password: str = PASSWORD) -> dict[str, str]:
    return {"email": email, "password": password}


# ---------------------------------------------------------------- the limiter


async def test_limiter_blocks_after_limit_and_sets_retry_after():
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window_seconds=60, clock=clock)

    limiter.hit("a")
    limiter.hit("a")
    with pytest.raises(HTTPException) as caught:
        limiter.hit("a")

    assert caught.value.status_code == 429
    assert caught.value.headers["Retry-After"] == "60"
    assert "Too many attempts" in caught.value.detail


async def test_limiter_window_expires():
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.hit("a")

    clock.now = 59
    with pytest.raises(HTTPException) as caught:
        limiter.hit("a")
    assert caught.value.headers["Retry-After"] == "1"

    clock.now = 60
    limiter.hit("a")  # the old hit has aged out


async def test_limiter_keys_are_independent_and_reset_works():
    limiter = RateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    limiter.hit("a")

    limiter.hit("b")  # a different key is unaffected
    with pytest.raises(HTTPException):
        limiter.check("a")

    limiter.reset("a")
    limiter.check("a")


async def test_check_does_not_count_but_record_does():
    limiter = RateLimiter(limit=1, window_seconds=60, clock=FakeClock())

    limiter.check("a")
    limiter.check("a")
    limiter.record("a")

    with pytest.raises(HTTPException):
        limiter.check("a")


async def test_long_waits_are_shown_in_minutes():
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window_seconds=900, clock=clock)
    limiter.hit("a")

    with pytest.raises(HTTPException) as caught:
        limiter.hit("a")

    assert "15 minutes" in caught.value.detail


# ---------------------------------------------------------------- endpoints


async def test_login_is_limited_per_ip(client, monkeypatch, rate_limits_on):
    monkeypatch.setattr(rate_limit, "login_ip_limiter", RateLimiter(3, 60))

    for _ in range(3):
        response = await client.post(LOGIN, json=credentials("nobody@example.com"))
        assert response.status_code == 401
    blocked = await client.post(LOGIN, json=credentials("nobody@example.com"))

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


async def test_repeated_failures_block_even_the_right_password(
    client, monkeypatch, rate_limits_on
):
    monkeypatch.setattr(rate_limit, "login_failure_limiter", RateLimiter(2, 900))
    await sign_up(client, "a@example.com")

    wrong = credentials("a@example.com", "wrong-password")
    assert (await client.post(LOGIN, json=wrong)).status_code == 401
    assert (await client.post(LOGIN, json=wrong)).status_code == 401
    blocked = await client.post(LOGIN, json=credentials("a@example.com"))

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


async def test_successful_login_clears_the_failure_count(
    client, monkeypatch, rate_limits_on
):
    monkeypatch.setattr(rate_limit, "login_failure_limiter", RateLimiter(2, 900))
    await sign_up(client, "a@example.com")
    wrong = credentials("a@example.com", "wrong-password")
    right = credentials("a@example.com")

    assert (await client.post(LOGIN, json=wrong)).status_code == 401
    assert (await client.post(LOGIN, json=right)).status_code == 200
    assert (await client.post(LOGIN, json=wrong)).status_code == 401
    assert (await client.post(LOGIN, json=wrong)).status_code == 401
    assert (await client.post(LOGIN, json=right)).status_code == 429


async def test_failures_for_one_email_do_not_block_another(
    client, monkeypatch, rate_limits_on
):
    monkeypatch.setattr(rate_limit, "login_failure_limiter", RateLimiter(2, 900))
    await sign_up(client, "a@example.com")
    await sign_up(client, "b@example.com")
    wrong = credentials("a@example.com", "wrong-password")
    await client.post(LOGIN, json=wrong)
    await client.post(LOGIN, json=wrong)

    response = await client.post(LOGIN, json=credentials("b@example.com"))

    assert response.status_code == 200


async def test_unknown_emails_are_counted_too(client, monkeypatch, rate_limits_on):
    monkeypatch.setattr(rate_limit, "login_failure_limiter", RateLimiter(2, 900))
    ghost = credentials("ghost@example.com")

    assert (await client.post(LOGIN, json=ghost)).status_code == 401
    assert (await client.post(LOGIN, json=ghost)).status_code == 401
    assert (await client.post(LOGIN, json=ghost)).status_code == 429


async def test_signup_is_limited_per_ip(client, monkeypatch, rate_limits_on):
    monkeypatch.setattr(rate_limit, "signup_ip_limiter", RateLimiter(2, 3600))

    await sign_up(client, "one@example.com")
    await sign_up(client, "two@example.com")
    blocked = await client.post(
        SIGNUP,
        json={"email": "three@example.com", "password": PASSWORD, "full_name": "T"},
    )

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


async def test_limits_do_nothing_when_disabled(client, monkeypatch):
    # No rate_limits_on fixture: the suite default is "disabled".
    monkeypatch.setattr(rate_limit, "login_ip_limiter", RateLimiter(1, 60))
    monkeypatch.setattr(rate_limit, "login_failure_limiter", RateLimiter(1, 60))

    for _ in range(3):
        response = await client.post(LOGIN, json=credentials("nobody@example.com"))
        assert response.status_code == 401


# ---------------------------------------------------------------- client IP


def make_request(forwarded: str | None, host: str = "9.9.9.9") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


@pytest.mark.parametrize(
    ("count", "forwarded", "expected"),
    [
        (0, "1.1.1.1, 2.2.2.2", "9.9.9.9"),  # not behind a proxy: header ignored
        (1, "1.1.1.1, 2.2.2.2", "2.2.2.2"),  # a forged left entry is ignored
        (2, "1.1.1.1, 2.2.2.2", "1.1.1.1"),
        (3, "1.1.1.1, 2.2.2.2", "9.9.9.9"),  # fewer entries than proxies: fall back
        (1, None, "9.9.9.9"),
    ],
)
async def test_client_ip(monkeypatch, count, forwarded, expected):
    monkeypatch.setattr(get_settings(), "trusted_proxy_count", count)

    assert client_ip(make_request(forwarded)) == expected


# ---------------------------------------------------------------- settings

BASE_SETTINGS = {"_env_file": None, "database_url": "sqlite+aiosqlite://"}
GOOD_SECRET = "k3Jf9sLq0Zx7VbN2mQw8Rt5Yu1Io6PaD"


async def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            **BASE_SETTINGS,
            environment="production",
            secret_key="replace-me-" + "x" * 30,
        )


async def test_production_rejects_low_variety_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(**BASE_SETTINGS, environment="production", secret_key="a" * 40)


async def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            **BASE_SETTINGS,
            environment="production",
            secret_key=GOOD_SECRET,
            cors_origins=["*"],
        )


async def test_production_accepts_real_settings():
    settings = Settings(
        **BASE_SETTINGS,
        environment="production",
        secret_key=GOOD_SECRET,
        cors_origins=["https://app.example.com"],
    )

    assert settings.is_production


async def test_local_environment_allows_placeholder_secret():
    settings = Settings(
        **BASE_SETTINGS, environment="local", secret_key="replace-me-" + "x" * 30
    )

    assert not settings.is_production