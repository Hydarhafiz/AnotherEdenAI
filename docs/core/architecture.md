# AnotherEdenAI Architecture

## Purpose

AnotherEdenAI is a GraphRAG application for building roster-constrained team recommendations for the JRPG *Another Eden*. The system combines a scraped and normalized Neo4j graph with a multi-step LangGraph workflow and a lightweight FastAPI web UI.

This document is the architectural source of truth for implementation planning. Use it alongside `SCHEMA.md` for any feature that changes data shape, graph traversal logic, prompt contracts, API behavior, or UI integration.

## Five Pillars

The project keeps five root documents as planning and release anchors:

- `milestone.md`: active epic scope, feature order, and completion state
- `CHANGELOG.md`: historical change log by phase and release
- `architecture.md`: current system design, boundaries, and extension points
- `SCHEMA.md`: graph contract and data-shape source of truth
- `README.md`: setup, execution, and operator-facing guidance

Supplementary planning context:

- `future-ideas.md`: deferred ideas and next-milestone candidates that should not yet be promoted into the active implementation contract

## System Overview

The system has three major layers:

1. ETL and graph loading
2. Query-time workflow orchestration
3. Web delivery and streaming UX

At a high level:

- Wiki data is scraped and normalized into Pydantic ETL models.
- The ETL pipeline loads Characters, Traits, Skills, PassiveSkills, Sidekicks, SidekickSkills, SidekickAuras, curated Superbosses, Grastas, Ores, and baseline Equipment into Neo4j with idempotent MERGE behavior.
- User roster input is normalized and augmented with free-to-play units.
- A five-node LangGraph pipeline plans the query, generates Cypher, validates it, analyzes results, and formats the output.
- FastAPI exposes query and admin routes, while SSE streams progress back to the browser.

## Runtime Components

### ETL Layer

- Entry point: `src/etl/run_etl.py`
- Scraper: `src/etl/scraper.py`
- Data models: `src/etl/models.py`
- Loader: `src/etl/loader.py`
- Constants and thresholds: `src/etl/constants.py`

Responsibilities:

- Retrieve live wiki pages with `nodriver`
- Parse Characters, character detail combat entries, Sidekicks, sidekick ability/aura entries, curated weak Superbosses, Grastas, Ores, and baseline weapon/armor Equipment
- Validate records with Pydantic
- Load normalized entities into Neo4j
- Assert schema and RAG-readiness expectations after load

Feature E ETL reliability behavior:

- The crawl manifest records every selected target with explicit `loaded`, `failed`, or inactive/not-selected state.
- Failed selected targets retain URL, failure stage, attempt count, last error, quality-gate reason when applicable, and raw/parsed cache artifact references.
- Parsed source mode reloads Neo4j from current schema-versioned JSON artifacts without live wiki access.
- The manifest readiness summary reports selected target accountability, failed and pending targets, and curated sidekick/superboss detail success rate.
- Post-load schema assertions verify milestone-added labels, required `schema_version`, wiki `source_url` attribution, sidekick association and ability/aura paths, boss affinity/mechanics retrieval, and baseline equipment context.

Milestone 4 Feature A mechanics corpus behavior:

- Referenced battle-mechanics wiki pages are cacheable as raw source artifacts under `data/raw/mechanics/` during live ETL runs.
- The recommendation-focused golden corpus is curated locally in `src/etl/mechanics_corpus.json` and replayed into schema-versioned parsed artifacts under `data/parsed/.../mechanics/`.
- Curated entries load as standalone `MechanicReference` nodes with source URL, source page, section path, mechanic type, topic tags, applies-to labels, rules text or summary, caveats, and schema version.
- `MechanicReference` retrieval is separate from boss, character, sidekick, Grasta/Ore, and equipment retrieval so recommendation reasoning can cite general battle rules independently from entity facts.
- Post-load schema assertions include golden retrieval checks for weakness handling, main/sub sidekick behavior, Stellar Awakening gating, speed/turn order, sustain, and Grasta/Ore setup.

Feature A sidekick graph behavior:

- The canonical Sidekick page discovers released sidekicks from sidekick cards; sidekick identity comes from `.sidekick-name`, while `.sidekick-owner` links are association facts.
- Sidekick detail pages use character skill-grid markup and are parsed into separate auto skills, charge skills, and aura records.
- Sidekicks load as `Sidekick` nodes, not `Character` nodes, preserving the later 6-hero plus main/sub sidekick legality model.
- `SidekickSkill` and `SidekickAura` child nodes are connected with `HAS_AUTO_SKILL`, `HAS_CHARGE_SKILL`, and `HAS_AURA`.
- Official owner/unlock facts load as `(:Character)-[:UNLOCKS_SIDEKICK]->(:Sidekick)` when the associated character exists in the graph.
- Milestone 5 cleanup reports exact `Character.name`/`Sidekick.name` overlaps and removes only confirmed duplicate `Character` nodes that lack character skill/passive detail and sidekick-unlock edges.
- Parsed or live ETL replay runs the cleanup after sidekick loading so sidekick-only records are not reintroduced as heroes.
- Small and fallback sidekick scope cover the full current sidekick detail set because the total sidekick list is small.
- The manual Feature A smoke runner clears generated sidekick detail artifacts and stale sidekick-detail manifest entries before live smoke runs to keep reused smoke roots honest.

Feature B curated superboss graph behavior:

- The canonical Superbosses page discovers weak-boss candidates as index metadata, including difficulty tier, refight status, version, characteristics, and detail URLs.
- Only curated weak superboss targets are promoted into detail crawl targets; broad all-superboss coverage remains deferred.
- Detail pages produce `Superboss` rows with source URL, tier/level context, HP and affinity fields where cleanly parseable, deterministic mechanic tags, mechanics text, and schema version.
- Section-anchored boss pages, such as Flame Eater on the Gariyu chance encounter page, are parsed within the selected section when the anchor is available.
- Superboss detail validation requires mechanics text for RAG grounding; selected boss URLs fail visibly in the manifest instead of being silently skipped.
- Index-only candidate facts are not loaded as final graph nodes.

Feature B combat graph behavior from earlier milestone work:

- Character index rows exclude sidekick-only records before character-detail crawling.
- Character detail crawl targets use canonical wiki hrefs from the Characters index, preserving alias/style pages such as `Dark_Devourer` and `Noble_Blossom_(Another_Style)`.
- Character detail pages produce `Skill` rows for active skills and basic attack replacements, plus `PassiveSkill` rows for non-executable mechanics such as stances and zones.
- Character detail validation requires recognizable active combat skills; partial or blocked pages with zero skills fail the selected ETL scope.
- Stellar Awakening availability is inferred from both index metadata and character detail page sections.

Feature C Grasta/Ore preservation behavior:

- Existing Grasta, Ore, Trait, `HAS_TRAIT`, and `REQUIRES_TRAIT` behavior is preserved; Grasta/Ore scraping is not rebuilt in this milestone.
- Grasta and Ore rows derive lightweight `effect_tags` from already-scraped name/category/stats/personality text for retrieval.
- `effect_tag_derivation` records that the tags are deterministic keyword metadata from existing fields.
- The tags support RAG lookup but do not represent exact damage math, optimizer ranking, or verified multiplier calculations.
- Ore nodes remain standalone; no `ENHANCES` or Grasta-to-Ore relationship is introduced.

Feature D equipment graph behavior:

- Weapon and armor index pages are parsed into a shared `Equipment` model keyed by `(equipment_slot, name)`.
- Weapon rows capture baseline attack and magic attack where available; armor rows capture baseline defense and magic defense where available.
- Equipment rows preserve category/type, level or tier, effect text, obtain/source text, source URL, and schema version for RAG grounding.
- Equipment nodes are loaded as standalone baseline context and do not imply best-in-slot ranking, optimizer scoring, exact damage math, survivability calculation, or equip/recommendation relationships.
- Verified ETL output on 2026-06-09 loaded 888 Equipment nodes: 664 weapons and 224 armor records.

### Workflow Layer

- Graph wiring: `src/workflow/graph.py`
- State contract: `src/workflow/state.py`
- LLM provider factory: `src/workflow/llm.py`
- Legality contract: `src/workflow/legality.py`
- Roster utilities: `src/workflow/normalize.py`, `src/workflow/f2p.py`
- Nodes: `src/workflow/nodes/`

Current workflow sequence:

1. `PLAN`
2. `GENERATE_CYPHER`
3. `VALIDATE`
4. `ANALYZE`
5. `FORMAT`

Routing notes:

- `VALIDATE` is the quality gate.
- Validation failures retry Cypher generation up to three times.
- Graceful fallback formatting is required when retries are exhausted.
- Alternatives output is supported when no exact ideal team exists.
- Milestone 4 Feature B legality models define structured roster ownership, optional Stellar Awakening state, owned sidekicks, exactly four frontline heroes, exactly two reserve heroes, optional main/sub sidekick slots, duplicate-hero rejection, sidekick-as-hero rejection, owned/F2P hero enforcement, sidekick ownership or assumption checks, skill/passive existence checks, and conservative SA-gated skill/passive handling.
- Milestone 4 Feature C retrieves selected `Superboss` affinity/mechanics facts plus relevant `MechanicReference` rows before analysis, then passes a transparent fit-rubric context into recommendation reasoning. Fit labels cover legality, offense, defense, synergy, sustain, MP, sidekick contribution, build readiness, uncertainty, and upgrade burden; they are ranking signals, not win probabilities.
- Milestone 4 Feature D uses deterministic broad roster-fact retrieval for boss-aware lineup requests so recommendation prompts are grounded in available characters, skills, passives, Grasta context, and matching `Superboss` facts instead of over-narrow exact-match Cypher filters.
- Milestone 4 Feature E carries optional owned-sidekick selections from the web request through SSE state and PLAN normalization. Broad lineup retrieval includes ability and aura facts only for normalized selected sidekicks; when none are selected, analysis keeps both sidekick slots empty and surfaces the missing ownership context as a risk.
- `VALIDATE` and `ANALYZE` compact Neo4j result rows before LLM calls, bounding record count, nested list size, dictionary keys, and long text snippets to keep hosted-model prompt sizes controlled.
- `FORMAT` validates the final recommendation shape, checks graph-backed boss affinity facts for fidelity against the selected boss context, then checks every single-team, top-three, or alternatives lineup against graph-backed character, sidekick, skill, passive, ownership, and Stellar Awakening facts before rendering. Illegal, unverifiable, or boss-fact-mismatched recommendations fail gracefully before the web layer presents them. Feature D top-three outputs are validated as exactly three recommendation plans with archetypes, strategy summaries, build notes, boss counterplay, sustain/MP notes, risks, fit/confidence labels, and citations.

### Web Layer

- FastAPI entry point: `src/web/app.py`
- Route modules: `src/web/routes/`
- SSE bridge: `src/web/streaming.py`
- Driver dependency management: `src/web/dependencies.py`
- Templates and static assets: `src/web/templates/`, `src/web/static/`

Responsibilities:

- Accept character roster, owned-sidekick, and natural-language query input
- Start background workflow execution
- Stream progress updates over SSE
- Render three collapsed recommendation summaries with expandable evidence, explicit short-strategy and main-risk labels, and clear fallbacks when skills, passives, or upgrade assumptions are absent
- Render final result or graceful failure UI
- Expose admin-triggered ETL refresh

## Data and Contract Boundaries

`SCHEMA.md` is the contract authority for graph structure. Any feature that changes node labels, properties, relationships, output payload assumptions, or query semantics must be evaluated against `SCHEMA.md`.

Important boundaries:

- ETL models must conform to the schema contract before Neo4j load
- Workflow prompts and Cypher generation must assume only documented graph shapes
- Web responses must remain compatible with the current formatting layer and templates

## External Dependencies

- Neo4j 5 for graph storage
- OpenRouter by default, or Anthropic, Bedrock, or Ollama through the LLM provider factory
- `nodriver` plus Chrome for scraping
- FastAPI, Jinja2, and HTMX for web delivery

## Operational Constraints

- The validation retry cap is a hard cost-control mechanism and should not be bypassed casually.
- Prompt-context compaction is part of the workflow cost-control boundary and should stay in place for graph rows with verbose skill, passive, boss, or mechanics text.
- The scraper depends on a real browser environment and is sensitive to Cloudflare behavior.
- The graph contract should remain stable before prompt or Cypher examples are expanded.
- The UI is intentionally lightweight; major frontend changes should preserve streaming visibility and failure transparency.

## Current Architectural Priorities

- Preserve roster-constrained correctness and zero hallucinated mechanics
- Keep graph contract changes deliberate and documented
- Maintain clear separation between ETL, workflow, and web concerns
- Favor observable, testable nodes over opaque prompt chains
- Keep fallback behavior graceful when exact recommendations are unavailable

## Known Extension Points

- AF zone mechanics and damage scoring
- Grasta stat optimization and build ranking
- Dungeon and farming recommendation workflows
- Superboss guide generation and stopper analysis
- Richer admin and observability features

## Change Guidance

Update this file when a change affects any of the following:

- System boundaries or component ownership
- New runtime dependencies or infrastructure assumptions
- Data flow between ETL, workflow, and web layers
- Request lifecycle or output semantics
- Architectural decisions that future feature work must honor
