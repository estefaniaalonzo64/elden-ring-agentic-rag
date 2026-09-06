from __future__ import annotations

from backend.config import get_settings
from backend.models.rag import RetrievedEntity
from backend.repositories.bigquery_repository import generate_query_embedding, vector_search


def search_elden_ring_knowledge(
    query: str,
    top_k: int | None = None,
    entity_types: list[str] | None = None,
) -> list[RetrievedEntity]:
    if not query or not query.strip():
        return []

    effective_top_k = top_k or get_settings().rag_top_k

    query_embedding = generate_query_embedding(query)
    rows = vector_search(query_embedding, top_k=effective_top_k, entity_types=entity_types)

    return [
        RetrievedEntity(
            rank=rank,
            score=(1.0 - row["distance"]) if row["distance"] is not None else None,
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            name=row["name"],
            searchable_text=row["searchable_text"],
        )
        for rank, row in enumerate(rows, start=1)
    ]
