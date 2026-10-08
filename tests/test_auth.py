from tests.conftest import PASSWORD, login, make_user

REG = {"name": "Rishad", "email": "rishad@example.com", "phone": "01712345678", "password": PASSWORD}


def test_register_creates_farmer_without_leaking_hash(client):
    r = client.post("/api/v1/auth/register", json=REG)
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "farmer" and body["email"] == "rishad@example.com"
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_is_409(client):
    client.post("/api/v1/auth/register", json=REG)
    r = client.post("/api/v1/auth/register", json=REG)
    assert r.status_code == 409 and r.json() == {"detail": "Email already registered"}


def test_register_validation(client):
    assert client.post("/api/v1/auth/register", json={**REG, "password": "short"}).status_code == 422
    assert client.post("/api/v1/auth/register", json={**REG, "email": "not-an-email"}).status_code == 422


def test_login_success_and_me(client):
    client.post("/api/v1/auth/register", json=REG)
    r = client.post("/api/v1/auth/login", data={"username": REG["email"], "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == REG["email"]


def test_login_wrong_password_is_401(client):
    client.post("/api/v1/auth/register", json=REG)
    r = client.post("/api/v1/auth/login", data={"username": REG["email"], "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["detail"] == "Incorrect email or password"


def test_me_requires_a_valid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_deactivated_user_cannot_log_in_or_use_old_token(db, client):
    u = make_user(db, "gone@example.com")
    headers = login(client, "gone@example.com")
    u.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401  # effective immediately
    r = client.post("/api/v1/auth/login", data={"username": "gone@example.com", "password": PASSWORD})
    assert r.status_code == 403


def test_profile_update_and_password_change(client, farmer):
    r = client.patch("/api/v1/users/me", headers=farmer, json={"name": "New Name", "phone": "01812345678"})
    assert r.status_code == 200 and r.json()["name"] == "New Name"
    bad = client.patch("/api/v1/users/me", headers=farmer, json={"current_password": "nope", "new_password": "AnotherPass1"})
    assert bad.status_code == 400
    ok = client.patch("/api/v1/users/me", headers=farmer, json={"current_password": PASSWORD, "new_password": "AnotherPass1"})
    assert ok.status_code == 200
    assert client.post("/api/v1/auth/login", data={"username": "farmer@example.com", "password": "AnotherPass1"}).status_code == 200
    assert client.patch("/api/v1/users/me", headers=farmer, json={"new_password": "OnlyNew12345"}).status_code == 422
