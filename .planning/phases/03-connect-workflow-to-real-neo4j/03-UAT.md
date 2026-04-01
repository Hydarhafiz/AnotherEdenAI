---
status: diagnosed
phase: 03-connect-workflow-to-real-neo4j
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md
started: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:01:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Character Name Normalization
expected: Running normalize_character_name() with a partial or differently-cased name like "aldo" or "ALDO" resolves to the canonical name "Aldo". Unresolvable names are dropped by normalize_roster() and do not appear in the final roster sent to the LLM.
result: pass

### 2. F2P Roster Augmentation
expected: augment_with_f2p() adds the 8 story-permanent F2P characters (Aldo, Feinne, Isuka, Riica, Miyu, Lokido, Nona, Bivette) to a user-provided roster without duplicates. If a character is already in the roster, it is not added a second time.
result: pass

### 3. Async plan_node with Roster Preprocessing
expected: When the pipeline runs, plan_node normalizes the roster (drops bad names) and augments with F2P characters before calling the LLM. The final state returned by plan_node contains both plan_strategy and the preprocessed roster.
result: pass

### 4. CLI run.py Entry Point
expected: Running `python -m src.workflow.run --roster "Aldo,Ciel" --query "blunt zone synergy team"` completes without an unhandled Python exception. It prints a JSON result dict (which may contain an error key if LLM credentials are unconfigured — that is acceptable; what must NOT happen is an unhandled traceback).
result: pass

### 5. Empty Roster Graceful Degradation
expected: Calling the pipeline with an empty roster (roster=[]) does not raise an exception. augment_with_f2p([]) produces a roster of just the F2P characters. A Cypher query against the live graph using only F2P names returns non-empty results.
result: pass

### 6. End-to-End Pipeline Completion
expected: The full pipeline chain (plan → validate → analyze → format) completes against live Neo4j without crashing. The integration test test_end_to_end_pipeline_with_latency passes in under 15 seconds, and the measured latency is logged to stdout.
result: pass

### 7. Full Integration Test Suite Passes
expected: Running `pytest tests/integration/test_query_pipeline.py -m integration -v` shows 9+ tests (original 6 from Plan 02 + 3 new from Plan 03) all green. No regressions in the full suite (`pytest tests/ -x -q`).
result: issue
reported: "Integration suite: 10 passed, 2 skipped (LLM rate limit — skip gracefully). Full suite errors in test_known_nodes.py: loaded_db fixture tries to live-scrape anothereden.wiki/w/Grasta_Special and gets 403 Forbidden. ETL scraper blocked by wiki, not a Phase 3 regression."
severity: minor

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "pytest tests/ -x -q passes with zero failures"
  status: failed
  reason: "User reported: test_known_nodes.py errors during loaded_db fixture setup — ETL scraper hits anothereden.wiki/w/Grasta_Special and gets 403 Forbidden. Phase 3 integration suite (test_query_pipeline.py) itself passes 10/12 (2 skipped due to LLM rate limit)."
  severity: minor
  test: 7
  root_cause: "loaded_db fixture in tests/conftest.py:57 triggers ETL when DB has < 100 characters. ETL's scrape_all() requests anothereden.wiki/w/Grasta_Special via httpx with User-Agent 'AnotherEdenAI-research-bot'. Wiki returns 403 (bot block or rate limit). Scraper has no retry/fallback and raises immediately. Only fires on cold DB; once DB is populated the fixture skips ETL."
  artifacts:
    - path: "tests/conftest.py"
      issue: "loaded_db fixture runs full ETL when count < 100 — no guard for wiki unavailability"
    - path: "src/etl/scraper.py"
      issue: "fetch_page raises immediately on 403 with no retry or graceful skip"
  missing:
    - "Either: skip test_known_nodes when wiki is unreachable (pytest.mark with condition check)"
    - "Or: add retry/backoff to fetch_page and fall back to cached fixture data on 403"
    - "Or: pre-populate DB before running full test suite (documented in README)"
  debug_session: ""
