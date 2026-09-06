import jwt
import pytest
from fastapi import HTTPException

from backend.auth import dependencies, service


def test_register_valid(fake_users_db):
    service.register("Fany", "s3cret-pass")
    assert "fany" in fake_users_db


def test_register_duplicate_username(fake_users_db):
    service.register("fany", "s3cret-pass")
    with pytest.raises(service.UsernameTakenError):
        service.register("Fany", "another-pass")


def test_login_wrong_password(fake_users_db):
    service.register("fany", "correct-pass")
    with pytest.raises(service.InvalidCredentialsError):
        service.authenticate("fany", "wrong-pass")


def test_login_success_returns_token_and_session(fake_users_db):
    service.register("fany", "correct-pass")
    token, session_id = service.authenticate("fany", "correct-pass")

    assert token
    assert session_id
    assert service.decode_token(token) == fake_users_db["fany"]["user_id"]


def test_decode_token_invalid_raises():
    with pytest.raises(jwt.PyJWTError):
        service.decode_token("not-a-real-token")


def test_get_current_user_id_missing_token_raises():
    with pytest.raises(HTTPException):
        dependencies.get_current_user_id(credentials=None)
