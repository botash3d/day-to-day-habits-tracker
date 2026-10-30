SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/users/me"
CREDS = {"email": "ashwani@example.com", "password": "a-strong-passphrase"}


async def register(client):
    response = await client.post(SIGNUP, json={**CREDS, "full_name": "Ashwani"})
    assert response.status_code == 201


async def test_login_returns_working_token(client):
    await register(client)
    response = await client.post(LOGIN, json=CREDS)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    me = await client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == CREDS["email"]


async def test_login_email_is_case_insensitive(client):
    await register(client)
    response = await client.post(LOGIN, json={**CREDS, "email": "ASHWANI@Example.com"})
    assert response.status_code == 200


async def test_wrong_password_and_unknown_email_look_identical(client):
    await register(client)
    wrong = await client.post(LOGIN, json={**CREDS, "password": "not-the-password"})
    unknown = await client.post(LOGIN, json={**CREDS, "email": "nobody@example.com"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_me_requires_valid_token(client):
    assert (await client.get(ME)).status_code == 401
    bad = await client.get(ME, headers={"Authorization": "Bearer not.a.token"})
    assert bad.status_code == 401
