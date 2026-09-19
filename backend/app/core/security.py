"""Password hashing and short-lived signed access tokens."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid


ITERATIONS = 600_000
TOKEN_LIFETIME_SECONDS = 8 * 60 * 60


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, count, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(count) != ITERATIONS:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt), ITERATIONS
        )
        return hmac.compare_digest(digest, _decode(expected))
    except (ValueError, TypeError):
        return False


def _token_secret() -> bytes:
    secret = os.getenv("LOADFORGE_TOKEN_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise RuntimeError("LOADFORGE_TOKEN_SECRET must contain at least 32 bytes")
    return secret


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {"sub": str(user_id), "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    body = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _encode(hmac.new(_token_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def read_access_token(token: str) -> uuid.UUID | None:
    if len(token) > 4096:
        return None
    try:
        body, signature = token.split(".")
        expected = _encode(
            hmac.new(_token_secret(), body.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_decode(body))
        if not isinstance(payload, dict) or not isinstance(payload.get("exp"), int):
            return None
        if payload["exp"] <= time.time():
            return None
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        return None
