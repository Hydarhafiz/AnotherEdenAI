# AnotherEdenAI Milestone

## Executive Summary

AnotherEdenAI has a production-style v1 baseline: ETL into Neo4j, a five-step LangGraph query pipeline, fallback alternatives output, and a streaming FastAPI web interface. The next planning horizon is to extend recommendation depth without breaking the current roster-constrained, schema-driven architecture.

## Scope

This milestone tracks the next major feature set after the current v1 baseline. It is intended to be overwritten by future planning sessions when a more specific epic is scoped.

## Non-Goals

- Rewriting the entire web stack away from FastAPI, Jinja2, or HTMX
- Replacing Neo4j with a different storage backend
- Broad refactors that are not tied to a milestone feature
- Reading or relying on local secret values for planning

## Dependencies And Assumptions

- `SCHEMA.md` remains the source of truth for graph structure
- Existing workflow stages remain in place unless a milestone explicitly changes them
- Neo4j-backed roster-constrained recommendations remain the core product behavior
- New features should preserve graceful fallback behavior and testability

## Current Completion Status

- v1 baseline: complete
- v2 planning: in progress
- v3 planning: not started

## Prioritized Feature Checklist

- [ ] Feature A: AF Zone And Combat Context Reasoning
  Status: Not started
  Goal: Expand recommendation quality by incorporating AF zone and battle-context reasoning into the workflow.
  Technical requirements:
  - Define the minimum additional graph or prompt context required for AF zone reasoning.
  - Preserve the current workflow structure unless a new node is justified.
  - Keep the recommendation output understandable and attributable.
  Acceptance criteria:
  - The system can answer at least one AF-zone-aware team-building request with grounded reasoning.
  - The feature does not break existing happy-path query handling.

- [ ] Feature B: Grasta Optimization And Scoring
  Status: Not started
  Goal: Move beyond compatibility-only matching into ranked build quality.
  Technical requirements:
  - Define a deterministic or semi-deterministic scoring strategy for Grasta selection.
  - Keep schema and output changes documented if ranking metadata is introduced.
  - Ensure recommendation formatting can explain why one setup outranks another.
  Acceptance criteria:
  - Queries that request strongest or highest-damage options return visibly ranked recommendations.
  - Ranking logic is testable and does not rely on hidden assumptions.

- [ ] Feature C: Farming And Dungeon Advisor
  Status: Not started
  Goal: Extend the product from single-query team assembly into actionable farming guidance.
  Technical requirements:
  - Define the data model and retrieval strategy for dungeon or farming context.
  - Decide whether this lives in the current graph, a side knowledge source, or both.
  - Preserve clear separation between graph facts and generated advice.
  Acceptance criteria:
  - The system can answer at least one farming-oriented request with explicit tradeoffs.
  - Source boundaries remain clear in the final output.

- [ ] Feature D: Observability And Operator Workflow Hardening
  Status: Not started
  Goal: Make debugging, refresh operations, and performance tracking easier as the system grows.
  Technical requirements:
  - Identify the minimum metrics and logs needed for workflow debugging and latency tracking.
  - Keep admin operations documented in `README.md`.
  - Avoid introducing secrets into logs or docs.
  Acceptance criteria:
  - Operators can identify workflow failure stage and latency without deep code digging.
  - Refresh and runtime troubleshooting steps remain documented and current.

## Open Questions

- Should AF zone reasoning be represented mostly through graph data, prompt logic, or a hybrid approach?
- What ranking philosophy should govern Grasta optimization: strict deterministic heuristics, LLM-assisted ranking, or a hybrid?
- Which v2 feature should be the first implementation target once a new planning session begins?
