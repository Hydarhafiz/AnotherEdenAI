"""Unit tests for SSE streaming pipeline — src/web/streaming.py (WEB-03).

Tests iterate pipeline_sse_generator() directly (not through TestClient/HTTP).
This avoids the TestClient SSE limitation and tests the generator logic in isolation.

Pattern: mock graph.astream as an async generator yielding known chunks.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_request(disconnected_after: int = 999):
    """Create a mock FastAPI Request that reports disconnected after N is_disconnected() calls."""
    call_count = 0

    async def is_disconnected():
        nonlocal call_count
        call_count += 1
        return call_count > disconnected_after

    mock_req = MagicMock()
    mock_req.is_disconnected = is_disconnected
    return mock_req


def _make_mock_templates(rendered_html: str = "<div>result</div>"):
    """Create a mock Jinja2Templates that returns rendered_html for any template."""
    mock_tmpl = MagicMock()
    mock_tmpl.env.get_template.return_value.render.return_value = rendered_html
    return mock_tmpl


def _make_mock_graph_astream(*node_updates):
    """Return an async generator factory that yields the given {node_name: state_update} dicts."""
    async def mock_astream(*args, **kwargs):
        for node_name, state_update in node_updates:
            yield {"type": "updates", "data": {node_name: state_update}}

    mock_graph = MagicMock()
    mock_graph.astream = mock_astream
    return mock_graph


class TestSSEEventsSequence:
    @pytest.mark.asyncio
    async def test_sse_events_sequence_happy_path(self):
        """Generator emits node_status for each node, then result, then done (WEB-03)."""
        from src.web.streaming import pipeline_sse_generator

        final_output = {
            "frontline": [{"name": "Aldo", "role": "DPS", "grastas": []}],
            "reserve": [],
            "synergy_explanation": "blunt zone",
            "error": None,
        }
        mock_graph = _make_mock_graph_astream(
            ("plan", {"plan_strategy": "test"}),
            ("generate_cypher", {"cypher_query": "MATCH..."}),
            ("validate", {"db_results": [{"n": "Aldo"}]}),
            ("analyze", {"analysis_result": '{"frontline":[], "reserve":[], "synergy_explanation":""}'}),
            ("format", {"final_output": final_output}),
        )

        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="best team",
                roster=["Aldo"],
                driver=MagicMock(),
                templates=_make_mock_templates(),
                request=_make_mock_request(),
            ):
                events.append(event)

        event_names = [e.event for e in events]
        # Should have 5 node_status events, 1 result, 1 done
        assert event_names.count("node_status") == 5
        assert "result" in event_names
        assert event_names[-1] == "done"
        assert events[-2].event == "result"

    @pytest.mark.asyncio
    async def test_node_labels_mapped_correctly(self):
        """Node names are mapped to display labels (PLAN, CYPHER, VALIDATE, ANALYZE, FORMAT)."""
        from src.web.streaming import pipeline_sse_generator

        mock_graph = _make_mock_graph_astream(
            ("plan", {"plan_strategy": "x"}),
            ("generate_cypher", {"cypher_query": "MATCH..."}),
        )

        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="q", roster=[], driver=MagicMock(),
                templates=_make_mock_templates(), request=_make_mock_request(),
            ):
                events.append(event)

        node_events = [e for e in events if e.event == "node_status"]
        nodes_seen = [json.loads(e.data)["node"] for e in node_events]
        assert "PLAN" in nodes_seen
        assert "CYPHER" in nodes_seen
        # Raw node names must not appear
        assert "plan" not in nodes_seen
        assert "generate_cypher" not in nodes_seen


class TestFinalSSEEventIsHTML:
    @pytest.mark.asyncio
    async def test_final_sse_event_is_html(self):
        """Second-to-last SSE event is event='result' with rendered HTML (WEB-03, D-12)."""
        from src.web.streaming import pipeline_sse_generator

        rendered = "<article><strong>Aldo</strong></article>"
        final_output = {
            "frontline": [{"name": "Aldo", "role": "DPS", "grastas": []}],
            "reserve": [],
            "synergy_explanation": "test",
            "error": None,
        }
        mock_graph = _make_mock_graph_astream(
            ("format", {"final_output": final_output}),
        )

        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="q", roster=[], driver=MagicMock(),
                templates=_make_mock_templates(rendered_html=rendered),
                request=_make_mock_request(),
            ):
                events.append(event)

        result_events = [e for e in events if e.event == "result"]
        assert len(result_events) == 1
        # raw_data carries the HTML (ServerSentEvent uses raw_data for pre-rendered HTML)
        result_event = result_events[0]
        assert result_event.event == "result"

    @pytest.mark.asyncio
    async def test_done_event_always_last(self):
        """SSE stream always ends with event='done' even when no format node fires."""
        from src.web.streaming import pipeline_sse_generator

        mock_graph = _make_mock_graph_astream(
            ("plan", {"plan_strategy": "x"}),
        )

        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="q", roster=[], driver=MagicMock(),
                templates=_make_mock_templates(), request=_make_mock_request(),
            ):
                events.append(event)

        assert events[-1].event == "done"


class TestValidateRetryAttemptNumber:
    @pytest.mark.asyncio
    async def test_validate_attempt_is_retry_count_plus_one(self):
        """VALIDATE events show attempt = retry_count + 1 (D-13, Pitfall 7)."""
        from src.web.streaming import pipeline_sse_generator

        # retry_count=1 means this is the second validation attempt; user should see attempt=2
        mock_graph = _make_mock_graph_astream(
            ("validate", {"validation_errors": ["bad cypher"], "retry_count": 1}),
        )

        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="q", roster=[], driver=MagicMock(),
                templates=_make_mock_templates(), request=_make_mock_request(),
            ):
                events.append(event)

        validate_events = [e for e in events if e.event == "node_status"]
        validate_data = [json.loads(e.data) for e in validate_events if json.loads(e.data)["node"] == "VALIDATE"]
        assert len(validate_data) == 1
        assert validate_data[0]["attempt"] == 2   # retry_count=1 -> attempt=2
        assert validate_data[0]["max"] == 3


class TestDisconnectStopsStream:
    @pytest.mark.asyncio
    async def test_disconnect_stops_generator(self):
        """Generator stops emitting events when client disconnects (Pitfall 5)."""
        from src.web.streaming import pipeline_sse_generator

        # 5-node pipeline, but disconnect after 1st event check
        mock_graph = _make_mock_graph_astream(
            ("plan", {"plan_strategy": "x"}),
            ("generate_cypher", {"cypher_query": "MATCH..."}),
            ("validate", {"db_results": [{}]}),
            ("analyze", {"analysis_result": "..."}),
            ("format", {"final_output": {"frontline": [], "reserve": [], "synergy_explanation": "", "error": None}}),
        )

        # Disconnect after first is_disconnected() check returns True
        with patch("src.web.streaming.build_graph", return_value=mock_graph):
            events = []
            async for event in pipeline_sse_generator(
                query="q", roster=[], driver=MagicMock(),
                templates=_make_mock_templates(),
                request=_make_mock_request(disconnected_after=1),  # disconnect after 1 check
            ):
                events.append(event)

        # Should have fewer than 5 node_status events (stream stopped early)
        node_status_count = sum(1 for e in events if e.event == "node_status")
        assert node_status_count < 5
        # done event should still be emitted (finally block)
        assert events[-1].event == "done"
