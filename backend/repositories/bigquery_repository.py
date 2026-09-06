from __future__ import annotations

from functools import lru_cache
from typing import Any

from google.cloud import bigquery

from backend.config import get_settings

# Fija en el handoff (VERTEX_RAG_HANDOFF.md §7/§11): comparte versión de plantilla con
# semantic_documents, no es un parámetro de despliegue configurable por entorno.
TEMPLATE_VERSION = "v1"


@lru_cache
def get_bigquery_client() -> bigquery.Client:
    settings = get_settings()
    return bigquery.Client(project=settings.gcp_project_id, location=settings.bq_location)


def generate_query_embedding(query_text: str) -> list[float]:
    settings = get_settings()
    remote_model = (
        f"`{settings.gcp_project_id}.{settings.bq_gold_dataset}.{settings.bq_vertex_remote_model}`"
    )

    # task_type y output_dimensionality deben ser literales constantes (VERTEX_RAG_HANDOFF.md
    # §6) — ML.GENERATE_EMBEDDING rechaza parámetros de consulta en ese STRUCT. Ninguno de los
    # dos viene de texto de usuario: task_type es una constante fija y la dimensión sale de
    # config validada por Pydantic, así que interpolarlos aquí no abre una inyección SQL.
    sql = f"""
        SELECT ml_generate_embedding_result AS embedding
        FROM ML.GENERATE_EMBEDDING(
          MODEL {remote_model},
          (SELECT @query_text AS content),
          STRUCT(
            TRUE AS flatten_json_output,
            'RETRIEVAL_QUERY' AS task_type,
            {int(settings.vertex_embedding_dimension)} AS output_dimensionality
          )
        )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("query_text", "STRING", query_text)]
    )
    rows = list(get_bigquery_client().query(sql, job_config=job_config).result())
    return list(rows[0]["embedding"])


def vector_search(
    query_embedding: list[float],
    top_k: int,
    entity_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    table = (
        f"`{settings.gcp_project_id}.{settings.bq_gold_dataset}.{settings.bq_vertex_embeddings_table}`"
    )

    query_parameters = [
        bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
        bigquery.ScalarQueryParameter("model_name", "STRING", settings.vertex_embedding_model),
        bigquery.ScalarQueryParameter(
            "embedding_dimension", "INT64", settings.vertex_embedding_dimension
        ),
        bigquery.ScalarQueryParameter("template_version", "STRING", TEMPLATE_VERSION),
    ]

    entity_type_filter = ""
    if entity_types:
        entity_type_filter = "AND entity_type IN UNNEST(@entity_types)"
        query_parameters.append(
            bigquery.ArrayQueryParameter("entity_types", "STRING", entity_types)
        )

    # top_k se interpola como int() ya casteado (no texto de usuario) porque la sintaxis de
    # VECTOR_SEARCH espera un literal en `top_k =>`, igual que el STRUCT de arriba.
    sql = f"""
        SELECT
          base.entity_type AS entity_type,
          base.entity_id AS entity_id,
          base.name AS name,
          base.searchable_text AS searchable_text,
          distance
        FROM VECTOR_SEARCH(
          (
            SELECT entity_type, entity_id, name, searchable_text, embedding
            FROM {table}
            WHERE model_name = @model_name
              AND embedding_dimension = @embedding_dimension
              AND template_version = @template_version
              {entity_type_filter}
          ),
          'embedding',
          (SELECT @query_embedding AS embedding),
          top_k => {int(top_k)},
          distance_type => 'COSINE'
        )
        ORDER BY distance ASC
    """
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    rows = get_bigquery_client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]
