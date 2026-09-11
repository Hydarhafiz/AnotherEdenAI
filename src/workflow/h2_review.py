"""Offline Feature H2 human-readable recommendation review.

H1 deliberately keeps provider diagnostics bounded and compact.  This module
turns that machine-oriented report into a small Markdown review document.  It
can consume an optional sanitized context sidecar when H1 did not contain the
names or boss facts needed for human review; absent evidence is never promoted
to a positive gate result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping


H2_REPORT_VERSION = "feature-h2-review-v1"
H2_DEFAULT_VARIANT = "baseline_a"
H2_INPUT_TOKEN_TARGET = 20_000
H2_DEFAULT_OUTPUT = "/tmp/anothereden-feature-h2-review.md"
REVIEW_STATUSES = ("PASS", "FAIL", "REVIEW", "UNKNOWN")

_AFFINITY_FIELDS = ("weak", "resist", "null", "absorb")
_KNOWN_CAPABILITY_PROVIDERS = {
    "requires_zone": "deploy_zone",
    "requires_pain": "inflict_pain",
    "requires_poison": "inflict_poison",
    "requires_lunatic": "activate_lunatic",
    "requires_af": "af_support",
    "requires_another_force": "__system__",
}
_ROLE_LABELS = {
    "primary_damage": "primary damage",
    "offensive_enablement": "offensive enablement",
    "zone_setup": "zone setup",
    "defense_mitigation": "defense / mitigation",
    "recovery_protection": "recovery / protection",
    "tank_control": "tank / control",
    "mp_sustain": "MP sustain",
    "boss_counter": "boss counter",
    "reserve_utility": "reserve utility",
    "af_support": "Another Force support",
}
_VALIDATION_EXPLANATIONS = {
    "swap.not_allowed": "The analyzer proposed a swap that is not in the backend-authorized swap list.",
    "id.skill": "The analyzer proposed a skill ID that is not available for the selected character.",
    "id.character": "The analyzer proposed a character ID that is not in the supplied character set.",
    "advisory.role": "An advisory used a role value that is not supported by the backend evidence.",
    "provider.empty_output": "The provider returned no structured analyzer object.",
    "structured_output.shape": "The provider response was not the required structured object.",
    "shape.empty": "The response contained no valid ranking or refinement.",
}


@dataclass(frozen=True)
class NameResolver:
    """Resolve bounded report IDs without inventing names."""

    characters: Mapping[str, Mapping[str, Any]]
    skills: Mapping[str, Mapping[str, Any]]
    passives: Mapping[str, Mapping[str, Any]]

    def character(self, identifier: Any) -> str:
        key = str(identifier or "")
        row = self.characters.get(key, {})
        return str(row.get("display_name") or row.get("name") or "Unknown character")

    def skill(self, identifier: Any) -> str:
        key = str(identifier or "")
        row = self.skills.get(key, {})
        return str(row.get("display_name") or row.get("name") or "Unknown skill")

    def passive(self, identifier: Any) -> str:
        key = str(identifier or "")
        row = self.passives.get(key, {})
        return str(row.get("display_name") or row.get("name") or "Unknown passive")


def load_h1_report(path: str | Path) -> dict[str, Any]:
    """Load an H1 report without invoking any production or provider code."""
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load H1 report {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("H1 report must be a JSON object")
    scenarios = value.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("H1 report must contain a scenarios list")
    return value


def load_review_context(path: str | Path) -> dict[str, Any]:
    """Load an optional sanitized context sidecar used for human names/facts."""
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load H2 review context {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("H2 review context must be a JSON object")
    return value


def build_h2_report(
    h1_report: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None = None,
    variant_id: str = H2_DEFAULT_VARIANT,
) -> dict[str, Any]:
    """Build a bounded, machine-readable review model from an H1 report."""
    scenarios = h1_report.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("H1 report must contain a scenarios list")
    context_value = dict(context or {})
    rendered = [
        _review_scenario(row, _scenario_context(context_value, row), variant_id)
        for row in scenarios
        if isinstance(row, Mapping)
    ]
    return {
        "report_version": H2_REPORT_VERSION,
        "source_evaluation_version": h1_report.get("evaluation_version"),
        "purpose": "offline human validation of modeled recommendation evidence",
        "variant": variant_id,
        "h1_operational_finding": (
            "DeepSeek reasoning=none/4k is the provisional operational winner from H1; "
            "this does not establish strategic quality or a production setting change."
        ),
        "bounded_claim": (
            "A lineup may be modeled as viable or well-matched according to supplied "
            "evidence; this report does not prove a gameplay clear."
        ),
        "scenario_count": len(rendered),
        "scenarios": rendered,
        "limitations": [
            "No combat simulator, turn-by-turn damage calculation, or gameplay clear is performed.",
            "Missing boss, character, skill, or elemental-taxonomy evidence remains REVIEW or UNKNOWN.",
            "Projection compression is outside H2 scope; observed input-budget excess is surfaced only.",
        ],
    }


def render_h2_markdown(review: Mapping[str, Any]) -> str:
    """Render the review model as bounded Markdown for a human operator."""
    lines = [
        "# Feature H2 — Human-Readable Recommendation Validation",
        "",
        f"Source evaluation: `{review.get('source_evaluation_version') or 'unknown'}`  ",
        f"Reviewed variant: `{review.get('variant') or H2_DEFAULT_VARIANT}`",
        "",
        "> **Bounded claim:** " + str(review.get("bounded_claim") or ""),
        "",
        "**H1 operational finding:** " + str(review.get("h1_operational_finding") or ""),
        "",
        "This is an offline review artifact. It does not make paid calls, change production settings, or guarantee a boss clear.",
        "",
    ]
    for scenario in review.get("scenarios", []):
        if isinstance(scenario, Mapping):
            lines.extend(_render_scenario(scenario))
    lines.extend(["## Report Limitations", ""])
    for limitation in review.get("limitations", []):
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)


def generate_h2_review(
    h1_report_path: str | Path,
    output_path: str | Path = H2_DEFAULT_OUTPUT,
    *,
    context_path: str | Path | None = None,
    variant_id: str = H2_DEFAULT_VARIANT,
) -> dict[str, Any]:
    """Generate the Markdown artifact and return the bounded review model."""
    h1_report = load_h1_report(h1_report_path)
    context = load_review_context(context_path) if context_path else None
    review = build_h2_report(h1_report, context=context, variant_id=variant_id)
    Path(output_path).write_text(render_h2_markdown(review), encoding="utf-8")
    return review


def _review_scenario(
    scenario: Mapping[str, Any],
    context: Mapping[str, Any],
    variant_id: str,
) -> dict[str, Any]:
    resolver = _resolver(scenario, context)
    candidates = _merge_candidates(scenario, context)
    variant = scenario.get("variants", {}).get(variant_id, {})
    if not isinstance(variant, Mapping):
        variant = {}
    recommendation = variant.get("top_recommendation")
    if not isinstance(recommendation, Mapping):
        recommendation = {}
    selected_id = _selected_candidate_id(variant)
    selected = next((item for item in candidates if item.get("candidate_id") == selected_id), {})
    selected = _merge_mapping(selected, variant.get("selected_top_candidate"))
    selected = _merge_mapping(selected, _candidate_for_context(context, selected_id))
    boss = _merge_mapping(_boss_from_scenario(scenario), context.get("boss"))
    diversity = _candidate_diversity(candidates)
    gates = {
        "damage_affinity": _gate_damage_affinity(selected, boss, context),
        "boss_mechanics": _gate_boss_mechanics(selected, boss, context, resolver),
        "team_synergy": _gate_team_synergy(selected, candidates, recommendation, context, resolver),
        "setup_executability": _gate_setup(selected, context, resolver),
    }
    return {
        "scenario_id": scenario.get("scenario_id") or scenario.get("id") or "unknown",
        "boss": scenario.get("boss") or boss.get("name") or "Unknown boss",
        "source_category": scenario.get("category") or "unclassified",
        "status": scenario.get("status") or "unknown",
        "projection": dict(scenario.get("projection") or {}),
        "boss_profile": _boss_profile(boss, context),
        "backend_candidates": [_render_candidate(item, resolver, context, boss) for item in candidates[:3]],
        "analyzer_recommendation": _recommendation(
            variant, recommendation, selected, selected_id, resolver, candidates
        ),
        "h1_comparison": _comparison_summary(scenario),
        "input_budget": _input_budget(scenario),
        "gates": gates,
        "overall": _overall_viability(gates),
        "candidate_diversity": diversity,
        "manual_review": _manual_review_checklist(),
    }


def _recommendation(
    variant: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    selected: Mapping[str, Any],
    selected_id: str | None,
    resolver: NameResolver,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    attempts = ((variant.get("application_validation") or {}).get("attempts") or [])
    errors = [
        code
        for attempt in attempts
        if isinstance(attempt, Mapping)
        for code in attempt.get("validation_error_codes", [])
        if code
    ]
    provider_errors = [
        item.get("code")
        for item in variant.get("provider_errors", [])
        if isinstance(item, Mapping) and item.get("code")
    ]
    ranking = list(variant.get("ranking") or [])
    return {
        "selected_candidate_id": selected_id,
        "selected_candidate_label": _candidate_label(selected, candidates, selected_id),
        "selected_candidate": _candidate_title(selected, resolver),
        "ranking": [_candidate_name(candidate_id, candidates) for candidate_id in ranking[:3]],
        "strategy_summary": _text(recommendation.get("strategy_summary"), "No strategy summary supplied."),
        "selected_skills": _selected_skills(recommendation, selected, resolver),
        "swap_decisions": [_swap_summary(row, resolver) for row in _bounded_list(variant.get("swap_decisions"), 3)],
        "advisories": _bounded_list(variant.get("advisories"), 6),
        "risks": _bounded_list(recommendation.get("risks") or variant.get("risks"), 6),
        "validation": {
            "final_response_valid": bool((variant.get("application_validation") or {}).get("final_response_valid")),
            "result_available": bool((variant.get("application_validation") or {}).get("result_available")),
            "degraded": bool((variant.get("application_validation") or {}).get("degraded")),
            "errors": _unique([*errors, *provider_errors]),
            "plain_language_errors": [_VALIDATION_EXPLANATIONS.get(code, f"Deterministic validation code: {code}") for code in _unique([*errors, *provider_errors])],
        },
    }


def _gate_damage_affinity(
    candidate: Mapping[str, Any],
    boss: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    elements = _primary_damage_elements(candidate, context)
    affinities, known = _affinities(boss)
    if not elements:
        return _gate("UNKNOWN", "Primary damage element/type is not present in the supplied evidence.", [])
    if not known:
        return _gate("UNKNOWN", "Boss Weak/Resist/Null/Absorb evidence is absent or explicitly unknown.", elements)

    classifications = []
    for element in elements:
        classification = _affinity_classification(element, affinities)
        classifications.append({"attribute": element, "result": classification})
    blocked = [row for row in classifications if row["result"] in {"resist", "null", "absorb"}]
    hard_blocked = [row for row in classifications if row["result"] in {"null", "absorb"}]
    positive = [row for row in classifications if row["result"] in {"weak", "neutral"}]
    if hard_blocked:
        status = "FAIL"
        message = "Primary damage includes a nullified or absorbed attribute."
    elif blocked and not positive:
        status = "FAIL"
        message = "All identified primary damage attributes are resisted or worse."
    elif blocked:
        status = "REVIEW"
        message = "The package mixes acceptable and resisted primary damage attributes."
    else:
        status = "PASS"
        message = "Identified primary damage is neutral-or-better against explicit boss affinities."

    relationships = _authoritative_element_relationships(context, elements, boss)
    if relationships:
        message += " Authoritative elemental relationships are shown below."
    else:
        message += " No authoritative native element relationship was supplied."
    return _gate(status, message, classifications, extra={"elemental_relationships": relationships})


def _gate_boss_mechanics(
    candidate: Mapping[str, Any],
    boss: Mapping[str, Any],
    context: Mapping[str, Any],
    resolver: NameResolver,
) -> dict[str, Any]:
    threats = _threats(boss, context)
    if not threats:
        return _gate("UNKNOWN", "No boss threats with authoritative counter requirements were supplied.", [])
    coverage = _candidate_coverage(candidate)
    capabilities = set(_strings(coverage.get("provided_capabilities")))
    rows = []
    for threat in threats[:8]:
        required = _strings(threat.get("required_capabilities") or threat.get("counter_capabilities") or threat.get("capabilities"))
        matched = sorted(set(required) & capabilities)
        evidence = _evidence_for_capabilities(coverage, matched)
        mandatory = bool(threat.get("mandatory") or threat.get("required"))
        if not required:
            status = "UNKNOWN"
            note = "Threat has no explicit counter capability in supplied evidence."
        elif matched:
            status = "PASS"
            note = "Concrete supplied capability evidence matches this threat."
        else:
            status = "FAIL" if mandatory else "REVIEW"
            note = "No supplied lineup capability matches the declared counter requirement."
        rows.append({
            "threat": _threat_label(threat),
            "mandatory": mandatory,
            "required_capabilities": required,
            "matched_capabilities": matched,
            "evidence": evidence,
            "status": status,
            "note": note,
        })
    status = _aggregate_gate_status([row["status"] for row in rows])
    return _gate(status, "Boss threats are evaluated only when their facts are supplied.", rows)


def _gate_team_synergy(
    candidate: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    recommendation: Mapping[str, Any],
    context: Mapping[str, Any],
    resolver: NameResolver,
) -> dict[str, Any]:
    coverage = _candidate_coverage(candidate)
    covered = set(_strings(coverage.get("covered_roles")))
    mandatory = set(_strings(coverage.get("mandatory")))
    missing = set(_strings(coverage.get("missing")))
    roles = sorted(covered, key=str)
    warnings = []
    if "primary_damage" not in covered and "primary_damage" in mandatory:
        return _gate("FAIL", "The selected candidate does not show backend primary-damage coverage.", [])
    if "offensive_enablement" not in covered:
        warnings.append("No offensive-enablement role is visible in the selected candidate.")
    if missing:
        warnings.append("Backend coverage reports missing requirements: " + ", ".join(sorted(missing)))
    if float((candidate.get("component_scores") or {}).get("role_overlap") or 0) > 0:
        warnings.append("Backend scoring reports frontline role overlap.")
    people = _candidate_people(candidate, recommendation, resolver, context)
    if any(item.get("name") == "Unknown character" for item in people):
        warnings.append("One or more selected characters could not be resolved to names.")
    if not people:
        warnings.append("Character placement and purpose are absent from the supplied evidence.")
    win_condition = _win_condition(candidate, covered, recommendation)
    if warnings:
        status = "REVIEW"
    elif not roles:
        status = "UNKNOWN"
    else:
        status = "PASS"
    return _gate(status, "Primary win condition: " + win_condition, people, extra={"roles": roles, "warnings": warnings})


def _gate_setup(candidate: Mapping[str, Any], context: Mapping[str, Any], resolver: NameResolver) -> dict[str, Any]:
    coverage = _candidate_coverage(candidate)
    dependencies = _strings(
        candidate.get("setup_dependencies")
        or coverage.get("setup_dependencies")
        or candidate.get("dependencies")
    )
    if not dependencies:
        return _gate("PASS", "The backend declares no setup dependencies for this candidate.", [])
    providers = context.get("dependency_providers") or candidate.get("dependency_providers") or {}
    capabilities = set(_strings(coverage.get("provided_capabilities")))
    rows = []
    for dependency in dependencies[:10]:
        explicit = providers.get(dependency) if isinstance(providers, Mapping) else None
        required_capability = _KNOWN_CAPABILITY_PROVIDERS.get(dependency)
        if isinstance(explicit, Mapping):
            provider = explicit.get("provider") or explicit.get("character_id")
            provider_name = explicit.get("provider_name") or resolver.character(provider)
            status = str(explicit.get("status") or ("PASS" if provider else "UNKNOWN")).upper()
            evidence = _bounded_list(explicit.get("evidence"), 2)
        elif dependency == "requires_another_force":
            provider_name = "system/player action"
            status = "REVIEW"
            evidence = []
        elif required_capability and required_capability in capabilities:
            provider_name = "Capability present; provider name unavailable"
            status = "REVIEW"
            evidence = _evidence_for_capabilities(coverage, [required_capability])
        elif required_capability:
            provider_name = "none found in supplied candidate evidence"
            status = "FAIL"
            evidence = []
        else:
            provider_name = "unknown"
            status = "UNKNOWN"
            evidence = []
        if status not in REVIEW_STATUSES:
            status = "UNKNOWN"
        rows.append({
            "dependency": dependency,
            "required_capability": required_capability,
            "provider": provider_name,
            "status": status,
            "evidence": evidence,
        })
    return _gate(_aggregate_gate_status([row["status"] for row in rows]), "Every declared setup dependency is mapped conservatively.", rows)


def _candidate_diversity(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {"candidate_count": 0, "status": "UNKNOWN", "warnings": ["No backend candidates were supplied."]}
    character_sets = [frozenset(_strings(item.get("character_ids"))) for item in candidates]
    frontline_sets = [
        frozenset(_strings(item.get("frontline_character_ids")))
        for item in candidates
        if item.get("frontline_character_ids")
    ]
    archetypes = _unique(str(item.get("archetype") or "unknown") for item in candidates)
    score_vectors = [_stable_mapping(item.get("component_scores")) for item in candidates]
    total_scores = [item.get("score") for item in candidates]
    pairwise = []
    for left, right in combinations(character_sets, 2):
        union = left | right
        pairwise.append(round(len(left & right) / len(union), 3) if union else 1.0)
    same_sets = len(set(character_sets)) == 1
    same_scores = len(set(_json_key(value) for value in total_scores)) == 1
    same_components = len(set(score_vectors)) == 1
    order_only = same_sets and len({tuple(_strings(item.get("character_ids"))) for item in candidates}) > 1
    warnings = []
    if same_sets and len(candidates) > 1:
        warnings.append("CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.")
    if same_scores and len(candidates) > 1:
        warnings.append("CANDIDATE_SCORE_WARNING: all candidates have identical total scores.")
    if same_components and len(candidates) > 1:
        warnings.append("CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.")
    if order_only:
        warnings.append("ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.")
    if len(archetypes) > 1 and same_sets and same_components:
        warnings.append("ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.")
    return {
        "candidate_count": len(candidates),
        "unique_character_set_count": len(set(character_sets)),
        "unique_frontline_set_count": len(set(frontline_sets)) if frontline_sets else None,
        "unique_archetype_count": len(archetypes),
        "archetypes": archetypes,
        "identical_total_scores": same_scores,
        "identical_component_score_vectors": same_components,
        "character_set_jaccard": pairwise,
        "ordering_only_or_same_set": order_only,
        "status": "REVIEW" if warnings else "PASS",
        "warnings": warnings,
    }


def _boss_profile(boss: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    affinities, known = _affinities(boss)
    threats = _threats(boss, context)
    return {
        "weak": affinities["weak"],
        "resist": affinities["resist"],
        "null": affinities["null"],
        "absorb": affinities["absorb"],
        "affinity_evidence_status": "PASS" if known else "UNKNOWN",
        "characteristics": _text(boss.get("characteristics"), "Not supplied."),
        "mechanics_text": _text(boss.get("mechanics_text"), "Not supplied."),
        "mechanic_tags": _bounded_list(boss.get("mechanic_tags"), 8),
        "offensive_mechanics": _bounded_list(boss.get("offensive_mechanics") or context.get("offensive_mechanics"), 6),
        "defensive_threats": _bounded_list(boss.get("defensive_threats") or context.get("defensive_threats"), 6),
        "status_effects": _bounded_list(boss.get("status_effects") or context.get("status_effects"), 6),
        "other_mechanics": _bounded_list(boss.get("other_mechanics") or context.get("other_mechanics"), 6),
        "threat_count": len(threats),
        "citations": _bounded_list(boss.get("citations") or context.get("citations"), 4),
    }


def _render_candidate(
    candidate: Mapping[str, Any],
    resolver: NameResolver,
    context: Mapping[str, Any],
    boss: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _merge_mapping(candidate, _candidate_for_context(context, candidate.get("candidate_id")))
    people = _candidate_people(candidate, {}, resolver, context)
    coverage = _candidate_coverage(candidate)
    return {
        "candidate_id": candidate.get("candidate_id"),
        "archetype": candidate.get("archetype") or "unknown",
        "score": candidate.get("score"),
        "boss_matchup_score": (candidate.get("component_scores") or {}).get("boss_matchup"),
        "primary_damage_elements": _primary_damage_elements(candidate, context),
        "boss_affinity_result": _candidate_affinity_result(candidate, boss, context),
        "coverage": {
            "mandatory": _bounded_list(coverage.get("mandatory"), 8),
            "covered_roles": [_ROLE_LABELS.get(role, role) for role in _bounded_list(coverage.get("covered_roles"), 10)],
            "missing": _bounded_list(coverage.get("missing"), 8),
        },
        "frontline": [item for item in people if item.get("placement") == "frontline"],
        "reserve": [item for item in people if item.get("placement") == "reserve"],
        "provided_capabilities": _bounded_list(coverage.get("provided_capabilities"), 10),
        "setup_dependencies": _bounded_list(coverage.get("setup_dependencies"), 8),
        "risks": _bounded_list(candidate.get("risks") or candidate.get("assumptions"), 5),
    }


def _candidate_people(
    candidate: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    resolver: NameResolver,
    context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    front_ids = _strings(candidate.get("frontline_character_ids"))
    reserve_ids = _strings(candidate.get("reserve_character_ids"))
    all_ids = _strings(candidate.get("character_ids"))
    if not front_ids and not reserve_ids and all_ids:
        front_ids, reserve_ids = all_ids[:4], all_ids[4:6]
    rec_rows = {
        str(row.get("character_id")): row
        for key in ("frontline", "reserve")
        for row in (recommendation.get(key) or [])
        if isinstance(row, Mapping) and row.get("character_id")
    }
    context_chars = {
        str(row.get("id") or row.get("character_id")): row
        for row in _records(context.get("characters"))
        if row.get("id") or row.get("character_id")
    }
    result = []
    for placement, ids in (("frontline", front_ids), ("reserve", reserve_ids)):
        for identifier in ids[:4 if placement == "frontline" else 2]:
            rec = rec_rows.get(identifier, {})
            char = context_chars.get(identifier, {})
            name = rec.get("name") or char.get("display_name") or char.get("name") or resolver.character(identifier)
            assignments = candidate.get("role_assignments")
            assignments = assignments if isinstance(assignments, Mapping) else {}
            roles = rec.get("role") or char.get("role_ids") or assignments.get(identifier, [])
            if isinstance(roles, str):
                roles = [roles]
            result.append({
                "character_id": identifier,
                "name": str(name),
                "placement": placement,
                "roles": [_ROLE_LABELS.get(str(role), str(role)) for role in _bounded_list(roles, 4)],
                "why_included": _why_included(char, candidate, identifier),
                "skills": _resolved_skills(rec, char, resolver),
            })
    return result


def _why_included(character: Mapping[str, Any], candidate: Mapping[str, Any], identifier: str) -> str:
    roles = candidate.get("role_assignments", {}).get(identifier, []) if isinstance(candidate.get("role_assignments"), Mapping) else []
    if roles:
        return "Backend role evidence: " + ", ".join(_ROLE_LABELS.get(str(role), str(role)) for role in roles[:4])
    capabilities = _strings(character.get("capabilities") or character.get("provided_capabilities"))
    if capabilities:
        return "Supplied capabilities: " + ", ".join(capabilities[:4])
    return "Purpose evidence unavailable in this report."


def _resolved_skills(recommendation: Mapping[str, Any], character: Mapping[str, Any], resolver: NameResolver) -> list[str]:
    names = _bounded_list(recommendation.get("recommended_skills"), 4)
    if names:
        return [str(value) for value in names]
    skills = character.get("skills") or []
    return [
        str(item.get("name") or item.get("display_name") or resolver.skill(item.get("id")))
        for item in skills[:4]
        if isinstance(item, Mapping)
    ]


def _selected_skills(recommendation: Mapping[str, Any], candidate: Mapping[str, Any], resolver: NameResolver) -> list[str]:
    values = []
    for row in (recommendation.get("frontline") or []) + (recommendation.get("reserve") or []):
        if isinstance(row, Mapping):
            values.extend(_resolved_skills(row, {}, resolver))
    if values:
        return _unique(values)[:12]
    selections = candidate.get("skill_package_ids") or candidate.get("selected_skill_package_ids") or {}
    if isinstance(selections, Mapping):
        for skill_ids in selections.values():
            for skill_id in _bounded_list(skill_ids, 4):
                values.append(resolver.skill(skill_id))
    return _unique(values)[:12]


def _primary_damage_elements(candidate: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    values = []
    for key in ("primary_damage_elements", "damage_elements", "primary_elements"):
        values.extend(_strings(candidate.get(key)))
    coverage = _candidate_coverage(candidate)
    for row in coverage.get("evidence", {}).get("primary_damage", []) if isinstance(coverage.get("evidence"), Mapping) else []:
        if isinstance(row, Mapping):
            values.extend(_strings(row.get("element") or row.get("damage_element")))
    selected_ids = set(_strings(candidate.get("character_ids")))
    for character in _records(context.get("characters")):
        character_id = str(character.get("id") or character.get("character_id") or "")
        if selected_ids and character_id not in selected_ids:
            continue
        for skill in _records(character.get("skills")):
            if skill.get("capability") == "direct_damage" or "primary_damage" in _strings(skill.get("role_ids")):
                values.extend(_strings(skill.get("element") or skill.get("damage_element")))
    return _unique(value for value in values if value and str(value).casefold() not in {"neutral", "non-type"})


def _authoritative_element_relationships(
    context: Mapping[str, Any],
    elements: Iterable[str],
    boss: Mapping[str, Any],
) -> list[dict[str, Any]]:
    relations = context.get("element_relationships") or context.get("elemental_relationships") or []
    if isinstance(relations, Mapping):
        relations = [
            {"attacker": attacker, "defender": defender, "relation": value, "authoritative": True}
            for attacker, defenders in relations.items()
            if isinstance(defenders, Mapping)
            for defender, value in defenders.items()
        ]
    boss_elements = _strings(boss.get("attack_elements") or boss.get("defensive_elements"))
    result = []
    for relation in relations if isinstance(relations, list) else []:
        if not isinstance(relation, Mapping) or relation.get("authoritative") is False:
            continue
        if relation.get("attacker") in elements and (not boss_elements or relation.get("defender") in boss_elements):
            result.append({key: relation.get(key) for key in ("attacker", "defender", "relation", "source_url") if relation.get(key) is not None})
    return result[:4]


def _affinity_classification(element: str, affinities: Mapping[str, list[str]]) -> str:
    normalized = str(element).casefold()
    for field in ("absorb", "null", "resist", "weak"):
        if normalized in {value.casefold() for value in affinities[field]}:
            return field
    return "neutral"


def _affinities(boss: Mapping[str, Any]) -> tuple[dict[str, list[str]], bool]:
    raw = boss.get("affinities") if isinstance(boss.get("affinities"), Mapping) else boss
    result = {}
    known = True
    for field in _AFFINITY_FIELDS:
        values = raw.get(field) if isinstance(raw, Mapping) else None
        state = boss.get(f"{field}_state")
        if not state and isinstance(boss.get("affinity_state"), Mapping):
            state = boss["affinity_state"].get(field)
        if state in {"unknown", "incomplete"} or values is None:
            known = False
        result[field] = [value for value in _strings(values) if value.casefold() not in {"unknown", "incomplete"}]
    if boss.get("affinity_complete") is False or boss.get("weakness_known") is False:
        known = False
    return result, known


def _threats(boss: Mapping[str, Any], context: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = context.get("threats") or context.get("boss_threats") or boss.get("threats") or boss.get("mechanics")
    if not isinstance(raw, list):
        raw = [item for item in (boss.get("facts") or []) if isinstance(item, Mapping) and item.get("counter_capabilities")]
    return [dict(item) for item in raw if isinstance(item, Mapping)][:8]


def _evidence_for_capabilities(coverage: Mapping[str, Any], capabilities: Iterable[str]) -> list[dict[str, Any]]:
    wanted = set(capabilities)
    evidence = coverage.get("evidence") if isinstance(coverage.get("evidence"), Mapping) else {}
    result = []
    for rows in evidence.values():
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, Mapping) and row.get("capability") in wanted:
                result.append({key: row.get(key) for key in ("capability", "fact_id", "evidence_id", "source_url") if row.get(key) is not None})
    return result[:5]


def _candidate_coverage(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    coverage = candidate.get("coverage")
    return coverage if isinstance(coverage, Mapping) else {}


def _candidate_title(candidate: Mapping[str, Any], resolver: NameResolver) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id") or candidate.get("id"),
        "archetype": candidate.get("archetype") or "unknown",
        "score": candidate.get("score"),
    }


def _candidate_name(identifier: Any, candidates: list[dict[str, Any]]) -> str:
    candidate = next((item for item in candidates if item.get("candidate_id") == identifier), None)
    if candidate:
        index = candidates.index(candidate) + 1
        return f"Candidate {index} ({candidate.get('archetype') or 'unknown'})"
    return "Unknown candidate"


def _candidate_label(
    candidate: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    identifier: Any,
) -> str:
    if identifier:
        return _candidate_name(identifier, candidates)
    return "No candidate selected"


def _win_condition(candidate: Mapping[str, Any], covered: set[str], recommendation: Mapping[str, Any]) -> str:
    explicit = recommendation.get("strategy_summary") or candidate.get("win_condition")
    if explicit:
        return _text(explicit, "")
    archetype = str(candidate.get("archetype") or "candidate")
    labels = [_ROLE_LABELS[role] for role in sorted(covered) if role in _ROLE_LABELS]
    return f"{archetype} plan using supplied roles: {', '.join(labels[:6]) or 'role evidence unavailable'}"


def _candidate_affinity_result(
    candidate: Mapping[str, Any],
    boss: Mapping[str, Any],
    context: Mapping[str, Any],
) -> str:
    elements = _primary_damage_elements(candidate, context)
    affinities, known = _affinities(boss)
    if not elements or not known:
        return "UNKNOWN"
    return ", ".join(f"{element}: {_affinity_classification(element, affinities)}" for element in elements)


def _overall_viability(gates: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    statuses = [str(gate.get("status") or "UNKNOWN") for gate in gates.values()]
    if "FAIL" in statuses:
        return {
            "modeled_viability": "REJECT",
            "status": "FAIL",
            "summary": "At least one modeled gate failed; do not treat this candidate as a supported recommendation.",
        }
    if "UNKNOWN" in statuses:
        return {
            "modeled_viability": "LOW",
            "status": "UNKNOWN",
            "summary": "Required evidence is missing or unknown, so modeled viability cannot receive a clean pass.",
        }
    if "REVIEW" in statuses:
        return {
            "modeled_viability": "MEDIUM",
            "status": "REVIEW",
            "summary": "The lineup is plausible under the supplied evidence but still requires human judgment.",
        }
    return {
        "modeled_viability": "HIGH",
        "status": "PASS",
        "summary": "All four modeled gates passed on the supplied evidence; this still does not prove a gameplay clear.",
    }


def _swap_summary(row: Any, resolver: NameResolver) -> dict[str, Any]:
    value = row.get("swap") if isinstance(row, Mapping) and isinstance(row.get("swap"), Mapping) else row
    if not isinstance(value, Mapping):
        return {"summary": _short(value)}
    current = value.get("current_character_id") or value.get("from_character_id")
    replacement = value.get("character_id") or value.get("replacement_character_id") or value.get("alternative_character_id")
    return {
        "slot": value.get("slot") or "unknown slot",
        "from": resolver.character(current) if current else "unknown character",
        "to": resolver.character(replacement) if replacement else "unknown character",
        "candidate_id": row.get("candidate_id") if isinstance(row, Mapping) else None,
    }


def _input_budget(scenario: Mapping[str, Any]) -> dict[str, Any]:
    variants = scenario.get("variants") or {}
    result = {}
    for variant_id, variant in variants.items():
        usage = variant.get("usage") if isinstance(variant, Mapping) else {}
        observed = usage.get("prompt_tokens") if isinstance(usage, Mapping) else None
        result[str(variant_id)] = {
            "target_tokens": H2_INPUT_TOKEN_TARGET,
            "observed_prompt_tokens": observed,
            "status": "UNKNOWN" if observed is None else "PASS" if observed <= H2_INPUT_TOKEN_TARGET else "EXCEEDED",
        }
    return result


def _comparison_summary(scenario: Mapping[str, Any]) -> dict[str, Any]:
    comparison = scenario.get("comparison") or {}
    return {key: comparison.get(key) for key in (
        "both_valid", "same_top_candidate", "same_ranking", "same_swap",
        "candidate_ids_closed_world", "skill_selections_valid", "swap_authorized",
        "token_delta", "cost_delta", "latency_delta_ms",
    ) if key in comparison}


def _manual_review_checklist() -> dict[str, Any]:
    return {
        "gate_1": [
            "Main DPS exploits a weakness or is at least neutral.",
            "No primary DPS damage is resisted, nullified, or absorbed.",
            "Elemental matchup explanation is supported by evidence.",
        ],
        "gate_2": [
            "Major boss damage/mechanics have a supported counter.",
            "Boss-counter roles are backed by actual capabilities and evidence.",
        ],
        "gate_3": [
            "The team's main win condition is understandable.",
            "Support, defensive, and reserve characters have clear purposes.",
        ],
        "gate_4": [
            "Required zone/status/setup can actually be established.",
            "No important dependency is missing or merely assumed.",
        ],
        "verdict_options": ["Strong candidate", "Plausible candidate", "Weak candidate", "Reject"],
    }


def _gate(status: str, summary: str, rows: list[Any], *, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    value = {"status": status if status in REVIEW_STATUSES else "UNKNOWN", "summary": summary, "evidence": rows}
    value.update(dict(extra or {}))
    return value


def _aggregate_gate_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    if "FAIL" in values:
        return "FAIL"
    if "REVIEW" in values:
        return "REVIEW"
    if values and all(value == "PASS" for value in values):
        return "PASS"
    return "UNKNOWN"


def _selected_candidate_id(variant: Mapping[str, Any]) -> str | None:
    selected = variant.get("selected_top_candidate")
    if isinstance(selected, Mapping) and selected.get("candidate_id"):
        return str(selected["candidate_id"])
    ranking = variant.get("ranking") or []
    return str(ranking[0]) if ranking else None


def _merge_candidates(scenario: Mapping[str, Any], context: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = context.get("candidates") or scenario.get("backend_candidate_ranking") or []
    if isinstance(source, Mapping):
        source = list(source.values())
    return [
        _merge_mapping({"candidate_id": item.get("candidate_id") or item.get("id")}, item)
        for item in source[:3]
        if isinstance(item, Mapping) and (item.get("candidate_id") or item.get("id"))
    ]


def _candidate_for_context(context: Mapping[str, Any], candidate_id: Any) -> Mapping[str, Any]:
    candidates = context.get("candidates") or []
    if isinstance(candidates, Mapping):
        candidates = list(candidates.values())
    return next((item for item in candidates if isinstance(item, Mapping) and (item.get("candidate_id") or item.get("id")) == candidate_id), {})


def _boss_from_scenario(scenario: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("boss_facts", "boss_profile", "boss_context", "boss_data"):
        if isinstance(scenario.get(key), Mapping):
            return scenario[key]
    return scenario.get("boss") if isinstance(scenario.get("boss"), Mapping) else {}


def _scenario_context(context: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, Any]:
    inline = scenario.get("review_context") or scenario.get("context")
    if isinstance(inline, Mapping):
        return dict(inline)
    rows = context.get("scenarios")
    scenario_id = scenario.get("scenario_id") or scenario.get("id")
    if isinstance(rows, Mapping) and isinstance(rows.get(scenario_id), Mapping):
        return dict(rows[scenario_id])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping) and (row.get("scenario_id") or row.get("id")) == scenario_id:
                return dict(row)
    return dict(context)


def _resolver(scenario: Mapping[str, Any], context: Mapping[str, Any]) -> NameResolver:
    characters = {}
    skills = {}
    passives = {}
    for source in (context.get("characters"),):
        for row in _records(source):
            identifier = row.get("id") or row.get("character_id")
            if identifier:
                characters[str(identifier)] = row
            for skill in _records(row.get("skills")):
                if skill.get("id"):
                    skills[str(skill["id"])] = skill
            for passive in _records(row.get("passives")):
                if passive.get("id"):
                    passives[str(passive["id"])] = passive
    for row in _recommendation_rows(scenario):
        identifier = row.get("character_id")
        if identifier and row.get("name"):
            characters.setdefault(str(identifier), row)
    return NameResolver(characters, skills, passives)


def _recommendation_rows(scenario: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result = []
    for variant in (scenario.get("variants") or {}).values():
        if not isinstance(variant, Mapping):
            continue
        rec = variant.get("top_recommendation")
        if isinstance(rec, Mapping):
            result.extend(row for key in ("frontline", "reserve") for row in (rec.get(key) or []) if isinstance(row, Mapping))
    return result


def _merge_mapping(left: Any, right: Any) -> dict[str, Any]:
    result = dict(left) if isinstance(left, Mapping) else {}
    if isinstance(right, Mapping):
        result.update(right)
    return result


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        return [dict(row, id=key) if isinstance(row, Mapping) else {"id": key, "name": row} for key, row in value.items()]
    return [dict(row) for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _render_scenario(scenario: Mapping[str, Any]) -> list[str]:
    lines = [
        f"# {scenario.get('scenario_id')} — {scenario.get('boss')}",
        "",
        f"Source status: `{scenario.get('status')}`  ",
        f"Category: `{scenario.get('source_category')}`",
        "",
        "## Boss Profile",
        "",
    ]
    profile = scenario.get("boss_profile") or {}
    for label in ("weak", "resist", "null", "absorb"):
        lines.append(f"- **{label.title()}:** {_join_or_unknown(profile.get(label))}")
    lines.append(f"- **Affinity evidence:** `{profile.get('affinity_evidence_status')}`")
    lines.append(f"- **Characteristics:** {profile.get('characteristics')}")
    lines.append(f"- **Mechanics:** {profile.get('mechanics_text')}")
    for label, key in (
        ("Offensive mechanics", "offensive_mechanics"),
        ("Defensive threats", "defensive_threats"),
        ("Status effects", "status_effects"),
        ("Other mechanics", "other_mechanics"),
    ):
        lines.append(f"- **{label}:** {_join_or_unknown(profile.get(key))}")
    lines.append("")

    lines.extend(["## Backend Candidates", ""])
    for index, candidate in enumerate(scenario.get("backend_candidates") or [], start=1):
        lines.extend(_render_candidate_markdown(index, candidate))
    if not scenario.get("backend_candidates"):
        lines.extend(["No backend candidates were supplied.", ""])

    rec = scenario.get("analyzer_recommendation") or {}
    validation = rec.get("validation") or {}
    lines.extend([
        "## Analyzer Recommendation",
        "",
        f"Selected candidate: **{rec.get('selected_candidate_label') or 'none'}**",
        f"Ranking: {', '.join(rec.get('ranking') or ['unavailable'])}",
        f"Strategy summary: {rec.get('strategy_summary')}",
        f"Validation: `{ 'PASS' if validation.get('final_response_valid') else 'FAIL' }`",
    ])
    if not validation.get("final_response_valid"):
        lines.append("**Analyzer recommendation rejected by deterministic validator.**")
    for error in validation.get("plain_language_errors") or []:
        lines.append(f"- {error}")
    lines.append(f"Selected skills: {_join_or_unknown(rec.get('selected_skills'))}")
    lines.append(f"Proposed swaps: {_swap_text(rec.get('swap_decisions'))}")
    lines.append(f"Advisories: {_join_or_unknown(rec.get('advisories'))}")
    lines.append(f"Risks: {_join_or_unknown(rec.get('risks'))}")
    lines.append("")

    lines.extend(["## H1 Comparison And Input Budget", ""])
    for key, value in (scenario.get("h1_comparison") or {}).items():
        lines.append(f"- **{key}:** `{value}`")
    for variant, budget in (scenario.get("input_budget") or {}).items():
        lines.append(f"- **Analyzer input budget ({variant}):** target <= {budget.get('target_tokens')} tokens; observed {budget.get('observed_prompt_tokens') or 'unavailable'}; status `{budget.get('status')}`")
    lines.append("")

    lines.extend(["## Four-Gate Review", ""])
    for title, key in (("Damage Affinity / Elemental Viability", "damage_affinity"), ("Boss Mechanic Counter Coverage", "boss_mechanics"), ("Team Synergy / Role Coherence", "team_synergy"), ("Setup Executability", "setup_executability")):
        gate = scenario.get("gates", {}).get(key) or {}
        lines.append(f"### Gate — {title}: `{gate.get('status', 'UNKNOWN')}`")
        lines.append("")

        lines.append(str(gate.get("summary") or "No summary supplied."))
        lines.extend(_render_gate_rows(gate.get("evidence") or []))
        if gate.get("warnings"):
            lines.extend(["Warnings:", "", *[f"- {item}" for item in gate["warnings"]]])
        lines.append("")

    overall = scenario.get("overall") or {}
    lines.extend([
        "## Overall Modeled Viability",
        "",
        f"**{overall.get('modeled_viability', 'UNKNOWN')}** (`{overall.get('status', 'UNKNOWN')}`)",
        "",
        str(overall.get("summary") or "No overall conclusion can be made."),
        "",
    ])

    diversity = scenario.get("candidate_diversity") or {}
    lines.extend(["## Candidate Diversity Audit", "", f"- Candidates: `{diversity.get('candidate_count', 0)}`", f"- Unique character sets: `{diversity.get('unique_character_set_count', 'unknown')}`", f"- Unique frontline sets: `{diversity.get('unique_frontline_set_count', 'unknown')}`", f"- Unique archetypes: `{diversity.get('unique_archetype_count', 'unknown')}`", f"- Identical total scores: `{diversity.get('identical_total_scores', 'unknown')}`", f"- Identical component scores: `{diversity.get('identical_component_score_vectors', 'unknown')}`", f"- Character-set Jaccard values: `{diversity.get('character_set_jaccard') or 'unavailable'}`", ""])
    lines.extend([*(f"- {warning}" for warning in diversity.get("warnings") or []), ""])

    lines.extend([
        "## Manual Review",
        "",
        "Check only what the supplied evidence supports:",
        "",
        "- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.",
        "- [ ] Gate 2: important boss threats have concrete, evidenced counters.",
        "- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.",
        "- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.",
        "- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.",
        "",
        "Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**",
        "",
        "Notes: ________________________________________________________________",
        "",
    ])
    return lines


def _render_candidate_markdown(index: int, candidate: Mapping[str, Any]) -> list[str]:
    lines = [
        f"### Candidate {index} — {candidate.get('archetype')}",
        "",
        f"Score: `{candidate.get('score')}`; boss matchup component: `{candidate.get('boss_matchup_score')}`",
        f"Mandatory roles: {_join_or_unknown((candidate.get('coverage') or {}).get('mandatory'))}",
        f"Covered roles: {_join_or_unknown((candidate.get('coverage') or {}).get('covered_roles'))}",
        f"Missing roles: {_join_or_unknown((candidate.get('coverage') or {}).get('missing'))}",
        f"Primary damage: {_join_or_unknown(candidate.get('primary_damage_elements'))}; boss affinity: `{candidate.get('boss_affinity_result')}`",
        f"Frontline: {_people_text(candidate.get('frontline'))}",
        f"Reserve: {_people_text(candidate.get('reserve'))}",
        f"Capabilities: {_join_or_unknown(candidate.get('provided_capabilities'))}",
        f"Setup dependencies: {_join_or_unknown(candidate.get('setup_dependencies'))}",
        f"Risks: {_join_or_unknown(candidate.get('risks'))}",
        "",
    ]
    return lines


def _render_gate_rows(rows: list[Any]) -> list[str]:
    if not rows:
        return ["", "Evidence: unavailable."]
    lines = ["", "| Evidence item | Status | Supporting detail |", "| --- | --- | --- |"]
    for row in rows[:8]:
        if isinstance(row, Mapping):
            label = row.get("threat") or row.get("dependency") or row.get("attribute") or row.get("capability") or "Evidence"
            status = row.get("status") or "REVIEW"
            detail = row.get("note") or row.get("provider") or row.get("result") or row.get("evidence") or row.get("matched_capabilities") or ""
        else:
            label, status, detail = str(row), "REVIEW", ""
        if isinstance(row, Mapping) and row.get("evidence"):
            evidence = _short(row.get("evidence"))
            detail = f"{detail}; evidence: {evidence}" if detail else f"evidence: {evidence}"
        lines.append(f"| {_md(label)} | `{_md(status)}` | {_md(_short(detail))} |")
    return lines


def _people_text(rows: Any) -> str:
    values = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, Mapping):
            role = ", ".join(row.get("roles") or [])
            values.append(f"{row.get('name') or 'Unknown character'} ({role or 'purpose unknown'})")
    return "; ".join(values) or "unknown"


def _swap_text(rows: Any) -> str:
    values = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            values.append(_short(row))
            continue
        values.append(f"{row.get('slot', 'unknown slot')}: {row.get('from', 'unknown character')} → {row.get('to', 'unknown character')}")
    return "; ".join(values) or "none reported"


def _text(value: Any, default: str) -> str:
    text = " ".join(str(value or "").split())
    return text[:2_000] if text else default


def _short(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_short(item) for item in list(value)[:5])
    if isinstance(value, Mapping):
        return "; ".join(f"{key}={_short(item)}" for key, item in list(value.items())[:5])
    return _text(value, "")[:400]


def _join_or_unknown(value: Any) -> str:
    values = _bounded_list(value, 8)
    return ", ".join(str(item) for item in values) if values else "unknown / not supplied"


def _bounded_list(value: Any, limit: int) -> list[Any]:
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, tuple):
        return list(value[:limit])
    return []


def _strings(value: Any) -> list[str]:
    values = value if isinstance(value, (list, tuple, set)) else [value] if value else []
    return [str(item) for item in values if item is not None and str(item)]


def _unique(values: Iterable[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        key = _json_key(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _stable_mapping(value: Any) -> str:
    return _json_key(value if isinstance(value, Mapping) else {})


def _json_key(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    except TypeError:
        return str(value)


def _threat_label(threat: Mapping[str, Any]) -> str:
    return str(threat.get("label") or threat.get("name") or threat.get("threat") or threat.get("kind") or "Unnamed boss threat")


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


__all__ = [
    "H2_DEFAULT_OUTPUT",
    "H2_INPUT_TOKEN_TARGET",
    "H2_REPORT_VERSION",
    "build_h2_report",
    "generate_h2_review",
    "load_h1_report",
    "load_review_context",
    "render_h2_markdown",
]
