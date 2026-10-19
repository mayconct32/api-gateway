"""Fluxos de usuário: cadastro, autenticação, consulta e autorização."""


def test_register_user(client):
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "Ana Lima",
            "email": "ana@example.com",
            "password": "s3cret-p4ss",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    # Hash da senha e role não vazam na resposta.
    assert "password" not in body
    assert "hashed_password" not in body
    assert body["role"] == "user"


def test_register_duplicate_email_conflict(client, user):
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "Maria Clone",
            "email": "maria@example.com",
            "password": "s3cret-p4ss",
        },
    )
    assert response.status_code == 409


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "X",
            "email": "not-an-email",
            "password": "s3cret-p4ss",
        },
    )
    assert response.status_code == 422


def test_register_short_password(client):
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "Curta",
            "email": "curta@example.com",
            "password": "1234567",
        },
    )
    assert response.status_code == 422


def test_login_success(client, user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "maria@example.com", "password": "s3cret-p4ss"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password(client, user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "maria@example.com", "password": "wrongpass123"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "ghost@example.com", "password": "s3cret-p4ss"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_me_returns_current_user(client, user):
    response = client.get("/api/v1/users/me", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == "maria@example.com"


def test_get_other_user_forbidden_for_common_user(client, user, another_user):
    response = client.get(
        f"/api/v1/users/{another_user['id']}", headers=user["headers"]
    )
    assert response.status_code == 403


def test_get_other_user_allowed_for_admin(client, admin, another_user):
    response = client.get(
        f"/api/v1/users/{another_user['id']}", headers=admin["headers"]
    )
    assert response.status_code == 200


def test_list_users_requires_admin(client, user):
    response = client.get("/api/v1/users", headers=user["headers"])
    assert response.status_code == 403


def test_list_users_as_admin(client, admin, user):
    response = client.get("/api/v1/users", headers=admin["headers"])
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert "maria@example.com" in emails


def test_update_own_name(client, user):
    response = client.patch(
        f"/api/v1/users/{user['id']}",
        json={"full_name": "Maria S. Silva"},
        headers=user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Maria S. Silva"


def test_update_other_user_forbidden(client, user, another_user):
    response = client.patch(
        f"/api/v1/users/{another_user['id']}",
        json={"full_name": "Hacked"},
        headers=user["headers"],
    )
    assert response.status_code == 403
