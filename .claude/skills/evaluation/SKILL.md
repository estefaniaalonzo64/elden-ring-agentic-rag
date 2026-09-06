---
name: evaluation
description: Generar o ejecutar los casos de evaluación manual y el LLM-as-a-judge, y medir contra los criterios mínimos del MVP. Usar cuando el trabajo toque evaluation/cases.yaml, manual_evaluation.md, llm_judge.py, o cuando haya que reportar métricas de calidad del sistema.
---

# evaluation

Alcance: PRD §34–§36, Fase 10 (§40).

## Dos niveles obligatorios — ninguno reemplaza al otro (§35.1)

1. Evaluación manual (humana, escala 1–5).
2. LLM-as-a-judge (Gemini como juez, estructurado).

Documentar ambos en la entrega; no es válido reportar solo el juez automático.

## Evaluación manual (§34.1) — 10 a 20 prompts, categorías mínimas

```text
Lore                      ("¿Qué sabes sobre <entidad existente>?")
Retrieval multilingüe     (una consulta en español, una en inglés)
Recommendation            ("Prefiero katanas y DEX, recomiéndame algo")
Recommendation + memory   (conversación de 3 turnos: playstyle → arma preferida → pide recomendación)
Persistent memory         (decir preferencia → logout → login nuevo → preguntar por esa preferencia)
Memory correction         ("ya no prefiero X, ahora quiero Y")
Memory forget             ("olvida que prefiero X")
Out-of-KB                 (pregunta fuera del corpus; se espera "no tengo suficiente información")
```

Guardar los casos en `evaluation/cases.yaml` y los resultados/observaciones en
`evaluation/manual_evaluation.md`.

Métricas (escala 1–5, PRD §34.2):

```text
Retrieval relevance | Groundedness | Answer relevance | Personalization
Recommendation usefulness | Lore fidelity | Language consistency | Source correctness
```

## LLM-as-a-judge (§35) — `evaluation/llm_judge.py`

Usar Gemini como juez. Entrada al juez por cada caso:

```text
user_question
player_profile
retrieved_documents
assistant_answer
```

Salida estructurada esperada:

```json
{
  "groundedness": 1,
  "relevance": 1,
  "personalization": 1,
  "source_alignment": 1,
  "hallucination_detected": false,
  "reason": "..."
}
```

Escala 1–5 en cada campo numérico. Persistir los resultados por caso (no solo el promedio) para
poder auditar cuál caso falló y por qué.

## Criterios mínimos del MVP (§36) — no son un benchmark científico, son evidencia académica

```text
Groundedness promedio >= 4/5
Relevance promedio >= 4/5
Personalization >= 4/5 en los casos donde aplique
0 fugas de memoria entre usuarios
0 passwords almacenados en texto plano
100% de las respuestas RAG con fuentes cuando corresponde
```

Si algún criterio no se cumple, repórtalo explícitamente en vez de suavizarlo — el objetivo es
evidencia honesta del funcionamiento, no maquillar el resultado.

## Definition of Done de esta pieza

Existen casos manuales documentados con sus puntajes, existe una corrida del LLM judge con
salida estructurada por caso, y ambos resultados están recopilados con evidencia (capturas o
logs) lista para el PDF de entrega (PRD §45.9).
