"""Feature C bounded analyzer correction and valid-lineup freezing tests."""

import json
from copy import deepcopy
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from src.workflow.nodes.analyze import (
    _candidate_prompt_bundle,
    analyze_node,
)
from tests.workflow.test_candidates import candidate_bundle, candidate_lineup


def _state(bundle):
    return {
        "user_query": "Create a lineup to defeat Mimi",
        "roster": [character["name"] for character in bundle["characters"]],
        "owned_sidekicks": ["Tetra"],
        "stellar_awakened": {},
        "plan_strategy": "Use Mimi weakness and mechanics candidates",
        "db_results": [{"boss": "Mimi"}],
        "retry_count": 1,
        "candidate_bundle": bundle,
        "candidate_warnings": [],
    }


def _mock_llm(*payloads):
    llm = MagicMock()
    llm.invoke.side_effect = [AIMessage(content=json.dumps(payload)) for payload in payloads]
    return llm


def test_fully_valid_first_response_skips_correction_calls():
    bundle = candidate_bundle()
    recommendations = [candidate_lineup(bundle, archetype=value) for value in ("burst", "sustain", "hybrid")]
    llm = _mock_llm({"recommendations": recommendations})

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        result = analyze_node(_state(bundle))

    output = json.loads(result["analysis_result"])
    assert len(output["recommendations"]) == 3
    assert result["analyzer_call_count"] == 1
    assert result["analyzer_correction_rounds"] == 0
    assert result["cypher_retry_count"] == 1
    assert llm.invoke.call_count == 1


def test_valid_lineup_is_frozen_while_invalid_lineup_is_corrected():
    bundle = candidate_bundle()
    frozen_burst = candidate_lineup(bundle, archetype="burst")
    invalid_sustain = candidate_lineup(bundle, archetype="sustain")
    invalid_sustain["frontline"][0]["character_id"] = "character:forged"
    corrected_sustain = candidate_lineup(bundle, archetype="sustain")
    llm = _mock_llm(
        {"recommendations": [frozen_burst, invalid_sustain]},
        {"recommendations": [corrected_sustain]},
    )

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        result = analyze_node(_state(bundle))

    output = json.loads(result["analysis_result"])
    assert [item["archetype"] for item in output["recommendations"]] == ["burst", "sustain"]
    assert output["recommendations"][0]["frontline"][0]["name"] == "Akane (Alter),Blooming Blade"
    assert result["analyzer_call_count"] == 2
    assert result["analyzer_correction_rounds"] == 1
    correction_prompt = llm.invoke.call_args_list[1].args[0][1].content
    assert "id.character" in correction_prompt
    assert "character:0" in correction_prompt
    assert "frozen_valid_lineups" in correction_prompt
    correction_bundle = json.loads(correction_prompt)["candidate_bundle"]
    assert "grastas" in correction_bundle
    assert "grasta_compatibility_groups" in correction_bundle
    assert "grasta_compatibility_group_id" in correction_bundle["characters"][0]
    assert "additional_grasta_ids" in correction_bundle["characters"][0]
    assert "grastas" not in correction_bundle["characters"][0]


def test_correction_cap_is_two_rounds_and_three_calls():
    bundle = candidate_bundle()
    invalid = candidate_lineup(bundle)
    invalid["frontline"][0]["character_id"] = "character:forged"
    llm = _mock_llm(
        {"recommendations": [invalid]},
        {"recommendations": [invalid]},
        {"recommendations": [invalid]},
    )

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        result = analyze_node(_state(bundle))

    assert result["analysis_failure"]["type"] == "analyzer_correction_exhausted"
    assert result["analyzer_call_count"] == 3
    assert result["analyzer_correction_rounds"] == 2
    assert llm.invoke.call_count == 3
    assert result["candidate_validation_errors"]


def test_invalid_after_cap_is_discarded_but_valid_partial_result_survives():
    bundle = candidate_bundle()
    valid = candidate_lineup(bundle, archetype="burst")
    invalid = candidate_lineup(bundle, archetype="sustain")
    invalid["reserve"][0]["skill_ids"] = ["skill:forged"] * 3
    llm = _mock_llm(
        {"recommendations": [valid, invalid]},
        {"recommendations": [invalid]},
        {"recommendations": [invalid]},
    )

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        result = analyze_node(_state(bundle))

    output = json.loads(result["analysis_result"])
    assert [item["archetype"] for item in output["recommendations"]] == ["burst"]
    assert all("forged" not in json.dumps(item) for item in output["recommendations"])
    assert any("Discarded 1 invalid lineup" in warning for warning in output["warnings"])
    assert any("Missing valid archetypes" in warning for warning in output["warnings"])


def test_structured_output_failure_is_distinct_from_candidate_validation():
    bundle = candidate_bundle()
    valid = candidate_lineup(bundle)
    llm = MagicMock()
    llm.invoke.side_effect = [
        AIMessage(content="not-json"),
        AIMessage(content=json.dumps({"recommendations": [valid]})),
    ]

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        result = analyze_node(_state(bundle))

    assert result["structured_output_errors"][0]["code"] == "structured_output.invalid_json"
    assert result["candidate_validation_errors"] == []
    assert result["analyzer_correction_rounds"] == 1


def test_correction_does_not_mutate_frozen_payload():
    bundle = candidate_bundle()
    frozen = candidate_lineup(bundle, archetype="burst")
    frozen_before = deepcopy(frozen)
    invalid = candidate_lineup(bundle, archetype="sustain")
    invalid["citation_ids"] = ["citation:forged"]
    corrected = candidate_lineup(bundle, archetype="sustain")
    llm = _mock_llm(
        {"recommendations": [frozen, invalid]},
        {"recommendations": [corrected]},
    )

    with patch("src.workflow.nodes.analyze.get_llm", return_value=llm):
        analyze_node(_state(bundle))

    assert frozen == frozen_before


def test_prompt_bundle_deduplicates_large_shared_grasta_catalog():
    template = candidate_bundle(character_count=1)["characters"][0]
    shared_grastas = [
        {
            "id": f"grasta:{index}",
            "display_name": f"Grasta {index}",
            "effect_text": "Shared graph-backed effect " + ("x" * 500),
            "acquisition_class": "repeatable",
            "max_theoretical_copies": None,
        }
        for index in range(200)
    ]
    characters = []
    for index in range(130):
        character = deepcopy(template)
        character["id"] = f"character:{index}"
        character["name"] = f"Hero {index}"
        character["display_name"] = f"Hero {index}"
        character["grastas"] = shared_grastas
        character["skills"] = [
            {
                "id": f"skill:{index}:{skill_index}",
                "name": f"Skill {index}-{skill_index}",
                "description": "Heals, buffs Fire, and restores MP. " + ("x" * 500),
                "element": "Fire",
                "skill_type": "Magic",
            }
            for skill_index in range(30)
        ]
        character["passives"] = [
            {
                "id": f"passive:{index}:{passive_index}",
                "name": f"Passive {index}-{passive_index}",
                "description": "Critical buff and status resistance. " + ("x" * 500),
            }
            for passive_index in range(6)
        ]
        characters.append(character)
    bundle = candidate_bundle()
    bundle["characters"] = characters
    bundle["coverage"] = {
        "eligible_roster_count": 130,
        "candidate_character_count": 130,
        "missing_character_names": [],
        "complete": True,
    }

    original_bytes = len(json.dumps(bundle).encode("utf-8"))
    prompt_bundle = _candidate_prompt_bundle(bundle)
    compact_bytes = len(
        json.dumps(prompt_bundle, separators=(",", ":")).encode("utf-8")
    )

    assert original_bytes > 8_000_000
    assert compact_bytes < 450_000
    assert len(prompt_bundle["characters"]) == 130
    assert len(prompt_bundle["grastas"]) == 200
    assert len(prompt_bundle["global_grasta_ids"]) == 200
    assert len(prompt_bundle["grasta_compatibility_groups"]) == 1
    assert not prompt_bundle["grasta_compatibility_groups"][0]["grasta_ids"]
    assert all(not character["additional_grasta_ids"] for character in prompt_bundle["characters"])


def test_prompt_compatibility_groups_preserve_each_character_allowed_ids():
    bundle = candidate_bundle()
    bundle["characters"][1]["grastas"] = bundle["characters"][1]["grastas"][:2]

    prompt_bundle = _candidate_prompt_bundle(bundle)
    groups = {
        group["id"]: set(group["grasta_ids"])
        for group in prompt_bundle["grasta_compatibility_groups"]
    }

    for original, compact in zip(
        bundle["characters"],
        prompt_bundle["characters"],
    ):
        expected = {grasta["id"] for grasta in original["grastas"]}
        actual = (
            set(prompt_bundle["global_grasta_ids"])
            | groups[compact["grasta_compatibility_group_id"]]
            | set(compact["additional_grasta_ids"])
        )
        assert actual == expected


def test_oversized_compacted_payload_fails_before_provider_call():
    bundle = candidate_bundle()
    with patch("src.workflow.nodes.analyze.ANALYZER_PROMPT_TEXT_LIMIT_BYTES", 1), \
         patch("src.workflow.nodes.analyze.get_llm") as get_llm:
        result = analyze_node(_state(bundle))

    assert result["analysis_failure"]["type"] == "candidate_payload_too_large"
    assert result["analyzer_call_count"] == 0
    get_llm.assert_not_called()
