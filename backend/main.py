from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from backend.agent.runner import run_turn
from backend.auth.dependencies import get_current_user_id
from backend.auth.service import InvalidCredentialsError, authenticate
from backend.config import get_settings
from backend.models.api import ChatRequest, ChatResponse, LoginRequest, LoginResponse
from backend.repositories.firestore_repository import add_chat_message, get_chat_session

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
    if session is None or session.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    add_chat_message(payload.session_id, role="user", content=payload.message)
    message, sources = run_turn(user_id, payload.session_id, payload.message)
    add_chat_message(payload.session_id, role="assistant", content=message, sources=sources)
    return ChatResponse(message=message, sources=sources)


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
