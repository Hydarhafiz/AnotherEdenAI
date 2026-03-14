# Stack Research

## Core Stack (Locked by Project Constraints)

| Layer | Choice | Version | Notes |
|-------|--------|---------|-------|
| Language | Python | 3.11+ | Required by stack |
| Agent Orchestration | LangGraph | 0.2.x | Multi-agent workflow |
| Graph DB | Neo4j | 5.x | AuraDB Free tier (cloud) or local |
| LLM Router (Reasoning) | Claude Sonnet 4.6 | Latest | PLAN, GENERATE_CYPHER, ANALYZE |
| LLM Router (Validation) | Claude Haiku 4.6 | Latest | VALIDATE node only |
| LLM Client | anthropic | 0.27+ | Official Python SDK |

## Web Framework

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **FastAPI** | ✅ Recommended | Async-native, Pydantic models, auto OpenAPI docs |
| Flask | ✗ Skip | Sync-only, poor async story |
| Django | ✗ Skip | Overkill for this use case |

FastAPI pairs well with LangGraph's async execution model.

## Graph DB Integration

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **neo4j** (official driver) | ✅ Use | `pip install neo4j` — async sessions supported |
| **langchain-neo4j** | ✅ Use | Pre-built Neo4jGraph, Text2Cypher chain, GraphRAG helpers |
| py2neo | ✗ Skip | Unmaintained, less Neo4j 5.x support |

Key: `langchain-neo4j` provides `Neo4jGraph`, `GraphCypherQAChain`, and `Neo4jVector` without needing to implement from scratch.

## Data Pipeline

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **httpx** | ✅ Recommended | Async HTTP, replaces requests for async pipeline |
| **BeautifulSoup4** | ✅ Keep | HTML parsing, well-tested |
| requests | ✗ Skip | Sync-only, blocks event loop |

## Frontend

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **HTMX + Jinja2** | ✅ Recommended | No JS build toolchain, server-side HTML, works with FastAPI |
| React/Next.js | ✗ Skip | Adds complexity; portfolio shows Python/AI skills, not frontend |
| Streamlit | ⚠️ Consider | Rapid prototype, but limited UI customization |

HTMX is ideal here — demonstrates MLOps architecture focus, keeps frontend simple.

## Validation & Serialization

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **Pydantic v2** | ✅ Use | LangGraph requires it, typed state management |
| dataclasses | ✗ Skip | Less validation, no serialization |

## Environment & Packaging

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **uv** | ✅ Recommended | Fast dependency resolution, replaces pip for 2025 projects |
| **python-dotenv** | ✅ Use | `.env` for Neo4j credentials, API keys |
| poetry | ⚠️ Acceptable | More familiar but slower than uv |

## Testing

| Choice | Verdict | Rationale |
|--------|---------|-----------|
| **pytest + pytest-asyncio** | ✅ Use | Async test support essential for FastAPI + LangGraph |
| **pytest-mock** | ✅ Use | Mock LLM calls and Neo4j sessions in unit tests |
| unittest | ✗ Skip | Weaker async story |

## Requirements File

```txt
# Core
langgraph>=0.2
langchain-neo4j>=0.3
anthropic>=0.27
neo4j>=5.0

# Web
fastapi>=0.110
uvicorn[standard]>=0.27

# Data Pipeline
httpx>=0.27
beautifulsoup4>=4.12
pydantic>=2.5

# Dev
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
pytest-mock>=3.12
```

## Confidence Levels

- LangGraph + Neo4j + langchain-neo4j: **High** — established pattern in GraphRAG community
- FastAPI + HTMX: **High** — works well for server-rendered AI tools
- uv over poetry: **Medium** — uv is newer but now widely adopted
- anthropic SDK over LangChain Anthropic wrapper: **High** — direct SDK reduces indirection

---
*Generated: 2026-03-14 (training knowledge, web search unavailable)*
