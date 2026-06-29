"""FORMAT node — transforms analysis_result into a Pydantic-validated team recommendation.

Reads analysis_result from WorkflowState.
Returns only: {"final_output": dict}

This node is intentionally LLM-free — pure Python transformation.
Validates output with Pydantic v2 TeamOutput model.

Error path: if retry_count >= 3 and db_results is empty, returns error schema
with the same keys (frontline, reserve, synergy_explanation, error) for
web layer compatibility.
"""
import json
import logging
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from ..legality import (
    CharacterBuild,
    LineupModel,
    RosterInput,
    collect_legality_context,
    validate_lineup_legality,
)
from ..state import WorkflowState


logger = logging.getLogger(__name__)


class CharacterSlot(CharacterBuild):
    """A single character slot in the team recommendation."""


class Citation(BaseModel):
    """One source citation carried through recommendation output."""

    label: str
    source_url: str


class BossAffinityOutput(BaseModel):
    """Boss affinity facts surfaced in the recommendation output."""

    weak: list[str] = Field(default_factory=list)
    resist: list[str] = Field(default_factory=list)
    null: list[str] = Field(default_factory=list)
    absorb: list[str] = Field(default_factory=list)


class TeamOutput(BaseModel):
    """Structured team recommendation output validated by Pydantic v2.

    frontline: EXACTLY 4 characters in the main battle formation
    reserve: EXACTLY 2 backup characters
    main_sidekick/sub_sidekick: optional sidekick slots, never counted as heroes
    synergy_explanation: human-readable explanation of grasta and role synergies
    error: set on error path (retry cap exhausted OR malformed/non-JSON LLM output),
           None on success path
    """

    frontline: list[CharacterSlot] = Field(min_length=4, max_length=4)
    reserve: list[CharacterSlot] = Field(min_length=2, max_length=2)
    main_sidekick: Optional[str] = None
    sub_sidekick: Optional[str] = None
    archetype: Optional[str] = None
    strategy_summary: str = ""
    key_facts: list[str] = Field(default_factory=list)
    build_notes: list[str] = Field(default_factory=list)
    boss_counterplay_notes: list[str] = Field(default_factory=list)
    sustain_mp_notes: list[str] = Field(default_factory=list)
    fit_label: Optional[Literal["high", "medium", "low"]] = None
    confidence_label: Optional[Literal["high", "medium", "low"]] = None
    rubric_summary: dict[str, str] = Field(default_factory=dict)
    boss_affinity: BossAffinityOutput = Field(default_factory=BossAffinityOutput)
    risks: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    synergy_explanation: str
    error: Optional[str] = None

    @model_validator(mode="after")
    def _validate_lineup_legality_shape(self) -> "TeamOutput":
        hero_names = [slot.name for slot in self.frontline + self.reserve]
        duplicates = sorted({name for name in hero_names if hero_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate heroes are not legal: {', '.join(duplicates)}")
        if self.main_sidekick and self.sub_sidekick and self.main_sidekick == self.sub_sidekick:
            raise ValueError("main_sidekick and sub_sidekick must be different")
        sidekicks = {name for name in [self.main_sidekick, self.sub_sidekick] if name}
        sidekick_as_hero = sorted(set(hero_names) & sidekicks)
        if sidekick_as_hero:
            raise ValueError(f"sidekicks cannot occupy hero slots: {', '.join(sidekick_as_hero)}")
        probability_text = " ".join(
            [
                self.synergy_explanation,
                *self.risks,
                *self.rubric_summary.values(),
            ]
        ).lower()
        if (
            "win probability" in probability_text
            or "win rate" in probability_text
            or "win chance" in probability_text
            or re.search(r"\b\d+(?:\.\d+)?\s*%\s*(?:win|clear|success|victory)", probability_text)
        ):
            raise ValueError("recommendations must not present numeric win probability")
        return self


class AlternativesOutput(BaseModel):
    """Three alternative full team compositions when db_results is empty.

    alternatives: exactly 3 complete TeamOutput-shaped objects (validated by Pydantic).
    reason: human-readable explanation of why alternatives were generated.
    """

    alternatives: list[TeamOutput] = Field(min_length=3, max_length=3)
    reason: str


class RecommendationSetOutput(BaseModel):
    """Feature D top-three recommendation envelope.

    recommendations: exactly 3 legal-shape lineup plans, usually burst/sustain/hybrid.
    boss_affinity: graph-derived affinity facts shared across the recommendation set.
    archetype_viability_notes: explains weaker archetypes or variant rationale.
    """

    recommendations: list[TeamOutput] = Field(min_length=3, max_length=3)
    boss_affinity: BossAffinityOutput = Field(default_factory=BossAffinityOutput)
    archetype_viability_notes: list[str] = Field(default_factory=list)
    error: Optional[str] = None

    @model_validator(mode="after")
    def _validate_feature_d_contract(self) -> "RecommendationSetOutput":
        archetypes = [rec.archetype.lower() for rec in self.recommendations if rec.archetype]
        for rec in self.recommendations:
            if not rec.archetype:
                raise ValueError("each recommendation must include an archetype")
            if not rec.strategy_summary:
                raise ValueError("each recommendation must include a strategy_summary")
            if not rec.citations:
                raise ValueError("each recommendation must include source citations")
            if not (rec.key_facts or rec.boss_counterplay_notes):
                raise ValueError("each recommendation must include key facts or boss counterplay notes")
            if not rec.build_notes:
                raise ValueError("each recommendation must include build notes")
            if not rec.boss_counterplay_notes:
                raise ValueError("each recommendation must include boss counterplay notes")
            if not rec.sustain_mp_notes:
                raise ValueError("each recommendation must include sustain and MP notes")
            if not rec.risks:
                raise ValueError("each recommendation must include risks or assumptions")
            if not rec.fit_label or not rec.confidence_label:
                raise ValueError("each recommendation must include fit and confidence labels")

        expected = {"burst", "sustain", "hybrid"}
        if not expected.issubset(set(archetypes)) and not self.archetype_viability_notes:
            raise ValueError("variant recommendations require archetype_viability_notes")
        return self


def _extract_json(text: str) -> dict:
    """Extract and parse a JSON object from an LLM response string.

    Tries direct JSON parse first, then falls back to regex extraction
    for cases where the LLM wraps JSON in preamble or markdown fences.

    Args:
        text: Raw LLM response string.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON object can be extracted.
    """
    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract JSON block from markdown fences (```json ... ```)
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: find the outermost {...} block in the text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    open_braces = text.count("{")
    close_braces = text.count("}")
    if open_braces > close_braces:
        raise ValueError(
            "analyzer returned incomplete JSON (the response appears to be truncated)"
        )
    raise ValueError("analyzer did not return a valid JSON object")


def _normalize_analyzer_shape(value):
    """Normalize safe graph-record variants before strict output validation."""
    if isinstance(value, dict):
        for child in value.values():
            _normalize_analyzer_shape(child)

        if "name" in value and "role" in value:
            grastas = value.get("grastas")
            if isinstance(grastas, list):
                while grastas and len(grastas) < 3:
                    grastas.append(grastas[-1])

            for key in ("recommended_skills", "recommended_passives"):
                choices = value.get(key)
                if isinstance(choices, list):
                    value[key] = [
                        choice["name"]
                        if isinstance(choice, dict) and isinstance(choice.get("name"), str)
                        else choice
                        for choice in choices
                    ]
    elif isinstance(value, list):
        for child in value:
            _normalize_analyzer_shape(child)
    return value


def _ground_missing_citations(value: dict, boss_context: str) -> dict:
    """Fill omitted recommendation citations only from trusted graph context."""
    recommendations = value.get("recommendations")
    if not isinstance(recommendations, list) or not boss_context:
        return value

    try:
        context = json.loads(boss_context)
    except (json.JSONDecodeError, TypeError):
        return value

    citations = [
        citation
        for citation in context.get("citations", [])
        if (
            isinstance(citation, dict)
            and isinstance(citation.get("label"), str)
            and isinstance(citation.get("source_url"), str)
            and citation["label"]
            and citation["source_url"]
        )
    ]
    if not citations:
        boss = context.get("boss")
        if (
            isinstance(boss, dict)
            and isinstance(boss.get("name"), str)
            and isinstance(boss.get("source_url"), str)
            and boss["name"]
            and boss["source_url"]
        ):
            citations = [{"label": boss["name"], "source_url": boss["source_url"]}]

    if citations:
        for recommendation in recommendations:
            if isinstance(recommendation, dict) and not recommendation.get("citations"):
                recommendation["citations"] = [dict(citation) for citation in citations]
    return value


def _format_structure_error(kind: str, exc: ValidationError | ValueError) -> str:
    """Return useful formatter diagnostics without exposing the raw LLM response."""
    if isinstance(exc, ValidationError):
        details = []
        for error in exc.errors(include_url=False)[:5]:
            location = ".".join(str(part) for part in error["loc"]) or "response"
            details.append(f"{location}: {error['msg']}")
        suffix = "; ".join(details)
    else:
        suffix = str(exc)
    return f"LLM returned malformed {kind} structure: {suffix}"


def format_node(state: WorkflowState) -> dict:
    """Format the analysis into a structured, Pydantic-validated team recommendation.

    Owned keys: final_output

    Error path (retry cap exhausted):
        When retry_count >= 3 and db_results is empty, returns error schema:
        {"frontline": [], "reserve": [], "synergy_explanation": "", "error": "<joined errors>"}

    Happy path:
        Parses analysis_result as JSON, validates with TeamOutput Pydantic model,
        returns model_dump() as final_output.

    Args:
        state: Current WorkflowState after ANALYZE has run (or error path).

    Returns:
        Dict containing only {"final_output": dict}.
    """
    retry_count = state.get("retry_count", 0)
    db_results = state.get("db_results", [])

    # Error path: retry cap exhausted (only when no alternatives were generated)
    if retry_count >= 3 and not db_results and not state.get("alternatives"):
        validation_errors = state.get("validation_errors", [])
        error_str = "; ".join(validation_errors) if validation_errors else "Query failed after 3 retries"
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": error_str,
            }
        }

    # Alternatives path: analyze_node detected empty db_results and generated alternatives
    alternatives_raw = state.get("alternatives", "")
    if alternatives_raw:
        try:
            parsed = _normalize_analyzer_shape(_extract_json(alternatives_raw))
            validated = AlternativesOutput.model_validate(parsed)
        except (ValidationError, ValueError) as exc:
            logger.warning("%s", _format_structure_error("alternatives", exc))
            return {
                "final_output": {
                    "frontline": [],
                    "reserve": [],
                    "synergy_explanation": "",
                    "error": _format_structure_error("alternatives", exc),
                }
            }
        return {"final_output": validated.model_dump()}

    # Happy path: parse and validate analysis_result
    analysis_result = state.get("analysis_result", "")
    try:
        parsed = _normalize_analyzer_shape(_extract_json(analysis_result))
        parsed = _ground_missing_citations(parsed, state.get("boss_context", ""))
        if "recommendations" in parsed:
            validated = RecommendationSetOutput.model_validate(parsed)
        else:
            validated = TeamOutput.model_validate(parsed)
    except (ValidationError, ValueError) as exc:
        # ValidationError: shape is wrong (e.g. 2 frontline instead of 3-4)
        # ValueError: _extract_json could not find JSON in the LLM output
        logger.warning("%s", _format_structure_error("team", exc))
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": _format_structure_error("team", exc),
            }
        }
    return {"final_output": validated.model_dump()}


async def format_and_validate_node(state: WorkflowState, driver) -> dict:
    """Format output, then enforce graph-backed lineup legality before rendering.

    The synchronous format_node remains the pure Pydantic transformation
    boundary. Production graph execution uses this wrapper so every successful
    single-team, recommendation-set, or alternatives payload is checked against
    roster ownership plus graph-backed character, sidekick, skill, passive, and
    Stellar Awakening facts before final_output is emitted.
    """
    formatted = format_node(state)
    final_output = formatted["final_output"]
    if final_output.get("error"):
        return formatted

    try:
        _validate_boss_affinity_fidelity(final_output, state.get("boss_context", ""))
        roster = RosterInput(
            owned_characters=state.get("roster", []),
            stellar_awakened=state.get("stellar_awakened", {}),
            owned_sidekicks=state.get("owned_sidekicks", []),
        )
        for lineup_payload in _lineup_payloads(final_output):
            lineup = LineupModel.model_validate(lineup_payload)
            context = await collect_legality_context(driver, lineup)
            validate_lineup_legality(lineup, roster, context)
    except Exception as exc:
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": f"Recommendation failed final validation: {exc}",
            }
        }

    return formatted


def _lineup_payloads(final_output: dict) -> list[dict]:
    """Return every lineup-shaped payload from a supported final envelope."""
    if "recommendations" in final_output:
        return final_output["recommendations"]
    if "alternatives" in final_output:
        return final_output["alternatives"]
    return [final_output]


def _validate_boss_affinity_fidelity(final_output: dict, boss_context: str) -> None:
    """Reject output affinities that differ from graph-backed boss facts."""
    if not boss_context:
        return
    try:
        context = json.loads(boss_context)
    except (TypeError, json.JSONDecodeError):
        return

    graph_boss = context.get("boss") if isinstance(context, dict) else None
    if not isinstance(graph_boss, dict):
        return

    output_affinities = _output_boss_affinities(final_output)
    if not output_affinities:
        raise ValueError("boss affinity output is missing despite graph-backed boss facts")

    mismatches = []
    for output_label, affinity in output_affinities:
        for field in ("weak", "resist", "null", "absorb"):
            expected = _normalized_affinity_values(graph_boss.get(field, []))
            actual = _normalized_affinity_values(affinity.get(field, []))
            if actual != expected:
                mismatches.append(
                    f"{output_label}.{field} expected {sorted(expected)} but received {sorted(actual)}"
                )
    if mismatches:
        raise ValueError("boss affinity facts do not match graph facts: " + "; ".join(mismatches))


def _output_boss_affinities(final_output: dict) -> list[tuple[str, dict]]:
    """Return canonical affinity objects for a supported output envelope."""
    if "recommendations" in final_output:
        value = final_output.get("boss_affinity")
        return [("recommendation_set", value)] if isinstance(value, dict) else []
    if "alternatives" in final_output:
        return [
            (f"alternative_{index}", affinity)
            for index, alternative in enumerate(final_output.get("alternatives", []), start=1)
            if isinstance((affinity := alternative.get("boss_affinity")), dict)
        ]
    value = final_output.get("boss_affinity")
    return [("team", value)] if isinstance(value, dict) else []


def _normalized_affinity_values(values) -> set[str]:
    """Compare affinity lists case-insensitively and independent of order."""
    if not isinstance(values, list):
        return set()
    return {
        normalized
        for value in values
        if (normalized := str(value).strip().lower()) and normalized != "unknown"
    }
