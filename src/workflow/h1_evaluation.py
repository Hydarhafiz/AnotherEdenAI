"""Opt-in Feature H1 comparison of bounded analyzer reasoning settings.

H1 prepares a production candidate bundle once, projects only the bounded
backend candidates, and runs that same projection through two independent
OpenRouter configurations. The live transport is deliberately supplied by
the caller so importing this module and running its tests cannot make a paid
request.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .analyzer import (
    ANALYZER_CUMULATIVE_TOKEN_BUDGET,
    ANALYZER_MAX_CALLS,
    ANALYZER_PER_CALL_TOKEN_BUDGET,
    AnalyzerProviderConfig,
    AnalyzerProviderRequest,
    build_compact_projection,
    create_analyzer_port,
    run_bounded_analyzer,
)
from .candidates import prepare_candidates_node
from .production import ProductionRequestError, validate_production_request


H1_EVALUATION_VERSION = "feature-h1-evaluation-v1"
H1_MODEL = "deepseek/deepseek-v4-flash-0731"
H1_MAX_SCENARIOS = 8


@dataclass(frozen=True)
class H1AnalyzerVariant:
    """One explicitly named comparison arm; no fallback is permitted."""

    variant_id: str
    reasoning_effort: str
    max_output_tokens: int

    def config(self) -> AnalyzerProviderConfig:
        return AnalyzerProviderConfig(
            provider="openrouter",
            model=H1_MODEL,
            initial_max_output_tokens=self.max_output_tokens,
            correction_max_output_tokens=2_000,
            reasoning_effort=self.reasoning_effort,
            fallback_models=(),
            per_call_token_budget=ANALYZER_PER_CALL_TOKEN_BUDGET,
            cumulative_token_budget=ANALYZER_CUMULATIVE_TOKEN_BUDGET,
        )


H1_VARIANTS = (
    H1AnalyzerVariant("baseline_a", "none", 4_000),
    H1AnalyzerVariant("variant_b", "low", 8_000),
)


@dataclass(frozen=True)
class H1Scenario:
    scenario_id: str
    request: dict[str, Any]
    category: str = "unclassified"
    selection_note: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "H1Scenario":
        scenario_id = str(value.get("scenario_id") or value.get("case_id") or value.get("id") or "").strip()
        request = value.get("request")
        if not scenario_id or not isinstance(request, dict):
            raise ValueError("H1 scenarios require a non-empty scenario_id and request object")
        return cls(
            scenario_id=scenario_id,
            request=dict(request),
            category=str(value.get("category") or "unclassified"),
            selection_note=str(value.get("selection_note") or ""),
        )


def load_h1_scenarios(path: str | Path, *, scenario_ids: Iterable[str] | None = None) -> list[H1Scenario]:
    """Load a small scenario manifest or select cases from the H fixture."""
    source_path = Path(path)
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load H1 scenario source {source_path}: {exc}") from exc
    if isinstance(raw, dict):
        rows = raw.get("scenarios")
        if rows is None:
            rows = raw.get("cases")
    else:
        rows = raw
    if not isinstance(rows, list):
        raise ValueError("H1 scenario source must contain a scenarios or cases list")

    requested = [str(value).strip() for value in (scenario_ids or ()) if str(value).strip()]
    available = {
        str(item.get("scenario_id") or item.get("case_id") or item.get("id")): item
        for item in rows
        if isinstance(item, dict)
    }
    if requested:
        missing = [value for value in requested if value not in available]
        if missing:
            raise ValueError("Unknown H1 scenario IDs: " + ", ".join(missing))
        rows = [available[value] for value in requested]
    if not rows or len(rows) > H1_MAX_SCENARIOS:
        raise ValueError(f"H1 requires one to {H1_MAX_SCENARIOS} selected scenarios")
    return [H1Scenario.from_mapping(row) for row in rows]


async def prepare_h1_scenario(scenario: H1Scenario, retrieval_service: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run typed production retrieval and candidate preparation once."""
    request = validate_production_request(scenario.request)
    result = getattr(retrieval_service, "retrieve", retrieval_service)(request)
    if inspect.isawaitable(result):
        result = await result
    retrieval = result.model_dump() if hasattr(result, "model_dump") else dict(result or {})
    prepared = await prepare_candidates_node(
        {"typed_retrieval": retrieval, "roster": list(request.roster)},
        None,
    )
    bundle = prepared.get("candidate_bundle") or {}
    if any(
        isinstance(candidate, dict) and candidate.get("id")
        for candidate in bundle.get("backend_candidates", [])
    ):
        projection = build_compact_projection(bundle, user_query=request.preferences)
    else:
        projection = {
            "version": "feature-h1-empty-projection-v1",
            "projection_id": "projection:no-backend-candidates",
            "candidate_ids": [],
            "candidates": [],
        }
    return bundle, projection


async def run_h1_evaluation(
    scenarios: Iterable[H1Scenario],
    retrieval_service: Any,
    transport: Callable[[AnalyzerProviderRequest], Any],
) -> dict[str, Any]:
    """Compare both arms over the real production retrieval boundary."""
    selected = list(scenarios)
    if not selected or len(selected) > H1_MAX_SCENARIOS:
        raise ValueError(f"H1 requires one to {H1_MAX_SCENARIOS} selected scenarios")
    reports = []
    for scenario in selected:
        try:
            bundle, projection = await prepare_h1_scenario(scenario, retrieval_service)
        except ProductionRequestError as exc:
            reports.append(_preparation_failure(scenario, "request_or_retrieval_error", [
                {"code": issue.code, "field": issue.field, "message": issue.message}
                for issue in exc.issues
            ]))
        except Exception as exc:  # noqa: BLE001 - report unexpected product failures by type only
            reports.append(_preparation_failure(scenario, "retrieval_unexpected_error", [{"type": type(exc).__name__}]))
        else:
            reports.append(compare_h1_bundle(scenario, bundle, projection, transport))

    return _aggregate_reports(reports, len(selected))


def compare_h1_bundle(
    scenario: H1Scenario,
    bundle: Mapping[str, Any],
    projection: Mapping[str, Any],
    transport: Callable[[AnalyzerProviderRequest], Any],
) -> dict[str, Any]:
    """Run A/B over a prepared bundle while retaining one projection object."""
    bundle_value = dict(bundle)
    projection_value = dict(projection)
    candidates = [
        candidate
        for candidate in bundle_value.get("backend_candidates", [])
        if isinstance(candidate, dict) and candidate.get("id")
    ]
    base = {
        "scenario_id": scenario.scenario_id,
        "category": scenario.category,
        "selection_note": scenario.selection_note,
        "boss": (bundle_value.get("boss") or {}).get("name"),
        "projection": _projection_metadata(projection_value),
        "backend_candidate_ranking": [_candidate_summary(candidate) for candidate in candidates],
        "variants": {},
    }
    if not candidates:
        base["status"] = "no_backend_candidates"
        base["preparation_errors"] = [{"code": "backend.no_candidates"}]
        base["comparison"] = _empty_comparison()
        return base

    variant_reports = {}
    for variant in H1_VARIANTS:
        config = variant.config()
        port = create_analyzer_port(config, transport)
        result = run_bounded_analyzer(
            {
                "user_query": str((scenario.request.get("preferences") or "")),
                "candidate_warnings": [],
                "analyzer_provider": config.provider,
                "analyzer_model": config.model,
                "analyzer_reasoning_effort": config.reasoning_effort,
                "analyzer_initial_max_output_tokens": config.initial_max_output_tokens,
                "analyzer_correction_max_output_tokens": config.correction_max_output_tokens,
                "analyzer_fallback_models": (),
                "analyzer_per_call_token_budget": config.per_call_token_budget,
                "analyzer_cumulative_token_budget": config.cumulative_token_budget,
            },
            bundle_value,
            port=port,
            projection=projection_value,
        )
        variant_reports[variant.variant_id] = _variant_report(
            variant,
            result,
            port.requests,
            projection_value,
            bundle_value,
        )

    base["status"] = "completed"
    base["variants"] = variant_reports
    base["comparison"] = _compare_variants(variant_reports)
    return base


def _variant_report(
    variant: H1AnalyzerVariant,
    result: Mapping[str, Any],
    requests: list[AnalyzerProviderRequest],
    projection: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    attempts = [dict(row) for row in result.get("analyzer_usage", []) if isinstance(row, Mapping)]
    raw_outputs = [row.get("raw_structured_output") for row in attempts if isinstance(row.get("raw_structured_output"), dict)]
    candidate_ids = {str(value) for value in projection.get("candidate_ids", [])}
    rankings = _collect_ranked_ids(raw_outputs, candidate_ids)
    refinements = [
        fragment
        for output in raw_outputs
        for fragment in (output.get("refinements") if isinstance(output.get("refinements"), list) else [])
        if isinstance(fragment, dict)
    ]
    analysis = _analysis_output(result.get("analysis_result"))
    recommendations = analysis.get("recommendations") if isinstance(analysis.get("recommendations"), list) else []
    top_candidate = _candidate_by_id(bundle, rankings[0] if rankings else None)
    fallback_used = any(_fallback_used(row.get("fallback")) for row in attempts)
    application_attempts = [
        {
            "call_number": row.get("call_number"),
            "call_kind": row.get("call_kind"),
            "passed": not row.get("validation_errors") and not row.get("error_code"),
            "validation_error_codes": [error.get("code") for error in row.get("validation_errors", []) if isinstance(error, dict)],
            "error_code": row.get("error_code"),
        }
        for row in attempts
    ]
    request_shapes = [
        {
            "call_number": index,
            "call_kind": request.call_kind,
            "model": request.model,
            "reasoning": request.payload.get("reasoning"),
            "max_output_tokens": request.max_output_tokens,
            "projection_id": request.projection_id,
            "fallback_models": list(request.fallback_models),
        }
        for index, request in enumerate(requests, start=1)
    ]
    usage = _usage_summary(attempts)
    output_valid = bool(recommendations) and bool(application_attempts) and application_attempts[-1]["passed"]
    refinement_ids_closed_world = all(
        fragment.get("candidate_id") in candidate_ids
        for fragment in refinements
    )
    return {
        "variant_id": variant.variant_id,
        "model": H1_MODEL,
        "reasoning_effort": variant.reasoning_effort,
        "initial_max_output_tokens": variant.max_output_tokens,
        "correction_max_output_tokens": variant.config().correction_max_output_tokens,
        "request_shapes": request_shapes,
        "application_validation": {
            "attempts": application_attempts,
            "final_response_valid": output_valid,
            "result_available": bool(recommendations),
            "degraded": bool(result.get("analysis_failure")),
        },
        "closed_world": {
            "candidate_ids": all(candidate_id in candidate_ids for candidate_id in rankings) and refinement_ids_closed_world,
            "refinement_candidate_ids": refinement_ids_closed_world,
            "swap_authorized": all(_swap_is_authorized(fragment.get("candidate_id"), fragment.get("swap"), projection) for fragment in refinements),
            "skill_selections_valid": all(_skills_are_valid(fragment, projection) for fragment in refinements),
        },
        "fallback_forbidden": {"used": fallback_used, "passed": not fallback_used},
        "provider_errors": [
            {"call_number": row.get("call_number"), "code": row.get("error_code")}
            for row in attempts
            if row.get("error_code")
        ],
        "ranking": rankings,
        "selected_top_candidate": top_candidate,
        "selected_skills": [dict(fragment.get("skill_selections") or {}) for fragment in refinements],
        "swap_decisions": [
            {"candidate_id": fragment.get("candidate_id"), "swap": fragment.get("swap")}
            for fragment in refinements
            if fragment.get("swap") is not None
        ],
        "advisories": [
            _bounded_text(advisory)
            for output in raw_outputs
            for advisory in (output.get("advisories") if isinstance(output.get("advisories"), list) else [])
            if isinstance(advisory, str)
        ][:8],
        "risks": [
            _bounded_text(risk)
            for risk in ((recommendations[0] or {}).get("risks") or [])
            if isinstance(risk, str)
        ][:8] if recommendations and isinstance(recommendations[0], dict) else [],
        "top_recommendation": _bounded_json(recommendations[0]) if recommendations and isinstance(recommendations[0], dict) else None,
        "usage": usage,
        "provider_diagnostics": [_safe_attempt(row) for row in attempts],
        "strategic_quality": "manual_review_required",
    }


def _aggregate_reports(reports: list[dict[str, Any]], scenario_count: int) -> dict[str, Any]:
    completed = [report for report in reports if report.get("status") == "completed"]
    return {
        "evaluation_version": H1_EVALUATION_VERSION,
        "purpose": "real-data quality/cost/reliability evaluation; not a production configuration change",
        "scenario_count": scenario_count,
        "initial_call_estimate": scenario_count * len(H1_VARIANTS),
        "maximum_application_call_count": scenario_count * len(H1_VARIANTS) * ANALYZER_MAX_CALLS,
        "fallback_enabled": False,
        "production_configuration_changed": False,
        "winner": None,
        "decision": "manual review of real-data results is required",
        "completed_scenario_count": len(completed),
        "scenarios": reports,
    }


def _compare_variants(variants: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    baseline = variants.get("baseline_a") or {}
    variant = variants.get("variant_b") or {}
    baseline_ranking = list(baseline.get("ranking") or [])
    variant_ranking = list(variant.get("ranking") or [])
    baseline_swaps = list(baseline.get("swap_decisions") or [])
    variant_swaps = list(variant.get("swap_decisions") or [])
    baseline_usage = baseline.get("usage") or {}
    variant_usage = variant.get("usage") or {}
    return {
        "same_top_candidate": bool(baseline_ranking and variant_ranking and baseline_ranking[0] == variant_ranking[0]),
        "same_ranking": bool(baseline_ranking and variant_ranking and baseline_ranking == variant_ranking),
        "same_swap": baseline_swaps == variant_swaps,
        "swap_authorized": bool((baseline.get("closed_world") or {}).get("swap_authorized", False)) and bool((variant.get("closed_world") or {}).get("swap_authorized", False)),
        "both_valid": bool((baseline.get("application_validation") or {}).get("final_response_valid")) and bool((variant.get("application_validation") or {}).get("final_response_valid")),
        "candidate_ids_closed_world": bool((baseline.get("closed_world") or {}).get("candidate_ids", False)) and bool((variant.get("closed_world") or {}).get("candidate_ids", False)),
        "skill_selections_valid": bool((baseline.get("closed_world") or {}).get("skill_selections_valid", False)) and bool((variant.get("closed_world") or {}).get("skill_selections_valid", False)),
        "token_delta": _delta(baseline_usage.get("total_tokens"), variant_usage.get("total_tokens")),
        "cost_delta": _delta(baseline_usage.get("cost"), variant_usage.get("cost")),
        "latency_delta_ms": _delta(baseline_usage.get("latency_ms"), variant_usage.get("latency_ms")),
        "strategic_quality": "manual_review_required",
    }


def _projection_metadata(projection: Mapping[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "projection_id": projection.get("projection_id"),
        "candidate_count": len(projection.get("candidate_ids", [])),
        "serialized_characters": len(serialized),
        "serialized_bytes": len(serialized.encode("utf-8")),
        "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


def _candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("id"),
        "archetype": candidate.get("archetype"),
        "character_ids": list(candidate.get("character_ids", [])),
        "score": candidate.get("score"),
        "component_scores": dict(candidate.get("component_scores") or {}),
        "coverage": dict(candidate.get("coverage") or candidate.get("backend_coverage") or {}),
    }


def _candidate_by_id(bundle: Mapping[str, Any], candidate_id: str | None) -> dict[str, Any] | None:
    if not candidate_id:
        return None
    for candidate in bundle.get("backend_candidates", []):
        if isinstance(candidate, dict) and candidate.get("id") == candidate_id:
            return _candidate_summary(candidate)
    return None


def _collect_ranked_ids(outputs: list[dict[str, Any]], candidate_ids: set[str]) -> list[str]:
    ranked: list[str] = []
    for output in outputs:
        for value in output.get("ranked_candidate_ids", []):
            if isinstance(value, str) and value in candidate_ids and value not in ranked:
                ranked.append(value)
    return ranked


def _swap_is_authorized(candidate_id: Any, swap: Any, projection: Mapping[str, Any]) -> bool:
    if swap is None:
        return True
    if not isinstance(swap, Mapping):
        return False
    return any(
        isinstance(item, dict)
        and item.get("candidate_id") == candidate_id
        and item.get("slot") == (swap or {}).get("slot")
        and item.get("alternative_character_id") == (swap or {}).get("character_id")
        for item in projection.get("allowed_swaps", [])
    )


def _skills_are_valid(fragment: Mapping[str, Any], projection: Mapping[str, Any]) -> bool:
    selected_ids = set()
    for candidate in projection.get("candidates", []):
        if isinstance(candidate, dict) and candidate.get("id") == fragment.get("candidate_id"):
            selected_ids.update(candidate.get("character_ids", []))
            break
    characters = projection.get("catalogs", {}).get("characters", {})
    selections = fragment.get("skill_selections") or {}
    if not isinstance(selections, Mapping):
        return False
    for character_id, skill_ids in selections.items():
        if character_id not in selected_ids:
            return False
        allowed = {skill.get("id") for skill in characters.get(character_id, {}).get("skills", []) if isinstance(skill, dict)}
        if not isinstance(skill_ids, list) or len(skill_ids) not in {3, 4} or not set(skill_ids).issubset(allowed):
            return False
    return True


def _analysis_output(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _safe_attempt(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep report diagnostics bounded to known non-sensitive fields."""
    safe = {
        key: row.get(key)
        for key in (
            "call_number",
            "call_kind",
            "provider",
            "model",
            "requested_model",
            "served_model",
            "served_model_status",
            "fallback_status",
            "finish_reason",
            "finish_reason_status",
            "allowed_candidate_ids",
            "relevant_allowed_swaps",
            "validation_errors",
            "metadata_availability",
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "cached_tokens",
            "total_tokens",
            "cost",
            "latency_ms",
            "generation_id",
            "error_code",
        )
        if key in row
    }
    fallback = row.get("fallback")
    if isinstance(fallback, Mapping):
        safe["fallback"] = {
            "used": bool(fallback.get("used")) if "used" in fallback else None,
            "served_model": fallback.get("served_model"),
        }
    elif fallback is not None:
        safe["fallback"] = bool(fallback)
    raw_output = row.get("raw_structured_output")
    if isinstance(raw_output, dict):
        safe["raw_structured_output"] = _bounded_json(raw_output, limit=12_000)
    return safe


def _bounded_text(value: str, limit: int = 2_000) -> str:
    return value[:limit]


def _bounded_json(value: Any, *, limit: int = 6_000) -> Any:
    """Bound provider-derived report content without retaining raw bodies."""
    if isinstance(value, str):
        return _bounded_text(value, min(limit, 2_000))
    if isinstance(value, list):
        return [_bounded_json(item, limit=max(500, limit // max(1, min(len(value), 8)))) for item in value[:8]]
    if isinstance(value, Mapping):
        return {
            str(key): _bounded_json(child, limit=max(500, limit // max(1, min(len(value), 16))))
            for key, child in list(value.items())[:16]
        }
    return value


def _usage_summary(attempts: list[Mapping[str, Any]]) -> dict[str, Any]:
    total_tokens = sum(
        _number(row.get("total_tokens"))
        or sum(_number(row.get(key)) for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens"))
        for row in attempts
    )
    costs = [_number(row.get("cost")) for row in attempts if row.get("cost") is not None]
    latencies = [_number(row.get("latency_ms")) for row in attempts if row.get("latency_ms") is not None]
    return {
        "attempt_count": len(attempts),
        "total_tokens": int(total_tokens),
        "cost": round(sum(costs), 8) if costs else None,
        "latency_ms": sum(latencies) if latencies else None,
        "prompt_tokens": _sum_available(attempts, "prompt_tokens"),
        "completion_tokens": _sum_available(attempts, "completion_tokens"),
        "reasoning_tokens": _sum_available(attempts, "reasoning_tokens"),
        "within_cumulative_budget": total_tokens <= ANALYZER_CUMULATIVE_TOKEN_BUDGET,
        "per_call_output_limits": [row.get("max_output_tokens") for row in attempts],
    }


def _sum_available(rows: list[Mapping[str, Any]], key: str) -> int | None:
    values = [row.get(key) for row in rows if row.get(key) is not None]
    return int(sum(_number(value) for value in values)) if values else None


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _delta(left: Any, right: Any) -> float | int | None:
    if left is None or right is None:
        return None
    value = _number(right) - _number(left)
    return int(value) if value.is_integer() else value


def _fallback_used(value: Any) -> bool:
    return value is True or isinstance(value, Mapping) and value.get("used") is True


def _empty_comparison() -> dict[str, Any]:
    return {
        "same_top_candidate": False,
        "same_ranking": False,
        "same_swap": False,
        "swap_authorized": False,
        "both_valid": False,
        "candidate_ids_closed_world": False,
        "skill_selections_valid": False,
        "token_delta": None,
        "cost_delta": None,
        "latency_delta_ms": None,
        "strategic_quality": "manual_review_required",
    }


def _preparation_failure(scenario: H1Scenario, status: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "category": scenario.category,
        "selection_note": scenario.selection_note,
        "boss": scenario.request.get("boss_id"),
        "status": status,
        "preparation_errors": errors,
        "variants": {},
        "comparison": _empty_comparison(),
    }


__all__ = [
    "H1AnalyzerVariant",
    "H1Scenario",
    "H1_EVALUATION_VERSION",
    "H1_MAX_SCENARIOS",
    "H1_MODEL",
    "H1_VARIANTS",
    "compare_h1_bundle",
    "load_h1_scenarios",
    "prepare_h1_scenario",
    "run_h1_evaluation",
]
