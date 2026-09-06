from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt

from backend.config import get_settings
from backend.repositories.firestore_repository import (
    create_chat_session,
    create_user,
    get_user_by_username,
)

PBKDF2_ITERATIONS = 260_000
JWT_ALGORITHM = "HS256"


class UsernameTakenError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS).hex()


def register(username: str, password: str) -> None:
    if get_user_by_username(username) is not None:
        raise UsernameTakenError(username)

    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)
    create_user(username=username, password_hash=password_hash, password_salt=salt.hex())


def authenticate(username: str, password: str) -> tuple[str, str]:
    user = get_user_by_username(username)
    if user is None:
        raise InvalidCredentialsError(username)

    salt = bytes.fromhex(user["password_salt"])
    if _hash_password(password, salt) != user["password_hash"]:
        raise InvalidCredentialsError(username)

    user_id = user["user_id"]
    token = _create_token(user_id)
    session_id = create_chat_session(user_id)
    return token, session_id


def _create_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    return payload["user_id"]
