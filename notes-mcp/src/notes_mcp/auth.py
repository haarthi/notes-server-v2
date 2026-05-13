"""OAuth 2.0 + PKCE — trust-all stubs.

Implements the surface area claude.ai needs to add a remote MCP connector:
  - GET  /.well-known/oauth-authorization-server  (RFC 8414 discovery)
  - POST /register                                 (RFC 7591 dynamic client registration)
  - GET  /authorize                                (no consent UI — immediate redirect with code)
  - POST /token                                    (PKCE verify + bearer issue)

Trust-all semantics:
  - any registration succeeds
  - any authorize request issues a code
  - any token exchange succeeds *iff* the PKCE verifier hashes to the stored challenge

This is enough to satisfy claude.ai's flow without standing up a real user
store. The PKCE check is real (S256 hash) because that's the only thing the
client-side flow actually validates against on the server.

Multi-user auth, token revocation, scope enforcement: out of scope for M1.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from starlette.responses import JSONResponse, RedirectResponse

from notes_mcp.config import Settings

# ----- In-memory stores --------------------------------------------------------
#
# Reset on restart. Acceptable for a personal instance since claude.ai
# re-issues tokens via the OAuth flow whenever they go missing.


@dataclass
class PendingCode:
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    expires_at: float


@dataclass
class _Stores:
    codes: dict[str, PendingCode] = field(default_factory=dict)
    tokens: set[str] = field(default_factory=set)
    # Trust-all: we don't actually use client metadata, just record the IDs.
    clients: dict[str, dict] = field(default_factory=dict)


_stores = _Stores()


# ----- PKCE -------------------------------------------------------------------


def verify_pkce_s256(verifier: str, challenge: str) -> bool:
    """RFC 7636: challenge = base64url(SHA256(verifier)), no padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(expected, challenge)


# ----- Bearer middleware helper -----------------------------------------------


def require_bearer(request: Request) -> str | None:
    """Return None if the request carries a valid bearer; an error string otherwise."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return "missing bearer token"
    token = auth.split(" ", 1)[1].strip()
    if token not in _stores.tokens:
        return "invalid bearer token"
    return None


def issue_token() -> str:
    token = secrets.token_urlsafe(32)
    _stores.tokens.add(token)
    return token


# ----- Routes -----------------------------------------------------------------


def build_auth_router(settings: Settings) -> APIRouter:
    router = APIRouter()
    issuer = f"http://{settings.host}:{settings.port}"

    @router.get("/.well-known/oauth-authorization-server")
    def discovery(request: Request) -> dict:
        # Use the request's actual base URL so tunnel / localhost both work.
        base = str(request.base_url).rstrip("/")
        return {
            "issuer": base,
            "authorization_endpoint": f"{base}/authorize",
            "token_endpoint": f"{base}/token",
            "registration_endpoint": f"{base}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }

    @router.post("/register")
    def register(payload: dict) -> dict:
        """Dynamic client registration — accepts any metadata."""
        client_id = f"client_{uuid.uuid4().hex[:16]}"
        _stores.clients[client_id] = payload
        return {
            "client_id": client_id,
            "client_id_issued_at": int(time.time()),
            "token_endpoint_auth_method": "none",
            **payload,  # echo back redirect_uris, client_name, etc.
        }

    @router.get("/authorize")
    def authorize(
        client_id: str,
        redirect_uri: str,
        response_type: str = "code",
        code_challenge: str = "",
        code_challenge_method: str = "S256",
        state: str | None = None,
        scope: str | None = None,
    ):
        if response_type != "code":
            raise HTTPException(400, f"unsupported response_type: {response_type}")
        if code_challenge_method != "S256":
            raise HTTPException(400, "only S256 PKCE is supported")
        if not code_challenge:
            raise HTTPException(400, "code_challenge is required")

        code = secrets.token_urlsafe(24)
        _stores.codes[code] = PendingCode(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=time.time() + 300,  # 5 min
        )
        sep = "&" if "?" in redirect_uri else "?"
        target = f"{redirect_uri}{sep}code={code}"
        if state:
            target += f"&state={state}"
        return RedirectResponse(target, status_code=302)

    @router.post("/token")
    def token(
        grant_type: Annotated[str, Form()],
        code: Annotated[str, Form()],
        redirect_uri: Annotated[str, Form()],
        client_id: Annotated[str, Form()],
        code_verifier: Annotated[str, Form()],
    ):
        if grant_type != "authorization_code":
            return JSONResponse(
                {"error": "unsupported_grant_type"}, status_code=400
            )
        pending = _stores.codes.pop(code, None)
        if pending is None:
            return JSONResponse({"error": "invalid_grant"}, status_code=400)
        if pending.expires_at < time.time():
            return JSONResponse({"error": "invalid_grant", "error_description": "expired"}, status_code=400)
        if pending.redirect_uri != redirect_uri or pending.client_id != client_id:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "redirect/client mismatch"},
                status_code=400,
            )
        if not verify_pkce_s256(code_verifier, pending.code_challenge):
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "pkce mismatch"},
                status_code=400,
            )
        return {
            "access_token": issue_token(),
            "token_type": "Bearer",
            "expires_in": 60 * 60 * 24 * 30,  # 30 days; we don't expire in-memory anyway
        }

    return router


# ----- Test helpers -----------------------------------------------------------
#
# Tests call these to inspect/reset the in-memory state.


def _reset_for_tests() -> None:
    _stores.codes.clear()
    _stores.tokens.clear()
    _stores.clients.clear()


def _inject_token_for_tests(token: str) -> None:
    _stores.tokens.add(token)
