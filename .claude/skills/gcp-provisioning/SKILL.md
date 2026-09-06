---
name: gcp-provisioning
description: Levantar, verificar y desplegar recursos GCP del proyecto (APIs, Firestore, BigQuery, Cloud Run, IAM) vía gcloud/bq CLI. Usar cuando haya que habilitar servicios, crear la base Firestore, verificar el dataset Gold, desplegar el backend a Cloud Run o revisar permisos.
---

# gcp-provisioning

Proyecto GCP objetivo: **`ah-estefania-alozno`**. Todos los comandos abajo asumen que ya
existe autenticación activa (`gcloud auth login` / ADC) — si falta, pide al usuario que la
haga (sugiérele `!gcloud auth login` si estás en Claude Code, ya que es interactivo).

## Regla de confirmación

- Comandos de **solo lectura** (`describe`, `list`, `bq show`, `bq query` SELECT) → ejecuta
  libremente para diagnóstico.
- Comandos que **crean, modifican, despliegan o borran** algo (`create`, `deploy`,
  `update`, `delete`, `bq mk`, `bq rm`) → confirma con el usuario antes, salvo autorización
  explícita ya dada en la conversación para ese comando exacto.
- **Nunca** ejecutes nada que borre o sobrescriba `elden_ring_gold.semantic_documents` ni
  `elden_ring_gold.entity_embeddings` (son de un proyecto Medallion externo, read-only). Solo
  se puede crear la tabla nueva `entity_embeddings_vertex` cuando así lo defina
  `VERTEX_RAG_HANDOFF.md`, y normalmente esa tabla la genera el proyecto Medallion, no este backend.

## 0. Fijar el proyecto activo

```bash
gcloud config set project ah-estefania-alozno
gcloud config get-value project
```

## 1. Habilitar APIs necesarias (idempotente, seguro de re-ejecutar)

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  --project ah-estefania-alozno
```

Verificar qué está habilitado:

```bash
gcloud services list --enabled --project ah-estefania-alozno
```

## 2. Firestore (memoria de aplicación — PRD §13, §30)

Verificar si ya existe una base de datos Firestore:

```bash
gcloud firestore databases list --project ah-estefania-alozno
```

Si no existe, crearla en modo Native (elige una región cercana al Cloud Run, ej. `us-central1`;
usar `(default)` como nombre salvo que el usuario pida otra cosa — coincide con
`FIRESTORE_DATABASE=(default)` del PRD §29):

```bash
gcloud firestore databases create \
  --project ah-estefania-alozno \
  --location=us-central1 \
  --type=firestore-native
```

No crear índices compuestos de entrada — el modelo de datos del MVP (§13) son documentos
sencillos y subcolecciones por `session_id`; solo agregar índices si una query concreta lo exige.

## 3. BigQuery Gold (conocimiento — PRD §2, §16)

**No es este skill el que crea el dataset Gold** (ya existe, viene del proyecto Medallion).
Úsalo solo para verificar contrato antes de codificar la tool RAG:

```bash
bq show ah-estefania-alozno:elden_ring_gold.semantic_documents
bq show ah-estefania-alozno:elden_ring_gold.entity_embeddings
bq show ah-estefania-alozno:elden_ring_gold.entity_embeddings_vertex   # puede no existir aún
```

Si `entity_embeddings_vertex` no existe todavía, es un bloqueo documentado en PRD §39/§Riesgos:
espera `VERTEX_RAG_HANDOFF.md` antes de continuar con `rag-bigquery`. No la crees tú mismo desde
este backend salvo instrucción explícita del usuario — pertenece al pipeline Medallion paralelo.

Verificar acceso al remote model de embeddings (una vez el handoff lo defina):

```bash
bq show --model ah-estefania-alozno:elden_ring_gold.<remote_model_name>
```

## 4. IAM (PRD §30)

MVP: usar la identidad/service account por defecto del proyecto con permisos amplios
suficientes para avanzar rápido (deuda técnica aceptada explícitamente, ver AGENTS.md §2).

Verificar qué roles tiene la identidad activa:

```bash
gcloud projects get-iam-policy ah-estefania-alozno \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)" \
  --format="table(bindings.role)"
```

Roles mínimos que debe poder ejercer la identidad usada por Cloud Run (verificar, no forzar
un rediseño de IAM en el MVP):

```text
roles/bigquery.dataViewer
roles/bigquery.jobUser
roles/aiplatform.user
roles/datastore.user      (Firestore)
roles/run.developer        (para desplegar)
```

Post-MVP (TODO-05, no ejecutar salvo pedido explícito): crear `elden-ring-agent-sa` dedicada
con esos mismos roles y nada más, y mover Cloud Run a usarla con
`gcloud run services update ... --service-account=elden-ring-agent-sa@ah-estefania-alozno.iam.gserviceaccount.com`.

## 5. Deploy a Cloud Run (Fase 8, PRD §33)

Confirma con el usuario antes de correr el deploy real. Patrón:

```bash
gcloud run deploy elden-ring-agent \
  --project ah-estefania-alozno \
  --region us-central1 \
  --source . \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GCP_PROJECT_ID=ah-estefania-alozno,BQ_LOCATION=US,BQ_GOLD_DATASET=elden_ring_gold,BQ_SEMANTIC_DOCUMENTS_TABLE=semantic_documents,BQ_VERTEX_EMBEDDINGS_TABLE=entity_embeddings_vertex,VERTEX_EMBEDDING_DIMENSION=768,GEMINI_MODEL=<modelo>,VERTEX_LOCATION=<region>,FIRESTORE_DATABASE="(default)",RAG_TOP_K=8,RECOMMENDATION_COUNT=3 \
  --set-secrets JWT_SECRET=jwt-secret:latest
```

Notas:

- `--allow-unauthenticated` es correcto para el MVP: la autenticación la maneja la aplicación
  (username/password + JWT), no IAM de Cloud Run (ADR-06).
- Prefiere `--set-secrets` con Secret Manager para `JWT_SECRET`; si no hay Secret Manager
  configurado, pregunta al usuario si prefiere crearlo (`gcloud secrets create jwt-secret ...`)
  o usar `--set-env-vars` como atajo de MVP (documentar la deuda técnica si se elige esto).
- La app debe escuchar `0.0.0.0:$PORT` — Cloud Run inyecta `$PORT`, no lo hardcodees en el Dockerfile.
- CORS permisivo es aceptable en MVP (TODO-06); no lo conviertas en bloqueante del deploy.

## 6. Smoke tests post-deploy

```bash
SERVICE_URL=$(gcloud run services describe elden-ring-agent \
  --project ah-estefania-alozno --region us-central1 --format='value(status.url)')

curl -s "$SERVICE_URL/health"
curl -s -X POST "$SERVICE_URL/login" -H 'Content-Type: application/json' \
  -d '{"username":"<uno de los 3 usuarios reales>","password":"<su password>"}'
```

No hay `/register` público — el registro se cerró a un roster fijo de usuarios creados vía
`scripts/create_user.py` (ver `SYSTEM_HEARTBEAT.md`). No lo reintroduzcas en el smoke test.

Si `/health` no responde `{"status":"ok"}`, revisar logs antes de tocar IAM o red:

```bash
gcloud run services logs read elden-ring-agent --project ah-estefania-alozno --region us-central1 --limit=100
```

## Riesgos conocidos (PRD §38) relevantes a este skill

- Cloud Run sin permisos suficientes → usar identidad de proyecto con permisos amplios en MVP.
- Demora de BigQuery → corpus pequeño + `top_k` reducido, no requiere tuning de infraestructura.
- Costos → preferir modelo Gemini económico configurable, no fijar uno caro por defecto.
