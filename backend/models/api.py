from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    session_id: str


class Source(BaseModel):
    entity_type: str
    entity_id: str
    name: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    message: str
    sources: list[Source]


class ChatSessionSummary(BaseModel):
    session_id: str
    created_at: datetime
    preview: str


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary]


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: list[Source]
    created_at: datetime


class ChatMessagesResponse(BaseModel):
    messages: list[ChatMessage]


class CreateSessionResponse(BaseModel):
    session_id: str
