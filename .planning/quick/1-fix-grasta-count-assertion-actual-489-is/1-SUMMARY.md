---
phase: quick
plan: 1
subsystem: etl
tags: [grasta, constants, assert-schema, calibration]
dependency_graph:
  requires: []
  provides: [calibrated-grasta-threshold]
  affects: [assert_schema.py]
tech_stack:
  added: []
  patterns: [wiki-audit-comment]
key_files:
  created: []
  modified:
    - src/etl/constants.py
decisions:
  - "Grasta EXPECTED_NODE_COUNTS minimum set to 460 (not raw wiki row count 647) because Neo4j MERGE on name deduplicates 647 wiki rows to 489 unique nodes"
  - "Buffer formula: actual - 20, rounded down to nearest 10 (~4%)"
metrics:
  duration: "2 minutes"
  completed: "2026-03-15"
  tasks_completed: 2
  files_changed: 1
---

# Quick Task 1: Fix Grasta Count Assertion (actual 489 < 500) — Summary

**One-liner:** Calibrated EXPECTED_NODE_COUNTS['Grasta'] from stale 500 to 460 after wiki audit revealed 647 rows deduplicate to 489 unique Neo4j nodes via MERGE-by-name.

## What Was Diagnosed

The assertion `Grasta count 489 < expected minimum 500` in `assert_schema.py` was caused by a stale constant. The comment "wiki has 647" was numerically correct for raw wiki table rows, but incorrect as a Neo4j node count floor because:

- The wiki has **647 total** `tr.grasta-row-entry` rows across 5 categories
- Grastas have identical names across tier levels (e.g., "Almighty Power" appears 35 times — tiers 1-35 all share the same name)
- The loader uses `MERGE (g:Grasta {name: $name})` which collapses all same-name rows into a single node
- Result: **489 unique Grasta nodes** in Neo4j (158 rows collapsed)

## Per-Category Wiki Counts

| Category | Wiki Rows | Unique Names | Duplicates |
|----------|-----------|--------------|------------|
| Attack   | 231       | 117          | 114        |
| Life     | 46        | 21           | 25         |
| Support  | 56        | 39           | 17         |
| Special  | 4         | 2            | 2          |
| VC       | 310       | 310          | 0          |
| **TOTAL**| **647**   | **489**      | **158**    |

VC grastas are all unique (character-specific names). Non-VC grastas share names across tier levels.

## Fix Applied

File: `src/etl/constants.py` line 27

```python
# Before:
"Grasta": 500,     # wiki has 647

# After:
"Grasta": 460,     # wiki audit 2026-03-15: actual=489 unique nodes (647 wiki rows deduplicate by name via MERGE), floor=460 (~4% buffer)
```

Formula: `floor = actual - 20 = 489 - 20 = 469` → rounded down to nearest 10 = **460**

## Verification

```
OK: Character = 389
OK: Grasta = 489
OK: Ore = 61
OK: Trait = 126
Exit: 0
```

`assert_schema.py` exits 0. No scraper code was modified — the scraper was working correctly all along.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1    | Add Grasta wiki diagnostic script | 65ddc7d |
| 2    | Calibrate threshold + remove diagnostic | 268a3ab |

## Deviations from Plan

### Investigation Branch

The plan's Task 1 diagnostic originally used simple row counting (`tr.grasta-row-entry` + `>= 4 td`), which returned 647. Since 647 > 510, the plan required investigating the selector before proceeding. The investigation revealed the scraper is correct — the discrepancy between 647 wiki rows and 489 Neo4j nodes is caused by MERGE deduplication by name (expected behavior, not a data loss bug). No scraper changes were needed.

This was logged as an auto-investigation (Rule 1 diagnostic extension), not a deviation requiring user approval.

## Self-Check: PASSED

- src/etl/constants.py modified with floor=460 and wiki audit comment: CONFIRMED
- diagnose_grasta.py absent from repo root: CONFIRMED
- assert_schema.py exits 0: CONFIRMED
- Commits 65ddc7d and 268a3ab exist: CONFIRMED
