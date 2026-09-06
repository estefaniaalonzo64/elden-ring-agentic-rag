# Elden Ring Agentic RAG Guide

Guía conversacional agéntica sobre Elden Ring. Ver [`AGENTS.md`](./AGENTS.md) para principios,
guardrails y mapa de skills, y [`PRD_Elden_Ring_Agentic_RAG_MVP.md`](./PRD_Elden_Ring_Agentic_RAG_MVP.md)
para el detalle completo de requisitos.

## Desarrollo local

```bash
uv venv
uv pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn backend.main:app --reload
```

`GET /health` debe responder `{"status": "ok"}`.

## Tests

```bash
.venv/bin/python -m pytest tests/
```

## Docker

```bash
docker build -t elden-ring-agent .
docker run -p 8080:8080 --env-file .env elden-ring-agent
```

## Frontend (Google Apps Script)

Código en [`frontend/apps-script/`](./frontend/apps-script/) (`Code.gs`, `Index.html`,
`styles.html`, `script.html`). El navegador llama al backend directamente vía `fetch()`
(por eso el backend habilita CORS permisivo — ver TODO-06 en el PRD).

**Ya está publicado.** Proyecto Apps Script creado y deployado vía `clasp`
(script id en `frontend/apps-script/.clasp.json`, detalle completo en
`SYSTEM_HEARTBEAT.md`). URL pública del Web App:

```
https://script.google.com/macros/s/AKfycbyVXj_a9TekA26uc8fOf8CtsmPX_uMZqu51B9h3vanrWWcyf2LWQlItqUPKWf7Z5ViM/exec
```

Pendiente: setear `BACKEND_URL` en Script Properties una vez exista la URL de Cloud Run
(Fase 8) — hasta entonces el login/chat muestran "BACKEND_URL no está configurado".

Para volver a publicar cambios de código:

```bash
cd frontend/apps-script
clasp push --force
```

`appsscript.json` usa `webapp.access: "ANYONE_ANONYMOUS"` (sin login de Google) +
`webapp.executeAs: "USER_DEPLOYING"` — esa combinación es obligatoria: `ANYONE_ANONYMOUS`
no es compatible con `USER_ACCESSING` (no hay identidad de usuario que "ejecutar como" si
el acceso es anónimo). Ver el gotcha #5 en `SYSTEM_HEARTBEAT.md` si esto cambia y `clasp
push` empieza a fallar con "Invalid manifest file".
