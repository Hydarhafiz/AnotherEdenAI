"""WorkflowState definition for the AnotherEdenAI LangGraph pipeline.

This module defines the single state contract shared by all nodes in the graph.
Each key is owned by at most one node — no key is written by multiple nodes.

Key ownership:
    user_query      — set by caller (input)
    roster          — set by caller (input)
    owned_sidekicks — set by caller (input), normalized by PLAN when present
    plan_strategy   — written by PLAN node only
    cypher_query    — written by GENERATE_CYPHER node only
    db_results      — written by VALIDATE node only (non-empty = success)
    validation_errors — VALIDATE appends via operator.add reducer
    retry_count     — incremented by VALIDATE only (starts 0, cap 3)
    candidate_bundle — written by PREPARE_CANDIDATES as the hard-field authority
    analysis_result — written by ANALYZE after bounded ID validation/correction
    final_output    — written by FORMAT with partial-result legality handling

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
    owned_sidekicks: list[str]
    stellar_awakened: dict
    light_shadow_points: dict
    boss_id: str
    item_policy: str
    workflow_mode: str
    typed_retrieval: dict

    # --- PLAN node output ---
    plan_strategy: str

    # --- SUPERBOSS_CONTEXT node output ---
    boss_context: str

    # --- GENERATE_CYPHER node output ---
    cypher_query: str

    # --- VALIDATE node outputs ---
    db_results: list[dict]
    validation_errors: Annotated[list[str], operator.add]
    retry_count: int
    cypher_retry_count: int

    # --- PREPARE_CANDIDATES node outputs ---
    candidate_bundle: dict
    candidate_warnings: list[str]

    # --- ANALYZE node output ---
    analysis_result: str   # written by ANALYZE only (normal path)
    alternatives: str      # written by ANALYZE only (empty db_results path; raw LLM JSON string)
    analyzer_call_count: int
    analyzer_correction_rounds: int
    analyzer_provider: str
    analyzer_model: str | None
    analyzer_port: object
    analyzer_transport: object
    analyzer_usage: list[dict]
    provider_transport_retries: int
    structured_output_errors: list[dict]
    candidate_validation_errors: list[dict]
    analysis_failure: dict

    # --- FORMAT node output ---
    final_output: dict
    final_legality_errors: list[dict]
