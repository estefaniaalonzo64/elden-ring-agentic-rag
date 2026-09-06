from pydantic import BaseModel


class RetrievedEntity(BaseModel):
    rank: int
    score: float | None
    entity_type: str
    entity_id: str
    name: str
    searchable_text: str
