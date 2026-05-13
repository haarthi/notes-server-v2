"""Integration: full OAuth flow + PKCE round-trip + bearer enforcement."""

from __future__ import annotations

import base64
import hashlib
import re
import secrets


def _make_pkce():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def test_discovery(client):
    r = client.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    body = r.json()
    assert body["authorization_endpoint"].endswith("/authorize")
    assert body["token_endpoint"].endswith("/token")
    assert body["registration_endpoint"].endswith("/register")
    assert "S256" in body["code_challenge_methods_supported"]


def test_full_oauth_flow_and_bearer(client):
    # 1. Register a client.
    r = client.post("/register", json={"redirect_uris": ["http://example/cb"], "client_name": "claude.ai"})
    assert r.status_code == 200, r.text
    client_id = r.json()["client_id"]
    assert client_id.startswith("client_")

    # 2. Authorize with PKCE.
    verifier, challenge = _make_pkce()
    r = client.get(
        "/authorize",
        params={
            "client_id": client_id,
            "redirect_uri": "http://example/cb",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "xyz",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    loc = r.headers["location"]
    code = re.search(r"code=([^&]+)", loc).group(1)
    assert "state=xyz" in loc

    # 3. Exchange code for token.
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://example/cb",
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert r.json()["token_type"] == "Bearer"

    # 4. MCP without bearer → 401.
    r = client.get("/mcp/")
    assert r.status_code == 401

    # 5. MCP with bogus bearer → 401.
    r = client.get("/mcp/", headers={"authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401

    # 6. MCP with real bearer → not 401 (transport-specific status; we only assert auth passed).
    r = client.get("/mcp/", headers={"authorization": f"Bearer {token}"})
    assert r.status_code != 401


def test_pkce_mismatch_rejected(client):
    r = client.post("/register", json={"client_name": "x"})
    client_id = r.json()["client_id"]
    _, challenge = _make_pkce()
    r = client.get(
        "/authorize",
        params={
            "client_id": client_id,
            "redirect_uri": "http://example/cb",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    code = re.search(r"code=([^&]+)", r.headers["location"]).group(1)

    # Send the wrong verifier — should be rejected.
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://example/cb",
            "client_id": client_id,
            "code_verifier": "wrong-verifier-totally",
        },
    )
    assert r.status_code == 400
    assert "pkce" in r.json()["error_description"].lower()
