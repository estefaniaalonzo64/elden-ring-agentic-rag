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

Publicarlo requiere una sesión de Google interactiva, así que estos pasos son manuales:

1. Instalar `clasp` y autenticarte (una vez): `npm install -g @google/clasp && clasp login`.
2. Crear el proyecto Apps Script apuntando a esta carpeta:
   `cd frontend/apps-script && clasp create --type webapp --title "Elden Ring Guide"`.
3. Subir el código: `clasp push`.
4. En el editor de Apps Script (`clasp open`): Project Settings → Script Properties →
   agregar `BACKEND_URL` con la URL del servicio Cloud Run (Fase 8).
5. Deploy → New deployment → Web app (Execute as: User accessing the app, Access: Anyone).
6. Incrustar la URL del Web App publicado en un Google Site (Fase 9).
