---
phase: 3
slug: connect-workflow-to-real-neo4j
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `pytest tests/ -m "not integration" -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Integration only** | `pytest tests/integration/ -m integration -x -q` |
| **Estimated runtime** | ~5s (unit), ~30s (full with Neo4j) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -m "not integration" -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q` (requires live Neo4j)
- **Before `/gsd:verify-work`:** Full suite must be green (including `@pytest.mark.integration`)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | QUERY-04 | unit | `pytest tests/workflow/test_normalize.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 3-01-02 | 01 | 1 | QUERY-02 | unit | `pytest tests/workflow/test_f2p.py -x -q` | ❌ Wave 0 | ⬜ pending |
| 3-01-03 | 01 | 1 | QUERY-01 | unit | `pytest tests/workflow/test_validate.py -x -q` | ✅ exists | ⬜ pending |
| 3-02-01 | 02 | 2 | QUERY-02 | integration | `pytest tests/integration/test_query_pipeline.py::test_roster_filtering_excludes_unowned -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-02 | 02 | 2 | QUERY-03 | integration | `pytest tests/integration/test_query_pipeline.py::test_end_to_end_happy_path -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-03 | 02 | 2 | QUERY-04 | integration | `pytest tests/integration/test_query_pipeline.py::test_name_normalization -x` | ❌ Wave 0 | ⬜ pending |
| 3-03-01 | 03 | 2 | QUERY-01,02,03,04 | integration | `pytest tests/integration/test_query_pipeline.py -x -q` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_query_pipeline.py` — integration test stubs for QUERY-01, QUERY-02, QUERY-03, QUERY-04 (marked `@pytest.mark.integration`)
- [ ] `tests/workflow/test_normalize.py` — unit tests for `normalize_character_name()` and `normalize_roster()`
- [ ] `tests/workflow/test_f2p.py` — unit tests for `F2P_CHARACTERS` and `augment_with_f2p()`

*Note: `tests/workflow/test_validate.py` already exists (20 passing tests). Wave 0 must update it to use `AsyncMock` for async validate_node.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AuraDB TLS connection works with `neo4j+s://` URI | QUERY-01 | Requires live AuraDB credentials | Set `NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io` in `.env`, run `pytest tests/integration/ -m integration -x -q`, confirm no SSL handshake errors |
| Known-good synergy pair returns correct Grasta + personality attribution | QUERY-03 | Requires human judgment on correctness | Run `test_known_good_synergy_pair`, inspect returned Grasta names and traits against wiki manually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
