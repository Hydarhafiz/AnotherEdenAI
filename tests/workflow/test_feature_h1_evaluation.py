"""Feature H1 offline comparison harness contracts."""

import json
from pathlib import Path

import pytest

from src.workflow.analyzer import AnalyzerProviderRequest, build_compact_projection
from src.workflow.h1_evaluation import (
    H1Scenario,
    H1_VARIANTS,
    _aggregate_reports,
    compare_h1_bundle,
    load_h1_scenarios,
    run_h1_evaluation,
)
from tests.workflow.test_analyzer import _bundle


ROOT = Path(__file__).parents[1]
REQUEST_FIXTURE = ROOT / "fixtures" / "evaluation" / "feature_h_requests.json"


def _provider_output(candidate_id: str):
    return {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "ranked_candidate_ids": [candidate_id],
                    "refinements": [],
                    "advisories": [],
                })
            }
        }],
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 30,
            "completion_tokens": 10,
            "reasoning_tokens": 2,
            "total_tokens": 42,
            "cost": 0.01,
            "latency_ms": 11,
        },
    }


def test_h1_variants_construct_exact_reasoning_and_bounded_payloads():
    projection = {"projection_id": "projection:h1", "candidate_ids": ["candidate:one"]}
    requests = [
        AnalyzerProviderRequest(
            provider=variant.config().provider,
            model=variant.config().resolved_model,
            call_kind="initial",
            messages=[{"role": "user", "content": "{}"}],
            projection_id=projection["projection_id"],
            max_output_tokens=variant.max_output_tokens,
            reasoning_effort=variant.reasoning_effort,
        )
        for variant in H1_VARIANTS
    ]

    assert [(variant.reasoning_effort, variant.max_output_tokens) for variant in H1_VARIANTS] == [
        ("none", 4_000),
        ("low", 8_000),
    ]
    assert all(request.payload["model"] == "deepseek/deepseek-v4-flash-0731" for request in requests)
    assert [request.payload["reasoning"] for request in requests] == [
        {"effort": "none"},
        {"effort": "low"},
    ]
    assert [request.payload["max_tokens"] for request in requests] == [4_000, 8_000]
    assert all("models" not in request.payload for request in requests)


def test_h1_runs_both_variants_with_one_equivalent_compact_projection():
    bundle = _bundle()
    projection = build_compact_projection(bundle, user_query="Mimi")
    candidate_id = projection["candidate_ids"][0]
    calls = []

    def transport(request):
        calls.append(request)
        return _provider_output(candidate_id)

    report = compare_h1_bundle(
        H1Scenario("H1-fixture", {"boss_id": "Mimi", "roster": ["Hero 0"], "preferences": "Mimi"}),
        bundle,
        projection,
        transport,
    )

    assert report["status"] == "completed"
    assert len(calls) == 2
    assert {call.projection_id for call in calls} == {projection["projection_id"]}
    assert {call.payload["reasoning"]["effort"] for call in calls} == {"none", "low"}
    assert {call.payload["max_tokens"] for call in calls} == {4_000, 8_000}
    assert all("models" not in call.payload for call in calls)
    assert all("full_catalog" not in json.dumps(call.payload) for call in calls)
    assert report["projection"]["candidate_count"] <= 10
    assert report["comparison"]["same_top_candidate"] is True
    assert report["comparison"]["same_ranking"] is True
    assert report["comparison"]["both_valid"] is True
    assert report["comparison"]["candidate_ids_closed_world"] is True
    assert report["comparison"]["skill_selections_valid"] is True
    assert report["comparison"]["token_delta"] == 0
    assert report["comparison"]["cost_delta"] == 0
    assert report["comparison"]["latency_delta_ms"] == 0


@pytest.mark.asyncio
async def test_h1_prepares_real_pipeline_once_before_running_two_arms():
    bundle = _bundle()
    skills = [
        {**skill, "character_name": character["name"]}
        for character in bundle["characters"]
        for skill in character.get("skills", [])
    ]
    passives = [
        {**passive, "character_name": character["name"]}
        for character in bundle["characters"]
        for passive in character.get("passives", [])
    ]
    retrieval = {
        "request": {"item_policy": "late_game_assumed", "stellar_awakened": {}},
        "boss": bundle["boss"],
        "characters": bundle["characters"],
        "skills": skills,
        "passives": passives,
        "mechanics": [],
        "sidekicks": [],
        "grastas": [],
        "equipment": [],
        "coverage": {"complete": True},
        "role_scores": bundle["backend_role_scores"],
        "lineup_candidates": bundle["candidate_generation"],
    }

    class Retrieval:
        calls = 0

        async def retrieve(self, _request):
            self.calls += 1
            return retrieval

    retrieval_service = Retrieval()
    calls = []

    def transport(request):
        calls.append(request)
        return _provider_output(build_compact_projection(bundle)["candidate_ids"][0])

    report = await run_h1_evaluation(
        [H1Scenario("H1-real-pipeline", {"boss_id": "Mimi", "roster": ["Hero 0"]})],
        retrieval_service,
        transport,
    )

    assert retrieval_service.calls == 1
    assert len(calls) == 2
    assert report["scenarios"][0]["projection"]["candidate_count"] <= 10
    assert report["scenarios"][0]["comparison"]["both_valid"] is True


def test_h1_captures_provider_errors_and_forbidden_fallback_without_raw_body():
    bundle = _bundle()
    projection = build_compact_projection(bundle)
    candidate_id = projection["candidate_ids"][0]

    def transport(request):
        return {
            **_provider_output(candidate_id),
            "fallback": {"used": True, "served_model": "other/model"},
            "model": "other/model",
        }

    report = compare_h1_bundle(
        H1Scenario("H1-fallback", {"boss_id": "Mimi", "roster": ["Hero 0"]}),
        bundle,
        projection,
        transport,
    )

    assert report["variants"]["baseline_a"]["fallback_forbidden"] == {"used": True, "passed": False}
    assert report["variants"]["variant_b"]["fallback_forbidden"] == {"used": True, "passed": False}
    assert report["comparison"]["both_valid"] is True
    assert "other/model" in json.dumps(report)


def test_h1_captures_provider_and_application_validation_failures():
    bundle = _bundle()
    projection = build_compact_projection(bundle)

    def provider_error(_request):
        return {"error": {"code": "provider.rate_limited", "message": "redacted provider detail"}}

    provider_report = compare_h1_bundle(
        H1Scenario("H1-provider-error", {"boss_id": "Mimi", "roster": ["Hero 0"]}),
        bundle,
        projection,
        provider_error,
    )
    assert provider_report["variants"]["baseline_a"]["provider_errors"] == [
        {"call_number": 1, "code": "provider.rate_limited"}
    ]
    assert provider_report["variants"]["baseline_a"]["application_validation"]["final_response_valid"] is False
    assert "redacted provider detail" not in json.dumps(provider_report)

    def invalid_output(_request):
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "ranked_candidate_ids": ["candidate:forged"],
                        "refinements": [],
                        "advisories": [],
                    })
                }
            }],
            "usage": {"total_tokens": 3},
        }

    validation_report = compare_h1_bundle(
        H1Scenario("H1-validation-error", {"boss_id": "Mimi", "roster": ["Hero 0"]}),
        bundle,
        projection,
        invalid_output,
    )
    assert validation_report["variants"]["variant_b"]["application_validation"]["final_response_valid"] is False
    assert validation_report["variants"]["variant_b"]["application_validation"]["attempts"]
    assert validation_report["variants"]["variant_b"]["application_validation"]["attempts"][0]["passed"] is False


def test_h1_aggregates_completed_and_preparation_failure_reports_without_winner():
    reports = _aggregate_reports([
        {"status": "completed", "scenario_id": "one"},
        {"status": "no_backend_candidates", "scenario_id": "two"},
    ], 2)

    assert reports["scenario_count"] == 2
    assert reports["initial_call_estimate"] == 4
    assert reports["maximum_application_call_count"] == 8
    assert reports["completed_scenario_count"] == 1
    assert reports["winner"] is None
    assert reports["production_configuration_changed"] is False


def test_h1_loader_selects_a_small_real_fixture_subset_in_requested_order():
    scenarios = load_h1_scenarios(
        REQUEST_FIXTURE,
        scenario_ids=["H-F01", "H-F03", "H-F05", "H-F08", "H-F12"],
    )

    assert [scenario.scenario_id for scenario in scenarios] == ["H-F01", "H-F03", "H-F05", "H-F08", "H-F12"]
    assert [scenario.request["boss_id"] for scenario in scenarios] == [
        "Zennon Ogre's Shadow",
        "Cradle System",
        "Nameless Girl",
        "Rotte Rivel",
        "Berserk Tempered Hound",
    ]
