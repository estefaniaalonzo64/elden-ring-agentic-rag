---
name: rag-bigquery
description: Implementar o modificar la tool search_elden_ring_knowledge, el embedding de queries y las consultas VECTOR_SEARCH sobre BigQuery Gold. Usar cuando el trabajo toque retrieval, embeddings, o el contrato de VERTEX_RAG_HANDOFF.md.
---

# rag-bigquery

Alcance: PRD §2.3, §16, §39, Fase 4 (§40), pruebas §42 "RAG", caso de aceptación B (§43).

## Bloqueo obligatorio antes de avanzar

Este skill **no puede completarse** sin el archivo `VERTEX_RAG_HANDOFF.md` (generado por el
proyecto Medallion en paralelo). Antes de escribir código de retrieval:

```bash
test -f VERTEX_RAG_HANDOFF.md && echo "handoff presente" || echo "FALTA handoff — bloqueado"
```

Si falta, dilo explícitamente al usuario y no asumas nombres de tabla, modelo, dimensión ni
task type "razonables" — el PRD prohíbe explícitamente asumir un contrato distinto al que el
handoff final defina (§39, último párrafo). Es correcto avanzar en otros skills mientras tanto.

El handoff debe definir, como mínimo: tabla de embeddings Vertex, modelo, dimensión, remote
model, task type, query SQL/función recomendada, prueba de `VECTOR_SEARCH`, permisos. Usa
exactamente esos valores, no los del ejemplo de abajo si difieren.

## Qué NO tocar

- `entity_embeddings` (legado, 384-dim, `intfloat/multilingual-e5-small`) — no se usa en este
  RAG nuevo, no se modifica ni se borra.
- `semantic_documents` — solo lectura, es el contrato de texto (`searchable_text`, etc.).

## Tool a implementar (contrato exacto — PRD §16.1, §22.4)

```python
def search_elden_ring_knowledge(
    query: str,
    top_k: int = 8,
    entity_types: list[str] | None = None,
) -> list[RetrievedEntity]: ...
```

```python
class RetrievedEntity(BaseModel):
    rank: int
    score: float | None
    entity_type: str
    entity_id: str
    name: str
    searchable_text: str
```

## Flujo (PRD §16.3)

```
query → embedding (task=RETRIEVAL_QUERY, mismo modelo/dimensión del handoff)
      → BigQuery VECTOR_SEARCH sobre entity_embeddings_vertex
      → top_k IDs
      → join con semantic_documents para el texto/nombre
      → devolver como RetrievedEntity[]
```

- Task type para embeddings de **documentos** (si algún día se regeneran desde este repo):
  `RETRIEVAL_DOCUMENT`. Para **queries** del usuario: `RETRIEVAL_QUERY`. No mezclarlos.
- Modelo y dimensión deben ser configurables por entorno
  (`VERTEX_EMBEDDING_MODEL`, `VERTEX_EMBEDDING_DIMENSION`), nunca hardcodeados.
- Con ~1,208 documentos, `VECTOR_SEARCH` **sin** índice ANN es suficiente (TODO-07). No
  optimices con índice vectorial antes de que el corpus crezca — sería trabajo prematuro.
- Todas las queries desde esta tool son **read-only** (PRD §37).

## Config relevante (PRD §29)

```dotenv
BQ_LOCATION=US
BQ_GOLD_DATASET=elden_ring_gold
BQ_SEMANTIC_DOCUMENTS_TABLE=semantic_documents
BQ_VERTEX_EMBEDDINGS_TABLE=entity_embeddings_vertex
BQ_VERTEX_REMOTE_MODEL=<remote_model_name>
VERTEX_EMBEDDING_MODEL=<configured_embedding_model>
VERTEX_EMBEDDING_DIMENSION=768
RAG_TOP_K=8
```

## Pruebas mínimas (§42)

```text
query vacía
query normal
top_k
entity_type filter
resultados con nombre/id/texto
```

Antes de cablear el LLM/agente encima, valida el retrieval "sin LLM" (Fase 4, §40): que
preguntas semánticas devuelvan entidades relevantes.

## Riesgos específicos (§38)

- Vertex embeddings aún no terminados → mitigación: consumir el handoff cuando esté listo, no
  antes.
- Query embedding incompatible con los embeddings de documentos → usar exactamente el mismo
  remote model/dimensión/task definidos en el handoff.
