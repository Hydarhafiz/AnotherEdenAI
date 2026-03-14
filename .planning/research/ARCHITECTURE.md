# Architecture Research

## System Overview

```
                    ┌─────────────────┐
                    │   Web Browser   │
                    │  (HTMX + HTML)  │
                    └────────┬────────┘
                             │ HTTP
                    ┌────────▼────────┐
                    │  FastAPI App    │
                    │  /api/query     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ LangGraph       │
                    │ Workflow Engine │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ PLAN Agent  │   │ GEN_CYPHER  │   │  ANALYZE    │
    │ Sonnet 4.6  │   │ Sonnet 4.6  │   │ Sonnet 4.6  │
    └─────────────┘   └──────┬──────┘   └──────┬──────┘
                             │                 │
                    ┌────────▼────────┐        │
                    │ VALIDATE Agent  │        │
                    │  Haiku 4.6      │        │
                    │  (3x retry cap) │        │
                    └────────┬────────┘        │
                             │                 │
                    ┌────────▼─────────────────▼────┐
                    │         Neo4j Graph DB         │
                    │  Characters / Traits / Grasta  │
                    └────────────────────────────────┘
                             ▲
                    ┌────────┴────────┐
                    │  Data Pipeline  │
                    │ (wiki scraper   │
                    │  + ETL loader)  │
                    └─────────────────┘
```

## LangGraph State Machine

```python
# Nodes (agents)
PLAN  →  GENERATE_CYPHER  →  VALIDATE  →  ANALYZE  →  FORMAT

# Conditional edges
VALIDATE:
  - pass  → ANALYZE
  - fail + retry_count < 3  → GENERATE_CYPHER (with error context)
  - fail + retry_count == 3 → FORMAT (with graceful error message)
```

### State Schema

```python
class WorkflowState(TypedDict):
    user_query: str          # Natural language input
    user_roster: list[str]   # Character names (owned units + F2P)
    plan: str                # PLAN agent output
    cypher_query: str        # Generated Cypher
    query_results: list      # Neo4j response
    validation_error: str    # Error message if VALIDATE fails
    retry_count: int         # Max 3
    analysis: str            # ANALYZE agent output
    final_response: dict     # Formatted team recommendation
```

## Component Responsibilities

### 1. Data Pipeline (scraper + ETL)
- **Runs independently** from the query workflow
- Scrapes anothereden.wiki → transforms to graph-ready format
- Loads into Neo4j using `neo4j` Python driver
- Idempotent: re-runs overwrite stale data

### 2. Neo4j Graph Schema

```cypher
// Nodes
(:Character {name, element, weapon, light_shadow, is_f2p})
(:Trait {name})
(:Grasta {name, category, tier, is_shareable, stats})
(:Ore {name, category, stats, source})

// Relationships
(:Character)-[:HAS_TRAIT]->(:Trait)
(:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
(:Ore)-[:ENHANCES]->(:Grasta)
```

### 3. LangGraph Workflow

- Single `StateGraph` with typed state
- Each node receives full state, returns partial state update
- VALIDATE node controls routing via conditional edge
- No memory/persistence needed (stateless per-request)

### 4. FastAPI API Layer

```
POST /api/query
  Body: { query: str, roster: [str] }
  Response: { team: [...], synergies: [...], explanation: str }

GET /
  Server-rendered UI via Jinja2 + HTMX

POST /admin/refresh-data
  Trigger data pipeline scrape + Neo4j reload
```

### 5. Frontend (HTMX + Jinja2)

- Form: roster input (multi-select or free text) + query box
- Submit → HTMX posts to `/api/query` → swaps result div in-place
- Loading state shows pipeline progress (PLAN → CYPHER → VALIDATE → ANALYZE)
- No page reloads

## Build Order (Phase Dependencies)

```
Phase 1: Neo4j Schema + Data Pipeline
  → Without data in graph, no queries possible

Phase 2: LangGraph Workflow (stub data)
  → Build + test agent flow with mock Neo4j responses

Phase 3: Connect Workflow to Neo4j
  → GENERATE_CYPHER queries real graph

Phase 4: FastAPI + Frontend
  → Expose workflow via HTTP, add HTMX UI

Phase 5: Integration + Polish
  → End-to-end testing, error handling, validation
```

## Secrets Management

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
ANTHROPIC_API_KEY=...
```

All via `.env` + `python-dotenv`. Never hardcoded.

---
*Generated: 2026-03-14 (training knowledge, web search unavailable)*
