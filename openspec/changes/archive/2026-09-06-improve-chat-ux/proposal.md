## Why

El MVP ya funciona de punta a punta (login, chat con RAG grounded, memoria de jugador). El
propio PRD dejó fuera del MVP, sin bloquear la entrega, el historial navegable de
conversaciones (TODO-01) y cualquier pulido de frontend más allá de lo mínimo (TODO-08). Con
el MVP cerrado, el usuario quiere resolver esas brechas de experiencia: poder retomar
conversaciones anteriores en vez de perderlas al hacer logout, ver que el sistema está
trabajando mientras `POST /chat` procesa (la llamada es síncrona y puede tardar varios
segundos por la vuelta RAG + LLM, y hoy la UI se queda muda durante ese tiempo), y mejorar el
acabado visual general del chat.

## What Changes

- Nuevo endpoint `GET /sessions`: lista las `chat_sessions` del usuario autenticado (más
  recientes primero), con un preview corto (primer mensaje de usuario) para identificarlas.
- Nuevo endpoint `GET /sessions/{session_id}/messages`: devuelve el transcript completo
  (`role`, `content`, `sources`, `created_at`) de una sesión propia del usuario autenticado.
- Nuevo endpoint `POST /sessions`: crea una `chat_session` nueva bajo demanda, para permitir
  "nueva conversación" sin cerrar sesión y volver a loguearse.
- Frontend: panel "Mis conversaciones" en la pantalla de Chat que lista las sesiones pasadas,
  permite abrir una (carga su transcript en el área de mensajes, en modo solo lectura de
  continuación — se puede seguir escribiendo) y un botón "Nueva conversación".
- Frontend: indicador visual de progreso ("Pensando..." / "Buscando información...") mientras
  se espera la respuesta de `POST /chat`; se oculta al llegar la respuesta o un error, y se
  bloquea el reenvío duplicado del formulario mientras está visible.
- Pulido visual del tema oscuro existente: estados vacíos del panel de conversaciones,
  legibilidad del indicador de progreso, ajustes de espaciado/responsive para que el panel
  conviva con el chat en pantallas angostas. No se adopta React/Next ni un rediseño completo
  (eso sigue siendo TODO-08, fuera de alcance).

## Capabilities

### New Capabilities

- `chat-history`: listar las conversaciones previas del usuario autenticado, abrir una para
  continuarla, y crear conversaciones nuevas bajo demanda — sin romper el aislamiento por
  `user_id` (P-03 / AGENTS.md §2).
- `chat-progress-indicator`: comunicar visualmente en la UI que el agente está procesando el
  turno actual, desde el envío del mensaje hasta que llega la respuesta (o un error).

### Modified Capabilities

_Ninguna._ Este es el primer change de OpenSpec del proyecto: no existe todavía una spec
formal para el login o el chat existentes, así que no hay una capability previa que modificar
— `chat-history` y `chat-progress-indicator` son aditivas sobre el comportamiento actual de
`POST /chat` sin cambiar su contrato.

## Impact

- **Backend**: `backend/main.py` (nuevas rutas `GET /sessions`, `GET /sessions/{id}/messages`,
  `POST /sessions`, todas detrás de `get_current_user_id`); `backend/repositories/firestore_repository.py`
  (queries de listado filtradas por `user_id`, lectura de subcolección `messages`);
  `backend/models/api.py` (nuevos modelos de respuesta). Sin cambios al contrato del agente ADK,
  a las tools, ni a BigQuery/embeddings.
- **Frontend**: `frontend/index.html` (panel de conversaciones, botón nueva conversación,
  marcador de progreso), `frontend/app.js` (fetch a los nuevos endpoints, máquina de estados
  simple para el indicador, deshabilitar envío mientras está en curso), `frontend/styles.css`
  (estilos del panel y del indicador, ajustes responsive).
- **Docs**: `.agents/skills/player-memory/SKILL.md` y `.agents/skills/frontend-delivery/SKILL.md`
  (y sus copias `.claude/skills/`) mencionan hoy TODO-01 como explícitamente fuera de alcance —
  quedan desactualizados una vez implementado esto y deben reflejar el nuevo comportamiento
  como parte de las tasks de este change, no del PRD original (que no se edita).
- **Seguridad**: los tres endpoints nuevos deben filtrar siempre por el `user_id` del JWT, igual
  que `POST /chat` ya hace con `get_chat_session` — caso de aceptación G (aislamiento
  usuario A/B) se extiende a ellos.
