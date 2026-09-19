import uuid

from app.core.security import create_access_token, hash_password, read_access_token, verify_password


def test_password_hash_is_salted_and_verifiable() -> None:
    password = "strong-password-123"
    first = hash_password(password)
    second = hash_password(password)

    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("wrong-password", first)


def test_token_rejects_tampering(monkeypatch) -> None:
    monkeypatch.setenv("LOADFORGE_TOKEN_SECRET", "test-only-secret-value-with-at-least-32-bytes")
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    assert read_access_token(token) == user_id
    replacement = "a" if token[-1] != "a" else "b"
    assert read_access_token(token[:-1] + replacement) is None


def test_short_token_secret_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("LOADFORGE_TOKEN_SECRET", "too-short")

    try:
        create_access_token(uuid.uuid4())
    except RuntimeError as exc:
        assert "at least 32 bytes" in str(exc)
    else:
        raise AssertionError("A short token secret was accepted")
