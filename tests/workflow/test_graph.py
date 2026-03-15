"""Tests for the StateGraph topology and routing logic.

Covers AGENT-04, AGENT-05:
- Graph compiles and runs (happy path)
- Single retry routes back to generate_cypher
- Retry cap (3) routes to format with error output
- route_after_validate unit tests (all 3 branches)
"""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

from src.workflow.graph import build_graph, route_after_validate


def _mock_llm_factory(content="stub response"):
    """Return a MagicMock LLM that returns a predictable AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=content)
    return llm


class TestRouteAfterValidate:
    """Unit tests for route_after_validate routing function."""

    def test_route_after_validate_success(self):
        """Non-empty db_results must route to analyze."""
        state = {
            "db_results": [{"name": "Aldo"}],
            "retry_count": 0,
        }
        assert route_after_validate(state) == "analyze"

    def test_route_after_validate_retry(self):
        """Empty db_results with retry_count < 3 must route to generate_cypher."""
        state = {
            "db_results": [],
            "retry_count": 1,
        }
        assert route_after_validate(state) == "generate_cypher"

    def test_route_after_validate_cap(self):
        """Empty db_results with retry_count >= 3 must route to format."""
        state = {
            "db_results": [],
            "retry_count": 3,
        }
        assert route_after_validate(state) == "format"

    def test_route_after_validate_cap_above_three(self):
        """retry_count > 3 also routes to format (defensive)."""
        state = {
            "db_results": [],
            "retry_count": 5,
        }
        assert route_after_validate(state) == "format"

    def test_route_after_validate_success_overrides_retry_count(self):
        """Non-empty db_results routes to analyze even if retry_count is high."""
        state = {
            "db_results": [{"name": "Ciel"}],
            "retry_count": 2,
        }
        assert route_after_validate(state) == "analyze"


class TestGraphHappyPath:
    """Graph invocation tests with stub nodes and mock driver."""

    def test_full_graph_happy_path(self, stub_driver, sample_state):
        """With a driver that returns results, graph should complete to final_output."""
        # stub_driver returns ([{"name": "Aldo"}], None, None) by default
        # Patch get_llm for both PLAN and GENERATE_CYPHER to avoid live API calls
        with patch("src.workflow.nodes.plan.get_llm", return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm", return_value=_mock_llm_factory("MATCH (n) RETURN n")):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        assert "final_output" in result
        final = result["final_output"]
        assert "frontline" in final
        assert "reserve" in final
        assert "synergy_explanation" in final

    def test_single_retry_routes_back_to_generate_cypher(self, stub_driver, sample_state):
        """Driver fails once then succeeds: expect retry_count=1, one validation_error."""
        stub_driver.execute_query.side_effect = [
            ([], None, None),               # first call — fail, trigger retry
            ([{"name": "Aldo"}], None, None),  # second call — success
        ]
        with patch("src.workflow.nodes.plan.get_llm", return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm", return_value=_mock_llm_factory("MATCH (n) RETURN n")):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        assert result["retry_count"] == 1, (
            f"Expected retry_count=1, got {result['retry_count']}"
        )
        assert len(result["validation_errors"]) == 1, (
            f"Expected 1 validation error, got {len(result['validation_errors'])}"
        )
        assert "final_output" in result
        final = result["final_output"]
        assert "frontline" in final
        assert "reserve" in final
        assert "synergy_explanation" in final
        # Should NOT have error key on success path
        assert "error" not in final

    def test_retry_cap_exhausted_routes_to_format_error(self, stub_driver, sample_state):
        """Driver always returns empty: retry cap at 3 routes to format with error."""
        stub_driver.execute_query.return_value = ([], None, None)
        with patch("src.workflow.nodes.plan.get_llm", return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm", return_value=_mock_llm_factory("MATCH (n) RETURN n")):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        assert result["retry_count"] == 3, (
            f"Expected retry_count=3 (cap), got {result['retry_count']}"
        )
        assert len(result["validation_errors"]) == 3, (
            f"Expected 3 validation errors, got {len(result['validation_errors'])}"
        )
        assert "final_output" in result
        final = result["final_output"]
        assert "error" in final, (
            f"Expected 'error' key in final_output on cap-exhausted path. Got: {final}"
        )
        assert final["frontline"] == [], (
            f"Expected frontline=[] on cap-exhausted path. Got: {final['frontline']}"
        )
