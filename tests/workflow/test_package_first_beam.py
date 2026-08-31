"""Regression coverage for package-first lineup expansion and readiness diagnostics."""

from src.workflow.lineup_generation import generate_lineup_candidates
from src.workflow.nodes.analyze import _analyze_candidate_bundle
from tests.workflow.test_lineup_generation import fixture


def _skill_package(package_id, *, roles=None, untagged=False):
    skill_ids = [f"{package_id}:skill:{index}" for index in range(3)]
    return {
        "id": package_id,
        "skill_ids": skill_ids,
        "skill_family_ids": [f"{package_id}:family:{index}" for index in range(3)],
        "package_size": 3,
        "slot_limit": 3,
        "role_ids": sorted(roles or {}),
        "role_scores": dict(roles or {}),
        "evidence": {
            role: [{"fact_id": f"{package_id}:{role}", "capability": role}]
            for role in roles or {}
        },
        "untagged_skill_ids": skill_ids if untagged else [],
        "legal": True,
    }


def test_beam_states_and_candidates_carry_one_legal_skill_package_per_character():
    characters, _, role_scores = fixture()
    role_scores["entities"][0]["skill_packages"] = [
        _skill_package("skill-package:hero-0-balanced", roles={"primary_damage": 4}),
        _skill_package("skill-package:hero-0-counter", roles={"primary_damage": 2, "boss_counter": 4}),
    ]

    result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
    )

    assert len(result["package_frontier"]["character:0"]) == 2
    for candidate in result["candidates"]:
        assert len(candidate["character_ids"]) == 6
        assert len(set(candidate["character_ids"])) == 6
        assert set(candidate["selected_skill_package_ids"]) == set(candidate["character_ids"])
        for character_id, package_id in candidate["selected_skill_package_ids"].items():
            assert package_id in {
                package["id"] for package in result["package_frontier"][character_id]
            }
            assert candidate["skill_package_ids"][character_id] == candidate["skill_packages"][character_id]["skill_ids"]
    assert all(row["package_first"] for row in result["diagnostics"]["beam_trace"])


def test_legal_untagged_package_remains_a_beam_choice_without_coverage_credit():
    characters, entities, role_scores = fixture()
    filler = next(entity for entity in entities if entity.get("id") == "character:5")
    filler["skill_packages"] = [_skill_package("skill-package:untagged-filler", untagged=True)]

    result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
    )

    candidates = [
        candidate for candidate in result["candidates"]
        if "character:5" in candidate["character_ids"]
    ]
    assert candidates
    assert all(candidate["role_assignments"]["character:5"] == [] for candidate in candidates)
    assert all(
        candidate["skill_packages"]["character:5"]["untagged_skill_ids"]
        for candidate in candidates
    )


def test_incomplete_optional_character_is_named_and_does_not_claim_infeasibility():
    characters, entities, role_scores = fixture()
    characters.append({"id": "character:missing", "name": "Missing Kit"})
    entities.append({
        "id": "character:missing",
        "name": "Missing Kit",
        "entity_type": "character",
        "eligible": True,
        "rejection_reasons": [],
    })

    result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores={**role_scores, "entities": entities},
    )

    exclusion = next(
        row for row in result["diagnostics"]["stage_diagnostics"]["preprocessing"]["exclusions"]
        if row["character_id"] == "character:missing"
    )
    assert exclusion["code"] == "character_data_incomplete"
    assert exclusion["reason"] == "skill_package.unavailable"
    assert result["status"] in {"success", "partial"}
    assert result["diagnostics"]["readiness"]["status"] == "reduced_roster"
    assert result["diagnostics"]["readiness"]["authoritative_infeasible"] is False


def test_fewer_than_six_complete_characters_returns_readiness_error_without_analyzer_work():
    characters, entities, role_scores = fixture()
    result = generate_lineup_candidates(
        characters=characters[:5],
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores={
            **role_scores,
            "entities": entities[:5],
        },
    )

    assert result["status"] == "data_error"
    assert result["error"]["type"] == "character_data_incomplete"
    assert result["candidate_count"] == 0
    analysis = _analyze_candidate_bundle({
        "candidate_bundle": {
            "coverage": {"complete": True},
            "candidate_generation": result,
        },
        "retry_count": 0,
    })
    assert analysis["analyzer_call_count"] == 0


def test_stage_diagnostics_are_disjoint_and_reproducible():
    characters, _, role_scores = fixture()
    first = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
    )
    second = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
    )

    assert first == second
    stages = first["diagnostics"]["stage_diagnostics"]
    assert set(stages) == {
        "preprocessing",
        "beam_expansion",
        "mandatory_coverage",
        "affinity_matchup",
        "allocation",
        "diversity_pruning",
        "post_beam_evaluation",
    }
    flow = stages["post_beam_evaluation"]
    assert sum(flow["rejected_at"].values()) == flow["rejected_attempts"]
    assert stages["diversity_pruning"]["retained_candidates"] == first["candidate_count"]
    assert stages["beam_expansion"]["trace"] == first["diagnostics"]["beam_trace"]
