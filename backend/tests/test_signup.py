import pytest
from sqlalchemy import select

from app.models.user import User

URL = "/api/v1/auth/signup"
VALID = {
    "email": "Ashwani@Example.com",
    "password": "a-strong-passphrase",
    "full_name": "Ashwani",
}


async def test_signup_creates_user(client, session_factory):
    response = await client.post(URL, json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ashwani@example.com"
    assert "password" not in body
    assert "hashed_password" not in body

    async with session_factory() as session:
        user = await session.scalar(select(User))
    assert user.hashed_password != VALID["password"]
    assert user.hashed_password.startswith("$argon2id$")


async def test_duplicate_email_is_case_insensitive(client):
    assert (await client.post(URL, json=VALID)).status_code == 201
    response = await client.post(URL, json={**VALID, "email": "ASHWANI@example.com"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "override",
    [{"password": "short"}, {"email": "not-an-email"}, {"full_name": "   "}],
)
async def test_invalid_payload_rejected(client, override):
    response = await client.post(URL, json={**VALID, **override})
    assert response.status_code == 422
