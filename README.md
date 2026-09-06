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

## Frontend (estático, servido por el mismo backend)

Código en [`frontend/`](./frontend/) (`index.html`, `app.js`, `styles.css`) — sin build,
sin dependencias propias. `backend/main.py` lo monta con `StaticFiles` en `/`, **mismo
origen** que `/login`/`/chat` (sin CORS). Login/logout usan estado en memoria de JS, nunca
`localStorage` (PRD §25.4). El chat renderiza Markdown real (`marked` + `DOMPurify` vía CDN)
para que `**bold**`/`### headers` de las respuestas del agente se vean bien.

> Se abandonó el frontend Apps Script/Google Sites original (PRD §25–§27, Fase 7/9): se
> publicó y funcionaba desde `curl`, pero el navegador real nunca pudo renderizarlo (ver
> "Desviación de arquitectura" en `SYSTEM_HEARTBEAT.md`). Este frontend estático reemplaza
> esa parte del PRD — la URL de Cloud Run de abajo **es** la app completa, no hace falta
> Google Sites.

**Ya está desplegado**, junto con el backend, en la misma URL de Cloud Run:

```
https://elden-ring-agent-704637212685.us-central1.run.app
```

Para volver a publicar cambios (de frontend o backend): mismo comando `gcloud run deploy`
de la sección Docker/Cloud Run (ver `SYSTEM_HEARTBEAT.md` para el comando completo con env
vars) — `frontend/` ya se copia a la imagen (`Dockerfile`).
