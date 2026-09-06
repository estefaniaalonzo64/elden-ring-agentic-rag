from __future__ import annotations

from typing import Any

from google.adk import Agent
from google.adk.models import Gemini
from google.genai import Client as GenAIClient

from backend.agent.instructions import SYSTEM_INSTRUCTION
from backend.config import get_settings
from backend.tools import memory as memory_tools
from backend.tools import rag as rag_tools

AGENT_NAME = "EldenRingGuideAgent"


def _build_llm() -> Gemini:
    settings = get_settings()
    client = GenAIClient(
        vertexai=True, project=settings.gcp_project_id, location=settings.vertex_location
    )
    return Gemini(model=settings.gemini_model, client=client)


def build_agent(user_id: str, sources_sink: list[dict[str, Any]]) -> Agent:
    """Builds a fresh EldenRingGuideAgent bound to one authenticated user.

    user_id is captured by closure here — it is never a parameter the LLM can
    fill in (PRD §12.4 / AGENTS.md §2), and sources_sink lets the caller collect
    everything search_elden_ring_knowledge returned during the turn without
    depending on ADK's internal callback wire format.
    """

    def get_player_profile() -> dict[str, Any]:
        """Returns the current player's persistent preferences and stats."""
        return memory_tools.get_player_profile(user_id)

    def update_player_memory(
        preferences_patch: dict[str, Any] | None = None,
        stats_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Saves or corrects stable preferences/stats detected in the conversation."""
        return memory_tools.update_player_memory(user_id, preferences_patch, stats_patch)

    def forget_player_memory(fields: list[str]) -> dict[str, Any]:
        """Forgets specific player-profile fields (dotted path, e.g. 'preferences.playstyle')."""
        return memory_tools.forget_player_memory(user_id, fields)

    def search_elden_ring_knowledge(
        query: str,
        top_k: int | None = None,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieves evidence from the Elden Ring corpus by semantic similarity (armor, weapon, boss, incantation, ash, npc)."""
        results = rag_tools.search_elden_ring_knowledge(
            query, top_k=top_k, entity_types=entity_types
        )
        dumped = [result.model_dump() for result in results]
        sources_sink.extend(dumped)
        return dumped

    return Agent(
        name=AGENT_NAME,
        model=_build_llm(),
        instruction=SYSTEM_INSTRUCTION,
        tools=[
            search_elden_ring_knowledge,
            get_player_profile,
            update_player_memory,
            forget_player_memory,
        ],
    )
