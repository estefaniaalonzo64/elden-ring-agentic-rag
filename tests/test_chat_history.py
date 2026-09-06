from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from google.cloud import firestore as firestore_module

from backend import main
from backend.repositories import firestore_repository


class _FakeDoc:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    def where(self, field, op, value):
        assert op == "=="
        return _FakeQuery([d for d in self._docs if d.get(field) == value])

    def order_by(self, field, direction=None):
        reverse = direction == firestore_module.Query.DESCENDING
        return _FakeQuery(sorted(self._docs, key=lambda d: d[field], reverse=reverse))

    def stream(self):
        return [_FakeDoc(d) for d in self._docs]


class _FakeSessionDocRef:
    def __init__(self, messages):
        self._messages = messages

    def collection(self, name):
        assert name == "messages"
        return _FakeQuery(self._messages)


class _FakeChatSessionsCollection(_FakeQuery):
    def __init__(self, sessions, messages_by_session):
        super().__init__(list(sessions))
        self._messages_by_session = messages_by_session

    def document(self, session_id):
        return _FakeSessionDocRef(self._messages_by_session.get(session_id, []))


class _FakeFirestoreClient:
    def __init__(self, sessions, messages_by_session=None):
        self._sessions = sessions
        self._messages_by_session = messages_by_session or {}

    def collection(self, name):
        assert name == "chat_sessions"
        return _FakeChatSessionsCollection(self._sessions, self._messages_by_session)


def test_list_chat_sessions_filters_by_user_and_orders_desc(monkeypatch):
    sessions = [
        {"session_id": "s1", "user_id": "user-a", "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        {"session_id": "s2", "user_id": "user-a", "created_at": datetime(2026, 1, 3, tzinfo=timezone.utc)},
        {"session_id": "s3", "user_id": "user-b", "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)},
    ]
    monkeypatch.setattr(
        firestore_repository, "get_firestore_client", lambda: _FakeFirestoreClient(sessions)
    )

    result = firestore_repository.list_chat_sessions("user-a")

    assert [s["session_id"] for s in result] == ["s2", "s1"]


def test_get_chat_messages_orders_ascending(monkeypatch):
    messages = [
        {"role": "assistant", "content": "b", "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)},
        {"role": "user", "content": "a", "created_at": datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)},
    ]
    monkeypatch.setattr(
        firestore_repository,
        "get_firestore_client",
        lambda: _FakeFirestoreClient([], {"s1": messages}),
    )

    result = firestore_repository.get_chat_messages("s1")

    assert [m["content"] for m in result] == ["a", "b"]


@pytest.fixture
def fake_sessions_backend(monkeypatch):
    sessions = {
        "session-a": {"session_id": "session-a", "user_id": "user-a", "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        "session-b": {"session_id": "session-b", "user_id": "user-b", "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)},
    }
    messages_by_session = {
        "session-a": [
            {"role": "user", "content": "hola", "sources": [], "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"role": "assistant", "content": "hola!", "sources": [], "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        ],
        "session-b": [],
    }
    created: list[str] = []

    def fake_get_chat_session(session_id):
        return sessions.get(session_id)

    def fake_list_chat_sessions(user_id):
        return [s for s in sessions.values() if s["user_id"] == user_id]

    def fake_get_chat_messages(session_id):
        return messages_by_session.get(session_id, [])

    def fake_create_chat_session(user_id):
        session_id = f"session-new-{len(created) + 1}"
        created.append(session_id)
        sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime(2026, 1, 3, tzinfo=timezone.utc),
        }
        return session_id

    monkeypatch.setattr(main, "get_chat_session", fake_get_chat_session)
    monkeypatch.setattr(main, "list_chat_sessions", fake_list_chat_sessions)
    monkeypatch.setattr(main, "get_chat_messages", fake_get_chat_messages)
    monkeypatch.setattr(main, "create_chat_session", fake_create_chat_session)

    return {"sessions": sessions, "messages_by_session": messages_by_session, "created": created}


def test_list_sessions_returns_only_own_sessions_with_preview(fake_sessions_backend):
    response = main.list_sessions_endpoint(user_id="user-a")

    assert [s.session_id for s in response.sessions] == ["session-a"]
    assert response.sessions[0].preview == "hola"


def test_list_sessions_for_user_with_no_sessions_is_empty(fake_sessions_backend):
    response = main.list_sessions_endpoint(user_id="user-c")

    assert response.sessions == []


def test_get_session_messages_returns_own_transcript(fake_sessions_backend):
    response = main.get_session_messages_endpoint("session-a", user_id="user-a")

    assert [m.content for m in response.messages] == ["hola", "hola!"]


def test_get_session_messages_rejects_other_users_session(fake_sessions_backend):
    with pytest.raises(HTTPException) as exc_info:
        main.get_session_messages_endpoint("session-b", user_id="user-a")
    assert exc_info.value.status_code == 404


def test_get_session_messages_rejects_unknown_session(fake_sessions_backend):
    with pytest.raises(HTTPException) as exc_info:
        main.get_session_messages_endpoint("does-not-exist", user_id="user-a")
    assert exc_info.value.status_code == 404


def test_create_session_returns_a_fresh_id_without_persisting_it(fake_sessions_backend):
    # POST /sessions only hands out an id — it's not saved until the first real
    # message goes through /chat (chat_endpoint's lazy creation), so a "nueva
    # conversación" click with no follow-up leaves no empty chat_sessions doc.
    response = main.create_session_endpoint(user_id="user-a")

    assert response.session_id
    assert response.session_id not in fake_sessions_backend["sessions"]
