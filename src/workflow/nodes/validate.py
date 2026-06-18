"""VALIDATE node — two-step hybrid gate (deterministic + semantic).

Step 1 (Deterministic): executes Cypher via driver.execute_query().
    - Exception from driver -> append error, increment retry_count, skip Step 2.
    - Empty result set    -> append error, increment retry_count, skip Step 2.

Step 2 (Haiku 4.6 Semantic Gate): if Step 1 passes, ask Haiku whether the
    results actually answer the user's query.
    - FAIL response -> append error, increment retry_count.
    - PASS response -> return db_results only.

Error message format (locked):
    "Attempt {N}: Query failed due to [Exception|Empty Result|Semantic Mismatch]. Context: [detail]"

The driver is injected via closure in graph.py:
    builder.add_node("validate", lambda s: validate_node(s, driver))
    LangGraph resolves async coroutines natively in ainvoke — lambda unchanged.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..context_compaction import compact_records
from ..llm import get_llm
from ..state import WorkflowState

RETRY_CAP = 3

SEMANTIC_GATE_SYSTEM_PROMPT = (
    "You are a validation gate for a game team-building assistant. "
    "The database returns RAW CHARACTER DATA (names, weapons, elements, traits, grastas) "
    "that a downstream AI analyzer will use to build the team recommendation. "
    "Your job is NOT to check if the results already contain a team recommendation — "
    "they never will. Instead, check whether the results contain relevant character "
    "data (weapon types, elements, traits, grastas) that could be used to answer the query. "
    "PASS if the results have any character attributes relevant to the query. "
    "FAIL only if the results are completely wrong data (e.g. wrong characters, empty fields "
    "unrelated to the query, or data for a completely different game mechanic). "
    "Respond with exactly 'PASS: [brief reason]' or 'FAIL: [explanation of mismatch]'."
)


async def validate_node(state: WorkflowState, driver) -> dict:
    """Execute the Cypher query and validate the results via two-step hybrid gate.

    Owned keys written on failure: validation_errors (appended), retry_count.
    Owned keys written on success: db_results.

    Args:
        state: Current WorkflowState.
        driver: Async Neo4j driver instance (injected via closure from graph.py).

    Returns:
        Dict with owned keys updated based on query outcome.
        On success: {"db_results": [records]} only.
        On failure: {"validation_errors": [error_msg], "retry_count": N+1}.
    """
    cypher = state.get("cypher_query", "MATCH (n) RETURN n")
    retry_count = state.get("retry_count", 0)

    # ------------------------------------------------------------------
    # Step 1: Deterministic — execute Cypher via async driver
    # ------------------------------------------------------------------
    try:
        records, _, _ = await driver.execute_query(
            cypher,
            roster=state.get("roster", []),
            owned_sidekicks=state.get("owned_sidekicks", []),
            user_query=state.get("user_query", ""),
            database_="neo4j",
        )
    except Exception as exc:
        error_msg = (
            f"Attempt {retry_count + 1}: Query failed due to Exception. "
            f"Context: {type(exc).__name__}: {exc}"
        )
        return {"validation_errors": [error_msg], "retry_count": retry_count + 1}

    if not records:
        error_msg = (
            f"Attempt {retry_count + 1}: Query failed due to Empty Result. "
            f"Context: Query returned no records -- possible hallucinated traversal path."
        )
        return {"validation_errors": [error_msg], "retry_count": retry_count + 1}

    # ------------------------------------------------------------------
    # Step 2: Haiku 4.6 Semantic Gate
    # ------------------------------------------------------------------
    llm = get_llm(role="validator")
    compacted_records = compact_records(
        records,
        max_records=6,
        max_list_items=2,
        max_string_chars=100,
        max_dict_keys=8,
    )
    results_json = json.dumps(compacted_records, indent=2)
    messages = [
        SystemMessage(content=SEMANTIC_GATE_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"User query: {state['user_query']}\n\n"
                f"Database results (JSON):\n{results_json}"
            )
        ),
    ]
    response = llm.invoke(messages)

    if response.content.strip().upper().startswith("PASS"):
        # Both steps pass — return only db_results
        return {"db_results": [dict(r) for r in records]}

    # Semantic fail — extract explanation from Haiku's response
    content = response.content.strip()
    if content.upper().startswith("FAIL:"):
        explanation = content[5:].strip()
    elif content.upper().startswith("FAIL"):
        explanation = content[4:].strip()
    else:
        explanation = content

    error_msg = (
        f"Attempt {retry_count + 1}: Query failed due to Semantic Mismatch. "
        f"Context: {explanation}"
    )
    return {"validation_errors": [error_msg], "retry_count": retry_count + 1}
