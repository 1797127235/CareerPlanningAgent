"""Tests for auth + app route wiring."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app, raise_server_exceptions=False)


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestAuth:
    def test_register_new_user(self):
        username = _unique("reg")
        r = client.post(
            "/api/auth/register",
            json={"username": username, "password": "test123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "id" in body["data"]
        assert body["data"]["username"] == username

    def test_register_duplicate(self):
        username = _unique("dup")
        client.post(
            "/api/auth/register",
            json={"username": username, "password": "pass"},
        )
        r = client.post(
            "/api/auth/register",
            json={"username": username, "password": "pass"},
        )
        assert r.status_code == 400

    def test_login(self):
        username = _unique("login")
        client.post(
            "/api/auth/register",
            json={"username": username, "password": "pass123"},
        )
        r = client.post(
            "/api/auth/login",
            json={"username": username, "password": "pass123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "token" in body["data"]
        assert body["data"]["user"]["username"] == username

    def test_login_wrong_password(self):
        username = _unique("wrong")
        client.post(
            "/api/auth/register",
            json={"username": username, "password": "correct"},
        )
        r = client.post(
            "/api/auth/login",
            json={"username": username, "password": "incorrect"},
        )
        assert r.status_code == 401

    def test_me_without_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_with_token(self):
        username = _unique("me")
        client.post(
            "/api/auth/register",
            json={"username": username, "password": "pass123"},
        )
        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": "pass123"},
        )
        token = login.json()["data"]["token"]
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "id" in body["data"]
        assert body["data"]["username"] == username


class TestAppRoutes:
    def test_app_has_routes(self):
        route_paths = [r.path for r in app.routes]
        assert "/api/auth/login" in route_paths
        assert "/api/auth/register" in route_paths
        assert "/api/auth/me" in route_paths
        assert "/api/chat/" in route_paths
        assert "/api/chat/stream" in route_paths
        assert "/api/graph/map" in route_paths
        assert "/api/profiles/" in route_paths
        assert "/api/jd/diagnose" in route_paths
        assert "/api/report/" in route_paths
        assert "/api/dashboard/stats" in route_paths
        assert "/api/practice/analyze" in route_paths

    def test_unauthenticated_graph_map(self):
        """Graph map should require auth."""
        r = client.get("/api/graph/map")
        assert r.status_code == 401
