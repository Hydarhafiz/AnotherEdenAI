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
- The Another Eden Wiki Grasta overview and Attack Grasta list ground personality matching, Dormant sharing, Tier 3 uniqueness defaults, repeatable exceptions, and Pain/Poison conditions.
- Community Reddit, GameFAQs, and Steam discussions inform the temporary role-based build heuristic only; they are not hard legality sources and require later gamer-beta validation.

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
- Grasta compatibility and exact-variant acquisition cardinality are deterministic backend constraints; only variants marked repeatable may reuse copies beyond their recorded limit.

AI dynamic checks own subjective or contextual judgment:

- Hero selection quality for the selected boss and owned roster.
- Burst, sustain, and hybrid archetype viability.
- Skill priority and role fit when multiple legal choices exist.
- Synergy across zones, buffs, debuffs, pain/poison setup, AF support, sustain, and sidekick auras.
- Role-aware ranking that prefers Pain/Poison on active damage dealers and distinct Dormant-shareable Grasta on reserve mules while allowing explained exceptions.
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

### Feature B: Build Item Identity, Cardinality, And Recommendation Policy

Status: Reopened; implementation incomplete after failed manual verification.

Goal: Correct the graph and recommendation data contract so weapon, armor, and Grasta assumptions use distinct, compatible, cardinality-aware records without requiring player inventory entry.

Why this feature was reopened:

- Manual Feature B verification exposed that multiple Almighty Power and Enhance if Max HP variants are collapsed into one Neo4j node because the current loader merges Grasta by name alone.
- The collapsed node can accumulate unrelated personality requirements, causing valid and invalid compatibility decisions to become indistinguishable.
- Akane Alter is present in parsed artifacts as Akane (Alter),Blooming Blade, but analyzer output shortened the canonical name and failed final legality.
- Feature C cannot build trustworthy constrained candidates until these data identities are corrected.

Technical requirements:

- Preserve the existing recommendation shape of exactly one weapon assumption, one armor assumption, and three Grasta assumptions per character.
- Keep build items assumption-based even when the player has not entered item ownership; this is not a full inventory optimizer.
- Introduce a stable grasta_id that distinguishes variants by the fields required for legality, including category, tier, base name, personality requirement, weapon requirement or weapon group, and any source variant needed to prevent collisions.
- Extend parsed Grasta data with source-grounded compatibility, sharing, acquisition, and display fields needed by recommendation logic, including personality/weapon discriminator, source_url, obtain/source text where available, finite-versus-repeatable acquisition classification, and maximum theoretical copies when known.
- Distinguish regular Attack Grasta such as Almighty Power (Dragon) from Personality Special Grasta and other special-slot records.
- Replace name-only Grasta MERGE identity and uniqueness constraints, increment SCHEMA_VERSION, update schema assertions, and require parsed/live ETL replay or a safe migration that removes collapsed legacy nodes.
- Preserve separate REQUIRES_TRAIT relationships per exact Grasta variant so one variant never accumulates unrelated personality requirements.
- Enforce theoretical account cardinality per lineup even without inventory input: a unique exact Tier 3 variant may appear at most once in one lineup, while variants explicitly marked repeatable may reuse copies according to their metadata.
- Reset account-cardinality allocation between alternative lineups because each recommendation is an independent plan.
- Allow one character to equip multiple distinct personality Grasta when the character matches every required trait and each exact variant remains within its copy limit.
- Preserve weapon-compatible repeatable Pain/Poison Grasta choices and require a skill, passive, sidekick, or explicit supported assumption that applies the corresponding status.
- Keep specific weapon and armor uniqueness scoped to one lineup; treat weapon/armor category labels as repeatable generic assumptions.
- Introduce stable canonical character candidate identity and display aliases so analyzer output cannot shorten Akane (Alter),Blooming Blade into an unknown character.
- Add a character coverage/readiness audit that compares parsed character targets, Neo4j Character nodes, and frontend-selectable roster entries; missing or stale identities must fail visibly.
- Preserve Equipment as retrieval context only and keep exact best-in-slot ranking, badges, Ores, Light/Shadow slot expansion, and full inventory ownership outside this feature.
- Update docs/guides/ETL_GUIDE.md during implementation because the schema change requires repeatable migration/replay and verification steps.

Acceptance criteria:

- Distinct Almighty Power personality variants and Enhance-if-Max-HP variants load as distinct graph records with stable IDs.
- No Grasta node has personality requirements belonging to another variant.
- The graph records whether an exact variant is unique, finite, repeatable, or unknown; legality uses that metadata instead of assuming all Grasta are infinitely reusable.
- The same unique exact Grasta cannot be assigned twice inside one lineup but may appear in separate alternative lineups.
- Distinct compatible personality variants may coexist on one matching character.
- Repeatable weapon-compatible Pain/Poison Grasta may fill multiple slots when the lineup has a supported status source.
- Akane (Alter),Blooming Blade and other alias/style characters round-trip from parsed data through Neo4j, frontend selection, candidate generation, and final display without canonical-name drift.
- Readiness checks identify any parsed or frontend-selectable character missing from Neo4j.
- Schema assertions and focused ETL tests fail against the old name-collapsing behavior.
- Feature B automated tests pass, then its manual verification remains pending until expanded Feature C can produce a valid end-to-end recommendation.

### Feature C: Candidate-Constrained Generation, Guardrail Ownership, And Correction Loop

Status: Expanded and planned; blocked on Feature B data-contract correction.

Goal: Replace free-text hard-field generation with backend-provided candidates, validate each lineup independently, and correct only invalid lineups under a bounded cost policy.

Technical requirements:

- Audit prompts, state, Pydantic models, graph retrieval, legality code, formatter behavior, UI error handling, and tests; classify every rule as deterministic backend, dynamic AI judgment, or documentation-only caveat.
- Add a deterministic candidate-preparation boundary after successful graph retrieval and before analysis.
- Build compact candidate bundles with stable IDs and display metadata for canonical characters, character-owned skills/passives, owned sidekicks, compatible Grasta variants, equipment assumptions, graph-backed citations, and boss affinity/mechanics facts.
- Preserve candidate coverage for the eligible roster; remove the arbitrary first-12-record behavior as a legality source and report when context selection omits an eligible candidate.
- Require the analyzer to select backend-provided IDs for all hard fields. The analyzer may author roles, strategy, tradeoffs, risks, and explanations, but may not invent character, skill, passive, sidekick, item, citation, or boss-fact identifiers.
- Resolve IDs to display names only after deterministic validation.
- Validate burst, sustain, and hybrid lineups independently for shape, ownership, canonical identity, skill/passive existence, Stellar Awakening gates, sidekick legality, equipment uniqueness, Grasta compatibility/cardinality, Pain/Poison source, citations, and boss-affinity fidelity.
- Freeze valid lineups between correction rounds.
- Return invalid lineup diagnostics as structured error codes and paths plus the exact allowed replacement candidate IDs; do not rely on prose-only retry feedback.
- Correct all remaining invalid lineups together in at most two conditional batched rounds after initial analysis, for no more than three analyzer calls per request.
- Skip correction calls when initial output is fully valid.
- Discard lineups that remain invalid after the correction cap. Never render an incompatible character, skill, item, or Grasta as part of a valid lineup.
- Return one to three fully valid lineups as a partial result set with warnings that identify missing archetypes and rejected/corrected proposals; return graceful failure only when zero valid lineups remain.
- Distinguish Cypher retrieval retries, provider transport retries, analyzer correction rounds, structured-output normalization, and final legality failures in state, logs, SSE progress, UI messages, and future eval reports.
- Use the current beta build heuristic as a ranking preference: favor Pain/Poison Grasta on active damage dealers when a reliable setter exists and favor distinct Dormant-shareable Grasta on reserve mules.
- Keep that build heuristic non-mandatory; allow support, tank, AF, farming, or boss-specific exceptions when the recommendation explains the tradeoff.
- Keep exact damage simulation, exact best-in-slot claims, and automatic substitution outside the approved candidate set out of scope.
- Add docs/guides/recommendation-validation.md with local setup, ETL/schema readiness checks, candidate inspection, Mimi smoke tests, correction-round diagnostics, partial-result expectations, failure classification, and what manual testers should report.
- Require later Features D, E, and G to update the guide when eval commands, provider/cost reporting, or context compression changes validation behavior.

Acceptance criteria:

- Analyzer output cannot reference a hard-field ID absent from the backend candidate bundle.
- Canonical alias/style identities such as Akane Alter cannot fail because the model shortened their display name.
- Incompatible personality/weapon Grasta and exhausted unique-copy variants are excluded from allowed replacements.
- A correction request receives structured validation errors and allowed candidates, not merely the original prompt.
- A fully valid first response performs no correction call.
- A request performs at most two correction rounds and at most three analyzer calls total.
- Valid lineups survive correction of other lineups unchanged.
- Invalid lineups remaining after the cap are absent from rendered recommendations and represented only by warnings.
- One or two valid lineups render successfully with explicit missing-archetype warnings; zero valid lineups render a graceful classified error.
- Cypher retry counters and analyzer correction counters are separate and visibly distinguishable.
- The default frontline Pain/Poison and reserve-mule preference is tested as ranking guidance, while hard compatibility/cardinality remains deterministic.
- Existing fixed guardrails remain backend-owned and have modular tests.
- The exact Mimi prompt used during Feature B verification returns at least one fully valid owned-roster lineup without incompatible Grasta, hallucinated characters, unsupported skills/passives, missing citations, or boss-affinity drift.
- docs/guides/recommendation-validation.md is sufficient for another developer or tester to repeat schema readiness, automated checks, and manual smoke verification.

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
- Update ETL guidance for the reopened Grasta identity/cardinality schema migration and character coverage checks.
- Add and maintain docs/guides/recommendation-validation.md for candidate inspection, correction-loop diagnostics, Mimi smoke testing, partial-result verification, and failure classification.

## Current Completion Status

- Milestone 5: active; Feature A is complete, Feature B is reopened, and later features remain pending.
- Feature A, Sidekick/Character Graph Cleanup: completed.
- Feature B, Build Item Identity, Cardinality, And Recommendation Policy: reopened; implementation incomplete after failed manual verification.
- Feature C, Candidate-Constrained Generation, Guardrail Ownership, And Correction Loop: expanded and planned; blocked on Feature B.
- Feature D, Golden Weak-Boss Evaluation Harness: planned.
- Feature E, Provider Strategy, Cost Reporting, And RM50 Budget Gate: planned.
- Feature F, Authentication, Persistence, Rate Limiting, And Beta Safety Plan: planned.
- Feature G, Context Compression, Prompt Cleanup, And Release Comparison Report: planned.

## Open Questions

- Which exact five bosses from the existing curated weak superboss scope should become the golden eval set?
- Which authentication approach best fits the controlled Discord beta: Discord OAuth, magic link, admin-issued access code, or another lightweight option?
- What per-user request limit should the beta start with under the RM50/month ceiling?
- Should beta feedback be stored in the app database, exported manually, or captured through a separate form for the first test round?
