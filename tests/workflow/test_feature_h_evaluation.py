"""Feature H deterministic oracle, provider gate, and accounting contracts."""

import json
from pathlib import Path

import pytest

from src.workflow.analyzer import (
    ANALYZER_CUMULATIVE_TOKEN_BUDGET,
    AnalyzerProviderRequest,
    OPENROUTER_MODEL_CHAIN,
    run_bounded_analyzer,
)
from src.workflow.build_packages import build_build_package_options
from src.workflow.evaluation import (
    EvaluationFixtureError,
    _candidate_allocation_fingerprint,
    _candidate_package_fingerprint,
    _witness_matches,
    build_openrouter_fallback_config,
    classify_analyzer_run,
    load_evaluation_cases,
    load_qualification_fixture,
    qualify_openrouter_models,
    run_h03_evaluation,
    run_qualification_suite,
    summarize_analyzer_usage,
    validate_evaluation_fixture,
)
from src.workflow.lineup_generation import generate_lineup_candidates
from tests.workflow.test_lineup_generation import fixture
from tests.workflow.test_analyzer import _bundle as analyzer_bundle


ROOT = Path(__file__).parents[1]
FIXTURE_PATH = ROOT / "fixtures" / "evaluation" / "feature_h_requests.json"
QUALIFICATION_FIXTURE_PATH = ROOT / "fixtures" / "evaluation" / "feature_h_qualification.json"
REAL_CHARACTER_IDS = [
    "character:f0fc3c52900fc4c961bd",
    "character:7f07fbeae5c5e2c2e097",
    "character:02ea4044c0f45024a6a4",
    "character:660d02bd77aba6f62ade",
    "character:ad78627c89203278696e",
    "character:79086a162d31f0d0b3fe",
]


def _fixture_backend():
    characters, _, role_scores = fixture()
    encoded = json.dumps({"characters": characters, "role_scores": role_scores})
    for index, character_id in enumerate(REAL_CHARACTER_IDS):
        encoded = encoded.replace(f"character:{index}", character_id)
    remapped = json.loads(encoded)
    return generate_lineup_candidates(
        characters=remapped["characters"],
        role_scores=remapped["role_scores"],
        boss={"name": "Fixture Boss", "weak": ["Fire"]},
    )


class _RetrievalFixture:
    def __init__(self):
        self.backend = _fixture_backend()
        self.infeasible_bosses = {
            "Thunder Alter Force",
            "EPS-245 Quadoxin",
            "Calamity Serpent",
            "Terra Nivium 20,000 B.C.",
            "Demon Spider & Menreiki",
            "Shadow of the Scales",
            "White Tiger",
            "Seiryu",
            "Time Anti-Spiral",
            "Aloof Wing",
        }
        self.cases = {
            case["request"]["boss_id"]: case
            for case in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"]
        }

    async def retrieve(self, request):
        if request.boss_id in self.infeasible_bosses:
            case = self.cases[request.boss_id]
            return {
                "coverage": {"complete": True},
                "lineup_candidates": {
                    "status": "zero",
                    "candidates": [],
                    "diagnostics": {
                        "zero_candidate_causes": case["impossibility_certificate"]["zero_candidate_causes"],
                        "rejection_counts": {cause: 4 for cause in case["impossibility_certificate"]["zero_candidate_causes"]},
                        "stage_diagnostics": {case["impossibility_certificate"]["stage"]: {"rejected_attempts": 4}},
                        "readiness": {"authoritative_infeasible": True},
                    },
                },
            }
        return {
            "coverage": {"complete": True},
            "characters": [{"id": f"character:{index}"} for index in range(6)],
            "role_scores": {"policy_version": "fixture"},
            "lineup_candidates": self.backend,
        }


def test_h_fixture_has_separate_20_10_oracle_and_fixed_roster_suite():
    cases = load_evaluation_cases(FIXTURE_PATH)

    assert len(cases) == 31
    assert sum(case.expected_outcome == "feasible" and case.suite == "boss_acceptance" for case in cases) == 20
    assert sum(case.expected_outcome == "infeasible" and case.suite == "boss_acceptance" for case in cases) == 10
    assert sum(case.suite == "fixed_roster_stress" for case in cases) == 1
    assert all(case.data_complete for case in cases if case.suite == "boss_acceptance")


@pytest.mark.asyncio
async def test_h03_runner_validates_backend_before_any_analyzer_call():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    candidate = _fixture_backend()["candidates"][0]
    for case in fixture["cases"]:
        if case["expected_outcome"] != "feasible":
            continue
        case["witness"] = {
            "candidate_id": candidate["id"],
            "character_ids": candidate["character_ids"],
            "package_fingerprint": _candidate_package_fingerprint(candidate),
            "coverage_roles": ["primary_damage", "offensive_enablement", "survival"],
            "allocation_fingerprint": _candidate_allocation_fingerprint(candidate),
        }

    report = await run_h03_evaluation(fixture, _RetrievalFixture())

    assert report["h03"]["ready"] is True
    assert report["h03"]["feasible"]["passed_count"] == 20
    assert report["h03"]["infeasible"]["passed_count"] == 10
    assert report["h03"]["analyzer_call_count"] == 0
    assert report["stress_suite"]["observed_count"] == 1


def test_h03_witness_fingerprints_are_authoritative():
    candidate = _fixture_backend()["candidates"][0]
    witness = {
        "candidate_id": candidate["id"],
        "character_ids": candidate["character_ids"],
        "package_fingerprint": _candidate_package_fingerprint(candidate),
        "coverage_roles": ["primary_damage", "offensive_enablement", "survival"],
        "allocation_fingerprint": _candidate_allocation_fingerprint(candidate),
    }

    assert _witness_matches(witness, [candidate]) is True
    witness["allocation_fingerprint"] = "sha256:tampered"
    assert _witness_matches(witness, [candidate]) is False


def test_late_game_package_frontier_keeps_a_generic_allocation_fallback():
    options = build_build_package_options(
        {"id": "character:hero", "name": "Hero", "weapon": "Sword"},
        equipment=[
            {"id": "equipment:shared-sword", "name": "Shared Sword", "equipment_slot": "weapon", "category": "Sword", "level": 100},
            {"id": "equipment:shared-armor", "name": "Shared Armor", "equipment_slot": "armor", "level": 100},
        ],
        item_policy="late_game_assumed",
    )

    assert len(options) <= 6
    assert any(
        all(item.get("generic") for item in [option.get("weapon"), option.get("armor"), *option.get("grastas", []), *option.get("ores", [])])
        for option in options
    )


def test_h_fixture_rejects_incomplete_strategic_oracle_case():
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw["cases"] = [
        {
            "case_id": "bad",
            "suite": "boss_acceptance",
            "expected_outcome": "infeasible",
            "boss_fixture_id": "mimi",
            "data_complete": False,
            "request": {"boss_id": "Mimi", "roster": ["A", "B", "C", "D", "E", "F"]},
            "impossibility_certificate": {"proof_id": "bad", "zero_candidate_causes": ["missing_mandatory_coverage"]},
        }
    ]

    with pytest.raises(EvaluationFixtureError, match="complete data"):
        validate_evaluation_fixture(raw, require_h03_counts=False)


def test_openrouter_models_are_qualified_individually_before_fallback():
    bundle = {"backend_candidates": [{"id": "candidate:1", "character_ids": []}], "characters": []}
    output = {"ranked_candidate_ids": ["candidate:1"], "refinements": [], "advisories": []}
    calls = []

    def transport(request):
        calls.append(request)
        return {
            "model": request.model,
            "id": f"generation:{request.model}",
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16, "cost": 0.01},
        }

    qualification = qualify_openrouter_models(bundle, transport)
    config = build_openrouter_fallback_config(qualification)

    assert qualification["all_passed"] is True
    assert [row["model"] for row in qualification["models"]] == list(OPENROUTER_MODEL_CHAIN)
    assert len(calls) == 3
    assert config.model == OPENROUTER_MODEL_CHAIN[0]
    assert config.fallback_models == OPENROUTER_MODEL_CHAIN[1:]
    assert calls[0].fallback_models == ()
    assert "models" not in calls[0].payload


def test_progressive_qualification_fixture_runs_all_stages_and_one_correction():
    fixture = load_qualification_fixture(QUALIFICATION_FIXTURE_PATH)
    stages = {stage["stage_id"]: stage for stage in fixture["stages"]}
    calls = []

    def transport(request):
        calls.append(request)
        payload = json.loads(request.messages[1]["content"])
        stage = stages[payload["qualification_stage"]]
        output = (
            stage["initial_response"]
            if stage["stage"] == "correction_recovery" and request.call_kind == "initial"
            else stage["response"]
        )
        return {
            "model": request.model,
            "finish_reason": "stop",
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    report = run_qualification_suite(QUALIFICATION_FIXTURE_PATH, transport, model="offline-model")

    assert report["all_passed"] is True
    assert report["analyzer_call_count"] == 7
    assert report["within_cumulative_budget"] is True
    assert [stage["stage"] for stage in report["stages"]] == [
        "ranking_only",
        "ranking_refinement_no_swap",
        "authorized_swap",
        "swap_abstention",
        "full_contract",
        "correction_recovery",
    ]
    assert report["stages"][-1]["call_count"] == 2
    assert report["stages"][-1]["correction_used"] is True
    assert all(stage["diagnostics"] for stage in report["stages"])
    assert calls[0].response_schema["properties"]["refinements"]["const"] == []
    assert calls[0].response_schema["properties"]["advisories"]["const"] == []
    assert calls[2].response_schema["properties"]["refinements"]["minItems"] == 1
    assert calls[2].response_schema["properties"]["refinements"]["items"]["oneOf"]
    assert calls[-1].call_kind == "correction"
    assert "projection" not in calls[-1].messages[1]["content"]


def test_staged_model_qualification_applies_the_same_suite_without_fallback():
    fixture = load_qualification_fixture(QUALIFICATION_FIXTURE_PATH)
    stages = {stage["stage_id"]: stage for stage in fixture["stages"]}

    def transport(request):
        payload = json.loads(request.messages[1]["content"])
        stage = stages[payload["qualification_stage"]]
        output = (
            stage["initial_response"]
            if stage["stage"] == "correction_recovery" and request.call_kind == "initial"
            else stage["response"]
        )
        return {"choices": [{"message": {"content": json.dumps(output)}}], "usage": {"total_tokens": 1}}

    qualification = qualify_openrouter_models(
        {"backend_candidates": [{"id": "candidate:1", "character_ids": []}], "characters": []},
        transport,
        models=("model:a", "model:b"),
        qualification_fixture=fixture,
    )

    assert qualification["all_passed"] is True
    assert all(item["qualification"]["all_passed"] for item in qualification["models"])
    assert all(item["qualification"]["fallback_enabled"] is False for item in qualification["models"])


def test_openrouter_fallback_request_emits_ordered_server_managed_models():
    request = AnalyzerProviderRequest(
        provider="openrouter",
        model=OPENROUTER_MODEL_CHAIN[0],
        fallback_models=OPENROUTER_MODEL_CHAIN[1:],
        call_kind="initial",
        messages=[{"role": "user", "content": "{}"}],
        projection_id="projection:test",
        max_output_tokens=10,
    )

    assert request.payload["models"] == list(OPENROUTER_MODEL_CHAIN[1:])


def test_usage_summary_preserves_unavailable_cost_and_enforces_cumulative_budget():
    summary = summarize_analyzer_usage([
        {"call_number": 1, "total_tokens": 12, "cost": 0.02},
        {"call_number": 2, "total_tokens": 8},
    ])

    assert summary["total_tokens"] == 20
    assert summary["within_cumulative_budget"] is True
    assert summary["cost"] == 0.02
    assert summary["cost_status"] == "reported"
    assert summary["cumulative_budget"] == ANALYZER_CUMULATIVE_TOKEN_BUDGET
    assert summary["baseline_reduction_ge_90_percent"] is True


def test_analyzer_usage_records_served_model_and_unavailable_metadata():
    bundle = analyzer_bundle()
    candidate_id = bundle["backend_candidates"][0]["id"]
    output = {"ranked_candidate_ids": [candidate_id], "refinements": [], "advisories": []}

    result = run_bounded_analyzer(
        {
            "analyzer_provider": "openrouter",
            "user_query": "fixture",
            "candidate_warnings": [],
            "analyzer_transport": lambda request: {
                "model": "openai/gpt-5.6-luna",
                "id": "generation:fixture",
                "choices": [{"message": {"content": json.dumps(output)}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            },
        },
        bundle,
    )

    usage = result["analyzer_usage"][0]
    assert usage["requested_model"] == "openrouter/auto"
    assert usage["served_model"] == "openai/gpt-5.6-luna"
    assert usage["served_model_status"] == "reported"
    assert usage["metadata_availability"]["cost"] == "unavailable"
    assert usage["metadata_availability"]["generation_id"] == "reported"


def test_analyzer_budget_stops_correction_after_a_per_call_overage():
    bundle = analyzer_bundle()
    candidate_id = bundle["backend_candidates"][0]["id"]
    calls = []

    def transport(request):
        calls.append(request)
        output = {
            "ranked_candidate_ids": [candidate_id],
            "refinements": [{"candidate_id": "candidate:forged"}],
            "advisories": [],
        }
        return {
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {"total_tokens": 20_001},
        }

    result = run_bounded_analyzer(
        {"analyzer_provider": "deepseek", "user_query": "fixture", "candidate_warnings": [], "analyzer_transport": transport},
        bundle,
    )

    assert len(calls) == 1
    assert result["analyzer_call_count"] == 1
    assert json.loads(result["analysis_result"])["degraded"] is True
    assert any("per-call ceiling" in warning for warning in json.loads(result["analysis_result"])["warnings"])


def test_h06_classification_keeps_transport_validation_budget_and_readiness_distinct():
    classification = classify_analyzer_run({
        "analysis_failure": {"type": "analyzer_degraded"},
        "structured_output_errors": [{"code": "structured_output.invalid_json"}],
        "candidate_validation_errors": [{"code": "id.skill"}],
        "analyzer_usage": [{
            "provider": "openrouter",
            "error_code": "provider.transport_error",
            "fallback": {"used": True},
        }],
        "warnings": ["Analyzer budget degradation: cumulative usage exceeded."],
        "degraded": True,
    })

    assert classification["categories"] == [
        "analyzer_refinement_failure",
        "analyzer_structure_failure",
        "budget_degradation",
        "local_validation_failure",
        "model_provider_fallback",
        "openrouter_transport_failure",
        "readiness_degraded",
    ]
    assert classification["ready_for_later_human_review"] is False
