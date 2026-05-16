# AnotherEdenAI Architecture

## Purpose

AnotherEdenAI is a GraphRAG application for building roster-constrained team recommendations for the JRPG *Another Eden*. The system combines a scraped and normalized Neo4j graph with a multi-step LangGraph workflow and a lightweight FastAPI web UI.

This document is the architectural source of truth for implementation planning. Use it alongside `SCHEMA.md` for any feature that changes data shape, graph traversal logic, prompt contracts, API behavior, or UI integration.

## Five Pillars

The project keeps five root documents as planning and release anchors:

- `milestone.md`: active epic scope, feature order, and completion state
- `CHANGELOG.md`: historical change log by phase and release
- `architecture.md`: current system design, boundaries, and extension points
- `SCHEMA.md`: graph contract and data-shape source of truth
- `README.md`: setup, execution, and operator-facing guidance

Supplementary planning context:

- `future-ideas.md`: deferred ideas and next-milestone candidates that should not yet be promoted into the active implementation contract

## System Overview

The system has three major layers:

1. ETL and graph loading
2. Query-time workflow orchestration
3. Web delivery and streaming UX

At a high level:

- Wiki data is scraped and normalized into Pydantic ETL models.
- The ETL pipeline loads Characters, Traits, Skills, PassiveSkills, Grastas, and Ores into Neo4j with idempotent MERGE behavior.
- User roster input is normalized and augmented with free-to-play units.
- A five-node LangGraph pipeline plans the query, generates Cypher, validates it, analyzes results, and formats the output.
- FastAPI exposes query and admin routes, while SSE streams progress back to the browser.

## Runtime Components

### ETL Layer

- Entry point: `src/etl/run_etl.py`
- Scraper: `src/etl/scraper.py`
- Data models: `src/etl/models.py`
- Loader: `src/etl/loader.py`
- Constants and thresholds: `src/etl/constants.py`

Responsibilities:

- Retrieve live wiki pages with `nodriver`
- Parse Characters, character detail combat entries, Grastas, and Ores
- Validate records with Pydantic
- Load normalized entities into Neo4j
- Assert schema expectations after load

Feature B combat graph behavior:

- Character index rows exclude sidekick-only records before character-detail crawling.
- Character detail crawl targets use canonical wiki hrefs from the Characters index, preserving alias/style pages such as `Dark_Devourer` and `Noble_Blossom_(Another_Style)`.
- Character detail pages produce `Skill` rows for active skills and basic attack replacements, plus `PassiveSkill` rows for non-executable mechanics such as stances and zones.
- Character detail validation requires recognizable active combat skills; partial or blocked pages with zero skills fail the selected ETL scope.
- Stellar Awakening availability is inferred from both index metadata and character detail page sections.

### Workflow Layer

- Graph wiring: `src/workflow/graph.py`
- State contract: `src/workflow/state.py`
- LLM provider factory: `src/workflow/llm.py`
- Roster utilities: `src/workflow/normalize.py`, `src/workflow/f2p.py`
- Nodes: `src/workflow/nodes/`

Current workflow sequence:

1. `PLAN`
2. `GENERATE_CYPHER`
3. `VALIDATE`
4. `ANALYZE`
5. `FORMAT`

Routing notes:

- `VALIDATE` is the quality gate.
- Validation failures retry Cypher generation up to three times.
- Graceful fallback formatting is required when retries are exhausted.
- Alternatives output is supported when no exact ideal team exists.

### Web Layer

- FastAPI entry point: `src/web/app.py`
- Route modules: `src/web/routes/`
- SSE bridge: `src/web/streaming.py`
- Driver dependency management: `src/web/dependencies.py`
- Templates and static assets: `src/web/templates/`, `src/web/static/`

Responsibilities:

- Accept roster and natural-language query input
- Start background workflow execution
- Stream progress updates over SSE
- Render final result or graceful failure UI
- Expose admin-triggered ETL refresh

## Data and Contract Boundaries

`SCHEMA.md` is the contract authority for graph structure. Any feature that changes node labels, properties, relationships, output payload assumptions, or query semantics must be evaluated against `SCHEMA.md`.

Important boundaries:

- ETL models must conform to the schema contract before Neo4j load
- Workflow prompts and Cypher generation must assume only documented graph shapes
- Web responses must remain compatible with the current formatting layer and templates

## External Dependencies

- Neo4j 5 for graph storage
- Anthropic, OpenRouter, Bedrock, or Ollama through the LLM provider factory
- `nodriver` plus Chrome for scraping
- FastAPI, Jinja2, and HTMX for web delivery

## Operational Constraints

- The validation retry cap is a hard cost-control mechanism and should not be bypassed casually.
- The scraper depends on a real browser environment and is sensitive to Cloudflare behavior.
- The graph contract should remain stable before prompt or Cypher examples are expanded.
- The UI is intentionally lightweight; major frontend changes should preserve streaming visibility and failure transparency.

## Current Architectural Priorities

- Preserve roster-constrained correctness and zero hallucinated mechanics
- Keep graph contract changes deliberate and documented
- Maintain clear separation between ETL, workflow, and web concerns
- Favor observable, testable nodes over opaque prompt chains
- Keep fallback behavior graceful when exact recommendations are unavailable

## Known Extension Points

- AF zone mechanics and damage scoring
- Grasta stat optimization and build ranking
- Dungeon and farming recommendation workflows
- Superboss guide generation and stopper analysis
- Richer admin and observability features

## Change Guidance

Update this file when a change affects any of the following:

- System boundaries or component ownership
- New runtime dependencies or infrastructure assumptions
- Data flow between ETL, workflow, and web layers
- Request lifecycle or output semantics
- Architectural decisions that future feature work must honor
