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

Important behavior:

- parsed artifacts are invalid when their schema version does not match the active ETL schema
- parsed-only runs can rebuild ETL output without live wiki fetches
- selected-scope failures should stay visible instead of being silently skipped

## Prerequisites

- Python environment installed and activated
- Chrome/Chromium available for `nodriver`
- Neo4j running if you want to execute the full load stage
- a usable display session if Cloudflare/browser interaction is needed

Typical setup:

```bash
uv sync
docker compose up -d
```

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
- `ETL_MAX_RETRIES`
- `ETL_SMALL_CHARACTER_LIMIT`
- `ETL_FALLBACK_CHARACTER_LIMIT`
- `ETL_OPERATOR_WAIT_SECONDS`
- `ETL_BROWSER_PROFILE_DIR`
- `ETL_SCHEMA_VERSION`

Artifact locations:

- `RAW_DATA_DIR`
- `PARSED_DATA_DIR`
- `ETL_STATE_DIR`

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

Useful diagnostics include:

- attempt count
- last error
- HTML byte size
- Cloudflare detection
- parsed counts
- quality status

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

### 3. Manual Scraper Smoke Check

Use the helper:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode live --scope small
```

Then rerun in parsed mode:

```bash
uv run python tools/manual_feature_a_smoke.py --run-root data/manual_feature_a/smoke1 --source-mode parsed --scope small
```

### 4. Schema Invalidation Check

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
- confirm browser/Chromium availability
- confirm display/browser interaction is possible
- retry with a smaller crawl scope for diagnosis

If Neo4j load fails:

- verify `NEO4J_URI` and `NEO4J_AUTH`
- confirm the database is reachable
- rerun `assert_schema.py` after a successful load

## Maintenance Rule

When an implementation changes ETL stages, crawl controls, manifest shape, operator workflow, artifact layout, or debugging steps, update this guide in the same feature.
