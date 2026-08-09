"""Feature G analyzer projection, adapter, and bounded refinement evidence."""

import json
from copy import deepcopy

from src.workflow.analyzer import (
    AnalyzerProviderConfig,
    AnalyzerProviderRequest,
    DeepSeekAnalyzerAdapter,
    OpenRouterAnalyzerAdapter,
    build_compact_projection,
    correction_payload,
    run_bounded_analyzer,
    validate_analyzer_output,
)
from src.web.routes.api import QueryRequest
from tests.workflow.test_lineup_generation import fixture


def _bundle():
    characters, entities, role_scores = fixture()
    for index, (character, entity) in enumerate(zip(characters, entities)):
        package = entity["build_package"]
        character.update(
            {
                "display_name": character["name"],
                "weapon": "Sword",
                "traits": ["Hero"],
                "skills": [
                    {"id": f"skill:{index}:{slot}", "name": f"Skill {index}-{slot}", "description": "Backend skill", "element": "Fire"}
                    for slot in range(4)
                ],
                "passives": [{"id": f"passive:{index}", "name": f"Passive {index}", "description": "Backend passive"}],
                "weapon_options": [{"id": package["weapon"]["id"], "display_name": "Backend weapon", "generic": True}],
                "armor_options": [{"id": package["armor"]["id"], "display_name": "Backend armor", "generic": True}],
                "grastas": [
                    {"id": item["id"], "display_name": item["name"], "effect_text": "Generic power", "generic": True}
                    for item in package["grastas"]
                ],
                "build_package": package,
                "role_ids": entity["role_ids"],
            }
        )
        entity["skill_shortlists"] = {
            "primary_damage": [
                {"skill_id": f"skill:{index}:0", "score": 10},
                {"skill_id": f"skill:{index}:1", "score": 10},
                {"skill_id": f"skill:{index}:2", "score": 10},
                {"skill_id": f"skill:{index}:3", "score": 1},
            ]
        }
    from src.workflow.lineup_generation import generate_lineup_candidates

    generated = generate_lineup_candidates(
        characters=characters,
        role_scores=role_scores,
        boss={"name": "Mimi", "weak": ["Fire"]},
    )
    return {
        "version": "feature-g-backend-bundle-v1",
        "item_policy": "late_game_assumed",
        "characters": characters,
        "sidekicks": [],
        "boss": {
            "name": "Mimi",
            "affinities": {"weak": ["Fire"], "resist": [], "null": [], "absorb": []},
            "facts": [{"id": "fact:mimi", "kind": "affinity", "value": {"weak": ["Fire"]}}],
            "citations": [{"id": "citation:mimi", "label": "Mimi source", "source_url": "https://example.test/mimi"}],
        },
        "coverage": {"complete": True},
        "backend_candidates": generated["candidates"],
        "candidate_generation": generated,
        "backend_role_scores": role_scores,
    }


def _state(bundle, *, transport=None, provider="deepseek"):
    return {
        "user_query": "Build a safe lineup for Mimi",
        "candidate_bundle": bundle,
        "candidate_warnings": [],
        "analyzer_provider": provider,
        "analyzer_model": None,
        "analyzer_transport": transport,
        "analyzer_port": None,
    }


def _provider_output(output):
    return {"choices": [{"message": {"content": json.dumps(output)}}], "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}


def test_provider_selection_is_explicit_in_the_request_contract():
    request = QueryRequest(query="safe team", roster=["Hero 0"], analyzer_provider="deepseek", analyzer_model="review-model")

    assert request.analyzer_provider == "deepseek"
    assert request.analyzer_model == "review-model"


def test_projection_is_closed_world_and_does_not_forward_broad_catalogs_or_free_text_authority():
    bundle = _bundle()
    bundle["characters"].append({"id": "character:rejected", "display_name": "Rejected", "skills": [{"id": "forged", "description": "huge"}]})
    bundle["full_catalog"] = {"every_character": ["rejected"], "all_grastas": ["forged"]}

    projection = build_compact_projection(bundle, user_query="Mimi")

    projected_ids = set(projection["catalogs"]["characters"])
    candidate_ids = set(projection["candidate_ids"])
    assert "character:rejected" not in projected_ids
    assert projected_ids == {hero_id for candidate in bundle["backend_candidates"] for hero_id in candidate["character_ids"]}
    assert "full_catalog" not in json.dumps(projection)
    assert "mandatory_coverage" in projection["constraints"]["forbidden_analyzer_fields"]
    assert projection["projection_id"].startswith("projection:")
    assert candidate_ids


def test_provider_adapters_share_structured_request_and_usage_error_envelope_offline():
    output = {"ranked_candidate_ids": ["candidate:1"], "refinements": [], "advisories": []}
    requests = []

    def transport(request):
        requests.append(request)
        return _provider_output(output)

    common = {
        "call_kind": "initial",
        "messages": [{"role": "user", "content": "{}"}],
        "projection_id": "projection:test",
        "max_output_tokens": 10,
    }
    deepseek = DeepSeekAnalyzerAdapter(AnalyzerProviderConfig(provider="deepseek"), transport)
    openrouter = OpenRouterAnalyzerAdapter(AnalyzerProviderConfig(provider="openrouter"), transport)
    deepseek_result = deepseek.generate(AnalyzerProviderRequest(provider="deepseek", model="deepseek-chat", **common))
    openrouter_result = openrouter.generate(AnalyzerProviderRequest(provider="openrouter", model="openrouter/auto", **common))

    assert deepseek_result.output == openrouter_result.output == output
    assert set(deepseek_result.as_dict()) == set(openrouter_result.as_dict())
    assert deepseek_result.usage["total_tokens"] == openrouter_result.usage["total_tokens"] == 18
    assert requests[0].payload["response_format"]["json_schema"]["strict"] is True
    assert requests[0].payload["response_format"] == requests[1].payload["response_format"]
    assert "api_key" not in json.dumps(deepseek_result.as_dict()).lower()


def test_analyzer_rejects_out_of_bundle_ids_role_authority_and_mandatory_coverage_claims():
    projection = build_compact_projection(_bundle())
    candidate_id = projection["candidate_ids"][0]
    bad = {
        "ranked_candidate_ids": [candidate_id],
        "refinements": [{
            "candidate_id": candidate_id,
            "role_ids": ["forged-role"],
            "skill_selections": {"character:forged": ["skill:forged"]},
            "mandatory_coverage": ["everything"],
        }],
        "advisories": [],
    }

    valid, invalid, errors = validate_analyzer_output(bad, projection)

    assert valid == []
    assert invalid
    assert any(error["code"] == "authority.forbidden_field" for error in errors)
    assert any(error["code"] == "authority.forbidden_field" for error in invalid[0]["errors"])


def test_bounded_correction_freezes_valid_candidate_and_sends_only_fragments():
    bundle = _bundle()
    candidate_ids = [candidate["id"] for candidate in bundle["backend_candidates"][:2]]
    initial = {
        "ranked_candidate_ids": candidate_ids,
        "refinements": [
            {"candidate_id": candidate_ids[0], "strategy_summary": "Keep the backend plan.", "explanation": "Advisory coherence."},
            {"candidate_id": "candidate:forged", "role_ids": ["forged"]},
        ],
        "advisories": [],
    }
    corrected = {
        "ranked_candidate_ids": [candidate_ids[0], candidate_ids[1]],
        "refinements": [{"candidate_id": candidate_ids[1], "explanation": "Corrected advisory."}],
        "advisories": [],
    }
    calls = []

    def transport(request):
        calls.append(request)
        return _provider_output(initial if request.call_kind == "initial" else corrected)

    result = run_bounded_analyzer(_state(bundle, transport=transport), bundle)

    assert result["analyzer_call_count"] == 2
    assert result["analyzer_correction_rounds"] == 1
    assert len(calls) == 2
    correction_content = calls[1].messages[1]["content"]
    assert "projection" not in correction_content
    assert "catalogs" not in correction_content
    rendered = json.loads(result["analysis_result"])
    assert len(rendered["recommendations"]) == 2
    assert rendered["recommendations"][0]["strategy_summary"] == "Keep the backend plan."


def test_provider_failure_returns_labeled_degraded_backend_candidates_without_retry():
    bundle = _bundle()
    result = run_bounded_analyzer(_state(bundle), bundle)
    output = json.loads(result["analysis_result"])

    assert result["analyzer_call_count"] == 1
    assert result["provider_transport_retries"] == 0
    assert result["analysis_failure"]["type"] == "analyzer_degraded"
    assert output["degraded"] is True
    assert output["recommendations"]
    assert any("degraded" in warning.casefold() for warning in output["warnings"])


def test_lower_scoring_skill_package_restores_backend_default():
    bundle = _bundle()
    candidate = bundle["backend_candidates"][0]
    character_id = candidate["character_ids"][0]
    output = {
        "ranked_candidate_ids": [candidate["id"]],
        "refinements": [{
            "candidate_id": candidate["id"],
            "skill_selections": {character_id: [f"skill:{character_id.rsplit(':', 1)[-1]}:0", f"skill:{character_id.rsplit(':', 1)[-1]}:1", f"skill:{character_id.rsplit(':', 1)[-1]}:3"]},
        }],
        "advisories": [],
    }

    result = run_bounded_analyzer(_state(bundle, transport=lambda request: _provider_output(output)), bundle)

    assert any("lower-scoring skill package" in warning for warning in json.loads(result["analysis_result"])["warnings"])
