from __future__ import annotations

from typing import Any

from backend.repositories.firestore_repository import forget_player_fields as _forget_player_fields
from backend.repositories.firestore_repository import get_player_profile as _get_player_profile
from backend.repositories.firestore_repository import update_player_profile as _update_player_profile

# These take user_id as an explicit argument here; when registered as ADK tools (Fase 5) the
# runtime must bind user_id from the authenticated request context (e.g. functools.partial),
# never expose it as a parameter the LLM can fill in (PRD §12.4 / AGENTS.md §2).


def get_player_profile(user_id: str) -> dict[str, Any]:
    return _get_player_profile(user_id)


def update_player_memory(
    user_id: str,
    preferences_patch: dict[str, Any] | None = None,
    stats_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _update_player_profile(user_id, preferences_patch or {}, stats_patch or {})
    return _get_player_profile(user_id)


def forget_player_memory(user_id: str, fields: list[str]) -> dict[str, Any]:
    _forget_player_fields(user_id, fields)
    return _get_player_profile(user_id)
