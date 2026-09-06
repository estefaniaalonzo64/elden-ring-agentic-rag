"""Fase 10 — corre evaluation/cases.yaml contra el agente real y lo juzga con Gemini (PRD §35).

Ejecuta cada caso contra Firestore/BigQuery/Vertex AI reales (mismas rutas que /chat), guarda
los transcripts completos en evaluation/transcripts.json, y le pide a Gemini que juzgue el
turno final de cada caso con la salida estructurada del PRD §35. Los resultados por caso (no
solo el promedio) quedan en evaluation/llm_judge_results.json.

Uso:
    PYTHONPATH=. .venv/bin/python evaluation/llm_judge.py
"""

from __future__ import annotations

import json
import statistics
import uuid
from pathlib import Path
from typing import Any

import yaml
from google.genai import Client as GenAIClient
from google.genai import types
from pydantic import BaseModel

from backend.agent.runner import run_turn
from backend.config import get_settings
from backend.repositories.firestore_repository import get_firestore_client
from backend.tools.memory import get_player_profile

EVAL_USER_ID = "eval-user-fase10"
CASES_PATH = Path(__file__).parent / "cases.yaml"
TRANSCRIPTS_PATH = Path(__file__).parent / "transcripts.json"
JUDGE_RESULTS_PATH = Path(__file__).parent / "llm_judge_results.json"


class JudgeVerdict(BaseModel):
    groundedness: int
    relevance: int
    personalization: int
    source_alignment: int
    hallucination_detected: bool
    reason: str


JUDGE_PROMPT = """\
You are grading one answer from an Elden Ring lore/recommendation agent. The agent must
only state facts backed by the cited sources, and must personalize recommendations using
the player's profile when the question calls for it.

Conversation so far (earlier turns in this same case, for context):
{prior_turns}

User's question being graded: {question}

Player profile in Firestore at this point: {profile}

Sources the agent cited for this answer: {sources}

Agent's answer being graded: {answer}

Score each field 1-5 (5 = best):
- groundedness: are the stated facts consistent with the cited sources (nothing invented)?
- relevance: does the answer actually address the question?
- personalization: does it use the player profile when the question calls for it? (score 5
  if personalization wasn't called for and none was forced)
- source_alignment: are sources cited when the answer states factual/recommendation content?
  (score 5 if no factual claim was made, e.g. a refusal for insufficient evidence)

Also set hallucination_detected (true only if the agent stated a specific Elden Ring fact
NOT supported by the sources or by this conversation), and a short reason (1-2 sentences).
"""


def _reset_eval_profile() -> None:
    get_firestore_client().collection("player_profiles").document(EVAL_USER_ID).delete()


def _load_cases() -> list[dict[str, Any]]:
    with open(CASES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["cases"]


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    turns_out = []
    for turn in case["turns"]:
        if turn.get("new_session"):
            session_id = str(uuid.uuid4())
        message = turn["message"]
        answer, sources = run_turn(EVAL_USER_ID, session_id, message)
        turns_out.append({"message": message, "answer": answer, "sources": sources})
    return {
        "id": case["id"],
        "category": case["category"],
        "notes": case.get("notes", ""),
        "turns": turns_out,
        "final_profile": get_player_profile(EVAL_USER_ID),
    }


def _judge_case(client: GenAIClient, model: str, transcript: dict[str, Any]) -> JudgeVerdict:
    *prior, last = transcript["turns"]
    prior_text = (
        "\n".join(f"- User: {t['message']}\n  Agent: {t['answer']}" for t in prior)
        if prior
        else "(none — single-turn case)"
    )
    prompt = JUDGE_PROMPT.format(
        prior_turns=prior_text,
        question=last["message"],
        profile=json.dumps(transcript["final_profile"], ensure_ascii=False),
        sources=json.dumps(last["sources"], ensure_ascii=False),
        answer=last["answer"],
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeVerdict,
        ),
    )
    return JudgeVerdict.model_validate_json(response.text)


def main() -> None:
    settings = get_settings()
    client = GenAIClient(
        vertexai=True, project=settings.gcp_project_id, location=settings.vertex_location
    )

    transcripts: list[dict[str, Any]] = []
    judge_results: list[dict[str, Any]] = []

    for case in _load_cases():
        _reset_eval_profile()
        transcript = _run_case(case)
        transcripts.append(transcript)

        verdict = _judge_case(client, settings.gemini_model, transcript)
        judge_results.append(
            {"case_id": case["id"], "category": case["category"], "verdict": verdict.model_dump()}
        )
        print(f"[{case['id']}] {verdict.model_dump()}")

    TRANSCRIPTS_PATH.write_text(
        json.dumps(transcripts, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    JUDGE_RESULTS_PATH.write_text(
        json.dumps(judge_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== Resumen ===")
    for field in ["groundedness", "relevance", "personalization", "source_alignment"]:
        values = [r["verdict"][field] for r in judge_results]
        print(f"{field}: avg={statistics.mean(values):.2f} (n={len(values)})")
    hallucinations = sum(1 for r in judge_results if r["verdict"]["hallucination_detected"])
    print(f"hallucination_detected: {hallucinations}/{len(judge_results)}")


if __name__ == "__main__":
    main()
