# AnotherEdenAI Milestone 2

## Executive Summary

Milestone 2 transitions AnotherEdenAI from a static graph lookup baseline into a backend-first GraphRAG and MLOps system for boss-aware team recommendations. The work focuses on resilient ETL, expanded Neo4j combat data, richer roster constraints, and automated LLM evaluation.

This milestone is strictly backend, ETL, graph schema, workflow, and AI evaluation scope. There is no frontend or UI work.

## Scope And Intended User Outcome

The system should recommend the best available lineup for a queried boss based on the user's owned roster, Stellar Awakening state, Light/Shadow points, character skills, passive mechanics, boss mechanics, and supporting build context.

For Milestone 2, "best lineup" means best mechanic fit and constraint legality. Exact numeric damage calculation is explicitly out of scope because Another Eden damage math is complex, inventory-dependent, and difficult to verify reliably at this stage.

The user-facing recommendation target is:

- A primary lineup that is legal for the user's current roster state.
- Optional backup lineup when the owned roster has enough viable alternatives.
- Optional upgrade or advanced suggestions for missing characters, Stellar Awakening unlocks, or investment paths that directly solve the queried boss mechanic.
- Boss-specific explanation and turn 1-2 priority skill guidance with role assignments.
- Clear disclaimer that exact damage output is not calculated.

## Explicit Non-Goals

- No frontend, UI, template, CSS, or web interaction changes.
- No full turn-by-turn battle simulator.
- No exact numeric damage calculator.
- No mandatory full Grasta optimizer or best-in-slot equipment solver.
- No mandatory Badge assignment for every lineup.
- No human expert-labeled supervised benchmark dataset.
- No full normalized combat ontology for every buff, debuff, trigger, zone, stack, and turn condition.
- No live A/B testing product layer. Provider switching is configurable, but the milestone does not require a production experiment dashboard.
- No FastAPI/admin ETL trigger expansion unless needed to preserve existing behavior.

## Dependencies And Assumptions

- `SCHEMA.md` remains the graph contract source of truth and must be updated during implementation when schema changes land.
- Neo4j remains the canonical store for graph-native combat data.
- Cached raw HTML is the long-lived source artifact for wiki data.
- Parsed JSON is a schema-versioned derived artifact and must be regenerated when schema changes invalidate it.
- Character and boss wiki pages may trigger Cloudflare or partial page loads.
- Operator-assisted browser challenge handling is allowed for long scrape runs.
- Kimi is the preferred low-cost generation model for reasoning nodes, while provider selection remains configurable.
- Claude or another stronger configurable paid judge model is expected for the full evaluation tier.
- Evaluation credentials must be supplied by the operator; missing paid-provider credentials fail the full evaluation tier when it is required.
- Existing simple roster input must remain backward-compatible through normalization.

## Prioritized Feature Checklist

### Feature A: Resumable Cached ETL Foundation

Status: Not started

Goal: Make long-running wiki ingestion reliable, debuggable, and restartable while reducing repeated live requests.

Technical requirements:

- Separate fetching, parsing, validation, and loading into distinct pipeline stages.
- Save raw HTML for every fetched URL under the local raw data cache.
- Save normalized parsed JSON snapshots as schema-versioned artifacts.
- Treat parsed JSON as invalid when its schema version does not match the active ETL schema.
- Load Neo4j from parsed JSON without requiring a live wiki fetch.
- Add a resumable crawl manifest that tracks each URL through states such as `pending`, `cached`, `parsed`, `loaded`, and `failed`.
- Record per-URL diagnostics such as attempt count, last error, HTML byte size, Cloudflare/challenge detection, parsed counts, and quality status.
- Retry failed URLs up to 3 times before failing the ETL run.
- Support operator-assisted browser sessions for Cloudflare clearance, including browser profile reuse where practical.
- Add configurable crawl controls for incremental runs, including small test runs, fallback-sized crawls, resume mode, and full-corpus attempts.

Acceptance criteria:

- ETL can resume after interruption without discarding successfully cached pages.
- A failed URL is visible in the manifest with enough detail to debug it.
- The loader can run from cached parsed JSON with no live wiki access.
- Unresolved failed URLs fail the ETL run for the selected crawl scope after 3 retries.
- The pipeline can intentionally run small-scope, fallback-scope, and full-scope crawls.

### Feature B: Combat Graph Schema Expansion

Status: Not started

Goal: Expand the Neo4j graph from character/grasta lookup into a richer combat knowledge graph while keeping the first implementation simple.

Technical requirements:

- Add or verify `Character.is_SA` as a game-data boolean meaning Stellar Awakening exists for that character.
- Infer or verify `Character.is_SA` from character detail pages when Stellar Awakened sections exist, not only from index/list metadata.
- Add `Skill` nodes for executable active skills and basic attack replacements.
- Add `PassiveSkill` nodes for passive skills, stacks, stances, zones, battle-start effects, Stellar Awakening passives, and other non-executable mechanics.
- Connect characters to combat entries with `HAS_SKILL` and `HAS_PASSIVE_SKILL`.
- Store rich descriptions as text properties under the Option A schema approach.
- Include baseline skill fields where available: `name`, `character_name`, `element`, `skill_type`, `mp`, `description`, `multiplier`, `source_url`, `section`, `requires_stellar_awakened`, and `schema_version`.
- Include baseline passive fields where available: `name`, `character_name`, `description`, `source_url`, `section`, `passive_type`, `requires_stellar_awakened`, and `schema_version`.
- Treat missing optional page sections as valid only when identity and required combat data pass quality checks.
- Use page quality gates to detect partial/blocked pages.
- Expect most characters to have around 8 active skills; zero active skills should fail unless explicitly documented as an exception.

Acceptance criteria:

- Character detail pages produce graph-native active skill and passive skill data.
- SA-gated skills/passives are marked and distinguishable from normal skills/passives.
- A character with missing optional Stellar Awakened or stance/zone sections can still parse successfully.
- A blocked or partial page with no recognizable combat data fails quality validation.

### Feature C: Superboss And Badge Data Ingestion

Status: Not started

Goal: Add boss mechanics and badge data to the graph so recommendations can reason against concrete fight constraints and optional build context.

Technical requirements:

- Use the wiki `Superbosses` page as the canonical discovery index for powerful optional boss candidates.
- Keep manual allowlist/limit controls for development and fallback runs, but treat the index as the source of truth for discovery.
- Add graph-native `Superboss` nodes using an Option A schema only after the linked detail page passes quality checks.
- Keep index-only boss rows in the crawl manifest as discovered or pending records, not as Neo4j `Superboss` facts.
- Boss detail quality gates must require identity, source URL, location/context, at least one stat or HP field, structured affinity data or explicit unknown, and at least one parsed mechanics/skills/turn-script section.
- Baseline boss properties are provisional pending real ETL inspection: `name`, `source_url`, `difficulty_label`, `location`, `hp`, `weak`, `resist`, `null`, `absorb`, `mechanics_text`, `turn_script_text`, `turn_events`, `mechanic_tags`, `offensive_elements`, `offensive_skill_types`, `status_effects_inflicted`, and `schema_version`.
- Store boss damage affinities as structured list properties only: `weak`, `resist`, `null`, and `absorb`.
- Standardize affinity, element, and skill-type values against the wiki Battle Mechanics vocabulary where possible, including `Slash`, `Pierce`, `Blunt`, `Magic`, `Fire`, `Water`, `Earth`, `Wind`, `Thunder`, `Shade`, and `Crystal`.
- Store complete turn mechanics in `turn_script_text` for LLM context.
- Store best-effort `turn_events` JSON for row-level debugging, evaluation, and future migration.
- Each `turn_events` item should include `turn`, `name`, `effect`, and best-effort parsed `elements` and `skill_types` when detectable.
- Store aggregate boss offense fields: `offensive_elements` and `offensive_skill_types`.
- Store aggregate `status_effects_inflicted` for statuses the boss can apply, standardized where possible.
- Keep statuses, buffs, debuffs, zones, AF effects, and resource effects in text fields, turn-event effects, and mechanic tags for Milestone 2 rather than fully normalizing them.
- Store `mechanic_tags` as best-effort retrieval metadata generated from index characteristics and detail-page text.
- Allow both recognized/common mechanic tags and freeform tags for unusual boss mechanics.
- Prefer JSON mechanic tag objects with fields such as `tag`, `source`, `confidence`, and `evidence_text`.
- Allow simple string mechanic tags as an exception for irregular pages that cannot reliably fit the default tag object shape.
- Boss PoC selection is capability-based, not tied to specific named bosses.
- Initial boss cases must be mechanically rich enough to test AF interaction, survivability, status handling, zone behavior, or roster constraints.
- Attempt full boss scraping when possible, but support fallback-sized crawl scope.
- Add graph-native `Badge` nodes.
- Baseline badge properties are provisional: `name`, `stats`, `effect`, `source`, `source_url`, and `schema_version`.
- Badge data may be referenced when directly relevant, but lineup output does not need mandatory badge assignments.
- Do not ingest general Battle Mechanics, Status Effects, Buffs & Debuffs, or other reference documentation as Feature C graph artifacts.

Acceptance criteria:

- Boss candidates are discovered from the `Superbosses` index.
- Neo4j `Superboss` nodes are created only for detail pages that pass quality checks.
- At least the fallback crawl scope can load boss data into Neo4j with structured affinity, offense, status, turn-event, and mechanic-tag fields.
- At least 1-2 mechanically rich boss records can be used by the workflow for boss-aware recommendations.
- Recommendations can prefer skills that hit boss `weak` affinities and avoid primary damage plans that hit boss `null` or `absorb` affinities unless the plan explicitly accounts for an affinity-changing mechanic.
- Recommendations can consider boss offensive elements, offensive skill types, and inflicted statuses when explaining survivability, cleanse, resistance, immunity, or mitigation needs.
- Badge records are ingested and queryable from Neo4j.
- Boss and badge fields can be revised after ETL data inspection without changing the milestone's Option A strategy.

### Feature D: Coverage Targets And Crawl Policy

Status: Not started

Goal: Define practical ingestion coverage while acknowledging Cloudflare and long-running crawl risk.

Technical requirements:

- Target coverage: scrape and load the full available character skill/passive corpus and full available superboss corpus when the wiki allows it.
- Minimum fallback coverage: at least 100+ characters with skills/passives and 20+ superbosses, selected through explicit crawl scope controls.
- The fallback threshold is a planned crawl scope, not permission to silently skip failed URLs inside the selected scope.
- Any URL selected for a run must pass fetch, parse, quality, and load stages or fail the ETL run after retries.

Acceptance criteria:

- A fallback-sized run can be executed intentionally and tracked through the manifest.
- A full-corpus attempt can resume from prior cached progress.
- Selected-scope failures are surfaced as ETL failures, not hidden omissions.

### Feature E: Roster Constraint Model

Status: Not started

Goal: Make recommendations legal against the player's actual roster state, including ownership, Stellar Awakening, and Light/Shadow investment.

Technical requirements:

- Normalize simple roster entries into structured entries.
- Default structured roster shape:

```json
{
  "name": "Alma AS",
  "owned": true,
  "stellar_awakened": false,
  "light_shadow_points": 0
}
```

- `Character.is_SA` means the game character has Stellar Awakening available.
- Roster `stellar_awakened` means the player has unlocked SA for that owned character.
- Plain name input remains supported and defaults to `owned=true`, `stellar_awakened=false`, and `light_shadow_points=0`.
- Automatic F2P roster augmentation must not make characters legal by default. Free and gacha characters are treated the same: they are legal only when explicitly listed/owned.
- Use Light/Shadow thresholds:
  - `< 80`: max 3 active equipped skills.
  - `>= 80`: max 4 active equipped skills.
  - `>= 120`: extra badge-slot context recorded for future equipment reasoning.
  - `>= 200`: extra grasta-slot context recorded for future Grasta reasoning.
- Hard enforcement in Milestone 2 is required for active skill slot count.
- SA-only skills/passives must not be presented as currently usable unless `stellar_awakened=true`.
- SA unlocks may be suggested only in upgrade/advanced sections when they directly solve the queried boss mechanic.

Acceptance criteria:

- Existing simple roster input continues to work through normalization.
- Main recommended teams include only owned characters.
- Main recommendations do not use SA-only skills for non-SA roster entries.
- Main recommendations do not equip more than 3 active skills for characters below 80 Light/Shadow or more than 4 for characters at or above 80.
- Missing characters, SA unlocks, or investment advice appear separately from the legal primary lineup.

### Feature F: Boss-Aware Recommendation Contract

Status: Not started

Goal: Align workflow behavior with the expanded graph while keeping output cost and complexity reasonable.

Technical requirements:

- Main output must recommend legal heroes and selected active skills against the queried boss.
- Output must include boss-specific counterplay reasoning.
- Output must include turn 1-2 priority skills and role assignments, not a full fight rotation.
- Output may include contextual Grasta suggestions when directly relevant, especially pain/poison or personality-compatible patterns.
- Grasta advice must be framed as optional build optimization unless a later optimizer makes it enforceable.
- Output may include contextual Badge suggestions when directly relevant.
- Primary lineup is required when enough legal roster data exists.
- Backup lineup is required only when the owned roster has enough viable alternatives.
- Upgrade/advanced suggestions may include missing characters, SA unlocks, or investment paths that directly solve the boss.
- The workflow output contract may remain natural-language initially and should be revisited after ETL data inspection.

Acceptance criteria:

- Recommendations explain why selected characters and skills address the boss mechanics.
- The system can gracefully return a best-effort provisional team with uncertainty when data is incomplete.
- Missing roster upgrades are boss-specific and do not become broad generic pull advice.
- The response includes a disclaimer that exact damage output is not calculated.

### Feature G: Configurable Provider Routing

Status: Not started

Goal: Keep provider usage cost-aware and swappable without building a full experiment platform.

Technical requirements:

- Expand the LLM provider factory so generation and judge providers are independently configurable.
- Prefer Kimi as the default low-cost reasoning provider.
- Keep Claude or another stronger paid model configurable for judging and fallback.
- Preserve existing syntax-heavy routing behavior where Claude may remain useful for Cypher generation if configured.
- Avoid hard-coding provider choices into workflow nodes.

Acceptance criteria:

- The operator can switch reasoning provider without code redesign.
- The operator can switch judge provider without code redesign.
- Provider configuration is visible enough for eval reports to identify which model produced and judged each run.

### Feature H: Two-Tier LLM Evaluation Framework

Status: Not started

Goal: Add CI/CD-ready evaluation that measures objective correctness cheaply first, then runs deeper paid evaluation only after basic gates pass.

Technical requirements:

- Build a `pytest` evaluation suite around a golden/adversarial dataset of approximately 20-30 queries.
- Use unsupervised LLM-as-a-judge evaluation, not human expert-supervised expected perfect teams.
- Include normal boss recommendation cases with rosters around 12-20 owned characters.
- Include adversarial cases such as impossible rosters, ambiguous boss requests, missing data, non-SA roster entries, SA upgrade opportunities, and skill-slot legality.
- Tier 1 is mandatory and uses Ollama or free OpenRouter-compatible models where possible.
- Tier 1 evaluates objective gates:
  - Strict factuality/hallucination.
  - Roster constraint adherence.
  - Schema formatting.
  - Skill-slot legality.
- Tier 2 runs only after Tier 1 passes and is mandatory at that point.
- Tier 2 uses the configured stronger paid judge model.
- Missing paid-provider credentials fail the overall evaluation run when Tier 2 is required.
- Tier 2 evaluates all metrics:
  - Strict factuality/hallucination.
  - Roster constraint adherence.
  - Tactical synergy and boss mechanic adherence.
  - Schema formatting.
  - Skill-slot legality.
- Tactical synergy should inspect both final recommendations and written reasoning/explanation.
- Tactical synergy starts as scored/reportable quality rather than the primary hard CI gate.

Acceptance criteria:

- CI fails on schema invalidity, roster-rule violations, skill-slot violations, or factual hallucination.
- CI reports tactical synergy and boss mechanic adherence scores from the paid judge tier.
- Eval reports identify model/provider configuration for generator and judge.
- The eval dataset includes at least one SA-gated scenario and one skill-slot legality scenario.
- Free/local model failures are visible in Tier 1 and can be used to decide whether paid evaluation is needed.

## Current Completion Status

- Milestone 2 planning: complete
- Feature A: not started
- Feature B: not started
- Feature C: not started
- Feature D: not started
- Feature E: not started
- Feature F: not started
- Feature G: not started
- Feature H: not started

## Open Questions

- After ETL inspection, should workflow output move from natural-language sections into strict structured fields such as `team`, `role_assignments`, `turn_1_2_skill_plan`, `boss_counterplay`, `upgrade_path`, and `confidence`?
- After real character and boss pages are parsed, should any combat mechanics graduate from Option A text properties into Option B normalized nodes or relationships?
- After Badge and Grasta data are available, what should be the next optimizer milestone boundary for equipment and damage setup?
