from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gcp_project_id: str = "ah-estefania-alozno"

    bq_location: str = "US"
    bq_gold_dataset: str = "elden_ring_gold"
    bq_semantic_documents_table: str = "semantic_documents"
    bq_vertex_embeddings_table: str = "entity_embeddings_vertex"
    bq_vertex_remote_model: str = ""

    vertex_embedding_model: str = ""
    vertex_embedding_dimension: int = 768

    gemini_model: str = ""
    vertex_location: str = ""

    jwt_secret: str = "dev-secret-change-me"
    jwt_ttl_minutes: int = 480

    firestore_database: str = "(default)"

    rag_top_k: int = 8
    recommendation_count: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
