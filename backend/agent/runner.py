from __future__ import annotations

from functools import lru_cache
from typing import Any

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.agent.agent import build_agent

APP_NAME = "elden-ring-agent"


@lru_cache
def get_session_service() -> InMemorySessionService:
    # In-memory on purpose (PRD §15.2): the ADK conversational session resets on
    # every login/process restart. Persistent memory lives in Firestore instead.
    return InMemorySessionService()


def _dedupe_sources(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    sources: list[dict[str, Any]] = []
    for entity in entities:
        key = (entity["entity_type"], entity["entity_id"])
        if key in seen:
            continue
        seen.add(key)
        # No mostrar score/distancia/embeddings al usuario (PRD §20).
        sources.append(
            {
                "entity_type": entity["entity_type"],
                "entity_id": entity["entity_id"],
                "name": entity["name"],
            }
        )
    return sources


def run_turn(user_id: str, session_id: str, message: str) -> tuple[str, list[dict[str, Any]]]:
    sources_sink: list[dict[str, Any]] = []
    agent = build_agent(user_id, sources_sink)
    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=get_session_service(),
        auto_create_session=True,
    )

    new_message = types.Content(role="user", parts=[types.Part(text=message)])

    final_text = ""
    for event in runner.run(user_id=user_id, session_id=session_id, new_message=new_message):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text for part in event.content.parts if part.text)

    return final_text, _dedupe_sources(sources_sink)
