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
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from ..state import WorkflowState


class CharacterSlot(BaseModel):
    """A single character slot in the team recommendation."""

    name: str
    role: str
    grastas: list[str]


class TeamOutput(BaseModel):
    """Structured team recommendation output validated by Pydantic v2.

    frontline: EXACTLY 3-4 characters in the main battle formation
    reserve: EXACTLY 1-2 backup characters
    synergy_explanation: human-readable explanation of grasta and role synergies
    error: set on error path (retry cap exhausted OR malformed/non-JSON LLM output),
           None on success path
    """

    frontline: list[CharacterSlot] = Field(min_length=3, max_length=4)
    reserve: list[CharacterSlot] = Field(min_length=1, max_length=2)
    synergy_explanation: str
    error: Optional[str] = None


class AlternativesOutput(BaseModel):
    """Three alternative full team compositions when db_results is empty.

    alternatives: exactly 3 complete TeamOutput-shaped objects (validated by Pydantic).
    reason: human-readable explanation of why alternatives were generated.
    """

    alternatives: list[TeamOutput] = Field(min_length=3, max_length=3)
    reason: str


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
