"""Pytest-compatible LLM-as-a-judge evaluations for Claude vs. Kimi."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.workflow.graph import build_graph
from src.workflow.llm import get_llm


class EvalCase(BaseModel):
    """One roster-constrained factuality benchmark."""

    id: str
    query: str
    roster: list[str]
    must_include: list[str] = Field(default_factory=list)
    factuality_checks: list[str] = Field(default_factory=list)


class JudgeScore(BaseModel):
    """Structured score returned by the judge LLM."""

    factuality_hallucination: int = Field(ge=0, le=25)
    roster_adherence: int = Field(ge=0, le=25)
    tactical_synergy: int = Field(ge=0, le=25)
    json_schema_adherence: int = Field(ge=0, le=25)
    total: int = Field(ge=0, le=100)
    rationale: str


JUDGE_PROMPT = """You are a strict evaluator for Another Eden team recommendations.
Score the candidate out of 100 using exactly four 25-point metrics:
1. Factuality/Hallucination: correct game facts and no invented weapon classes.
2. Roster Adherence: only uses the provided roster plus allowed F2P units.
3. Tactical Synergy: coherent roles, grasta attribution, and matchup logic.
4. JSON Schema adherence: matches TeamOutput or AlternativesOutput shape.

Return only JSON with keys:
factuality_hallucination, roster_adherence, tactical_synergy,
json_schema_adherence, total, rationale."""


def _load_cases() -> list[EvalCase]:
    path = Path(__file__).with_name("test_cases.json")
    return [EvalCase.model_validate(item) for item in json.loads(path.read_text())]


async def _run_candidate(case: EvalCase, provider: str, driver) -> dict[str, Any]:
    os.environ["LLM_REASONING_PROVIDER"] = provider
    graph = build_graph(driver=driver)
    state = {
        "user_query": case.query,
        "roster": case.roster,
        "plan_strategy": "",
        "boss_context": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "alternatives": "",
        "final_output": {},
    }
    result = await graph.ainvoke(state)
    return result["final_output"]


def _judge(case: EvalCase, provider: str, output: dict[str, Any]) -> JudgeScore:
    judge = get_llm(role="judge")
    response = judge.invoke([
        SystemMessage(content=JUDGE_PROMPT),
        HumanMessage(content=json.dumps({
            "case": case.model_dump(),
            "candidate_provider": provider,
            "team_output": output,
        }, indent=2)),
    ])
    return JudgeScore.model_validate(json.loads(response.content))


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("RUN_LLM_EVALS") != "1", reason="live LLM evals disabled")
@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c.id)
@pytest.mark.parametrize("provider", ["anthropic", "kimi"])
async def test_team_output_judged_against_factuality_cases(case, provider, loaded_db):
    """Benchmark Claude vs. Kimi on factuality-sensitive team outputs."""
    output = await _run_candidate(case, provider, loaded_db)
    score = _judge(case, provider, output)
    assert score.total >= int(os.getenv("LLM_EVAL_MIN_SCORE", "75")), score.model_dump()
