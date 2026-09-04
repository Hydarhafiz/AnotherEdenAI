"""Regression coverage for the source-backed H witness capability set."""

from __future__ import annotations

import json
from pathlib import Path

from src.workflow.lineup_generation import generate_lineup_candidates
from src.workflow.role_scoring import derive_contextual_role_scores


CATALOG = Path("src/etl/kit_catalog.json")
H_ROSTER = {"Aisha", "Aldo", "Alma", "Anabel", "Ashtear", "Azami"}


def _h_catalog_rows() -> list[dict]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    return [row for row in payload["characters"] if row["character"]["name"] in H_ROSTER]


def _h_role_scores() -> tuple[list[dict], dict]:
    rows = _h_catalog_rows()
    characters = [row["character"] for row in rows]
    skills = [skill for row in rows for skill in row["skills"]]
    passives = [passive for row in rows for passive in row["passive_skills"]]
    boss = {
        "name": "C6.1 smoke boss",
        "weak": [],
        "resist": [],
        "null": [],
        "absorb": [],
        "required_counters": [],
        "mechanic_tags": [],
    }
    role_scores = derive_contextual_role_scores(
        boss=boss,
        characters=characters,
        skills=skills,
        passives=passives,
        sidekicks=[],
        stellar_awakened={name: "awakened" for name in H_ROSTER},
    )
    return characters, role_scores


def test_h_roster_capability_evidence_is_source_backed_and_role_complete():
    expected = {
        "Aisha": {"direct_damage", "deploy_zone", "inflict_pain"},
        "Aldo": {"direct_damage"},
        "Alma": {"direct_damage"},
        "Anabel": {"direct_damage", "damage_reduction"},
        "Ashtear": {"direct_damage", "damage_reduction_barrier"},
        "Azami": {"direct_damage"},
    }

    observed = {}
    for row in _h_catalog_rows():
        facts = [*row["skills"], *row["passive_skills"]]
        observed[row["character"]["name"]] = {
            capability
            for fact in facts
            for capability in fact["capabilities"]
        }
        for fact in facts:
            evidence = json.loads(fact["capability_evidence_json"])
            assert all(
                item["review_decision"] in {"approve", "correct", "proven"}
                for item in evidence
            )

    assert observed == expected

    characters, role_scores = _h_role_scores()
    pools = role_scores["role_pools"]
    assert {item["entity_id"] for item in pools["primary_damage"]} == {
        "Aisha", "Aldo", "Alma", "Anabel", "Ashtear", "Azami"
    }
    assert {item["entity_id"] for item in pools["offensive_enablement"]} == {"Aisha"}
    assert {item["entity_id"] for item in pools["zone_setup"]} == {"Aisha"}
    assert {item["entity_id"] for item in pools["defense_mitigation"]} == {"Anabel", "Ashtear"}


def test_h_roster_generates_all_bounded_archetypes_without_analyzer():
    characters, role_scores = _h_role_scores()
    result = generate_lineup_candidates(
        characters=characters,
        sidekicks=[],
        boss={
            "name": "C6.1 smoke boss",
            "weak": [],
            "resist": [],
            "null": [],
            "absorb": [],
            "required_counters": [],
            "mechanic_tags": [],
        },
        role_scores=role_scores,
    )

    assert result["status"] == "success"
    assert result["candidate_count"] >= 3
    assert result["missing_archetypes"] == []
    assert result["diagnostics"].get("zero_candidate_causes") == []
