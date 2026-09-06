# CLAUDE.md

Este proyecto usa [`AGENTS.md`](./AGENTS.md) como fuente única de verdad para principios,
guardrails, hechos clave y mapa de skills. **Léelo primero** — aplica a ti igual que a
cualquier otro agente. Este archivo solo añade lo específico de Claude Code.

## Invocación de skills

Los mismos skills documentados en `AGENTS.md` §4 están registrados como Skills de Claude Code
en `.claude/skills/<nombre>/SKILL.md` (idéntico contenido a `.agents/skills/<nombre>/SKILL.md`,
enlazado por symlink). Invócalos con la tool `Skill` usando el nombre de la carpeta:

```
gcp-provisioning · auth-service · player-memory · rag-bigquery · elden-agent · frontend-delivery · evaluation
```

No repliques manualmente el procedimiento de un skill si puedes invocarlo — el skill ya
resume lo operativo del PRD para ese dominio.

## Acciones con gcloud / bq CLI

El skill `gcp-provisioning` te da la facultad de levantar y verificar recursos en el proyecto
GCP `ah-estefania-alozno` (Firestore, BigQuery, Vertex AI, Cloud Run, IAM) vía `gcloud`/`bq`.
Antes de ejecutar cualquier comando de ese skill que **cree, modifique, despliegue o borre**
recursos (no solo `describe`/`list`), sigue la política estándar de esta sesión: comunica la
acción y confirma con el usuario, salvo que ya haya autorizado ese comando exacto en esta
conversación. Los comandos de solo lectura (`gcloud ... describe`, `bq show`, `bq query` de
lectura) puedes ejecutarlos libremente para diagnóstico.

## Notas de entorno

- No es un repositorio git todavía (`git init` si el usuario lo pide antes de commitear).
- El PRD completo vive en `PRD_Elden_Ring_Agentic_RAG_MVP.md` en la raíz del repo.
