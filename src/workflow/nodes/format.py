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
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from ..legality import CharacterBuild
from ..state import WorkflowState


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

    raise ValueError(f"No valid JSON object found in analysis_result: {text!r}")


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
            parsed = _extract_json(alternatives_raw)
            validated = AlternativesOutput.model_validate(parsed)
        except (ValidationError, ValueError):
            return {
                "final_output": {
                    "frontline": [],
                    "reserve": [],
                    "synergy_explanation": "",
                    "error": "LLM returned malformed alternatives structure — retry or check model",
                }
            }
        return {"final_output": validated.model_dump()}

    # Happy path: parse and validate analysis_result
    analysis_result = state.get("analysis_result", "")
    try:
        parsed = _extract_json(analysis_result)
        if "recommendations" in parsed:
            validated = RecommendationSetOutput.model_validate(parsed)
        else:
            validated = TeamOutput.model_validate(parsed)
    except (ValidationError, ValueError):
        # ValidationError: shape is wrong (e.g. 2 frontline instead of 3-4)
        # ValueError: _extract_json could not find JSON in the LLM output
        return {
            "final_output": {
                "frontline": [],
                "reserve": [],
                "synergy_explanation": "",
                "error": "LLM returned malformed team structure — retry or check model",
            }
        }
    return {"final_output": validated.model_dump()}
