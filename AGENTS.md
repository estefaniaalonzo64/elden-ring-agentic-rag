# AGENTS.md — Elden Ring Agentic RAG Guide

Orquestador **lean** para cualquier agente (Claude Code, Codex CLI, u otro) que trabaje en este
repositorio. Este archivo es la fuente de verdad compartida entre agentes. No repite el PRD:
solo fija principios no-negociables, hechos clave y cuándo delegar a un skill.

> Fuente completa de requisitos: [`PRD_Elden_Ring_Agentic_RAG_MVP.md`](./PRD_Elden_Ring_Agentic_RAG_MVP.md).
> Si algo aquí y el PRD difieren, el PRD manda; actualiza este archivo.

## 0. Qué es este proyecto

Guía conversacional agéntica sobre Elden Ring que **reutiliza como Data Product terminado**
la capa Gold de un proyecto Medallion previo (BigQuery). Agrega encima: un agente ADK con
tools, RAG vía `VECTOR_SEARCH`, memoria de jugador en Firestore, autenticación propia y un
frontend Apps Script embebido en Google Sites, corriendo en Cloud Run.

```
Jugador → Apps Script (Sites) → FastAPI (Cloud Run) → ADK Agent → tools → BigQuery/Firestore/Gemini
```

## 1. Principios no negociables (ver PRD §5)

- **P-01 Grounding estricto**: el agente nunca usa conocimiento pretenido de Gemini como
  hecho sobre Elden Ring. Todo hecho debe venir de `search_elden_ring_knowledge`. Sin evidencia
  suficiente, responder literalmente algo equivalente a *"No tengo suficiente información en mi
  base de conocimiento para responder eso con confianza."* — nunca inventar.
- **P-02 Data Product reutilizable**: nunca reconstruir Bronze/Silver/templates semánticos.
  `semantic_documents` y `entity_embeddings` (384-dim, legado) son **read-only e intocables**.
- **P-03 Memoria explícita**: contexto de conversación ≠ memoria persistente del jugador ≠
  transcript. Son tres cosas distintas (ver skill `player-memory`).
- **P-04 Complejidad mínima**: un solo agente ADK (`EldenRingGuideAgent`) con 4 tools. No
  multiagente sin justificación funcional nueva.
- **P-05 Cost conscious**: Cloud Run + Firestore + BigQuery + modelos Gemini configurables;
  búsqueda vectorial exacta (sin índice ANN) mientras el corpus sea ~1.2k documentos.

## 2. Guardrails de seguridad (aplican siempre, en cualquier skill)

- `user_id` **solo** sale del token autenticado en el backend. El LLM **nunca** elige ni recibe
  un `user_id` como parámetro libre.
- Nunca almacenar contraseñas en texto plano (PBKDF2-HMAC-SHA256+salt, o bcrypt/argon2).
- Las queries de la tool RAG a BigQuery son **read-only**.
- Secretos (`JWT_SECRET`, credenciales) solo por variables de entorno; nunca commitear.
- No ejecutar operaciones destructivas de `gcloud`/`bq`/`gcloud firestore` (delete, truncate,
  overwrite de datasets Gold) sin confirmación explícita del usuario — ver skill `gcp-provisioning`.

## 3. Hechos clave del proyecto

| Concepto | Valor |
|---|---|
| Proyecto GCP | `ah-estefania-alozno` |
| Dataset Gold | `elden_ring_gold` (BigQuery, ya existe, no modificar su contenido base) |
| Tabla contrato de texto | `semantic_documents` (read-only) |
| Embeddings legado (no usar/no tocar) | `entity_embeddings` (384-dim, `intfloat/multilingual-e5-small`) |
| Embeddings nuevos (RAG del agente) | `entity_embeddings_vertex` (768-dim, Vertex/Gemini) — contrato en `VERTEX_RAG_HANDOFF.md` (**debe existir antes de cerrar el skill `rag-bigquery`**) |
| Memoria de aplicación | Firestore: `users`, `player_profiles`, `chat_sessions`, `chat_sessions/{id}/messages` |
| Framework agéntico | Google ADK — un agente: `EldenRingGuideAgent` |
| Tools del agente | `search_elden_ring_knowledge`, `get_player_profile`, `update_player_memory`, `forget_player_memory` |
| LLM | Gemini vía Vertex AI, configurable por `GEMINI_MODEL` / `VERTEX_LOCATION` |
| Backend | FastAPI en Cloud Run, escucha `0.0.0.0:$PORT` |
| Frontend | Google Apps Script (Login/Registro/Chat) embebido en Google Sites |
| Dependencias prohibidas en el backend agéntico | `faiss`, `torch`, `sentence-transformers` |

## 4. Skills — dónde vive cada procedimiento

Este archivo **no** contiene procedimientos paso a paso. Antes de trabajar en un dominio,
lee por completo el skill correspondiente en `.agents/skills/<nombre>/SKILL.md`
(agentes Claude Code: usa la tool `Skill` con estos mismos nombres, definidos también en
`.claude/skills/`; ambas carpetas apuntan al mismo contenido).

| Skill | Úsalo cuando... | Fase PRD |
|---|---|---|
| `gcp-provisioning` | necesites habilitar APIs, crear/verificar Firestore, verificar BigQuery, desplegar o inspeccionar Cloud Run vía `gcloud`/`bq` CLI | Fase 8, §30, §33 |
| `auth-service` | implementes/toques registro, login, hashing de password, JWT, dependencia de auth | Fase 2, §12, §13.1 |
| `player-memory` | implementes/toques perfil del jugador, tools de memoria, aislamiento por usuario, transcript de conversación | Fase 3 y 6, §13.2–13.4, §14, §15 |
| `rag-bigquery` | implementes/toques la tool de retrieval, `VECTOR_SEARCH`, embeddings de query | Fase 4, §16, §39 |
| `elden-agent` | implementes/toques el agente ADK, su system instruction, el recomendador, grounding, multilingüe, fuentes | Fase 5, §17–§23 |
| `frontend-delivery` | implementes/toques Apps Script, pantallas Login/Registro/Chat, embebido en Google Sites, CORS | Fase 7 y 9, §25–§27 |
| `evaluation` | generes casos de evaluación manual o el LLM-as-a-judge, o midas contra los criterios mínimos | Fase 10, §34–§36 |

Regla de oro: **si el skill existe, no improvises el procedimiento desde cero ni releas el PRD
entero** — el skill ya extrajo lo operativo. Vuelve al PRD solo para matices no cubiertos.

## 5. Estructura de código esperada (se crea bajo demanda, no de antemano)

Ver PRD §31 para el árbol completo (`backend/`, `frontend/apps-script/`, `evaluation/`, `tests/`).
Si el material del profesor ya trae una estructura funcional equivalente, reutilízala en vez de
refactorizar por estética (indicación explícita del PRD).

## 6. Definition of Done

La lista completa está en PRD §44. No la dupliques aquí; consúltala antes de declarar el MVP
terminado.
