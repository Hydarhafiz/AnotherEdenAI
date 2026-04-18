---
phase: 1
slug: graph-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `pytest.ini` — Wave 0 creates it |
| **Quick run command** | `pytest tests/unit/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30s (unit) / ~90s (full with Docker Neo4j) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite green + `python assert_schema.py` exits 0
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | GRAPH-07 | assertion | `python assert_schema.py` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-01 | unit | `pytest tests/unit/test_scraper.py::test_parse_character -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | DATA-02 | unit | `pytest tests/unit/test_scraper.py::test_parse_grasta_categories -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | DATA-03 | unit | `pytest tests/unit/test_scraper.py::test_parse_ores -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | DATA-01,02,03 | unit | `pytest tests/unit/ -x -q` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 2 | GRAPH-01,02 | integration | `pytest tests/integration/test_known_nodes.py::test_character_properties -x` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 2 | GRAPH-03,04,05 | integration | `pytest tests/integration/test_known_nodes.py::test_grasta_properties -x` | ❌ W0 | ⬜ pending |
| 1-02-06 | 02 | 2 | GRAPH-06 | integration | `pytest tests/integration/test_known_nodes.py::test_ore_properties -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 3 | DATA-04 | integration | `pytest tests/integration/test_idempotency.py -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 3 | DATA-05,GRAPH-07 | assertion | `python assert_schema.py` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 3 | ALL | full suite | `pytest tests/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest.ini` — `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`
- [ ] `tests/conftest.py` — async Neo4j driver fixture (function-scoped DB wipe, session-scoped driver)
- [ ] `tests/unit/test_scraper.py` — fixture HTML stubs (no network calls); covers DATA-01, DATA-02, DATA-03
- [ ] `tests/unit/test_models.py` — Pydantic strict vs lenient mode validation; covers DATA-02 validation boundary
- [ ] `tests/integration/test_idempotency.py` — run ETL twice, compare node/rel counts; requires Docker Neo4j; covers DATA-04
- [ ] `tests/integration/test_known_nodes.py` — post-ETL Cypher queries for known-good values; covers GRAPH-01 through GRAPH-07
- [ ] `assert_schema.py` — exits 0 when expected node labels exist + SCHEMA.md diff check; covers DATA-05, GRAPH-07
- [ ] `pip install pytest pytest-asyncio` — framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SCHEMA.md matches `get_schema()` output visually | GRAPH-07 | String format may differ; human review needed | Run `python -c "from langchain_neo4j import Neo4jGraph; g=Neo4jGraph(...); print(g.get_schema())"` and diff against SCHEMA.md |
| Docker Neo4j starts cleanly and accepts connections | Infrastructure | No pytest for container health | `docker compose up -d && docker compose ps` — confirm State=healthy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
