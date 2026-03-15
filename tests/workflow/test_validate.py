"""Unit tests for the VALIDATE node — two-step hybrid gate.

Covers AGENT-03, AGENT-04:
- Step 1 (deterministic): driver execution failure modes (exception, empty result)
- Step 2 (semantic gate): Haiku 4.6 PASS/FAIL evaluation
- Error message format: "Attempt {N}: Query failed due to [mode]. Context: [detail]"
- retry_count incremented on all failure paths, unchanged on success
- db_results only returned on full success (both steps pass)
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

from src.workflow.nodes.validate import validate_node


def _make_state(retry_count=0, user_query="best fire team", cypher_query="MATCH (n) RETURN n"):
    return {
        "user_query": user_query,
        "roster": ["Aldo", "Ciel"],
        "plan_strategy": "stub plan",
        "cypher_query": cypher_query,
        "db_results": [],
        "validation_errors": [],
        "retry_count": retry_count,
        "analysis_result": "",
        "final_output": {},
    }


def _mock_haiku(content):
    """Return a MagicMock LLM that returns a predictable AIMessage."""
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=content)
    return llm


# ---------------------------------------------------------------------------
# Step 1 (Deterministic) tests
# ---------------------------------------------------------------------------

class TestStep1Exception:
    """Driver raises an exception — Step 2 must be skipped."""

    def test_validate_exception_returns_error(self):
        """Exception in driver returns validation_errors and incremented retry_count."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.side_effect = Exception("Unknown label")
        mock_haiku = _mock_haiku("PASS: Should not be called")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "validation_errors" in result
        assert isinstance(result["validation_errors"], list)
        assert len(result["validation_errors"]) == 1
        assert "retry_count" in result
        assert result["retry_count"] == 1
        # Step 2 must be skipped
        mock_haiku.invoke.assert_not_called()

    def test_validate_exception_error_format(self):
        """Exception error message must match the locked template."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.side_effect = Exception("Unknown label")

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        error_msg = result["validation_errors"][0]
        assert "Attempt 1" in error_msg
        assert "Exception" in error_msg
        assert "Unknown label" in error_msg

    def test_validate_exception_error_format_attempt_number(self):
        """Attempt number in error must reflect current retry_count + 1."""
        state = _make_state(retry_count=2)
        driver = MagicMock()
        driver.execute_query.side_effect = Exception("Syntax error")

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        error_msg = result["validation_errors"][0]
        assert "Attempt 3" in error_msg

    def test_validate_exception_increments_retry_from_current(self):
        """retry_count increments from current state value."""
        state = _make_state(retry_count=2)
        driver = MagicMock()
        driver.execute_query.side_effect = Exception("Syntax error")

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        assert result["retry_count"] == 3

    def test_validate_exception_does_not_return_db_results(self):
        """Exception path must NOT include db_results in result."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.side_effect = Exception("Error")

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        assert "db_results" not in result


class TestStep1EmptyResult:
    """Driver returns empty list — Step 2 must be skipped."""

    def test_validate_empty_result_returns_error(self):
        """Empty result returns validation_errors and incremented retry_count."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([], None, None)
        mock_haiku = _mock_haiku("PASS: Should not be called")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "validation_errors" in result
        assert len(result["validation_errors"]) == 1
        assert "retry_count" in result
        assert result["retry_count"] == 1
        # Step 2 must be skipped
        mock_haiku.invoke.assert_not_called()

    def test_validate_empty_result_error_format(self):
        """Empty result error message must contain 'Empty Result' indicator."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([], None, None)

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        error_msg = result["validation_errors"][0]
        assert "Attempt 1" in error_msg
        assert "Empty Result" in error_msg

    def test_validate_empty_result_increments_retry_from_current(self):
        """retry_count increments from current state value on empty result."""
        state = _make_state(retry_count=1)
        driver = MagicMock()
        driver.execute_query.return_value = ([], None, None)

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        assert result["retry_count"] == 2

    def test_validate_empty_result_does_not_return_db_results(self):
        """Empty result path must NOT include db_results in result."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([], None, None)

        with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
            result = validate_node(state, driver)

        assert "db_results" not in result


class TestStep1FailureGeneral:
    """General assertions applying to all Step 1 failure modes."""

    def test_validate_failure_does_not_return_db_results(self):
        """On any failure path, db_results must not be in result keys."""
        for driver_behavior, exc in [
            (Exception("err"), True),
            (([], None, None), False),
        ]:
            state = _make_state(retry_count=0)
            driver = MagicMock()
            if exc:
                driver.execute_query.side_effect = driver_behavior
            else:
                driver.execute_query.return_value = driver_behavior

            with patch("src.workflow.nodes.validate.get_llm", return_value=MagicMock()):
                result = validate_node(state, driver)

            assert "db_results" not in result, (
                f"db_results should not be in result for failure mode exc={exc}"
            )


# ---------------------------------------------------------------------------
# Step 2 (Haiku 4.6 Semantic Gate) tests
# ---------------------------------------------------------------------------

class TestStep2SemanticGate:
    """Semantic gate tests: Haiku 4.6 pass/fail evaluation."""

    def test_validate_semantic_gate_called_with_query_and_results(self):
        """Haiku must be called with user_query and db_results JSON in prompt."""
        state = _make_state(retry_count=0, user_query="best fire team")
        driver = MagicMock()
        records = [{"name": "Aldo", "element": "Fire"}]
        driver.execute_query.return_value = (records, None, None)
        mock_haiku = _mock_haiku("PASS: Results match")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            validate_node(state, driver)

        mock_haiku.invoke.assert_called_once()
        call_args = mock_haiku.invoke.call_args
        # The messages arg is the first positional arg
        messages = call_args[0][0]
        # Join all message content to check both user_query and db_results appear
        all_content = " ".join(str(m.content) for m in messages)
        assert "best fire team" in all_content
        assert "Aldo" in all_content  # from JSON of records

    def test_validate_semantic_pass(self):
        """Haiku returning PASS: must return only db_results — no error keys."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        records = [{"name": "Aldo"}]
        driver.execute_query.return_value = (records, None, None)
        mock_haiku = _mock_haiku("PASS: Results correctly match the user's request for fire-element characters.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "db_results" in result
        assert result["db_results"] == [{"name": "Aldo"}]
        assert "validation_errors" not in result
        assert "retry_count" not in result

    def test_validate_success_returns_only_db_results(self):
        """On full success, result must have exactly the db_results key (AGENT-07)."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Aldo"}], None, None)
        mock_haiku = _mock_haiku("PASS: Results match.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert list(result.keys()) == ["db_results"]

    def test_validate_success_returns_db_results(self):
        """Driver returns data + semantic PASS: result has db_results with records."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        records = [{"name": "Aldo"}]
        driver.execute_query.return_value = (records, None, None)
        mock_haiku = _mock_haiku("PASS: The results correctly contain fire-element characters matching the user query.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "db_results" in result
        assert result["db_results"] == [{"name": "Aldo"}]

    def test_validate_semantic_fail(self):
        """Haiku returning FAIL: must return validation_errors + retry_count, no db_results."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Ciel", "element": "Wind"}], None, None)
        mock_haiku = _mock_haiku("FAIL: The query returned Wind-element characters but the user asked for Fire-element teams.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "validation_errors" in result
        assert len(result["validation_errors"]) == 1
        assert "retry_count" in result
        assert result["retry_count"] == 1
        assert "db_results" not in result

    def test_validate_semantic_fail_error_format(self):
        """Semantic fail error must contain 'Semantic Mismatch' and Haiku's explanation."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Ciel", "element": "Wind"}], None, None)
        mock_haiku = _mock_haiku("FAIL: The query returned Wind-element characters but the user asked for Fire-element teams.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        error_msg = result["validation_errors"][0]
        assert "Attempt 1" in error_msg
        assert "Semantic Mismatch" in error_msg
        assert "Wind-element" in error_msg  # Haiku's explanation included

    def test_validate_semantic_fail_error_format_attempt_prefix(self):
        """Semantic fail error must start with 'Attempt {N}: Query failed due to Semantic Mismatch'."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Ciel"}], None, None)
        explanation = "The query returned Wind-element characters but the user asked for Fire-element teams."
        mock_haiku = _mock_haiku(f"FAIL: {explanation}")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        error_msg = result["validation_errors"][0]
        assert error_msg.startswith("Attempt 1: Query failed due to Semantic Mismatch. Context:")
        assert explanation in error_msg

    def test_validate_uses_validator_role(self):
        """get_llm must be called with role='validator'."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Aldo"}], None, None)
        mock_haiku = _mock_haiku("PASS: Match")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku) as mock_get_llm:
            validate_node(state, driver)

        mock_get_llm.assert_called_once_with(role="validator")

    def test_validate_semantic_increments_retry_from_current(self):
        """Semantic fail increments retry_count from current state value."""
        state = _make_state(retry_count=2)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Ciel"}], None, None)
        mock_haiku = _mock_haiku("FAIL: Wrong element group.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert result["retry_count"] == 3

    def test_validate_semantic_fail_does_not_return_db_results(self):
        """Semantic fail path must NOT include db_results in result."""
        state = _make_state(retry_count=0)
        driver = MagicMock()
        driver.execute_query.return_value = ([{"name": "Ciel"}], None, None)
        mock_haiku = _mock_haiku("FAIL: Wrong results.")

        with patch("src.workflow.nodes.validate.get_llm", return_value=mock_haiku):
            result = validate_node(state, driver)

        assert "db_results" not in result
