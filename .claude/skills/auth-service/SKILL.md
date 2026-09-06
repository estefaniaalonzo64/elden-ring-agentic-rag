---
name: auth-service
description: Implementar o modificar registro, login, hashing de password, tokens JWT y la dependencia de autenticación de FastAPI. Usar cuando el trabajo toque /register, /login, password hashing, tokens Bearer, o el aislamiento de user_id.
---

# auth-service

Alcance: PRD §12, §13.1, Fase 2 (§40), pruebas §42 "Auth", caso de aceptación A (§43).

## Requisito de negocio

Solo `username` + `password`. **No** implementar email, verificación de email, recuperación
de contraseña ni MFA — está fuera de alcance a propósito (deuda técnica aceptada, PRD §37).

## Modelo Firestore

```text
users/{username_normalized}
{
  "user_id": "uuid",
  "username": "fany",
  "password_hash": "...",
  "password_salt": "...",
  "created_at": "timestamp"
}
```

Normaliza `username` (p.ej. lowercase + trim) para usarlo como doc id y evitar colisiones tipo
`Fany` vs `fany`.

## Password storage

- PBKDF2-HMAC-SHA256 + salt aleatorio + iteraciones configurables, **o** bcrypt/Argon2 si el
  código de ejemplo del profesor ya lo trae implementado (reutilízalo, no lo reemplaces).
- Nunca loguear ni exponer el password ni el hash en respuestas de API.

## Token

- Al hacer login exitoso, emitir un JWT firmado con `JWT_SECRET`, TTL `JWT_TTL_MINUTES`
  (PRD §29).
- El frontend lo envía como `Authorization: Bearer <token>`.
- El payload del JWT debe incluir `user_id` (el UUID interno, no el username crudo) para que
  el resto del backend lo use sin volver a tocar Firestore en cada request si no es necesario.

## Regla crítica de aislamiento (P-03 / AGENTS.md §2)

`user_id` se obtiene **exclusivamente** de la dependencia de autenticación de FastAPI que
decodifica el JWT. Ninguna tool del agente, ni el propio LLM, debe poder pasar o elegir un
`user_id` por texto libre. Esto es no negociable — ver PRD §12.4.

## Flujo login → nueva sesión (PRD §11.2, §15.1)

Cada login exitoso, además de emitir el token, debe crear una `chat_sessions/{session_id}`
nueva (ver skill `player-memory`) y devolverla junto con el token:

```json
{ "access_token": "...", "session_id": "..." }
```

## Endpoints (PRD §24)

- `POST /register` → `{username, password}` → `{created: true}` (o error si el username
  ya existe).
- `POST /login` → `{username, password}` → `{access_token, session_id}`.
- Dependencia reusable de auth para `/chat` y cualquier endpoint protegido futuro.

## Pruebas mínimas (PRD §42)

```text
register válido
username duplicado
password incorrecto
token inválido
/chat sin token
```

## Definition of Done de esta pieza

Dos usuarios pueden registrarse y autenticarse de forma independiente sin poder ver ni
influenciar el estado del otro (esto se termina de validar en el skill `player-memory`,
caso de aislamiento G).
