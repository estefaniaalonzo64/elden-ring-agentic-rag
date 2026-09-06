## 1. Backend — repositorio Firestore

- [x] 1.1 Agregar `list_chat_sessions(user_id)` en `backend/repositories/firestore_repository.py`
      que consulte `chat_sessions` filtrando por `user_id` y ordene por `created_at` descendente;
      verificar con un test unitario que mockea el cliente de Firestore.
- [x] 1.2 Agregar `get_chat_messages(session_id)` en el mismo módulo, que lea la subcolección
      `chat_sessions/{session_id}/messages` ordenada por `created_at` ascendente; verificar con
      un test unitario equivalente.
- [x] 1.3 Exponer `create_chat_session` (ya existe) para su uso directo desde un endpoint nuevo
      (no solo desde `authenticate`); confirmar que no requiere cambios de firma.

## 2. Backend — modelos y endpoints

- [x] 2.1 Agregar a `backend/models/api.py` los modelos `ChatSessionSummary` (`session_id`,
      `created_at`, `preview`), `ChatSessionListResponse`, `ChatMessage` (`role`, `content`,
      `sources`, `created_at`) y `ChatMessagesResponse`.
- [x] 2.2 Implementar `GET /sessions` en `backend/main.py` detrás de
      `Depends(get_current_user_id)`, usando `list_chat_sessions(user_id)` y derivando el
      `preview` del primer mensaje de usuario de cada sesión (o cadena vacía si no tiene
      mensajes); verificar con un test que dos usuarios distintos solo ven sus propias sesiones
      (mismo patrón que `test_chat_rejects_session_belonging_to_another_user`).
- [x] 2.3 Implementar `GET /sessions/{session_id}/messages` en `backend/main.py`, validando
      que la sesión exista y pertenezca al `user_id` autenticado (igual que ya hace
      `chat_endpoint` con `get_chat_session`) antes de devolver `get_chat_messages`; verificar
      con tests que cubran: sesión propia con mensajes, sesión ajena (404, sin filtrar
      contenido), sesión inexistente (404).
- [x] 2.4 Implementar `POST /sessions` en `backend/main.py` detrás de
      `Depends(get_current_user_id)` que llame `create_chat_session(user_id)` y devuelva el
      `session_id` nuevo; verificar con un test que el `user_id` de la sesión creada coincide
      con el del token, nunca con un valor del payload.

## 3. Frontend — indicador de progreso

- [x] 3.1 En `frontend/index.html`, agregar el elemento del indicador de progreso ("Pensando..."
      / "Buscando información...") dentro de la pantalla de chat, oculto por defecto.
- [x] 3.2 En `frontend/app.js`, mostrar el indicador al enviar el formulario de chat y
      deshabilitar el botón de envío hasta que la promesa de `POST /chat` resuelva o falle;
      ocultarlo y rehabilitar el botón tanto en `.then()` como en `.catch()`. Verificado que
      `POST /chat` real (contra Firestore/BigQuery/Gemini reales) devuelve la respuesta que
      dispara el `.then()`/`.catch()` que oculta el indicador (ver §6.1 de este apply); **no**
      se pudo confirmar visualmente en un navegador real por falta de herramientas de browser
      headless en este entorno (sin chromium/playwright instalados) — pendiente de una pasada
      manual en el navegador (ver tarea 6.3).
- [x] 3.3 En `frontend/styles.css`, dar estilo al indicador (visible, legible sobre el tema
      oscuro existente) reutilizando las variables de color ya definidas en `:root`.

## 4. Frontend — panel "Mis conversaciones"

- [x] 4.1 En `frontend/index.html`, agregar el panel de conversaciones a la pantalla de chat
      (lista de sesiones + botón "Nueva conversación"), sin quitar los elementos existentes de
      login/chat.
- [x] 4.2 En `frontend/app.js`, al entrar a la pantalla de chat, llamar `GET /sessions` y
      renderizar la lista (preview + fecha); manejar el caso de lista vacía con un mensaje en
      vez de dejar el panel en blanco. Verificado por API real (curl) que `GET /sessions`
      devuelve la forma esperada por `renderConversations`.
- [x] 4.3 En `frontend/app.js`, al hacer click en una conversación de la lista, llamar
      `GET /sessions/{id}/messages`, limpiar el área de mensajes actual, renderizar el
      transcript recuperado (reusando `appendMessage` para cada mensaje) y actualizar
      `state.sessionId` para que los mensajes nuevos se agreguen a esa conversación. Verificado
      por API real que `GET /sessions/{id}/messages` devuelve `role`/`content`/`sources` en el
      formato que consume `appendMessage`.
- [x] 4.4 En `frontend/app.js`, implementar el botón "Nueva conversación": llamar
      `POST /sessions`, limpiar el área de mensajes, actualizar `state.sessionId` con el nuevo
      id y refrescar la lista del panel para que la nueva conversación aparezca. Verificado por
      API real que `POST /sessions` crea una sesión nueva que luego aparece primera en
      `GET /sessions`.
- [x] 4.5 En `frontend/styles.css`, dar estilo al panel (lista, estado vacío, elemento activo) y
      ajustar el layout responsive para que el panel y el chat convivan en pantallas angostas
      sin romper el diseño existente de `.screen`.

## 5. Documentación

- [x] 5.1 Actualizar `.agents/skills/player-memory/SKILL.md` (y su copia en
      `.claude/skills/player-memory/SKILL.md`) para quitar la mención de "TODO-01 fuera de
      alcance" en la sección "Sesión nueva por login" y reflejar que el historial ya es
      navegable. (Ambas copias son hardlinks al mismo inodo — un solo edit actualizó las dos.)
- [x] 5.2 Actualizar `.agents/skills/frontend-delivery/SKILL.md` (y su copia en
      `.claude/skills/frontend-delivery/SKILL.md`) para documentar el panel de conversaciones y
      el indicador de progreso como parte de la pantalla de Chat, y quitar la mención de
      "no agregar historial de conversaciones" que ya no aplica. (Mismo hardlink que arriba.)

## 6. Verificación de aislamiento y regresión

- [x] 6.1 Ejecutar `pytest tests/test_chat.py tests/test_auth.py -v` y confirmar que los tests
      existentes siguen pasando sin modificaciones no relacionadas. (17/17 tests pasan,
      incluyendo los 8 nuevos de `tests/test_chat_history.py`.)
- [x] 6.2 Con dos usuarios de prueba (roster fijo vía `scripts/create_user.py`), validar
      manualmente en el navegador que el usuario A nunca ve conversaciones ni transcripts del
      usuario B en el panel — extensión del caso de aceptación G a las rutas nuevas. Validado
      vía API real (backend local + Firestore/BigQuery/Gemini reales del proyecto
      `ah-estefania-alozno`, no mocks) con dos usuarios de prueba (`qa-test-chatux`,
      `qa-test-chatux-b`): B nunca ve las sesiones de A en `GET /sessions`, y recibe 404 tanto
      en `GET /sessions/{id}/messages` como en `POST /chat` sobre una sesión de A. No se hizo
      en un navegador real (ver 6.3) sino a nivel HTTP directo, que es donde vive la lógica de
      aislamiento.
- [ ] 6.3 Validar manualmente en el navegador (no solo `curl`, por el aprendizaje ya
      documentado en `frontend-delivery`) el flujo completo: login → ver panel con
      conversaciones previas → abrir una → continuarla → crear una nueva → ver el indicador de
      progreso durante un turno real contra el backend desplegado. **Pendiente**: este entorno
      no tiene un navegador ni herramientas headless (chromium/playwright) instaladas, así que
      esta pasada visual todavía no se hizo — ver nota en el reporte de esta sesión de apply.

## 7. Corrección post-deploy: no persistir conversaciones sin interacción

Encontrado por el usuario tras el primer despliegue: el panel de conversaciones se llenaba de
entradas vacías porque `POST /login` y `POST /sessions` escribían el `chat_session` en
Firestore de inmediato, aunque el usuario nunca llegara a escribir nada.

- [x] 7.1 Cambiar `create_chat_session` (`backend/repositories/firestore_repository.py`) para
      aceptar un `session_id` explícito opcional, en vez de generar siempre uno nuevo.
- [x] 7.2 Cambiar `authenticate()` (`backend/auth/service.py`) para generar el `session_id` de
      login con `uuid.uuid4()` sin escribir a Firestore.
- [x] 7.3 Cambiar `POST /sessions` (`backend/main.py`) para devolver un `session_id` nuevo sin
      escribir a Firestore.
- [x] 7.4 Cambiar `POST /chat` (`backend/main.py`) para crear el `chat_session` de forma
      perezosa (con el `user_id` del JWT) la primera vez que su `session_id` no existe, en vez
      de responder 404; mantener el 404 cuando la sesión sí existe pero pertenece a otro
      usuario. Verificado con `tests/test_chat.py` (creación perezosa + no-recreación de una
      sesión existente) y en vivo contra Firestore real: ni login ni "nueva conversación" dejan
      documento alguno hasta el primer mensaje.
- [x] 7.5 Actualizar `specs/chat-history/spec.md` y `design.md` de este mismo change para
      reflejar la creación perezosa (nuevo requirement "No persistir conversaciones sin
      interacción"), ya que el change todavía no estaba archivado.
- [x] 7.6 Limpieza de datos puntual: borrar en Firestore los `chat_sessions` existentes sin
      ningún mensaje. Ejecutado una sola vez contra el proyecto real tras confirmar con el
      usuario el alcance (41 de 53 documentos, incluyendo cuentas reales y de prueba); no
      requiere repetirse.
- [x] 7.7 Redesplegar a Cloud Run y verificar en vivo: login/"nueva conversación" no crean
      documento, el primer mensaje sí. (Revisión `elden-ring-agent-00006-2wg`.)
