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
from collections.abc import AsyncIterable

from fastapi.sse import ServerSentEvent
from fastapi.templating import Jinja2Templates

from src.workflow.graph import build_graph

logger = logging.getLogger(__name__)

# Maps LangGraph add_node() string keys to user-facing display labels (per D-11)
# Keys must match graph.py builder.add_node(...) first argument exactly.
NODE_LABELS: dict[str, str] = {
    "plan": "PLAN",
    "generate_cypher": "CYPHER",
    "validate": "VALIDATE",
    "analyze": "ANALYZE",
    "format": "FORMAT",
}


async def pipeline_sse_generator(
    query: str,
    roster: list[str],
    driver,
    templates: Jinja2Templates,
    request,
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
        driver:    Neo4j AsyncDriver singleton from app.state (passed from route handler).
        templates: Jinja2Templates instance from the route's templates variable.
        request:   FastAPI Request (used for is_disconnected() check).
    """
    graph = build_graph(driver=driver)
    initial_state = {
        "user_query": query,
        "roster": roster,
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": "",
        "final_output": {},
    }

    final_output = None

    try:
        async for chunk in graph.astream(initial_state, stream_mode="updates"):
            # Disconnect detection — stop generator if client closed tab
            if await request.is_disconnected():
                logger.info("Client disconnected during SSE stream — stopping pipeline")
                break

            # stream_mode="updates" yields {node_name: state_update} dicts directly
            for node_name, state_update in chunk.items():
                label = NODE_LABELS.get(node_name, node_name.upper())

                # Pitfall 7: retry_count in update is post-increment value.
                # attempt shown to user = retry_count + 1 for validate node.
                if node_name == "validate":
                    retry_count = state_update.get("retry_count", 0)
                    attempt = retry_count + 1
                    max_attempts = 3
                else:
                    attempt = 1
                    max_attempts = 1

                event_data = json.dumps({
                    "event": "node_status",
                    "node": label,
                    "attempt": attempt,
                    "max": max_attempts,
                })

                yield ServerSentEvent(data=event_data, event="node_status")
                logger.debug("SSE node_status: node=%s attempt=%d", label, attempt)

                # Capture final_output from format node for result rendering
                if node_name == "format" and "final_output" in state_update:
                    final_output = state_update["final_output"]

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline error during SSE stream: %s", exc)
        error_data = json.dumps({
            "event": "node_status",
            "node": "ERROR",
            "attempt": 1,
            "max": 1,
        })
        yield ServerSentEvent(data=error_data, event="node_status")

    finally:
        # Send final HTML result fragment (D-12: Jinja2 renders server-side)
        if final_output is not None:
            try:
                template = templates.env.get_template("partials/result.html")
                html = template.render(result=final_output)
                yield ServerSentEvent(raw_data=html, event="result")
                logger.debug("SSE result event emitted (%d chars)", len(html))
            except Exception as render_exc:  # noqa: BLE001
                logger.exception("Failed to render result template: %s", render_exc)

        # Always send done event — HTMX sse-close="done" closes the connection
        yield ServerSentEvent(data="", event="done")
        logger.debug("SSE done event emitted")
