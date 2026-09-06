# System Heartbeat

Bitácora viva del estado del proyecto. **Cualquier agente (Claude Code, Codex CLI, u otro)**
que retome este trabajo debe leer este archivo primero (después de `AGENTS.md`) y actualizarlo
al terminar su turno: qué hizo, qué encontró, qué falta. No es documentación de arquitectura
(eso vive en `AGENTS.md`/PRD) — es el "dónde quedamos" entre sesiones.

## Estado por fase (PRD §40)

| Fase | Qué es | Estado |
|---|---|---|
| 1 | Skeleton (FastAPI + `/health`, Dockerfile) | ✅ hecho, validado local |
| 2 | Auth + Firestore (`/register`, `/login`, JWT) | ✅ hecho, validado contra Firestore real |
| 3 | Memoria (`player_profiles`, 3 tools) | ✅ hecho, validado contra Firestore real |
| 4 | RAG (`search_elden_ring_knowledge`) | ✅ hecho, validado contra BigQuery real (5 queries de aceptación del handoff) |
| 5 | ADK (`EldenRingGuideAgent`, `/chat`) | ✅ hecho, validado contra Gemini/Vertex AI real |
| 6 | Transcript (`chat_sessions/{id}/messages`) | ✅ hecho, validado (sobrevive logout, aislamiento A/B) |
| 7 | Frontend Apps Script (Login/Registro/Chat) | ✅ código completo, **sin publicar** (falta `clasp`, ver Bloqueos) |
| 8 | Cloud Run (deploy real) | ⏳ pendiente — siguiente paso natural |
| 9 | Google Sites (embed) | ⏳ pendiente — depende de 7 (publicar) y 8 (URL real) |
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
- Usuarios de prueba ya registrados (Firestore real): `smoketest`, `smoketest_b`
  (password `changeme123` en ambos). Su `player_profiles` tiene datos de smoke-test reales
  (preferencias de bleed/dexterity aprendidas automáticamente en Fase 5) — no son basura,
  déjalos o límpialos si estorban.

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

## Bloqueos activos

- **`clasp` (Apps Script CLI) no está instalado** y el usuario no tiene Node/npm nativo de WSL
  (solo el `node.exe`/`npm` de Windows expuesto vía `/mnt/c`, poco fiable para instalar global
  por permisos). El usuario necesita correr esto él mismo en una terminal WSL real (no vía
  Claude Code, porque `sudo` pide contraseña interactiva):
  ```bash
  sudo apt update && sudo apt install -y nodejs npm
  npm install -g @google/clasp
  clasp login   # abre navegador, requiere su cuenta Google
  ```
  Una vez hecho esto, retomar Fase 7 (publicar el Web App) y Fase 9 (embed en Sites).

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
smoke test `/health` + `/register` contra la URL real, y luego volver a Fase 7/9 con esa URL
para `BACKEND_URL` en Script Properties.

---
*Última actualización: 2026-09-05, sesión Claude Code (Sonnet 5). Actualiza esta sección al
cerrar tu turno: fecha, qué cambiaste, qué falta.*
