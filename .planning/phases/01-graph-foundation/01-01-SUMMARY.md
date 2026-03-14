---
phase: 01-graph-foundation
plan: "01"
subsystem: infrastructure
tags: [neo4j, docker, schema, etl, pytest, constants]
dependency_graph:
  requires: []
  provides:
    - docker-compose.yml (Neo4j 5.x Community container)
    - SCHEMA.md v1.0.0 (versioned schema contract for LLM prompt injection)
    - src/etl/constants.py (SCHEMA_VERSION, ETL_MODE, all URLs and counts)
    - assert_schema.py (post-load CI assertion script)
    - pytest.ini + tests/ Wave 0 scaffold (13 stubs ready for implementation)
  affects:
    - 01-02-PLAN.md (scraper/models use WIKI_URLS and constants from constants.py)
    - 01-03-PLAN.md (loader uses NEO4J_URI, NEO4J_AUTH from constants; integration tests run against docker-compose Neo4j)
    - Phase 2 (GENERATE_CYPHER agent injects SCHEMA.md into prompts)
tech_stack:
  added:
    - neo4j:5-community (Docker container)
    - neo4j>=5.0 (Python async driver)
    - pytest>=8.0 + pytest-asyncio>=0.23 (test framework)
    - python-dotenv>=1.0 (env loading)
  patterns:
    - ETL_MODE=strict/lenient toggle via environment variable
    - SCHEMA_VERSION constant linked between SCHEMA.md and constants.py
    - Session-scoped async driver fixture with loop_scope="session" to avoid event loop errors
key_files:
  created:
    - docker-compose.yml
    - pyproject.toml
    - src/__init__.py
    - src/etl/__init__.py
    - src/etl/constants.py
    - .env.example
    - SCHEMA.md
    - assert_schema.py
    - pytest.ini
    - tests/__init__.py
    - tests/conftest.py
    - tests/unit/__init__.py
    - tests/unit/test_scraper.py
    - tests/unit/test_models.py
    - tests/integration/__init__.py
    - tests/integration/test_idempotency.py
    - tests/integration/test_known_nodes.py
  modified: []
decisions:
  - "Ore is documented as standalone in SCHEMA.md with explicit NOTE prohibiting ENHANCES edges — consistent with CONTEXT.md decision"
  - "SCHEMA_VERSION=1.0.0 lives in constants.py and is referenced in SCHEMA.md header — single source of truth enforced by verification check"
  - "conftest.py uses @pytest_asyncio.fixture(loop_scope='session') for the driver fixture to prevent RuntimeError: Event loop is closed with function-scoped tests"
  - "assert_schema.py exits 1 with descriptive FAIL message (not a traceback) when Neo4j is unreachable — designed for CI pipelines"
metrics:
  duration_seconds: 230
  completed_date: "2026-03-14"
  tasks_completed: 2
  tasks_total: 2
  files_created: 17
  files_modified: 0
---

# Phase 1 Plan 01: Infrastructure and Schema Contract Summary

**One-liner:** Neo4j 5.x Docker setup with versioned SCHEMA.md v1.0.0 contract, ETL constants, and 13 Wave 0 pytest stubs covering all Phase 1 requirements.

## What Was Built

Two tasks executed to deliver the infrastructure and schema contract that all subsequent ETL and LLM work depends on:

**Task 1** — Docker, pyproject, and ETL constants:
- `docker-compose.yml`: Neo4j 5.x Community with health check (`wget localhost:7474`), named volumes, and `.env` support for `NEO4J_AUTH`
- `pyproject.toml`: Full dependency list including httpx, beautifulsoup4, pydantic>=2.8, neo4j, langchain-neo4j, plus dev group (pytest, pytest-asyncio, python-dotenv)
- `src/etl/constants.py`: Exports `SCHEMA_VERSION="1.0.0"`, `ETL_MODE`, `STRICT`, `NEO4J_URI`, `NEO4J_AUTH`, `WIKI_URLS` (7 wiki page URLs), `GRASTA_CATEGORIES`, and `EXPECTED_NODE_COUNTS` (minimum node counts for CI assertion)
- `.env.example`: Environment variable template for developers

**Task 2** — SCHEMA.md, assert_schema.py, and Wave 0 test scaffold:
- `SCHEMA.md`: Versioned schema contract v1.0.0 documenting all 4 node labels (Character, Trait, Grasta, Ore), 2 relationship types (HAS_TRAIT, REQUIRES_TRAIT), and explicit NOTE that Ore is standalone with no ENHANCES relationship
- `assert_schema.py`: CI assertion script that exits 0 on success, 1 with descriptive FAIL message when Neo4j is unreachable or node counts fall below minimums
- `pytest.ini`: `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`
- `tests/conftest.py`: Session-scoped async Neo4j driver + function-scoped `clean_db` fixture
- 5 test stub files (13 total stubs, all skipped with TODO comments pointing to implementing plans)

## Verification Results

| Check | Result |
|-------|--------|
| `docker-compose.yml` has `neo4j:5-community` | PASS |
| `constants.py` imports with `SCHEMA_VERSION="1.0.0"` | PASS |
| `pytest --collect-only` finds 13 tests, no ImportError | PASS |
| `SCHEMA_VERSION` in both SCHEMA.md and constants.py | PASS |
| `asyncio_mode = auto` in pytest.ini | PASS |
| `assert_schema.py` exits 1 with descriptive message (no traceback) when Neo4j unavailable | PASS |
| No ENHANCES relationship type defined in SCHEMA.md | PASS |

## Commits

| Hash | Message |
|------|---------|
| b295d0e | feat(01-01): scaffold Docker, pyproject, and ETL constants |
| 7752803 | feat(01-01): SCHEMA.md contract, assert_schema.py, and Wave 0 test scaffold |

## Deviations from Plan

None — plan executed exactly as written.

Note: The verification check `grep "ENHANCES" SCHEMA.md` does match lines in SCHEMA.md, but those lines are explicit NOTE statements saying ENHANCES does NOT exist (e.g., "There is no ENHANCES relationship in the graph"). No ENHANCES relationship type is defined. This is correct behavior.

## Self-Check: PASSED

Files verified:
- docker-compose.yml: FOUND
- src/etl/constants.py: FOUND
- SCHEMA.md: FOUND
- pytest.ini: FOUND
- assert_schema.py: FOUND
- tests/conftest.py: FOUND
- tests/unit/test_scraper.py: FOUND
- tests/unit/test_models.py: FOUND
- tests/integration/test_idempotency.py: FOUND
- tests/integration/test_known_nodes.py: FOUND

Commits verified: b295d0e and 7752803 present in git log.
