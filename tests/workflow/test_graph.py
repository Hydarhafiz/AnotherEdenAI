"""Tests for the StateGraph topology and routing logic.

Covers AGENT-04, AGENT-05, AGENT-06, AGENT-07:
- Graph compiles and runs (happy path) with all real nodes mocked
- Single retry routes back to generate_cypher
- Retry cap (3) routes to format with error output
- Semantic fail triggers retry just like driver failures
- Full pipeline: no live LLM calls, no live Neo4j connections
- route_after_validate unit tests (all 3 branches)

Note: validate_node is async (Phase 3), so graph tests use ainvoke().
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from langchain_core.messages import AIMessage

from src.workflow.graph import build_graph, route_after_validate


def _mock_llm_factory(content="stub response"):
    """Return a MagicMock LLM that returns a predictable AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=content)
    return llm


# Canned ANALYZE JSON response used in happy-path tests.
# Must have 3-4 frontline and 1-2 reserve to satisfy TeamOutput length validators.
_ANALYZE_RESPONSE = (
    '{"frontline": ['
    '{"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},'
    '{"name": "Riica", "role": "support", "grastas": ["SPD Up"]},'
    '{"name": "Bertrand", "role": "tank", "grastas": []}'
    '],'
    ' "reserve": [{"name": "Ciel", "role": "support", "grastas": []}],'
    ' "synergy_explanation": "Fire synergy with Aldo as main DPS"}'
)


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
        """Empty db_results with retry_count >= 3 must route to analyze (alternatives path)."""
        state = {
            "db_results": [],
            "retry_count": 3,
        }
        assert route_after_validate(state) == "analyze"

    def test_route_after_validate_cap_above_three(self):
        """retry_count > 3 also routes to analyze/alternatives (defensive)."""
        state = {
            "db_results": [],
            "retry_count": 5,
        }
        assert route_after_validate(state) == "analyze"

    def test_route_after_validate_success_overrides_retry_count(self):
        """Non-empty db_results routes to analyze even if retry_count is high."""
        state = {
            "db_results": [{"name": "Ciel"}],
            "retry_count": 2,
        }
        assert route_after_validate(state) == "analyze"


class TestGraphHappyPath:
    """Graph invocation tests with mock LLMs and mock driver.

    All graph tests use ainvoke() because validate_node is async.
    """

    @pytest.mark.asyncio
    async def test_full_graph_happy_path(self, stub_driver, sample_state):
        """Full pipeline with all 5 nodes: query flows through to structured team output.

        Mocks:
          - PLAN: returns plan strategy string
          - GENERATE_CYPHER: returns Cypher query string
          - VALIDATE: Haiku returns PASS (results match)
          - ANALYZE: returns valid JSON team recommendation
          - stub_driver: returns non-empty results

        Asserts:
          - final_output has frontline with Aldo, reserve with Ciel
          - synergy_explanation is non-empty
          - retry_count == 0, validation_errors == []
          - no error key on success path
        """
        stub_driver.execute_query.return_value = (
            [{"c.name": "Aldo", "t.name": "Straw Dummy"}], None, None
        )

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("Find Fire element characters with synergy traits")), \
             patch("src.workflow.nodes.plan.normalize_roster",
                   new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory(
                       "MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait) "
                       "WHERE c.name IN $roster RETURN c.name, t.name"
                   )), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=_mock_llm_factory("PASS: Results match the user query.")), \
             patch("src.workflow.nodes.analyze.get_llm",
                   return_value=_mock_llm_factory(_ANALYZE_RESPONSE)):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)

        assert "final_output" in result
        final = result["final_output"]
        assert "frontline" in final
        assert "reserve" in final
        assert "synergy_explanation" in final

        # Aldo should be in frontline
        frontline_names = [slot["name"] for slot in final["frontline"]]
        assert "Aldo" in frontline_names, (
            f"Expected 'Aldo' in frontline, got: {frontline_names}"
        )
        # Ciel should be in reserve
        reserve_names = [slot["name"] for slot in final["reserve"]]
        assert "Ciel" in reserve_names, (
            f"Expected 'Ciel' in reserve, got: {reserve_names}"
        )
        # synergy_explanation should be non-empty
        assert final["synergy_explanation"], "Expected non-empty synergy_explanation"

        # Success path: no error key (or error is None)
        assert final.get("error") is None, (
            f"Expected no error on success path, got: {final.get('error')}"
        )

        assert result["retry_count"] == 0, (
            f"Expected retry_count=0 on happy path, got: {result['retry_count']}"
        )
        assert result["validation_errors"] == [], (
            f"Expected empty validation_errors, got: {result['validation_errors']}"
        )

    @pytest.mark.asyncio
    async def test_single_retry_routes_back_to_generate_cypher(self, stub_driver, sample_state):
        """Driver fails once (empty result) then succeeds: retry_count=1, one error, team data.

        First validate: empty result -> retry
        Second validate: non-empty result -> success -> ANALYZE -> FORMAT
        """
        stub_driver.execute_query.side_effect = [
            ([], None, None),                                              # 1st validate: fail
            ([{"c.name": "Aldo", "t.name": "Straw Dummy"}], None, None),  # 2nd validate: success
        ]
        mock_validate_llm = _mock_llm_factory("PASS: Results match the user query.")

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.plan.normalize_roster",
                   new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm), \
             patch("src.workflow.nodes.analyze.get_llm",
                   return_value=_mock_llm_factory(_ANALYZE_RESPONSE)):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)

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
        assert final.get("error") is None, (
            f"Expected no 'error' key on retry-then-success path. Got: {final.get('error')}"
        )

    @pytest.mark.asyncio
    async def test_retry_cap_exhausted_routes_to_analyze_alternatives(self, stub_driver, sample_state):
        """Driver always returns empty: retry cap at 3 routes to analyze (alternatives path).

        Phase 5: analyze_node detects empty db_results and calls _generate_alternatives.
        FORMAT then validates AlternativesOutput and returns final_output with alternatives list.
        stub_driver.execute_query must be called exactly 3 times.
        """
        import json as _json

        _team = {
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},
                {"name": "Ciel", "role": "healer", "grastas": ["HP Up"]},
                {"name": "Riica", "role": "support", "grastas": []},
            ],
            "reserve": [{"name": "Miyu", "role": "support", "grastas": []}],
            "synergy_explanation": "Aldo: Fire T3 Grasta (Courage) — boosts Fire damage.",
        }
        _alternatives_response = _json.dumps({
            "alternatives": [_team, _team, _team],
            "reason": "No Cypher results found for query.",
        })

        stub_driver.execute_query.return_value = ([], None, None)
        mock_validate_llm = MagicMock()  # Should never be called (Step 1 always fails)

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.plan.normalize_roster",
                   new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm), \
             patch("src.workflow.nodes.analyze.get_llm",
                   return_value=_mock_llm_factory(_alternatives_response)):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)

        # Haiku never called when Step 1 always fails (empty result)
        mock_validate_llm.invoke.assert_not_called()

        assert result["retry_count"] == 3, (
            f"Expected retry_count=3 (cap), got {result['retry_count']}"
        )
        assert len(result["validation_errors"]) == 3, (
            f"Expected 3 validation errors, got {len(result['validation_errors'])}"
        )
        # Driver called exactly 3 times (never a 4th)
        assert stub_driver.execute_query.call_count == 3, (
            f"Expected exactly 3 driver calls, got {stub_driver.execute_query.call_count}"
        )
        assert "final_output" in result
        final = result["final_output"]
        # Alternatives path: final_output has "alternatives" key with 3 team dicts
        assert "alternatives" in final, (
            f"Expected 'alternatives' key in final_output on cap-exhausted path. Got: {final}"
        )
        assert len(final["alternatives"]) == 3, (
            f"Expected 3 alternatives, got {len(final['alternatives'])}"
        )
        assert final.get("error") is None, (
            f"Expected no error on alternatives path, got: {final.get('error')}"
        )

    @pytest.mark.asyncio
    async def test_semantic_fail_triggers_retry(self, stub_driver, sample_state):
        """Semantic FAIL from Haiku triggers retry back to generate_cypher."""
        # Driver always returns data — Step 1 always passes
        stub_driver.execute_query.return_value = (
            [{"c.name": "Aldo", "t.name": "Straw Dummy"}], None, None
        )

        # Haiku: FAIL on first validate call, PASS on second
        mock_validate_llm = MagicMock()
        mock_validate_llm.invoke.side_effect = [
            AIMessage(content="FAIL: Wrong element group, user asked for Fire but got Wind."),
            AIMessage(content="PASS: Results correctly match the fire-element query."),
        ]

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("stub plan")), \
             patch("src.workflow.nodes.plan.normalize_roster",
                   new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")), \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=mock_validate_llm), \
             patch("src.workflow.nodes.analyze.get_llm",
                   return_value=_mock_llm_factory(_ANALYZE_RESPONSE)):
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)

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
        assert final.get("error") is None, (
            f"Expected no 'error' key in final_output after semantic retry success. Got: {final}"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_no_live_calls(self, stub_driver, sample_state):
        """Smoke test: full pipeline runs without any live LLM or Neo4j calls.

        Confirms AGENT requirement: pytest passes with all nodes mocked —
        no ANTHROPIC_API_KEY needed, no live Neo4j connection needed.
        """
        stub_driver.execute_query.return_value = (
            [{"c.name": "Aldo", "t.name": "Straw Dummy"}], None, None
        )

        with patch("src.workflow.nodes.plan.get_llm",
                   return_value=_mock_llm_factory("plan strategy")) as mock_plan, \
             patch("src.workflow.nodes.plan.normalize_roster",
                   new_callable=AsyncMock, return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.plan.augment_with_f2p", return_value=["Aldo", "Ciel"]), \
             patch("src.workflow.nodes.cypher.get_llm",
                   return_value=_mock_llm_factory("MATCH (n) RETURN n")) as mock_cypher, \
             patch("src.workflow.nodes.validate.get_llm",
                   return_value=_mock_llm_factory("PASS: OK")) as mock_validate, \
             patch("src.workflow.nodes.analyze.get_llm",
                   return_value=_mock_llm_factory(_ANALYZE_RESPONSE)) as mock_analyze:
            graph = build_graph(driver=stub_driver)
            result = await graph.ainvoke(sample_state)

        # Each LLM-using node called get_llm exactly once
        mock_plan.assert_called_once()
        mock_cypher.assert_called_once()
        mock_analyze.assert_called_once()

        # Pipeline completed successfully
        assert "final_output" in result
        assert result["final_output"] is not None

        # stub_driver (not live Neo4j) was used
        stub_driver.execute_query.assert_called()
