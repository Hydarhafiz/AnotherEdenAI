# AnotherEdenAI Milestone 4

## Executive Summary

Milestone 4 builds the first source-grounded AI lineup recommendation navigator for curated Another Eden superbosses. The milestone focuses on legal, roster-constrained, boss-aware team formation using the RAG-ready graph foundation from Milestone 3 plus a new manually curated battle-mechanics corpus stored in Neo4j.

The system should recommend three lineup archetypes for a selected weak superboss: burst, sustain, and hybrid. Recommendations are navigation and inspiration, not deterministic win predictions. They should explain why each lineup is plausible, cite boss facts and battle-mechanics references, surface risks and assumptions, and avoid unsupported certainty.

## Scope And Intended User Outcome

The user should enter an owned roster, optionally include Stellar Awakening state and owned sidekicks, select one of the supported weak superbosses, and receive three legal 6-hero plus 2-sidekick lineup plans:

- Burst lineup for fast weakness-focused pressure and AF or zone burst.
- Sustain lineup for safer long-fight play with healing, mitigation, status handling, and MP stability.
- Hybrid lineup balancing damage and survivability.

Each recommendation should provide a compact default view plus expandable detail for character roles, recommended skills, sidekick choices, Grasta/Ore/equipment build notes, boss counterplay, risks, confidence, and citations.

The portfolio story is that AnotherEdenAI moves from general GraphRAG answering into a transparent recommendation system with hard legality checks, source-grounded mechanics retrieval, and evaluation gates that prevent hallucinated or impossible teams.

## Explicit Non-Goals

- No exact deterministic damage simulator.
- No numeric win-probability prediction.
- No full turn-by-turn battle simulator.
- No all-superboss support.
- No intermediate or strong superboss evaluation tiers.
- No full equipment, Grasta, Ore, badge, or Light/Shadow optimizer.
- No exact player inventory entry for every Grasta, Ore, weapon, or armor.
- No alternative not-owned character or pull-planning recommendations in the active lineup output.
- No sidekick equipment optimization.
- No major frontend redesign beyond recommendation-result presentation needed for compact and expandable output.
- No production deployment work.

## Dependencies And Assumptions

- Milestone 3 ETL data remains available: Characters, Skills, PassiveSkills, Sidekicks, SidekickSkills, SidekickAuras, curated weak Superbosses, Grastas, Ores, and baseline Equipment.
- `docs/core/SCHEMA.md` is the graph contract source of truth and must be updated when `MechanicReference` nodes or recommendation-related schema changes are introduced.
- `docs/core/planning-sources.md` stores the source references and planning decisions that ground this milestone.
- The target user is endgame or near-endgame and can be assumed to have general late-game Grasta/Ore/equipment access.
- Build advice may recommend common late-game setup patterns, but rare or specific assumptions must be labeled.
- Roster input requires owned character names. Stellar Awakening state and sidekick ownership are optional in Milestone 4.
- Light/Shadow detail is deferred unless a specific legality or skill-slot requirement makes it necessary.
- Recommendations should use transparent fit and confidence labels, not exact success probability.
- Kimi K2.6 or similar OpenRouter models may be used for final reasoning/ranking when cost is controlled, but deterministic legality and retrieval filtering should minimize unnecessary paid-token usage.

## Research References And Source Grounding

Detailed references and planning decisions live in `docs/core/planning-sources.md`.

Primary external mechanics sources for this milestone include:

- Damage Formula
- Buffs and Debuffs
- Status Effects
- Zones
- Battle Mechanics
- Another Force
- Grasta
- Stats
- Healing Formula
- Speed Control
- Stellar Awakening
- Turn Order
- Sidekick

Source-grounding notes:

- Battle-mechanics sources are primary RAG references for recommendation reasoning.
- Wiki mechanics should be scraped/cached into project artifacts, then manually curated section-by-section into recommendation-focused `MechanicReference` records.
- Exact damage, healing, AF, speed, and survival calculations remain research-backed context for reasoning, not deterministic simulation commitments in this milestone.
- The Another Eden Wiki is a community source; recommendations should cite retrieved facts and mark uncertainty when data is incomplete.

## Prioritized Feature Checklist

### Feature A: Battle Mechanics Corpus And `MechanicReference` Graph

Status: Completed

Goal: Add a compact, manually curated mechanics RAG layer so the recommender grounds lineup reasoning in source-backed battle rules before proposing teams.

Technical requirements:

- Scrape/cache the full referenced mechanics pages as durable raw artifacts.
- Create curated section artifacts for the recommendation-focused golden corpus.
- Store curated entries in Neo4j as `MechanicReference` nodes.
- Include fields such as:
  - `id`
  - `title`
  - `source_url`
  - `source_page`
  - `section_path`
  - `mechanic_type`
  - `topic_tags`
  - `applies_to`
  - `rules_text`
  - `summary`
  - `caveats`
  - `schema_version`
- Cover at least the golden mechanics needed for lineup navigation:
  - party/frontline/reserve basics
  - main and sub sidekick behavior
  - weakness, resist, null, and absorb handling
  - high-level damage multiplier factors
  - healing and sustain basics
  - buffs, debuffs, mitigation, and resistance support
  - status effects and cleanse/protection relevance
  - zone/stance basics
  - Another Force basics
  - speed, preemptive, delayed, and turn-order basics
  - Stellar Awakening-gated skills/passives
  - Grasta/Ore DPS and support setup basics
- Load from curated local artifacts so corrections can replay without repeated live scraping.
- Add schema assertions and golden retrieval tests for important mechanics.
- Update `docs/core/SCHEMA.md` when node labels/properties are introduced.
- Update or add `docs/guides/ETL_GUIDE.md` coverage for mechanics corpus scrape/cache/replay behavior if the implementation extends ETL commands.

Acceptance criteria:

- Raw mechanics source pages are cached in project artifacts.
- Curated mechanics artifacts can load `MechanicReference` nodes into Neo4j.
- Every loaded mechanics entry has source URL, section/source context, topic tags, rules text or summary, and schema version.
- Golden retrieval tests can find relevant references for weakness handling, main/sub sidekick behavior, Stellar Awakening gating, speed/turn order, sustain, and Grasta/Ore setup.
- The recommender can retrieve mechanics references separately from boss, character, sidekick, and equipment facts.

### Feature B: Roster And Party Legality Contract

Status: Completed

Goal: Prevent impossible recommendations before AI ranking or explanation happens.

Technical requirements:

- Define a structured roster input model with required owned character names and optional fields for:
  - Stellar Awakening state
  - owned sidekicks
- Preserve existing name normalization and free-to-play augmentation behavior where appropriate.
- Define a structured lineup model with:
  - exactly 4 frontline heroes
  - exactly 2 reserve heroes
  - optional or selected main sidekick
  - optional or selected sub sidekick
  - no duplicate heroes
  - no sidekick counted as a hero
- Validate that actual lineup heroes are owned or allowed free-to-play additions.
- Validate that selected sidekicks are owned or explicitly available through known assumptions.
- Validate that recommended skills exist on the selected character.
- Validate Stellar Awakening-gated skills/passives against roster SA state when known.
- Treat unknown SA state conservatively in actual usable recommendations and label upgrade assumptions separately.
- Keep Light/Shadow out of required input unless a specific legality or skill-slot rule needs it.

Acceptance criteria:

- Invalid lineup shapes fail before final output.
- Hallucinated characters, duplicate heroes, sidekick-as-hero errors, and unsupported skills fail tests.
- SA-gated skill recommendations are either legal for the roster state or clearly labeled as an upgrade assumption.
- Tests cover owned-roster enforcement, sidekick slot rules, skill existence, and 4-frontline/2-reserve shape.

### Feature C: Boss Matchup Retrieval And Transparent Fit Rubric

Status: Completed

Goal: Rank and explain candidate lineups as a navigation tool using transparent fit criteria rather than fake win probability.

Technical requirements:

- Retrieve selected boss facts from the graph:
  - weakness
  - resist
  - null
  - absorb
  - characteristics
  - mechanic tags
  - mechanics text
  - source URL
- Retrieve relevant mechanics references from `MechanicReference`.
- Retrieve candidate character skills/passives, sidekick abilities/auras, Grasta/Ore tags, and equipment context as needed.
- Implement or define a transparent rubric with labels such as high, medium, low, or numeric sub-scores used internally for ranking.
- Rubric categories should include:
  - legality gate
  - boss matchup offense
  - boss matchup defense
  - lineup synergy
  - sustain and recovery
  - MP sustainability
  - sidekick contribution
  - Grasta/Ore/equipment readiness
  - uncertainty or missing data penalty
  - upgrade burden penalty
- Prioritize boss weakness coverage while penalizing resist/null/absorb conflicts.
- Reward defensive resistance, mitigation, cleanse, status handling, healing, and long-fight stability where boss mechanics call for them.
- Keep the language and data model clear that scores are fit/ranking signals, not success probabilities.

Acceptance criteria:

- Matchup evaluation never presents numeric win probability.
- Recommendations explain offense, defense, synergy, sustain, MP, sidekick, and upgrade-burden tradeoffs where relevant.
- Boss affinity facts in recommendation output match graph facts.
- Missing or uncertain data lowers confidence or adds risk notes rather than producing unsupported certainty.
- Unit tests cover affinity handling, missing data behavior, and rubric output shape.

### Feature D: Top 3 Lineup Recommendation Contract

Status: Planned

Goal: Produce three useful, legal, source-grounded lineup plans for each supported boss.

Technical requirements:

- Generate three archetype-oriented recommendations when viable:
  - Burst
  - Sustain
  - Hybrid
- If the boss strongly favors one archetype, allow variants but require the output to explain why other archetypes are weaker.
- For each lineup, provide:
  - frontline heroes
  - reserve heroes
  - main sidekick
  - sub sidekick
  - archetype
  - compact strategy summary
  - per-character role
  - recommended 3 or 4 skills per character where data supports it
  - key skill/passive/sidekick facts
  - Grasta/Ore/equipment build notes under late-game-access assumptions
  - boss counterplay notes
  - sustain and MP notes
  - risks and assumptions
  - fit/confidence labels
  - source citations to graph facts and mechanics references
- Actual lineups must use owned roster characters only, plus allowed free-to-play additions if the existing system keeps that behavior.
- Do not include not-owned alternative character or pull-planning suggestions in active output.
- Keep output structured with Pydantic validation before rendering.
- Use a single final reasoning/ranking call where practical to control OpenRouter cost.

Acceptance criteria:

- For each supported weak boss, the system can produce burst, sustain, and hybrid lineup recommendations or explain why one archetype is not viable.
- Each lineup passes legality validation.
- Each lineup includes cited boss and mechanics evidence.
- Recommended skills exist and respect known SA gating.
- Output clearly separates usable recommendations, build assumptions, risks, and uncertainty.
- Token usage is bounded by compact retrieval context and structured output limits.

### Feature E: Compact And Expandable Recommendation UI

Status: Planned

Goal: Present rich recommendation data without overwhelming the user.

Technical requirements:

- Render a compact default result for each of the top 3 lineups:
  - archetype
  - heroes and sidekicks
  - short strategy
  - fit/confidence
  - main risks
- Add expandable details for:
  - character role and placement
  - recommended skills
  - build notes
  - sidekick reasoning
  - boss counterplay
  - sustain/MP notes
  - citations
  - assumptions and uncertainty
- Preserve existing streaming progress visibility and graceful failure behavior.
- Avoid a large frontend redesign; focus only on result rendering needed for the new contract.

Acceptance criteria:

- Default output is scannable and shows all three lineup archetypes.
- Detailed evidence is available without cluttering the default view.
- Failed legality/factuality checks render a clear graceful error instead of a misleading recommendation.
- Existing web route and streaming tests are updated for the new output shape.

### Feature F: Evaluation Gates And Golden Weak-Boss Set

Status: Planned

Goal: Verify the navigator with deterministic gates first, then judge recommendation quality only after impossible outputs are blocked.

Technical requirements:

- Use a golden evaluation set of 5 curated weak superbosses from the Milestone 3 data foundation.
- Design eval metadata so future tiers can add `weak`, `intermediate`, and `strong` boss groups, but defer non-weak tiers.
- Prioritize deterministic legality and factuality tests:
  - exactly 6 heroes
  - 4 frontline and 2 reserve
  - main/sub sidekick legality
  - only owned characters in actual lineups
  - no duplicate heroes
  - recommended skills exist
  - SA-gated skills are legal or clearly labeled as upgrade assumptions
  - boss facts match graph facts
  - cited mechanics references exist
  - no numeric win-probability claims
- Add recommendation quality judge tests only after legality/factuality gates pass.
- Quality judging should evaluate:
  - burst lineup behaves like burst
  - sustain lineup includes sustain/mitigation
  - hybrid lineup is meaningfully balanced
  - tradeoffs are useful
  - risks and assumptions are honest
  - recommendation is helpful as navigation

Acceptance criteria:

- The system passes deterministic legality and factuality tests for the 5 weak-boss eval set.
- Quality judge tests run only after core gates pass.
- Eval reports separate hard failures from subjective quality feedback.
- Intermediate and strong boss eval tiers are explicitly deferred but easy to add later.

## Planned Guide Updates

- Update `docs/guides/ETL_GUIDE.md` or add a mechanics corpus guide if mechanics source scraping, cache layout, curated artifact editing, or Neo4j replay commands become reusable operator workflows.
- Add recommendation evaluation guidance if the golden weak-boss eval workflow requires repeated manual commands, report interpretation, or cleanup steps.

## Current Completion Status

- Milestone 4 planning: in progress
- Feature A: planned
- Feature B: planned
- Feature C: planned
- Feature D: planned
- Feature E: planned
- Feature F: planned

## Open Questions

- Which exact 5 weak superbosses should be selected for the golden evaluation set?
- Should `MechanicReference` retrieval start with keyword/topic-tag matching only, or include vector search in the first implementation?
- How should optional Stellar Awakening state be represented in the web form and API payload?
- Which model/provider should be used for final recommendation ranking during local development and portfolio demos?
