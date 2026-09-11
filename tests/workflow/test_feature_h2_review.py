"""Offline contracts for the Feature H2 human-readable review."""

import json
from pathlib import Path

from src.workflow.h2_review import (
    H2_INPUT_TOKEN_TARGET,
    build_h2_report,
    generate_h2_review,
    render_h2_markdown,
)


def _candidate(candidate_id, archetype, characters, *, element="Fire", score=100.0, components=None):
    return {
        "candidate_id": candidate_id,
        "archetype": archetype,
        "character_ids": characters,
        "frontline_character_ids": characters[:4],
        "reserve_character_ids": characters[4:],
        "primary_damage_elements": [element],
        "score": score,
        "component_scores": components or {"boss_matchup": 20, "role_overlap": 0},
        "role_assignments": {
            characters[0]: ["zone_setup"],
            characters[1]: ["primary_damage"],
            characters[2]: ["offensive_enablement"],
            characters[3]: ["defense_mitigation"],
            characters[4]: ["reserve_utility"],
            characters[5]: ["reserve_utility"],
        },
        "coverage": {
            "mandatory": ["primary_damage", "offensive_enablement", "survival"],
            "covered_roles": ["primary_damage", "offensive_enablement", "zone_setup", "defense_mitigation"],
            "missing": [],
            "provided_capabilities": ["direct_damage", "deploy_zone", "inflict_pain", "damage_reduction"],
            "setup_dependencies": ["requires_zone", "requires_pain", "requires_another_force"],
            "evidence": {
                "zone_setup": [{"capability": "deploy_zone", "fact_id": "skill:zone", "evidence_id": "zone-proof"}],
                "offensive_enablement": [{"capability": "inflict_pain", "fact_id": "skill:pain", "evidence_id": "pain-proof"}],
                "defense_mitigation": [{"capability": "damage_reduction", "fact_id": "passive:guard", "evidence_id": "guard-proof"}],
            },
        },
    }


def _report(*, valid=True, candidate_rows=None, provider_error=None, usage_prompt=18_000):
    characters = [f"character:{value}" for value in "abcdef"]
    candidates = candidate_rows or [
        _candidate("lineup:one", "burst", characters),
        _candidate("lineup:two", "hybrid", list(reversed(characters)), score=99.0),
        _candidate("lineup:three", "sustain", characters, score=98.0),
    ]
    baseline = {
        "ranking": [item["candidate_id"] for item in candidates],
        "selected_top_candidate": candidates[0],
        "top_recommendation": {
            "strategy_summary": "Use a Fire-zone burst plan.",
            "frontline": [
                {"character_id": characters[0], "name": "Aisha", "role": "zone setup", "recommended_skills": ["Flame Serenade"]},
                {"character_id": characters[1], "name": "Aldo", "role": "primary damage", "recommended_skills": ["Fire Slash"]},
                {"character_id": characters[2], "name": "Anabel", "role": "defense mitigation", "recommended_skills": ["Barrier"]},
                {"character_id": characters[3], "name": "Ciel", "role": "offensive enablement", "recommended_skills": ["Pain Song"]},
            ],
            "reserve": [
                {"character_id": characters[4], "name": "Shion", "role": "reserve utility", "recommended_skills": []},
                {"character_id": characters[5], "name": "Myrus", "role": "reserve utility", "recommended_skills": []},
            ],
            "risks": ["Item ownership is unverified."],
        },
        "application_validation": {
            "final_response_valid": valid,
            "result_available": True,
            "degraded": False,
            "attempts": [{
                "validation_error_codes": [] if valid else ["id.skill"],
                "error_code": provider_error,
            }],
        },
        "provider_errors": [] if not provider_error else [{"code": provider_error}],
        "advisories": ["Review setup order."],
        "risks": ["Backend assumption remains unverified."],
        "swap_decisions": [],
        "usage": {"prompt_tokens": usage_prompt, "total_tokens": usage_prompt + 100, "cost": 0.001},
    }
    variant = dict(baseline)
    variant["ranking"] = [item["candidate_id"] for item in candidates]
    return {
        "evaluation_version": "feature-h1-evaluation-v1",
        "scenarios": [{
            "scenario_id": "H-F08",
            "boss": "Rotte Rivel",
            "category": "review",
            "status": "completed",
            "projection": {"candidate_count": 3, "serialized_bytes": 1000},
            "backend_candidate_ranking": candidates,
            "variants": {"baseline_a": baseline, "variant_b": variant},
            "comparison": {
                "both_valid": valid,
                "same_top_candidate": True,
                "same_ranking": True,
                "same_swap": True,
                "candidate_ids_closed_world": True,
                "skill_selections_valid": valid,
                "swap_authorized": True,
                "token_delta": 0,
                "cost_delta": 0,
            },
        }],
    }


def _context():
    characters = [
        {"id": f"character:{value}", "name": name, "display_name": name, "capabilities": [capability]}
        for value, name, capability in (
            ("a", "Aisha", "deploy_zone"),
            ("b", "Aldo", "direct_damage"),
            ("c", "Anabel", "damage_reduction"),
            ("d", "Ciel", "inflict_pain"),
            ("e", "Shion", "reserve_utility"),
            ("f", "Myrus", "reserve_utility"),
        )
    ]
    return {
        "boss": {
            "name": "Rotte Rivel",
            "affinities": {"weak": ["Fire"], "resist": ["Water"], "null": [], "absorb": []},
            "characteristics": "Wind boss",
            "mechanics_text": "Uses heavy Wind damage.",
            "attack_elements": ["Wind"],
        },
        "characters": characters,
        "threats": [{
            "label": "Heavy Wind damage",
            "mandatory": True,
            "required_capabilities": ["damage_reduction"],
        }],
        "dependency_providers": {
            "requires_zone": {"provider_name": "Aisha", "status": "PASS", "evidence": ["skill:zone"]},
            "requires_pain": {"provider_name": "Ciel", "status": "PASS", "evidence": ["skill:pain"]},
        },
        "element_relationships": [{
            "attacker": "Fire",
            "defender": "Wind",
            "relation": "strong_against",
            "authoritative": True,
            "source_url": "https://example.test/elements",
        }],
    }


def test_h2_resolves_names_and_renders_a_bounded_human_review():
    review = build_h2_report(_report(), context=_context())
    scenario = review["scenarios"][0]
    markdown = render_h2_markdown(review)

    assert scenario["boss_profile"]["weak"] == ["Fire"]
    assert scenario["gates"]["damage_affinity"]["status"] == "PASS"
    assert scenario["gates"]["boss_mechanics"]["status"] == "PASS"
    assert scenario["gates"]["setup_executability"]["status"] == "REVIEW"
    assert scenario["overall"] == {
        "modeled_viability": "MEDIUM",
        "status": "REVIEW",
        "summary": "The lineup is plausible under the supplied evidence but still requires human judgment.",
    }
    assert "Aisha" in markdown
    assert "Gate — Damage Affinity / Elemental Viability: `PASS`" in markdown
    assert "## Overall Modeled Viability" in markdown
    assert "guarantee a boss clear" in markdown
    assert "lineup:one" not in markdown
    assert len(markdown.splitlines()) < 180


def test_h2_explicit_blocked_affinity_overrides_authoritative_element_relationship():
    context = _context()
    context["boss"]["affinities"] = {"weak": ["Fire"], "resist": [], "null": ["Fire"], "absorb": []}
    review = build_h2_report(_report(), context=context)

    gate = review["scenarios"][0]["gates"]["damage_affinity"]
    assert gate["status"] == "FAIL"
    assert gate["evidence"][0]["result"] == "null"


def test_h2_affinity_precedence_marks_absorb_and_resist_as_blocked():
    context = _context()
    context["boss"]["affinities"] = {"weak": [], "resist": ["Fire"], "null": [], "absorb": ["Fire"]}
    review = build_h2_report(_report(), context=context)

    gate = review["scenarios"][0]["gates"]["damage_affinity"]
    assert gate["status"] == "FAIL"
    assert gate["evidence"][0]["result"] == "absorb"


def test_h2_missing_boss_and_element_evidence_is_not_a_pass():
    review = build_h2_report(_report())
    scenario = review["scenarios"][0]

    assert scenario["gates"]["damage_affinity"]["status"] == "UNKNOWN"
    assert scenario["gates"]["boss_mechanics"]["status"] == "UNKNOWN"
    assert scenario["gates"]["setup_executability"]["status"] == "REVIEW"
    assert scenario["input_budget"]["baseline_a"]["status"] == "PASS"


def test_h2_setup_missing_provider_fails_and_manual_statuses_remain_bounded():
    context = _context()
    context["dependency_providers"] = {}
    review = build_h2_report(_report(), context=context)
    gate = review["scenarios"][0]["gates"]["setup_executability"]

    assert gate["status"] == "REVIEW"
    assert any(row["dependency"] == "requires_zone" for row in gate["evidence"])


def test_h2_diversity_warns_when_character_sets_and_scores_are_identical():
    characters = [f"character:{value}" for value in "abcdef"]
    rows = [
        _candidate("lineup:one", "burst", characters, score=100.0),
        _candidate("lineup:two", "hybrid", list(reversed(characters)), score=100.0),
        _candidate("lineup:three", "sustain", characters, score=100.0),
    ]
    for row in rows:
        row["component_scores"] = {"boss_matchup": 20, "role_overlap": 0}
    diversity = build_h2_report(_report(candidate_rows=rows))["scenarios"][0]["candidate_diversity"]

    assert diversity["candidate_count"] == 3
    assert diversity["unique_character_set_count"] == 1
    assert diversity["identical_total_scores"] is True
    assert diversity["identical_component_score_vectors"] is True
    assert diversity["ordering_only_or_same_set"] is True
    assert any("CANDIDATE_DIVERSITY_WARNING" in warning for warning in diversity["warnings"])
    assert any("ARCHETYPE_DIFFERENTIATION_WARNING" in warning for warning in diversity["warnings"])


def test_h2_exposes_input_budget_exceeded_and_plain_validation_failure():
    review = build_h2_report(_report(valid=False, provider_error="provider.empty_output", usage_prompt=H2_INPUT_TOKEN_TARGET + 1))
    scenario = review["scenarios"][0]
    recommendation = scenario["analyzer_recommendation"]

    assert scenario["input_budget"]["baseline_a"]["status"] == "EXCEEDED"
    assert recommendation["validation"]["final_response_valid"] is False
    assert "provider.empty_output" in recommendation["validation"]["errors"]
    assert any("no structured analyzer object" in message for message in recommendation["validation"]["plain_language_errors"])


def test_h2_generates_the_markdown_artifact_from_an_h1_json(tmp_path: Path):
    h1_path = tmp_path / "h1.json"
    output_path = tmp_path / "h2-review.md"
    h1_path.write_text(json.dumps(_report()), encoding="utf-8")

    review = generate_h2_review(h1_path, output_path, context_path=None)

    assert review["scenario_count"] == 1
    assert output_path.exists()
    assert "# Feature H2" in output_path.read_text(encoding="utf-8")
