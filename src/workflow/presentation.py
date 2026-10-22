"""Bounded evidence projection for already validated recommendation output.

This module only joins the final displayed character/skill IDs to existing
retrieval and candidate diagnostics. It does not rank candidates or infer new
combat capabilities.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceSource(BaseModel):
    label: str
    source_url: str | None = None


class ReviewedEffect(BaseModel):
    capability: str
    direction: str = ""
    target: str = ""
    trigger: str = ""
    matched_phrase: str = ""
    source_id: str = ""
    source_fact_id: str = ""
    review_decision: str = ""
    artifact_version: str = ""
    review_artifact_version: str = ""


class SelectedSkillEvidence(BaseModel):
    character_id: str
    character_name: str
    skill_id: str
    skill_name: str
    placement: Literal["frontline", "reserve_after_switch"]
    review_status: Literal[
        "reviewed",
        "no_reviewed_capability_evidence",
        "unavailable",
    ]
    source: EvidenceSource | None = None
    reviewed_effects: list[ReviewedEffect] = Field(default_factory=list)
    proposal_counts: dict[str, int | None] = Field(default_factory=dict)


class CandidateEvidence(BaseModel):
    status: Literal["available", "unavailable"]
    note: str
    modeled_roles: dict[str, list[str]] = Field(default_factory=dict)
    modeled_coverage_gaps: list[str] = Field(default_factory=list)
    component_scores: dict[str, int | float] = Field(default_factory=dict)
    component_score_scope: dict[str, str] = Field(default_factory=dict)
    scorer_uncertainty_count: int | None = None
    scorer_uncertainty_scope: str | None = None
    selected_skill_matchups: list[dict[str, Any]] = Field(default_factory=list)
    selected_skill_matchups_unavailable: bool = False


class PresentationWarning(BaseModel):
    code: str
    title: str
    message: str
    sources: list[EvidenceSource] = Field(default_factory=list)


class RecommendationPresentation(BaseModel):
    selected_skill_evidence_status: Literal["available", "partial", "unavailable"]
    selected_skill_count: int | None = None
    joined_skill_count: int = 0
    skills_with_reviewed_capabilities: int | None = None
    unreviewed_proposal_count: int | None = None
    skills_without_reviewed_capabilities: list[dict[str, str]] = Field(default_factory=list)
    selected_skills: list[SelectedSkillEvidence] = Field(default_factory=list)
    source_effect_coverage: Literal["not_established"] = "not_established"
    candidate: CandidateEvidence
    warnings: list[PresentationWarning] = Field(default_factory=list)


class BossAffinityEvidence(BaseModel):
    dimension: Literal["weak", "resist", "null", "absorb"]
    values: list[str] = Field(default_factory=list)
    state: str = "unavailable"


class RequestCoverageEvidence(BaseModel):
    status: Literal["available", "unavailable"]
    metrics: dict[str, int | float] = Field(default_factory=dict)
    unknown_data: dict[str, int | float] = Field(default_factory=dict)
    note: str


class ResultPresentation(BaseModel):
    mode: Literal["production", "exploratory", "unknown"] = "unknown"
    boss_name: str | None = None
    boss_source: EvidenceSource | None = None
    boss_affinities: list[BossAffinityEvidence] = Field(default_factory=list)
    request_coverage: RequestCoverageEvidence
    explanation_limit: str


_AFFINITY_DIMENSIONS = ("weak", "resist", "null", "absorb")
_COVERAGE_METRICS = (
    "user_roster_count",
    "f2p_augmented_count",
    "distinct_available_count",
    "data_complete_count",
    "boss_eligible_count",
    "role_pool_union_count",
    "candidate_count",
    "unique_character_set_count",
    "unique_frontline_set_count",
    "unique_archetype_count",
)
_REVIEWED_DECISIONS = {"approve", "correct", "proven"}


def build_result_presentation(state: dict[str, Any]) -> dict[str, Any]:
    """Project boss and request diagnostics for the rendered result view."""
    retrieval = _mapping(state.get("typed_retrieval"))
    boss = _mapping(retrieval.get("boss"))
    boss_name = _nonempty_string(boss.get("name"))
    boss_source_url = _nonempty_string(boss.get("source_url") or boss.get("citation_url"))

    affinities = []
    for dimension in _AFFINITY_DIMENSIONS:
        raw_values = boss.get(dimension)
        values = sorted(
            {str(value).strip() for value in raw_values if str(value).strip()}
        ) if isinstance(raw_values, list) else []
        state_value = _nonempty_string(boss.get(f"{dimension}_state")) or "unavailable"
        affinities.append(BossAffinityEvidence(
            dimension=dimension,
            values=values,
            state=state_value,
        ))

    coverage = _mapping(retrieval.get("request_coverage"))
    raw_metrics = _mapping(coverage.get("metrics"))
    metrics = _numeric_fields(raw_metrics, _COVERAGE_METRICS)
    unknown_data = _numeric_mapping(coverage.get("unknown_data"))
    has_coverage = bool(coverage.get("report_type")) and bool(raw_metrics)
    request_coverage = RequestCoverageEvidence(
        status="available" if has_coverage else "unavailable",
        metrics=metrics,
        unknown_data=unknown_data,
        note=(
            "Counts describe request retrieval and the deterministic search pool before final analyzer and graph-legality filtering. "
            "They do not measure reviewed source-effect coverage."
            if has_coverage
            else "Request coverage diagnostics were not supplied for this result."
        ),
    )
    return ResultPresentation(
        mode=(
            str(state.get("workflow_mode"))
            if state.get("workflow_mode") in {"production", "exploratory"}
            else "unknown"
        ),
        boss_name=boss_name,
        boss_source=(EvidenceSource(label=f"{boss_name} source", source_url=boss_source_url)
                     if boss_source_url else None),
        boss_affinities=affinities,
        request_coverage=request_coverage,
        explanation_limit=(
            "Fit and component labels are internal heuristic ranking signals. Confidence reflects only uncertainty represented by the scorer. "
            "Neither is a measure of battle strength, complete boss-counter coverage, source completeness, or win likelihood."
        ),
    ).model_dump()


def build_recommendation_presentation(
    recommendation: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Join source/review facts and candidate diagnostics to final displayed IDs."""
    retrieval = _mapping(state.get("typed_retrieval"))
    raw_skills = [
        item for item in retrieval.get("skills", []) if isinstance(item, dict)
    ]
    selected_skills, selected_count = _selected_skill_evidence(recommendation, raw_skills)
    joined_count = sum(skill.review_status != "unavailable" for skill in selected_skills)
    if selected_count is None or selected_count == 0:
        evidence_status = "partial" if selected_skills else "unavailable"
        reviewed_skill_count = None
    else:
        evidence_status = "available" if joined_count == selected_count else "partial"
        reviewed_skill_count = sum(
            bool(skill.reviewed_effects) for skill in selected_skills
        )

    diagnostics_available = all(
        skill.review_status != "unavailable" for skill in selected_skills
    ) and bool(selected_skills)
    unreviewed_count = (
        sum(skill.proposal_counts.get("unreviewed") or 0 for skill in selected_skills)
        if diagnostics_available
        and all(skill.proposal_counts.get("unreviewed") is not None for skill in selected_skills)
        else None
    )
    without_reviewed = [
        {"skill_name": skill.skill_name, "character_name": skill.character_name, "placement": skill.placement}
        for skill in selected_skills
        if skill.review_status == "no_reviewed_capability_evidence"
    ]

    candidate = _exact_backend_candidate(recommendation, state)
    candidate_evidence = _candidate_evidence(candidate, recommendation)
    warnings = _candidate_warnings(recommendation, selected_skills, state)
    return RecommendationPresentation(
        selected_skill_evidence_status=evidence_status,
        selected_skill_count=selected_count,
        joined_skill_count=joined_count,
        skills_with_reviewed_capabilities=reviewed_skill_count,
        unreviewed_proposal_count=unreviewed_count,
        skills_without_reviewed_capabilities=without_reviewed,
        selected_skills=selected_skills,
        candidate=candidate_evidence,
        warnings=warnings,
    ).model_dump()


def _selected_skill_evidence(
    recommendation: dict[str, Any],
    raw_skills: list[dict[str, Any]],
) -> tuple[list[SelectedSkillEvidence], int | None]:
    by_identity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for skill in raw_skills:
        skill_id = _skill_id(skill)
        character_id = _nonempty_string(skill.get("character_id"))
        if skill_id and character_id:
            by_identity.setdefault((character_id, skill_id), []).append(skill)

    selected: list[SelectedSkillEvidence] = []
    selected_count = 0
    missing_identity = False
    for placement, heroes in (
        ("frontline", recommendation.get("frontline", [])),
        ("reserve_after_switch", recommendation.get("reserve", [])),
    ):
        for hero in heroes:
            if not isinstance(hero, dict):
                continue
            character_id = _nonempty_string(hero.get("character_id"))
            skill_ids = hero.get("selected_skill_ids")
            if not character_id or not isinstance(skill_ids, list) or not skill_ids:
                missing_identity = True
                continue
            names = hero.get("recommended_skills")
            names = names if isinstance(names, list) else []
            selected_count += len(skill_ids)
            for index, raw_skill_id in enumerate(skill_ids):
                skill_id = _nonempty_string(raw_skill_id)
                if not skill_id:
                    missing_identity = True
                    continue
                matches = by_identity.get((character_id, skill_id), [])
                skill = matches[0] if len(matches) == 1 else None
                selected.append(_project_skill(
                    character_id=character_id,
                    character_name=str(hero.get("name") or "Unknown character"),
                    skill_id=skill_id,
                    fallback_name=(str(names[index]) if index < len(names) and names[index] else skill_id),
                    placement=placement,
                    skill=skill,
                ))

    if missing_identity:
        selected_count_value = None
    elif not selected_count:
        selected_count_value = None
    else:
        selected_count_value = selected_count
    return selected, selected_count_value


def _project_skill(
    *,
    character_id: str,
    character_name: str,
    skill_id: str,
    fallback_name: str,
    placement: str,
    skill: dict[str, Any] | None,
) -> SelectedSkillEvidence:
    if skill is None:
        return SelectedSkillEvidence(
            character_id=character_id,
            character_name=character_name,
            skill_id=skill_id,
            skill_name=fallback_name,
            placement=placement,
            review_status="unavailable",
        )

    diagnostics = _decode_mapping(skill.get("capability_diagnostics_json", skill.get("capability_diagnostics")))
    raw_evidence = _decode_list(skill.get("capability_evidence_json", skill.get("capability_evidence")))
    capabilities = {str(value) for value in skill.get("capabilities", []) if value}
    reviewed = [
        row for row in raw_evidence
        if isinstance(row, dict)
        and row.get("kind") == "capability"
        and str(row.get("value") or "") in capabilities
        and str(row.get("source_fact_id") or "") == skill_id
        and str(row.get("review_decision") or "").casefold() in _REVIEWED_DECISIONS
    ]
    effects = [
        ReviewedEffect(
            capability=str(row["value"]),
            direction=str(row.get("direction") or ""),
            target=str(row.get("target") or ""),
            trigger=str(row.get("trigger") or ""),
            matched_phrase=str(row.get("matched_phrase") or ""),
            source_id=str(row.get("source_id") or ""),
            source_fact_id=str(row.get("source_fact_id") or ""),
            review_decision=str(row.get("review_decision") or ""),
            artifact_version=str(row.get("artifact_version") or ""),
            review_artifact_version=str(row.get("review_artifact_version") or ""),
        )
        for row in reviewed
    ]
    has_diagnostics = bool(diagnostics)
    review_status = (
        "reviewed" if effects
        else "no_reviewed_capability_evidence" if has_diagnostics
        else "unavailable"
    )
    counts = {}
    if has_diagnostics:
        for output_key, input_key in (
            ("proposed", "proposed"),
            ("reviewed", "reviewed"),
            ("proven", "proven"),
            ("unreviewed", "candidate"),
        ):
            counts[output_key] = _optional_int(diagnostics.get(input_key))
    source_url = _nonempty_string(skill.get("source_url"))
    return SelectedSkillEvidence(
        character_id=character_id,
        character_name=character_name,
        skill_id=skill_id,
        skill_name=str(skill.get("name") or fallback_name),
        placement=placement,
        review_status=review_status,
        source=EvidenceSource(label=f"{skill.get('name') or fallback_name} source", source_url=source_url) if source_url else None,
        reviewed_effects=effects,
        proposal_counts=counts,
    )


def _exact_backend_candidate(
    recommendation: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any] | None:
    bundle = _mapping(state.get("candidate_bundle"))
    candidates = bundle.get("backend_candidates")
    if not isinstance(candidates, list):
        candidates = _mapping(bundle.get("candidate_generation")).get("candidates", [])
    heroes = [
        hero
        for group in (recommendation.get("frontline", []), recommendation.get("reserve", []))
        for hero in group if isinstance(hero, dict)
    ]
    final_ids = [str(hero.get("character_id") or "") for hero in heroes]
    if len(final_ids) != 6 or any(not value for value in final_ids):
        return None
    final_skills = {
        str(hero.get("character_id")): list(hero.get("selected_skill_ids") or [])
        for hero in heroes
    }
    for candidate in candidates if isinstance(candidates, list) else []:
        if not isinstance(candidate, dict) or candidate.get("character_ids") != final_ids:
            continue
        candidate_skills = candidate.get("skill_package_ids") or {}
        if all(candidate_skills.get(character_id) == final_skills[character_id] for character_id in final_ids):
            return candidate
    return None


def _candidate_evidence(
    candidate: dict[str, Any] | None,
    recommendation: dict[str, Any],
) -> CandidateEvidence:
    if candidate is None:
        return CandidateEvidence(
            status="unavailable",
            note=(
                "No backend diagnostic has the exact final character order and equipped skill IDs. "
                "This can happen after a permitted refinement or swap; earlier diagnostics are not reused."
            ),
            selected_skill_matchups_unavailable=True,
        )
    coverage = _mapping(candidate.get("coverage"))
    roles_by_placement = _mapping(coverage.get("roles_by_character_placement"))
    component_scores = {
        str(key): value for key, value in _mapping(candidate.get("component_scores")).items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    scopes = {
        str(key): str(value) for key, value in _mapping(candidate.get("component_score_scope")).items()
        if value
    }
    uncertainty = _mapping(candidate.get("uncertainty"))
    evidence_diagnostics = _mapping(candidate.get("evidence_diagnostics"))
    count = _optional_int(evidence_diagnostics.get("scorer_uncertainty_count"))
    matchups = _selected_skill_matchups(candidate, recommendation)
    return CandidateEvidence(
        status="available",
        note=(
            "These diagnostics match the final validated character order and equipped skill IDs. "
            "They summarize deterministic ranking inputs, not complete boss-counter or battle validation."
        ),
        modeled_roles={
            "frontline": _string_list(roles_by_placement.get("frontline")),
            "reserve_after_switch": _string_list(roles_by_placement.get("reserve_after_switch")),
        },
        modeled_coverage_gaps=_string_list(coverage.get("missing")),
        component_scores=component_scores,
        component_score_scope=scopes,
        scorer_uncertainty_count=count,
        scorer_uncertainty_scope=(
            str(evidence_diagnostics.get("scorer_uncertainty_scope") or "")
            or (str(uncertainty.get("scope")) if uncertainty.get("scope") else None)
        ),
        selected_skill_matchups=matchups,
        selected_skill_matchups_unavailable=not bool(matchups),
    )


def _selected_skill_matchups(
    candidate: dict[str, Any],
    recommendation: dict[str, Any],
) -> list[dict[str, Any]]:
    packages = _mapping(candidate.get("skill_packages"))
    result = []
    for placement, heroes in (
        ("frontline", recommendation.get("frontline", [])),
        ("reserve_after_switch", recommendation.get("reserve", [])),
    ):
        for hero in heroes:
            if not isinstance(hero, dict):
                continue
            character_id = str(hero.get("character_id") or "")
            selected_ids = {
                str(value): index
                for index, value in enumerate(hero.get("selected_skill_ids") or [])
            }
            package = _mapping(packages.get(character_id))
            for matchup in package.get("damage_matchups", []):
                if not isinstance(matchup, dict):
                    continue
                skill_id = str(matchup.get("fact_id") or "")
                evidence_ids = _string_list(matchup.get("evidence_ids"))
                if (
                    skill_id not in selected_ids
                    or not evidence_ids
                    or matchup.get("state") not in {"weak", "resisted", "blocked", "neutral"}
                ):
                    continue
                result.append({
                    "character_name": str(hero.get("name") or "Unknown character"),
                    "skill_id": skill_id,
                    "skill_name": _selected_skill_name(hero, selected_ids[skill_id], skill_id),
                    "placement": placement,
                    "elements": _string_list(matchup.get("element")),
                    "attack_types": _string_list(matchup.get("attack_type")),
                    "state": str(matchup["state"]),
                    "evidence_ids": evidence_ids,
                })
    return result


def _selected_skill_name(hero: dict[str, Any], index: int, skill_id: str) -> str:
    names = hero.get("recommended_skills")
    return str(names[index]) if isinstance(names, list) and index < len(names) else skill_id


def _candidate_warnings(
    recommendation: dict[str, Any],
    selected_skills: list[SelectedSkillEvidence],
    state: dict[str, Any],
) -> list[PresentationWarning]:
    retrieval = _mapping(state.get("typed_retrieval"))
    boss = _mapping(retrieval.get("boss"))
    boss_id = str(boss.get("id") or _mapping(retrieval.get("request")).get("boss_id") or "").casefold()
    boss_name = str(boss.get("name") or "the selected boss")
    boss_url = _nonempty_string(boss.get("source_url") or boss.get("citation_url"))
    warnings: list[PresentationWarning] = []

    venom = [
        skill for skill in selected_skills
        if skill.character_name.casefold() == "toova"
        and skill.skill_name.casefold() == "venom"
        and skill.review_status == "reviewed"
    ]
    venom_effects = {
        effect.capability
        for skill in venom for effect in skill.reviewed_effects
    }
    if boss_id == "celestial-mushroom" and venom and venom_effects & {"inflict_pain", "inflict_poison"}:
        ailments = [
            label for capability, label in (
                ("inflict_pain", "Pain"),
                ("inflict_poison", "Poison"),
            )
            if capability in venom_effects
        ]
        names = " and ".join(ailments)
        sources = _unique_sources([
            *[_skill_source(skill) for skill in venom],
            EvidenceSource(label=f"{boss_name} source", source_url=boss_url) if boss_url else None,
        ])
        warnings.append(PresentationWarning(
            code="venom_mushroom_harm",
            title="Known harmful interaction",
            message=(
                f"Toova's Venom applies {names}. Against Celestial Mushroom, those ailments raise its resistance; "
                "the boss clears them and heals at turn end."
            ),
            sources=sources,
        ))

    zone_skills = [
        skill for skill in selected_skills
        if skill.review_status == "reviewed"
        and {effect.capability for effect in skill.reviewed_effects} & {"deploy_zone", "awaken_zone"}
    ]
    if len({skill.skill_id for skill in zone_skills}) > 1:
        names = ", ".join(dict.fromkeys(skill.skill_name for skill in zone_skills))
        warnings.append(PresentationWarning(
            code="alternative_zone_options",
            title="Alternative Zone options",
            message=(
                f"The selected skill packages include these Zone options: {names}. "
                "This result does not set an activation order or claim that multiple Zones are active together."
            ),
            sources=_unique_sources([_skill_source(skill) for skill in zone_skills]),
        ))

    reserve_skills = [skill for skill in selected_skills if skill.placement == "reserve_after_switch"]
    if reserve_skills:
        warnings.append(PresentationWarning(
            code="reserve_requires_switch",
            title="Reserve skills require switching",
            message=(
                "The listed active skills for reserve characters are options after switching them into the frontline; "
                "they are not active frontline support while those characters remain in reserve."
            ),
            sources=_unique_sources([_skill_source(skill) for skill in reserve_skills]),
        ))
    return warnings


def _skill_source(skill: SelectedSkillEvidence) -> EvidenceSource | None:
    return skill.source


def _unique_sources(sources: list[EvidenceSource | None]) -> list[EvidenceSource]:
    result = []
    seen = set()
    for source in sources:
        if source is None:
            continue
        identity = (source.label, source.source_url)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(source)
    return result


def _decode_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _decode_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _numeric_fields(value: dict[str, Any], keys: tuple[str, ...]) -> dict[str, int | float]:
    return {
        key: value[key] for key in keys
        if isinstance(value.get(key), (int, float)) and not isinstance(value.get(key), bool)
    }


def _numeric_mapping(value: Any) -> dict[str, int | float]:
    return {
        str(key): item for key, item in _mapping(value).items()
        if isinstance(item, (int, float)) and not isinstance(item, bool)
    }


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value if isinstance(item, str) and item] if isinstance(value, list) else []


def _skill_id(skill: dict[str, Any]) -> str | None:
    value = skill.get("id") or skill.get("skill_id")
    return _nonempty_string(value)


def _nonempty_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
