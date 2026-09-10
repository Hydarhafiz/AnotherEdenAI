"""Deterministic Feature H evaluation and provider-admission contracts.

The H-03 runner deliberately stops at typed production retrieval.  It never
invokes the analyzer, so a zero-candidate result cannot be hidden by a paid
call.  Provider qualification is a separate, transport-injected operation and
does not read credentials or perform network I/O itself.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .analyzer import (
    ANALYZER_MAX_CALLS,
    ANALYZER_CUMULATIVE_TOKEN_BUDGET,
    AnalyzerProviderConfig,
    AnalyzerProviderRequest,
    OPENROUTER_MODEL_CHAIN,
    QUALIFICATION_STAGES,
    build_provider_diagnostic,
    build_compact_projection,
    build_request_specific_response_schema,
    correction_payload,
    create_analyzer_port,
    validate_analyzer_output,
)
from .production import ProductionRequestError, validate_production_request


EVALUATION_POLICY_VERSION = "feature-h-evaluation-v1"
REQUEST_FIXTURE_VERSION = "feature-h-request-fixtures-v1"
QUALIFICATION_FIXTURE_VERSION = "feature-h-qualification-v1"
HISTORICAL_BASELINE_TOKENS = 601_000
H03_FEASIBLE_COUNT = 20
H03_INFEASIBLE_COUNT = 10
H03_EXPECTED_COUNT = H03_FEASIBLE_COUNT + H03_INFEASIBLE_COUNT
REQUIRED_POLICY_VERSION_FIELDS = (
    "kit_corpus",
    "kit_receipts",
    "capability",
    "package_policy",
    "allocation_policy",
    "search_policy",
    "boss_fixture",
    "request_fixture",
)


class EvaluationFixtureError(ValueError):
    """A malformed or non-authoritative evaluation fixture."""


@dataclass(frozen=True)
class EvaluationCase:
    """One versioned H request and its independent expected oracle."""

    case_id: str
    suite: str
    expected_outcome: str
    request: dict[str, Any]
    boss_fixture_id: str
    witness: dict[str, Any] | None = None
    impossibility_certificate: dict[str, Any] | None = None
    data_complete: bool = True
    source_authority: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvaluationCase":
        case_id = str(value.get("case_id") or value.get("id") or "").strip()
        suite = str(value.get("suite") or "").strip()
        expected = str(value.get("expected_outcome") or value.get("outcome") or "").strip().casefold()
        request = value.get("request")
        boss_fixture_id = str(value.get("boss_fixture_id") or value.get("boss_id") or "").strip()
        witness = value.get("witness")
        certificate = value.get("impossibility_certificate")
        if not case_id or not suite or expected not in {"feasible", "infeasible", "stress"}:
            raise EvaluationFixtureError(f"Invalid evaluation case header: {case_id or '<missing>'}")
        if not isinstance(request, dict):
            raise EvaluationFixtureError(f"{case_id}: request must be an object")
        if not boss_fixture_id:
            raise EvaluationFixtureError(f"{case_id}: boss_fixture_id is required")
        if witness is not None and not isinstance(witness, dict):
            raise EvaluationFixtureError(f"{case_id}: witness must be an object")
        if certificate is not None and not isinstance(certificate, dict):
            raise EvaluationFixtureError(f"{case_id}: impossibility_certificate must be an object")
        return cls(
            case_id=case_id,
            suite=suite,
            expected_outcome=expected,
            request=dict(request),
            boss_fixture_id=boss_fixture_id,
            witness=dict(witness) if witness else None,
            impossibility_certificate=dict(certificate) if certificate else None,
            data_complete=bool(value.get("data_complete", True)),
            source_authority=str(value.get("source_authority") or ""),
        )


def load_evaluation_fixture(path: str | Path) -> dict[str, Any]:
    """Load and validate a JSON fixture without executing production code."""
    fixture_path = Path(path)
    try:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationFixtureError(f"Unable to load evaluation fixture {fixture_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise EvaluationFixtureError("Evaluation fixture must be a JSON object")
    validate_evaluation_fixture(raw)
    return raw


def load_evaluation_cases(path: str | Path) -> list[EvaluationCase]:
    """Load the ordered cases from a validated H fixture."""
    raw = load_evaluation_fixture(path)
    return [EvaluationCase.from_mapping(item) for item in raw["cases"]]


def validate_evaluation_fixture(
    fixture: Mapping[str, Any],
    *,
    require_h03_counts: bool = True,
) -> list[EvaluationCase]:
    """Validate fixture shape, oracle separation, and evidence declarations."""
    version = str(fixture.get("fixture_version") or "")
    if not version:
        raise EvaluationFixtureError("fixture_version is required")
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise EvaluationFixtureError("cases must be a list")
    policy_versions = fixture.get("policy_versions")
    if not isinstance(policy_versions, dict):
        raise EvaluationFixtureError("policy_versions must declare H-08 source versions")
    missing_versions = [field for field in REQUIRED_POLICY_VERSION_FIELDS if not str(policy_versions.get(field) or "").strip()]
    if missing_versions:
        raise EvaluationFixtureError("Missing policy versions: " + ", ".join(missing_versions))

    parsed: list[EvaluationCase] = []
    seen: set[str] = set()
    for item in cases:
        if not isinstance(item, dict):
            raise EvaluationFixtureError("Every evaluation case must be an object")
        case = EvaluationCase.from_mapping(item)
        if case.case_id in seen:
            raise EvaluationFixtureError(f"Duplicate evaluation case ID: {case.case_id}")
        seen.add(case.case_id)
        _validate_case_contract(case)
        parsed.append(case)

    feasible = [case for case in parsed if case.suite == "boss_acceptance" and case.expected_outcome == "feasible"]
    infeasible = [case for case in parsed if case.suite == "boss_acceptance" and case.expected_outcome == "infeasible"]
    stress = [case for case in parsed if case.suite == "fixed_roster_stress"]
    if require_h03_counts and (len(feasible) != H03_FEASIBLE_COUNT or len(infeasible) != H03_INFEASIBLE_COUNT):
        raise EvaluationFixtureError(
            f"H-03 requires {H03_FEASIBLE_COUNT} feasible and {H03_INFEASIBLE_COUNT} infeasible boss cases; "
            f"found {len(feasible)} and {len(infeasible)}"
        )
    if require_h03_counts and not stress:
        raise EvaluationFixtureError("The fixed-roster stress suite must remain separate from H-03")
    return parsed


async def run_h03_evaluation(
    source: str | Path | Mapping[str, Any] | Sequence[EvaluationCase],
    retrieval_service: Any,
) -> dict[str, Any]:
    """Run boss acceptance cases before the analyzer and report typed results.

    ``retrieval_service`` may be a ``ProductionRetrievalService`` or an async
    callable accepting a ``ProductionRecommendationRequest``.  The callable
    is intentionally limited to retrieval so the report can prove the
    analyzer-call count is zero for H-03.
    """
    fixture, cases = _normalise_source(source)
    validate_evaluation_fixture(
        fixture,
        require_h03_counts=not isinstance(source, Sequence) or isinstance(source, (str, bytes, bytearray)),
    )
    case_reports: list[dict[str, Any]] = []
    for case in cases:
        case_reports.append(await _run_case(case, retrieval_service))

    boss_cases = [item for item in case_reports if item["suite"] == "boss_acceptance"]
    feasible = [item for item in boss_cases if item["expected_outcome"] == "feasible"]
    infeasible = [item for item in boss_cases if item["expected_outcome"] == "infeasible"]
    stress = [item for item in case_reports if item["suite"] == "fixed_roster_stress"]
    return {
        "evaluation_version": EVALUATION_POLICY_VERSION,
        "fixture_version": fixture.get("fixture_version"),
        "policy_versions": dict(fixture.get("policy_versions") or {}),
        "h03": {
            "feasible": _suite_summary(feasible, H03_FEASIBLE_COUNT),
            "infeasible": _suite_summary(infeasible, H03_INFEASIBLE_COUNT),
            "ready": (
                len(feasible) == H03_FEASIBLE_COUNT
                and len(infeasible) == H03_INFEASIBLE_COUNT
                and all(item["passed"] for item in [*feasible, *infeasible])
            ),
            "analyzer_call_count": sum(item["analyzer_call_count"] for item in boss_cases),
        },
        "stress_suite": _suite_summary(stress, len(stress)),
        "cases": case_reports,
    }


async def evaluate_feature_h(
    source: str | Path | Mapping[str, Any] | Sequence[EvaluationCase],
    retrieval_service: Any,
) -> dict[str, Any]:
    """Compatibility entry point for the deterministic H evaluation."""
    return await run_h03_evaluation(source, retrieval_service)


def load_qualification_fixture(path: str | Path) -> dict[str, Any]:
    """Load the small, provider-neutral progressive qualification register."""
    fixture_path = Path(path)
    try:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationFixtureError(f"Unable to load qualification fixture {fixture_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise EvaluationFixtureError("Qualification fixture must be a JSON object")
    validate_qualification_fixture(raw)
    return raw


def validate_qualification_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Validate stage order and fixture outputs with the application authority."""
    if fixture.get("fixture_version") != QUALIFICATION_FIXTURE_VERSION:
        raise EvaluationFixtureError("Unsupported qualification fixture version")
    projection = fixture.get("projection")
    if not isinstance(projection, dict):
        raise EvaluationFixtureError("Qualification fixture projection must be an object")
    candidate_ids = projection.get("candidate_ids")
    if (
        not isinstance(candidate_ids, list)
        or not candidate_ids
        or any(not isinstance(value, str) or not value for value in candidate_ids)
        or len(set(candidate_ids)) != len(candidate_ids)
    ):
        raise EvaluationFixtureError("Qualification projection candidate_ids must be unique non-empty strings")
    candidates = projection.get("candidates")
    candidate_records = {
        str(item.get("id")): item
        for item in candidates or []
        if isinstance(item, dict) and item.get("id")
    }
    if set(candidate_ids) != set(candidate_records):
        raise EvaluationFixtureError("Qualification projection candidates must match candidate_ids")
    allowed_swaps = projection.get("allowed_swaps", [])
    if not isinstance(allowed_swaps, list):
        raise EvaluationFixtureError("Qualification projection allowed_swaps must be a list")
    for item in allowed_swaps:
        if (
            not isinstance(item, dict)
            or item.get("candidate_id") not in candidate_ids
            or not isinstance(item.get("slot"), str)
            or not isinstance(item.get("alternative_character_id"), str)
            or not item.get("alternative_character_id")
        ):
            raise EvaluationFixtureError("Every qualification swap must be backend-authorized and bounded")

    stages = fixture.get("stages")
    if not isinstance(stages, list) or [item.get("stage") for item in stages if isinstance(item, dict)] != list(QUALIFICATION_STAGES):
        raise EvaluationFixtureError("Qualification stages must follow the progressive stage order")
    seen_ids: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise EvaluationFixtureError("Every qualification stage must be an object")
        stage_id = str(stage.get("stage_id") or "")
        if not stage_id or stage_id in seen_ids:
            raise EvaluationFixtureError("Qualification stage IDs must be present and unique")
        seen_ids.add(stage_id)
        if not isinstance(stage.get("request"), dict) or not isinstance(stage.get("response"), dict):
            raise EvaluationFixtureError(f"{stage_id}: request and response must be objects")
        _validate_qualification_response(stage["response"], stage["stage"], projection, stage_id)
        if stage["stage"] == "correction_recovery":
            initial = stage.get("initial_response")
            if not isinstance(initial, dict):
                raise EvaluationFixtureError(f"{stage_id}: correction stage requires initial_response")
            _, _, initial_errors = validate_analyzer_output(initial, projection)
            if not initial_errors:
                raise EvaluationFixtureError(f"{stage_id}: initial_response must exercise application correction")
    return dict(fixture)


def build_qualification_request(
    projection: Mapping[str, Any],
    stage: Mapping[str, Any],
    config: AnalyzerProviderConfig,
    *,
    call_kind: str = "initial",
    invalid_fragments: list[dict[str, Any]] | None = None,
) -> AnalyzerProviderRequest:
    """Build a stage request with dynamic closed-world response constraints."""
    stage_name = str(stage.get("stage") or "")
    stage_id = str(stage.get("stage_id") or "qualification")
    if call_kind == "correction":
        content = correction_payload(dict(projection), invalid_fragments or [], [])
        content["qualification_stage"] = stage_id
        content["request"] = dict(stage.get("request") or {})
    else:
        content = {
            "qualification_stage": stage_id,
            "request": dict(stage.get("request") or {}),
            "projection": dict(projection),
        }
    return AnalyzerProviderRequest(
        provider=config.provider,
        model=config.resolved_model,
        call_kind=call_kind,
        messages=[
            {
                "role": "system",
                "content": "Return only the qualification JSON schema. Backend IDs and authorized swaps are closed-world and read-only.",
            },
            {"role": "user", "content": json.dumps(content, ensure_ascii=False, separators=(",", ":"))},
        ],
        projection_id=f"{projection.get('projection_id', 'projection:qualification')}:{stage_id}",
        max_output_tokens=min(
            config.initial_max_output_tokens if call_kind == "initial" else config.correction_max_output_tokens,
            config.per_call_token_budget,
        ),
        response_schema=build_request_specific_response_schema(dict(projection), stage=stage_name),
    )


def run_qualification_suite(
    source: str | Path | Mapping[str, Any],
    transport: Callable[[AnalyzerProviderRequest], Any],
    *,
    provider: str = "openrouter",
    model: str = "qualification-model",
) -> dict[str, Any]:
    """Run every progressive qualification stage through one injected port."""
    fixture = load_qualification_fixture(source) if isinstance(source, (str, Path)) else dict(source)
    validate_qualification_fixture(fixture)
    projection = dict(fixture["projection"])
    config = AnalyzerProviderConfig(provider=provider, model=model)
    port = create_analyzer_port(config, transport)
    stage_reports: list[dict[str, Any]] = []
    total_tokens = 0
    for stage in fixture["stages"]:
        stage_id = stage["stage_id"]
        if total_tokens >= config.cumulative_token_budget:
            stage_reports.append({
                "stage_id": stage_id,
                "stage": stage["stage"],
                "passed": False,
                "call_count": 0,
                "correction_used": False,
                "application_validation_errors": [{"code": "qualification.cumulative_budget"}],
                "provider_errors": [],
                "diagnostics": [],
                "schema_candidate_ids": sorted(projection["candidate_ids"]),
                "schema_allowed_swap_count": len(projection.get("allowed_swaps", [])),
            })
            continue
        diagnostics: list[dict[str, Any]] = []
        application_errors: list[dict[str, Any]] = []
        provider_errors: list[dict[str, Any]] = []
        calls_before = len(port.requests)

        initial_response = port.generate(build_qualification_request(projection, stage, config))
        initial_errors, initial_provider_errors = _qualification_response_errors(
            initial_response,
            stage,
            projection,
        )
        provider_errors.extend(initial_provider_errors)
        initial_tokens = _usage_tokens(initial_response.usage)
        total_tokens += initial_tokens
        diagnostics.append(
            build_provider_diagnostic(
                initial_response,
                len(port.requests),
                "initial",
                projection,
                validation_errors=initial_errors,
            )
        )

        final_response = initial_response
        correction_used = False
        if stage["stage"] == "correction_recovery":
            if initial_response.output is not None and initial_errors and not initial_response.error:
                correction_budget = min(config.correction_max_output_tokens, config.per_call_token_budget)
                if len(port.requests) - calls_before >= ANALYZER_MAX_CALLS:
                    application_errors.append({"code": "qualification.correction_cap"})
                elif total_tokens + correction_budget > config.cumulative_token_budget:
                    application_errors.append({"code": "qualification.cumulative_budget"})
                else:
                    correction_used = True
                    correction_request = build_qualification_request(
                        projection,
                        stage,
                        config,
                        call_kind="correction",
                        invalid_fragments=[{"fragment": initial_response.output, "errors": initial_errors}],
                    )
                    final_response = port.generate(correction_request)
                    correction_errors, correction_provider_errors = _qualification_response_errors(
                        final_response,
                        stage,
                        projection,
                    )
                    application_errors.extend(correction_errors)
                    provider_errors.extend(correction_provider_errors)
                    total_tokens += _usage_tokens(final_response.usage)
                    diagnostics.append(
                        build_provider_diagnostic(
                            final_response,
                            len(port.requests),
                            "correction",
                            projection,
                            validation_errors=correction_errors,
                        )
                    )
            else:
                application_errors.append({"code": "qualification.correction_not_exercised"})
        else:
            application_errors.extend(initial_errors)

        application_errors.extend(_qualification_budget_errors(initial_response, config, cumulative_tokens=0))
        if final_response is not initial_response:
            application_errors.extend(
                _qualification_budget_errors(
                    final_response,
                    config,
                    cumulative_tokens=initial_tokens,
                )
            )
        stage_reports.append({
            "stage_id": stage_id,
            "stage": stage["stage"],
            "passed": not application_errors and not provider_errors and correction_used is (stage["stage"] == "correction_recovery"),
            "call_count": len(port.requests) - calls_before,
            "correction_used": correction_used,
            "application_validation_errors": application_errors,
            "provider_errors": provider_errors,
            "diagnostics": diagnostics,
            "schema_candidate_ids": sorted(projection["candidate_ids"]),
            "schema_allowed_swap_count": len(projection.get("allowed_swaps", [])),
        })
    return {
        "evaluation_version": EVALUATION_POLICY_VERSION,
        "qualification_fixture_version": fixture["fixture_version"],
        "provider": provider,
        "model": model,
        "fallback_enabled": False,
        "analyzer_call_count": len(port.requests),
        "total_tokens": total_tokens,
        "within_cumulative_budget": total_tokens <= config.cumulative_token_budget,
        "stages": stage_reports,
        "all_passed": bool(stage_reports) and all(item["passed"] for item in stage_reports),
    }


def _validate_qualification_response(output, stage, projection, stage_id):
    _, _, errors = validate_analyzer_output(output, projection)
    errors = [*errors, *_qualification_shape_errors(output, stage)]
    if errors:
        raise EvaluationFixtureError(
            f"{stage_id}: response is not a valid {stage} qualification output: {errors[0].get('code')}"
        )


def _qualification_response_errors(response, stage, projection):
    if response.error or response.output is None:
        return [], [{"code": (response.error or {}).get("code", "provider.empty_response")}]
    _, _, validation_errors = validate_analyzer_output(response.output, projection)
    return [*validation_errors, *_qualification_shape_errors(response.output, stage["stage"])], []


def _qualification_shape_errors(output, stage):
    errors: list[dict[str, Any]] = []
    if not isinstance(output, dict):
        return [{"code": "qualification.shape.object"}]
    missing = sorted({"ranked_candidate_ids", "refinements", "advisories"} - set(output))
    errors.extend({"code": "qualification.shape.missing_field", "field": field} for field in missing)
    if stage == "ranking_only" and (output.get("refinements") != [] or output.get("advisories") != []):
        errors.append({"code": "qualification.ranking_only_shape"})
    if stage == "ranking_refinement_no_swap":
        if not output.get("refinements") or any(
            item.get("swap") is not None for item in output["refinements"] if isinstance(item, dict)
        ):
            errors.append({"code": "qualification.refinement_swap_present"})
    if stage == "authorized_swap":
        if not output.get("refinements") or not any(
            item.get("swap") is not None for item in output["refinements"] if isinstance(item, dict)
        ):
            errors.append({"code": "qualification.authorized_swap_missing"})
    if stage == "swap_abstention" and any(
        item.get("swap") is not None for item in output.get("refinements", []) if isinstance(item, dict)
    ):
        errors.append({"code": "qualification.swap_abstention_failed"})
    return errors


def _qualification_budget_errors(response, config, *, cumulative_tokens):
    observed = _usage_tokens(response.usage)
    errors = []
    if observed > config.per_call_token_budget:
        errors.append({"code": "qualification.per_call_budget"})
    if cumulative_tokens + observed > config.cumulative_token_budget:
        errors.append({"code": "qualification.cumulative_budget"})
    return errors


def qualify_openrouter_models(
    bundle: Mapping[str, Any],
    transport: Callable[[AnalyzerProviderRequest], Any],
    *,
    models: Iterable[str] = OPENROUTER_MODEL_CHAIN,
    qualification_fixture: str | Path | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Qualify each OpenRouter model independently against one strict fixture.

    This function never supplies a fallback array.  A caller must run this
    gate for every model before calling ``build_openrouter_fallback_config``.
    """
    projection = build_compact_projection(dict(bundle))
    requested_models = tuple(str(model).strip() for model in models if str(model).strip())
    results: list[dict[str, Any]] = []
    for model in requested_models:
        if qualification_fixture is not None:
            qualification = run_qualification_suite(
                qualification_fixture,
                transport,
                provider="openrouter",
                model=model,
            )
            results.append({
                "model": model,
                "passed": qualification["all_passed"],
                "strict_output": qualification["all_passed"],
                "authority_valid": not any(
                    stage["provider_errors"] or any(
                        str(error.get("code", "")).startswith("authority.")
                        for error in stage["application_validation_errors"]
                    )
                    for stage in qualification["stages"]
                ),
                "served_model": None,
                "served_model_status": "reported_in_stage_diagnostics" if qualification["all_passed"] else "unavailable",
                "fallback": None,
                "usage": {"total_tokens": qualification["total_tokens"]},
                "metadata_availability": {"qualification": "reported"},
                "qualification": qualification,
                "errors": [
                    error
                    for stage in qualification["stages"]
                    for error in [*stage["application_validation_errors"], *stage["provider_errors"]]
                ],
            })
            continue
        config = AnalyzerProviderConfig(provider="openrouter", model=model)
        port = create_analyzer_port(config, transport)
        request = AnalyzerProviderRequest(
            provider="openrouter",
            model=model,
            call_kind="initial",
            messages=[
                {"role": "system", "content": "Return only the strict analyzer JSON schema."},
                {"role": "user", "content": json.dumps({"projection": projection}, separators=(",", ":"))},
            ],
            projection_id=projection["projection_id"],
            max_output_tokens=config.initial_max_output_tokens,
            response_schema=build_request_specific_response_schema(projection, stage="full_contract"),
        )
        response = port.generate(request)
        valid, invalid, errors = validate_analyzer_output(response.output, projection) if response.output is not None else ([], [], [])
        application_errors = list(errors)
        if response.error:
            errors = [*application_errors, {"code": response.error.get("code", "provider.error"), "message": response.error.get("message", "Provider error")}]
        diagnostic = build_provider_diagnostic(response, 1, "initial", projection, validation_errors=application_errors)
        metadata = _metadata_availability(response.usage, response.served_model)
        results.append({
            "model": model,
            "passed": not bool(response.error or errors) and bool(valid or response.output and response.output.get("ranked_candidate_ids")),
            "strict_output": not bool(invalid) and response.output is not None,
            "authority_valid": not any(str(error.get("code", "")).startswith("authority.") for error in errors),
            "served_model": response.served_model,
            "served_model_status": "reported" if response.served_model else "unavailable",
            "fallback": response.fallback,
            "usage": dict(response.usage),
            "metadata_availability": metadata,
            "diagnostics": [diagnostic],
            "errors": errors,
        })
    return {
        "evaluation_version": EVALUATION_POLICY_VERSION,
        "provider": "openrouter",
        "models": results,
        "all_passed": len(results) == len(requested_models) and all(item["passed"] for item in results),
        "fallback_enabled": False,
    }


def build_openrouter_fallback_config(qualification: Mapping[str, Any]) -> AnalyzerProviderConfig:
    """Enable the server-managed ordered chain only after individual gates pass."""
    if qualification.get("provider") != "openrouter" or qualification.get("all_passed") is not True:
        raise EvaluationFixtureError("OpenRouter fallback requires all individual model gates to pass")
    qualified = tuple(str(item.get("model")) for item in qualification.get("models", []) if item.get("passed"))
    if qualified != OPENROUTER_MODEL_CHAIN:
        raise EvaluationFixtureError("Qualified model order must equal the approved OpenRouter chain")
    return AnalyzerProviderConfig(
        provider="openrouter",
        model=qualified[0],
        fallback_models=qualified[1:],
    )


def summarize_analyzer_usage(
    usage_rows: Iterable[Mapping[str, Any]],
    *,
    cumulative_budget: int = ANALYZER_CUMULATIVE_TOKEN_BUDGET,
    baseline_tokens: int = HISTORICAL_BASELINE_TOKENS,
) -> dict[str, Any]:
    """Summarize observed provider usage without inventing unavailable fields."""
    rows = [dict(row) for row in usage_rows]
    total_tokens = sum(_usage_tokens(row) for row in rows)
    known_costs = [_number(row.get("cost")) for row in rows if row.get("cost") is not None]
    cost_available = bool(known_costs)
    cost = round(sum(known_costs), 8) if cost_available else None
    reduction = max(0.0, 1.0 - (total_tokens / baseline_tokens)) if baseline_tokens else None
    return {
        "attempt_count": len(rows),
        "total_tokens": total_tokens,
        "cumulative_budget": cumulative_budget,
        "within_cumulative_budget": total_tokens <= cumulative_budget,
        "cost": cost,
        "cost_status": "reported" if cost_available else "unavailable",
        "baseline_tokens": baseline_tokens,
        "baseline_reduction": reduction,
        "baseline_reduction_ge_90_percent": reduction is not None and reduction >= 0.90,
        "attempts": rows,
    }


def classify_analyzer_run(result: Mapping[str, Any]) -> dict[str, Any]:
    """Classify analyzer outcomes for H-06 without collapsing failure causes."""
    categories: set[str] = set()
    analysis_failure = result.get("analysis_failure") or {}
    failure_type = str(analysis_failure.get("type") or "")
    if failure_type in {"no_backend_candidates", "backend_failure", "backend_projection_render_failed"}:
        categories.add("backend_failure")
    if result.get("structured_output_errors"):
        categories.add("analyzer_structure_failure")
    if result.get("candidate_validation_errors"):
        categories.add("local_validation_failure")
        categories.add("analyzer_refinement_failure")
    usage_rows = [row for row in result.get("analyzer_usage", []) if isinstance(row, Mapping)]
    if any(str(row.get("error_code") or "").startswith("provider.") for row in usage_rows):
        categories.add("openrouter_transport_failure" if any(row.get("provider") == "openrouter" for row in usage_rows) else "provider_transport_failure")
    if any(_fallback_was_used(row) for row in usage_rows):
        categories.add("model_provider_fallback")
    if any("budget" in str(warning).casefold() for warning in result.get("warnings", [])):
        categories.add("budget_degradation")
    if result.get("degraded") or failure_type == "analyzer_degraded":
        categories.add("readiness_degraded")
    return {
        "categories": sorted(categories),
        "backend_failure": "backend_failure" in categories,
        "ready_for_later_human_review": not bool(categories.intersection({"backend_failure", "openrouter_transport_failure", "provider_transport_failure"})),
    }


summarize_analyzer_run = classify_analyzer_run


def _normalise_source(source):
    if isinstance(source, (str, Path)):
        fixture = load_evaluation_fixture(source)
        return fixture, [EvaluationCase.from_mapping(item) for item in fixture["cases"]]
    if isinstance(source, Mapping):
        fixture = dict(source)
        return fixture, [EvaluationCase.from_mapping(item) for item in fixture.get("cases", [])]
    cases = list(source)
    return _synthetic_fixture_for_cases(cases), cases


def _synthetic_fixture_for_cases(cases):
    """Build an explicit non-H03 wrapper for small unit tests."""
    return {
        "fixture_version": REQUEST_FIXTURE_VERSION,
        "policy_versions": {field: "unit-test" for field in REQUIRED_POLICY_VERSION_FIELDS},
        "cases": [
            {
                "case_id": case.case_id,
                "suite": case.suite,
                "expected_outcome": case.expected_outcome,
                "request": case.request,
                "boss_fixture_id": case.boss_fixture_id,
                "witness": case.witness,
                "impossibility_certificate": case.impossibility_certificate,
                "data_complete": case.data_complete,
            }
            for case in cases
        ],
    }


async def _run_case(case: EvaluationCase, retrieval_service: Any) -> dict[str, Any]:
    report = {
        "case_id": case.case_id,
        "suite": case.suite,
        "expected_outcome": case.expected_outcome,
        "boss_fixture_id": case.boss_fixture_id,
        "passed": False,
        "failure_codes": [],
        "analyzer_call_count": 0,
        "observed_status": None,
        "observed_candidate_count": 0,
        "diagnostics": {},
    }
    try:
        request = validate_production_request(case.request)
    except ProductionRequestError as exc:
        report["failure_codes"] = ["fixture.invalid_request", *[issue.code for issue in exc.issues]]
        return report
    if case.suite == "boss_acceptance" and len(request.roster) < 6:
        report["failure_codes"] = ["fixture.roster_too_small"]
        return report
    try:
        result = getattr(retrieval_service, "retrieve", retrieval_service)(request)
        if inspect.isawaitable(result):
            result = await result
    except ProductionRequestError as exc:
        report["failure_codes"] = ["retrieval.request_error", *[issue.code for issue in exc.issues]]
        return report
    except Exception as exc:  # noqa: BLE001 - report unexpected fixture/product errors
        report["failure_codes"] = ["retrieval.unexpected_error", type(exc).__name__]
        return report

    payload = result.model_dump() if hasattr(result, "model_dump") else dict(result or {})
    generation = payload.get("lineup_candidates") or payload.get("candidate_generation") or {}
    candidates = list(generation.get("candidates") or []) if isinstance(generation, dict) else []
    coverage = payload.get("coverage") or {}
    diagnostics = generation.get("diagnostics") or {} if isinstance(generation, dict) else {}
    readiness = diagnostics.get("readiness") or {}
    report.update({
        "observed_status": generation.get("status") if isinstance(generation, dict) else None,
        "observed_candidate_count": len(candidates),
        "diagnostics": diagnostics,
        "coverage_complete": bool(coverage.get("complete", False)),
        "authoritative_infeasible": bool(readiness.get("authoritative_infeasible", False)),
        "analyzer_call_count": int(payload.get("analyzer_call_count", 0) or 0),
        "policy_versions": _observed_policy_versions(payload),
    })

    if report["analyzer_call_count"]:
        report["failure_codes"].append("h03.analyzer_called_before_backend_oracle")
    if case.suite == "fixed_roster_stress":
        report["passed"] = not report["failure_codes"]
        return report
    if not case.data_complete or not report["coverage_complete"]:
        report["failure_codes"].append("fixture.incomplete_data_not_strategic_oracle")
        return report
    if case.expected_outcome == "feasible":
        legal = [candidate for candidate in candidates if _candidate_is_legal(candidate)]
        if not legal:
            report["failure_codes"].append("h03.missing_legal_backend_candidate")
        elif not _witness_matches(case.witness, legal):
            report["failure_codes"].append("h03.independent_witness_not_replayed")
        else:
            report["passed"] = not report["failure_codes"]
    elif case.expected_outcome == "infeasible":
        if candidates:
            report["failure_codes"].append("h03.unexpected_backend_candidate")
        if not report["authoritative_infeasible"]:
            report["failure_codes"].append("h03.non_authoritative_infeasibility")
        if not _certificate_matches(case.impossibility_certificate, generation):
            report["failure_codes"].append("h03.impossibility_certificate_mismatch")
        else:
            report["passed"] = not report["failure_codes"]
    else:
        report["failure_codes"].append("fixture.invalid_boss_acceptance_outcome")
    return report


def _validate_case_contract(case: EvaluationCase) -> None:
    if case.suite not in {"boss_acceptance", "fixed_roster_stress"}:
        raise EvaluationFixtureError(f"{case.case_id}: unsupported suite {case.suite}")
    if not case.request.get("boss_id") or not isinstance(case.request.get("roster"), list):
        raise EvaluationFixtureError(f"{case.case_id}: typed boss request is incomplete")
    if case.suite == "boss_acceptance":
        if len(case.request["roster"]) < 6:
            raise EvaluationFixtureError(f"{case.case_id}: strategic cases require at least six requested heroes")
        if not case.data_complete:
            raise EvaluationFixtureError(f"{case.case_id}: strategic oracle cases must declare complete data")
        if case.expected_outcome == "feasible":
            witness = case.witness or {}
            character_ids = witness.get("character_ids") or witness.get("hero_ids")
            if not isinstance(character_ids, list) or len(character_ids) != 6 or len(set(character_ids)) != 6:
                raise EvaluationFixtureError(f"{case.case_id}: feasible case needs an independent six-hero witness")
            for field in ("candidate_id", "package_fingerprint", "coverage_roles", "allocation_fingerprint"):
                if not witness.get(field):
                    raise EvaluationFixtureError(f"{case.case_id}: witness is missing {field}")
            if not isinstance(witness.get("coverage_roles"), list) or not witness["coverage_roles"]:
                raise EvaluationFixtureError(f"{case.case_id}: witness coverage_roles must be a non-empty list")
        elif case.expected_outcome == "infeasible":
            certificate = case.impossibility_certificate or {}
            if not certificate.get("proof_id") or not certificate.get("zero_candidate_causes"):
                raise EvaluationFixtureError(f"{case.case_id}: infeasible case needs a deterministic certificate")


def _candidate_is_legal(candidate: Mapping[str, Any]) -> bool:
    character_ids = list(candidate.get("character_ids") or [])
    coverage = candidate.get("coverage") or {}
    validation = candidate.get("validation") or {}
    allocation = candidate.get("build_allocation") or {}
    allocation_search = candidate.get("allocation_search") or {}
    return (
        len(character_ids) == 6
        and len(set(character_ids)) == 6
        and validation.get("valid") is True
        and validation.get("build_allocation") == "validated"
        and not coverage.get("missing")
        and allocation_search.get("exhausted") is not True
        and isinstance(allocation, dict)
        and allocation.get("scope") == "lineup"
    )


def _witness_matches(witness: Mapping[str, Any] | None, candidates: Sequence[Mapping[str, Any]]) -> bool:
    if not isinstance(witness, Mapping):
        return False
    witness_ids = {str(value) for value in witness.get("character_ids", witness.get("hero_ids", []))}
    if len(witness_ids) != 6:
        return False
    expected_candidate_id = witness.get("candidate_id")
    expected_roles = {str(value) for value in witness.get("coverage_roles", []) if value}
    expected_package = str(witness.get("package_fingerprint") or "")
    expected_allocation = str(witness.get("allocation_fingerprint") or "")
    for candidate in candidates:
        if expected_candidate_id and candidate.get("id") != expected_candidate_id:
            continue
        if set(map(str, candidate.get("character_ids", []))) != witness_ids:
            continue
        if expected_package and expected_package != _candidate_package_fingerprint(candidate):
            continue
        if expected_allocation and expected_allocation != _candidate_allocation_fingerprint(candidate):
            continue
        if expected_roles and not expected_roles.issubset(_candidate_coverage_roles(candidate)):
            continue
        return True
    return False


def _candidate_package_fingerprint(candidate: Mapping[str, Any]) -> str:
    selected = candidate.get("selected_skill_package_ids")
    if not isinstance(selected, Mapping):
        selected = candidate.get("skill_package_ids")
    return _fingerprint(selected or {})


def _candidate_allocation_fingerprint(candidate: Mapping[str, Any]) -> str:
    return _fingerprint(candidate.get("build_allocation") or {})


def _candidate_coverage_roles(candidate: Mapping[str, Any]) -> set[str]:
    coverage = candidate.get("coverage") or {}
    roles = {str(value) for value in coverage.get("covered_roles", []) if value}
    if roles.intersection({"defense_mitigation", "recovery_protection", "tank_control"}):
        roles.add("survival")
    return roles


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _certificate_matches(certificate: Mapping[str, Any] | None, generation: Mapping[str, Any]) -> bool:
    if not isinstance(certificate, Mapping):
        return False
    diagnostics = generation.get("diagnostics") or {}
    actual_causes = set(str(value) for value in diagnostics.get("zero_candidate_causes", []))
    actual_counts = set(str(value) for value in (diagnostics.get("rejection_counts") or {}))
    expected_causes = set(str(value) for value in certificate.get("zero_candidate_causes", []))
    if expected_causes and not expected_causes.intersection(actual_causes | actual_counts):
        return False
    expected_stage = certificate.get("stage")
    if expected_stage:
        stages = diagnostics.get("stage_diagnostics") or {}
        if expected_stage not in stages:
            return False
    return bool(certificate.get("proof_id"))


def _suite_summary(rows: Sequence[Mapping[str, Any]], expected_count: int) -> dict[str, Any]:
    return {
        "expected_count": expected_count,
        "observed_count": len(rows),
        "passed_count": sum(1 for row in rows if row.get("passed")),
        "failed_case_ids": [row.get("case_id") for row in rows if not row.get("passed")],
        "ready": len(rows) == expected_count and all(row.get("passed") for row in rows),
    }


def _observed_policy_versions(payload: Mapping[str, Any]) -> dict[str, Any]:
    role_scores = payload.get("role_scores") or {}
    generation = payload.get("lineup_candidates") or {}
    return {
        "role_scoring": role_scores.get("policy_version"),
        "skill_package": role_scores.get("skill_package_policy_version"),
        "search": generation.get("policy_version") if isinstance(generation, dict) else None,
        "build_packages": next(
            (
                (row.get("build_package") or {}).get("version")
                for row in payload.get("characters", [])
                if isinstance(row, dict) and (row.get("build_package") or {}).get("version")
            ),
            None,
        ),
    }


def _usage_tokens(row: Mapping[str, Any]) -> int:
    value = row.get("total_tokens")
    if value is None:
        value = sum(_number(row.get(key)) for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"))
    return max(0, int(_number(value)))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _metadata_availability(usage: Mapping[str, Any], served_model: str | None) -> dict[str, str]:
    return {
        field: "reported" if field in usage else "unavailable"
        for field in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "cached_tokens", "total_tokens", "cost", "latency_ms", "generation_id")
    } | {"actual_model": "reported" if served_model else "unavailable"}


def _fallback_was_used(row: Mapping[str, Any]) -> bool:
    value = row.get("fallback")
    if value is True:
        return True
    return isinstance(value, Mapping) and value.get("used") is True


__all__ = [
    "EVALUATION_POLICY_VERSION",
    "EvaluationCase",
    "EvaluationFixtureError",
    "QUALIFICATION_FIXTURE_VERSION",
    "build_qualification_request",
    "build_openrouter_fallback_config",
    "classify_analyzer_run",
    "evaluate_feature_h",
    "load_evaluation_cases",
    "load_evaluation_fixture",
    "load_qualification_fixture",
    "qualify_openrouter_models",
    "run_qualification_suite",
    "run_h03_evaluation",
    "summarize_analyzer_usage",
    "summarize_analyzer_run",
    "validate_qualification_fixture",
    "validate_evaluation_fixture",
]
