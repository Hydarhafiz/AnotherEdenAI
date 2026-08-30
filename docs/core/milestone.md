# AnotherEdenAI Milestone 5 Plan

## Executive Summary

Status: Active; Features A, B, C1-C5, D, E, F, G, and G1 are complete. Feature H began offline verification but is blocked at H-03 by a cross-feature data, package, search, allocation, and oracle conflict. The human-approved Milestone 5 correction sequence C6 -> D2 -> E2 -> F2 must complete before H resumes. No paid call is authorized by this plan.

Milestone 5 replaces broad-context LLM lineup search with a distributed backend-plus-LLM recommendation pipeline. Before contextual role scoring begins, a reopened Feature C must replace broad keyword-authored role tags with reviewed atomic capabilities and dependencies. The backend is the scout, filter, role scorer, skill/build packager, candidate generator, and referee. The analyzer LLM is a bounded strategist, tie-breaker, refiner, and communicator over five to ten compact legal candidates when that many exist.

The production recommender will use deterministic typed Neo4j retrieval rather than PLAN, generated Cypher, or LLM semantic retrieval validation. It will hard-reject impossible choices, compute contextual role and skill scores, generate capability-coverage lineups through bounded search, and validate all analyzer refinements. Normal paid usage is one analyzer call; the worst case is one initial call plus one fragment-only correction. A legal backend fallback prevents analyzer format, budget, or refinement failures from destroying otherwise valid recommendations.

This rewrite preserves verified prior work but does not credit the current broad candidate-bundle prototype as completed architecture. Candidate/team scoring and legality are implemented and proven before paid analyzer-quality work.

## Scope And Intended User Outcome

A late-game or near-endgame Another Eden player should be able to submit:

- An owned roster.
- Optional owned sidekicks.
- Optional per-character Stellar Awakening state.
- Optional per-character Light/Shadow points; omission conservatively permits only three equipped active skills, while a declared value of at least 80 permits four.
- A canonical selected boss.
- Optional natural-language strategy preferences.
- The default `late_game_assumed` item policy.

The user should receive one to three legal, boss-aware lineup recommendations when viable, preferably representing burst, sustain, and hybrid strategies without fabricating missing archetypes. Each result should include selected heroes, contextual roles, three or four recommended skills, an assumption-labeled build package, optional legal sidekicks, boss counterplay, setup dependencies, risks, uncertainty, tradeoffs, and citations.

Sparse data should produce diagnostics, reduced confidence, fewer candidates, or a typed zero-candidate result. It must never produce silent roster drops, fabricated ownership, invented mechanics, illegal skills/items, or padded lineups.

The owner should be able to inspect why candidates were rejected, how survivors scored, which policy versions were used, what the analyzer saw, which refinements were accepted or rejected, and how many tokens and how much provider-reported cost each call consumed.

## Architecture Boundary

### Production Recommender

The production path is:

1. Normalize canonical request IDs and report unresolved/ambiguous inputs.
2. Retrieve typed roster, boss, mechanics, sidekick, skill/passive, Grasta, and equipment facts.
3. Apply hard legality and matchup rejection.
4. Separate legal executable skill facts from reviewed capability proof, then compute contextual role and per-role skill scores only from proven capabilities.
5. Generate up to three distinct non-dominated, boss-aware legal skill packages per complete character.
6. Build role-specific top-K pools with boss-counter exceptions and deterministic alternative build choices.
7. Generate burst, sustain, and hybrid candidates from capability templates using bounded `(character, selected_package)` beam search.
8. Resolve finite item allocation across each six-hero lineup, then validate, score, deduplicate, and diversity-filter legal candidates.
9. Project only referenced facts for up to ten candidates to the analyzer.
10. Accept ranking, skill choices, explanations, and at most one backend-bounded hero swap per lineup.
11. Re-score and revalidate all refinements.
12. Run at most one fragment-only correction when required.
13. Return valid refined results or legal backend candidates in clearly labeled degraded mode.

### Exploratory GraphRAG

The existing PLAN -> GENERATE_CYPHER -> VALIDATE -> ANALYZE -> FORMAT flow may remain for exploratory graph questions. It is not responsible for production lineup legality and is never a fallback for missing production boss or roster data.

Natural-language query text may adjust soft preferences or explanations, but it cannot expand the legal candidate universe or control legality-critical retrieval.

## Explicit Non-Goals

- No exact deterministic damage simulator.
- No full turn-by-turn battle simulator.
- No numeric win probability, clear rate, or guaranteed victory.
- No full player inventory optimizer.
- No exact best-in-slot optimizer.
- No required weapon, armor, Grasta, Ore, badge, or sidekick-equipment inventory entry for MVP.
- No required `declared_owned_only` item mode in the first implementation.
- No unbounded all-superboss ingestion or evaluation expansion; the post-Feature-G checkpoint admits only the bounded Feature G1 stages and their per-boss readiness gates.
- No more than thirty recommendation-ready superbosses in Milestone 5: ten weak at wiki difficulty 1.0-4.0, ten medium at 4.5-8.8, and ten strong at 9.0-12.0.
- No live AI role tagging during requests or normal ETL.
- No mandatory AI-assisted labeling in initial acceptance.
- No exhaustive proof or strategic classification of every skill in the 367-character MVP corpus; only high-value capabilities needed for contextual roles, mandatory coverage, and acceptance witnesses require review now.
- No boss HP-stopper, phase, or turn-script simulation in the correction sequence.
- No free-form analyzer lineup assembly.
- No more than one analyzer-proposed hero swap per lineup.
- No AI judge in live or offline evaluation; deterministic gates own Milestone 5 acceptance, while a controlled Discord demo and player-feedback program are deferred until after the portfolio preview is stable.
- No rerun of the historical ~601k-token failure merely to recreate its baseline.
- No major frontend redesign beyond status, diagnostics, assumptions, degradation, and cost visibility required by this milestone.
- No deployment implementation beyond the portfolio-preview safety decisions explicitly retained after the core recommendation gates.

## Dependencies And Assumptions

- Milestone 4 recommendation shape, final legality concepts, curated weak bosses, MechanicReference corpus, and current UI remain the baseline.
- Sidekick/Character overlap cleanup is complete and must remain replay-safe.
- Grasta exact-variant identity, compatibility, acquisition class, and maximum-copy metadata must pass verification before build-package scoring is trusted.
- Canonical Character IDs and aliases must round-trip through request, graph, candidate, analyzer, validation, and display boundaries.
- Skills, passives, sidekick skills, and sidekick auras require stable backend candidate IDs. Sidekick IDs must include owner plus skill kind/name or aura name and remain reproducible across replay.
- Every one of the 367 canonical character forms/styles in the approved MVP corpus requires a successful, non-ambiguous kit-materialization receipt before H acceptance. A verified absence of passive or SA data is an explicit state, not an empty relationship interpreted as success.
- Legal active-skill availability and reviewed capability evidence are independent contracts. Untagged legal skills may occupy a package slot but never grant score or mandatory-coverage credit.
- Schema changes require a version bump, ETL replay/migration, schema assertions, and planned ETL-guide updates.
- The default target player has broad late-game item access; item ownership is not verified unless a future policy says otherwise.
- Curated boss and mechanics data may be incomplete. Unknown data lowers confidence and must remain distinct from confirmed facts.
- OpenRouter model, provider-routing, usage, price, structured-output, and limit metadata are mutable external facts and must be captured at paid release-evaluation time. Direct DeepSeek remains an offline adapter compatibility path and is deferred from Milestone 5 paid qualification.
- The historical ~601k-token failed run is a user-observed baseline for reduction reporting.
- The live portfolio-preview contract permits paid analysis only for email-verified registered users, at ten logical paid requests per calendar month, under atomic reservation, per-IP burst/concurrency controls, a global kill switch, and an RM50 global monthly hard ceiling. Deployment implementation remains separately sequenced and no paid call is authorized here.
- Secrets, credentials, API keys, and real user authentication data remain outside documentation and repository files.

## Research References And Source Grounding

Detailed entries live in `docs/core/planning-sources.md`.

Repository-grounded inputs include:

- `src/workflow/candidates.py` currently retrieves the full eligible roster, every owned character's skills/passives, and all Grasta before prompt projection.
- `src/workflow/nodes/analyze.py` currently permits a 450,000-byte analyzer payload and up to two correction rounds after the initial call.
- `src/workflow/nodes/cypher.py` and `src/workflow/nodes/validate.py` show the current generated-Cypher recommendation path and separate retry cost.
- `src/workflow/legality.py` contains reusable ownership, sidekick, skill/passive, SA, equipment, Grasta, and setup legality concepts.
- Existing candidate, correction, partial-output, matchup, legality, and eval tests provide regression starting points but do not prove the rewritten architecture.

External/current inputs include:

- OpenRouter Usage Accounting documents automatic per-response usage and cost fields, including reasoning and cache details where available.
- OpenRouter Structured Outputs documents strict JSON Schema output for compatible models; schema enforcement does not replace semantic legality validation.
- OpenRouter Models documentation provides model capability, pricing, context, completion, and supported-parameter metadata that must be snapshotted for paid qualification.
- OpenRouter model fallback documentation permits one ordered `models` array and reports the model that ultimately answers. The post-G revision targets `deepseek/deepseek-v4-flash-0731`, then `openai/gpt-5.6-luna`, then `z-ai/glm-5.2`; all three currently advertise structured outputs, but release-time fixtures and metadata—not leaderboard position—govern qualification.
- Existing Another Eden wiki and mechanics references ground affinity, status, zone, SA, sidekick, and Grasta constraints.
- Feature C3 references now ground Status Effects, Damage Formula, Focus effects, reversal, Kaleido, barrier pierce, Link/Copy/Chain/counting behavior, Magic Overcritical, Lunatic variants, and the Oh No Help compound amplification case; detailed entries and retrieval caveats live in `docs/core/planning-sources.md`.
- Community build references remain heuristic evidence only and require fixture or beta validation before tuning weights.

Open research gaps:

- Actual compact-projection token and cost distributions.
- Initial scoring-weight quality across the curated weak-boss fixtures.
- Experienced-player validation for high-impact role overrides and counter exceptions.
- Release-time metadata, fallback behavior, and paid quality evidence for the admitted OpenRouter model chain.
- Per-boss readiness and independent golden-fixture quality across Feature G1's ten weak, ten medium, and ten strong cohorts.
- Value of optional provider-assisted low-confidence tag suggestions.
- Authentication, persistence, and per-user/global limits for beta.
- Exact dedicated-page wording for several C3 mechanics that the planning browser could not retrieve; cached source facts and the accessible Status Effects/Damage Formula pages ground the current taxonomy, while unresolved formula or interaction details remain non-authoritative.
- The initial conservative Feature D policy for using reviewed stacking evidence; C3 captures it but does not require maximum-stack scoring.

No unsupported external performance or pricing claim is used as a fixed acceptance criterion. Token ceilings are project policy; observed provider usage measures compliance.

## Locked Ownership Policy

### Backend Deterministic Authority

The backend owns:

- Canonical identity and normalization diagnostics.
- Owned/F2P and sidekick eligibility.
- Stellar Awakening availability and assumption labeling.
- Typed boss, roster, mechanics, skill/passive, sidekick, and build retrieval.
- Hard rejection before scoring.
- Atomic capability/dependency taxonomy application, review status, and evidence materialization.
- Contextual role and skill scoring.
- Role-specific top-K pools and must-include counter exceptions.
- Skill and build package construction.
- Template and bounded beam candidate generation.
- Full-lineup scoring, deduplication, and diversity.
- Sidekick main/sub legality.
- Grasta compatibility, exact identity, and copy cardinality.
- Specific equipment allocation when named.
- Final validation, re-scoring, fallback, and partial-result classification.
- Preflight token budgets and observed usage accounting.

### Role Taxonomy Ownership

The word `role` refers to three different contracts and must not collapse them into one field:

| Contract | Examples | Authority | Persistence |
| --- | --- | --- | --- |
| Atomic combat facts | `direct_damage`, `heal_hp`, `guard`, `deploy_zone`, `af_combo_gain_up`, `requires_zone` | Reviewed taxonomy plus deterministic ETL materialization | Canonical review/taxonomy artifacts and reproducible graph fields |
| Contextual role dimensions | primary damage, offensive enablement, zone/setup, defense/mitigation, recovery/protection, tank/control, AF support, MP sustain, boss counter, reserve utility | Feature D backend policy computed from proven facts, boss, SA state, placement, and selected package | Versioned scoring policy and per-request score/evidence output; never permanent Character labels |
| Strategic interpretation | candidate ordering, execution complexity, strategic coherence, matchup nuance, tradeoff wording, and a concise display-role phrase grounded in backend role IDs | Analyzer advice over supplied legal candidates | Request result and evaluation evidence only; never capability or coverage authority |

`DPS`, `healer`, `tank`, `support`, `zone setter`, `cleanser`, and similar player-facing labels are deterministic groupings over the contextual dimensions when used for filtering, scoring, or coverage. Their scores change with boss and package context, but the AI does not verify or certify them. Burst, sustain, and hybrid are likewise backend candidate-template IDs, not analyzer-invented archetypes.

The analyzer may describe a hero as, for example, “Fire primary damage with AF support,” only when the projection supplies those backend role IDs and evidence. Soft judgments that the backend cannot prove—such as execution difficulty or strategic elegance—must remain explicitly advisory and cannot create mandatory coverage, rescue an illegal candidate, or change a score.

The current broad candidate prototype still accepts analyzer-authored free-text `role` values. Feature D introduces the fixed contextual role-score contract, and Feature G must retire free-text role authority from the production path while preserving any legacy shape only for exploratory compatibility.

### Analyzer Dynamic Authority

The analyzer may:

- Rank supplied backend candidates.
- Choose exactly three or four skill IDs from supplied shortlists.
- Explain strategy, counterplay, risks, assumptions, uncertainty, and tradeoffs.
- Propose at most one hero swap per lineup from `allowed_swaps`.
- Explain the required-role reason for a proposed swap.

The analyzer may not invent or introduce any character, skill, passive, build package, Grasta, equipment, sidekick, boss fact, mechanic, or citation ID. It may not freely assemble a lineup from the owned roster.

Every proposed swap and skill change is re-scored. An invalid or lower-scoring swap falls back to the original candidate. An invalid or lower-scoring skill package falls back to the backend default.

## Capability Taxonomy, Review, And Role-Derivation Policy

A versioned local capability artifact replaces broad ETL-level role assignment. It is the source of truth for:

- Atomic capability and dependency vocabularies.
- Direction and explicit target scopes, including self, one ally, adjacent allies, self plus adjacent allies, frontline, main plus reserve, enemy, field, and zone semantics.
- Deterministic positive rules and explicit negative/rejected patterns.
- Evidence fields, constrained effect subtypes, optional reviewed magnitude/timing/scaling/stacking qualifiers, sidekick placement availability, curated overrides, review status, and artifact version.

Defensive/setup facts distinguish `damage_reduction`, `damage_reduction_barrier`, `shield`, `heal_hp`, `regen_hp`, `remove_status_ailment`, `remove_debuff`, `grant_status_immunity`, `knockback_immunity`, `hold_ground`, `taunt`, `cover`, `guard`, `dodge`, `stalk`, and direction-aware/target-aware `revive`. Barrier and Shield each emit one distinct fact; neither also emits generic damage reduction. Compound sources may emit multiple facts only when each is independently proven. Zone, resistance, MP recovery, offensive/support, and dependency facts remain separate atomic concepts.

ETL or parsed-artifact replay materializes only reviewed `proven` capabilities as active Skill, PassiveSkill, SidekickSkill, and SidekickAura graph facts. Sidekick skill facts are `main_only`; aura facts are `main_or_sub`, with activation conditions retained. `candidate` matches remain review diagnostics and cannot satisfy mandatory coverage. `rejected` matches are preserved as negative regression fixtures so later taxonomy changes cannot reintroduce known false positives. Untagged facts are valid and reported.

Every proven capability cites the matched source phrase, direction/target semantics, rule or override, stable source fact ID, review provenance, and artifact version. When source text explicitly provides them, reviewed evidence may include `magnitude_value`, constrained `magnitude_unit`, `activation_count`, `duration_turns`, constrained `trigger`, bounded effect qualifiers, capture-only scaling evidence, `stacking_behavior`, and `max_stacks`; absent values remain unknown, never zero or inferred. Capture-only qualifiers do not calculate accumulated magnitude, proc probability, damage, healing, AF behavior, turn order, or rotations. Neo4j is materialized output rather than the source of truth. Identical parsed data, review artifacts, and taxonomy versions must reproduce identical graph facts, and drift tests fail on differences.

Character and sidekick roles are not permanent ETL labels. Feature D deterministically derives contextual `RoleScores` and coverage from proven atomic facts, reviewed qualifiers, selected package, sidekick main/sub placement, SA state, boss matchup, build assumptions, and lineup coverage. The analyzer may explain or rank supplied candidates but may not independently certify mandatory coverage.

### Human Review Loop

The repository-native review workflow uses generated CSV batches for editing and canonical JSON for stable IDs, decisions, reviewer notes, gold fixtures, and regression history. No review UI is required.

Review proceeds in three ordered phases:

1. Mandatory defensive/setup capabilities: zone deployment, mitigation, healing, cleanse/status protection, tanking, MP sustain, and required setup.
2. Offensive/support capabilities: direct damage, atomic amplification and stat/critical/resistance effects, Pain/Poison/Break, named transformations and focus effects, AF effects, affinity conversion, attack bypass, Lunatic activation, Links, Copy/repeat/Chain/follow-up attacks, and independently reviewed qualifiers.
3. Dependencies and conditions: zone/status/stack/SA requirements, EOT effects, party-composition conditions, limited-use activation, and similar qualifiers.

Each phase generates deterministic stratified batches of exactly 45 new proposed decisions. Every row requires an explicit `approve`, `reject`, `correct`, or `ambiguous` decision before import; blank decisions fail validation. The generated reviewer template constrains decision, capability, dependency, direction, target, sidekick availability, qualifier units, and triggers, and includes source text, source URL, and concise field guidance. Explicit qualifier proposals must be approved or corrected; genuinely absent qualifiers remain unknown. Reviewers consult the linked wiki source only when captured evidence is unclear; they do not manually reconstruct the corpus or assign contextual roles.

The loop is generate batch -> pause at `Awaiting human review` -> edit CSV -> validate/import canonical JSON -> identify repeated failure patterns -> update rules/overrides -> rerun all accumulated fixtures -> generate the next batch. New targeted reproductions join the automatic regression set rather than inflating the next 45-row human batch. Rare or high-risk additions first receive explicit decisions in a targeted migration/seed-review artifact outside the 45-row batches, then become permanent automatic positive or negative regressions. A phase passes only after every accumulated fixture passes and two consecutive fully reviewed batches reveal no new critical false-positive pattern.

Artifact migrations preserve unaffected decisions through proposal IDs that are stable independently of taxonomy version; evidence still records the exact version used. Renamed, split, or semantically changed facts return through a targeted migration-review artifact outside the 45-new-proposal batches. Superseded generated batches remain audit artifacts and cannot be imported under the replacement vocabulary.

A critical false-positive pattern is a repeatable rule error that could falsely satisfy mandatory lineup coverage, reverse ally/enemy or grant/require semantics, omit a gating zone/SA/status/stack dependency, or misclassify damage, defense, sustain, or setup across multiple facts. Discovery resets the phase's clean-batch streak. Rejected fixtures and untagged facts are expected; ambiguous facts remain non-proven; zero rejected records and full-corpus tagging are not goals.

### Optional AI-Assisted Curation

A configured DeepSeek-direct or OpenRouter route may later support a developer/admin-only batch that reads parsed artifacts and emits suggestion files for untagged, low-confidence, or selected high-impact records. It never runs during live recommendations or normal ETL, never directly mutates Neo4j or canonical artifacts, and is safe to skip.

Suggestion records include evidence, confidence, provider, model, prompt version, timestamp, and source reference. Human review is mandatory. Accepted suggestions become ordinary versioned curated overrides, after which runtime materialization is deterministic without an AI provider.

This optional batch is not required for first implementation acceptance.

## Skill Selection Policy

### Stage 1: Per-Role Shortlisting

Before lineup generation, the backend scores each available skill per character against contextual role, boss matchup, affinity, mechanic tags, SA state, setup value, and MP/long-fight pressure.

Unavailable choices are excluded. SA-gated choices require known availability or an explicit upgrade-assumption branch. The normal shortlist contains four to six role-relevant skills per character, not the full skill list.

### Stage 2: Lineup-Aware Packages

During lineup scoring, the backend creates one or more default three-to-four-skill packages for each selected hero and assigned contextual role. Packages consider:

- Required setup dependencies.
- Capability coverage.
- Redundancy.
- MP pressure.
- Affinity.
- Pain/Poison/Break requirements.
- Zone/stance application.
- Sustain, mitigation, cleanse, taunt, or other mandatory functions.

A lineup receives no capability credit unless the selected/default package proves that capability. Analyzer-selected packages are validated by stable ID and fall back to the backend default when invalid, incomplete, or lower-scoring.

## Item And Build-Package Policy

The required MVP policy is `late_game_assumed`.

The backend may use compatible catalog Grasta, weapons, armor, and supported Ore/build-intent context as late-game assumptions. Specific ownership is not verified. Output clearly labels packages as assumed late-game builds and treats unavailable items as farming/build targets.

Each compact build package contains:

- One weapon or weapon-category assumption.
- One armor or armor-category assumption.
- Three Grasta choices.
- Optional Ore/build-intent notes when supported.
- Compatibility evidence.
- Copy/cardinality allocation.
- Setup dependencies.
- Assumption labels.
- Source/citation IDs.

The backend enforces exact Grasta identity, personality/weapon compatibility, unique/finite/repeatable cardinality, lineup-scoped allocation, named equipment duplication, and Pain/Poison/Break/zone dependencies. The analyzer sees only referenced build-package IDs and compact explanations.

`generic_only` remains a fallback design. `declared_owned_only` is future-compatible but not an MVP requirement.

## Affinity And No-Weakness Policy

The backend distinguishes:

- Confirmed weakness.
- Confirmed no weakness.
- Weakness unknown.
- Incomplete affinity data.

A confirmed no-weakness boss receives no missing-weakness penalty. Primary damage that is nullified or absorbed is rejected. Resisted primary damage is penalized unless a validated bypass, affinity change, or alternate neutral plan exists. Primary DPS requires at least one neutral-or-better usable damage skill.

When weakness is unavailable, scoring shifts toward a neutral damage engine: role coverage, mechanic counterplay, zone/damage-type synergy, buffs/debuffs, setup, AF support, sustain, mitigation, status protection, MP stability, sidekick value, reserve utility, setup reliability, uncertainty, and assumption burden.

Unknown or incomplete affinity lowers confidence but is not treated as confirmed no weakness. Scores remain internal ranking signals only.

## Capability-Coverage Templates

Templates express required and optional capabilities, not rigid one-role-per-hero slots. A hero satisfies multiple requirements only when selected skill/passive/build evidence proves them.

### Burst

Requires credible primary damage, damage enablement, complete required setup, and enough survival or mandatory counterplay for the boss. Healer/tank coverage is required only when boss mechanics demand it.

### Sustain

Requires credible primary damage, defensive or recovery stability, offensive enablement, and MP/long-fight stability when relevant. Sustain candidates must still have a clear progress/damage plan.

### Hybrid

Requires credible damage, setup, support/enablement, and defensive reliability. Hybrid is the balanced default when it carries fewer assumptions or lower risk.

Missing mandatory coverage rejects a lineup. Missing optional coverage lowers score, confidence, or rank. Reserve heroes score swap value, passive utility, and legal Grasta-mule contribution. Sidekick packages contribute only through legal main/sub behavior.

## Candidate Generation And Scoring

A versioned scoring-policy artifact owns initial weights, component definitions, penalties, diversity rules, and policy version.

The backend:

- Applies hard rejection before scoring.
- Retains the top eight candidates per role by default.
- Adds bounded must-include exceptions for rare boss counters or required enablers outside the top eight.
- Expands burst, sustain, and hybrid capability templates without random shuffle.
- Retains at most 50 partial combinations at each beam-search step.
- Scores complete six-hero lineups.
- Deduplicates equivalent rosters and near-identical strategies.
- Preserves strategic diversity.
- Sends only five to ten diverse legal candidates when available.

Must-include exceptions may cover mandatory cleanse/immunity, unique bypass, required zone, rare setup, boss-specific mitigation, affinity change, or other proven counterplay.

Full-lineup scoring includes:

- Capability/role coverage.
- Boss matchup.
- Setup completeness.
- Synergy.
- Sustain and mitigation.
- Skill-package readiness.
- Sidekick contribution.
- Reserve utility and Grasta-mule value.
- Item/build assumption burden.
- Role overlap.
- Missing setup.
- Uncertainty.

Each candidate retains scoring-policy version, component breakdown, major penalties, assumptions, validation status, and pruning-survival reason. Initial weights may be heuristic, but tuning requires golden fixtures, regression evidence, documented evaluation, or beta feedback.

## Candidate Contracts

### Full Backend Candidate Object

Internal only. It may contain full evidence, rejected candidates, detailed scores, validation metadata, intermediate signals, debugging data, and correction authority. It is never sent directly to the analyzer.

### Compact Analyzer Projection

Contains only:

- Schema, role-taxonomy, role-artifact, and scoring-policy versions.
- Assumption policy.
- Compact boss facts and referenced mechanic summaries/IDs.
- One to ten legal scored candidates, normally five to ten.
- Six assigned hero IDs per lineup.
- Role-score summaries and evidence for selected heroes.
- Four-to-six-skill shortlists and default packages only for selected heroes.
- Referenced build-package IDs.
- Selected sidekick package and limited legal alternatives.
- `allowed_swaps` grouped by slot and required capability.
- Component score breakdown.
- Setup dependencies.
- Uncertainty and risk flags.
- Deduplicated catalogs resolving referenced IDs only.
- Citation IDs.
- Immutable validation constraints.

It excludes rejected heroes, the full owned roster after pruning, broad skill/passive lists, full item catalogs, raw boss pages, and unlimited replacements.

## Analyzer Refinement And Correction

The analyzer may keep a candidate unchanged or propose at most one hero swap per lineup from supplied `allowed_swaps`. It explains the capability reason. The backend re-scores and revalidates the result. Invalid swaps or swaps scoring below the original are rejected, and the original candidate is restored.

Valid lineups are frozen. Correction targets only invalid fragments and never regenerates the entire answer.

Maximum analyzer calls per request:

- Normal: one initial analyzer call.
- Worst case: one initial call plus one batched fragment-only correction.
- No third analyzer call.

Invalid skill selections fall back to backend defaults where safe. Invalid refinements are discarded after correction. Return one to three valid results. If analyzer output entirely fails, budget is exhausted, or refinement is skipped, legal coverage-valid backend candidates may be returned in clearly labeled degraded mode.

## Token And Cost-Control Gates

### Initial Call

- Target input: at most 20,000 tokens.
- Hard input cap: 25,000 tokens.
- Completion hard cap: 4,000 tokens.

### Correction Call

- Target input: at most 6,000 tokens.
- Hard input cap: 8,000 tokens.
- Completion hard cap: 2,000 tokens.
- Never resend the full projection.
- Send only invalid fragments, error codes, relevant allowed IDs, fallback defaults, and immutable constraints.

### Cumulative Analyzer Budget

- Target total usage across all analyzer attempts: at most 30,000 tokens.
- Hard acceptance ceiling: 40,000 total analyzer tokens.
- Include provider-reported prompt, completion, reasoning, cached, total, and other available token categories.
- Estimate input before a paid request and skip calls that exceed the per-call budget.
- Budget exhaustion returns legal backend candidates in degraded mode.
- Paid golden acceptance requires at least 90% reduction from the observed ~601k-token failed run.

For each attempt record provider, model, prompt, completion, reasoning, cached, total tokens, provider-reported cost, and estimated cost when needed. Model pricing and currency conversion remain configurable and are snapshotted for release evaluation.

## Sparse Input And Failure Policy

- Unknown, misspelled, or ambiguous roster names produce diagnostics, suggestions, and eligible-count reporting; they are never silently dropped.
- Fewer than six eligible heroes after owned/F2P policy returns typed `insufficient_roster`.
- Missing skill/passive data removes unsupported capabilities but may leave other proven roles usable.
- No owned sidekicks keeps both slots empty and surfaces risk where relevant.
- One or two viable archetypes return as partial success with missing-archetype reasons.
- One to four backend candidates may reach the analyzer when no more legal diverse candidates exist.
- Zero candidates produce structured dominant rejection causes and no analyzer call.
- Incomplete boss/mechanics data lowers confidence and creates readiness warnings.
- Degraded mode returns only legal, coverage-valid backend candidates.

Dominant zero-candidate causes include insufficient heroes, no usable primary damage, null/absorb conflicts, missing mandatory defense/setup, missing source data, build incompatibility, Grasta cardinality conflicts, and boss-data unreadiness.

## Execution Workflow And Evidence Policy

Repository behavior and authoritative test/evidence paths outrank milestone status text; this document owns approved scope and ordering; ignored `.sdd/` handoffs are reconstructable execution cache only.

Each planned feature below records a compact route from the current SDD routing matrix. Execution uses an ignored `.sdd/active/milestone-5/<feature>.json` handoff for exact paths, current role, known dirty files, temporary blockers, and command results. The handoff is never committed and never proves completion.

Implementation-bearing work follows `builder-executor -> tdd-loop`. Verification/evidence remediation may enter `tdd-loop` directly. Important source authority, compatibility, destructive removal, formula, or disputed completion claims route through `contract-auditor` before the owning role. Milestone, shared-boundary, boss-coverage, provider-policy, or cross-feature sequence decisions return to `architect-planner` and require the named human checkpoint.

Every feature has one completion boundary and one detailed feature commit containing all durable code, tests, fixtures/evidence, required documentation, and the milestone status update. There are no separate routing, planning-approval, preflight, evidence-seal, progress-sync, SHA-recording, or handoff-cleanup commits. A standalone planning/research deliverable may use one planning feature commit when explicitly completed as the deliverable.

Before a feature is complete:

- Acceptance must execute the authoritative production path with an independent fixture, oracle, or invariant where one exists; a green suite that only repeats implementation logic is insufficient.
- Required manual product, graph, provider, or operator checks must pass and be recorded, or the feature must state truthfully that none are required.
- Temporary tests, review batches, prompts, scenarios, command logs, generated reports, and handoff notes must be promoted to a durable semantic home or purged.
- Permanent tests must protect supported capabilities rather than milestone letters, workflow bookkeeping, or historical SHAs unless compatibility requires that history.
- The milestone status, relevant guide, and durable evidence must describe current behavior rather than projected completion.

Current audit verdict is `E complete`: committed evidence supports Features A, B, C1-C5, D, and E. The existing broad candidate/analyzer flow remains legacy compatibility evidence for the not-yet-implemented F-G architecture.

## Prioritized Feature Checklist

Implementation order is mandatory. Deterministic legality, scoring, and candidate quality precede analyzer refinement and paid tests.

### Feature A: Data Identity And Readiness Foundation

Status: Completed.

Route: `builder-executor -> tdd-loop` (completed feature boundary).

Prior work status:

- Sidekick/Character cleanup is completed and must remain regression-covered.
- Grasta identity/cardinality and canonical-character changes are implemented but await focused automated and manual verification.
- The broad candidate-bundle/correction implementation is a superseded prototype and carries no completion credit into later features.

Technical requirements:

- Verify stable Character and Grasta IDs across parsed artifacts, Neo4j, request normalization, frontend entities, and output.
- Verify Grasta exact variants, compatibility, acquisition classes, and maximum copies.
- Verify sidekick cleanup does not regress on ETL replay.
- Define stable Skill and PassiveSkill candidate identity or plan the required schema extension.
- Add readiness reporting for missing character, skill, passive, boss, mechanics, and item facts.
- Update schema version/assertions and plan ETL replay/migration if identity or role-evidence properties change.
- Preserve unrelated existing user changes while replacing only the superseded recommendation path during implementation.

Acceptance criteria:

- Sidekick-only names cannot enter hero pools.
- Canonical alias/style identities round-trip without analyzer-authored names.
- Exact Grasta variants do not collapse or accumulate unrelated requirements.
- Unique/finite variants enforce known limits.
- Missing/stale graph identities fail readiness visibly.
- Focused automated tests pass before Feature B.
- Manual readiness verification is repeatable using planned guide updates.

### Feature B: Typed Production Request And Retrieval Boundary

Status: Completed.

Route: `builder-executor -> tdd-loop` (completed feature boundary).

Technical requirements:

- Define typed request fields for canonical boss ID, roster, optional sidekicks, SA state, `late_game_assumed` policy, and natural-language preferences.
- Add deterministic service methods for boss, roster, skills/passives, mechanics, sidekicks, Grasta/build, and equipment context.
- Keep natural-language preferences outside legality-critical retrieval.
- Return typed missing/unsupported boss and normalization errors.
- Detect conflicts between selected boss ID and query text rather than guessing.
- Ensure production recommendation does not invoke PLAN, generated Cypher, or LLM retrieval validation.
- Preserve exploratory GraphRAG as a separate path or mode without using it as production fallback.

Acceptance criteria:

- Backend candidate preparation runs with zero retrieval/planner LLM calls.
- Invalid boss IDs fail deterministically.
- Typed retrieval returns only requested/eligible facts with coverage metadata.
- Natural-language preferences cannot expand ownership or candidate universe.
- Tests assert dynamic Cypher generation is not called.

### Feature C: Reviewed Atomic Capability Taxonomy And Reproducible Materialization

Status: C1-C5 completed. Feature D consumes the reviewed materialization handoff; Features D, E, and F are complete and Feature G is now admitted.

#### Feature C1: Atomic Contracts, Review Tooling, And Safety Cutover

Status: Completed.

Route: `builder-executor -> tdd-loop` (completed feature boundary).

Technical requirements:

- Replace Skill/PassiveSkill `role_tags` materialization immediately with versioned atomic `capability` and `dependency` contracts; do not retain both active systems during the review period.
- Define direction-aware and target-aware capability rules, explicit negative patterns, review states, evidence schema, overrides, and artifact version.
- Bump the schema version, remove stale broad-role graph properties, permit initially sparse proven materialization, and make candidate/rejected/ambiguous/untagged states non-authoritative.
- Generate deterministic stratified 45-row CSV batches from parsed facts and canonical JSON review/gold artifacts keyed by stable skill/passive IDs.
- Provide a constrained reviewer template, allowed-value reference, field guidance, source text/URL attribution, and validation that rejects blanks or invalid corrections before import.
- Preserve approved, corrected, ambiguous, and rejected decisions with reviewer notes; keep rejected decisions as permanent negative regression fixtures.
- Add deterministic diagnostics for proposed, proven, candidate, rejected, ambiguous, untagged, and reviewed counts per capability without hiding sparse coverage.
- Add artifact and graph drift detection over capabilities, dependencies, evidence, diagnostics, and artifact/schema versions.
- Keep live/request-time AI tagging, contextual role assignment, and direct AI mutation of canonical review artifacts out of scope.
- Amend record-type support, stable IDs, evidence, diagnostics, materialization, and drift checks for `SidekickSkill` and `SidekickAura` without restoring broad role tags.
- Make proposal IDs stable independently of taxonomy version while retaining exact taxonomy/review/schema versions in canonical evidence.
- Add constrained review fields for explicit target scopes, sidekick placement availability, optional magnitude/timing qualifiers, and qualifier corrections.

Acceptance criteria:

- The old active Skill/PassiveSkill broad-role properties and materializer are removed rather than maintained beside the atomic system.
- Every proven graph fact cites its matched phrase, direction/target, rule or override, source fact ID, review provenance, and artifact version.
- Review exports are deterministic for identical parsed facts, taxonomy version, phase, batch number, and sampling seed.
- Review import fails on blank decisions, unknown vocabulary values, malformed corrections, source-ID drift, or edited immutable evidence fields.
- Candidate, rejected, ambiguous, dependency-only, and untagged records cannot satisfy mandatory Feature D coverage.
- Neo4j is not the sole source of truth; artifact/graph drift fails visibly.
- No live AI tagging occurs.
- Sidekick skill/aura facts and taxonomy-version migrations obey the same immutable-evidence, review-state, reproducibility, and drift guarantees as character skills/passives.

#### Feature C2: Defensive And Setup Human-Review Gate

Status: Completed.

Route: `builder-executor -> tdd-loop` with required human review (completed feature boundary).

Technical requirements:

- Version and implement the expanded defensive/setup vocabulary across Skill, PassiveSkill, SidekickSkill, and SidekickAura records before review resumes.
- Keep objective atomic facts rather than ETL-level `mitigation`, `healing`, tank, healer, or sidekick-role labels; Feature D owns deterministic contextual grouping and RoleScores.
- Review zone deployment, resistance, `damage_reduction`, `damage_reduction_barrier`, `shield`, `heal_hp`, `regen_hp`, `remove_status_ailment`, `remove_debuff`, status and knockback immunity, `hold_ground`, `taunt`, `cover`, `guard`, `dodge`, `stalk`, direction-aware/target-aware `revive`, MP sustain, and required setup.
- Treat Barrier, Shield, and non-Barrier damage reduction as mutually distinct facts. Permit multiple facts from one source only when each effect is independently proven; Guard additionally proves Hold Ground only when source text explicitly says so.
- Review explicit ally scopes for self, one ally, adjacent allies, self plus adjacent allies, frontline, and main plus reserve, retaining relevant enemy/field/zone/none scopes.
- Record SidekickSkill capability availability as `main_only` and SidekickAura availability as `main_or_sub`, with captured activation conditions.
- Review explicit optional `magnitude_value`, constrained `magnitude_unit`, `activation_count`, `duration_turns`, and constrained `trigger` qualifiers. Unknown values remain unknown and cannot be invented or treated as zero.
- Preserve target scope separately from recipient eligibility. Weapon, element, personality, status, stack, position, and similar recipient requirements are condition evidence reviewed in C4 rather than target enum variants.
- Bump taxonomy/review/schema contracts as required, use version-independent proposal IDs, migrate unaffected batch-1 decisions, and produce a targeted migration-review artifact for renamed, split, or otherwise changed decisions.
- Preserve the original generated batch 2 as superseded audit history; reject its import under the replacement vocabulary and generate a replacement only after migration fixtures pass.
- Pause at `Awaiting human review` for every batch; require an explicit decision for every row before import.
- After import, correct repeated rule/override failures, add targeted regression fixtures, rerun all accumulated fixtures, and reset the clean-batch streak after any critical false-positive pattern.
- After migration review passes, complete two fresh consecutive 45-row batches with no new critical false-positive pattern.
- Plan the expanded migration, review, qualifier, sidekick, diagnostics, and recovery procedure for `docs/guides/ETL_GUIDE.md`; Feature C5 writes/finalizes the reusable guide after verification.

Acceptance criteria:

- Stable source IDs cover all four record types, and identical inputs reproduce identical proposals, qualifiers, review state, diagnostics, and materialized evidence.
- Unaffected batch-1 decisions survive migration; changed decisions cannot become proven until explicit targeted migration review passes.
- The superseded batch 2 fails import under the new contract, and its deterministic replacement contains exactly 45 new proposals using the expanded vocabulary and reference constraints.
- All accumulated C2 positive, corrected, rejected, ambiguous, migration, sidekick-placement, target-scope, compound-effect, and qualifier fixtures pass after every correction.
- Barrier, Shield, generic damage reduction, direct heal, Regen, ailment removal, debuff removal, status immunity, knockback immunity, Hold Ground, revive, taunt, Cover, Guard, dodge, and Stalk cannot satisfy one another unless Feature D later groups them through explicit deterministic policy.
- Missing qualifiers remain unknown; candidate, rejected, ambiguous, dependency-only, and untagged facts remain non-proven.
- Two fresh consecutive 45-row batches complete after migration with no new critical false-positive pattern.

#### Feature C3: Offensive And Support Human-Review Gate

Status: Completed; the MVP review tooling limits C3 to 25 active, source-backed families. The targeted seed review and two clean 45-row batches have passed their accumulated artifact regressions; C3 remains the artifact-only review boundary, with its reviewed output materialized by C5.

Route: `builder-executor -> tdd-loop` with required human review (completed feature boundary).

Technical requirements:

- Freeze the current C3 CSV review. Preserve the generated narrow-vocabulary batch 1 as a superseded audit artifact and make it non-importable under the replacement contract; it earns no clean-batch credit.
- Introduce a breaking taxonomy/review-schema `3.0.0` boundary while keeping proposal IDs stable independently of taxonomy version and retaining exact taxonomy, review, and schema versions in evidence.
- Preserve every unaffected C2 decision and C2's completed gate. Route renamed, split, or semantically changed facts through an explicit targeted migration-review artifact; never silently promote them under new semantics.
- Replace `ally_damage_up` with narrowly proven `outgoing_damage_up`; add `healing_effectiveness_up` without allowing either to prove `heal_hp` or `regen_hp`.
- Review only these 25 MVP atomic offensive/support families across Skill, PassiveSkill, SidekickSkill, and SidekickAura facts: `direct_damage`, `outgoing_damage_up`, `healing_effectiveness_up`, `fixed_damage`, `barrier_pierce`, `ignore_target_defense`, `element_resistance_down`, `inflict_pain`, `inflict_poison`, `inflict_break`, `af_gauge_restore`, `af_combo_gain_up`, `af_damage_up`, `grant_mental_focus`, `grant_singular_focus`, `grant_physical_overcritical`, `grant_magic_overcritical`, `apply_buff_reversal`, `apply_debuff_reversal`, `inflict_expose`, `apply_kaleido`, `grant_link`, `attack_again`, `chain_attack`, and `activate_lunatic`.
- Reserve but remove from active C3 rules, batches, seed coverage, and MVP scoring the ambiguous families `af_gauge_gain_up`, `invert_weakness_resistance`, `grant_copy`, and residual `follow_up_attack`. Their vocabulary names remain reserved; they are deferred to the future Offensive Taxonomy Extension and remain non-authoritative.
- All other unimplemented offensive/support families listed in earlier C3 drafts are likewise outside the MVP review contract. Their effects remain untagged and cannot supply contextual-role or mandatory-coverage credit.
- Use constrained qualifier domains rather than compound capability names: equipment class is Staff/Sword/Katana/Axe/Lance/Bow/Fists/Hammer; attack type is Slash/Pierce/Blunt/Magic; element is Fire/Water/Wind/Earth/Thunder/Shade/Crystal with explicit non-type only where valid. `Weapon Break` uses an attack-type qualifier, not an equipment-class qualifier.
- Represent Break through its named family plus constrained generic/elemental/weapon kind and matching attack-type or element qualifier. Preserve applied stack count as magnitude when explicit; do not execute its consumption behavior.
- Represent Lunatic as `activate_lunatic` plus a constrained Charge, Copy, Static/Discharge, Mind's Eye, Risktaker, or Sacrifice qualifier. Emit separately proven outcomes as independent facts; never introduce a permanent Lunatic role label.
- Keep `grant_link`, `attack_again`, and `chain_attack` distinct. Copy and residual follow-up semantics are deferred rather than inferred from Lunatic or Chain wording.
- Emit `direct_damage` only when the reviewed fact itself executes an attack or explicitly deals damage. Pure grants or enablers do not imply direct damage; compound facts emit multiple capabilities only when separate clauses prove each one.
- Emit only the named Buff Reversal, Debuff Reversal, and Expose facts. Do not synthesize the buffs, debuffs, weakness, or resistance states they could produce. Buff Reversal is enemy-directed; Debuff Reversal is self/ally-directed.
- Keep target scope, recipient eligibility, condition/dependency, duration, magnitude, stacking, and trigger orthogonal. C3 reviews capability, target, explicit magnitude, duration, trigger, bounded scaling evidence, and stacking; C4 reviews recipient eligibility and activation dependencies. A C3-approved fact with unresolved gating evidence cannot satisfy unconditional mandatory coverage before C4.
- Add minimal capture-only `stacking_behavior` values `not_applicable`, `stackable`, `overwrites`, and `unknown`, plus explicit `max_stacks` when proven. Do not calculate accumulated magnitude or assume maximum stacks are reached.
- Capture Max MP, enemy-level, excess-critical-rate, or similar scaling only as cited bounded evidence when explicitly stated. Do not implement formula evaluation, proc probability, damage/healing totals, move counting, AF simulation, turn scheduling, or rotations.
- Expand constrained trigger and qualifier references enough to distinguish battle/turn/skill activation, own-action Link/follow-up behavior, ally-action Chain behavior, on-hit behavior, Stellar Burst, and other explicitly reviewed triggers without executing them.
- Create and explicitly review a targeted seed artifact for rare/high-risk MVP cases, including reversal, Expose, both Overcritical channels, Focus effects, Lunatic variants, Chain, Link, attack again, barrier pierce, fixed damage, defense bypass, and misleading damage/healing/AF/resistance phrases. These decisions become permanent accumulated regressions and do not count toward either 45-row batch.
- Stabilize C3 review sequencing before batch credit: deterministically diagnose every active C3 family for positive and negative/cross-family fixture coverage; generate the targeted seed artifact only from source-backed parsed facts; and stop with a named coverage gap when an active family has no usable candidate. A gap requires one human-supplied canonical character or sidekick wiki page, exact fact name, and intended atomic capability before it can be added as a fixture; no capability may be inferred, silently skipped, or substituted from a general mechanics page.
- Preserve already reviewed replacement-batch decisions. When a seed fixture overlaps a reviewed batch proposal, retain that decision as seed evidence and deterministically refill only the overlap count with new unreviewed proposals so the eventual batch still has exactly 45 distinct new proposals. Do not require re-review of preserved rows.
- Keep C3 artifact-only: taxonomy, seed, batch, canonical-review, fixture, diagnostics, and regression work must not write reviewed capability facts to Neo4j. Feature C5 alone performs the full C2-C4 parsed replay, materialization, and graph-drift gate.
- Update `docs/guides/ETL_GUIDE.md` before replacement batch 1 with taxonomy 3.0 migration, superseded-batch rejection, targeted seed review, constrained qualifier and stacking review, import/correction, accumulated regression, and clean-streak recovery. Feature C5 verifies and finalizes the guide after full replay.
- Generate two deterministic stratified batches of exactly 45 new proposals each across active capability families and all four record types. The existing completed replacement batch may earn the first clean-batch streak after seed overlap is preserved, only the overlap count is deterministically refilled with new proposals, those new rows receive explicit human decisions, and the combined batch plus accumulated regressions pass without a critical pattern.
- Treat Feature C3 as correctness-based rather than exhaustive-tagging-based. Ambiguous, unsupported, candidate, rejected, and untagged facts remain reported and non-proven.

Acceptance criteria:

- Taxonomy/review-schema 3.0 validates every new capability and qualifier domain, rejects unknown values and invalid combinations, and reproduces identical proposals/evidence for identical inputs.
- Every unaffected C2 decision and fixture remains unchanged and passing; every semantic rename or split returns through targeted migration review before it can become proven.
- The superseded C3 batch 1 fails import under taxonomy 3.0, and its deterministic replacement contains exactly 45 new proposals after migration/seed review and regressions pass.
- The seed generator emits a deterministic, auditable targeted artifact containing one source-backed positive fixture and one negative or cross-family fixture for every uncovered active C3 family. It reports any unavailable active family by capability/rule and accepts no partial active-C3 seed as complete.
- An overlapping reviewed replacement-batch row is preserved rather than re-reviewed, then replaced with one deterministic new row before the batch receives clean-batch credit.
- Canonical C3 review import, fixture checks, and coverage diagnostics remain repository artifacts until Feature C5's full Neo4j replay; no earlier C3 action materializes facts to the graph.
- Every active C3 capability family has reviewed positive coverage and a relevant negative or cross-family fixture; every targeted rare/high-risk seed decision passes as an accumulated regression before a batch counts as clean.
- Direct damage, channel-agnostic outgoing damage, healing effectiveness, elemental-resistance reduction, Focus effects, active AF effects, bypass effects, reviewed transformations, and reviewed additional-execution mechanics cannot satisfy one another unless Feature D later groups them through explicit deterministic policy.
- Equipment class, attack type, element, target scope, recipient eligibility, dependency, duration, magnitude/scaling, stacking, and trigger round-trip independently through CSV, canonical JSON, evidence materialization, diagnostics, and drift checks.
- Missing magnitude, scaling, stacking, duration, trigger, or eligibility remains unknown rather than zero, maximum, unconditional, or inferred. C3-approved condition-sensitive facts remain ineligible for unconditional mandatory coverage until C4 validates their predicates.
- Sign of Collapse proves its enemy resistance reduction and granted Link/Break effects without proving zone deployment or party mitigation. Oh No Help proves outgoing-damage and healing-effectiveness amplification without proving a direct heal. Buff/Debuff Reversal, Expose, Link, attack again, Chain, Lunatic, barrier pierce, fixed damage, and defense bypass each prove only independently evidenced atomic facts.
- All accumulated C2-C3 positive, corrected, rejected, ambiguous, migration, seed, sidekick, target, compound, qualifier, stacking, and negative fixtures pass after every correction.
- `docs/guides/ETL_GUIDE.md` documents the replacement workflow before human batch review resumes and remains marked for C5 replay-aligned finalization.
- The refilled reviewed replacement batch earns the first clean-batch credit only after all its new rows and accumulated regressions pass; one subsequent fresh 45-row C3 batch completes the two-batch streak. Any critical pattern resets the C3 streak to zero.
- Recommended-lineup output identifies each selected skill/passive with untagged effect text by stable fact ID, display name, source URL, and compact captured snippet, explicitly labels it as non-authoritative and excluded from scoring/coverage, and never presents it as an inferred role. The MVP has no in-app feedback collection; experts submit those stable references through an external form for later CSV triage.
- Ambiguous and untagged facts are allowed, but no unsupported external mechanic, exact damage/healing result, proc probability, maximum-stack assumption, AF total, or turn-by-turn outcome becomes authoritative.

#### Feature C4: Dependencies And Conditions Human-Review Gate

Status: Completed.

Route: `builder-executor -> tdd-loop` with required human review (completed feature boundary).

Technical requirements:

- Review zone/status/stack/SA requirements, EOT effects, party-composition conditions, limited-use activation, sidekick activation conditions, and structured recipient eligibility such as weapon, element, personality, status, stack, or position in deterministic 45-row stratified batches.
- Use the same explicit-decision, human-review pause, correction, accumulated-regression, and clean-streak reset contract as C2-C3.
- Preserve all earlier decisions and verify that dependency rules cannot be promoted as standalone mandatory capabilities.

Acceptance criteria:

- Sign of Collapse proves its awakened-zone dependency without proving zone deployment.
- Conditional enhanced effects prove coverage only for recipients satisfying their reviewed eligibility predicates; eligibility never mutates the basic target-scope vocabulary.
- All accumulated C2-C4 fixtures pass after every correction.
- Two consecutive 45-row C4 batches complete with no new critical false-positive pattern.

#### Feature C5: Full Replay, Materialization, Drift Gate, And Handoff

Status: Completed; two clean full parsed replays, graph drift checks, schema assertions, and manual operator checks pass.

Evidence: Both replays produced taxonomy/review corpus `3.1.0`, gold fixture `1.0.0`, schema `1.5.0`, and 5,791 parsed facts with diagnostics totals of candidate 6,166, proposed 6,422, proven 229, reviewed 256, rejected 27, ambiguous 0, and untagged 2,310. The 5,103-record capability projection reproduced SHA-256 `0bcea9febee8118b4e2d49ea4fd525e84bd177be9e711eed2f66e8692e607dfa`; post-load schema and operator checks found zero stale schema nodes, broad-role properties, unreleased placeholders, or Character/Sidekick name overlap. The readiness report continues to expose sparse passive coverage as a visible data-completeness condition.

Route: `tdd-loop` for verification, durable evidence curation, milestone/guide reconciliation, and the single C5 feature commit. Return to `builder-executor` only if verification exposes a contained implementation defect.

Technical requirements:

- Replay the full parsed corpus using the locked taxonomy and canonical review artifacts, materializing only proven Skill, PassiveSkill, SidekickSkill, and SidekickAura capabilities and their dependencies into Neo4j.
- Verify identical inputs reproduce identical capabilities, dependencies, evidence, diagnostics, and graph state.
- Verify every rejected fixture remains rejected and every ambiguous/candidate/untagged fact remains non-authoritative.
- Update `docs/guides/ETL_GUIDE.md` with artifact bump, batch generation, human-review handoff, validation/import, correction loop, replay, diagnostics, and drift-repair procedures.
- Record the final taxonomy, artifact, schema, review-corpus, and diagnostics versions required by Feature D.

Acceptance criteria:

- **C5-01:** Same parsed data, review artifacts, taxonomy version, and schema version reproduce identical materialization and diagnostics across two clean full parsed replays.
- **C5-02:** Graph drift, artifact drift, stale broad-role properties, incomplete review imports, and rejected-fixture regressions fail visibly; the focused automated suite and post-load schema assertion pass.
- **C5-03:** The ETL guide makes the complete C1-C5 workflow repeatable without relying on chat history, and a manual operator follows its diagnostics/handoff inspection successfully.
- **C5-04:** The durable handoff records the exact taxonomy, review-corpus, gold-fixture, schema, and diagnostic contract that Feature D consumes, while every non-proven review state remains ineligible for coverage.

### Feature D: Hard Filters, RoleScores, And Skill Shortlists

Status: Completed. The typed production retrieval now derives deterministic backend-only Feature D policy output (`feature-d-role-score-v1`) from reviewed materialized facts: rejected characters never enter normal pools; required boss counters receive bounded explicit top-eight exceptions; all ten fixed role dimensions emit scores and source evidence; unavailable/SA-gated/non-proven facts never contribute; shortlists contain at most six legal skills and default packages contain three or four skills when available. Focused scoring, production retrieval, matchup, and legality suites pass (58 focused tests; workflow suite passes).

Route: `builder-executor -> tdd-loop`. Use `contract-auditor` first only for a disputed capability source, formula, compatibility boundary, or removal decision.

Technical requirements:

- Implement ownership/F2P, sidekick, SA, skill/passive, affinity, item, and setup hard filters.
- Hard-reject null/absorb primary damage and require neutral-or-better usable primary damage.
- Distinguish no weakness, unknown weakness, and incomplete affinity.
- Version the fixed contextual role dimensions `primary_damage`, `offensive_enablement`, `zone_setup`, `defense_mitigation`, `recovery_protection`, `tank_control`, `af_support`, `mp_sustain`, `boss_counter`, and `reserve_utility`.
- Derive per-character and per-sidekick contextual scores for those dimensions only from proven atomic Skill, PassiveSkill, SidekickSkill, and SidekickAura capabilities, reviewed qualifiers, placement availability, evidence, selected package, boss context, SA state, and policy version.
- Emit backend-owned primary/secondary role IDs and evidence. Keep any player-facing free-text role phrase non-authoritative and constrained to those IDs.
- Keep top eight per role plus bounded must-include exceptions.
- Score four-to-six skills per contextual role.
- Construct default three-to-four-skill packages for later lineup scoring.
- Add component breakdowns, penalties, confidence, and deterministic tie-breaking.

Acceptance criteria:

- **D-01:** Impossible candidates never enter normal role pools.
- **D-02:** Required boss counters survive top-eight pruning through explicit exceptions.
- **D-03:** Fixed role dimension IDs remain schema-valid while their scores vary deterministically by boss, SA state, placement, and selected package.
- **D-04:** Missing data cannot create capabilities, and candidate, rejected, dependency-only, ambiguous, or untagged facts cannot satisfy role or lineup coverage.
- **D-05:** Backend role IDs and evidence, rather than AI-authored role text, own filtering, top-K membership, and mandatory coverage.
- **D-06:** Skill shortlists exclude unavailable choices and remain bounded.
- **D-07:** Identical inputs and policy/artifact versions reproduce ordered pools, scores, role assignments, evidence, and packages.

### Feature E: Late-Game Build Packages And Allocation

Status: Completed. The backend now emits deterministic compact build packages under the `late_game_assumed` default (with `generic_only` fallback-compatible output), labels all item ownership as unverified, carries exact compatibility/evidence/assumption/setup/citation metadata, and validates finite Grasta and named-equipment allocation per lineup. Production candidate projection includes only selected package choices and bounded skill facts; it does not pass full Grasta or equipment catalogs to the analyzer.

Route: `builder-executor -> tdd-loop` (completed feature boundary).

Evidence: `.venv/bin/pytest -q tests/workflow/test_build_packages.py tests/workflow/test_role_scoring.py tests/workflow/test_feature_b_production.py tests/workflow/test_candidates.py` passes 34 tests, and `.venv/bin/pytest -q tests/unit` passes 141 tests. No manual or external-provider test is required for this deterministic backend feature.

Technical requirements:

- Implement `late_game_assumed` as the default and required item policy.
- Generate compact weapon, armor, three-Grasta, and optional Ore/build-intent packages.
- Validate exact compatibility, cardinality, named equipment allocation, and setup dependencies.
- Label ownership as unverified and provide farming/build-target wording.
- Retain `generic_only` as fallback-compatible design.
- Keep `declared_owned_only` deferred.

Acceptance criteria:

- **E-01:** Users need not enter inventory for MVP; every package labels item ownership as unverified under `late_game_assumed`.
- **E-02:** Exact personality/trait and weapon compatibility is enforced, and unique/finite Grasta cannot be illegally reused within a lineup.
- **E-03:** Specific named equipment is allocated at most once per lineup unless its source metadata explicitly permits reuse.
- **E-04:** Every package has compact weapon, armor, three-Grasta, optional Ore/build-intent, evidence, assumptions, allocation, setup dependencies, and citation fields; `generic_only` remains a safe fallback.
- **E-05:** Production analyzer projection contains only bounded package choices and never a full item catalog.

### Feature F: Capability Templates, Beam Generation, And Lineup Scoring

Status: Completed. The typed production path now generates deterministic,
coverage-valid backend lineups from burst, sustain, and hybrid capability
templates. Beam expansion is capped at 50 partial combinations per step;
full-lineup build allocation, sidekick placement, reserve utility, scoring,
deduplication, diversity, partial output, zero-candidate diagnostics, and the
analyzer zero-call gate are covered by durable regression tests.

Route: `builder-executor -> tdd-loop` (completed feature boundary).

Evidence: `.venv/bin/pytest -q tests/workflow/test_lineup_generation.py
tests/workflow/test_role_scoring.py tests/workflow/test_build_packages.py
tests/workflow/test_candidates.py tests/workflow/test_feature_b_production.py`
passes 40 tests; `.venv/bin/pytest -q tests/workflow --ignore=tests/workflow/test_graph.py`
passes 235 tests; and `.venv/bin/pytest -q tests/unit
tests/web/unit/test_feature_e_result_ui.py` passes 145 tests with one existing
dependency deprecation warning. The legacy graph happy-path test did not
complete in the local test environment and does not exercise the typed Feature
F generation path. No manual or external-provider test is required for this
deterministic backend feature.

Technical requirements:

- Express burst, sustain, and hybrid as mandatory/optional capability coverage.
- Use selected skill/build packages as proof of coverage.
- Generate from role pools without random shuffle.
- Cap beam expansion at 50 partial combinations per step.
- Score full lineups using the locked components and penalties.
- Score reserves and legal main/sub sidekick contributions.
- Deduplicate equivalent and near-identical strategies.
- Preserve diversity and retain up to ten legal candidates.
- Return partial candidates or structured zero-candidate causes.

Acceptance criteria:

- Candidate generation does not enumerate all six-hero combinations.
- All-DPS teams fail when mandatory coverage is missing.
- Multifunction heroes can satisfy multiple proven requirements.
- Burst, sustain, and hybrid remain distinct.
- Identical input reproduces candidates, scores, pruning reasons, and order.
- One to four candidates remain valid output when that is all that survives.
- Zero candidates skip the analyzer.

### Feature G: Compact Analyzer Projection And Bounded Refinement

Status: Completed. The typed production path now separates its full backend
candidate authority from a closed-world compact analyzer projection. Explicit
DeepSeek and OpenRouter adapters share an offline structured-output envelope;
the selected provider/model is carried per run without credentials. Analyzer
ranking and advisory refinements are bounded to one initial call plus one
fragment-only correction, while swaps and skill packages are re-scored and
revalidated against backend legality. Provider failure returns the legal
backend candidates in labeled degraded mode.

Route: `builder-executor -> tdd-loop`.

Technical requirements:

- Maintain separate full backend and compact analyzer contracts.
- Project only referenced candidates, catalogs, shortlists, packages, boss/mechanics facts, swaps, constraints, and citations.
- Introduce a provider-neutral analyzer port with independently selectable direct DeepSeek and OpenRouter routes. The post-G checkpoint owns paid admission; configuration may name providers/models but never store keys or credential values.
- Keep provider selection explicit per run. Application-managed cross-provider retry remains out of scope; Feature H may prove OpenRouter's server-managed ordered model fallback while preserving the application call cap, usage, cost, and degradation semantics.
- Use strict structured output on supported provider routes.
- Allow ranking, explanations, skill choice, and one supplied swap per lineup.
- Permit advisory execution-complexity, strategic-coherence, and matchup-nuance judgments, plus concise display-role wording grounded in supplied backend role IDs; do not accept AI-authored RoleScores, role IDs, or coverage claims.
- Re-score/revalidate refinements and restore defaults when worse or invalid.
- Freeze valid lineups.
- Permit one fragment-only correction call.
- Return legal backend candidates in labeled degraded mode when analyzer work fails or is skipped.

Evidence: `.venv/bin/pytest -q tests/workflow/test_analyzer.py
tests/workflow/test_lineup_generation.py tests/workflow/test_build_packages.py
tests/workflow/test_candidates.py tests/workflow/test_feature_b_production.py
tests/workflow/test_state.py` passes 45 tests; `.venv/bin/pytest -q
tests/workflow --ignore=tests/workflow/test_graph.py` passes 242 tests; and
`.venv/bin/pytest -q tests/unit tests/web/unit/test_feature_e_result_ui.py`
passes 145 tests with one existing Starlette/httpx deprecation warning. The
Feature G evidence includes independent offline adapter parity, projection
isolation, forbidden-authority rejection, two-call correction/freeze behavior,
lower-score fallback, and degraded provider fallback. No paid provider call,
live scrape, or credential-bearing manual check is authorized or required
before the named post-G human checkpoint.

Acceptance criteria:

- **G-01:** Projection contains no rejected roster, broad catalogs, non-proven coverage, or hidden free-text role authority.
- **G-02:** Analyzer cannot introduce out-of-bundle IDs, RoleScores, role IDs, or mandatory coverage claims.
- **G-03:** Direct DeepSeek and OpenRouter routes satisfy the same provider-neutral request, response, usage, validation, and error envelope in offline adapter tests.
- **G-04:** No request exceeds two analyzer calls; correction does not resend the full projection, and no automatic cross-provider retry adds an unbudgeted call.
- **G-05:** Lower-scoring swaps/packages fall back to originals, and AI advisory judgments never override deterministic score or legality results.
- **G-06:** One to three valid lineups may return.
- **G-07:** Analyzer or provider failure cannot invalidate legal backend candidates.

### Required Post-Feature-G Human Checkpoint: Boss Coverage And Paid Provider Admission

Status: Completed on 2026-08-09 and revised with human direction on 2026-08-10 as a read-only architecture decision after Feature G. Disposition 2 remains selected: insert a staged boss-corpus expansion feature before H. This checkpoint is not implementation authorization, paid-call authorization, or live-scrape authorization.

Route: `contract-auditor -> architect-planner` completed for the decision only. Feature G1 has its own `builder-executor -> tdd-loop` boundary before Feature H.

Audit verdict: `Conditional pass`. Feature G correctly keeps deterministic retrieval, RoleScores, candidate generation, compact projection, refinement validation, and degraded fallback closed-world. Its tests use synthetic boss facts, however, and do not establish an independent recommendation-ready boss corpus. The current parser configuration names seven weak bosses, while the checked-in v1.5.0 cache materializes only five. Those five retain source URLs and mechanics text, but all five have unknown weakness/null/absorb values, one has contaminated resistance text, whole-page mechanics fallback can cross boss/section boundaries, and no current fixture independently proves each boss's identity, affinity, mechanics, and citations through the Feature G path.

The cached Superbosses index exposes 178 rows and 176 distinct names, with 177 linked rows, but only five detail pages are cached. Its decimal difficulty values provide enough candidates for a stratified pilot: 35 unique names at 1.0-4.0, 33 rows at 4.5-8.8, and 109 unique names at 9.0-12.0. One name appears at two tiers, so no cross-band row may count twice without an explicit variant identity. Therefore 171 additional distinct identities have discovery metadata but no inspected detail-page evidence, and zero of 176 bosses currently meet the complete recommendation-readiness contract. An all-boss cutover would require source-manifest identity decisions, section/variant handling, affinity and mechanics parsing, source attribution, independent fixtures, deterministic replay, regression coverage, and evaluation cases for every admitted boss. Selected-boss retrieval keeps per-request runtime projection bounded, but crawl, curation, fixture, and paid-evaluation burden grows approximately linearly with admitted bosses. Index discovery and difficulty are selection metadata, not recommendation readiness.

Provider audit: Feature G proves only transport-injected offline envelope parity. Current official OpenRouter metadata lists `response_format` and `structured_outputs` for `deepseek/deepseek-v4-flash-0731`, `openai/gpt-5.6-luna`, and `z-ai/glm-5.2`. OpenRouter's ordered `models` fallback is one gateway request: it advances only when a model returns a routing-eligible error, charges the model that ultimately answers, and returns that served model in the response. It does not retry a successful HTTP response that later fails local schema or authority validation. The current application accepts one model string and has not yet proven ordered-model transport, served-model attribution, or fallback-aware usage/cost reporting. Direct DeepSeek remains useful offline adapter evidence but is not a Milestone 5 paid beta route.

Checkpoint acceptance:

- **PG-01 — revised and recorded with human approval:** Use the cached Another Eden Wiki Superbosses index/detail pages plus explicit per-boss source manifests as source authority. Feature G1 must produce exactly thirty recommendation-ready bosses: ten weak at wiki difficulty 1.0-4.0, ten medium at 4.5-8.8, and ten strong at 9.0-12.0. The five cached weak bosses count toward the weak cohort only after their affinity/mechanics/provenance defects are repaired, so twenty-five additional unique boss identities require admitted detail sources. Within each band, selection must maximize mechanics, affinity, parser, page-section, and beta-review diversity rather than choosing rows by difficulty alone. Every admitted boss needs canonical identity/aliases, exact source URL and section boundary, independently expected affinity/mechanics facts, parser regression fixtures, replay evidence, and a feasible or infeasible recommendation fixture; no canonical identity counts twice across bands. Flame Eater variants remain outside the supported boundary until their shared-section identity and independent mechanics evidence are resolved. All-boss coverage, live scraping without a separate checkpoint, automatic admission from index rows, and comprehensive coverage claims remain non-goals. Feature G1 remains before H with its own `builder-executor -> tdd-loop` boundary.
- **PG-02 — revised and recorded:** Milestone 5 paid beta qualification uses OpenRouter only, with the ordered model chain `deepseek/deepseek-v4-flash-0731` primary, `openai/gpt-5.6-luna` first fallback, and `z-ai/glm-5.2` final fallback. Direct DeepSeek paid qualification and Moonshot Kimi are deferred. Feature H must qualify all three models individually against the same strict projection/schema/authority fixtures before enabling OpenRouter's server-managed fallback array, capture the actual served model, and truthfully retain available prompt, completion, reasoning, cache, total, charged cost, latency, generation, and fallback metadata. Server-managed fallback counts as one application analyzer call; a locally invalid successful response may use the one fragment-correction call but cannot trigger an unbounded model retry loop. The 2026-08-10 hard-budget snapshot projects roughly RM0.02 for DeepSeek V4 Flash, RM0.03 for GPT-5.6 Luna, or RM0.02 for GLM-5.2 per worst-case logical request; the chain is conservatively below about RM0.03 per request, RM0.90 for thirty one-run boss cases, or RM2.70 for one worst-case run per boss against each of the three models. These are mutable planning estimates, exclude payment fees, and are not acceptance prices. No credential value is stored in the repository.
- **PG-03 — revised and recorded:** Feature H remains blocked until Feature G1 completes, deterministic boss fixtures pass, the three OpenRouter routes and ordered fallback/accounting behavior pass offline verification, and the human separately authorizes paid calls. No AI judge is admitted. The 2026-08-22 correction further defers Discord subjective feedback until after a stable portfolio preview; it is not an H acceptance gate. No paid call or live boss scrape is authorized by this checkpoint record.

### Feature G1: Thirty-Boss Stratified Corpus Readiness

Status: Completed; admitted by the post-Feature-G checkpoint and completed before Feature H. The bounded live fetch used the separately authorized exact thirty-page scope; no all-boss discovery or recursive crawl was used.

Route: `builder-executor -> tdd-loop` with a required human checkpoint before any live boss-page fetch.

Scope:

- Stage 1 repairs and independently fixtures the five cached weak bosses: Zennon Ogre's Shadow, Mimi, Cradle System, Insula Ventorum, and Nameless Girl.
- Stage 1 replaces implicit index-name authority with an explicit versioned boss source manifest containing canonical ID/name, aliases, source URL, optional section anchor, variant relationship, and support status.
- Stage 1 makes affinity parsing distinguish confirmed empty/neutral from unknown, rejects contaminated narrative fields, constrains mechanics extraction to the owned boss section, and retains source attribution for every projected boss fact.
- Stage 2 adds five unique weak bosses from difficulty 1.0-4.0, completing a ten-boss weak cohort that includes the repaired Stage-1 bosses.
- Stage 3 adds ten unique medium bosses from difficulty 4.5-8.8.
- Stage 4 adds ten unique strong bosses from difficulty 9.0-12.0.
- Every cohort must deliberately cover different affinity states and recommendation triggers, including combinations of weakness/resistance/null/absorb, zones, stoppers or phases, status pressure, summons or multiple targets, turn limits, sustain or MP pressure, AF constraints, and shared-page/section shapes where authoritative evidence permits them.
- Each boss is admitted individually only after parser, provenance, replay, and production recommendation fixtures pass. A failed selection remains unsupported and must be replaced by another unique candidate in the same band before Feature H; it cannot weaken the thirty-boss exit gate.

Non-goals:

- No automatic admission of all 176 discovered identities.
- No unbounded or recursive crawl, full all-boss scrape, claim of comprehensive coverage within any difficulty band, or claim that an index row or tier proves recommendation support.
- No LLM-authored boss facts, source repair, affinity inference, fixture oracle, or automatic curation.
- No Feature H paid provider call and no AI judge.

Acceptance criteria:

- **G1-01:** Every admitted boss round-trips through an explicit canonical identity/alias and source-section manifest; shared pages and variants cannot collapse or inherit one another's mechanics silently.
- **G1-02:** Weak, resist, null, and absorb fields preserve `confirmed values`, `confirmed none/neutral`, and `unknown` as distinct states, and independent fixtures catch narrative contamination or cross-section leakage.
- **G1-03:** Mechanics facts and compact projection cite the exact boss source and owned section; raw whole-page fallbacks cannot mark a boss recommendation-ready.
- **G1-04:** The ten weak bosses, including all five repaired cached bosses, each have independent parser and production fixtures that exercise retrieval, contextual roles/counters, candidate outcomes or typed infeasibility, compact boss projection, citations, and degraded fallback.
- **G1-05:** Exactly ten unique bosses in each approved band pass the same admission gates; eval metadata records `weak`, `medium`, or `strong`, and no canonical identity is counted in more than one cohort.
- **G1-06:** Deterministic replay and focused regression suites pass across all thirty bosses, permanent fixtures have documented authority independent of implementation, temporary crawl/evaluation outputs are promoted or purged, and one detailed Feature G1 commit owns implementation, evidence, guide/milestone updates, and handoff cleanup.

G1 completion evidence: `src/etl/superboss_manifest.json` validates the fixed
30-record exit gate; `tests/fixtures/superbosses/` contains the five repaired
cached fixtures, twenty-five bounded live section fixtures, independent
expected facts, and offline production outcomes; `tests/unit/test_superboss_corpus.py`
replays identity, affinity state, section, mechanics, provenance, production,
compact-projection, citation, and degraded-fallback gates. The unit suite and
G1-focused ETL/workflow suites pass; a broader workflow run remains subject to
an existing graph happy-path stall and is not used as G1 completion evidence.

## Approved Milestone 5 Correction Sequence

The 2026-08-22 architecture decision preserves the completed C-F commits as historical evidence while reopening their shared boundaries through new correction features. The blocking production evidence is authoritative over green synthetic tests: Neo4j retrieval completed with full requested coverage, yet a representative expected-feasible request had 17 eligible characters and zero candidates; a 65-character expansion also returned zero. Of those 65 characters only eight produced a three-to-four-skill default package. The current graph audit found 367 Character nodes, 267 with no `HAS_SKILL` relationship, only 99 with at least three Skill rows, and 288 with no passive rows. Within the explicit nine-character H roster, legal skill rows exist but only one to three capability-tagged skills per character are available, while the eight automatically added F2P characters have no skill or passive rows. This proves two distinct defects: incomplete kit materialization and an incorrect coupling between package legality and capability proof.

The correction architecture has two layers:

1. A complete legal-kit catalog determines which skills exist, belong to an exact character form/style, share an upgrade family, are equipable, and carry SA, manifest, equipment, or other dependencies.
2. Conservative reviewed capability evidence determines contextual RoleScores and mandatory coverage. Untagged legal skills remain selectable but receive no capability credit.

The ordered execution path is C6 -> D2 -> E2 -> F2 -> H. Each correction feature uses `feature-planner -> builder-executor -> tdd-loop`, owns one detailed feature commit, and must preserve the strict Feature C proof boundary. A source-authority or destructive migration dispute adds `contract-auditor` before implementation. Neo4j mutation, live crawling, paid-provider use, deployment, and publishing retain their separate human authorization gates.

### Feature C6: Full Character Kit Readiness And Selective Capability Evidence

Status: Complete. Automated verification, exact-corpus readiness, two
consecutive local Neo4j replays, targeted Laclair checks, and post-load schema
assertions pass.

Outcome: Every one of the 367 canonical MVP character forms/styles has a complete, replay-safe legal kit, while capability authority remains limited to reviewed proven atomic facts.

Scope:

- Crawl or replay the exact 367-character detail scope and normalize active skill families, passives, SA facts, dependencies, source revision, exact form/style ownership, and equipability.
- Emit one explicit materialization receipt per character. The receipt distinguishes successful population, verified absence, not-applicable data, and failed or ambiguous extraction.
- Treat upgrade stages and SA-enhanced forms of one equipped skill as one skill family. Ordinary basic attacks, Valor Chants, passives, and sidekick actions do not occupy active-skill package slots; legal basic-attack replacements or equipment-dependent actives must carry explicit type and dependency evidence.
- Make authoritative replay remove or replace stale character-kit relationships rather than accumulating obsolete rows.
- Review only high-value capabilities needed by contextual roles, mandatory boss coverage, feasible witnesses, and infeasibility certificates. Preserve every candidate, rejected, ambiguous, and untagged fact as non-authoritative.

Non-goals: exhaustive proof of every skill effect, complete combat-formula interpretation, role labels stored on Character nodes, or turn/rotation simulation.

Acceptance criteria:

- **C6-01:** Exactly 367/367 canonical character forms/styles have successful, non-ambiguous receipts with source/version provenance and explicit active/passive/SA states.
- **C6-02:** Every character has at least three distinct equipable active-skill families, or fails the milestone data gate with source-specific diagnostics rather than being classified as a weak or infeasible hero.
- **C6-03:** No active skill is orphaned, attached to the wrong style, duplicated through upgrade/SA variants, or silently retained after authoritative replay.
- **C6-04:** Identical source artifacts and policy versions reproduce identical kit facts, receipts, and graph state; schema, parser, loader, drift, and operator gates pass before H consumes the corpus.
- **C6-05:** Only reviewed proven capabilities contribute RoleScores or mandatory coverage; untagged legal skills remain visible and package-eligible with zero capability credit.

Current implementation evidence: schema 1.6.0 now carries explicit skill-family
and slot-eligibility fields, passive-grid extraction, authoritative stale-kit
replay, receipt projection, and graph readiness assertions. The durable
`src/etl/kit_catalog.json` replay contains exactly 367 canonical receipts and
reports 367 complete receipts with no ambiguous or failed records. The
refreshed `Laclair (Alter),Selfless Seeker` source contains nine distinct
equipable active families, while `Bow Strike` is an ordinary basic attack and
`Another Zone` is non-equipable. Unit/workflow verification, exact-corpus
validation, two consecutive local Neo4j replays, targeted Browser queries, and
post-load schema assertions passed on 2026-08-30. D2 may now consume the
complete corpus.

### Feature D2: Legal Skill Families And Contextual Package Frontier

Status: Approved and admitted as the next correction feature after C6.

Outcome: Package legality is independent of capability proof, and each complete hero exposes useful boss-aware alternatives rather than one global default package.

Scope:

- Generate one to three distinct, non-dominated package options per character and request. Offensive, sustain/defense/recovery, and counter/setup profiles guide diversity but are not rigid required labels.
- Use contextual value and boss/lineup requirements rather than raw tag count. A rare proven one-skill counter may dominate a package even when another category has more tagged skills.
- Require three distinct equipable skill families by default. Permit four only when that character's request input explicitly declares Light/Shadow points greater than or equal to 80; SA and `late_game_assumed` never infer the fourth slot.
- Allow legal untagged skills as fillers without granting role or coverage credit. Enforce SA, manifest, equipment, replacement, and other dependencies.
- Deduplicate equivalent package variants and preserve deterministic package IDs, evidence, and ordering.

Acceptance criteria:

- **D2-01:** A complete character is package-ready when at least one legal three-skill package exists; lack of three proven capability-tagged skills is not a readiness failure.
- **D2-02:** Every selected package contains distinct legal skill families and obeys the declared Light/Shadow slot limit and all dependencies.
- **D2-03:** Each proven capability contribution traces to the selected package or applicable passive evidence; untagged fillers contribute exactly zero coverage.
- **D2-04:** Representative multi-role heroes produce distinct non-dominated contextual options when evidence supports them, without forcing three artificial variants.

### Feature E2: Deterministic Alternative Build Allocation

Status: Approved and blocked by D2; may be implemented after D2's package dependency contract is stable.

Outcome: A lineup is rejected for build incompatibility only after deterministic compatible alternatives and finite-copy allocation have been exhausted.

Scope:

- Define `late_game_assumed` as access to the released catalog, never as an ownership claim.
- Enforce exact known maximum copies across one six-hero lineup. Allocation resets between alternative lineups.
- Treat named equipment as one copy unless repeatability is proven. For unknown named Grasta cardinality, avoid duplicate named copies and use compatible labelled generic placeholders when allowed.
- Generate deterministic per-character build alternatives and resolve lineup-wide compatibility through bounded matching or backtracking.
- Label and penalize generic placeholders; reject only when no compatible complete allocation exists.

Acceptance criteria:

- **E2-01:** Every accepted lineup has a complete compatibility-valid allocation respecting known finite maxima and conservative unknown-cardinality rules.
- **E2-02:** A greedy first choice cannot cause rejection when a deterministic alternative allocation exists.
- **E2-03:** Allocation is deterministic, bounded, independently reset per lineup, and reports named, generic, assumed, and unavailable choices distinctly.
- **E2-04:** `generic_only` remains legal and diagnosable but cannot hide missing skill packages or capability coverage.

### Feature F2: Package-First Beam Search And Stage Diagnostics

Status: Approved and blocked by D2 and E2.

Outcome: Beam search expands only structurally valid character-package choices while retaining complete diagnostics for excluded heroes and later constraint failures.

Scope:

- Precompute the valid `(character, selected_package)` frontier before lineup expansion.
- Prevent two package variants of the same hero from occupying multiple lineup slots.
- Exclude incomplete or structurally package-invalid choices before expansion, while naming the character and exact data/package reason in preprocessing diagnostics.
- Continue a request after excluding incomplete optional characters when at least six complete characters remain, but never claim authoritative infeasibility from the reduced roster. Fewer than six complete characters returns a data-readiness error.
- Keep preprocessing, mandatory coverage, affinity/matchup, allocation, and diversity/pruning diagnostics stage-accountable rather than presenting overlapping totals as independent candidate counts.

Acceptance criteria:

- **F2-01:** No beam state contains a character without a selected legal package or contains the same character twice.
- **F2-02:** Complete legal untagged fillers are not filtered out as capability failures; mandatory coverage still requires proven evidence.
- **F2-03:** `character_data_incomplete` exclusions are visible, never trigger a paid analyzer call, and never produce a definitive infeasible label.
- **F2-04:** Identical input, corpus, and policy versions produce identical frontier, beam, allocation, candidate order, and diagnostics.

### Feature H: Deterministic Evaluation, Token Accounting, And Paid Gates

Status: In progress but blocked at H-03. Existing offline fixture and evaluation work is incomplete and must be preserved. H returns to `feature-planner` after C6-D2-E2-F2 complete because its fixture authority and evidence contract changed materially. No paid call is authorized.

Route: `feature-planner -> builder-executor -> tdd-loop` for the corrected fixture/oracle and any remaining evaluation or provider transport implementation. Paid calls remain a separate human checkpoint.

Technical requirements:

- Build layered tests for taxonomy, materialization, normalization, hard filters, role/skill scoring, packages, templates, beam bounds, no-weakness affinity, projection leakage/budgets, swaps, partial output, and zero candidates.
- Split H into two suites. The boss-specific acceptance suite contains independently reviewed feasible witnesses and deterministic infeasibility certificates. The existing common nine-character requests remain unchanged as a fixed-roster stress suite and do not become feasible merely because their fixture label says so.
- A feasible acceptance case records a realistic owned roster plus at least one independently reviewed six-hero witness with legal selected packages, proven mandatory coverage, compatible affinity, and a valid finite-item allocation.
- An infeasible acceptance case is a valid, data-complete request with at least six usable characters and an explicit deterministic impossibility certificate. Unknown character names are request-validation regressions; incomplete kits are data-quality regressions; neither counts toward the ten strategic infeasible cases.
- Use the boss corpus admitted by the post-G checkpoint; an approved expansion must complete its own implementation/verification feature before H consumes it.
- Require all deterministic gates before paid analyzer calls.
- Qualify `deepseek/deepseek-v4-flash-0731`, `openai/gpt-5.6-luna`, and `z-ai/glm-5.2` individually against the same fixtures before enabling their ordered OpenRouter fallback chain.
- Keep the application-level maximum at two OpenRouter requests: initial analysis plus at most one fragment-only correction. OpenRouter's internal model/provider attempts do not grant additional application retries, and a locally invalid successful response does not trigger a fresh unbounded model chain.
- Capture provider/model metadata snapshot for every paid run.
- Record attempt-level usage, cost, latency, validation, actual served model, fallback, and degradation.
- Enforce locked per-call and cumulative budgets.
- Preserve the ~601k failure as a recorded baseline artifact.
- Export sanitized, deterministically valid recommendation samples for portfolio evidence and possible later Discord feedback; do not make Discord participation an H gate and do not use an AI judge.

Acceptance criteria:

- **H-01:** Hard legality and out-of-bundle ID gates pass 100%.
- **H-02:** Identical fixture input produces deterministic backend results.
- **H-03:** Every one of twenty independently witnessed feasible acceptance cases returns at least one legal, mandatory-coverage-valid, finite-allocation-valid backend candidate before any analyzer call. Every one of ten valid data-complete infeasible acceptance cases returns zero candidates for its recorded deterministic impossibility certificate and makes zero analyzer calls. The unchanged nine-character fixed-roster suite reports deterministic stress outcomes separately and cannot establish or invalidate the 20/10 oracle by itself.
- **H-04:** Each admitted OpenRouter model and every served fallback response reports or truthfully classifies unavailable prompt, completion, reasoning, cached, total-token, cost, latency, generation, and actual-model metadata without mixing model identities.
- **H-05:** Paid golden runs remain under 40k cumulative analyzer tokens and reduce baseline usage by at least 90%.
- **H-06:** Reports distinguish backend failures, analyzer structure/refinement failures, OpenRouter transport failures, model/provider fallback selection, local validation failure, budget degradation, and readiness for later human review.
- **H-07:** The ordered fallback chain is exercised only after all three models pass independent strict-output and authority gates; no AI judge call exists in the evaluation or public portfolio path.
- **H-08:** H evidence records the exact kit-corpus, receipt, capability, package-policy, allocation-policy, search-policy, boss-fixture, and request-fixture versions used; fake-runner or synthetic unit success alone cannot satisfy H-03.

### Feature I: Reusable Guidance And Portfolio-Preview Safeguards

Status: Planned after corrected Feature H. It locks the pre-deployment operating contract for the portfolio preview; deployment implementation remains sequenced after the frontend milestone. The controlled Discord demo and feedback program are deferred.

Route: `architect-planner` for the beta safeguard decision, then `release-manager-sync` only after repository evidence proves the milestone implementation and verification are complete. Deployment implementation remains Milestone 7.

Technical requirements:

- Reconcile `docs/guides/ETL_GUIDE.md` with the verified taxonomy/rule versions, replay, evidence materialization, drift tests, migration, and C5 handoff behavior.
- Rewrite stale portions of `docs/guides/recommendation-validation.md` for typed production readiness, backend role IDs/scores, pool pruning, beam diagnostics, projection inspection, the two-call cap, OpenRouter model fallback/served-model evidence, swaps, degraded mode, and golden evals.
- Require later related features to maintain these guides when commands, diagnostics, artifacts, or contracts change.
- Specify persistent email-verified registration, atomic monthly quota reservation, idempotent logical-request accounting, per-IP burst/concurrency protection, a global kill switch, and audit records that exclude prompts and secrets.
- Permit ten paid logical recommendation requests per registered user per calendar month. One initial analyzer call plus its optional fragment-only correction consumes one logical request; deterministic rejection before analyzer invocation consumes none.
- Enforce an RM50 global monthly hard ceiling. When either a user quota or the global ceiling is exhausted, paid analysis stops while deterministic candidate output remains available.
- Show selected-lineup untagged skill/passive diagnostics with stable fact IDs, names, source URLs, and short captured snippets, explicitly excluded from scoring and coverage.

Acceptance criteria:

- **I-01:** Another developer can reproduce capability materialization and diagnose drift.
- **I-02:** Another tester can inspect deterministic role derivation and candidate generation, then repeat offline and approved paid-provider validation.
- **I-03:** The guides contain no stale three-call, broad-Cypher production, free-text role-authority, or single-provider instructions.
- **I-04:** The future public portfolio deployment cannot expose an anonymous or unlimited paid endpoint; the ten-request user quota and RM50 global ceiling have precise persistent and atomic semantics.
- **I-05:** Portfolio-preview safety decisions are documented before deployment implementation, and guide maintenance remains part of later feature acceptance when behavior changes.
- **I-06:** Discord demo, reviewer recruitment, feedback forms, and public feedback metrics are absent from Milestone 5 acceptance and recorded in the future roadmap.

## Pre-Paid Evaluation Ladder

Paid OpenRouter testing is blocked until these gates pass in order:

1. C6 proves 367/367 legal-kit receipts, authoritative replay, and strict proven-capability separation.
2. Canonical identity, ownership, SA, declared Light/Shadow, affinity, sidekick, and hard rejection.
3. D2 contextual package frontiers with three legal skill families by default and four only at declared Light/Shadow >=80.
4. E2 build alternatives, compatibility, finite cardinality, and deterministic lineup allocation.
5. F2 package-first beam bounds, lineup invariants, stage diagnostics, and determinism.
6. No-weakness, unknown, resist, null, and absorb cases.
7. Projection schema, leakage prevention, and token preflight.
8. Swap re-scoring, rejection, fallback, frozen output, partial results, and degraded mode.
9. Boss-specific witnessed feasible and certified infeasible acceptance cases, plus the separate fixed-nine-roster stress suite.
10. Neo4j-backed H-03 evidence with zero pre-candidate analyzer calls.
11. Post-Feature-G boss-coverage and provider-admission decisions.
12. Separately qualified DeepSeek V4 Flash, GPT-5.6 Luna, and GLM-5.2 OpenRouter analyzer runs with captured model metadata and observed usage.
13. Ordered OpenRouter fallback verification and sanitized portfolio-preview sample export; no AI judge or Discord beta gate.

Hard gates require 100% legality, zero out-of-bundle IDs, deterministic backend output for identical inputs, at least one valid candidate for every feasible fixture, typed diagnostics for infeasible fixtures, and budget compliance.

## Planned Guide Updates

The owning implementation or release feature must update:

- `docs/guides/ETL_GUIDE.md` for capability artifact versioning, replay/materialization, schema migration, evidence diagnostics, and drift repair.
- `docs/guides/recommendation-validation.md` for candidate readiness, backend role-score inspection, pruning, beam tracing, build/skill packages, analyzer projection, the two-call correction contract, OpenRouter model fallback and served-model attribution, degraded mode, usage reports, and golden evaluation.

Later changes to the taxonomy, scoring policy, candidate contract, provider usage, evaluation commands, or operator workflow must maintain the relevant guide.

## Current Completion Status

- Milestone 5: active under the current lightweight SDD workflow.
- Feature A: completed; identity, cardinality, readiness, and replay-safe sidekick cleanup verified.
- Feature B: completed; typed production retrieval exists without PLAN or generated Cypher.
- Features C1-C4: completed with canonical review artifacts and accumulated regression evidence.
- Feature C5: completed; two clean full parsed replays, graph-drift, schema, guide, and manual operator gates pass.
- Feature D: completed; hard filters, backend-owned contextual RoleScores/evidence, deterministic top-eight pools with boss-counter exceptions, and bounded skill/package output are verified.
- Feature E: completed; late-game assumed compact build packages, exact item compatibility, finite/named allocation validation, assumption/evidence/citation metadata, and catalog-free production projection are verified.
- Feature F: completed; deterministic capability-template beam generation, full-lineup scoring, build/sidekick legality, diversity, partial/zero diagnostics, and analyzer zero-call handling are verified.
- Feature G: completed; compact closed-world projection, provider-neutral DeepSeek/OpenRouter offline adapters, strict authority validation, two-call fragment correction, deterministic refinement fallback, and labeled degraded backend output are verified.
- Post-Feature-G checkpoint: completed, revised, and human-approved; Disposition 2 admits Feature G1's fixed thirty-boss corpus of ten weak, ten medium, and ten strong cases plus an OpenRouter-only beta chain of DeepSeek V4 Flash, GPT-5.6 Luna, then GLM-5.2. Direct DeepSeek, Kimi, and AI judging are deferred. No live scrape, paid call, Feature G1 implementation, or Feature H work is authorized by the planning approval alone.
- Feature G1: completed; the fixed manifest and durable section fixtures contain exactly thirty unique recommendation-ready bosses across ten weak, ten medium, and ten strong cohorts, with the five cached weak repairs and twenty-five explicitly authorized additions independently replayed.
- Correction planning: completed and human-approved on 2026-08-22; C6 is complete, D2 is the next admitted correction feature, and E2/F2 remain sequenced behind D2 and E2 respectively.
- Feature H: in progress but blocked at H-03; current fixture labels do not independently prove feasible lineups, and existing work must be preserved through correction planning and implementation.
- The legacy exploratory analyzer remains a superseded broad-context prototype and must not be credited as the typed production compact-projection or two-call architecture.
- No new compact-projection or rewritten analyzer feature is credited as complete before its new acceptance gates pass.

## Milestone Exit Criteria

Milestone 5 completes only when:

- Features A-I, correction Features C6/D2/E2/F2, and any post-G boss-expansion feature admitted by the human checkpoint meet their acceptance criteria and each implementation feature owns one detailed completion commit.
- C5 proves reproducible reviewed materialization, D-F prove deterministic legal candidate generation, G proves bounded provider-neutral refinement and fallback, and H proves the admitted corpus and paid-provider gates.
- Production recommendation uses no PLAN, generated Cypher, retrieval-validation LLM, AI-authored RoleScores, or unbounded roster/catalog projection.
- The exact 367-character MVP corpus passes kit completeness, every feasible acceptance case has an independent witness and yields at least one legal coverage/allocation-valid backend candidate, and every strategic infeasible case has a deterministic impossibility certificate and returns typed diagnostics without an analyzer call.
- OpenRouter paid evidence for each admitted model and the ordered fallback chain stays within the locked call/token budgets, records the actual served model, and never depends on repository-stored credentials.
- Required operator/manual checks pass; ETL and recommendation guides match current commands, counters, contracts, and failure classifications.
- Temporary handoffs, generated outputs, obsolete scenarios, superseded workflow artifacts, and duplicate tests have been promoted or purged, and release reconciliation leaves the living roadmap accurate.

## Open Questions

The correction architecture has no unresolved shared-boundary decision. The following are scheduled evidence-driven refinements rather than permission to widen current scope:

- Exact initial scoring weights within the locked component model.
- Which reasoning setting for each admitted OpenRouter model gives the best structured recommendation quality within the locked token budget; model qualification must decide this before the fallback chain is enabled.
- Whether optional AI-assisted curation earns its cost.
- The exact authentication provider and persistence technology used later to implement the locked portfolio-preview quota and budget contract.
