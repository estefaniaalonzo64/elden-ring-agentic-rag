# Corpus vectorial Vertex AI — Elden Ring Lakehouse

**Handoff para un agente de RAG externo (FastAPI + Google ADK + Firestore + Gemini + Cloud Run)**

- **Fecha:** 2026-09-05
- **Origen:** `practica_uno` (Elden Ring Medallion Lakehouse)
- **Proyecto GCP:** `ah-estefania-alozno`
- **Ubicación BigQuery:** `US`

## 0. Qué es esto y qué NO es

Esta es la **segunda** estrategia de embeddings del proyecto, agregada como extensión independiente sobre la capa Gold ya existente — ver [`RAG_HANDOFF.md`](./RAG_HANDOFF.md) para la primera (E5 local + FAISS, que sigue intacta y sin cambios).

```
elden_ring_gold.semantic_documents   (contrato de entrada — sin cambios)
            │
            ▼
BigQuery ML.GENERATE_EMBEDDING  (modelo remoto → Vertex AI gemini-embedding-001)
            │
            ▼
elden_ring_gold.entity_embeddings_vertex
            │
            ▼
BigQuery VECTOR_SEARCH  (exacto, sin índice ANN — corpus pequeño)
```

**No incluye generación con LLM.** Es la capa de recuperación (la "R" de RAG): texto + embedding + una prueba de `VECTOR_SEARCH`. El agente consumidor aporta la generación — tomar el `top_k`, armar el prompt y llamar a Gemini.

**Ambas estrategias de embeddings coexisten y son independientes**: `entity_embeddings` (E5, 384 dim) no se tocó, no se leyó y no se modificó en absoluto durante esta extensión — sigue siendo evidencia intacta del proyecto anterior.

## 1. Tabla a consumir

```
ah-estefania-alozno.elden_ring_gold.entity_embeddings_vertex
```

Fuente de entrada (no la reconstruyas, ya viene generada): `ah-estefania-alozno.elden_ring_gold.semantic_documents`.

## 2. Proyecto y dataset

| Campo | Valor |
|---|---|
| Proyecto GCP | `ah-estefania-alozno` |
| Dataset | `elden_ring_gold` |
| Ubicación BigQuery | `US` |
| Autenticación | ADC (`gcloud auth application-default login`) con lectura sobre el proyecto |

## 3. Modelo de embeddings

| Campo | Valor |
|---|---|
| Modelo | `gemini-embedding-001` (Vertex AI, vía modelo remoto de BigQuery ML) |
| Modelo remoto de BigQuery | `ah-estefania-alozno.elden_ring_gold.elden_ring_embedding_model` |
| BigQuery Connection | `ah-estefania-alozno.US.vertex_ai_connection` (CLOUD_RESOURCE) |
| Framework | `ML.GENERATE_EMBEDDING` — el vector se calcula 100% server-side, nunca se descarga un modelo ni se ejecuta código Python de inferencia |

## 4. Dimensión

**768** (`output_dimensionality` — gemini-embedding-001 soporta dimensiones configurables tipo Matryoshka: 768/1536/3072/…; se fijó 768 en este proyecto). Verificar siempre `embedding_dimension` en la fila, no asumir.

## 5. Task type de documentos

Cada fila de `entity_embeddings_vertex` se generó con:

```
task_type = RETRIEVAL_DOCUMENT
```

(columna `embedding_task` en la tabla, para que quede trazable si en el futuro coexisten varios task_types).

## 6. Cómo generar el embedding de una consulta (RETRIEVAL_QUERY)

**Regla crítica — patrón asimétrico:** los documentos se vectorizaron con `RETRIEVAL_QUERY` **nunca**, con `RETRIEVAL_DOCUMENT` siempre. Cualquier pregunta de usuario debe vectorizarse con `RETRIEVAL_QUERY` usando el **mismo modelo y la misma dimensión** — de lo contrario la comparación de distancia cae en espacios no comparables y degrada la recuperación en silencio (sin error).

```sql
SELECT ml_generate_embedding_result AS embedding
FROM ML.GENERATE_EMBEDDING(
  MODEL `ah-estefania-alozno.elden_ring_gold.elden_ring_embedding_model`,
  (SELECT @query_text AS content),
  STRUCT(
    TRUE AS flatten_json_output,
    'RETRIEVAL_QUERY' AS task_type,
    768 AS output_dimensionality
  )
);
```

**Advertencia de plataforma (no evidente en la documentación pública al momento de escribir esto):** el `STRUCT(...)` de opciones de `ML.GENERATE_EMBEDDING` exige valores **literales constantes** para `task_type` y `output_dimensionality` — no acepta parámetros de consulta (`@task_type` falla con `"Table Valued Function expects the settings struct to have literal constant values"`). Si tu backend arma esta consulta dinámicamente, interpola esos dos valores como literales (con una lista blanca de valores válidos, nunca con el texto del usuario) en vez de bindearlos como parámetro.

Este proyecto expone la misma consulta ya resuelta vía CLI, útil como referencia de implementación exacta:

```bash
python -m src.cli vertex-search "tu pregunta aquí" --top-k 5
```

Ver `sql/gold/vertex_query_embedding.sql` y `VertexEmbeddingRepository.generate_query_embedding` en `src/gold/vertex_embedding_repository.py` para la implementación de referencia (Python + `google-cloud-bigquery`).

## 7. Ejemplo de `VECTOR_SEARCH`

Con ~1,208 documentos no se justifica un `VECTOR INDEX` (ANN) — BigQuery hace un escaneo exacto directamente sobre la columna `embedding` cuando no existe un índice. Filtrar siempre por `model_name`/`embedding_dimension`/`template_version` antes de buscar, para no mezclar corridas futuras con otro modelo o dimensión:

```sql
SELECT
  base.entity_type,
  base.entity_id,
  base.name,
  base.searchable_text,
  distance
FROM VECTOR_SEARCH(
  (
    SELECT entity_type, entity_id, name, searchable_text, embedding
    FROM `ah-estefania-alozno.elden_ring_gold.entity_embeddings_vertex`
    WHERE model_name = 'gemini-embedding-001'
      AND embedding_dimension = 768
      AND template_version = 'v1'
  ),
  'embedding',
  (SELECT @query_embedding AS embedding),   -- ARRAY<FLOAT64>, ver §6
  top_k => 5,
  distance_type => 'COSINE'
)
ORDER BY distance ASC;
```

Notas de sintaxis verificadas contra el proyecto real (BigQuery rechaza patrones "razonables" que no son los soportados):
- El **primer** argumento de `VECTOR_SEARCH` solo admite `TABLE nombre_de_tabla` o un `(SELECT ... WHERE ...)` — **no** acepta una CTE que contenga `ML.GENERATE_EMBEDDING` ni patrones de subconsulta más complejos.
- Las columnas de salida vienen ya nombradas `base.*` (y `query.*` si el lado de la consulta trae columnas propias) — **no** le pongas un alias de tabla a la llamada completa (`... ) AS base` rompe la referencia, porque `base` ya es el nombre del STRUCT de salida).
- `distance_type => 'COSINE'` es la opción segura independientemente de si el proveedor normaliza o no el vector (a diferencia de E5, donde el proyecto anterior normalizaba explícitamente y usaba producto interno).

Prueba funcional completa (5 consultas de aceptación, sin generación de texto):

```bash
python -m src.cli vertex-search "fast katana for an aggressive dexterity playstyle" --top-k 5
python -m src.cli vertex-search "powerful magic staff for an intelligence build" --top-k 5
python -m src.cli vertex-search "boss associated with stars" --top-k 5
python -m src.cli vertex-search "armor with strong physical resistance" --top-k 5
python -m src.cli vertex-search "NPC from Roundtable Hold" --top-k 5
```

Resultados reales obtenidos contra `ah-estefania-alozno` (recuperación semántica correcta en las 5): katanas (Nagakiba, Uchigatana, Rivers of Blood…) para la primera; báculos/glintstone staves para la segunda; Starscourge Radahn y Astel, Stars Of Darkness para la tercera; armaduras pesadas para la cuarta; Enia, Knight Diallos, Fia — NPCs efectivamente asociados a Roundtable Hold — para la quinta.

## 8. Esquema de la tabla

```
entity_type            STRING     NOT NULL   -- armor · weapon · boss · incantation · ash · npc
entity_id              STRING     NOT NULL
name                   STRING     NOT NULL

searchable_text        STRING     NOT NULL   -- idéntico al de semantic_documents, es lo que se vectorizó
searchable_text_hash   STRING     NOT NULL
source_record_hash     STRING     NOT NULL
source_updated_at      TIMESTAMP  NOT NULL

embedding              ARRAY<FLOAT64>        -- 768 posiciones
embedding_dimension    INT64      NOT NULL
embedding_hash         STRING     NOT NULL   -- sha256 (hex) del vector, vía SQL: TO_HEX(SHA256(TO_JSON_STRING(embedding)))

model_name             STRING     NOT NULL   -- 'gemini-embedding-001'
embedding_task         STRING     NOT NULL   -- 'RETRIEVAL_DOCUMENT'
template_version       STRING     NOT NULL   -- comparte versión de plantilla con semantic_documents

embedded_at            TIMESTAMP  NOT NULL
```

Clave lógica (para MERGE/idempotencia, y para filtrar antes de VECTOR_SEARCH):
`(entity_type, entity_id, model_name, embedding_dimension, template_version)`

## 9. Configuración necesaria

Variables de entorno (ver `.env.example`, sección Vertex — no reemplazan ni pisan las de E5):

```env
VERTEX_EMBEDDING_MODEL=gemini-embedding-001
VERTEX_EMBEDDING_DIMENSION=768
VERTEX_EMBEDDING_TASK_DOCUMENT=RETRIEVAL_DOCUMENT
VERTEX_EMBEDDING_TASK_QUERY=RETRIEVAL_QUERY
BQ_VERTEX_EMBEDDING_TABLE=entity_embeddings_vertex
BQ_VERTEX_REMOTE_MODEL=elden_ring_embedding_model
BQ_CONNECTION_ID=vertex_ai_connection
```

Un backend externo que solo **lee** esta tabla y genera embeddings de consulta necesita, como mínimo: `GCP_PROJECT_ID`, `BQ_GOLD_DATASET` (`elden_ring_gold`), `BQ_LOCATION` (`US`), y los cinco valores de arriba (modelo/dimensión/task_query/remote_model/tabla) para poder reproducir exactamente la consulta de `ML.GENERATE_EMBEDDING`.

## 10. Permisos (IAM) — MVP académico, prioriza velocidad sobre mínimo privilegio

Para que **este** proyecto pudiera generar los embeddings, se aprovisionó (una sola vez, documentado en `sql/gold/create_vertex_connection_or_instructions.sql`):

1. API habilitada: `aiplatform.googleapis.com`.
2. BigQuery Connection CLOUD_RESOURCE: `ah-estefania-alozno.US.vertex_ai_connection` → aprovisionó la service account `bqcx-704637212685-lu2y@gcp-sa-bigquery-condel.iam.gserviceaccount.com`.
3. Esa service account recibió `roles/aiplatform.user` a nivel de **proyecto** (el mensaje de error de BigQuery lo llama "Agent Platform User" — es el mismo rol, renombrado en la consola/documentación reciente).

Para que un **backend externo** (FastAPI/Cloud Run) pueda:
- **Leer** `entity_embeddings_vertex` y correr `VECTOR_SEARCH`: su identidad (service account de Cloud Run) necesita `roles/bigquery.dataViewer` sobre el dataset `elden_ring_gold` + `roles/bigquery.jobUser` sobre el proyecto (para poder ejecutar el `SELECT ... VECTOR_SEARCH`).
- **Generar embeddings de consulta** (`ML.GENERATE_EMBEDDING` con `RETRIEVAL_QUERY`) usando el mismo modelo remoto: además de lo anterior, necesita permiso para invocar ese modelo remoto — como es un modelo de BigQuery ML (no una llamada directa a la API de Vertex AI), con `roles/bigquery.dataViewer` + `roles/bigquery.jobUser` alcanza; la propia BigQuery Connection ya está autorizada contra Vertex AI y actúa en nombre de la consulta.

Comando de referencia para otorgar esos dos roles a la service account del backend externo:

```bash
gcloud projects add-iam-policy-binding ah-estefania-alozno \
  --member="serviceAccount:<SERVICE_ACCOUNT_DEL_BACKEND>" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding ah-estefania-alozno \
  --member="serviceAccount:<SERVICE_ACCOUNT_DEL_BACKEND>" \
  --role="roles/bigquery.jobUser"
```

> **Nota de honestidad:** este proyecto se ejecutó y validó con la cuenta `owner` (`estefania6409@gmail.com`), no con una service account de backend separada — los dos roles de arriba son la referencia estándar de Google para consultar un modelo remoto ya creado, pero no se probaron empíricamente en este repo con una identidad distinta. Si al integrar falla con un error de permisos sobre el modelo o la conexión, el rol adicional a probar primero es `roles/bigquery.connectionUser` sobre `ah-estefania-alozno.US.vertex_ai_connection`.

## 11. Volumen final

| Entity type | Filas en `semantic_documents` | Filas en `entity_embeddings_vertex` | Cobertura |
|---|---:|---:|---:|
| armor | 563 | 563 | 100% |
| weapon | 286 | 286 | 100% |
| boss | 105 | 105 | 100% |
| incantation | 100 | 100 | 100% |
| ash | 94 | 94 | 100% |
| npc | 60 | 60 | 100% |
| **Total** | **1,208** | **1,208** | **100%** |

Validado tras la primera corrida real (`inserted=1208, updated=0, noop=0, errors=0`) y confirmado en una segunda corrida idempotente (`inserted=0, updated=0, noop=1208`). Sin nulos (`COUNTIF(embedding IS NULL) = 0`), sin duplicados por clave lógica, sin filas con dimensión distinta de 768.

## 12. Limitaciones conocidas

- **Sin `VECTOR INDEX` (ANN)** — deliberado, ver §13. Con este volumen el escaneo exacto es rápido y evita complejidad/infra innecesaria.
- **Sin capa de generación** — ver §0. Este handoff entrega retrieval, no un endpoint de pregunta-respuesta.
- **`STRUCT(...)` de `ML.GENERATE_EMBEDDING` exige literales, no parámetros** — ver la advertencia de §6; cualquier reimplementación en otro lenguaje/librería debe respetar esta restricción de la plataforma.
- **`embedding_hash` no es comparable con el de `entity_embeddings` (E5)** — se calculan con algoritmos distintos (SQL `SHA256(TO_JSON_STRING(...))` vs. Python `hashlib.sha256(vector.tobytes())`); no asumir que representan el mismo vector aunque compartan `entity_type`/`entity_id`.
- **Las 6 entidades `boss` en cuarentena en Silver** (drops mezclados en el campo de HP en la API de origen) siguen fuera de ambos corpus, E5 y Vertex — es basura real de la fuente, no un bug de esta extensión.

## 13. Optimización futura: `VECTOR INDEX`

Si el corpus crece significativamente (decenas de miles de filas o más), agregar un índice ANN sobre `entity_embeddings_vertex` reduciría el costo de `VECTOR_SEARCH` de escaneo exacto a aproximado:

```sql
CREATE VECTOR INDEX entity_embeddings_vertex_ivf
ON `ah-estefania-alozno.elden_ring_gold.entity_embeddings_vertex`(embedding)
OPTIONS (
  index_type = 'IVF',
  distance_type = 'COSINE'
);
```

No se creó en este proyecto (~1.2k filas no lo justifica — BigQuery ni siquiera lo recomienda por debajo de varios miles de filas, y añadiría un costo de mantenimiento de índice sin beneficio medible).

## 14. Cómo regenerar

```bash
cd practica_uno
source .venv/bin/activate   # o el entorno que uses
python -m src.cli vertex-embeddings
```

Es idempotente: solo genera embeddings para entidades cuyo `source_record_hash` o `searchable_text_hash` cambiaron desde la última corrida (ver `sql/gold/vertex_embedding_delta.sql`). Nunca reconstruye la tabla completa (`MERGE`, no `CREATE OR REPLACE TABLE`).

## 15. Cómo comprobar cobertura

La propia CLI la imprime al final de cada corrida (`coverage: 100% (1208/1208)` + tabla por `entity_type`). Para verificarlo manualmente:

```sql
SELECT
  (SELECT COUNT(*) FROM `ah-estefania-alozno.elden_ring_gold.semantic_documents`) AS source_count,
  (
    SELECT COUNT(*)
    FROM `ah-estefania-alozno.elden_ring_gold.entity_embeddings_vertex`
    WHERE model_name = 'gemini-embedding-001'
      AND embedding_dimension = 768
      AND template_version = 'v1'
  ) AS embedded_count;
```

## 16. Cómo integrarlo desde un backend externo (FastAPI + ADK + Firestore + Gemini + Cloud Run)

Flujo recomendado para el agente consumidor:

1. **Autenticación**: usar una service account dedicada del backend con los roles de §10 (nunca reusar credenciales personales/ADC de este repo).
2. **Por cada pregunta de usuario**: ejecutar la consulta de §6 (`ML.GENERATE_EMBEDDING` con `RETRIEVAL_QUERY`, mismo modelo/dimensión) para obtener el `ARRAY<FLOAT64>` de la pregunta.
3. **Recuperación**: ejecutar la consulta de §7 (`VECTOR_SEARCH`) con ese vector, `top_k` configurable (5 es un buen default, igual que en este repo).
4. **Prompt**: armar el contexto para Gemini a partir de `searchable_text` de las filas recuperadas (no de `name` solo — el texto ya trae todos los atributos relevantes por tipo de entidad).
5. **Estado de sesión** (si el agente ADK lo requiere): Firestore es responsabilidad del proyecto consumidor — este handoff no prescribe su esquema, solo el contrato de recuperación de arriba.
6. **Nunca** escribir en `entity_embeddings_vertex` ni en `entity_embeddings` desde el backend externo — ambas tablas son de solo lectura para cualquier consumidor fuera de este repo; la generación/actualización de embeddings vive únicamente en `practica_uno` vía `python -m src.cli vertex-embeddings`.

---

Generado como extensión sobre `practica_uno` (Elden Ring Medallion Lakehouse) — la estrategia E5 + FAISS original permanece intacta y documentada en [`RAG_HANDOFF.md`](./RAG_HANDOFF.md).
