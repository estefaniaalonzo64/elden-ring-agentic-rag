## Context

Ver `proposal.md` - Why. Estado actual relevante para el diseño:

- `POST /login` crea una única `chat_session` por login (`backend/auth/service.py:authenticate`)
  y el frontend guarda `session_id` solo en memoria de módulo (`frontend/app.js`). No existe
  hoy ningún endpoint para listar o releer `chat_sessions` — el transcript se escribe en
  Firestore (`add_chat_message`) pero nunca se vuelve a leer.
  El caso de aceptación G (aislamiento usuario A/B) ya se prueba sobre `POST /chat` vía
  `session.get("user_id") != user_id`; los endpoints nuevos deben repetir exactamente ese
  patrón.
- `POST /chat` es una llamada síncrona (`backend/agent/runner.py:run_turn`) que puede incluir
  una vuelta a BigQuery (`VECTOR_SEARCH`) y una o más llamadas a Gemini vía ADK. El frontend
  hoy no muestra ningún estado mientras esa promesa está pendiente.
- El frontend es HTML/CSS/JS vanilla sin build step, servido como estático por el mismo
  FastAPI (`frontend-delivery` skill). Cualquier solución debe seguir siendo vanilla — no se
  introduce un bundler ni un framework (eso sería TODO-08, explícitamente fuera de alcance).

## Goals / Non-Goals

**Goals:**
- Exponer lectura de `chat_sessions`/`messages` ya persistidos, filtrada estrictamente por el
  `user_id` del JWT, reusando `get_current_user_id` tal como hace `/chat`.
- Permitir crear una `chat_session` nueva sin pasar por `/login`.
- Dar feedback visual inmediato y confiable durante la espera de `/chat`, sin cambiar el
  contrato de esa ruta.
- Mantener el frontend 100% vanilla (sin bundler, sin dependencias nuevas más allá de las que
  ya se cargan por CDN).

**Non-Goals:**
- No se implementa streaming de la respuesta del agente (SSE/WebSockets) — el indicador de
  progreso es un estado binario "procesando/no procesando" en el cliente, no un streaming de
  los pasos internos del agente. Eso queda fuera de este change.
- No se implementa edición ni borrado de conversaciones, ni feedback 👍👎 (TODO-02) — solo
  listar, abrir, continuar y crear.
- No se agregan endpoints administrativos de otros usuarios (TODO-03 sigue fuera de alcance);
  `GET /sessions` solo devuelve las del usuario autenticado.
- No se rediseña visualmente el chat con un framework nuevo (TODO-08 completo sigue fuera de
  alcance) — el pulido visual de este change se limita al panel nuevo y al indicador.

## Decisions

**Endpoints nuevos en `backend/main.py`, no un router aparte.** El proyecto ya define todas
sus rutas directamente en `main.py` (solo 3 endpoints hoy); mantener el mismo estilo hasta que
el archivo lo justifique evita una reestructuración no pedida.

**Preview de conversación = primer mensaje de usuario, truncado.** Alternativa considerada:
generar un título con el LLM (una llamada extra a Gemini por conversación). Se descarta por
costo y complejidad (P-05 cost conscious) — un preview derivado del primer mensaje ya
identifica la conversación sin llamadas adicionales.

**Reabrir una conversación reutiliza `POST /chat` sin cambios.** Alternativa considerada:
un endpoint distinto para "continuar" una sesión. Se descarta porque `POST /chat` ya recibe
`session_id` en el payload y ya valida que pertenezca al usuario — reabrir una conversación
solo cambia qué `session_id` guarda el frontend en su estado, no el contrato del backend.

**Indicador de progreso es un estado del cliente, no un campo del backend.** El frontend marca
"procesando" al hacer submit y lo desmarca en `.then()`/`.catch()` de la misma promesa que ya
existe para `POST /chat`. No requiere cambios de contrato en el backend ni polling adicional.

**`list_chat_sessions` ordena en Python, no con `order_by()` de Firestore.** Descubierto
durante la implementación: `where("user_id", "==", ...).order_by("created_at")` requiere un
índice compuesto que Firestore no crea automáticamente (`FailedPrecondition: 400 The query
requires an index`, confirmado contra el proyecto real). Alternativa considerada: crear el
índice compuesto vía `gcloud`/consola. Se descarta para no depender de un paso manual de
provisioning por una consulta que devuelve, como mucho, unas pocas decenas de documentos por
usuario — se ordena la lista en memoria después de `stream()`.

**El panel de conversaciones se carga bajo demanda, no en cada login.** `GET /sessions` se
llama cuando el usuario abre el panel (o al entrar a la pantalla de chat), no en cada mensaje,
para no agregar una llamada de red por turno.

**Un `chat_session` se crea de forma perezosa, no en `/login` ni en `POST /sessions`.**
Decisión revisada tras el primer despliegue: la versión inicial de este change hacía que
`POST /login` y `POST /sessions` escribieran el documento en Firestore de inmediato, lo que
llenó el panel de sesiones vacías (huérfanas) apenas unos minutos de uso real — 41 de 53
documentos existentes no tenían un solo mensaje. Ambos endpoints ahora solo generan y
devuelven un `session_id` (`uuid.uuid4()`) sin tocar Firestore; `POST /chat` es quien crea el
documento (`create_chat_session(user_id, session_id=...)`) la primera vez que ese
`session_id` no existe, en el mismo turno en que llega el primer mensaje real. Así, "iniciar
sesión" o pulsar "Nueva conversación" sin escribir nada nunca deja rastro en `GET /sessions`.
Se sigue verificando que una sesión ya existente pertenezca al `user_id` autenticado antes de
usarla (aislamiento sin cambios) — la creación perezosa solo aplica cuando la sesión no existe
todavía.

## Risks / Trade-offs

- [`POST /chat` ahora puede crear la sesión implícitamente en vez de solo 404 ante un
  `session_id` desconocido] → esto es seguro porque el documento se crea con el `user_id` del
  JWT, nunca con uno inventado por el payload; un `session_id` que ya pertenece a otro usuario
  sigue devolviendo 404 sin crear ni sobrescribir nada. Mitigación: sin acción adicional
  necesaria, el aislamiento por usuario no cambia.
- [Cargar el transcript completo de una conversación larga en una sola respuesta] → con las
  conversaciones cortas típicas de este proyecto (pocas decenas de mensajes) no hay problema
  de tamaño de payload; si el corpus de mensajes creciera mucho, se necesitaría paginación
  (no incluida aquí, ver Open Questions).
- [El indicador de progreso es puramente del cliente] → si el usuario recarga la página a
  mitad de un turno en curso, el estado "procesando" se pierde junto con todo el estado de
  sesión en memoria (comportamiento ya existente y documentado en `frontend-delivery`: recargar
  vuelve a Login). No es una regresión nueva.

## Migration Plan

No hay migración de esquema: los endpoints nuevos son de solo lectura/creación sobre
colecciones (`chat_sessions`, `messages`) que ya existen con el mismo esquema. Despliegue
normal vía el flujo ya establecido del skill `gcp-provisioning` (build + deploy a Cloud Run);
no se requiere backfill ni cambios de esquema en Firestore. Rollback: revertir el despliegue de
la imagen anterior, sin pasos adicionales, porque no se modifica el esquema de datos.

Sí hubo una limpieza de datos puntual, hecha una sola vez tras detectar el problema de
sesiones huérfanas (ver decisión de creación perezosa arriba): se borraron los 41
`chat_sessions` existentes sin ningún mensaje (de 53 totales, incluyendo cuentas reales y de
prueba), dejando los 12 que sí tenían transcript. No hace falta repetirla — con la creación
perezosa ya no vuelven a generarse sesiones vacías.

## Open Questions

- Si el número de conversaciones o mensajes por usuario creciera mucho, `GET /sessions` y
  `GET /sessions/{id}/messages` necesitarían paginación — no es un problema con el volumen
  actual del proyecto y se puede resolver después sin cambiar el contrato de alto nivel (solo
  agregaría parámetros opcionales de paginación).
