"""M7 presentation joins evidence only to final selected IDs."""

from __future__ import annotations

import json
from copy import deepcopy

from src.workflow.presentation import (
    build_recommendation_presentation,
    build_result_presentation,
)


def _skill(character_id, name, capabilities, *, url=None):
    skill_id = f"skill:{character_id}:{name.casefold().replace(' ', '-')}"
    evidence = [
        {
            "kind": "capability",
            "value": capability,
            "direction": "enemy" if capability.startswith("inflict_") or capability == "direct_damage" else "ally",
            "target": "single_enemy" if capability.startswith("inflict_") else "party",
            "trigger": "",
            "matched_phrase": name,
            "source_id": f"rule:{capability}",
            "source_fact_id": skill_id,
            "review_decision": "approve",
            "artifact_version": "taxonomy-test",
            "review_artifact_version": "reviews-test",
        }
        for capability in capabilities
    ]
    return {
        "id": skill_id,
        "skill_id": skill_id,
        "character_id": character_id,
        "character_name": character_id.removeprefix("character:"),
        "name": name,
        "capabilities": list(capabilities),
        "capability_evidence_json": json.dumps(evidence),
        "capability_diagnostics_json": json.dumps({
            "proposed": len(capabilities),
            "reviewed": len(capabilities),
            "proven": len(capabilities),
            "candidate": 0,
        }),
        "source_url": url,
    }


def _state():
    character_ids = [f"character:{name}" for name in ("Toova", "ZoneSetter", "DPS", "Support", "ReserveA", "ReserveB")]
    skills = [
        _skill(character_ids[0], "Venom", ["inflict_pain", "inflict_poison"], url="https://example.test/Toova#Venom"),
        _skill(character_ids[1], "Double Crush", ["awaken_zone"], url="https://example.test/ZoneSetter#Double_Crush"),
        _skill(character_ids[2], "Fire Strike", ["direct_damage"], url="https://example.test/DPS#Fire_Strike"),
        _skill(character_ids[3], "Support Skill", ["heal_hp", "deploy_zone"], url="https://example.test/Support"),
        _skill(character_ids[4], "Reserve Heal", ["heal_hp"], url="https://example.test/ReserveA"),
        _skill(character_ids[5], "Reserve Guard", ["damage_reduction"], url="https://example.test/ReserveB"),
    ]
    selected = {character_id: [skill["id"]] for character_id, skill in zip(character_ids, skills)}
    recommendation = {
        "frontline": [
            {"name": name, "character_id": character_id, "selected_skill_ids": selected[character_id],
             "recommended_skills": [skill["name"]]}
            for name, character_id, skill in zip(("Toova", "ZoneSetter", "DPS", "Support"), character_ids[:4], skills[:4])
        ],
        "reserve": [
            {"name": name, "character_id": character_id, "selected_skill_ids": selected[character_id],
             "recommended_skills": [skill["name"]]}
            for name, character_id, skill in zip(("ReserveA", "ReserveB"), character_ids[4:], skills[4:])
        ],
    }
    candidate = {
        "id": "lineup:exact",
        "character_ids": character_ids,
        "skill_package_ids": selected,
        "skill_packages": {
            character_ids[2]: {
                "damage_matchups": [{
                    "fact_id": skills[2]["id"],
                    "element": ["Fire"],
                    "attack_type": ["Slash"],
                    "state": "weak",
                    "evidence_ids": [skills[2]["id"]],
                }]
            }
        },
        "coverage": {
            "roles_by_character_placement": {
                "frontline": ["primary_damage", "recovery_protection"],
                "reserve_after_switch": ["reserve_utility"],
            },
            "missing": ["mandatory.counter.grant_status_immunity"],
        },
        "component_scores": {"boss_matchup": 18},
        "component_score_scope": {"boss_matchup": "All selected characters; reserve attacks may require switching."},
        "uncertainty": {"count": 0},
        "evidence_diagnostics": {
            "scorer_uncertainty_count": 0,
            "scorer_uncertainty_scope": "Represented matchup and SA uncertainty only.",
        },
    }
    state = {
        "workflow_mode": "production",
        "candidate_bundle": {"backend_candidates": [candidate]},
        "typed_retrieval": {
            "boss": {
                "id": "celestial-mushroom",
                "name": "Celestial Mushroom",
                "source_url": "https://example.test/Celestial_Mushroom",
                "weak": [], "weak_state": "confirmed_empty",
                "resist": ["Pierce", "Blunt"], "resist_state": "confirmed_values",
                "null": [], "null_state": "unknown",
                "absorb": [], "absorb_state": "unknown",
            },
            "request_coverage": {
                "report_type": "feature_a_request_coverage",
                "metrics": {
                    "user_roster_count": 6,
                    "f2p_augmented_count": 0,
                    "distinct_available_count": 6,
                    "data_complete_count": 6,
                    "candidate_count": 1,
                    "unique_character_set_count": 1,
                    "unique_frontline_set_count": 1,
                },
                "unknown_data": {"character_sets_unknown": 0},
            },
            "skills": skills,
        },
    }
    return recommendation, state


def test_final_selection_joins_review_sources_warnings_and_exact_matchups():
    recommendation, state = _state()
    result = build_recommendation_presentation(recommendation, state)
    codes = {warning["code"] for warning in result["warnings"]}

    assert result["selected_skill_evidence_status"] == "available"
    assert result["selected_skill_count"] == 6
    assert result["skills_with_reviewed_capabilities"] == 6
    assert result["source_effect_coverage"] == "not_established"
    assert result["candidate"]["status"] == "available"
    assert result["candidate"]["modeled_roles"]["reserve_after_switch"] == ["reserve_utility"]
    assert result["candidate"]["selected_skill_matchups"] == [{
        "character_name": "DPS",
        "skill_id": "skill:character:DPS:fire-strike",
        "skill_name": "Fire Strike",
        "placement": "frontline",
        "elements": ["Fire"],
        "attack_types": ["Slash"],
        "state": "weak",
        "evidence_ids": ["skill:character:DPS:fire-strike"],
    }]
    assert codes == {
        "venom_mushroom_harm",
        "alternative_zone_options",
        "reserve_requires_switch",
    }
    venom = next(skill for skill in result["selected_skills"] if skill["skill_name"] == "Venom")
    assert venom["reviewed_effects"][0]["source_fact_id"] == venom["skill_id"]
    assert venom["source"]["source_url"].endswith("Toova#Venom")


def test_nonmatching_final_candidate_does_not_reuse_stale_scores_or_specific_warnings():
    recommendation, state = _state()
    recommendation = deepcopy(recommendation)
    state = deepcopy(state)
    state["typed_retrieval"]["boss"]["id"] = "rotte-rivel"
    state["typed_retrieval"]["boss"]["name"] = "Rotte Rivel"
    recommendation["frontline"][1]["selected_skill_ids"] = ["skill:not-the-final-zone"]

    result = build_recommendation_presentation(recommendation, state)

    assert result["candidate"]["status"] == "unavailable"
    assert result["candidate"]["selected_skill_matchups"] == []
    assert {warning["code"] for warning in result["warnings"]} == {"reserve_requires_switch"}
    assert any(skill["review_status"] == "unavailable" for skill in result["selected_skills"])


def test_missing_legacy_diagnostics_and_unknown_affinities_stay_unavailable():
    recommendation = {"frontline": [{"name": "Aldo"}], "reserve": []}
    recommendation_evidence = build_recommendation_presentation(recommendation, {})
    result_evidence = build_result_presentation({"workflow_mode": "exploratory"})

    assert recommendation_evidence["selected_skill_evidence_status"] == "unavailable"
    assert recommendation_evidence["selected_skill_count"] is None
    assert recommendation_evidence["candidate"]["status"] == "unavailable"
    assert result_evidence["request_coverage"]["status"] == "unavailable"
    assert all(item["state"] == "unavailable" for item in result_evidence["boss_affinities"])
