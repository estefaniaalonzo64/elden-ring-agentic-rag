# System Heartbeat

Bitácora viva del estado del proyecto. **Cualquier agente (Claude Code, Codex CLI, u otro)**
que retome este trabajo debe leer este archivo primero (después de `AGENTS.md`) y actualizarlo
al terminar su turno: qué hizo, qué encontró, qué falta. No es documentación de arquitectura
(eso vive en `AGENTS.md`/PRD) — es el "dónde quedamos" entre sesiones.

## Estado por fase (PRD §40)

| Fase | Qué es | Estado |
|---|---|---|
| 1 | Skeleton (FastAPI + `/health`, Dockerfile) | ✅ hecho, validado local |
| 2 | Auth + Firestore (`/login`, JWT — **sin** `/register` público) | ✅ hecho, validado contra Firestore real |
| 3 | Memoria (`player_profiles`, 3 tools) | ✅ hecho, validado contra Firestore real |
| 4 | RAG (`search_elden_ring_knowledge`) | ✅ hecho, validado contra BigQuery real (5 queries de aceptación del handoff) |
| 5 | ADK (`EldenRingGuideAgent`, `/chat`) | ✅ hecho, validado contra Gemini/Vertex AI real |
| 6 | Transcript (`chat_sessions/{id}/messages`) | ✅ hecho, validado (sobrevive logout, aislamiento A/B) |
| 7 | Frontend Apps Script (Login/Registro/Chat) | ✅ **publicado y funcionando** end-to-end (login+chat validados contra el backend real) |
| 8 | Cloud Run (deploy real) | ✅ desplegado y validado (`/health`, `/login`, `/chat` reales) |
| 9 | Google Sites (embed) | ⏳ pendiente — único paso manual que falta (crear el Site, incrustar la URL del Web App) |
| 10 | Evaluación (manual + LLM-as-judge) | ⏳ pendiente |

## Recursos GCP ya provisionados (proyecto `ah-estefania-alozno`)

No los vuelvas a crear/verificar desde cero — ya existen:

- APIs habilitadas: `firestore.googleapis.com`, `aiplatform.googleapis.com`,
  `bigquery.googleapis.com` (+ sub-APIs), `run.googleapis.com`, `cloudbuild.googleapis.com`,
  `artifactregistry.googleapis.com`, `secretmanager.googleapis.com`.
- Cloud Run: servicio `elden-ring-agent` en `us-central1`, desplegado desde `--source .`
  (Dockerfile), `--allow-unauthenticated` (autenticación la maneja la app, no IAM de Cloud
  Run). URL real: `https://elden-ring-agent-704637212685.us-central1.run.app`.
- Secret Manager: secreto `jwt-secret` (JWT_SECRET real, fuerte, generado con
  `secrets.token_urlsafe`), montado en Cloud Run vía `--set-secrets`. La service account de
  Cloud Run (`704637212685-compute@developer.gserviceaccount.com`, rol `roles/editor` +
  `roles/storage.objectViewer` + `roles/secretmanager.secretAccessor` sobre `jwt-secret`)
  necesitó ambos roles extra a mano — el `roles/editor` por defecto NO alcanza para que Cloud
  Build lea el source subido ni para leer el secreto en runtime.
- Firestore: base `(default)`, modo Native, región `us-central1`. Colecciones en uso:
  `users`, `player_profiles`, `chat_sessions`, `chat_sessions/{id}/messages`.
- BigQuery: `elden_ring_gold.entity_embeddings_vertex` ya existe (1208 filas, ver
  `VERTEX_RAG_HANDOFF.md` en la raíz — contrato completo copiado desde `practica_uno`).
- Usuarios reales creados (Firestore real, roster cerrado — ver Registro cerrado abajo):
  `estefania`, `profesor`, `usuariodex`. Passwords **no** están en este repo — las conoce el
  dueño del proyecto. `smoketest`/`smoketest_b` (cuentas de prueba de las fases anteriores) se
  **borraron** — no los recrees, ya no son parte del roster.

## Gotchas reales encontrados (no obvios desde el código)

1. **Firestore Python + `set(dict_con_claves_con_punto, merge=True)` NO anida** — guarda las
   claves punteadas como nombres de campo literales (`"stats.level"` en vez de anidar
   `stats.level`). El merge parcial correcto usa `update()` con esas mismas claves punteadas
   (que sí resuelve el path), asegurando antes que el doc exista con
   `doc_ref.set({}, merge=True)`. Ver `backend/repositories/firestore_repository.py`.
2. **El idioma del system instruction/docstrings de las tools sesga el idioma de respuesta
   del agente**, incluso con una regla explícita de "responde en el idioma del usuario". Con
   el prompt e instrucciones de tools en español, `gemini-2.5-flash` respondía en español a
   preguntas en inglés pese a instrucciones explícitas. Se resolvió reescribiendo
   `backend/agent/instructions.py` y las docstrings de `backend/agent/agent.py` en inglés.
   Si tocas ese prompt, vuelve a probar ambos idiomas en vivo antes de dar por bueno.
3. **`google-adk` instalado es 2.8.0**, con una API bastante distinta de tutoriales viejos de
   ADK (basada en `Agent`/`Runner`/`Event`, no en clases más simples). `Agent.tools` acepta
   callables planos directamente (no hace falta envolver en `FunctionTool`), y conserva su
   `__name__` — por eso las tools se registran como closures locales dentro de
   `build_agent(user_id, ...)` en vez de usar `functools.partial` (que no tiene `__name__`).
4. **WSL**: usar siempre `uv venv` + `uv pip install`, nunca `python -m venv`/`pip` a secas
   (más lento en WSL). Cuidado con `VIRTUAL_ENV` heredado de otro proyecto hermano
   (`diplo2026/.venv`) — si `uv pip install` no deja los paquetes donde esperas, hacer
   `unset VIRTUAL_ENV` antes o pasar `--python .venv/bin/python` explícito.
5. **`appsscript.json`: `webapp.access: "ANYONE_ANONYMOUS"` es incompatible con
   `webapp.executeAs: "USER_ACCESSING"`** — `clasp push` lo rechaza con un error genérico
   ("Invalid manifest file") sin decir por qué. Tiene sentido: no puedes "ejecutar como el
   usuario que accede" si ese usuario es anónimo/no identificado. La combinación válida para
   acceso público sin login de Google es `access: ANYONE_ANONYMOUS` + `executeAs:
   USER_DEPLOYING` (el script siempre corre con la identidad del desarrollador — está bien
   porque `Code.gs` no llama APIs de Google que necesiten la identidad del visitante). El
   mensaje de tip de `clasp create-script` sugiere la clave `"webApp"` (camelCase) pero el
   manifest real usa `"webapp"` (minúsculas) — `"webApp"` da `unknown fields: [webApp]`.
6. **`clasp` vía el binario de Windows desde WSL es lento** (cada invocación puede tardar
   >60s, el Bash tool las manda a background) — es normal, no es que algo esté colgado.
7. **`gcloud run deploy --source .` con la service account por defecto necesita 2 roles
   extra que `roles/editor` NO cubre**: `roles/storage.objectViewer` (para que el build de
   Cloud Build pueda leer el .zip de fuente subido a GCS — sin esto falla con
   `PERMISSION_DENIED... could not resolve source`) y, si usas `--set-secrets`,
   `roles/secretmanager.secretAccessor` otorgado **sobre el secreto específico**
   (`gcloud secrets add-iam-policy-binding`), no solo a nivel proyecto. Ambos son fixes
   de una sola vez por proyecto, no hace falta repetirlos en redeploys futuros.
8. **Abrir `script.google.com/d/<scriptId>/edit` puede fallar** ("No se pudo abrir el
   archivo en este momento") incluso con la cuenta correcta ya logueada en el navegador —
   pasó en esta sesión sin causa clara (¿propagación de Drive para proyectos creados vía API?
   ¿caché del navegador?). El formato alterno `script.google.com/home/projects/<scriptId>/edit`
   sí funcionó. Si un usuario reporta esto, prueba esa URL antes de asumir que es un problema
   de cuenta/permisos.

## Registro cerrado (decisión del usuario, 2026-09-05)

El usuario pidió explícitamente **quitar el registro público** porque el Web App es de acceso
anónimo (`ANYONE_ANONYMOUS`, ver Fase 7) y no quiere que cualquiera cree una cuenta y gaste
tokens de Gemini. Cambios:

- `POST /register` **ya no existe** en `backend/main.py` (ni `RegisterRequest`/
  `RegisterResponse` en `backend/models/api.py`). `/login` sigue igual.
- `backend/auth/service.py` conserva `register()`/`UsernameTakenError` — los usa
  `scripts/create_user.py`, no la API pública.
- Alta de usuarios nuevos: `PYTHONPATH=. .venv/bin/python scripts/create_user.py <user> <pass>`
  (solo local, contra Firestore real, nunca por HTTP). Idempotente: si el username ya existe,
  lo reporta y no falla.
- Roster actual: `estefania`, `profesor`, `usuariodex` (passwords fuera del repo).
- Si en el futuro se pide reabrir el registro, es una reversión explícita de esta decisión —
  no la reintroduzcas por tu cuenta sin que el usuario lo pida de nuevo.

## Bloqueos activos

Ninguno. Backend real desplegado y frontend publicado, ambos validados end-to-end
(login+chat reales, ver Frontend/Backend abajo). Lo único que falta es Fase 9 (crear el
Google Site e incrustar la URL del Web App) y Fase 10 (evaluación) — ambos pasos manuales o
de contenido, no bloqueados por infraestructura.

## Backend en Cloud Run (Fase 8)

- Servicio: `elden-ring-agent`, región `us-central1`, proyecto `ah-estefania-alozno`.
- URL: `https://elden-ring-agent-704637212685.us-central1.run.app`.
- Validado con curl real: `/health` → 200, `/login` (los 3 usuarios reales) → 200, `/chat`
  completo (RAG + Gemini + fuentes, en español e inglés) → 200.
- Redeploy tras cambios de código: mismo comando `gcloud run deploy elden-ring-agent
  --project ah-estefania-alozno --region us-central1 --source . --allow-unauthenticated
  --port 8080 --set-env-vars BQ_VERTEX_REMOTE_MODEL=elden_ring_embedding_model,VERTEX_EMBEDDING_MODEL=gemini-embedding-001,GEMINI_MODEL=gemini-2.5-flash,VERTEX_LOCATION=us-central1
  --set-secrets JWT_SECRET=jwt-secret:latest` (los env vars con default correcto en
  `backend/config.py` no hace falta repetirlos — ver esa tabla si agregas uno nuevo).

## Frontend publicado (Fase 7) — funcionando end-to-end

- Script ID: `1G7TWkov2cmtmMezsRpyPzIAUvGG9N-wGIgWTJRa-4hmeHwkUPkXtSB9R`. Editor:
  `https://script.google.com/home/projects/<scriptId>/edit` (el formato `/d/<id>/edit` le
  falló al usuario en esta sesión, ver gotcha #8 — usa `/home/projects/` si vuelve a pasar).
- Deployment id `AKfycbyVXj_a9TekA26uc8fOf8CtsmPX_uMZqu51B9h3vanrWWcyf2LWQlItqUPKWf7Z5ViM`.
- **URL pública del Web App**:
  `https://script.google.com/macros/s/AKfycbyVXj_a9TekA26uc8fOf8CtsmPX_uMZqu51B9h3vanrWWcyf2LWQlItqUPKWf7Z5ViM/exec`
- Script Property `BACKEND_URL` ya seteada por el usuario (manual, vía Project Settings →
  Script Properties) apuntando al Cloud Run real de arriba. Confirmado con curl que el HTML
  servido ya trae el valor correcto inyectado.
- Login + chat probados end-to-end (simulando el fetch del navegador con
  `Origin: https://script.google.com`) — funciona completo, en español e inglés, formato de
  fuentes correcto.
- Para repushear tras cambios de código: `cd frontend/apps-script && clasp push --force`. Para
  una nueva versión del deployment: `clasp create-deployment --deploymentId <id> -d "..."`
  (o `redeploy`), no crear un deployment nuevo cada vez salvo que quieras otra URL.

## Config local

- `.env` existe local (gitignored) con los mismos valores que se usaron para Cloud Run:
  `GEMINI_MODEL=gemini-2.5-flash`, `VERTEX_LOCATION=us-central1`, resto de `.env.example`.
  `JWT_SECRET` local sigue siendo el placeholder corto de dev — el real y fuerte vive solo en
  Secret Manager (`jwt-secret`), no en este repo ni en `.env`.
- Tests: `.venv/bin/python -m pytest tests/` → 26 passed (todo mockeado, no pega a GCP).
  Validación contra infra real (Firestore/BigQuery/Vertex AI/Cloud Run/Apps Script) se hizo
  manualmente vía smoke tests con `curl` durante el desarrollo — no quedaron como tests
  automatizados de integración.

## Próximo paso sugerido

Fase 9 — Google Sites: crear el Site, incrustar la URL del Web App de arriba (por URL/iframe
según lo permita Apps Script — `setXFrameOptionsMode(ALLOWALL)` ya está puesto en `Code.gs`
para que el embed funcione), validar login+chat+logout desde la URL final de Sites. Después,
Fase 10 — Evaluación (`evaluation/cases.yaml`, manual + LLM-as-judge, skill `evaluation`).

---
*Última actualización: 2026-09-05, sesión Claude Code (Sonnet 5) — Fase 8 (Cloud Run) y Fase 7
(Apps Script) completas y validadas end-to-end contra infraestructura real. Quedan Fase 9
(Sites, manual) y Fase 10 (Evaluación). Actualiza esta sección al cerrar tu turno: fecha, qué
cambiaste, qué falta.*
