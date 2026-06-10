# Another Eden AI — GraphRAG Team Builder

A production-grade AI system that answers natural-language team-building questions for the JRPG *Another Eden*, constrained to the player's actual roster with zero hallucinated mechanics.

> **Portfolio note:** This project demonstrates a full MLOps pipeline — from graph ETL through multi-agent LLM orchestration to a streaming web UI — built end-to-end using Claude Sonnet 4.6, LangGraph, and Neo4j.

---

## What It Does

You type: *"What's the highest-damage blunt-zone synergy I can build from my roster?"*

The system:
1. Scrapes live character, sidekick, curated superboss, Grasta, Ore, weapon, and armor data from the community wiki into a Neo4j graph
2. Normalises your roster input to canonical graph names and augments it with free-to-play units
3. Routes your question through a 5-node LangGraph agent pipeline (PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE → FORMAT)
4. Streams pipeline progress to your browser via SSE — "Validating... attempt 2/3" — so you know it's working
5. Returns a 4-frontline / 2-reserve team with per-character role annotations, Grasta+trait source attribution, and — when no perfect match exists — the top 3 closest alternatives with tradeoff explanations

---

## Architecture

```
Browser (HTMX + SSE)
        │
        ▼
FastAPI Web Layer  ──── POST /api/query ──────┐
        │                                      │
        │            LangGraph Pipeline        │
        │  ┌────────────────────────────────┐  │
        │  │  PLAN  →  GENERATE_CYPHER  →  │  │
        └─►│  VALIDATE (max 3 retries)  →  │──┘
           │  ANALYZE  →  FORMAT           │
           └──────────┬─────────────────────┘
                      │
                      ▼
              Neo4j Graph Database
   (Characters, Traits, Skills, Sidekicks,
    Superbosses, Grastas, Ores, Equipment)
                      ▲
                      │
               ETL Pipeline
        (nodriver scraper → Pydantic models → MERGE loader)
```

### Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Web framework | FastAPI + Jinja2 + HTMX |
| Streaming | Server-Sent Events (SSE) |
| Agent orchestration | LangGraph 1.0 StateGraph |
| Reasoning LLM | Claude Sonnet 4.6 (PLAN, CYPHER, ANALYZE nodes) |
| Validation LLM | Claude Haiku 4.5 (VALIDATE node — fast and cheap) |
| Graph database | Neo4j 5 (AuraDB Free or local Docker) |
| Graph client | langchain-neo4j `Neo4jGraph` + async driver |
| ETL scraping | nodriver (async headless Chrome, Cloudflare bypass) |
| Data validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Package manager | uv |
| Local LLM (dev) | Ollama (`LLM_PROVIDER=ollama`) |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- Docker (for local Neo4j) **or** a free [AuraDB](https://neo4j.com/cloud/platform/aura-graph-database/) instance
- Anthropic API key (or Ollama for local dev)

### 2. Clone and install

```bash
git clone https://github.com/Hydarhafiz/AnotherEdenAI.git
cd AnotherEdenAI
uv sync
```

### Python Environment Policy

Run project commands from the repository root:

```bash
cd /home/shogunix/AnotherEdenAI
```

Use `uv` as the primary Python runner and dependency manager:

```bash
uv sync
uv run python -m src.etl.run_etl
uv run python assert_schema.py
uv run pytest tests/unit -q
```

Avoid bare `python`, `pytest`, or `pip install ...` for normal project work because they can target a different interpreter or environment. Keep `pip` only as a fallback for bootstrapping `uv` on a new machine when no OS package, standalone installer, or `uv` binary is available.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

| Variable | Required | Description |
|----------|----------|-------------|
| `NEO4J_URI` | yes | Bolt URI — `bolt://localhost:7687` (Docker) or AuraDB URI |
| `NEO4J_AUTH` | yes | Credentials in `user/pass` format |
| `LLM_PROVIDER` | yes | `anthropic` (production) or `ollama` (local dev, no API cost) |
| `ANTHROPIC_API_KEY` | if `anthropic` | Your Anthropic API key |
| `OPENROUTER_API_KEY` | if `openrouter` | OpenRouter key (alternative provider) |
| `OLLAMA_MODEL` | no | Ollama model name (default: `llama3.2`) |
| `ETL_MODE` | no | `strict` (default) or `lenient` |
| `ADMIN_KEY` | yes | Secret for `POST /admin/refresh-data`; sent as `X-Admin-Key` header |

### 4. Start Neo4j

```bash
# Local Docker
docker compose up -d
# Wait ~30s for Neo4j to be ready, then verify at http://localhost:7474
```

### 5. Run the ETL pipeline

This scrapes the selected wiki scope and loads it into Neo4j, including characters, combat skills, sidekicks, curated weak superbosses, Grastas, Ores, and baseline weapon/armor equipment:

```bash
uv run python -m src.etl.run_etl
uv run python assert_schema.py   # must exit 0
```

> **Note:** The scraper uses a nodriver headless browser to bypass Cloudflare. It requires a display (DISPLAY=:0 on WSL2/Linux, or runs natively on macOS/Windows Chrome).
>
> For crawl scopes, parsed-only reruns, manifest inspection, cache layout, and troubleshooting, use [ETL_GUIDE.md](guides/ETL_GUIDE.md).

### 6. Run the tests

```bash
# Unit + workflow tests only (no Neo4j needed)
uv run pytest tests/unit tests/workflow tests/web --tb=short

# Full suite including integration tests (requires loaded Neo4j)
uv run pytest --tb=short
```

### 7. Start the web app

```bash
uv run fastapi dev src/web/app.py
# Open http://localhost:8000
```

Enter your roster (comma-separated character names) and ask a natural-language question. Pipeline progress streams live to the page.

---

## Running Without API Keys (Ollama)

Set `LLM_PROVIDER=ollama` and install [Ollama](https://ollama.com). The default model is `llama3.2`:

```bash
ollama pull llama3.2
# In .env:
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

All LLM calls route through Ollama — no Anthropic API spend.

---

## Project Structure

```
AnotherEdenAI/
├── src/
│   ├── etl/
│   │   ├── constants.py       # EXPECTED_NODE_COUNTS, wiki URLs
│   │   ├── models.py          # Pydantic v2 ETL boundary models
│   │   ├── scraper.py         # nodriver async wiki scraper
│   │   ├── loader.py          # Idempotent MERGE-based Neo4j loader
│   │   └── run_etl.py         # ETL orchestrator entry point
│   ├── workflow/
│   │   ├── state.py           # WorkflowState TypedDict (Pydantic v2)
│   │   ├── graph.py           # LangGraph StateGraph wiring
│   │   ├── llm.py             # get_llm(role) factory — LLM_PROVIDER switch
│   │   ├── normalize.py       # Character name normalisation
│   │   ├── f2p.py             # Free-to-play roster augmentation
│   │   ├── run.py             # CLI entry point
│   │   └── nodes/
│   │       ├── plan.py        # PLAN node (Sonnet 4.6)
│   │       ├── cypher.py      # GENERATE_CYPHER node (Sonnet 4.6)
│   │       ├── validate.py    # VALIDATE node (Haiku 4.5, retry loop)
│   │       ├── analyze.py     # ANALYZE node (Sonnet 4.6)
│   │       └── format.py      # FORMAT node — TeamOutput / AlternativesOutput
│   └── web/
│       ├── app.py             # FastAPI app with lifespan handler
│       ├── dependencies.py    # Neo4j driver singleton
│       ├── streaming.py       # SSE pipeline_sse_generator
│       ├── routes/
│       │   ├── api.py         # POST /api/query, GET /api/stream/{job_id}
│       │   ├── admin.py       # POST /admin/refresh-data (ADMIN_KEY protected)
│       │   └── pages.py       # GET / (index page)
│       ├── templates/         # Jinja2 HTML templates + HTMX partials
│       └── static/            # CSS + JS
├── tests/
│   ├── unit/                  # ETL model and scraper unit tests
│   ├── workflow/              # LangGraph node unit tests (all mocked)
│   ├── web/unit/              # FastAPI route unit tests
│   └── integration/           # Live Neo4j integration tests
├── SCHEMA.md                  # Graph schema contract (v1.0.0)
├── assert_schema.py           # Post-ETL schema assertion script
├── docker-compose.yml         # Neo4j 5 + APOC
└── pyproject.toml
```

---

## Graph Schema

The Neo4j graph models roster heroes, combat facts, build context, and RAG retrieval targets:

```
(:Character)-[:HAS_TRAIT]->(:Trait)<-[:REQUIRES_TRAIT]-(:Grasta)
(:Character)-[:HAS_SKILL]->(:Skill)
(:Character)-[:HAS_PASSIVE_SKILL]->(:PassiveSkill)
(:Character)-[:UNLOCKS_SIDEKICK]->(:Sidekick)
(:Sidekick)-[:HAS_AUTO_SKILL|HAS_CHARGE_SKILL]->(:SidekickSkill)
(:Sidekick)-[:HAS_AURA]->(:SidekickAura)
(:Superboss)

(:Ore)
(:Equipment)
```

Full contract: [SCHEMA.md](SCHEMA.md) - versioned at SCHEMA_VERSION: 1.0.0.

### Verified ETL Snapshot

Milestone 3 verified baseline equipment output on 2026-06-09 with 888 Equipment nodes: 664 weapons and 224 armor records. Character, skill, passive skill, sidekick, superboss, Grasta, Ore, and Trait counts vary by selected crawl scope and should be checked with uv run python assert_schema.py after ETL.

The original Grasta synergy path remains available: a character-compatible shareable Grasta is one where (c)-[:HAS_TRAIT]->(t)<-[:REQUIRES_TRAIT]-(g {is_shareable: true}). Milestone 3 adds RAG-ready retrieval paths for sidekick associations, sidekick abilities and auras, boss affinities and mechanics text, and baseline equipment context.

---

## LangGraph Pipeline

```
START → PLAN → GENERATE_CYPHER → VALIDATE ─► ANALYZE → FORMAT → END
                      ▲               │
                      └── retry ──────┘ (max 3x, then graceful error)
```

| Node | Model | Responsibility |
|------|-------|---------------|
| PLAN | Sonnet 4.6 | Decompose query into graph traversal sub-goals |
| GENERATE_CYPHER | Sonnet 4.6 | Produce Cypher with injected schema + few-shot examples |
| VALIDATE | Haiku 4.5 | Syntax check + non-empty result gate; retry on failure |
| ANALYZE | Sonnet 4.6 | Synthesise results into team recommendation with attribution |
| FORMAT | — | Structure into `TeamOutput` or `AlternativesOutput` Pydantic model |

When `VALIDATE` fails three times the graph routes to graceful error formatting — the retry cap is a hard budget guard against runaway API costs.

---

## Key Engineering Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph `StateGraph` over plain function chain | Explicit conditional edges, first-class retry loop, testable node isolation |
| `WorkflowState` as Pydantic-validated `TypedDict` | Nodes return only the keys they own — mutation bugs surface immediately in tests |
| Haiku for VALIDATE, Sonnet for reasoning | Haiku is fast and cheap enough for a syntax gate; Sonnet earns its cost on PLAN and ANALYZE |
| 3× retry hard cap on VALIDATE | Personal API budget guard — prevents runaway Sonnet spend on broken Cypher loops |
| `LLM_PROVIDER` env var factory | `ollama` for local dev, `anthropic` for production — same code path, zero code changes |
| nodriver (undetected headless Chrome) over httpx | Cloudflare Turnstile blocks headless scrapers; nodriver spoofs a real browser fingerprint |
| Idempotent MERGE loader | Re-running ETL is safe — no duplicate nodes, stale data is overwritten in place |
| SSE over WebSocket | One-way server-push is sufficient for pipeline progress; SSE requires no upgrade handshake |
| `AlternativesOutput` fallback path | When no exact team match exists, return top 3 alternatives rather than an error — avoids dead ends |

---

## Development Notes

**Local LLM budget tip:** Set `LLM_PROVIDER=ollama` during development. All five nodes switch to your local model automatically — no API spend until you flip to `anthropic` for final validation.

**ETL without a browser:** The nodriver scraper requires Chrome. On headless CI or Docker, set `DISPLAY=:0` (WSL2 has this available). A future version could swap in a static fixture for CI.

**Admin data refresh:** `POST /admin/refresh-data` with header `X-Admin-Key: <your-ADMIN_KEY>` re-runs the full ETL pipeline against the live Neo4j instance.

## Root Project Docs

The project uses five root-level planning and release documents:

- `milestone.md` for active epic scope and feature sequencing
- `CHANGELOG.md` for release history
- `architecture.md` for current system design and boundaries
- `SCHEMA.md` for graph contract changes
- `README.md` for setup and operator workflow

Operator-facing ETL and scraping runbooks live in `ETL_GUIDE.md`.

These are intended to stay in the repository root so planning, build, test, and release workflows can use the same source of truth across future milestones.

Supplementary planning notes live in `future-ideas.md`. That file is the parking lot for promising ideas intentionally deferred from the active milestone so brainstorming can stay focused without losing good follow-up directions.

---

## Roadmap

| Version | Focus |
|---------|-------|
| Milestone 4 (active) | Legal 6-hero plus 2-sidekick lineup recommendation intelligence |
| Milestone 5 | AI agent optimization, evaluation, and cost control |
| Milestone 6 | Portfolio frontend experience |
| Milestone 7 | Cost-controlled demo deployment |

---

## License

MIT — see [LICENSE](LICENSE).
