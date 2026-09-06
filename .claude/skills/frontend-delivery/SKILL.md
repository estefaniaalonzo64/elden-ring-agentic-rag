---
name: frontend-delivery
description: Implementar o modificar el frontend estático (Login/Chat) servido por el mismo FastAPI. Usar cuando el trabajo toque frontend/index.html, frontend/app.js, frontend/styles.css, o cómo se sirven junto al backend.
---

# frontend-delivery

Alcance original: PRD §25–§27, Fase 7 y 9 (§40), caso de aceptación A/I (§43 vía UI).

> **Override explícito del usuario (2026-09-05), reemplaza PRD §25–§27 y Fase 7/9 — ver
> "Desviación de arquitectura" en `SYSTEM_HEARTBEAT.md` para el detalle completo:**
> el PRD pedía Apps Script embebido en Google Sites. Se implementó y se publicó, pero el
> navegador real del usuario nunca pudo renderizar el Web App (funcionaba desde `curl`, las
> ejecuciones de `doGet()` en el servidor siempre salían "Completada" sin error — la causa
> nunca se encontró, pese a descartar cuenta/cookies/red/dispositivo). Se abandonó Apps
> Script/Sites y se reemplazó por un **frontend estático servido directo por el mismo
> FastAPI** (`StaticFiles`, mismo origen, sin CORS), tomando el patrón del repo hermano
> `/home/fanny/diplo2026/ah-grupo-fundador` (mismo profesor). No reintroduzcas Apps
> Script/Sites salvo que el usuario lo pida explícitamente de nuevo.

## Pantallas — solo estas dos

```text
Login
Chat
```

**No hay pantalla de Registro** — el registro público está cerrado (ver skill
`auth-service` / `SYSTEM_HEARTBEAT.md`, "Registro cerrado"). Los usuarios son un roster fijo
creado con `scripts/create_user.py`. TODO-01 (historial navegable) ya está implementado — ver
"Panel de conversaciones" más abajo. Feedback 👍👎 (TODO-02) y endpoints administrativos de
otros usuarios (TODO-03) siguen explícitamente fuera del MVP.

## Login

```text
username
password
botón entrar
```

Al hacer login exitoso, guardar en estado de sesión del frontend (una variable JS en memoria
del módulo, **nunca** `localStorage` — se limpia al logout o al recargar la página, PRD
§25.4): `token` (`access_token` del backend), `session_id`.

## Chat

```text
mensajes (renderizados como Markdown real — ver abajo)
textarea
botón enviar
logout
```

Cada mensaje enviado va a `POST /chat` con `Authorization: Bearer <token>` y
`{session_id, message}`. Mostrar `message` (parseado con `marked` + sanitizado con
`DOMPurify`, ambos vía CDN — las respuestas del agente traen `**bold**`/`### headers` reales
que se ven mal como texto plano) y, si vienen, las `sources` de la respuesta (formato simple
`entity_type · name`, nunca el `entity_id` crudo ni score/distancia).

Mientras la respuesta de `POST /chat` está pendiente, se muestra un indicador de progreso
("Pensando..." / "Buscando información...") y se deshabilita el botón de envío, para que la UI
nunca parezca congelada durante la vuelta RAG + LLM. Se oculta tanto en éxito como en error.

### Panel de conversaciones (TODO-01, implementado)

La pantalla de Chat incluye un panel "Mis conversaciones" que lista las `chat_sessions`
propias del usuario autenticado (`GET /sessions`, más recientes primero, con preview del
primer mensaje) — por construcción solo aparecen ahí las que ya tienen al menos un mensaje
(ver skill `player-memory`, "Sesión nueva por login": la creación en Firestore es perezosa, no
al loguearse ni al pedir una nueva). Al hacer click en una, se carga su transcript completo
(`GET /sessions/{id}/messages`) en el área de mensajes y los mensajes nuevos se agregan a esa
misma conversación. El botón "Nueva conversación" (`POST /sessions`) solo entrega un
`session_id` nuevo, sin necesidad de cerrar sesión y volver a loguearse — esa conversación
recién aparecerá en el panel una vez que se le envíe el primer mensaje. Las tres rutas están
filtradas por el `user_id` del token, igual que `/chat`.

## Estado y logout

```
logout → borrar token → borrar session_id → volver a Login
```

El siguiente login siempre genera una `session_id` nueva (coordinado por el backend, no por
el frontend).

## Estructura de archivos (reemplaza PRD §31 para esta pieza)

```text
frontend/
├── index.html   # shell: pantallas Login/Chat, carga marked+DOMPurify por CDN
├── app.js        # lógica cliente: fetch a /login y /chat, estado en memoria, render markdown
└── styles.css    # estilos (tema oscuro Elden Ring)
```

`backend/main.py` monta este directorio con
`app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")`,
**después** de declarar todas las rutas de API (`/health`, `/login`, `/chat`) para no
taparlas. `Dockerfile` copia `frontend/` a la imagen junto con `backend/`.

## CORS — ya no aplica

Como el frontend se sirve desde el mismo origen que la API, **no hace falta CORS**. Si ves
`CORSMiddleware` en `backend/main.py`, es un resabio de la época Apps Script — quítalo si
sigue ahí.

## Definition of Done de esta pieza

Existe una URL de Cloud Run (no de Google Sites) desde la cual se puede iniciar sesión,
chatear y cerrar sesión contra el backend real — validado por el usuario directamente en su
navegador, no solo por `curl` (aprendizaje de esta sesión: `curl` no detecta fallas de
renderizado JS del lado del cliente).
