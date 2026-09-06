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
| 7 | Frontend Apps Script (Login/Registro/Chat) | ✅ **publicado** como Web App, ver URL abajo. Falta setear `BACKEND_URL` (depende de Fase 8) |
| 8 | Cloud Run (deploy real) | ⏳ pendiente — siguiente paso natural |
| 9 | Google Sites (embed) | ⏳ pendiente — depende de 8 (URL real de Cloud Run) |
| 10 | Evaluación (manual + LLM-as-judge) | ⏳ pendiente |

## Recursos GCP ya provisionados (proyecto `ah-estefania-alozno`)

No los vuelvas a crear/verificar desde cero — ya existen:

- APIs habilitadas: `firestore.googleapis.com`, `aiplatform.googleapis.com`, `bigquery.googleapis.com`
  (+ sub-APIs de BigQuery). **NO habilitadas todavía**: `run.googleapis.com`,
  `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com` — se necesitan para Fase 8.
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

- Ninguno bloqueante ahora mismo. `clasp` ya está instalado y logueado (vía npm de Windows,
  `/mnt/c/Users/estef/AppData/Roaming/npm/clasp`), y el Web App de Fase 7 ya está publicado
  (ver sección Frontend abajo). El único pendiente real es Fase 8 (Cloud Run) para tener una
  `BACKEND_URL` real que setear en las Script Properties del proyecto Apps Script.

## Frontend publicado (Fase 7)

- Script ID: `1G7TWkov2cmtmMezsRpyPzIAUvGG9N-wGIgWTJRa-4hmeHwkUPkXtSB9R`
  (editor: `clasp open-script` desde `frontend/apps-script/`, o
  `https://script.google.com/d/<scriptId>/edit`).
- Deployment id `AKfycbyVXj_a9TekA26uc8fOf8CtsmPX_uMZqu51B9h3vanrWWcyf2LWQlItqUPKWf7Z5ViM`
  (descripción "Elden Ring Guide MVP", versión 1).
- **URL pública del Web App** (confirmado `curl` → HTTP 200, sirve el HTML real):
  `https://script.google.com/macros/s/AKfycbyVXj_a9TekA26uc8fOf8CtsmPX_uMZqu51B9h3vanrWWcyf2LWQlItqUPKWf7Z5ViM/exec`
- **Falta**: entrar al editor (`clasp open-script`) → Project Settings → Script Properties →
  agregar `BACKEND_URL` = URL de Cloud Run (Fase 8). Sin eso, el login/chat fallan con
  "BACKEND_URL no está configurado" (mensaje intencional en `script.html`).
- Para repushear tras cambios de código: `cd frontend/apps-script && clasp push --force`. Para
  una nueva versión del deployment: `clasp create-deployment --deploymentId <id> -d "..."`
  (o `redeploy`), no crear un deployment nuevo cada vez salvo que quieras otra URL.

## Config local

- `.env` existe local (gitignored) con valores reales de dev: `GEMINI_MODEL=gemini-2.5-flash`,
  `VERTEX_LOCATION=us-central1`, resto de `.env.example`. `JWT_SECRET` es un placeholder corto
  (`<secret>`) — bueno para dev, cambiar antes de un deploy real (Fase 8 debería usar Secret
  Manager, ver skill `gcp-provisioning`).
- Tests: `.venv/bin/python -m pytest tests/` → 26 passed (todo mockeado, no pega a GCP).
  Validación contra infra real se hizo manualmente vía smoke tests con `curl`/scripts sueltos
  durante el desarrollo — no quedaron como tests automatizados de integración.

## Próximo paso sugerido

Fase 8 — Cloud Run: habilitar `run.googleapis.com`/`cloudbuild.googleapis.com`/
`artifactregistry.googleapis.com`, `gcloud run deploy` (ver skill `gcp-provisioning` §5),
smoke test `/health` + `/login` (con uno de los 3 usuarios reales) contra la URL real. Luego:
setear `BACKEND_URL` en las Script Properties del Apps Script ya publicado (Fase 7, ver
arriba) y validar login+chat desde
`https://script.google.com/macros/s/AKfycbyVXj.../exec` antes de pasar a Fase 9 (Sites).

---
*Última actualización: 2026-09-05, sesión Claude Code (Sonnet 5) — Fase 7 publicada (Web App
real arriba) + registro público eliminado (roster cerrado de 3 usuarios). Actualiza esta
sección al cerrar tu turno: fecha, qué cambiaste, qué falta.*
