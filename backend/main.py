import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from backend.agent.runner import run_turn
from backend.auth.dependencies import get_current_user_id
from backend.auth.service import InvalidCredentialsError, authenticate
from backend.config import get_settings
from backend.models.api import (
    ChatMessagesResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionListResponse,
    ChatSessionSummary,
    CreateSessionResponse,
    LoginRequest,
    LoginResponse,
)
from backend.repositories.firestore_repository import (
    add_chat_message,
    create_chat_session,
    get_chat_messages,
    get_chat_session,
    list_chat_sessions,
)

app = FastAPI(title="Elden Ring Agentic RAG Guide")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login_endpoint(payload: LoginRequest) -> LoginResponse:
    try:
        access_token, session_id = authenticate(payload.username, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        ) from exc
    return LoginResponse(access_token=access_token, session_id=session_id)


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    payload: ChatRequest, user_id: str = Depends(get_current_user_id)
) -> ChatResponse:
    # Messages/transcript are memory too (PRD §15.3) — filtered strictly by the
    # authenticated user_id, never trusted from the request payload (P-03 / AGENTS.md §2).
    session = get_chat_session(payload.session_id)
    if session is None:
        # Lazy creation: session_id came from /login or POST /sessions without ever
        # being persisted — only the first real message turns it into a saved
        # conversation, so logins/"nueva conversación" clicks with no follow-up
        # leave no empty chat_sessions doc behind.
        create_chat_session(user_id, session_id=payload.session_id)
    elif session.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    add_chat_message(payload.session_id, role="user", content=payload.message)
    message, sources = run_turn(user_id, payload.session_id, payload.message)
    add_chat_message(payload.session_id, role="assistant", content=message, sources=sources)
    return ChatResponse(message=message, sources=sources)


PREVIEW_MAX_LENGTH = 80


def _preview_for_session(session_id: str) -> str:
    for msg in get_chat_messages(session_id):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if len(content) > PREVIEW_MAX_LENGTH:
                return content[:PREVIEW_MAX_LENGTH].rstrip() + "…"
            return content
    return ""


@app.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions_endpoint(user_id: str = Depends(get_current_user_id)) -> ChatSessionListResponse:
    sessions = list_chat_sessions(user_id)
    return ChatSessionListResponse(
        sessions=[
            ChatSessionSummary(
                session_id=session["session_id"],
                created_at=session["created_at"],
                preview=_preview_for_session(session["session_id"]),
            )
            for session in sessions
        ]
    )


@app.get("/sessions/{session_id}/messages", response_model=ChatMessagesResponse)
def get_session_messages_endpoint(
    session_id: str, user_id: str = Depends(get_current_user_id)
) -> ChatMessagesResponse:
    session = get_chat_session(session_id)
    if session is None or session.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return ChatMessagesResponse(messages=get_chat_messages(session_id))


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session_endpoint(user_id: str = Depends(get_current_user_id)) -> CreateSessionResponse:
    # Not persisted here either — same lazy-creation rule as /login (see chat_endpoint).
    return CreateSessionResponse(session_id=str(uuid.uuid4()))


# Frontend estático servido por el mismo FastAPI (mismo origen que /login, /chat — sin CORS).
# Se monta al final para no tapar las rutas de API de arriba.
_frontend = Path(__file__).parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")


if __name__ == "__main__":
    import os

    import uvicorn

    get_settings()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
