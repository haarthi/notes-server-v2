"""Unit tests for PKCE S256 verification."""

from __future__ import annotations

import base64
import hashlib

from notes_mcp.auth import verify_pkce_s256


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def test_pkce_valid_pair():
    verifier = "a" * 64
    assert verify_pkce_s256(verifier, _challenge(verifier))


def test_pkce_mismatch():
    verifier = "a" * 64
    other = "b" * 64
    assert not verify_pkce_s256(verifier, _challenge(other))


def test_pkce_real_world_pair():
    # Example from RFC 7636 § 4.2
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert verify_pkce_s256(verifier, expected)
