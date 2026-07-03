"""Feature C deterministic candidate preparation and hard-field guardrails."""

import json
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.workflow.candidates import (
    prepare_candidates_node,
    resolve_candidate_recommendations,
    validate_candidate_response,
)


def candidate_bundle(*, character_count=6):
    characters = []
    for index in range(character_count):
        name = "Akane (Alter),Blooming Blade" if index == 0 else f"Hero {index}"
        skills = [
            {
                "id": f"skill:{index}:{skill_index}",
                "name": "Pain Setter" if index == 0 and skill_index == 0 else f"Skill {index}-{skill_index}",
                "description": "Inflicts Pain" if index == 0 and skill_index == 0 else "Graph-backed skill",
                "requires_stellar_awakened": skill_index == 3,
            }
            for skill_index in range(4)
        ]
        characters.append(
            {
                "id": f"character:{index}",
                "name": name,
                "display_name": name,
                "aliases": [name, "Akane Alter"] if index == 0 else [name],
                "weapon": "Katana" if index == 0 else "Sword",
                "traits": ["Eastern"] if index == 0 else ["Hero"],
                "skills": skills,
                "passives": [{"id": f"passive:{index}", "name": f"Passive {index}", "description": "Support"}],
                "weapon_options": [{"id": f"weapon:{index}", "display_name": "Katana" if index == 0 else "Sword", "generic": True}],
                "armor_options": [{"id": f"armor:{index}", "display_name": "available armor", "generic": True}],
                "grastas": [
                    {
                        "id": "grasta:repeatable",
                        "display_name": "Power of Mind",
                        "effect_text": "General power",
                        "acquisition_class": "repeatable",
                        "max_theoretical_copies": None,
                    },
                    {
                        "id": "grasta:unique",
                        "display_name": "Almighty Power (Eastern)",
                        "effect_text": "Personality power",
                        "acquisition_class": "unique",
                        "max_theoretical_copies": 1,
                    },
                    {
                        "id": "grasta:pain",
                        "display_name": "Pain Katana Grasta",
                        "effect_text": "Damage while enemy has Pain",
                        "acquisition_class": "repeatable",
                        "max_theoretical_copies": None,
                    },
                ],
            }
        )
    return {
        "version": "feature-c-v1",
        "characters": characters,
        "sidekicks": [{"id": "sidekick:tetra", "name": "Tetra", "skills": [], "auras": []}],
        "stellar_awakened": {},
        "boss": {
            "name": "Mimi",
            "affinities": {"weak": ["Fire"], "resist": [], "null": [], "absorb": []},
            "facts": [{"id": "boss-fact:mimi", "kind": "affinities", "value": {"weak": ["Fire"]}}],
            "citations": [{"id": "citation:mimi", "label": "Mimi", "source_url": "https://example.test/Mimi"}],
        },
        "coverage": {
            "eligible_roster_count": character_count,
            "candidate_character_count": character_count,
            "missing_character_names": [],
            "complete": True,
        },
        "ranking_policy": {
            "frontline": "Prefer Pain/Poison with a setter.",
            "reserve": "Prefer distinct Dormant-shareable Grasta.",
        },
    }


def candidate_lineup(bundle, *, archetype="burst"):
    def hero(character):
        return {
            "character_id": character["id"],
            "role": "DPS",
            "weapon_id": character["weapon_options"][0]["id"],
            "armor_id": character["armor_options"][0]["id"],
            "grasta_ids": ["grasta:repeatable"] * 3,
            "skill_ids": [choice["id"] for choice in character["skills"][:3]],
            "passive_ids": [character["passives"][0]["id"]],
            "upgrade_assumptions": [],
        }

    return {
        "archetype": archetype,
        "frontline": [hero(character) for character in bundle["characters"][:4]],
        "reserve": [hero(character) for character in bundle["characters"][4:6]],
        "main_sidekick_id": "sidekick:tetra",
        "sub_sidekick_id": None,
        "strategy_summary": "Use graph-backed candidates against Mimi.",
        "key_facts": ["Mimi is weak to Fire."],
        "build_notes": ["Generic equipment assumptions only."],
        "boss_counterplay_notes": ["Exploit the recorded weakness."],
        "sustain_mp_notes": ["Monitor MP."],
        "risks": ["Exact damage is not simulated."],
        "fit_label": "high",
        "confidence_label": "medium",
        "rubric_summary": {"offense": "high - weakness coverage"},
        "citation_ids": ["citation:mimi"],
        "boss_fact_ids": ["boss-fact:mimi"],
        "synergy_explanation": "Candidate IDs provide the legal build.",
    }


def test_valid_candidate_ids_resolve_only_after_validation_and_preserve_alias_name():
    bundle = candidate_bundle()
    proposal = candidate_lineup(bundle)

    valid, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
    resolved = resolve_candidate_recommendations(valid, bundle, [])

    assert invalid == []
    assert resolved["recommendations"][0]["frontline"][0]["name"] == "Akane (Alter),Blooming Blade"
    assert resolved["recommendations"][0]["frontline"][0]["recommended_skills"] == [
        "Pain Setter", "Skill 0-1", "Skill 0-2"
    ]
    assert resolved["boss_affinity"]["weak"] == ["Fire"]


def test_unknown_character_id_returns_structured_path_and_allowed_replacements():
    bundle = candidate_bundle()
    proposal = candidate_lineup(bundle)
    proposal["frontline"][0]["character_id"] = "character:invented"

    valid, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
    diagnostic = next(error for error in invalid[0]["errors"] if error["code"] == "id.character")

    assert valid == []
    assert diagnostic["path"] == "recommendations.0.frontline.0.character_id"
    assert "character:0" in diagnostic["allowed_ids"]
    assert "character:invented" not in diagnostic["allowed_ids"]


def test_incompatible_grasta_id_is_rejected_with_only_character_compatible_ids():
    bundle = candidate_bundle()
    bundle["characters"][0]["grastas"] = [bundle["characters"][0]["grastas"][0]]
    proposal = candidate_lineup(bundle)
    proposal["frontline"][0]["grasta_ids"] = ["grasta:forged"] * 3

    _, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
    diagnostic = next(error for error in invalid[0]["errors"] if error["code"] == "id.grasta")

    assert diagnostic["allowed_ids"] == ["grasta:repeatable"]


def test_exhausted_unique_grasta_is_excluded_from_allowed_replacements():
    bundle = candidate_bundle()
    proposal = candidate_lineup(bundle)
    proposal["frontline"][0]["grasta_ids"] = ["grasta:unique"] * 3

    _, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
    diagnostic = next(error for error in invalid[0]["errors"] if error["code"] == "cardinality.grasta")

    assert "grasta:unique" not in diagnostic["allowed_ids"]
    assert "grasta:repeatable" in diagnostic["allowed_ids"]


def test_pain_grasta_requires_status_source_and_accepts_selected_setter():
    bundle = candidate_bundle()
    without_source = candidate_lineup(bundle)
    without_source["frontline"][0]["grasta_ids"] = ["grasta:pain"] * 3
    without_source["frontline"][0]["skill_ids"] = [
        bundle["characters"][0]["skills"][index]["id"] for index in (1, 2, 3)
    ]
    without_source["frontline"][0]["upgrade_assumptions"] = ["Skill 0-3 requires Stellar Awakening"]

    _, invalid = validate_candidate_response({"recommendations": [without_source]}, bundle)
    assert any(error["code"] == "status.source_missing" for error in invalid[0]["errors"])

    with_source = deepcopy(without_source)
    with_source["frontline"][0]["skill_ids"][0] = "skill:0:0"
    valid, invalid = validate_candidate_response({"recommendations": [with_source]}, bundle)
    assert len(valid) == 1
    assert invalid == []


def test_unique_cardinality_resets_between_independent_lineups():
    bundle = candidate_bundle()
    first = candidate_lineup(bundle, archetype="burst")
    second = candidate_lineup(bundle, archetype="sustain")
    first["frontline"][0]["grasta_ids"] = ["grasta:unique", "grasta:repeatable", "grasta:repeatable"]
    second["reserve"][0]["grasta_ids"] = ["grasta:unique", "grasta:repeatable", "grasta:repeatable"]

    valid, invalid = validate_candidate_response({"recommendations": [first, second]}, bundle)

    assert len(valid) == 2
    assert invalid == []


def test_valid_and_invalid_lineups_are_classified_independently():
    bundle = candidate_bundle()
    valid_lineup = candidate_lineup(bundle, archetype="burst")
    invalid_lineup = candidate_lineup(bundle, archetype="sustain")
    invalid_lineup["reserve"][1]["skill_ids"] = ["skill:forged"] * 3

    valid, invalid = validate_candidate_response(
        {"recommendations": [valid_lineup, invalid_lineup]}, bundle
    )

    assert valid == [valid_lineup]
    assert invalid[0]["proposal"] == invalid_lineup
    assert any(error["code"] == "id.skill" for error in invalid[0]["errors"])


@pytest.mark.asyncio
async def test_candidate_preparation_preserves_full_roster_and_reports_missing_coverage():
    character_rows = [
        {"id": f"character:{index}", "name": f"Hero {index}", "display_name": f"Hero {index}", "aliases": [], "weapon": "Sword", "has_stellar_awakening": False}
        for index in range(13)
    ]
    driver = MagicMock()
    driver.execute_query = AsyncMock(
        side_effect=[
            (character_rows, None, None),
            ([], None, None),
            ([], None, None),
            ([], None, None),
            ([], None, None),
            ([], None, None),
        ]
    )
    state = {
        "roster": [*[f"Hero {index}" for index in range(13)], "Missing Hero"],
        "owned_sidekicks": [],
        "boss_context": "",
        "stellar_awakened": {},
    }

    result = await prepare_candidates_node(state, driver)

    assert len(result["candidate_bundle"]["characters"]) == 13
    assert result["candidate_bundle"]["coverage"]["missing_character_names"] == ["Missing Hero"]
    assert "Missing Hero" in result["candidate_warnings"][0]
    assert driver.execute_query.call_count == 6


@pytest.mark.asyncio
async def test_candidate_preparation_preserves_persisted_skill_and_passive_ids():
    driver = MagicMock()
    driver.execute_query = AsyncMock(side_effect=[
        ([{"id": "character:aldo", "name": "Aldo", "display_name": "Aldo", "aliases": ["Aldo"], "weapon": "Sword", "has_stellar_awakening": False}], None, None),
        ([], None, None),
        ([{"character_name": "Aldo", "id": "skill:persisted", "name": "X Slash", "description": "Slash attack"}], None, None),
        ([{"character_name": "Aldo", "id": "passive:persisted", "name": "Dragon God", "description": "Battle passive"}], None, None),
        ([], None, None),
        ([], None, None),
    ])

    result = await prepare_candidates_node(
        {"roster": ["Aldo"], "owned_sidekicks": [], "boss_context": "", "stellar_awakened": {}},
        driver,
    )

    character = result["candidate_bundle"]["characters"][0]
    assert character["skills"][0]["id"] == "skill:persisted"
    assert character["passives"][0]["id"] == "passive:persisted"


def test_ranking_policy_keeps_status_and_reserve_preferences_non_mandatory():
    bundle = candidate_bundle()
    policy = json.dumps(bundle["ranking_policy"])

    assert "Prefer Pain/Poison" in policy
    assert "Prefer distinct Dormant" in policy
    proposal = candidate_lineup(bundle)
    valid, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
    assert len(valid) == 1
    assert invalid == []
