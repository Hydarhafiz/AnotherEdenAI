"""Feature C partial formatting, classified failure, routing, and SSE tests."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workflow.candidates import resolve_candidate_recommendations
from src.workflow.graph import route_after_validate
from src.workflow.nodes.format import format_and_validate_node, format_node
from tests.workflow.test_candidates import candidate_bundle, candidate_lineup


def _resolved_set(count=2):
    bundle = candidate_bundle()
    proposals = [
        candidate_lineup(bundle, archetype=value)
        for value in ("burst", "sustain", "hybrid")[:count]
    ]
    return resolve_candidate_recommendations(proposals, bundle, [])


def test_format_accepts_one_or_two_valid_lineups_with_missing_archetype_warning():
    payload = _resolved_set(count=2)

    result = format_node(
        {"analysis_result": json.dumps(payload), "db_results": [{"ok": True}], "retry_count": 0}
    )["final_output"]

    assert len(result["recommendations"]) == 2
    assert any("Missing valid archetypes" in warning for warning in result["warnings"])
    assert result.get("error") is None


def test_zero_valid_lineups_returns_classified_graceful_failure():
    result = format_node(
        {
            "analysis_failure": {
                "type": "analyzer_correction_exhausted",
                "message": "No fully valid lineup remained after the correction cap.",
                "diagnostics": [{"code": "id.character"}],
            },
            "db_results": [{"ok": True}],
            "retry_count": 0,
        }
    )["final_output"]

    assert result["error_type"] == "analyzer_correction_exhausted"
    assert result["frontline"] == []
    assert result["diagnostics"][0]["code"] == "id.character"


@pytest.mark.asyncio
async def test_final_legality_discards_only_invalid_lineup():
    payload = _resolved_set(count=2)
    state = {
        "analysis_result": json.dumps(payload),
        "db_results": [{"ok": True}],
        "retry_count": 0,
        "roster": ["Akane (Alter),Blooming Blade", *[f"Hero {index}" for index in range(1, 6)]],
        "owned_sidekicks": ["Tetra"],
        "stellar_awakened": {},
        "boss_context": "",
    }

    with patch("src.workflow.nodes.format.collect_legality_context", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("src.workflow.nodes.format.validate_lineup_legality", side_effect=[MagicMock(), ValueError("bad sustain")]):
        result = await format_and_validate_node(state, MagicMock())

    assert [item["archetype"] for item in result["final_output"]["recommendations"]] == ["burst"]
    assert result["final_legality_errors"][0]["path"] == "recommendations.1"
    assert any("Discarded 1 lineup" in warning for warning in result["final_output"]["warnings"])


def test_validate_routing_separates_retry_success_and_exhaustion():
    assert route_after_validate({"db_results": [{"ok": True}], "retry_count": 0}) == "prepare_candidates"
    assert route_after_validate({"db_results": [], "retry_count": 1}) == "generate_cypher"
    assert route_after_validate({"db_results": [], "retry_count": 3}) == "format"


@pytest.mark.asyncio
async def test_sse_exposes_candidate_and_analyzer_correction_metrics():
    from src.web.streaming import pipeline_sse_generator

    async def astream(*args, **kwargs):
        yield {"prepare_candidates": {"candidate_bundle": {"coverage": {"complete": True}}}}
        yield {
            "analyze": {
                "analysis_result": "{}",
                "analyzer_call_count": 3,
                "analyzer_correction_rounds": 2,
                "provider_transport_retries": 1,
                "structured_output_errors": [{"code": "invalid_json"}],
                "candidate_validation_errors": [{"code": "id.skill"}],
                "cypher_retry_count": 1,
                "analysis_failure": {},
            }
        }

    graph = MagicMock()
    graph.astream = astream
    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)
    templates = MagicMock()

    with patch("src.web.streaming.build_graph", return_value=graph):
        events = [
            event
            async for event in pipeline_sse_generator(
                query="Mimi", roster=[], driver=MagicMock(), templates=templates, request=request
            )
        ]

    node_payloads = [json.loads(event.data) for event in events if event.event == "node_status"]
    assert node_payloads[0]["node"] == "CANDIDATES"
    analyze = next(payload for payload in node_payloads if payload["node"] == "ANALYZE")
    assert analyze["attempt"] == 3
    assert analyze["correction_rounds"] == 2
    assert analyze["provider_transport_retries"] == 1
    assert analyze["structured_output_error_count"] == 1
    assert analyze["candidate_validation_error_count"] == 1
