# System Heartbeat

Bitácora viva del estado del proyecto. **Cualquier agente (Claude Code, Codex CLI, u otro)**
que retome este trabajo debe leer este archivo primero (después de `AGENTS.md`) y actualizarlo
al terminar su turno: qué hizo, qué encontró, qué falta. No es documentación de arquitectura
(eso vive en `AGENTS.md`/PRD) — es el "dónde quedamos" entre sesiones.

## Desviación de arquitectura frente al PRD (decisión del usuario, 2026-09-05)

El PRD (§25–§27, Fase 7/9) describía un frontend Apps Script embebido en Google Sites. Se
implementó, se publicó, y **funcionaba desde `curl`/mi lado**, pero el navegador real del
usuario nunca pudo renderizar el Web App (`https://script.google.com/macros/s/.../exec`
mostraba "No se pudo abrir el archivo en este momento" — el wrapper JS de Google que Apps
Script usa para cargar el contenido en un iframe interno fallaba de forma consistente en
todas sus pruebas: distintas cuentas, redes, dispositivos, con/sin Kaspersky, en incógnito).
Las ejecuciones de `doGet()` en el servidor SIEMPRE aparecían "Completada" sin error — el
problema nunca fue nuestro código, fue algo en la capa de serving/CDN de Google para ese
deployment específico, y no se encontró causa raíz pese a bastante troubleshooting (ver
gotchas #5, #8 abajo, ahora históricos).

**El usuario decidió abandonar Apps Script/Google Sites por completo** y usar en su lugar el
patrón del repo hermano `/home/fanny/diplo2026/ah-grupo-fundador` (mismo profesor/diplomado):
frontend estático (`index.html`/`app.js`/`styles.css`) servido **directamente por el mismo
FastAPI** vía `StaticFiles`, mismo origen que `/login`/`/chat` — cero CORS, cero Apps
Script, cero Google Sites. La URL de Cloud Run **es** la app completa.

Esto reemplaza las Fases 7 y 9 del PRD tal como estaban escritas. No reintroduzcas Apps
Script/Sites salvo que el usuario lo pida explícitamente nuevamente.

## Estado por fase (PRD §40, con la desviación de arriba)

| Fase | Qué es | Estado |
|---|---|---|
| 1 | Skeleton (FastAPI + `/health`, Dockerfile) | ✅ hecho, validado local |
| 2 | Auth + Firestore (`/login`, JWT — **sin** `/register` público) | ✅ hecho, validado contra Firestore real |
| 3 | Memoria (`player_profiles`, 3 tools) | ✅ hecho, validado contra Firestore real |
| 4 | RAG (`search_elden_ring_knowledge`) | ✅ hecho, validado contra BigQuery real (5 queries de aceptación del handoff) |
| 5 | ADK (`EldenRingGuideAgent`, `/chat`) | ✅ hecho, validado contra Gemini/Vertex AI real |
| 6 | Transcript (`chat_sessions/{id}/messages`) | ✅ hecho, validado (sobrevive logout, aislamiento A/B) |
| 7 | Frontend — **estático, servido por FastAPI** (no Apps Script, ver desviación arriba) | ✅ hecho, validado end-to-end por el usuario en su navegador real |
| 8 | Cloud Run (deploy real) | ✅ desplegado y validado (`/health`, `/login`, `/chat`, frontend, todo real) |
| 9 | ~~Google Sites~~ — **N/A**, absorbida por Fase 7/8 (la URL de Cloud Run es el entregable) | ✅ cumplida por diseño, nada que hacer aquí |
| 10 | Evaluación (manual + LLM-as-judge) | ✅ hecho — 13 casos, ambos niveles, todos los criterios mínimos del PRD §36 cumplidos |

## Recursos GCP ya provisionados (proyecto `ah-estefania-alozno`)

No los vuelvas a crear/verificar desde cero — ya existen:

- APIs habilitadas: `firestore.googleapis.com`, `aiplatform.googleapis.com`,
  `bigquery.googleapis.com` (+ sub-APIs), `run.googleapis.com`, `cloudbuild.googleapis.com`,
  `artifactregistry.googleapis.com`, `secretmanager.googleapis.com`.
- Cloud Run: servicio `elden-ring-agent` en `us-central1`, desplegado desde `--source .`
  (Dockerfile), `--allow-unauthenticated` (autenticación la maneja la app, no IAM de Cloud
  Run). **URL real — es la app completa, frontend incluido**:
  `https://elden-ring-agent-704637212685.us-central1.run.app`
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
- **Proyecto Apps Script abandonado** (no borrado, solo sin usar): Script ID
  `1G7TWkov2cmtmMezsRpyPzIAUvGG9N-wGIgWTJRa-4hmeHwkUPkXtSB9R`. Sigue publicado y funcionando
  desde `curl`, pero el usuario no puede renderizarlo en su navegador (ver desviación arriba).
  No lo uses como entregable. Bórralo solo si el usuario lo pide explícitamente.

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
   Si tocas ese prompt, vuelve a probar ambos idiomas en vivo antes de dar por bueno. **Nota
   post-Fase 7**: aun así se observó una respuesta en inglés con un carácter chino suelto
   ("出血 (Bleed)") — el sesgo de idioma no está 100% resuelto, revisar en Fase 10
   (evaluación) si se repite con más frecuencia.
3. **`google-adk` instalado es 2.8.0**, con una API bastante distinta de tutoriales viejos de
   ADK (basada en `Agent`/`Runner`/`Event`, no en clases más simples). `Agent.tools` acepta
   callables planos directamente (no hace falta envolver en `FunctionTool`), y conserva su
   `__name__` — por eso las tools se registran como closures locales dentro de
   `build_agent(user_id, ...)` en vez de usar `functools.partial` (que no tiene `__name__`).
4. **WSL**: usar siempre `uv venv` + `uv pip install`, nunca `python -m venv`/`pip` a secas
   (más lento en WSL). Cuidado con `VIRTUAL_ENV` heredado de otro proyecto hermano
   (`diplo2026/.venv`) — si `uv pip install` no deja los paquetes donde esperas, hacer
   `unset VIRTUAL_ENV` antes o pasar `--python .venv/bin/python` explícito.
5. *(histórico — ya no aplica, Apps Script abandonado)* `appsscript.json`:
   `webapp.access: "ANYONE_ANONYMOUS"` es incompatible con `webapp.executeAs:
   "USER_ACCESSING"` — combinación válida: `ANYONE_ANONYMOUS` + `USER_DEPLOYING`.
6. *(histórico)* `clasp` vía el binario de Windows desde WSL es lento (>60s por invocación).
7. **`gcloud run deploy --source .` con la service account por defecto necesita 2 roles
   extra que `roles/editor` NO cubre**: `roles/storage.objectViewer` (para que el build de
   Cloud Build pueda leer el .zip de fuente subido a GCS — sin esto falla con
   `PERMISSION_DENIED... could not resolve source`) y, si usas `--set-secrets`,
   `roles/secretmanager.secretAccessor` otorgado **sobre el secreto específico**
   (`gcloud secrets add-iam-policy-binding`), no solo a nivel proyecto. Ambos son fixes
   de una sola vez por proyecto, no hace falta repetirlos en redeploys futuros. **Esto sigue
   aplicando** (no es histórico, Cloud Run sigue siendo nuestra infraestructura real).
8. *(histórico)* Abrir `script.google.com/d/<scriptId>/edit` fallaba con un error de Drive;
   `script.google.com/home/projects/<scriptId>/edit` sí abría. Las ejecuciones de `doGet()`
   en el editor (menú "Ejecuciones") siempre mostraban "Completada" sin error — la falla
   nunca fue nuestro código. Causa raíz real: nunca se encontró (ver desviación de
   arquitectura arriba) — se abandonó Apps Script en vez de seguir insistiendo.
9. **El repo hermano `/home/fanny/diplo2026/ah-grupo-fundador`** (mismo profesor) tiene un
   patrón de referencia sólido para este stack (FastAPI + ADK + Firestore/Postgres): sirve el
   frontend estático con `app.mount("/", StaticFiles(directory="frontend", html=True))`
   *después* de declarar todas las rutas de API, y usa `marked`+`DOMPurify` (CDN) para
   renderizar Markdown real en el chat en vez de texto plano — lo adoptamos ambos. **No**
   adoptamos su rate-limiting/prompt-injection/audit-log (fuera del alcance de nuestro PRD,
   equivalente a TODO-04) ni su login basado en email/localStorage (nuestro PRD pide username
   y explícitamente prohíbe `localStorage` para el token — ver PRD §25.4).

## Registro cerrado (decisión del usuario, 2026-09-05)

El usuario pidió explícitamente **quitar el registro público** porque el frontend es de
acceso anónimo y no quiere que cualquiera cree una cuenta y gaste tokens de Gemini. Cambios:

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

Ninguno. **Fases 1–10 completas.** El PRD queda cumplido salvo la desviación de arquitectura
documentada arriba (Fase 7/9, decisión explícita del usuario). Lo que sigue, si algo, es
opcional/de pulido — no hay pendientes bloqueantes.

## Evaluación (Fase 10)

- `evaluation/cases.yaml`: 13 casos, cubre las 8 categorías mínimas del PRD §34.1.
- `evaluation/llm_judge.py`: corre los 13 casos contra el sistema real (mismo camino que
  `/chat`, usuario sintético `eval-user-fase10` para no ensuciar los perfiles reales) y
  juzga el turno final de cada caso con Gemini (salida estructurada, PRD §35). Reusable:
  `PYTHONPATH=. .venv/bin/python evaluation/llm_judge.py`.
- `evaluation/transcripts.json` / `llm_judge_results.json`: evidencia cruda por caso
  (conversaciones completas + veredicto del juez), generada por la corrida real de esta
  sesión — no fabricada.
- `evaluation/manual_evaluation.md`: revisión humana de esos mismos transcripts, con tabla
  de las 8 métricas del PRD §34.2 por caso, y verificación explícita de los 6 criterios
  mínimos del PRD §36 — **todos cumplidos**.
- **Hallazgo real, no maquillado**: el juez automático marcó 1/13 casos (`lore-01`, sobre
  Malenia) como `hallucination_detected: true`. La revisión manual encontró que es un falso
  positivo — el corpus (`semantic_documents` en BigQuery) contiene dos entidades `boss`
  duplicadas para Malenia con listas de "Drops" inconsistentes entre sí, y el agente reportó
  fielmente ambos registros marcando la discrepancia, sin inventar nada. Es un defecto de
  calidad de datos **upstream** (capa Gold del proyecto Medallion, read-only para nosotros —
  P-02), no del agente ni del RAG. Documentado en detalle en `manual_evaluation.md` punto 1.
- El episodio de mezcla de idioma visto en Fase 5 (un carácter chino suelto en una respuesta
  en inglés) no se reprodujo en los 13 casos de esta batería, pero sigue documentado como
  riesgo conocido (no 100% resuelto, solo mitigado) — ver gotcha #2 abajo.

## App real en Cloud Run (Fases 7 + 8, frontend + backend juntos)

## App real en Cloud Run (Fases 7 + 8, frontend + backend juntos)

- Servicio: `elden-ring-agent`, región `us-central1`, proyecto `ah-estefania-alozno`.
- **URL** (frontend + API, todo en uno): `https://elden-ring-agent-704637212685.us-central1.run.app`
- `backend/main.py` monta `frontend/` (StaticFiles, `html=True`) en `/`, **después** de las
  rutas `/health`, `/login`, `/chat` — así el mount no las tapa. Sin CORS (mismo origen).
- Validado con curl real: `/`, `/app.js`, `/styles.css` → 200; `/login` (los 3 usuarios
  reales) → 200; `/chat` completo (RAG + Gemini + fuentes, en español e inglés) → 200.
  **Validado además por el usuario directamente en su navegador**: login + chat + logout
  funcionando.
- Redeploy tras cambios de código (mismo comando de siempre, incluye el frontend porque ya
  no está en `.dockerignore`):
  ```bash
  gcloud run deploy elden-ring-agent --project ah-estefania-alozno --region us-central1 \
    --source . --allow-unauthenticated --port 8080 \
    --set-env-vars BQ_VERTEX_REMOTE_MODEL=elden_ring_embedding_model,VERTEX_EMBEDDING_MODEL=gemini-embedding-001,GEMINI_MODEL=gemini-2.5-flash,VERTEX_LOCATION=us-central1 \
    --set-secrets JWT_SECRET=jwt-secret:latest
  ```
  (los env vars con default correcto en `backend/config.py` no hace falta repetirlos — ver
  esa tabla si agregas uno nuevo).

## Config local

- `.env` existe local (gitignored) con los mismos valores que se usaron para Cloud Run:
  `GEMINI_MODEL=gemini-2.5-flash`, `VERTEX_LOCATION=us-central1`, resto de `.env.example`.
  `JWT_SECRET` local sigue siendo el placeholder corto de dev — el real y fuerte vive solo en
  Secret Manager (`jwt-secret`), no en este repo ni en `.env`.
- Tests: `.venv/bin/python -m pytest tests/` → 26 passed (todo mockeado, no pega a GCP).
  Validación contra infra real (Firestore/BigQuery/Vertex AI/Cloud Run) se hizo manualmente
  vía smoke tests con `curl` durante el desarrollo — no quedaron como tests automatizados de
  integración.

## Próximo paso sugerido

Ninguno bloqueante — el MVP (PRD §44, con la desviación de Fase 7/9 documentada) está
completo. Si se retoma el proyecto, lo más valioso sería: (a) preparar el PDF de entrega
(PRD §45.9) con las capturas/evidencia ya generada, (b) si se quiere pulir más, investigar
por qué a veces se mezcla idioma (gotcha #2) con una batería más grande de casos en inglés.

---
*Última actualización: 2026-09-05, sesión Claude Code (Sonnet 5) — se abandonó Apps
Script/Google Sites (Fase 7/9 del PRD) por un problema de rendering nunca resuelto del lado
de Google, y se reemplazó por un frontend estático servido directo desde el mismo FastAPI
(patrón tomado de `ah-grupo-fundador`), desplegado y validado end-to-end en Cloud Run por el
usuario en su navegador real. Fase 10 (Evaluación) completa: 13 casos, ambos niveles
requeridos, todos los criterios mínimos del PRD §36 cumplidos, con un hallazgo real de
calidad de datos upstream documentado honestamente. **Fases 1-10 completas.** Actualiza
esta sección al cerrar tu turno: fecha, qué cambiaste, qué falta.*
