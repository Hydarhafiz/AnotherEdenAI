"""WorkflowState definition for the AnotherEdenAI LangGraph pipeline.

This module defines the single state contract shared by all nodes in the graph.
Each key is owned by at most one node — no key is written by multiple nodes.

Key ownership:
    user_query      — set by caller (input)
    roster          — set by caller (input)
    plan_strategy   — written by PLAN node only
    cypher_query    — written by GENERATE_CYPHER node only
    db_results      — written by VALIDATE node only (non-empty = success)
    validation_errors — VALIDATE appends via operator.add reducer
    retry_count     — incremented by VALIDATE only (starts 0, cap 3)
    analysis_result — written by ANALYZE only (intermediate synthesis text)
    final_output    — written by FORMAT only (structured recommendation dict)

Note on analysis_result:
    This intermediate key resolves the ANALYZE->FORMAT ambiguity. ANALYZE writes
    its synthesis text here; FORMAT reads it and produces the structured final_output
    dict. This keeps the two nodes independently testable.
"""
import operator
from typing import Annotated

from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """State container for the AnotherEdenAI team-recommendation workflow."""

    # --- Caller-provided inputs ---
    user_query: str
    roster: list[str]

    # --- PLAN node output ---
    plan_strategy: str

    # --- GENERATE_CYPHER node output ---
    cypher_query: str

    # --- VALIDATE node outputs ---
    db_results: list[dict]
    validation_errors: Annotated[list[str], operator.add]
    retry_count: int

    # --- ANALYZE node output ---
    analysis_result: str

    # --- FORMAT node output ---
    final_output: dict
