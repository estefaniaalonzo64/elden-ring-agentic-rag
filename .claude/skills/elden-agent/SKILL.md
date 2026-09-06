---
name: elden-agent
description: Implementar o modificar el agente ADK EldenRingGuideAgent, su system instruction, el registro de tools, el recomendador Top 3, el grounding estricto, el manejo multilingüe y el formato de fuentes. Usar cuando el trabajo toque el comportamiento conversacional del agente.
---

# elden-agent

Alcance: PRD §17–§23, ADR-01/ADR-02, Fase 5 (§40), pruebas §42 "Agent", casos C/H/I (§43).

## Requisito arquitectónico (P-04 / ADR-02)

Un único agente ADK: `EldenRingGuideAgent`, con exactamente estas 4 tools registradas
(implementadas en los skills `rag-bigquery` y `player-memory`):

```text
search_elden_ring_knowledge
get_player_profile
update_player_memory
forget_player_memory
```

No introducir sub-agentes, orquestación multiagente ni handoffs entre agentes — no hay
justificación funcional para ello en este alcance (si en algún momento la hubiera, es una
decisión de arquitectura que requiere discutirse con el usuario, no una extensión silenciosa).

## System instruction (usar como base, PRD §23)

```text
Eres una guía especializada en el corpus proporcionado de Elden Ring.

Tus hechos sobre Elden Ring deben estar respaldados por resultados
recuperados mediante search_elden_ring_knowledge.

No completes información faltante usando tu conocimiento preentrenado.

Cuando el usuario pida recomendaciones:
1. consulta su perfil cuando sea relevante;
2. pregunta solo si falta información necesaria;
3. recupera evidencia;
4. devuelve hasta 3 opciones;
5. explica brevemente por qué encajan;
6. incluye lore cuando la evidencia lo soporte;
7. lista las fuentes al final.

Detecta preferencias y stats estables expresados por el usuario y
persistelos mediante update_player_memory.

Si el usuario corrige información, actualízala.

Si pide olvidar algo, usa forget_player_memory.

Si pregunta qué recuerdas de él, usa get_player_profile.

Responde en el idioma utilizado por el usuario.
```

## Grounding estricto (P-01)

- El LLM puede: interpretar intención, resumir, traducir, comparar, estructurar, razonar
  **sobre documentos recuperados**.
- El LLM no puede: aportar hechos de Elden Ring no respaldados por `search_elden_ring_knowledge`.
- Evidencia insuficiente (retrieval vacío, resultados irrelevantes, pregunta fuera de corpus,
  mecánica no documentada) → responder algo equivalente a:
  *"No tengo suficiente información en mi base de conocimiento para responder esa pregunta."*
  Puede sugerir reformular, nunca inventar (§21).

## Recomendador (§17)

Detección de intención implícita (sin botón dedicado) cuando el usuario pide: qué arma usar,
qué equipo le conviene, opciones para una preferencia, alternativas, combinaciones.

Flujo:

```
petición → get_player_profile → identificar preferencias relevantes
  → si falta info crítica → preguntar (solo lo estrictamente necesario)
  → query de retrieval enriquecida con esas preferencias
  → search_elden_ring_knowledge
  → rankear/razonar usando EXCLUSIVAMENTE la evidencia recuperada
  → Top 3
```

Puede mezclar categorías (`weapon`, `armor`, `ash`, `incantation`) cuando tenga sentido; no
forzar una entidad de cada categoría.

Formato de salida esperado (§17.4):

```markdown
### 1. <opción>

**Por qué te encaja:** ...
**Qué aporta:** ...
**Lore:** ...

### 2. <opción>
...

### 3. <opción>
...

**Fuentes**
- weapon · ...
- ash · ...
- incantation · ...
```

El lore solo se incluye si la evidencia recuperada lo soporta (§17.5) — no rellenar con lore
inventado por completitud del formato.

## Respuestas de lore/conocimiento puro (§18)

```
pregunta → RAG → síntesis → respuesta → fuentes
```

No usar memoria de perfil si no aporta a la respuesta — no forzar personalización donde no
aplica.

## Multilingüe (§19)

1. Detectar idioma del mensaje entrante.
2. Recuperar semánticamente (el corpus puede estar en inglés, eso no cambia el idioma de
   retrieval).
3. Sintetizar y responder en el idioma del usuario.

El idioma **no se persiste** en Firestore — puede cambiar libremente entre turnos o sesiones.

## Fuentes (§20)

Formato mínimo al final de cualquier respuesta factual o de recomendación basada en RAG:

```markdown
**Fuentes**
- weapon · Moonveil
- npc · Ranni the Witch
- ash · Bloody Slash
```

No mostrar score, confidence, embeddings ni métricas internas al usuario.

## Sesión ADK (§15.2)

Nueva sesión conversacional en cada login (coordinar con `auth-service`/`player-memory`) para
evitar contexto infinito y mantener comportamiento predecible. La memoria importante y el
transcript no dependen de que la sesión ADK sobreviva — viven en Firestore.

## Pruebas mínimas (§42)

```text
lore grounded
recommendation top 3
sources
idioma
insuficiencia
memoria automática
```

## Definition of Done de esta pieza

`/chat` produce una respuesta grounded, con fuentes cuando corresponde, en el idioma del
usuario, y usando memoria de perfil cuando la petición es de recomendación (Fase 5, §40).
