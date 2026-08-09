"""Provider-neutral, bounded analyzer refinement for typed production candidates.

The backend candidate bundle is the legality authority.  This module exposes a
small projection to an analyzer, validates only advisory refinements, and then
re-validates every resulting lineup against the deterministic backend contract.
Provider adapters are deliberately transport-injected so offline tests never
need credentials or a live paid call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .candidates import resolve_candidate_recommendations, validate_candidate_response
from .lineup_generation import evaluate_backend_lineup


ANALYZER_PROJECTION_VERSION = "feature-g-analyzer-projection-v1"
ANALYZER_PORT_VERSION = "feature-g-analyzer-port-v1"
ANALYZER_MAX_CALLS = 2
ANALYZER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ranked_candidate_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "refinements": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "candidate_id": {"type": "string"},
                    "strategy_summary": {"type": "string"},
                    "explanation": {"type": "string"},
                    "skill_selections": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                            "maxItems": 4,
                        },
                    },
                    "hero_advice": {
                        "type": "array",
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "character_id": {"type": "string"},
                                "display_role": {"type": "string"},
                            },
                            "required": ["character_id", "display_role"],
                        },
                    },
                    "swap": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "slot": {"type": "string"},
                                    "character_id": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["slot", "character_id", "reason"],
                            },
                        ]
                    },
                    "risks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 6,
                    },
                },
                "required": ["candidate_id"],
            },
        },
        "advisories": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
    },
    "required": ["ranked_candidate_ids", "refinements", "advisories"],
}

_FORBIDDEN_AUTHORITY_KEYS = {
    "role_scores",
    "role_ids",
    "mandatory_coverage",
    "coverage_claims",
    "proven_coverage",
}
_FORBIDDEN_AUTHORITY_PHRASES = (
    "mandatory coverage",
    "role score",
    "role id",
    "coverage claim",
)


@dataclass(frozen=True)
class AnalyzerProviderConfig:
    """Explicit per-run provider selection; no credential values are stored."""

    provider: Literal["deepseek", "openrouter"]
    model: str | None = None
    initial_max_output_tokens: int = 4000
    correction_max_output_tokens: int = 2000
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if self.provider not in {"deepseek", "openrouter"}:
            raise ValueError("provider must be deepseek or openrouter")

    @property
    def resolved_model(self) -> str:
        if self.model:
            return self.model
        return "deepseek-chat" if self.provider == "deepseek" else "openrouter/auto"


@dataclass(frozen=True)
class AnalyzerProviderRequest:
    provider: str
    model: str
    call_kind: Literal["initial", "correction"]
    messages: list[dict[str, str]]
    projection_id: str
    max_output_tokens: int
    response_schema: dict[str, Any] = field(default_factory=lambda: ANALYZER_RESPONSE_SCHEMA)

    @property
    def payload(self) -> dict[str, Any]:
        """Return the common structured-output payload used by both adapters."""
        return {
            "model": self.model,
            "messages": self.messages,
            "temperature": 0.0,
            "max_tokens": self.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "another_eden_analyzer",
                    "strict": True,
                    "schema": self.response_schema,
                },
            },
        }


@dataclass
class AnalyzerResponseEnvelope:
    """Shared response/usage/error envelope for DeepSeek and OpenRouter."""

    provider: str
    model: str
    output: dict[str, Any] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": ANALYZER_PORT_VERSION,
            "provider": self.provider,
            "model": self.model,
            "output": self.output,
            "usage": self.usage,
            "error": self.error,
        }


class AnalyzerAdapter:
    """Small transport-injected adapter shared by the two provider routes."""

    provider: Literal["deepseek", "openrouter"]

    def __init__(self, config: AnalyzerProviderConfig, transport: Callable[[AnalyzerProviderRequest], Any] | None = None):
        self.config = config
        self.transport = transport
        self.requests: list[AnalyzerProviderRequest] = []

    def generate(self, request: AnalyzerProviderRequest) -> AnalyzerResponseEnvelope:
        self.requests.append(request)
        if self.transport is None:
            return AnalyzerResponseEnvelope(
                provider=self.config.provider,
                model=self.config.resolved_model,
                error={
                    "code": "provider.transport_unconfigured",
                    "message": "No analyzer transport was configured for this run.",
                    "retriable": False,
                },
            )
        try:
            raw = self.transport(request)
        except Exception as exc:  # noqa: BLE001 - provider failures are degraded, not fatal
            return AnalyzerResponseEnvelope(
                provider=self.config.provider,
                model=self.config.resolved_model,
                error={
                    "code": "provider.transport_error",
                    "message": str(exc),
                    "retriable": False,
                },
            )
        return _normalise_provider_response(raw, self.config)


class DeepSeekAnalyzerAdapter(AnalyzerAdapter):
    provider = "deepseek"


class OpenRouterAnalyzerAdapter(AnalyzerAdapter):
    provider = "openrouter"


def create_analyzer_port(
    config: AnalyzerProviderConfig,
    transport: Callable[[AnalyzerProviderRequest], Any] | None = None,
) -> AnalyzerAdapter:
    """Create the explicitly selected adapter without reading environment keys."""
    adapter_type = DeepSeekAnalyzerAdapter if config.provider == "deepseek" else OpenRouterAnalyzerAdapter
    return adapter_type(config, transport)


def build_compact_projection(bundle: dict[str, Any], *, user_query: str = "", max_candidates: int = 10) -> dict[str, Any]:
    """Project only referenced backend candidates and their bounded facts."""
    backend_candidates = [
        candidate for candidate in bundle.get("backend_candidates", [])
        if isinstance(candidate, dict) and candidate.get("id")
    ][:max(1, min(int(max_candidates), 10))]
    candidate_ids = {str(candidate["id"]) for candidate in backend_candidates}
    character_ids = {
        str(character_id)
        for candidate in backend_candidates
        for character_id in candidate.get("character_ids", [])
    }
    characters = {
        str(row.get("id")): row
        for row in bundle.get("characters", [])
        if isinstance(row, dict) and row.get("id") in character_ids
    }
    sidekick_ids = {
        str(sidekick_id)
        for candidate in backend_candidates
        for sidekick_id in (candidate.get("main_sidekick_id"), candidate.get("sub_sidekick_id"))
        if sidekick_id
    }
    sidekicks = {
        str(row.get("id")): row
        for row in bundle.get("sidekicks", [])
        if isinstance(row, dict) and row.get("id") in sidekick_ids
    }

    compact_characters = {
        character_id: _compact_character(row)
        for character_id, row in sorted(characters.items())
    }
    compact_candidates = [
        _compact_candidate(candidate, compact_characters)
        for candidate in backend_candidates
    ]
    allowed_swaps = _allowed_swaps(compact_candidates, compact_characters)
    projection = {
        "version": ANALYZER_PROJECTION_VERSION,
        "user_query": str(user_query or "")[:1000],
        "candidate_ids": sorted(candidate_ids),
        "candidates": compact_candidates,
        "catalogs": {
            "characters": compact_characters,
            "sidekicks": {
                sidekick_id: _compact_sidekick(row)
                for sidekick_id, row in sorted(sidekicks.items())
            },
            "citations": _compact_citations(bundle.get("boss", {}).get("citations", [])),
        },
        "boss": _compact_boss(bundle.get("boss", {})),
        "allowed_swaps": allowed_swaps,
        "constraints": {
            "max_recommendations": 3,
            "max_swaps_per_lineup": 1,
            "skill_count_per_character": [3, 4],
            "role_authority": "backend_role_assignments_are_read_only",
            "coverage_authority": "backend_candidate_coverage_is_read_only",
            "forbidden_analyzer_fields": sorted(_FORBIDDEN_AUTHORITY_KEYS),
            "candidate_ids_are_closed_world": True,
        },
        "policy_versions": {
            "projection": ANALYZER_PROJECTION_VERSION,
            "candidate_generation": _candidate_generation_version(bundle),
            "role_scoring": _role_scoring_version(bundle),
            "build_packages": _build_package_version(bundle),
        },
    }
    projection["projection_id"] = _stable_json_id(projection)
    return projection


build_analyzer_projection = build_compact_projection


def validate_analyzer_output(value: Any, projection: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return valid advisory fragments, invalid fragments, and structured errors."""
    if not isinstance(value, dict):
        return [], [], [_error("structured_output.shape", "response", "Expected an object", [])]
    authority_errors = [
        _error("authority.forbidden_field", f"response.{key}", "Analyzer cannot author deterministic backend authority", [])
        for key in value
        if key in _FORBIDDEN_AUTHORITY_KEYS
    ]
    if authority_errors:
        return [], [{"fragment": value, "errors": authority_errors}], authority_errors
    allowed_top = {"ranked_candidate_ids", "refinements", "advisories"}
    unknown = sorted(set(value) - allowed_top)
    if unknown:
        error = _error("structured_output.extra_field", "response", "Unknown analyzer fields", unknown)
        return [], [{"fragment": value, "errors": [error]}], [error]

    candidate_ids = set(projection.get("candidate_ids", []))
    ranked = value.get("ranked_candidate_ids", [])
    refinements = value.get("refinements", [])
    advisories = value.get("advisories", [])
    errors: list[dict[str, Any]] = []
    if not isinstance(ranked, list) or len(ranked) > 3:
        errors.append(_error("shape.ranking", "ranked_candidate_ids", "Ranking must contain at most three IDs", sorted(candidate_ids)))
        ranked = []
    else:
        for index, candidate_id in enumerate(ranked):
            if candidate_id not in candidate_ids:
                errors.append(_error("id.candidate", f"ranked_candidate_ids.{index}", "Unknown backend candidate ID", sorted(candidate_ids)))
    if not isinstance(refinements, list) or len(refinements) > 3:
        errors.append(_error("shape.refinements", "refinements", "Refinements must contain at most three objects", []))
        refinements = []
    if not isinstance(advisories, list) or any(not isinstance(item, str) for item in advisories):
        errors.append(_error("shape.advisories", "advisories", "Advisories must be strings", []))
        advisories = []

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, fragment in enumerate(refinements):
        fragment_errors = _validate_refinement(fragment, index, projection)
        if fragment_errors:
            invalid.append({"index": index, "fragment": fragment, "errors": fragment_errors})
            errors.extend(fragment_errors)
            continue
        candidate_id = fragment["candidate_id"]
        if candidate_id in seen_ids:
            duplicate = _error("candidate.duplicate", f"refinements.{index}.candidate_id", "Candidate may be refined only once", sorted(candidate_ids))
            invalid.append({"index": index, "fragment": fragment, "errors": [duplicate]})
            errors.append(duplicate)
            continue
        seen_ids.add(candidate_id)
        valid.append(_normalise_refinement(fragment))

    if not valid and not [item for item in ranked if item in candidate_ids]:
        missing = _error("shape.empty", "response", "At least one valid candidate ranking or refinement is required", sorted(candidate_ids))
        errors.append(missing)
    return valid, invalid, errors


def correction_payload(
    projection: dict[str, Any],
    invalid_fragments: list[dict[str, Any]],
    frozen_candidate_ids: list[str],
) -> dict[str, Any]:
    """Build a fragment-only correction payload with no full projection replay."""
    candidate_ids = set(projection.get("candidate_ids", []))
    return {
        "schema_version": ANALYZER_PORT_VERSION,
        "instruction": "Correct only the invalid fragments. Frozen candidates are final; do not repeat or modify them.",
        "frozen_candidate_ids": [value for value in frozen_candidate_ids if value in candidate_ids],
        "invalid_fragments": invalid_fragments,
        "allowed_candidate_ids": sorted(candidate_ids),
        "allowed_swap_slots": sorted({item.get("slot") for item in projection.get("allowed_swaps", []) if item.get("slot")}),
        "immutable_constraints": projection.get("constraints", {}),
    }


def run_bounded_analyzer(state: dict[str, Any], bundle: dict[str, Any], port: AnalyzerAdapter | None = None) -> dict[str, Any]:
    """Run one initial call and at most one fragment-only correction call."""
    projection = build_compact_projection(bundle, user_query=state.get("user_query", ""))
    config = AnalyzerProviderConfig(
        provider=state.get("analyzer_provider", "openrouter"),
        model=state.get("analyzer_model"),
    )
    port = port or state.get("analyzer_port") or create_analyzer_port(config, state.get("analyzer_transport"))
    usage_rows: list[dict[str, Any]] = []
    structured_errors: list[dict[str, Any]] = []
    candidate_errors: list[dict[str, Any]] = []
    warnings = list(state.get("candidate_warnings", []))
    frozen: dict[str, dict[str, Any]] = {}
    pending_invalid: list[dict[str, Any]] = []
    call_count = 0
    correction_rounds = 0
    advisories: list[str] = []

    request = _provider_request(
        config,
        call_kind="initial",
        projection_id=projection["projection_id"],
        content={"instruction": "Rank and optionally refine the supplied backend candidates.", "projection": projection},
    )
    response = port.generate(request)
    call_count += 1
    usage_rows.append(_usage_row(response, call_count, "initial"))
    if response.error or response.output is None:
        return _degraded_result(
            bundle,
            warnings,
            reason=(response.error or {}).get("code", "provider.empty_response"),
            call_count=call_count,
            correction_rounds=0,
            usage_rows=usage_rows,
            structured_errors=structured_errors,
            candidate_errors=candidate_errors,
            provider=config,
        )

    valid, pending_invalid, errors = validate_analyzer_output(response.output, projection)
    if errors and not pending_invalid and not valid:
        pending_invalid = [{"index": 0, "fragment": response.output, "errors": errors}]
    structured_errors.extend(error for error in errors if error.get("code", "").startswith("structured_output"))
    candidate_errors.extend(error for error in errors if not error.get("code", "").startswith("structured_output"))
    advisories = [item for item in response.output.get("advisories", []) if isinstance(item, str)][:8]
    _freeze_fragments(frozen, valid)
    ranked_ids = _valid_ranked_ids(response.output, projection)

    if pending_invalid and call_count < ANALYZER_MAX_CALLS:
        correction_rounds = 1
        correction = correction_payload(projection, pending_invalid, list(frozen))
        correction_request = _provider_request(
            config,
            call_kind="correction",
            projection_id=projection["projection_id"],
            content=correction,
        )
        correction_response = port.generate(correction_request)
        call_count += 1
        usage_rows.append(_usage_row(correction_response, call_count, "correction"))
        if correction_response.error or correction_response.output is None:
            warnings.append("Analyzer correction failed; valid initial refinements were frozen.")
        else:
            corrected, still_invalid, correction_errors = validate_analyzer_output(correction_response.output, projection)
            _freeze_fragments(frozen, corrected)
            candidate_errors.extend(correction_errors)
            pending_invalid = still_invalid
            ranked_ids.extend(_valid_ranked_ids(correction_response.output, projection))
            advisories.extend(
                item for item in correction_response.output.get("advisories", [])
                if isinstance(item, str)
            )
    if pending_invalid:
        warnings.append(f"Discarded {len(pending_invalid)} invalid analyzer fragment(s) after the correction cap.")
    if advisories:
        warnings.append("Analyzer advisories are non-authoritative and were revalidated against backend candidates.")

    return _render_result(
        bundle=bundle,
        projection=projection,
        frozen=frozen,
        ranked_ids=ranked_ids,
        warnings=warnings,
        call_count=call_count,
        correction_rounds=correction_rounds,
        usage_rows=usage_rows,
        structured_errors=structured_errors,
        candidate_errors=candidate_errors,
        provider=config,
        degraded=not bool(frozen or ranked_ids),
    )


def _render_result(*, bundle, projection, frozen, ranked_ids, warnings, call_count, correction_rounds, usage_rows, structured_errors, candidate_errors, provider, degraded):
    backend_by_id = {str(candidate.get("id")): candidate for candidate in bundle.get("backend_candidates", [])}
    ordered_ids = []
    for candidate_id in ranked_ids:
        if candidate_id in backend_by_id and candidate_id not in ordered_ids:
            ordered_ids.append(candidate_id)
    if not ordered_ids:
        ordered_ids.extend(backend_by_id)
    proposals: list[dict[str, Any]] = []
    for candidate_id in ordered_ids[:3]:
        candidate = backend_by_id[candidate_id]
        refinement = frozen.get(candidate_id, {})
        refined_candidate, refinement_warnings = _apply_refinement(candidate, refinement, bundle, projection)
        warnings.extend(refinement_warnings)
        proposal = _candidate_proposal(refined_candidate, bundle, refinement, degraded=degraded)
        valid, invalid = validate_candidate_response({"recommendations": [proposal]}, bundle)
        if not valid:
            fallback_proposal = _candidate_proposal(candidate, bundle, {}, degraded=degraded)
            valid, fallback_invalid = validate_candidate_response({"recommendations": [fallback_proposal]}, bundle)
            invalid = fallback_invalid
            if valid:
                proposal = fallback_proposal
                warnings.append(f"Analyzer refinement for {candidate_id} was rejected; backend default retained.")
        if valid:
            proposals.append(proposal)
        else:
            candidate_errors.extend(error for item in invalid for error in item.get("errors", []))
    if not proposals and degraded and backend_by_id:
        # Backend candidates already passed the deterministic generation gates;
        # preserve them even if the display projection cannot be reassembled.
        proposals = [
            _candidate_proposal(backend_by_id[candidate_id], bundle, {}, degraded=True)
            for candidate_id in ordered_ids[:3]
        ]
        warnings.append("Degraded backend candidates were retained without analyzer refinement.")
    if not proposals:
        return _degraded_result(
            bundle,
            warnings,
            reason="backend_projection_render_failed",
            call_count=call_count,
            correction_rounds=correction_rounds,
            usage_rows=usage_rows,
            structured_errors=structured_errors,
            candidate_errors=candidate_errors,
            provider=provider,
        )
    resolved = resolve_candidate_recommendations(proposals[:3], bundle, warnings)
    resolved["degraded"] = degraded
    return {
        "analysis_result": json.dumps(resolved, ensure_ascii=False),
        "cypher_retry_count": 0,
        "analyzer_provider": provider.provider,
        "analyzer_model": provider.resolved_model,
        "analyzer_call_count": min(call_count, ANALYZER_MAX_CALLS),
        "analyzer_correction_rounds": correction_rounds,
        "provider_transport_retries": 0,
        "analyzer_usage": usage_rows,
        "structured_output_errors": structured_errors,
        "candidate_validation_errors": candidate_errors,
        "analysis_failure": {"type": "analyzer_degraded", "message": "Backend candidates were returned without analyzer authority."} if degraded else {},
    }


def _degraded_result(bundle, warnings, *, reason, call_count, correction_rounds, usage_rows, structured_errors, candidate_errors, provider):
    warnings = [*warnings, f"Analyzer degraded mode: {reason}. Backend candidates remain authoritative."]
    return _render_result(
        bundle=bundle,
        projection=build_compact_projection(bundle),
        frozen={},
        ranked_ids=[],
        warnings=warnings,
        call_count=call_count,
        correction_rounds=correction_rounds,
        usage_rows=usage_rows,
        structured_errors=structured_errors,
        candidate_errors=candidate_errors,
        provider=provider,
        degraded=True,
    )


def _provider_request(config, *, call_kind, projection_id, content):
    return AnalyzerProviderRequest(
        provider=config.provider,
        model=config.resolved_model,
        call_kind=call_kind,
        projection_id=projection_id,
        max_output_tokens=(config.initial_max_output_tokens if call_kind == "initial" else config.correction_max_output_tokens),
        messages=[
            {
                "role": "system",
                "content": "Return only the strict analyzer JSON schema. Backend IDs, legality, role assignments, and coverage are read-only.",
            },
            {"role": "user", "content": json.dumps(content, ensure_ascii=False, separators=(",", ":"))},
        ],
    )


def _normalise_provider_response(raw, config):
    if isinstance(raw, AnalyzerResponseEnvelope):
        return raw
    if not isinstance(raw, dict):
        return AnalyzerResponseEnvelope(config.provider, config.resolved_model, error={"code": "provider.invalid_envelope", "message": "Provider response must be an object", "retriable": False})
    if raw.get("error"):
        error = raw["error"] if isinstance(raw["error"], dict) else {"message": str(raw["error"])}
        return AnalyzerResponseEnvelope(config.provider, config.resolved_model, usage=_normalise_usage(raw.get("usage")), error={"code": error.get("code", "provider.error"), "message": error.get("message", "Provider returned an error"), "retriable": bool(error.get("retriable", False))})
    output = raw.get("output")
    if output is None:
        choices = raw.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices and isinstance(choices[0], dict) else None
        if isinstance(content, dict):
            output = content
        elif isinstance(content, str):
            try:
                output = json.loads(content)
            except json.JSONDecodeError:
                return AnalyzerResponseEnvelope(config.provider, config.resolved_model, usage=_normalise_usage(raw.get("usage")), error={"code": "structured_output.invalid_json", "message": "Provider content was not valid JSON", "retriable": False})
    if not isinstance(output, dict):
        return AnalyzerResponseEnvelope(config.provider, config.resolved_model, usage=_normalise_usage(raw.get("usage")), error={"code": "provider.empty_output", "message": "Provider returned no structured analyzer object", "retriable": False})
    return AnalyzerResponseEnvelope(config.provider, config.resolved_model, output=output, usage=_normalise_usage(raw.get("usage")))


def _normalise_usage(value):
    if not isinstance(value, dict):
        return {}
    keys = ("prompt_tokens", "completion_tokens", "reasoning_tokens", "cached_tokens", "total_tokens", "cost", "latency_ms", "generation_id", "metadata")
    return {key: value[key] for key in keys if key in value}


def _usage_row(response, call_number, call_kind):
    return {
        "call_number": call_number,
        "call_kind": call_kind,
        "provider": response.provider,
        "model": response.model,
        **response.usage,
        "error_code": (response.error or {}).get("code"),
    }


def _compact_candidate(candidate, characters):
    character_ids = [str(value) for value in candidate.get("character_ids", []) if str(value) in characters]
    return {
        "id": str(candidate["id"]),
        "archetype": candidate.get("archetype"),
        "character_ids": character_ids,
        "frontline_character_ids": [str(value) for value in candidate.get("frontline_character_ids", []) if str(value) in characters],
        "reserve_character_ids": [str(value) for value in candidate.get("reserve_character_ids", []) if str(value) in characters],
        "backend_role_assignments": {
            key: list(value) for key, value in candidate.get("role_assignments", {}).items() if key in characters and isinstance(value, list)
        },
        "main_sidekick_id": candidate.get("main_sidekick_id"),
        "sub_sidekick_id": candidate.get("sub_sidekick_id"),
        "skill_package_ids": {
            key: [value for value in values if value in {skill["id"] for skill in characters[key].get("skills", [])}]
            for key, values in candidate.get("skill_package_ids", {}).items()
            if key in characters and isinstance(values, list)
        },
        "build_package_ids": dict(candidate.get("build_package_ids", {})),
        "backend_coverage": {
            "mandatory": list(candidate.get("coverage", {}).get("mandatory", [])),
            "optional": list(candidate.get("coverage", {}).get("optional", [])),
            "covered_roles": list(candidate.get("coverage", {}).get("covered_roles", [])),
            "required_boss_counters": list(candidate.get("coverage", {}).get("required_boss_counters", [])),
        },
        "component_scores": dict(candidate.get("component_scores", {})),
        "score": candidate.get("score"),
        "assumptions": list(candidate.get("assumptions", [])),
        "uncertainty": candidate.get("uncertainty"),
    }


def _compact_character(row):
    package = row.get("build_package") or {}
    return {
        "id": row.get("id"),
        "display_name": row.get("display_name") or row.get("name"),
        "weapon": row.get("weapon"),
        "traits": list(row.get("traits") or []),
        "backend_role_ids": list(row.get("role_ids") or []),
        "skills": [
            {"id": item.get("id"), "name": item.get("name"), "element": item.get("element"), "effect_tags": _effect_tags(item.get("description")), "requires_stellar_awakened": bool(item.get("requires_stellar_awakened"))}
            for item in row.get("skills", []) if item.get("id")
        ],
        "passives": [
            {"id": item.get("id"), "name": item.get("name"), "effect_tags": _effect_tags(item.get("description"))}
            for item in row.get("passives", []) if item.get("id")
        ],
        "build_package": {
            "id": package.get("id"),
            "weapon_id": package.get("weapon_id") or _nested_id(package.get("weapon")),
            "armor_id": package.get("armor_id") or _nested_id(package.get("armor")),
            "grasta_ids": list(package.get("grasta_ids") or [_nested_id(item) for item in package.get("grastas", []) if _nested_id(item)]),
            "assumptions": list(package.get("assumptions") or []),
            "setup_dependencies": list(package.get("setup_dependencies") or []),
            "citation_ids": list(package.get("citation_ids") or []),
        },
        "grastas": [
            {"id": item.get("id"), "display_name": item.get("display_name") or item.get("name"), "effect_tags": _effect_tags(item.get("effect_text") or item.get("description")), "acquisition_class": item.get("acquisition_class"), "max_theoretical_copies": item.get("max_theoretical_copies")}
            for item in row.get("grastas", []) if item.get("id")
        ],
    }


def _allowed_swaps(candidates, characters):
    pool = sorted({character_id for candidate in candidates for character_id in candidate.get("character_ids", [])})
    result = []
    for candidate in candidates:
        current_ids = list(candidate.get("character_ids", []))
        for slot_index, current_id in enumerate(current_ids):
            slot = f"frontline.{slot_index}" if slot_index < 4 else f"reserve.{slot_index - 4}"
            for alternative_id in pool:
                if alternative_id == current_id or alternative_id not in characters:
                    continue
                result.append({
                    "candidate_id": candidate["id"],
                    "slot": slot,
                    "current_character_id": current_id,
                    "alternative_character_id": alternative_id,
                    "backend_role_ids": characters[alternative_id].get("backend_role_ids", []),
                })
    return result


def _compact_sidekick(row):
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "skills": [{"id": item.get("id"), "name": item.get("name"), "effect_tags": _effect_tags(item.get("description"))} for item in row.get("skills", [])],
        "auras": [{"id": item.get("id"), "name": item.get("name"), "effect_tags": _effect_tags(item.get("description"))} for item in row.get("auras", [])],
    }


def _compact_boss(boss):
    return {
        "name": boss.get("name"),
        "affinities": {key: list(boss.get("affinities", {}).get(key, [])) for key in ("weak", "resist", "null", "absorb")},
        "facts": [{"id": item.get("id"), "kind": item.get("kind"), "value": item.get("value")} for item in boss.get("facts", []) if item.get("id")],
        "citation_ids": [item.get("id") for item in boss.get("citations", []) if item.get("id")],
    }


def _compact_citations(citations):
    return [{"id": item.get("id"), "label": item.get("label"), "source_url": item.get("source_url")} for item in citations if item.get("id") and item.get("source_url")]


def _validate_refinement(fragment, index, projection):
    path = f"refinements.{index}"
    errors = []
    if not isinstance(fragment, dict):
        return [_error("shape.refinement", path, "Refinement must be an object", [])]
    errors.extend(_authority_errors(fragment, path))
    candidate_ids = set(projection.get("candidate_ids", []))
    candidate_id = fragment.get("candidate_id")
    if candidate_id not in candidate_ids:
        errors.append(_error("id.candidate", f"{path}.candidate_id", "Unknown backend candidate ID", sorted(candidate_ids)))
    if "strategy_summary" in fragment and not isinstance(fragment["strategy_summary"], str):
        errors.append(_error("shape.strategy_summary", f"{path}.strategy_summary", "Expected text", []))
    if "explanation" in fragment and not isinstance(fragment["explanation"], str):
        errors.append(_error("shape.explanation", f"{path}.explanation", "Expected text", []))
    for key in ("strategy_summary", "explanation"):
        value = fragment.get(key)
        if isinstance(value, str) and any(phrase in value.casefold() for phrase in _FORBIDDEN_AUTHORITY_PHRASES):
            errors.append(_error("authority.free_text", f"{path}.{key}", "Free text cannot author backend authority", []))
    characters = projection.get("catalogs", {}).get("characters", {})
    selected_ids = set()
    candidate = next((item for item in projection.get("candidates", []) if item.get("id") == candidate_id), {})
    selected_ids.update(candidate.get("character_ids", []))
    skill_selections = fragment.get("skill_selections", {})
    if not isinstance(skill_selections, dict):
        errors.append(_error("shape.skill_selections", f"{path}.skill_selections", "Expected an object", []))
    else:
        for character_id, skill_ids in skill_selections.items():
            if character_id not in selected_ids:
                errors.append(_error("id.character", f"{path}.skill_selections.{character_id}", "Character is not in the backend candidate", sorted(selected_ids)))
                continue
            allowed = {skill.get("id") for skill in characters.get(character_id, {}).get("skills", [])}
            if not isinstance(skill_ids, list) or len(skill_ids) not in {3, 4} or len(set(skill_ids)) != len(skill_ids):
                errors.append(_error("shape.skills", f"{path}.skill_selections.{character_id}", "Select three or four distinct bounded skill IDs", sorted(allowed)))
            elif any(skill_id not in allowed for skill_id in skill_ids):
                errors.append(_error("id.skill", f"{path}.skill_selections.{character_id}", "Skill ID is outside the compact character catalog", sorted(allowed)))
    advice = fragment.get("hero_advice", [])
    if not isinstance(advice, list):
        errors.append(_error("shape.hero_advice", f"{path}.hero_advice", "Expected a list", sorted(selected_ids)))
    else:
        for advice_index, item in enumerate(advice):
            if not isinstance(item, dict) or set(item) != {"character_id", "display_role"} or item.get("character_id") not in selected_ids or not isinstance(item.get("display_role"), str) or not item["display_role"].strip():
                errors.append(_error("advisory.role", f"{path}.hero_advice.{advice_index}", "Display role wording must reference a selected character without a role ID", sorted(selected_ids)))
    swap = fragment.get("swap")
    if swap is not None:
        allowed_swaps = [item for item in projection.get("allowed_swaps", []) if item.get("candidate_id") == candidate_id]
        if not isinstance(swap, dict) or set(swap) != {"slot", "character_id", "reason"} or not isinstance(swap.get("reason"), str):
            errors.append(_error("shape.swap", f"{path}.swap", "Swap must be one supplied slot, ID, and reason", []))
        elif not any(item.get("slot") == swap.get("slot") and item.get("alternative_character_id") == swap.get("character_id") for item in allowed_swaps):
            errors.append(_error("swap.not_allowed", f"{path}.swap", "Swap is not in the backend-supplied alternative set", sorted({item.get("alternative_character_id") for item in allowed_swaps})))
    risks = fragment.get("risks", [])
    if risks is not None and (not isinstance(risks, list) or any(not isinstance(item, str) for item in risks)):
        errors.append(_error("shape.risks", f"{path}.risks", "Risks must be strings", []))
    return errors


def _authority_errors(value, path="response"):
    errors = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_AUTHORITY_KEYS:
                errors.append(_error("authority.forbidden_field", f"{path}.{key}", "Analyzer cannot author deterministic backend authority", []))
            errors.extend(_authority_errors(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_authority_errors(child, f"{path}.{index}"))
    return errors


def _normalise_refinement(fragment):
    return {
        "candidate_id": fragment["candidate_id"],
        "strategy_summary": str(fragment.get("strategy_summary") or ""),
        "explanation": str(fragment.get("explanation") or ""),
        "skill_selections": {str(key): list(value) for key, value in (fragment.get("skill_selections") or {}).items()},
        "hero_advice": list(fragment.get("hero_advice") or []),
        "swap": fragment.get("swap"),
        "risks": list(fragment.get("risks") or []),
    }


def _freeze_fragments(frozen, fragments):
    for fragment in fragments:
        frozen.setdefault(fragment["candidate_id"], fragment)


def _valid_ranked_ids(value, projection):
    allowed = set(projection.get("candidate_ids", []))
    return [candidate_id for candidate_id in value.get("ranked_candidate_ids", []) if candidate_id in allowed]


def _apply_refinement(candidate, refinement, bundle, projection):
    if not refinement:
        return candidate, []
    warnings = []
    candidate_copy = json.loads(json.dumps(candidate))
    swap = refinement.get("swap")
    if swap:
        character_ids = list(candidate_copy.get("character_ids", []))
        slot_index = _slot_index(swap.get("slot"))
        if slot_index is None or slot_index >= len(character_ids):
            return candidate, ["Analyzer swap was outside the backend lineup shape; default retained."]
        replacement = swap.get("character_id")
        if replacement in character_ids:
            return candidate, ["Analyzer swap duplicated a backend character; default retained."]
        character_ids[slot_index] = replacement
        replacement_candidate = _revalidate_candidate(candidate_copy, character_ids, bundle)
        if replacement_candidate is None or replacement_candidate.get("score", float("-inf")) < candidate.get("score", float("-inf")):
            warnings.append("Analyzer supplied a lower-scoring or invalid swap; backend default retained.")
        else:
            candidate_copy = replacement_candidate
    selections = refinement.get("skill_selections") or {}
    if selections and _skill_package_score(candidate_copy, selections, bundle) < _skill_package_score(candidate_copy, candidate_copy.get("skill_package_ids", {}), bundle):
        warnings.append("Analyzer supplied a lower-scoring skill package; backend default retained.")
    elif selections:
        candidate_copy["skill_package_ids"] = selections
    candidate_copy["analyzer_refinement"] = {
        "strategy_summary": refinement.get("strategy_summary", ""),
        "explanation": refinement.get("explanation", ""),
        "hero_advice": refinement.get("hero_advice", []),
        "risks": refinement.get("risks", []),
    }
    return candidate_copy, warnings


def _revalidate_candidate(candidate, character_ids, bundle):
    role_scores = bundle.get("backend_role_scores") or {}
    entities = {str(item.get("id")): dict(item) for item in role_scores.get("entities", []) if isinstance(item, dict) and item.get("id")}
    for row in bundle.get("characters", []):
        if row.get("id"):
            entities[str(row["id"])] = {**row, **entities.get(str(row["id"]), {})}
    sidekick_entities = {str(item.get("id")): dict(item) for item in role_scores.get("entities", []) if isinstance(item, dict) and item.get("entity_type") == "sidekick" and item.get("id")}
    result, _ = evaluate_backend_lineup(
        archetype=str(candidate.get("archetype") or "hybrid"),
        character_ids=character_ids,
        sidekick_pair=(candidate.get("main_sidekick_entity_id"), candidate.get("sub_sidekick_entity_id")),
        entities=entities,
        sidekick_entities=sidekick_entities,
        role_scores=role_scores,
        boss=bundle.get("boss", {}),
    )
    return result


def _skill_package_score(candidate, selections, bundle):
    role_entities = {str(item.get("id")): item for item in (bundle.get("backend_role_scores") or {}).get("entities", []) if isinstance(item, dict)}
    total = 0
    for character_id in candidate.get("character_ids", []):
        entity = role_entities.get(character_id, {})
        scores = {}
        for choices in (entity.get("skill_shortlists") or {}).values():
            for choice in choices:
                if choice.get("skill_id"):
                    scores[str(choice["skill_id"])] = max(scores.get(str(choice["skill_id"]), 0), int(choice.get("score") or 0))
        skill_ids = selections.get(character_id, candidate.get("skill_package_ids", {}).get(character_id, []))
        total += sum(scores.get(str(skill_id), 0) for skill_id in skill_ids)
    return total


def _candidate_proposal(candidate, bundle, refinement, *, degraded=False):
    characters = {str(row.get("id")): row for row in bundle.get("characters", [])}
    selections = refinement.get("skill_selections", {}) if refinement else {}
    proposal = {
        "archetype": candidate.get("archetype", "hybrid"),
        "frontline": [_hero_proposal(character_id, candidate, characters, selections) for character_id in candidate.get("frontline_character_ids", [])],
        "reserve": [_hero_proposal(character_id, candidate, characters, selections) for character_id in candidate.get("reserve_character_ids", [])],
        "main_sidekick_id": candidate.get("main_sidekick_id"),
        "sub_sidekick_id": candidate.get("sub_sidekick_id"),
        "strategy_summary": (refinement or {}).get("strategy_summary") or f"Use the deterministic {candidate.get('archetype', 'hybrid')} backend candidate.",
        "key_facts": ["Lineup legality and backend capability coverage are deterministic."],
        "build_notes": ["Use the backend-selected build package; item ownership remains unverified."],
        "boss_counterplay_notes": ["Use the supplied boss affinity and mechanics facts."],
        "sustain_mp_notes": ["Adjust rotation for the supplied sustain and MP facts."],
        "risks": list((refinement or {}).get("risks") or candidate.get("assumptions") or ["Analyzer advice is advisory; backend legality remains authoritative."]),
        "fit_label": _fit_label(candidate),
        "confidence_label": "low" if degraded else _confidence_label(candidate),
        "rubric_summary": {key: _score_label(value) for key, value in candidate.get("component_scores", {}).items()},
        "synergy_explanation": (refinement or {}).get("explanation") or "Backend role assignments and build packages were retained after validation.",
        "citation_ids": [item.get("id") for item in bundle.get("boss", {}).get("citations", []) if item.get("id")],
        "boss_fact_ids": [item.get("id") for item in bundle.get("boss", {}).get("facts", []) if item.get("id")],
    }
    return proposal


def _hero_proposal(character_id, candidate, characters, selections):
    row = characters[character_id]
    package = row.get("build_package") or {}
    weapon_id = package.get("weapon_id") or _nested_id(package.get("weapon")) or row.get("weapon_options", [{}])[0].get("id")
    armor_id = package.get("armor_id") or _nested_id(package.get("armor")) or row.get("armor_options", [{}])[0].get("id")
    grasta_ids = list(package.get("grasta_ids") or [_nested_id(item) for item in package.get("grastas", []) if _nested_id(item)])
    if len(grasta_ids) < 3:
        grasta_ids = [item.get("id") for item in row.get("grastas", []) if item.get("id")][:3]
    skill_ids = list(selections.get(character_id) or candidate.get("skill_package_ids", {}).get(character_id) or [item.get("id") for item in row.get("skills", []) if item.get("id")][:3])
    passive_ids = [item.get("id") for item in row.get("passives", []) if item.get("id")][:1]
    assumptions = list(package.get("assumptions") or [])
    for skill in row.get("skills", []):
        if skill.get("id") in skill_ids and skill.get("requires_stellar_awakened"):
            assumptions.append(f"{skill.get('name')} requires Stellar Awakening")
    role_ids = candidate.get("role_assignments", {}).get(character_id, [])
    return {
        "character_id": character_id,
        "role": str(role_ids[0] if role_ids else "backend-selected role"),
        "weapon_id": weapon_id,
        "armor_id": armor_id,
        "grasta_ids": grasta_ids[:3],
        "skill_ids": skill_ids[:4],
        "passive_ids": passive_ids,
        "upgrade_assumptions": assumptions,
    }


def _slot_index(slot):
    if not isinstance(slot, str) or "." not in slot:
        return None
    group, raw_index = slot.split(".", 1)
    try:
        index = int(raw_index)
    except ValueError:
        return None
    if group == "frontline" and 0 <= index < 4:
        return index
    if group == "reserve" and 0 <= index < 2:
        return 4 + index
    return None


def _candidate_generation_version(bundle):
    return (bundle.get("candidate_generation") or {}).get("policy_version")


def _role_scoring_version(bundle):
    return (bundle.get("backend_role_scores") or {}).get("policy_version")


def _build_package_version(bundle):
    for row in bundle.get("characters", []):
        version = (row.get("build_package") or {}).get("version")
        if version:
            return version
    return None


def _effect_tags(value):
    text = str(value or "").casefold()
    return [word for word in ("pain", "poison", "zone", "heal", "restore", "buff", "debuff", "resist", "barrier", "shield", "cleanse", "break", "weakness", "status", "mp", "critical", "fire", "water", "wind", "earth", "thunder", "shade", "crystal") if word in text]


def _nested_id(value):
    return value.get("id") if isinstance(value, dict) else None


def _stable_json_id(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "projection:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _error(code, path, message, allowed_ids):
    return {"code": code, "path": path, "message": message, "allowed_ids": list(allowed_ids)}


def _fit_label(candidate):
    score = float(candidate.get("score") or 0)
    return "high" if score >= 500 else "medium" if score >= 250 else "low"


def _confidence_label(candidate):
    raw = candidate.get("uncertainty") or 0
    uncertainty = int(raw.get("count", 0) if isinstance(raw, dict) else raw)
    return "high" if uncertainty == 0 else "medium" if uncertainty <= 2 else "low"


def _score_label(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "unavailable"
    return "high" if score >= 75 else "medium" if score >= 25 else "low"
