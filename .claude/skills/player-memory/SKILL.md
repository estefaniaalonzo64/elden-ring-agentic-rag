---
name: player-memory
description: Implementar o modificar el perfil persistente del jugador (preferencias/stats), las tools get/update/forget_player_memory, las chat_sessions y el transcript de mensajes en Firestore. Usar cuando el trabajo toque memoria del jugador, aislamiento entre usuarios, o persistencia de conversaciones.
---

# player-memory

Alcance: PRD §13.2–13.4, §14, §15, Fase 3 y 6 (§40), pruebas §42 "Memory", casos D/E/F/G (§43).

## Los tres conceptos que NO se deben mezclar (P-03)

1. **Contexto de conversación** — vive en la sesión ADK, se reinicia en cada login.
2. **Memoria persistente del jugador** — preferencias/stats estables, vive en Firestore,
   sobrevive a logins.
3. **Transcript** — historial crudo de mensajes, vive en Firestore, sobrevive a logins pero
   no se re-inyecta automáticamente como contexto activo del agente.

## Modelo Firestore

```text
player_profiles/{user_id}
{
  "preferences": {
    "preferred_weapon_types": ["katana", "twinblade"],
    "playstyle": "aggressive",
    "preferred_effects": ["bleed"],
    "preferred_combat_style": "melee"
  },
  "stats": {
    "level": 85, "vigor": 40, "mind": 15, "endurance": 25,
    "strength": 18, "dexterity": 45, "intelligence": 9, "faith": 8, "arcane": 35
  },
  "updated_at": "timestamp"
}
```

Todos los campos son opcionales — **nunca** exigir onboarding. El perfil puede estar
completamente vacío y es válido.

```text
chat_sessions/{session_id}
{ "session_id": "...", "user_id": "...", "created_at": "...", "status": "active" }

chat_sessions/{session_id}/messages/{message_id}
{ "role": "user|assistant", "content": "...", "created_at": "...", "sources": [] }
```

## Qué SÍ se persiste automáticamente como memoria estable (§14.1)

Preferencias: estilo de juego, melee/magia/híbrido, tipos de arma preferidos, efectos
preferidos, afinidades, tendencias estables relevantes a recomendaciones.

Stats: level, vigor, mind, endurance, strength, dexterity, intelligence, faith, arcane.

## Qué NO se persiste como preferencia estable (§14.2)

Boss actual, zona actual, progreso puntual, una pregunta aislada, estados temporales. Si el
agente detecta esto, es contexto de conversación, no memoria.

## Tools (contrato exacto — PRD §22.1–22.3)

### `get_player_profile`

Sin parámetros de identidad (el `user_id` lo inyecta el runtime desde el contexto autenticado,
nunca el LLM). Devuelve:

```json
{ "preferences": {}, "stats": {} }
```

### `update_player_memory`

```json
{ "preferences_patch": {}, "stats_patch": {} }
```

Debe hacer **merge parcial** (no reemplazar el documento completo) y actualizar `updated_at`.

### `forget_player_memory`

```json
{ "fields": ["preferences.preferred_weapon_types"] }
```

Debe borrar **solo** los campos pedidos (dotted path), dejando el resto del perfil intacto.

## Aprendizaje progresivo, corrección y olvido (§14.3–14.6)

- No hay formulario de onboarding. El agente detecta preferencias/stats mencionados
  naturalmente y llama `update_player_memory`.
- Corrección ("ya no juego con arcano, ahora voy full int") → `update_player_memory` con el
  patch corregido, no acumula valores viejos.
- Olvido ("olvida que me gustan las katanas") → `forget_player_memory` con el/los campos
  exactos, no un reset total del perfil salvo que el usuario lo pida así explícitamente.
- "¿Qué recuerdas de mí?" → el agente puede llamar `get_player_profile` y explicarlo en
  lenguaje natural; no requiere endpoint HTTP dedicado en el MVP (eso es TODO-03).

## Sesión nueva por login (§15.2)

Cada login crea una `chat_sessions/{session_id}` nueva para evitar contexto infinito y reducir
tokens — esto es responsabilidad conjunta con `auth-service`, no de este skill en solitario.
El transcript de sesiones anteriores permanece en Firestore aunque no se muestre en el MVP
(TODO-01 es el selector de historial, fuera de alcance).

## Aislamiento — la regla que no se puede romper

Toda lectura/escritura de memoria y de mensajes se filtra por el `user_id` del token
autenticado, nunca por un valor que el LLM pueda inventar o que venga del payload del chat.
Verifícalo con el caso de aceptación G (§43): usuario A nunca debe poder leer u obtener
memoria de usuario B.

## Pruebas mínimas (§42)

```text
guardar preferencia
guardar stats
actualizar preferencia
olvidar preferencia
aislamiento usuario A/B
```

## Definition of Done de esta pieza

Las preferencias sobreviven un nuevo login (caso D, §43) y el transcript existe en Firestore
incluso después de logout (Fase 6, §40).
