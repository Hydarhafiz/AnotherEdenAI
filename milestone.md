# AnotherEdenAI Milestone 3

## Executive Summary

Milestone 3 builds a verified RAG-ready combat data foundation before deeper AI lineup recommendation work. The focus is ETL structure, graph coverage, source attribution, quality gates, and operator runbooks for sidekicks, curated weak superbosses, and baseline equipment context.

This milestone intentionally prioritizes reliable scraped data over agent behavior. Recommendation intelligence, soft synergy scoring, turn-by-turn battle planning, exact damage calculation, and production deployment are deferred to later milestones.

## Scope And Intended User Outcome

The system should load enough structured combat context for future AI recommendations to reason from facts rather than guesses. After this milestone, the graph should support retrieval for:

- 6-hero lineup plus main and sub sidekick party composition.
- Official sidekick-to-character unlock or association facts.
- Sidekick auto skills, charge skills, and aura effects.
- Curated weak superboss identity, difficulty, affinities, characteristics, mechanics text, and source attribution.
- Existing character, skill, passive, Grasta, and Ore data without regression.
- Baseline weapon and armor stats/effects where practical, used as context rather than full optimization.

The portfolio story is that AnotherEdenAI has a deterministic, auditable ETL foundation with clear scrape scopes, diagnostics, and RAG-ready graph structure.

## Explicit Non-Goals

- No AI lineup recommendation implementation beyond preserving existing behavior.
- No exact numeric damage calculator.
- No full turn-by-turn battle simulator.
- No full equipment optimizer.
- No sidekick equipment ingestion.
- No AI-derived sidekick strategic synergy scoring.
- No broad all-superboss scrape requirement.
- No frontend redesign.
- No production VPS/AWS deployment implementation.
- No always-on cloud automation.

## Dependencies And Assumptions

- `SCHEMA.md` remains the graph contract source of truth and must be updated when schema changes land.
- Existing character, skill, passive, Grasta, Ore, and roster behavior must not regress.
- Cached raw HTML and parsed JSON remain the preferred durable ETL artifacts.
- Scraper runs may encounter Cloudflare and partial pages; failures must be explicit and diagnosable.
- Sidekick equipment is useful but lower priority than sidekick identity, abilities, aura, and official associations.
- Grasta/Ore is the highest-impact build layer, but the current data should be reused unless review reveals a blocking gap.
- Weapons and armor provide baseline attack/defense and effect context, but should not drive first-pass lineup decisions as strongly as Grasta/Ore or sidekicks.
- Development and ETL should remain runnable locally to avoid unnecessary monthly cost.

## Build-Impact Priority Model

1. Grasta/Ore: highest priority for damage multipliers, shareable party support, and future optimizer value.
2. Sidekick: high priority for aura, auto-action, charge skill, AF support, and official character association.
3. Weapon/Armor: baseline priority for attack, magic attack, defense, magic defense, and contextual effects.
4. Sidekick Equipment: deferred because impact is smaller and enhancement structure deserves its own milestone.

## Prioritized Feature Checklist

### Feature A: Sidekick Graph ETL

Status: Completed

Goal: Add sidekicks as first-class non-hero party members with structured ability and aura data.

Technical requirements:

- Scrape the Sidekick index as the canonical discovery source.
- Scrape selected sidekick detail pages from canonical wiki URLs.
- Add `Sidekick` nodes with identity, source URL, acquisition/unlock text where available, rarity/rank where available, and `schema_version`.
- Add structured child nodes for sidekick abilities:
  - `SidekickSkill` for auto skills.
  - `SidekickSkill` for charge skills.
  - `SidekickAura` for aura effects.
- Connect sidekicks to ability records using relationships such as `HAS_AUTO_SKILL`, `HAS_CHARGE_SKILL`, and `HAS_AURA`.
- Model official hero association or unlock facts using a relationship such as `(:Character)-[:UNLOCKS_SIDEKICK]->(:Sidekick)` when discoverable from wiki content.
- Keep sidekicks separate from `Character` nodes because party legality is 6 heroes plus main/sub sidekick slots.
- Represent main/sub sidekick behavior in data or documentation: main sidekick can use full sidekick abilities, while sub sidekick contributes aura-only effects.
- Treat Tetra Another Style and Minalca Another Style as a golden fixture for official association/unlock behavior.
- Unknown or irregular sidekick sections must be captured in diagnostics or raw text rather than silently ignored.
- Update `guides/ETL_GUIDE.md` when sidekick crawl controls, cache layout, quality gates, or debugging steps are implemented.

Acceptance criteria:

- Sidekick records load into Neo4j with source attribution.
- Sidekick auto skill, charge skill, and aura records are queryable separately.
- The graph can retrieve official sidekick-character association/unlock facts for at least one golden fixture.
- Sidekick records do not count as frontline or backline heroes.
- Selected sidekick pages either load successfully or fail with manifest diagnostics after retries.

### Feature B: Curated Weak Superboss ETL

Status: Not started

Goal: Add a small, reliable superboss seed set before scaling to broader boss coverage.

Technical requirements:

- Use the `Superbosses` wiki page as the canonical discovery index.
- Capture index metadata such as tier/level, refight status, version, characteristics, and linked detail URL where available.
- Detail-parse only a curated weak-boss allowlist in this milestone.
- Initial candidates include:
  - Zennon Ogre's Shadow
  - Flame Eater from the Gariyu chance encounter page
  - Nameless Girl
  - 2 to 5 additional Level 1 to 3 candidates after page-shape inspection
- Add `Superboss` nodes only when detail pages pass quality gates.
- Store structured fields where practical: `name`, `source_url`, `difficulty_tier`, `level`, `hp`, `weak`, `resist`, `null`, `absorb`, `characteristics`, `mechanic_tags`, `mechanics_text`, and `schema_version`.
- Store mechanics text for RAG grounding even when turn-by-turn structure is not reliable.
- Defer strict turn-event normalization unless a page has a clean table that can be parsed safely.
- Keep full superboss coverage as a later scaling milestone.
- Update `guides/ETL_GUIDE.md` when boss discovery, allowlists, crawl controls, or quality gates are implemented.

Acceptance criteria:

- The index can discover superboss candidates without loading unvalidated index-only facts as final boss nodes.
- At least 3 weak superbosses load with source URL, difficulty/tier context, affinity fields or explicit unknowns, and mechanics text.
- At least one section-anchored boss page, such as Flame Eater, is handled or fails with clear diagnostics.
- The graph can retrieve boss weak/resist/null/absorb fields and mechanics text without LLM inference.
- Selected boss URLs are not silently skipped.

### Feature C: Grasta/Ore Preservation And Lightweight Retrieval Tags

Status: Not started

Goal: Preserve the existing highest-impact build data while adding only safe metadata needed for retrieval.

Technical requirements:

- Do not rebuild Grasta/Ore scraping from scratch in this milestone.
- Preserve existing Grasta, Ore, Trait, and related relationship behavior.
- Add lightweight effect tags or multiplier metadata only when they can be parsed cheaply and safely from existing fields.
- Keep Grasta/Ore data review as a required handoff item before the AI lineup recommendation milestone.
- Avoid introducing unverified exact damage math.

Acceptance criteria:

- Existing Grasta/Ore ETL and schema assertions still pass.
- Existing graph queries for shareable Grasta compatibility still work.
- Any new tags include source or derivation clarity.
- Open Grasta/Ore coverage questions are documented for the next milestone review.

### Feature D: Weapon And Armor Baseline ETL

Status: Not started

Goal: Add baseline equipment context for future damage and survivability reasoning without building a full optimizer.

Technical requirements:

- Scrape weapon and armor index/list pages where page structure is stable enough.
- Add baseline equipment nodes such as `Weapon` and `Armor`, or a shared `Equipment` model if that better matches observed data.
- Capture baseline fields where available:
  - name
  - type/category
  - level or tier
  - attack/magic attack for weapons
  - defense/magic defense for armor
  - effect text
  - obtain/source text
  - source URL
  - `schema_version`
- Treat weapons as attack/magic attack baseline before Grasta/Ore multipliers.
- Treat armor as defense/sustainability baseline.
- Do not rank best-in-slot equipment in this milestone.

Acceptance criteria:

- A small selected equipment scope can load baseline weapon and armor data with source attribution.
- Equipment effects are retrievable as text for future RAG use.
- Equipment load failures are tracked in the manifest.
- The implementation does not imply exact damage or survivability optimization.

### Feature E: ETL Reliability, Manifest, And RAG Readiness Gates

Status: Not started

Goal: Define measurable ETL success so the milestone is judged by data quality, not subjective AI output.

Technical requirements:

- Every selected URL must end in an explicit state such as loaded or failed after retries.
- Failed URLs must include diagnostics: URL, stage, attempt count, last error, quality-gate reason, and cache artifact references where available.
- Parsed JSON must be able to reload Neo4j without live scraping.
- Every loaded graph entity must have source URL attribution where the wiki source exists.
- Every structured node added in this milestone must include `schema_version`.
- Add or update schema assertion coverage for new labels and relationships.
- Maintain local/offline ETL operation guidance to keep development cost low.
- Update `guides/ETL_GUIDE.md` for new commands, troubleshooting, manifest states, and replay-from-cache workflows.

Acceptance criteria:

- Selected crawl scope has 100% pass/fail accountability.
- Curated sidekick and weak-superboss scope targets 90-100% successful load rate.
- No selected URL is silently skipped.
- Schema assertions pass after loading selected scope.
- Golden retrieval queries prove sidekick association, sidekick ability/aura, boss affinity, boss mechanics text, and baseline equipment context.
- The ETL can be rerun from parsed artifacts without live wiki access.

## Planned Sub-Guides

- Update `guides/ETL_GUIDE.md` for sidekick, boss, equipment, manifest, cache, quality-gate, and local/offline operation steps.
- Add a short ETL coverage review section or future guide before the AI lineup recommendation milestone. This review should inspect whether Grasta/Ore, sidekick, boss, weapon, and armor fields are enough for legal lineup generation.

## Current Completion Status

- Milestone 3 planning: complete
- Feature A: completed
- Feature B: not started
- Feature C: not started
- Feature D: not started
- Feature E: not started

## Open Questions

- After inspecting sidekick pages, are there sidekicks with irregular extra ability or aura sections that require additional node types?
- After inspecting weak superboss pages, which 2 to 5 additional Level 1 to 3 bosses should join the seed set?
- Should weapons and armor share one equipment label or use separate labels after real page-shape inspection?
- Which Grasta/Ore fields are missing for the next AI lineup recommendation milestone?
