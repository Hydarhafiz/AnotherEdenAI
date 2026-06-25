# AnotherEdenAI Milestone 5 Plan

## Executive Summary

Status: Active.

Milestone 5 turns the completed Milestone 4 recommendation contract into a measurable, cost-controlled portfolio system. The epic starts with graph hygiene and deterministic recommendation policy, then adds evaluation, paid-provider reporting, and live-site safeguards before public beta or deployment.

The guiding product outcome is a controlled Discord beta for roughly 20-30 Another Eden players. The beta should generate useful feedback and portfolio case-study evidence without allowing uncontrolled LLM spend. The starter OpenRouter budget target is RM50/month for public demo or beta periods, with warning thresholds and a hard stop before the ceiling is exceeded.

## Scope And Intended User Outcome

The system owner should be able to run recommendations locally with free/local models, promote the same flows through staging and release tests with the intended paid OpenRouter model, and produce evaluation reports that show legality, factuality, quality, latency, and cost evidence.

Beta testers should receive legal, boss-aware top-three lineup recommendations without seeing internal guardrail complexity. The app should reject impossible recommendations before display, preserve transparent risks and assumptions, and prevent repeated public requests from creating runaway bills.

Portfolio reviewers should see a credible AI engineering story: deterministic backend validation handles fixed constraints, paid AI is reserved for dynamic recommendation judgment and release-quality evidence, and public demo operations are bounded by authentication, rate limits, and monthly cost controls.

## Explicit Non-Goals

- No exact deterministic damage simulator.
- No numeric win-probability or clear-rate prediction.
- No full turn-by-turn battle simulator.
- No full all-superboss evaluation tier.
- No intermediate or strong superboss evaluation tier.
- No complete player inventory optimizer for weapons, armor, Grasta, Ores, badges, or sidekick equipment.
- No sidekick equipment ingestion or optimization.
- No always-on production deployment.
- No public unauthenticated unlimited recommendation endpoint.
- No paid judge model call on every live user recommendation.
- No replacement of the Milestone 4 recommendation UI beyond targeted status, error, cost, or limit messaging needed for this milestone.

## Dependencies And Assumptions

- Milestone 4 Features A-E are complete and remain the recommendation contract baseline.
- The graph contains `Character`, `Skill`, `PassiveSkill`, `Sidekick`, `SidekickSkill`, `SidekickAura`, `Superboss`, `MechanicReference`, `Grasta`, `Ore`, and baseline `Equipment` data as documented in `docs/core/SCHEMA.md`.
- Existing curated weak superboss crawl scope includes: Zennon Ogre's Shadow, Flame Eater, Flame Eater female variant, Nameless Girl, Mimi, Cradle System, and Insula Ventorum.
- Development can continue with free/local providers, including `nvidia/nemotron-3-super-120b-a12b:free` through OpenRouter or local Ollama models.
- Staging, evaluation, and release testing should use `moonshotai/kimi-k2.6` as the intended paid OpenRouter production model unless evaluation evidence shows another paid model is materially better within budget.
- The RM50/month starter ceiling is a public demo or Discord beta budget, not a commitment to always-on production spend.
- Budget increases should require evidence from usage reports, beta feedback, and portfolio value.
- Secrets, real API keys, and user credentials must stay out of docs and repository files.

## Research References And Source Grounding

Detailed source notes live in `docs/core/planning-sources.md`.

Repository-grounded planning inputs:

- `docs/core/roadmap.md` defines Milestone 5 as evaluation, optimization, graph cleanup, equipment policy, and live-site cost control.
- `docs/core/milestone.md` Milestone 4 closeout deferred Feature F evaluation gates and seeded sidekick cleanup, equipment policy, authentication, persistence, and rate limiting.
- `docs/core/architecture.md` identifies the ETL, workflow, LLM provider, validation, and web boundaries.
- `docs/core/SCHEMA.md` documents the current graph contract and confirms Equipment nodes are baseline context, not optimizer relationships.
- `src/workflow/llm.py` already centralizes provider/model selection.
- `src/workflow/legality.py` and `src/workflow/nodes/format.py` already enforce core lineup legality and final recommendation validation.
- `src/etl/scraper.py` defines the existing curated weak superboss scope.

External/current planning inputs:

- OpenRouter public model metadata inspected on 2026-06-25 confirms `moonshotai/kimi-k2.6` availability, structured-output support, tool support, 262144-token context, and public pricing at the time of inspection.
- OpenRouter pricing and model availability are current external facts and must be rechecked before release decisions or budget estimates are finalized.

Open research gaps:

- Actual average prompt and completion token usage for one recommendation run after Milestone 5 context compression.
- Actual paid-model quality comparison for free/local model output versus `moonshotai/kimi-k2.6`.
- Whether Kimi K2.6 remains the best paid default after staging evals, or whether another paid OpenRouter model gives better quality per RM.
- Exact Discord beta traffic pattern: number of users, expected recommendations per user per day, and whether testers need saved roster profiles.

## Guardrail Ownership Policy

Backend deterministic checks own fixed constraints. These checks should run before paid AI judging and before user-visible output:

- Exactly four frontline heroes and two reserve heroes.
- No duplicate heroes.
- Sidekicks cannot occupy hero slots.
- Main and sub sidekick slots must be different.
- Heroes must be owned or explicitly free-to-play available.
- Sidekicks must be owned or explicitly assumption-available.
- Recommended skills and passives must exist on the selected character.
- Stellar Awakening-gated skills/passives must respect known roster state or be labeled as upgrade assumptions.
- Recommended skill counts must stay within the supported 3/4-skill display contract.
- Boss affinity output must match graph-backed boss facts.
- Recommendation text must not claim numeric win probability, win rate, clear chance, or deterministic victory.
- Weapon and armor recommendations must not assign the same specific weapon or armor to more than one character in the same lineup when the recommendation names specific equipment.
- Grasta recommendations may reuse common assumptions across characters unless a future inventory-aware mode is explicitly added.

AI dynamic checks own subjective or contextual judgment:

- Hero selection quality for the selected boss and owned roster.
- Burst, sustain, and hybrid archetype viability.
- Skill priority and role fit when multiple legal choices exist.
- Synergy across zones, buffs, debuffs, pain/poison setup, AF support, sustain, and sidekick auras.
- Whether build notes are useful, specific, and honestly caveated.
- Whether risks and uncertainty are clear enough for a real player.
- Whether recommendation quality improved or regressed between providers, prompts, or retrieval strategies.

## Prioritized Feature Checklist

Implementation order matters for this milestone. Work starts with graph/data correctness and deterministic backend rules before paid-model setup, because clean data and backend validation make later Kimi K2.6 staging tests cheaper and more meaningful.

### Feature A: Sidekick/Character Graph Cleanup

Status: Completed.

Goal: Remove sidekick records incorrectly represented as `Character` nodes without damaging legitimate character data.

Technical requirements:

- Add a dry-run cleanup query that finds exact name overlap between `Character.name` and `Sidekick.name`.
- Report all matched names before deletion.
- Verify each matched `Character` node has sidekick-like origin or lacks required character detail data where possible.
- Add a safe cleanup command or ETL migration path that removes only confirmed duplicate `Character` nodes.
- Preserve `Sidekick` nodes, `SidekickSkill`, `SidekickAura`, and official `UNLOCKS_SIDEKICK` relationships.
- Add post-cleanup schema or data assertions that sidekick names no longer appear as character nodes.
- Document the cleanup workflow if it becomes a repeated operator task.

Acceptance criteria:

- Dry run lists the expected overlapping sidekick/character names without modifying the graph.
- Cleanup removes confirmed duplicate `Character` nodes only.
- Legitimate character nodes and sidekick association relationships remain intact.
- Recommendation legality tests continue to reject sidekick-as-hero output.
- ETL replay does not reintroduce the duplicate records.

### Feature B: Weapon, Armor, And Grasta Recommendation Policy

Status: Planned.

Goal: Decide and enforce how build recommendations should mention per-character weapon, armor, and Grasta setup without pretending to know full player inventory.

Technical requirements:

- Keep Milestone 5 as assumption-based build advice, not full inventory optimization.
- Extend the recommendation output contract so each recommended character can carry exactly one weapon assumption, exactly one armor assumption, and exactly three Grasta assumptions.
- Treat weapon, armor, and Grasta suggestions as recommended build assumptions even when the player has not entered ownership for those items.
- Treat specific weapon and armor recommendations as per-lineup assumptions, not account-wide ownership facts.
- Enforce or test that one named weapon and one named armor are not assigned to multiple characters in the same lineup when the model names specific items.
- Permit the same named weapon or armor to appear in separate top-three recommendation lineups, because each lineup is an alternative plan.
- Allow Grasta recommendations to be reused many times under late-game-access assumptions, including repeated copies on the same character when the recommendation explicitly calls for them.
- Validate Grasta compatibility against the character weapon type or personality requirement where graph data supports that check; unsupported compatibility claims must be labeled as assumptions rather than treated as graph facts.
- Require damage-oriented build notes that depend on pain/poison multipliers to identify a lineup skill, passive, sidekick, or clearly labeled assumption that applies or enables pain/poison against the boss.
- Require rare, event-limited, or unusually specific build assumptions to be labeled.
- Keep `Equipment` nodes as retrieval context only; do not add equip relationships or optimizer rankings in this milestone.
- Identify what future inventory-aware mode would require, including user-owned equipment, Grasta, Ore, badge, and Light/Shadow data.

Acceptance criteria:

- Recommendation output clearly separates lineup legality from build assumptions.
- Each character recommendation can display one weapon, one armor, and three Grasta slots without relying on free-text parsing.
- Weapon/armor uniqueness per lineup is documented and covered by tests or a deterministic validator.
- Weapon/armor uniqueness checks are scoped to a single lineup and do not reject the same item appearing in another alternative lineup.
- Grasta reuse assumptions are documented, allowed by validation, and not treated as ownership proof.
- Grasta recommendations are checked against available graph compatibility data, or explicitly caveated when compatibility cannot be verified.
- Pain/poison-dependent damage recommendations identify the lineup source of pain/poison application or clearly label it as a build assumption.
- No output claims exact best-in-slot optimization.
- Any future inventory-aware optimizer remains deferred unless explicitly promoted in a later milestone.

### Feature C: Backend Guardrail Audit And AI Responsibility Split

Status: Planned.

Goal: Reduce prompt overload and conflicting instructions by moving fixed validation out of AI prompts wherever possible.

Technical requirements:

- Audit current recommendation prompts, Pydantic models, legality code, format validation, and tests.
- Classify each guardrail as deterministic backend, dynamic AI generation, dynamic AI judge, or documentation-only caveat.
- Add or tighten backend tests for fixed constraints that should not depend on the model.
- Keep AI prompts focused on dynamic recommendation reasoning rather than repeating every fixed rule in full.
- Preserve enough prompt guidance for the model to produce valid structured output, but make backend validation the source of truth.
- Document failure behavior when the AI proposes an illegal or unverifiable output.

Acceptance criteria:

- Fixed constraints listed in the Guardrail Ownership Policy have backend tests or an explicit implementation task.
- Recommendation prompts no longer carry unnecessary duplicated guardrail text once backend checks exist.
- Illegal or unverifiable model output fails gracefully before rendering.
- Eval reports identify whether a failure belongs to backend validation, AI generation, or AI judgment.

### Feature D: Golden Weak-Boss Evaluation Harness

Status: Planned.

Goal: Promote the deferred Milestone 4 Feature F into a repeatable eval workflow for legality, factuality, recommendation quality, latency, and cost.

Technical requirements:

- Define a golden evaluation set of five weak superboss cases selected from the existing curated weak superboss scope.
- Store eval fixtures with boss name, roster, optional owned sidekicks, optional Stellar Awakening state, query, expected hard constraints, and human-readable quality expectations.
- Run deterministic backend gates before any paid judge call.
- Separate hard failures from subjective quality feedback.
- Record provider, model ID, prompt token estimate or observed usage where available, completion token estimate or observed usage, latency, and run timestamp.
- Support free/local development evals and paid staging/release evals using the same fixture shape.
- Add a reusable guide if the eval workflow requires repeated commands, report interpretation, fixture updates, or artifact cleanup.

Acceptance criteria:

- A developer can run the golden weak-boss eval set without paid model calls by default.
- Paid eval mode is explicit and requires the intended paid model configuration.
- Deterministic legality and factuality failures stop before subjective judge scoring.
- Eval output identifies which provider generated each recommendation and which provider judged it, if any.
- Reports distinguish backend hard-gate failures, model-output format failures, and subjective recommendation-quality concerns.
- The five-boss eval set is documented and can be extended later to intermediate and strong tiers.

### Feature E: Provider Strategy, Cost Reporting, And RM50 Budget Gate

Status: Planned.

Goal: Make OpenRouter the primary/default production AI path while keeping paid usage bounded and explainable.

Technical requirements:

- Keep free/local development as the default low-friction workflow.
- Configure `moonshotai/kimi-k2.6` as the intended paid staging/evaluation/release model through environment-driven settings.
- Preserve role-based provider/model overrides for future generator, validator, and judge experiments.
- Add per-run provider/model metadata to recommendation and eval artifacts.
- Add token and cost estimation using current configured model prices, with a clear caveat when usage is estimated rather than provider-reported.
- Define RM50/month as the starter public demo/beta ceiling.
- Add warning thresholds, recommended at 50%, 80%, and 95% of the RM50 ceiling.
- Add a hard stop or admin-disable mechanism when the monthly ceiling is reached.
- Include scenario estimates for controlled beta usage, such as 20-30 testers with bounded requests per tester.

Acceptance criteria:

- The system can run with free/local models during development and Kimi K2.6 during staging/release without code changes.
- Eval reports include provider/model, latency, estimated or observed tokens, and estimated RM cost.
- Documentation explains when paid model usage is allowed: staging, evaluation, release testing, and controlled beta/demo traffic.
- Documentation explains when paid judge usage is not allowed: normal live requests by default.
- The RM50 monthly ceiling is visible in planning docs and operator guidance.
- The app or planned deployment flow has a clear way to stop recommendation calls before the ceiling is exceeded.

### Feature F: Authentication, Persistence, Rate Limiting, And Beta Safety Plan

Status: Planned.

Goal: Prepare live-site cost protection and useful beta feedback capture before deployment work.

Technical requirements:

- Decide the minimum authentication model for controlled beta, such as invite-only login, magic links, Discord OAuth, or admin-issued access codes.
- Decide what user data should persist: roster, owned sidekicks, Stellar Awakening state, recent recommendation history, feedback, and consent state.
- Add a rate-limit policy for anonymous, authenticated, and admin users.
- Add monthly and per-user budget protections around paid recommendation calls.
- Plan request deduplication or caching for repeated identical roster/boss/query inputs where practical.
- Add feedback capture fields suitable for portfolio case studies, such as usefulness rating, issue category, free-text feedback, and permission to quote anonymized feedback.
- Keep deployment implementation in Milestone 7 unless a minimal local/staging persistence feature is required for beta preparation.

Acceptance criteria:

- Public beta cannot run as an unlimited unauthenticated paid endpoint.
- The RM50 monthly ceiling has a concrete enforcement plan.
- User data persistence scope is documented before schema or database work begins.
- Rate limits include per-user and global budget controls.
- Feedback capture supports portfolio case-study evidence without collecting unnecessary personal data.
- Deployment secrets and credentials remain out of repository docs and source files.

### Feature G: Context Compression, Prompt Cleanup, And Release Comparison Report

Status: Planned.

Goal: Improve recommendation latency, cost, and stability while producing evidence for portfolio case studies.

Technical requirements:

- Measure baseline latency, prompt size, completion size, and estimated cost for the golden weak-boss eval set.
- Review retrieved graph context for redundant boss, skill, passive, mechanics, Grasta, Ore, and Equipment text.
- Compress or prioritize context before paid model calls.
- Compare free/local development model output against Kimi K2.6 staging/release output.
- Add an evaluation summary report suitable for README, portfolio screenshots, or interview discussion.
- Preserve source citations and uncertainty labels after compression.

Acceptance criteria:

- Baseline and current reports show latency and cost movement across at least one optimization pass.
- Kimi K2.6 release eval results are captured separately from free/local development results.
- Context compression does not remove required legality, boss-affinity, mechanics, or citation evidence.
- The final report explains quality/cost tradeoffs in portfolio-friendly language without hiding failures.

## Planned Guide Updates

- Add or update `docs/guides/` evaluation guidance if the golden weak-boss eval workflow requires repeated commands, fixtures, paid-mode toggles, report interpretation, or cleanup steps.
- Add or update operator guidance for paid-model configuration, RM50 budget thresholds, and public beta safety if those steps become repeated procedures.
- Update ETL guidance if sidekick/character cleanup becomes a replayable ETL or Neo4j maintenance workflow.

## Current Completion Status

- Milestone 5: active planning complete, implementation not started.
- Feature A, Sidekick/Character Graph Cleanup: planned.
- Feature B, Weapon, Armor, And Grasta Recommendation Policy: planned.
- Feature C, Backend Guardrail Audit And AI Responsibility Split: planned.
- Feature D, Golden Weak-Boss Evaluation Harness: planned.
- Feature E, Provider Strategy, Cost Reporting, And RM50 Budget Gate: planned.
- Feature F, Authentication, Persistence, Rate Limiting, And Beta Safety Plan: planned.
- Feature G, Context Compression, Prompt Cleanup, And Release Comparison Report: planned.

## Open Questions

- Which exact five bosses from the existing curated weak superboss scope should become the golden eval set?
- Which authentication approach best fits the controlled Discord beta: Discord OAuth, magic link, admin-issued access code, or another lightweight option?
- What per-user request limit should the beta start with under the RM50/month ceiling?
- Should beta feedback be stored in the app database, exported manually, or captured through a separate form for the first test round?
