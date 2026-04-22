"""Unit tests for the FORMAT node.

Covers AGENT-06, AGENT-07:
- format_node returns only {"final_output": ...}
- final_output has frontline, reserve, synergy_explanation
- Pydantic TeamOutput validation on output
- Error path: retry_count >= 3 and empty db_results produces error schema
- Error string contains joined validation_errors
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from src.workflow.nodes.format import format_node, TeamOutput


@pytest.fixture
def valid_team_json():
    """A valid JSON team recommendation string as ANALYZE would produce.

    Uses 3 frontline + 1 reserve (minimum valid shape under TeamOutput length validators).
    """
    return json.dumps({
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3", "ATK Up"]},
            {"name": "Ciel", "role": "healer", "grastas": ["HP Up"]},
            {"name": "Riica", "role": "support", "grastas": ["SPD Up"]},
        ],
        "reserve": [
            {"name": "Miyu", "role": "support", "grastas": []},
        ],
        "synergy_explanation": "Aldo as fire DPS anchor with Ciel healing, Riica boosting speed, and Miyu reserve support.",
    })


@pytest.fixture
def success_state(valid_team_json):
    """WorkflowState on the happy path with a valid analysis_result."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo", "Ciel", "Miyu"],
        "plan_strategy": "Find Fire element characters",
        "cypher_query": "MATCH (c:Character) RETURN c",
        "db_results": [{"c.name": "Aldo"}, {"c.name": "Ciel"}],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": valid_team_json,
        "final_output": {},
    }


@pytest.fixture
def error_state():
    """WorkflowState on the error path: retry cap exhausted, no db_results."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": ["err1", "err2", "err3"],
        "retry_count": 3,
        "analysis_result": "",
        "final_output": {},
    }


class TestFormatSuccessPath:
    """format_node on the happy path produces a complete, validated team output."""

    def test_format_success_returns_only_final_output(self, success_state):
        """format_node result must have only the 'final_output' key."""
        result = format_node(success_state)
        assert list(result.keys()) == ["final_output"], (
            f"Expected only 'final_output' key, got: {list(result.keys())}"
        )

    def test_format_success_has_required_keys(self, success_state):
        """final_output must have frontline, reserve, and synergy_explanation."""
        result = format_node(success_state)
        final = result["final_output"]
        assert "frontline" in final, "Missing 'frontline' key"
        assert "reserve" in final, "Missing 'reserve' key"
        assert "synergy_explanation" in final, "Missing 'synergy_explanation' key"

    def test_format_success_frontline_is_list(self, success_state):
        """frontline must be a list."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["frontline"], list), (
            f"Expected frontline to be a list, got: {type(result['final_output']['frontline'])}"
        )

    def test_format_success_reserve_is_list(self, success_state):
        """reserve must be a list."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["reserve"], list), (
            f"Expected reserve to be a list, got: {type(result['final_output']['reserve'])}"
        )

    def test_format_success_synergy_explanation_is_str(self, success_state):
        """synergy_explanation must be a string."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["synergy_explanation"], str), (
            f"Expected synergy_explanation to be a str"
        )

    def test_format_success_validates_with_pydantic(self, success_state):
        """final_output dict must pass TeamOutput.model_validate without raising."""
        result = format_node(success_state)
        # This must not raise
        validated = TeamOutput.model_validate(result["final_output"])
        assert validated is not None

    def test_format_success_slot_has_name_role_grastas(self, success_state):
        """Each item in frontline/reserve must have name, role, and grastas keys."""
        result = format_node(success_state)
        final = result["final_output"]
        for slot in final["frontline"] + final["reserve"]:
            assert "name" in slot, f"Slot missing 'name': {slot}"
            assert "role" in slot, f"Slot missing 'role': {slot}"
            assert "grastas" in slot, f"Slot missing 'grastas': {slot}"

    def test_format_success_no_error_key(self, success_state):
        """Happy path final_output must not have an 'error' key (or error is None)."""
        result = format_node(success_state)
        final = result["final_output"]
        # error key should either be absent or None
        assert final.get("error") is None, (
            f"Expected no error on happy path, got: {final.get('error')}"
        )


class TestFormatErrorPath:
    """format_node error path: retry cap exhausted with no db_results."""

    def test_format_error_path_on_retry_cap(self, error_state):
        """retry_count >= 3 and no db_results must produce error schema."""
        result = format_node(error_state)
        assert list(result.keys()) == ["final_output"], (
            f"Expected only 'final_output' key, got: {list(result.keys())}"
        )
        final = result["final_output"]
        assert "error" in final, "Expected 'error' key in error-path final_output"

    def test_format_error_path_frontline_is_empty(self, error_state):
        """Error path frontline must be []."""
        result = format_node(error_state)
        assert result["final_output"]["frontline"] == [], (
            f"Expected frontline=[] on error path, got: {result['final_output']['frontline']}"
        )

    def test_format_error_path_reserve_is_empty(self, error_state):
        """Error path reserve must be []."""
        result = format_node(error_state)
        assert result["final_output"]["reserve"] == [], (
            f"Expected reserve=[] on error path, got: {result['final_output']['reserve']}"
        )

    def test_format_error_path_synergy_explanation_is_empty_str(self, error_state):
        """Error path synergy_explanation must be empty string."""
        result = format_node(error_state)
        assert result["final_output"]["synergy_explanation"] == "", (
            f"Expected synergy_explanation='' on error path"
        )

    def test_format_error_contains_validation_errors(self, error_state):
        """Error string must contain the joined validation_errors."""
        result = format_node(error_state)
        error_str = result["final_output"]["error"]
        # All validation error strings should be in the error output
        for err in error_state["validation_errors"]:
            assert err in error_str, (
                f"Expected '{err}' to appear in error string. Got: {error_str!r}"
            )

    def test_format_error_path_is_pydantic_valid(self, error_state):
        """Error schema must have the correct keys and types (frontline=[], reserve=[] by design)."""
        result = format_node(error_state)
        final = result["final_output"]
        assert "frontline" in final and isinstance(final["frontline"], list)
        assert "reserve" in final and isinstance(final["reserve"], list)
        assert "synergy_explanation" in final
        assert "error" in final

    def test_format_no_error_path_when_retry_count_2(self, error_state):
        """retry_count=2 (below cap) should NOT trigger error path even with no db_results."""
        state = dict(error_state)
        state["retry_count"] = 2
        state["analysis_result"] = json.dumps({
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
            ],
            "synergy_explanation": "test",
        })
        result = format_node(state)
        final = result["final_output"]
        assert final.get("error") is None, (
            f"retry_count=2 should NOT produce error path output, got: {final.get('error')}"
        )


class TestTeamOutputPydanticModel:
    """Direct tests for the TeamOutput Pydantic model."""

    def test_team_output_valid_structure(self):
        """TeamOutput.model_validate must accept a valid team dict."""
        data = {
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
            ],
            "reserve": [{"name": "Miyu", "role": "support", "grastas": []}],
            "synergy_explanation": "Fire synergy.",
        }
        output = TeamOutput.model_validate(data)
        assert output.frontline[0].name == "Aldo"
        assert output.reserve[0].name == "Miyu"
        assert output.synergy_explanation == "Fire synergy."

    def test_team_output_optional_error_field(self):
        """TeamOutput error field is optional and accepts a string value."""
        data = {
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
            ],
            "synergy_explanation": "",
            "error": "Query failed",
        }
        output = TeamOutput.model_validate(data)
        assert output.error == "Query failed"

    def test_team_output_error_defaults_to_none(self):
        """TeamOutput error field defaults to None when not provided."""
        data = {
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
            ],
            "synergy_explanation": "test",
        }
        output = TeamOutput.model_validate(data)
        assert output.error is None
