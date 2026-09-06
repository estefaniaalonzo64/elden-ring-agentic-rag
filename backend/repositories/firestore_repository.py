from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from google.cloud import firestore

from backend.config import get_settings


@lru_cache
def get_firestore_client() -> firestore.Client:
    settings = get_settings()
    return firestore.Client(project=settings.gcp_project_id, database=settings.firestore_database)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def get_user_by_username(username: str) -> dict[str, Any] | None:
    doc = get_firestore_client().collection("users").document(normalize_username(username)).get()
    return doc.to_dict() if doc.exists else None


def create_user(username: str, password_hash: str, password_salt: str) -> str:
    user_id = str(uuid.uuid4())
    get_firestore_client().collection("users").document(normalize_username(username)).set(
        {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "password_salt": password_salt,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return user_id


def create_chat_session(user_id: str, session_id: str | None = None) -> str:
    # Called lazily on the first real message (backend/main.py:chat_endpoint), not at
    # login/POST /sessions time — a session_id handed to the client is only worth
    # persisting once there is an actual interaction to attach to it.
    session_id = session_id or str(uuid.uuid4())
    get_firestore_client().collection("chat_sessions").document(session_id).set(
        {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "status": "active",
        }
    )
    return session_id


def get_chat_session(session_id: str) -> dict[str, Any] | None:
    doc = get_firestore_client().collection("chat_sessions").document(session_id).get()
    return doc.to_dict() if doc.exists else None


def list_chat_sessions(user_id: str) -> list[dict[str, Any]]:
    # Sorted in Python, not via Firestore order_by(), to avoid requiring a
    # manually-provisioned composite index (user_id ==, created_at) for what
    # is at most a few dozen documents per user (P-05 cost conscious).
    query = get_firestore_client().collection("chat_sessions").where("user_id", "==", user_id)
    sessions = [doc.to_dict() for doc in query.stream()]
    sessions.sort(key=lambda session: session["created_at"], reverse=True)
    return sessions


def get_chat_messages(session_id: str) -> list[dict[str, Any]]:
    query = (
        get_firestore_client()
        .collection("chat_sessions")
        .document(session_id)
        .collection("messages")
        .order_by("created_at", direction=firestore.Query.ASCENDING)
    )
    return [doc.to_dict() for doc in query.stream()]


def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> str:
    message_ref = (
        get_firestore_client()
        .collection("chat_sessions")
        .document(session_id)
        .collection("messages")
        .document()
    )
    message_ref.set(
        {
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc),
            "sources": sources or [],
        }
    )
    return message_ref.id


def get_player_profile(user_id: str) -> dict[str, Any]:
    doc = get_firestore_client().collection("player_profiles").document(user_id).get()
    if not doc.exists:
        return {"preferences": {}, "stats": {}}
    data = doc.to_dict() or {}
    return {"preferences": data.get("preferences", {}), "stats": data.get("stats", {})}


def update_player_profile(user_id: str, preferences_patch: dict[str, Any], stats_patch: dict[str, Any]) -> None:
    # Dotted field paths only merge nested maps surgically via update() — set(merge=True)
    # stores dotted strings as literal (non-nested) field names instead of resolving the path.
    updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
    for key, value in preferences_patch.items():
        updates[f"preferences.{key}"] = value
    for key, value in stats_patch.items():
        updates[f"stats.{key}"] = value
    doc_ref = get_firestore_client().collection("player_profiles").document(user_id)
    doc_ref.set({}, merge=True)  # ensure the doc exists — update() errors on a missing doc
    doc_ref.update(updates)


def forget_player_fields(user_id: str, fields: list[str]) -> None:
    updates: dict[str, Any] = {field: firestore.DELETE_FIELD for field in fields}
    updates["updated_at"] = datetime.now(timezone.utc)
    doc_ref = get_firestore_client().collection("player_profiles").document(user_id)
    doc_ref.set({}, merge=True)
    doc_ref.update(updates)
