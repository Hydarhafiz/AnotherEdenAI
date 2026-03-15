"""Tests for the StateGraph topology and routing logic.

Covers AGENT-04, AGENT-05:
- Graph compiles and runs (happy path)
- Single retry routes back to generate_cypher
- Retry cap (3) routes to format with error output
- Semantic fail triggers retry just like driver failures
- route_after_validate unit tests (all 3 branches)
"""
import pytest
from unittest.mock import MagicMock, patch, call
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
    """Graph invocation tests with mock LLMs and mock driver."""

    def test_full_graph_happy_path(self, stub_driver, sample_state):
        """With a driver that returns results, graph should complete to final_output."""
        # stub_driver returns ([{"name": "Aldo"}], None, None) by default
        # Patch get_llm for all LLM-using node modules to avoid live API calls
        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=_mock_llm_factory("PASS: Results match the user query.")):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        assert "final_output" in result
        final = result["final_output"]
        assert "frontline" in final
        assert "reserve" in final
        assert "synergy_explanation" in final

    def test_single_retry_routes_back_to_generate_cypher(self, stub_driver, sample_state):
        """Driver fails once (empty result) then succeeds: expect retry_count=1, one error."""
        # First call: empty results (Step 1 fails, Step 2 skipped)
        # Second call: non-empty results (proceed to Step 2)
        stub_driver.execute_query.side_effect = [
            ([], None, None),                    # first validate — Step 1 empty result fail
            ([{"name": "Aldo"}], None, None),    # second validate — Step 1 success
        ]
        # Haiku mock: only called on the 2nd validate attempt (Step 2)
        mock_validate_llm = _mock_llm_factory("PASS: Results match the user query.")

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm):
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
        # All 3 attempts fail at Step 1 (empty results) — Haiku never called
        stub_driver.execute_query.return_value = ([], None, None)
        mock_validate_llm = MagicMock()  # Should never be called

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        # Haiku should never be invoked when Step 1 always fails
        mock_validate_llm.invoke.assert_not_called()

        assert result["retry_count"] == 3, (
            f"Expected retry_count=3 (cap), got {result['retry_count']}"
        )
        assert len(result["validation_errors"]) == 3, (
            f"Expected 3 validation errors, got {len(result['validation_errors'])}"
        )
        # Driver should be called exactly 3 times (never a 4th)
        assert stub_driver.execute_query.call_count == 3, (
            f"Expected exactly 3 driver calls, got {stub_driver.execute_query.call_count}"
        )
        assert "final_output" in result
        final = result["final_output"]
        assert "error" in final, (
            f"Expected 'error' key in final_output on cap-exhausted path. Got: {final}"
        )
        assert final["frontline"] == [], (
            f"Expected frontline=[] on cap-exhausted path. Got: {final['frontline']}"
        )
        assert final["reserve"] == [], (
            f"Expected reserve=[] on cap-exhausted path. Got: {final['reserve']}"
        )

    def test_semantic_fail_triggers_retry(self, stub_driver, sample_state):
        """Semantic FAIL from Haiku triggers retry back to generate_cypher."""
        # Driver always returns data — Step 1 always passes
        stub_driver.execute_query.return_value = ([{"name": "Aldo"}], None, None)

        # Haiku: FAIL on first validate call, PASS on second
        mock_validate_llm = MagicMock()
        mock_validate_llm.invoke.side_effect = [
            AIMessage(content="FAIL: Wrong element group, user asked for Fire but got Wind."),
            AIMessage(content="PASS: Results correctly match the fire-element query."),
        ]

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm):
            graph = build_graph(driver=stub_driver)
            result = graph.invoke(sample_state)

        assert result["retry_count"] == 1, (
            f"Expected retry_count=1, got {result['retry_count']}"
        )
        assert len(result["validation_errors"]) == 1, (
            f"Expected 1 validation error (semantic mismatch), got {len(result['validation_errors'])}"
        )
        assert "Semantic Mismatch" in result["validation_errors"][0], (
            f"Expected 'Semantic Mismatch' in error. Got: {result['validation_errors'][0]}"
        )
        assert "final_output" in result
        final = result["final_output"]
        # Should NOT have error key on success path
        assert "error" not in final, (
            f"Expected no 'error' key in final_output after semantic retry success. Got: {final}"
        )
