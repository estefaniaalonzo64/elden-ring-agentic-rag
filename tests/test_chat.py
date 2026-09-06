import pytest
from fastapi import HTTPException

from backend import main
from backend.models.api import ChatRequest


@pytest.fixture
def fake_chat_backend(monkeypatch):
    sessions = {"session-a": {"session_id": "session-a", "user_id": "user-a"}}
    messages: list[dict] = []

    def fake_get_chat_session(session_id):
        return sessions.get(session_id)

    def fake_add_chat_message(session_id, role, content, sources=None):
        messages.append(
            {"session_id": session_id, "role": role, "content": content, "sources": sources or []}
        )
        return f"msg-{len(messages)}"

    def fake_run_turn(user_id, session_id, message):
        return f"echo: {message}", [
            {"entity_type": "weapon", "entity_id": "moonveil", "name": "Moonveil"}
        ]

    monkeypatch.setattr(main, "get_chat_session", fake_get_chat_session)
    monkeypatch.setattr(main, "add_chat_message", fake_add_chat_message)
    monkeypatch.setattr(main, "run_turn", fake_run_turn)

    return messages


def test_chat_persists_user_and_assistant_messages_with_sources(fake_chat_backend):
    response = main.chat_endpoint(
        ChatRequest(session_id="session-a", message="hola"), user_id="user-a"
    )

    assert response.message == "echo: hola"
    assert [m["role"] for m in fake_chat_backend] == ["user", "assistant"]
    assert fake_chat_backend[0]["content"] == "hola"
    assert fake_chat_backend[1]["content"] == "echo: hola"
    assert fake_chat_backend[1]["sources"][0]["name"] == "Moonveil"


def test_chat_rejects_session_belonging_to_another_user(fake_chat_backend):
    with pytest.raises(HTTPException) as exc_info:
        main.chat_endpoint(ChatRequest(session_id="session-a", message="hola"), user_id="user-b")
    assert exc_info.value.status_code == 404
    assert fake_chat_backend == []


def test_chat_rejects_unknown_session(fake_chat_backend):
    with pytest.raises(HTTPException) as exc_info:
        main.chat_endpoint(
            ChatRequest(session_id="does-not-exist", message="hola"), user_id="user-a"
        )
    assert exc_info.value.status_code == 404
