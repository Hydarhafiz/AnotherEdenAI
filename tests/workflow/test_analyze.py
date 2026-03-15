"""Unit tests for the ANALYZE node.

Covers AGENT-06, AGENT-07:
- analyze_node returns only {"analysis_result": ...}
- analyze_node passes db_results, user_query, roster, and plan_strategy to LLM
- analyze_node uses Sonnet 4.6 via get_llm(role="analyzer")
- analysis_result is the LLM response content string
"""
import pytest
from unittest.mock import MagicMock, patch, call
from langchain_core.messages import AIMessage

from src.workflow.nodes.analyze import analyze_node


@pytest.fixture
def sample_analyze_state():
    """Complete WorkflowState for analyze_node tests."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo", "Ciel"],
        "plan_strategy": "Find Fire element characters with synergy traits",
        "cypher_query": "MATCH (c:Character) WHERE c.element = 'Fire' RETURN c",
        "db_results": [
            {"c.name": "Aldo", "t.name": "Straw Dummy"},
            {"c.name": "Ciel", "t.name": "Fire Support"},
        ],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "final_output": {},
    }


def _make_mock_llm(content="mock analysis response"):
    """Create a MagicMock LLM returning the given content."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=content)
    return llm


class TestAnalyzeReturnsOnlyAnalysisResult:
    """AGENT-07: analyze_node must return only the analysis_result key."""

    def test_analyze_returns_only_analysis_result(self, sample_analyze_state):
        """analyze_node result must have only the 'analysis_result' key."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            result = analyze_node(sample_analyze_state)

        assert list(result.keys()) == ["analysis_result"], (
            f"Expected only 'analysis_result' key, got: {list(result.keys())}"
        )


class TestAnalyzePassesContextToLLM:
    """analyze_node must include all required context in the LLM prompt."""

    def test_analyze_passes_db_results_to_llm(self, sample_analyze_state):
        """db_results must appear in the LLM messages."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            analyze_node(sample_analyze_state)

        assert mock_llm.invoke.called, "LLM was never called"
        messages = mock_llm.invoke.call_args[0][0]
        # Join all message content for inspection
        all_content = " ".join(str(m.content) for m in messages)
        assert "Aldo" in all_content, (
            "Expected 'Aldo' (from db_results) to appear in LLM prompt"
        )

    def test_analyze_passes_user_query_to_llm(self, sample_analyze_state):
        """user_query must appear in the LLM messages."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            analyze_node(sample_analyze_state)

        messages = mock_llm.invoke.call_args[0][0]
        all_content = " ".join(str(m.content) for m in messages)
        assert "best fire team" in all_content, (
            "Expected 'best fire team' (user_query) to appear in LLM prompt"
        )

    def test_analyze_passes_roster_to_llm(self, sample_analyze_state):
        """roster must appear in the LLM messages."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            analyze_node(sample_analyze_state)

        messages = mock_llm.invoke.call_args[0][0]
        all_content = " ".join(str(m.content) for m in messages)
        assert "Ciel" in all_content, (
            "Expected 'Ciel' (from roster) to appear in LLM prompt"
        )

    def test_analyze_passes_plan_strategy_to_llm(self, sample_analyze_state):
        """plan_strategy must appear in the LLM messages."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            analyze_node(sample_analyze_state)

        messages = mock_llm.invoke.call_args[0][0]
        all_content = " ".join(str(m.content) for m in messages)
        assert "Fire element" in all_content, (
            "Expected plan_strategy content ('Fire element') to appear in LLM prompt"
        )


class TestAnalyzeUsesAnalyzerRole:
    """analyze_node must call get_llm with role='analyzer'."""

    def test_analyze_uses_analyzer_role(self, sample_analyze_state):
        """get_llm must be called with role='analyzer'."""
        mock_llm = _make_mock_llm()
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm) as mock_get_llm:
            analyze_node(sample_analyze_state)

        mock_get_llm.assert_called_once_with(role="analyzer")


class TestAnalyzeResultIsLLMContent:
    """analysis_result must be the raw content string from the LLM response."""

    def test_analyze_result_is_llm_content(self, sample_analyze_state):
        """analysis_result value must equal response.content from the LLM."""
        expected_content = '{"frontline": [{"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]}]}'
        mock_llm = _make_mock_llm(content=expected_content)
        with patch("src.workflow.nodes.analyze.get_llm", return_value=mock_llm):
            result = analyze_node(sample_analyze_state)

        assert result["analysis_result"] == expected_content, (
            f"Expected analysis_result == LLM content. "
            f"Got: {result['analysis_result']!r}, Expected: {expected_content!r}"
        )
