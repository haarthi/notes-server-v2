"""Integration: /health endpoint smoke."""

from __future__ import annotations


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["categories_loaded"] >= 1
    assert "version" in body


def test_health_unauthenticated_is_fine(client):
    # /health should be reachable without a bearer.
    r = client.get("/health", headers={})
    assert r.status_code == 200
