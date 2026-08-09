"""SSE streaming bridge — LangGraph astream() to FastAPI ServerSentEvent sequence.

pipeline_sse_generator() is the core of the two-phase POST->SSE-GET pattern:
1. POST /api/query stores job payload in app.state.jobs[job_id]
2. GET /api/stream/{job_id} calls this generator wrapped in EventSourceResponse
3. Generator runs LangGraph pipeline and emits events per node completion

Event protocol (per D-11, D-12):
  node_status: JSON {"event": "node_status", "node": str, "attempt": int, "max": int}
  result:      Raw Jinja2-rendered HTML fragment (partials/result.html)
  done:        Empty data — signals HTMX sse-close to close the connection

Node name mapping (per graph.py add_node strings):
  "plan"            -> "PLAN"
  "generate_cypher" -> "CYPHER"
  "validate"        -> "VALIDATE"
  "analyze"         -> "ANALYZE"
  "format"          -> "FORMAT"
"""
import json
import logging
import time
from collections.abc import AsyncIterable

from fastapi.sse import ServerSentEvent
from fastapi.templating import Jinja2Templates

from src.workflow.graph import build_graph, build_production_graph
from src.workflow.production import ProductionRequestError

logger = logging.getLogger(__name__)

# Maps LangGraph add_node() string keys to user-facing display labels (per D-11)
# Keys must match graph.py builder.add_node(...) first argument exactly.
NODE_LABELS: dict[str, str] = {
    "plan": "PLAN",
    "superboss_context": "SUPERBOSS",
    "generate_cypher": "CYPHER",
    "validate": "VALIDATE",
    "prepare_candidates": "CANDIDATES",
    "analyze": "ANALYZE",
    "format": "FORMAT",
    "production_retrieve": "RETRIEVE",
}


def pipeline_error_payload(exc: Exception) -> dict:
    """Return a safe SSE failure payload, preserving typed request diagnostics."""
    payload = {
        "event": "node_status",
        "node": "ERROR",
        "attempt": 1,
        "max": 1,
    }
    if isinstance(exc, ProductionRequestError):
        payload["failure_type"] = exc.issues[0].code if exc.issues else "request.invalid"
        payload["message"] = str(exc)
        payload["issues"] = [issue.model_dump() for issue in exc.issues]
    return payload


async def pipeline_sse_generator(
    query: str,
    roster: list[str],
    driver,
    templates: Jinja2Templates,
    request,
    owned_sidekicks: list[str] | None = None,
    stellar_awakened: dict | None = None,
    boss_id: str | None = None,
    item_policy: str = "late_game_assumed",
    mode: str = "exploratory",
    analyzer_provider: str = "openrouter",
    analyzer_model: str | None = None,
) -> AsyncIterable[ServerSentEvent]:
    """Async generator: run LangGraph pipeline, emit SSE events per node completion.

    Emits:
        node_status events for each LangGraph node (PLAN, CYPHER, VALIDATE, ANALYZE, FORMAT)
        result event: rendered Jinja2 HTML fragment from partials/result.html
        done event: empty — signals HTMX sse-close to close SSE connection

    Disconnect safety: checks request.is_disconnected() before each yield.
    Error safety: catches all exceptions, emits error event, always emits done.

    Args:
        query:     User's natural language query string.
        roster:    List of owned character name strings.
        owned_sidekicks: List of owned sidekick name strings.
        driver:    Neo4j AsyncDriver singleton from app.state (passed from route handler).
        templates: Jinja2Templates instance from the route's templates variable.
        request:   FastAPI Request (used for is_disconnected() check).
    """
    use_production = mode == "production"
    graph = build_production_graph(driver=driver) if use_production else build_graph(driver=driver)
    initial_state = {
        "user_query": query,
        "roster": roster,
        "owned_sidekicks": owned_sidekicks or [],
        "plan_strategy": "",
        "boss_context": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "stellar_awakened": stellar_awakened or {},
        "boss_id": boss_id or "",
        "item_policy": item_policy,
        "workflow_mode": "production" if use_production else "exploratory",
        "analyzer_provider": analyzer_provider,
        "analyzer_model": analyzer_model,
        "analyzer_port": None,
        "analyzer_transport": None,
        "typed_retrieval": {},
        "cypher_retry_count": 0,
        "candidate_bundle": {},
        "candidate_warnings": [],
        "analyzer_call_count": 0,
        "analyzer_correction_rounds": 0,
        "analyzer_usage": [],
        "provider_transport_retries": 0,
        "structured_output_errors": [],
        "candidate_validation_errors": [],
        "analysis_failure": {},
        "final_legality_errors": [],
        "analysis_result": "",
        "alternatives": "",
        "final_output": {},
    }

    final_output = None
    start_ms = time.monotonic()

    try:
        async for chunk in graph.astream(initial_state, stream_mode="updates"):
            # Disconnect detection — stop generator if client closed tab
            if await request.is_disconnected():
                logger.info("Client disconnected during SSE stream — stopping pipeline")
                break

            # stream_mode="updates" yields {node_name: state_update} dicts directly
            for node_name, state_update in chunk.items():
                label = NODE_LABELS.get(node_name, node_name.upper())

                # retry_count is the number of completed failed attempts.
                # The displayed attempt is the next validation attempt.
                if node_name == "validate":
                    retry_count = state_update.get("cypher_retry_count", state_update.get("retry_count", 0))
                    attempt = retry_count + 1
                    max_attempts = 3
                elif node_name == "analyze":
                    attempt = max(1, state_update.get("analyzer_call_count", 1))
                    max_attempts = 2 if "analyzer_provider" in state_update else 3
                else:
                    attempt = 1
                    max_attempts = 1

                event_data = json.dumps({
                    "event": "node_status",
                    "node": label,
                    "attempt": attempt,
                    "max": max_attempts,
                    "cypher_retries": state_update.get("cypher_retry_count", state_update.get("retry_count", 0)),
                    "correction_rounds": state_update.get("analyzer_correction_rounds", 0),
                    "provider_transport_retries": state_update.get("provider_transport_retries", 0),
                    "structured_output_error_count": len(state_update.get("structured_output_errors", [])),
                    "candidate_validation_error_count": len(state_update.get("candidate_validation_errors", [])),
                    "failure_type": state_update.get("analysis_failure", {}).get("type"),
                })

                yield ServerSentEvent(data=event_data, event="node_status")
                logger.debug("SSE node_status: node=%s attempt=%d", label, attempt)

                # Capture final_output from format node for result rendering
                if node_name == "format" and "final_output" in state_update:
                    final_output = state_update["final_output"]
                    elapsed_ms = int((time.monotonic() - start_ms) * 1000)
                    logger.info("latency_ms: %d", elapsed_ms)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline error during SSE stream: %s", exc)
        error_data = json.dumps(pipeline_error_payload(exc))
        yield ServerSentEvent(data=error_data, event="node_status")

    finally:
        # Send final HTML result fragment (D-12: Jinja2 renders server-side)
        if final_output is not None:
            try:
                is_alternatives = bool(final_output.get("alternatives"))
                template_name = (
                    "partials/alternatives.html" if is_alternatives
                    else "partials/result.html"
                )
                template = templates.env.get_template(template_name)
                html = template.render(result=final_output)
                yield ServerSentEvent(raw_data=html, event="result")
                logger.debug("SSE result event emitted (%d chars)", len(html))
            except Exception as render_exc:  # noqa: BLE001
                logger.exception("Failed to render result template: %s", render_exc)

        # Always send done event — HTMX sse-close="done" closes the connection
        yield ServerSentEvent(data="", event="done")
        logger.debug("SSE done event emitted")
