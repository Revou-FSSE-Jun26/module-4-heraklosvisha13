from datetime import timedelta

import jwt as pyjwt
from flask_jwt_extended import create_access_token

from conftest import PASSWORD, auth_headers, make_user

VALID = {"name": "Dana", "email": "dana@example.com", "password": PASSWORD}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**VALID, **overrides})


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {"data": {"status": "ok"}}


class TestRegister:
    def test_success_returns_public_user(self, client):
        res = register(client)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["email"] == "dana@example.com"
        assert data["name"] == "Dana"
        assert "id" in data
        assert "password" not in data and "password_hash" not in data

    def test_email_is_normalized(self, client):
        res = register(client, email="Dana@Example.COM")
        assert res.status_code == 201
        assert res.get_json()["data"]["email"] == "dana@example.com"

    def test_duplicate_email_is_400(self, client):
        assert register(client).status_code == 201
        res = register(client, email="DANA@example.com")
        assert res.status_code == 400
        assert isinstance(res.get_json()["error"], str)

    def test_missing_fields_are_400(self, client):
        for field in ("name", "email", "password"):
            payload = {k: v for k, v in VALID.items() if k != field}
            res = client.post("/api/auth/register", json=payload)
            assert res.status_code == 400, field
            assert field in res.get_json()["error"]

    def test_invalid_email_is_400(self, client):
        assert register(client, email="not-an-email").status_code == 400

    def test_short_password_is_400(self, client):
        assert register(client, password="short").status_code == 400

    def test_empty_body_is_400(self, client):
        assert client.post("/api/auth/register").status_code == 400


class TestLogin:
    def test_success_returns_token_that_works(self, client):
        register(client)
        res = client.post(
            "/api/auth/login", json={"email": "dana@example.com", "password": PASSWORD}
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["access_token"]
        assert data["user"]["email"] == "dana@example.com"

        me = client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {data['access_token']}"}
        )
        assert me.status_code == 200

    def test_email_is_case_insensitive(self, client):
        register(client)
        res = client.post(
            "/api/auth/login", json={"email": "DANA@example.com", "password": PASSWORD}
        )
        assert res.status_code == 200

    def test_wrong_password_is_401(self, client):
        register(client)
        res = client.post(
            "/api/auth/login", json={"email": "dana@example.com", "password": "wrong-pass"}
        )
        assert res.status_code == 401
        assert res.get_json() == {"error": "Invalid email or password"}

    def test_unknown_email_gives_same_401(self, client):
        res = client.post(
            "/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
        )
        assert res.status_code == 401
        assert res.get_json() == {"error": "Invalid email or password"}

    def test_missing_fields_are_400(self, client):
        assert client.post("/api/auth/login", json={"email": "a@b.co"}).status_code == 400
        assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 400


class TestProtectedRoutes:
    def test_no_token_is_401(self, client):
        res = client.get("/api/users/me")
        assert res.status_code == 401
        assert isinstance(res.get_json()["error"], str)

    def test_garbage_token_is_401(self, client):
        res = client.get("/api/users/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert res.status_code == 401

    def test_token_signed_with_other_secret_is_401(self, client, alice):
        forged = pyjwt.encode({"sub": alice.id, "type": "access"}, "x" * 40, algorithm="HS256")
        res = client.get("/api/users/me", headers={"Authorization": f"Bearer {forged}"})
        assert res.status_code == 401

    def test_expired_token_is_401(self, app, client, alice):
        token = create_access_token(identity=alice.id, expires_delta=timedelta(seconds=-1))
        res = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "expired" in res.get_json()["error"].lower()


class TestCurrentUser:
    def test_get_me(self, client, alice, alice_h):
        res = client.get("/api/users/me", headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["id"] == alice.id

    def test_update_name(self, client, alice_h):
        res = client.patch("/api/users/me", json={"name": "Alicia"}, headers=alice_h)
        assert res.status_code == 200
        assert res.get_json()["data"]["name"] == "Alicia"

    def test_update_email_to_taken_is_400(self, client, alice_h, bob):
        res = client.patch("/api/users/me", json={"email": bob.email}, headers=alice_h)
        assert res.status_code == 400

    def test_update_empty_body_is_400(self, client, alice_h):
        assert client.patch("/api/users/me", json={}, headers=alice_h).status_code == 400

    def test_token_of_deleted_user_is_rejected(self, client, app):
        user = make_user("Gone")
        headers = auth_headers(user)
        user.soft_delete()
        from app.extensions import db

        db.session.commit()
        res = client.get("/api/users/me", headers=headers)
        assert res.status_code in (401, 404)
