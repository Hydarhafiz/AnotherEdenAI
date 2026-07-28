# ETL And Web Scraping Guide

This guide covers how to run, inspect, and debug the AnotherEdenAI ETL and wiki scraping system.

## Purpose

The ETL pipeline is responsible for:

- fetching wiki pages through a real browser session
- caching raw HTML locally
- parsing schema-versioned JSON artifacts from cached pages
- loading Neo4j from parsed artifacts
- tracking crawl progress and failures through a manifest

The runtime entry point is `src.etl.run_etl`.

## Main Concepts

The ETL flow is staged:

1. `fetch`
2. `parse`
3. `validate`
4. `load`

Important local artifacts:

- `data/raw/`: raw cached HTML
- `data/parsed/`: schema-versioned parsed JSON snapshots
- `data/etl/crawl_manifest.json`: crawl state and diagnostics
- `src/etl/mechanics_corpus.json`: curated Milestone 4 mechanics references replayed into parsed artifacts

Important behavior:

- parsed artifacts are invalid when their schema version does not match the active ETL schema
- parsed-only runs can rebuild ETL output without live wiki fetches
- mechanics references load from the curated local corpus, while live runs also cache the referenced source pages under `data/raw/mechanics/`
- selected-scope failures should stay visible instead of being silently skipped
- the manifest summarizes selected-target accountability and curated sidekick/superboss load success

## Prerequisites

- Python environment installed and activated
- `uv` available on PATH
- Chrome/Chromium available for `nodriver`
- Neo4j running if you want to execute the full load stage
- a usable display session if Cloudflare/browser interaction is needed

Typical setup:

```bash
cd /home/shogunix/AnotherEdenAI
uv sync
docker compose up -d
```

Use `uv run ...` for ETL, schema checks, and tests so commands use the project environment resolved from `pyproject.toml` and `uv.lock`. Avoid bare `python`, `pytest`, or `pip install ...` during normal project work; keep `pip` only as a fallback for bootstrapping `uv` on a new machine.

## Standard Commands

Full ETL run:

```bash
uv run python -m src.etl.run_etl
```

Post-load schema assertion:

```bash
uv run python assert_schema.py
```

Run the manual Feature A smoke helper:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode live --scope small
```

Parsed-only smoke rerun:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode parsed --scope small
```

## Key Environment Variables

Core runtime:

- `ETL_MODE`: `strict` or `lenient`
- `NEO4J_URI`
- `NEO4J_AUTH`

Pipeline controls:

- `ETL_SOURCE_MODE`: `live` or `parsed`
- `ETL_CRAWL_SCOPE`: `small`, `fallback`, or `full`
- `ETL_INCREMENTAL`
- `ETL_RESUME`
- `ETL_INCLUDE_CHARACTER_PAGES`
- `ETL_INCLUDE_SIDEKICK_PAGES`
- `ETL_INCLUDE_SUPERBOSS_PAGES`
- `ETL_MAX_RETRIES`
- `ETL_SMALL_CHARACTER_LIMIT`
- `ETL_SMALL_SIDEKICK_LIMIT`
- `ETL_FALLBACK_CHARACTER_LIMIT`
- `ETL_FALLBACK_SIDEKICK_LIMIT`
- `ETL_OPERATOR_WAIT_SECONDS`
- `ETL_BROWSER_PROFILE_DIR`
- `ETL_SCHEMA_VERSION`

Artifact locations:

- `RAW_DATA_DIR`
- `PARSED_DATA_DIR`
- `ETL_STATE_DIR`
- `CURATED_MECHANICS_PATH`

## Crawl Scopes

Use crawl scope intentionally:

- `small`: quick operator smoke runs
- `fallback`: planned reduced-coverage runs
- `full`: full-corpus attempt

The selected scope should be explicit. A smaller scope is not permission to hide failures inside that chosen scope.

## Reading The Manifest

The crawl manifest records per-target state such as:

- `pending`
- `cached`
- `parsed`
- `loaded`
- `failed`
- `inactive`

Useful diagnostics include:

- attempt count
- last error
- failure stage
- quality-gate reason
- HTML byte size
- Cloudflare detection
- parsed counts
- quality status
- raw and parsed cache artifact paths

The top-level `readiness_summary` gives a quick Feature E check:

- `selected_target_count`
- `loaded_count`
- `failed_count`
- `pending_accountability_count`
- `pass_fail_accountability_percent`
- `curated_detail_success_percent`
- `failed_targets`
- `pending_targets`

Use the manifest first when a run behaves unexpectedly.

## Common Workflows

### 1. Fresh Live Run

```bash
uv run python -m src.etl.run_etl
```

Use this when you want fresh data and a full fetch/parse/load cycle.

### 2. Parsed-Only Rerun

Set:

```bash
ETL_SOURCE_MODE=parsed
```

Then run:

```bash
uv run python -m src.etl.run_etl
```

Use this when raw and parsed cache already exist and you want to confirm Neo4j can load without live wiki access.

On PowerShell, use:

```powershell
$env:ETL_SOURCE_MODE = "parsed"
uv run python -m src.etl.run_etl
```

On bash, use:

```bash
ETL_SOURCE_MODE=parsed uv run python -m src.etl.run_etl
```

Parsed replay requires current schema-versioned index artifacts and only selects detail artifacts that already exist. Missing detail artifacts are marked `inactive` instead of fetched.

### 3. Feature E Readiness Gate

After a successful load, run:

```bash
uv run python assert_schema.py
```

This checks:

- minimum node presence for character, Grasta, Ore, Trait, Skill, PassiveSkill, Sidekick, SidekickSkill, SidekickAura, Superboss, and Equipment labels
- `schema_version` on milestone-added structured labels
- `source_url` attribution on wiki-sourced structured labels
- golden retrieval paths for sidekick associations, sidekick abilities and auras, boss affinities and mechanics text, and baseline equipment context
- golden retrieval paths for weakness handling, sidekick behavior, Stellar Awakening gating, speed/turn order, sustain, and Grasta/Ore mechanics references

### 4. Mechanics Corpus Replay

The Milestone 4 mechanics corpus is curated in:

```bash
src/etl/mechanics_corpus.json
```

During ETL, the corpus is validated as `MechanicReference` rows, written to:

```bash
data/parsed/v1.0.0/mechanics/mechanic_references.json
```

and loaded into Neo4j as standalone `MechanicReference` nodes. Live ETL mode also caches the full referenced mechanics pages under `data/raw/mechanics/` for auditability; parsed mode can still replay the curated corpus without those live source-page caches.

### 5. Manual Scraper Smoke Check

Use the helper:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode live --scope small
```

Then rerun in parsed mode:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode parsed --scope small
```

### 6. Schema Invalidation Check

Corrupt a parsed artifact's `schema_version`, then rerun parsed mode.

Expected behavior:

- parsed mode should fail
- a live rerun should refresh the artifact
- parsed mode should succeed again afterward

## Cloudflare And Operator Notes

- some runs may need a visible browser window
- browser profile reuse can help when repeated Cloudflare checks happen
- use `ETL_BROWSER_PROFILE_DIR` when you want to preserve browser state between runs
- if a page is partially loaded or blocked, prefer surfacing it in the manifest over guessing

## Troubleshooting

If parsed mode fails immediately:

- check parsed artifact schema version
- check whether the expected parsed file exists
- inspect `crawl_manifest.json`

If a live run fails:

- inspect failed targets in the manifest
- check `failure_stage` first: `fetch`, `parse`, or `quality_gate`
- use `quality_gate_reason` to distinguish blocked/partial pages from parser defects
- open the listed raw or parsed cache artifact when available
- confirm browser/Chromium availability
- confirm display/browser interaction is possible
- retry with a smaller crawl scope for diagnosis

If Neo4j load fails:

- verify `NEO4J_URI` and `NEO4J_AUTH`
- confirm the database is reachable
- rerun `assert_schema.py` after a successful load

## Feature B Grasta Identity Migration

Schema 1.1.0 replaces the name-only Grasta constraint with `grasta_id`. A normal ETL replay drops the legacy constraint, removes only Grasta nodes without a stable ID, and reloads exact variants from current parsed artifacts.

Because schema-versioned parsed artifacts from 1.0.0 are invalid, refresh/reparse the cached Grasta index pages, then run:

```bash
ETL_SOURCE_MODE=parsed uv run python -m src.etl.run_etl
uv run python assert_schema.py
```

The ETL must report removal of collapsed legacy Grasta nodes before loading exact variants. Verify that Almighty Power personality variants and weapon-specific Enhance if Max HP variants have distinct `grasta_id` values, one `REQUIRES_TRAIT` relationship at most per exact personality variant, and explicit acquisition/cardinality metadata.

The same ETL run performs the character coverage gate. Any parsed character missing from Neo4j or excluded from the frontend roster list aborts visibly; alias/style inputs such as Akane Alter must resolve to the full canonical display name.

## Milestone 5 Feature A Identity Replay

Schema 1.2.0 adds persisted `skill_id` and `passive_skill_id` candidate identities and records `schema_version` on Character nodes. Refresh or reparse older artifacts before replay because artifacts from an earlier schema version are intentionally rejected.

Run a current parsed replay and the post-load assertions:

```bash
ETL_SOURCE_MODE=parsed uv run python -m src.etl.run_etl
uv run python assert_schema.py
```

The ETL log must include a graph readiness report. `ready` is `true` only when identity properties and schema versions are current, boss mechanics exist, and Grasta, Equipment, and MechanicReference facts are present. The report also lists characters without skills or passives so intentionally sparse crawl scopes remain visible.

In Neo4j Browser, verify persisted identities and replay-safe sidekick cleanup:

```cypher
MATCH (c:Character)-[:HAS_SKILL]->(s:Skill)
RETURN c.character_id, c.name, s.skill_id, s.name, c.schema_version, s.schema_version
LIMIT 20;

MATCH (c:Character)-[:HAS_PASSIVE_SKILL]->(p:PassiveSkill)
RETURN c.character_id, c.name, p.passive_skill_id, p.name, p.schema_version
LIMIT 20;

MATCH (c:Character)
MATCH (:Sidekick {name: c.name})
RETURN c.name;
```

The identity columns must be non-empty and schema versions must be `1.2.0`. The overlap query must return no rows. Run the parsed replay a second time and confirm these results remain unchanged.

### Feature C Atomic Capability Review

`src/etl/capability_taxonomy.json` and the canonical review/gold artifacts are the source of truth. Do not edit capability fields in Neo4j. C4 uses taxonomy/review schema 3.1.0: it retains C3's 25 active offensive/support families, adds reviewed dependency and recipient-eligibility vocabulary across all four fact types, and keeps `af_gauge_gain_up`, `invert_weakness_resistance`, `grant_copy`, and residual `follow_up_attack` reserved and non-authoritative.

Generate a targeted C3 seed review from parsed character and sidekick facts:

```bash
.venv/bin/python -m src.etl.capability_taxonomy generate-c3-seed \
  --parsed-dir data/parsed \
  --csv src/etl/review_batches/c3_offensive_support_seed_review.csv
```

The command either writes a deterministic CSV and reference JSON or stops with named coverage gaps. A general mechanics page cannot fill a gap: add a human-supplied canonical character or sidekick page, exact fact name, and intended atomic capability first.

After human seed decisions exist, recover the reviewed replacement batch while preserving seed evidence and refilling only overlaps:

```bash
.venv/bin/python -m src.etl.capability_taxonomy recover-c3-batch \
  --parsed-dir data/parsed \
  --reviewed-batch src/etl/review_batches/c3_offensive_support_batch_1_replacement.csv \
  --seed-csv src/etl/review_batches/c3_offensive_support_seed_review.csv \
  --csv src/etl/review_batches/c3_offensive_support_batch_1_recovered.csv
```

Review every new row explicitly, then import it with the same parsed directory. C3 remains artifact-only: do not run an ETL replay or inspect Neo4j capability materialization until Feature C5.

After C4 dependency/condition batch review, import the reviewed CSV with the same parsed facts:

```bash
.venv/bin/python -m src.etl.capability_taxonomy import \
  --parsed-dir data/parsed \
  --csv src/etl/review_batches/c4_dependencies_conditions_batch_N.csv
```

Use `clear` in an optional corrected qualifier field when the proposed value must not be retained; the importer canonicalizes it to `__clear__`, and materialized evidence records the value as unknown/blank. C4 remains artifact-only: do not replay Neo4j until Feature C5.

## Maintenance Rule

When an implementation changes ETL stages, crawl controls, manifest shape, operator workflow, artifact layout, or debugging steps, update this guide in the same feature.
