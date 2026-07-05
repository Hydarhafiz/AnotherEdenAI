# AnotherEdenAI Milestone 5 Plan

## Executive Summary

Status: Active; rewritten and resequenced around deterministic recommendation generation.

Milestone 5 replaces broad-context LLM lineup search with a distributed backend-plus-LLM recommendation pipeline. Before contextual role scoring begins, a reopened Feature C must replace broad keyword-authored role tags with reviewed atomic capabilities and dependencies. The backend is the scout, filter, role scorer, skill/build packager, candidate generator, and referee. The analyzer LLM is a bounded strategist, tie-breaker, refiner, and communicator over five to ten compact legal candidates when that many exist.

The production recommender will use deterministic typed Neo4j retrieval rather than PLAN, generated Cypher, or LLM semantic retrieval validation. It will hard-reject impossible choices, compute contextual role and skill scores, generate capability-coverage lineups through bounded search, and validate all analyzer refinements. Normal paid usage is one analyzer call; the worst case is one initial call plus one fragment-only correction. A legal backend fallback prevents analyzer format, budget, or refinement failures from destroying otherwise valid recommendations.

This rewrite preserves verified prior work but does not credit the current broad candidate-bundle prototype as completed architecture. Candidate/team scoring and legality are implemented and proven before paid analyzer-quality work.

## Scope And Intended User Outcome

A late-game or near-endgame Another Eden player should be able to submit:

- An owned roster.
- Optional owned sidekicks.
- Optional per-character Stellar Awakening state.
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
4. Compute contextual role and per-role skill scores.
5. Build role-specific top-K pools with boss-counter exceptions.
6. Construct lineup-aware skill and build packages.
7. Generate burst, sustain, and hybrid candidates from capability templates using bounded beam search.
8. Validate, score, deduplicate, and diversity-filter legal candidates.
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
- No all-superboss evaluation tier.
- No intermediate or strong superboss evaluation tier.
- No live AI role tagging during requests or normal ETL.
- No mandatory AI-assisted labeling in initial acceptance.
- No free-form analyzer lineup assembly.
- No more than one analyzer-proposed hero swap per lineup.
- No paid judge on every live request.
- No rerun of the historical ~601k-token failure merely to recreate its baseline.
- No major frontend redesign beyond status, diagnostics, assumptions, degradation, and cost visibility required by this milestone.
- No deployment implementation beyond the beta-safety decisions explicitly retained after the core recommendation gates.

## Dependencies And Assumptions

- Milestone 4 recommendation shape, final legality concepts, curated weak bosses, MechanicReference corpus, and current UI remain the baseline.
- Sidekick/Character overlap cleanup is complete and must remain replay-safe.
- Grasta exact-variant identity, compatibility, acquisition class, and maximum-copy metadata must pass verification before build-package scoring is trusted.
- Canonical Character IDs and aliases must round-trip through request, graph, candidate, analyzer, validation, and display boundaries.
- Skills and passives require stable backend candidate IDs. Implementation may extend the schema if current composite identity is insufficient.
- Schema changes require a version bump, ETL replay/migration, schema assertions, and planned ETL-guide updates.
- The default target player has broad late-game item access; item ownership is not verified unless a future policy says otherwise.
- Curated boss and mechanics data may be incomplete. Unknown data lowers confidence and must remain distinct from confirmed facts.
- OpenRouter usage and model metadata are mutable external facts and must be captured at paid release-evaluation time.
- The historical ~601k-token failed run is a user-observed baseline for reduction reporting.
- The RM50/month public demo/beta ceiling remains a later operational constraint.
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
- Existing Another Eden wiki and mechanics references ground affinity, status, zone, SA, sidekick, and Grasta constraints.
- Community build references remain heuristic evidence only and require fixture or beta validation before tuning weights.

Open research gaps:

- Actual compact-projection token and cost distributions.
- Initial scoring-weight quality across the curated weak-boss fixtures.
- Experienced-player validation for high-impact role overrides and counter exceptions.
- Best paid analyzer model at release time.
- Value of optional OpenRouter-assisted low-confidence tag suggestions.
- Authentication, persistence, and per-user/global limits for beta.

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
- Direction and target semantics, such as ally versus enemy and grant/deploy versus require/consume.
- Deterministic positive rules and explicit negative/rejected patterns.
- Evidence fields, curated overrides, review status, and artifact version.

Representative atomic facts include `deploy_zone`, `awaken_zone`, `requires_zone`, `ally_resistance_up`, `enemy_resistance_down`, `inflict_break`, `direct_damage`, `grant_link`, healing, cleanse, taunt, barrier, MP recovery, and SA/stack/status/setup dependencies. The final vocabulary is locked through reviewed fixtures rather than inferred from this illustrative list.

ETL or parsed-artifact replay materializes only reviewed `proven` capabilities as active Skill and PassiveSkill graph facts. `candidate` matches remain review diagnostics and cannot satisfy mandatory coverage. `rejected` matches are preserved as negative regression fixtures so later taxonomy changes cannot reintroduce known false positives. Untagged facts are valid and reported.

Every proven capability cites the matched source phrase, direction/target semantics, rule or override, stable source skill/passive ID, review provenance, and artifact version. Neo4j is materialized output rather than the source of truth. Identical parsed data, review artifacts, and taxonomy versions must reproduce identical graph facts, and drift tests fail on differences.

Character roles are not permanent ETL labels. Feature D derives contextual `RoleScores` from proven Skill/PassiveSkill capabilities, selected package, SA state, boss matchup, build/sidekick assumptions, and lineup coverage. One character may support different roles in different contexts.

### Human Review Loop

The repository-native review workflow uses generated CSV batches for editing and canonical JSON for stable IDs, decisions, reviewer notes, gold fixtures, and regression history. No review UI is required.

Review proceeds in three ordered phases:

1. Mandatory defensive/setup capabilities: zone deployment, mitigation, healing, cleanse/status protection, tanking, MP sustain, and required setup.
2. Offensive/support capabilities: direct damage, buffs, debuffs, Pain/Poison, Break, AF support, and Links.
3. Dependencies and conditions: zone/status/stack/SA requirements, EOT effects, party-composition conditions, limited-use activation, and similar qualifiers.

Each phase generates deterministic stratified batches of exactly 45 new proposed decisions. Every row requires an explicit `approve`, `reject`, `correct`, or `ambiguous` decision before import; blank decisions fail validation. The generated reviewer template constrains decision, capability, dependency, direction, and target values and includes source text, source URL, and concise field guidance. Reviewers consult the linked wiki source only when the captured evidence is unclear; they do not manually reconstruct the corpus or assign contextual character roles.

The loop is generate batch -> pause at `Awaiting human review` -> edit CSV -> validate/import canonical JSON -> identify repeated failure patterns -> update rules/overrides -> rerun all accumulated fixtures -> generate the next batch. New targeted reproductions join the automatic regression set rather than inflating the next 45-row human batch. A phase passes only after every accumulated fixture passes and two consecutive fully reviewed batches reveal no new critical false-positive pattern.

A critical false-positive pattern is a repeatable rule error that could falsely satisfy mandatory lineup coverage, reverse ally/enemy or grant/require semantics, omit a gating zone/SA/status/stack dependency, or misclassify damage, defense, sustain, or setup across multiple facts. Discovery resets the phase's clean-batch streak. Rejected fixtures and untagged facts are expected; ambiguous facts remain non-proven; zero rejected records and full-corpus tagging are not goals.

### Optional AI-Assisted Curation

OpenRouter may later support a developer/admin-only batch that reads parsed artifacts and emits suggestion files for untagged, low-confidence, or selected high-impact records. It never runs during live recommendations or normal ETL, never directly mutates Neo4j or canonical artifacts, and is safe to skip.

Suggestion records include evidence, confidence, model, prompt version, timestamp, and source reference. Human review is mandatory. Accepted suggestions become ordinary versioned curated overrides, after which runtime materialization is deterministic without OpenRouter.

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

## Prioritized Feature Checklist

Implementation order is mandatory. Deterministic legality, scoring, and candidate quality precede analyzer refinement and paid tests.

### Feature A: Data Identity And Readiness Foundation

Status: Completed.

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

Status: Reopened and split into C1-C5; Feature D remains blocked until C5 completes.

#### Feature C1: Atomic Contracts, Review Tooling, And Safety Cutover

Status: Planned.

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

Acceptance criteria:

- The old active Skill/PassiveSkill broad-role properties and materializer are removed rather than maintained beside the atomic system.
- Every proven graph fact cites its matched phrase, direction/target, rule or override, source fact ID, review provenance, and artifact version.
- Review exports are deterministic for identical parsed facts, taxonomy version, phase, batch number, and sampling seed.
- Review import fails on blank decisions, unknown vocabulary values, malformed corrections, source-ID drift, or edited immutable evidence fields.
- Candidate, rejected, ambiguous, dependency-only, and untagged records cannot satisfy mandatory Feature D coverage.
- Neo4j is not the sole source of truth; artifact/graph drift fails visibly.
- No live AI tagging occurs.

#### Feature C2: Defensive And Setup Human-Review Gate

Status: Planned; blocked until C1 is verified.

Technical requirements:

- Review zone deployment, mitigation, healing, cleanse/status protection, tanking, MP sustain, and required setup in deterministic 45-row stratified batches.
- Pause at `Awaiting human review` for every batch; require an explicit decision for every row before import.
- After import, correct repeated rule/override failures, add targeted regression fixtures, rerun all accumulated fixtures, and reset the clean-batch streak after any critical false-positive pattern.
- Continue until two consecutive fully reviewed batches reveal no new critical false-positive pattern.

Acceptance criteria:

- All accumulated C2 fixtures pass after every correction.
- Two consecutive 45-row batches complete with no new critical false-positive pattern.
- Rejected and ambiguous defensive/setup claims remain non-proven after full-corpus replay.

#### Feature C3: Offensive And Support Human-Review Gate

Status: Planned; blocked until C2 completes.

Technical requirements:

- Review direct damage, buffs, debuffs, Pain/Poison, Break, AF support, and Links in deterministic 45-row stratified batches.
- Use the same explicit-decision, human-review pause, correction, accumulated-regression, and clean-streak reset contract as C2.
- Preserve all earlier C2 decisions and prove that C3 rule changes do not regress them.

Acceptance criteria:

- Sign of Collapse proves enemy resistance debuffs and granted Link/Break effects without proving zone deployment or party mitigation.
- All accumulated C2-C3 fixtures pass after every correction.
- Two consecutive 45-row C3 batches complete with no new critical false-positive pattern.

#### Feature C4: Dependencies And Conditions Human-Review Gate

Status: Planned; blocked until C3 completes.

Technical requirements:

- Review zone/status/stack/SA requirements, EOT effects, party-composition conditions, limited-use activation, and similar qualifiers in deterministic 45-row stratified batches.
- Use the same explicit-decision, human-review pause, correction, accumulated-regression, and clean-streak reset contract as C2-C3.
- Preserve all earlier decisions and verify that dependency rules cannot be promoted as standalone mandatory capabilities.

Acceptance criteria:

- Sign of Collapse proves its awakened-zone dependency without proving zone deployment.
- All accumulated C2-C4 fixtures pass after every correction.
- Two consecutive 45-row C4 batches complete with no new critical false-positive pattern.

#### Feature C5: Full Replay, Materialization, Drift Gate, And Handoff

Status: Planned; blocked until C2-C4 each pass their human-review gate.

Technical requirements:

- Replay the full parsed corpus using the locked taxonomy and canonical review artifacts, materializing only proven capabilities and their dependencies into Neo4j.
- Verify identical inputs reproduce identical capabilities, dependencies, evidence, diagnostics, and graph state.
- Verify every rejected fixture remains rejected and every ambiguous/candidate/untagged fact remains non-authoritative.
- Update `docs/guides/ETL_GUIDE.md` with artifact bump, batch generation, human-review handoff, validation/import, correction loop, replay, diagnostics, and drift-repair procedures.
- Record the final taxonomy, artifact, schema, review-corpus, and diagnostics versions required by Feature D.

Acceptance criteria:

- Same parsed data, review artifacts, taxonomy version, and schema version reproduce identical materialization and diagnostics across repeated clean replays.
- Graph drift, artifact drift, stale broad-role properties, incomplete review imports, and rejected-fixture regressions fail visibly.
- The ETL guide makes the complete C1-C5 workflow repeatable without relying on chat history.
- Feature D consumes only proven atomic capabilities from the locked C5 handoff and remains unable to treat any other review state as coverage.

### Feature D: Hard Filters, RoleScores, And Skill Shortlists

Status: Planned; blocked until Feature C5 completes the reviewed materialization handoff.

Technical requirements:

- Implement ownership/F2P, sidekick, SA, skill/passive, affinity, item, and setup hard filters.
- Hard-reject null/absorb primary damage and require neutral-or-better usable primary damage.
- Distinguish no weakness, unknown weakness, and incomplete affinity.
- Derive per-character per-role scores only from proven atomic Skill/PassiveSkill capabilities, with evidence and policy version.
- Keep top eight per role plus bounded must-include exceptions.
- Score four-to-six skills per contextual role.
- Construct default three-to-four-skill packages for later lineup scoring.
- Add component breakdowns, penalties, confidence, and deterministic tie-breaking.

Acceptance criteria:

- Impossible candidates never enter normal role pools.
- Required boss counters survive top-eight pruning through explicit exceptions.
- Role scores vary by boss and available package.
- Missing data cannot create capabilities.
- Candidate, rejected, dependency-only, and untagged facts cannot satisfy mandatory role or lineup coverage.
- Skill shortlists exclude unavailable choices and remain bounded.
- Identical inputs/policy versions reproduce ordered pools and packages.

### Feature E: Late-Game Build Packages And Allocation

Status: Planned.

Technical requirements:

- Implement `late_game_assumed` as the default and required item policy.
- Generate compact weapon, armor, three-Grasta, and optional Ore/build-intent packages.
- Validate exact compatibility, cardinality, named equipment allocation, and setup dependencies.
- Label ownership as unverified and provide farming/build-target wording.
- Retain `generic_only` as fallback-compatible design.
- Keep `declared_owned_only` deferred.

Acceptance criteria:

- Users need not enter inventory for MVP.
- Unique/finite Grasta cannot be illegally reused within a lineup.
- Specific named equipment cannot be duplicated illegally.
- Every package has evidence, assumptions, allocation, setup dependencies, and citations.
- Analyzer never receives full item catalogs.

### Feature F: Capability Templates, Beam Generation, And Lineup Scoring

Status: Planned.

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

Status: Planned.

Technical requirements:

- Maintain separate full backend and compact analyzer contracts.
- Project only referenced candidates, catalogs, shortlists, packages, boss/mechanics facts, swaps, constraints, and citations.
- Use strict structured output on supported provider routes.
- Allow ranking, explanations, skill choice, and one supplied swap per lineup.
- Re-score/revalidate refinements and restore defaults when worse or invalid.
- Freeze valid lineups.
- Permit one fragment-only correction call.
- Return legal backend candidates in labeled degraded mode when analyzer work fails or is skipped.

Acceptance criteria:

- Projection contains no rejected roster or broad catalogs.
- Analyzer cannot introduce out-of-bundle IDs.
- No request exceeds two analyzer calls.
- Correction does not resend the full projection.
- Lower-scoring swaps/packages fall back to originals.
- One to three valid lineups may return.
- Analyzer failure cannot invalidate legal backend candidates.

### Feature H: Deterministic Evaluation, Token Accounting, And Paid Gates

Status: Planned.

Technical requirements:

- Build layered tests for taxonomy, materialization, normalization, hard filters, role/skill scoring, packages, templates, beam bounds, no-weakness affinity, projection leakage/budgets, swaps, partial output, and zero candidates.
- Define feasible and infeasible golden weak-boss fixtures with expected constraints and quality notes.
- Require all deterministic gates before paid analyzer or judge calls.
- Capture provider/model metadata snapshot for paid runs.
- Record attempt-level usage, cost, latency, validation, fallback, and degradation.
- Enforce locked per-call and cumulative budgets.
- Preserve the ~601k failure as a recorded baseline artifact.
- Use paid judge only offline on deterministically valid output.

Acceptance criteria:

- Hard legality and out-of-bundle ID gates pass 100%.
- Identical fixture input produces deterministic backend results.
- Every feasible fixture returns at least one legal coverage-valid candidate.
- Infeasible fixtures return classified diagnostics without analyzer calls.
- Paid golden runs remain under 40k cumulative analyzer tokens and reduce baseline usage by at least 90%.
- Reports distinguish backend failures, analyzer structure/refinement failures, provider transport failures, budget degradation, and subjective quality.
- Provider generation and judging roles are explicit.

### Feature I: Reusable Guidance And Beta Safeguards

Status: Planned after Features A-H.

Technical requirements:

- Plan updates to `docs/guides/ETL_GUIDE.md` for taxonomy/rule versions, replay, evidence materialization, drift tests, and migration.
- Plan updates to `docs/guides/recommendation-validation.md` for readiness, score breakdowns, pool pruning, beam diagnostics, projection inspection, token budgets, swaps, degraded mode, and golden evals.
- Require later related features to maintain these guides when commands, diagnostics, artifacts, or contracts change.
- Decide authentication, persistence, feedback, caching/deduplication, rate limits, and monthly budget enforcement before controlled beta.
- Preserve RM50/month as the starter beta/demo ceiling unless later evidence changes it.

Acceptance criteria:

- Another developer can reproduce role materialization and diagnose drift.
- Another tester can inspect candidate generation and repeat golden validation.
- Public beta cannot expose an unlimited unauthenticated paid endpoint.
- Beta safety decisions are documented before deployment implementation.
- Guide maintenance is part of later feature acceptance when behavior changes.

## Pre-Paid Evaluation Ladder

Paid OpenRouter testing is blocked until these gates pass in order:

1. Role artifact schema and reproducibility.
2. Canonical identity, ownership, SA, affinity, sidekick, and hard rejection.
3. Contextual RoleScores and bounded skill shortlists.
4. Skill-package dependency and fallback.
5. Build compatibility, cardinality, and allocation.
6. Capability templates, beam bounds, lineup invariants, and determinism.
7. No-weakness, unknown, resist, null, and absorb cases.
8. Projection schema, leakage prevention, and token preflight.
9. Swap re-scoring, rejection, fallback, frozen output, partial results, and degraded mode.
10. Offline end-to-end feasible and infeasible golden cases.
11. Paid analyzer with captured model metadata and observed usage.
12. Optional paid judge only for deterministically valid release-evaluation outputs.

Hard gates require 100% legality, zero out-of-bundle IDs, deterministic backend output for identical inputs, at least one valid candidate for every feasible fixture, typed diagnostics for infeasible fixtures, and budget compliance.

## Planned Guide Updates

Implementation must update, but this architect-planner session does not edit:

- `docs/guides/ETL_GUIDE.md` for role artifact versioning, replay/materialization, schema migration, evidence diagnostics, and drift repair.
- `docs/guides/recommendation-validation.md` for candidate readiness, score inspection, pruning, beam tracing, build/skill packages, analyzer projection, correction, degraded mode, usage reports, and golden evaluation.

Later changes to the taxonomy, scoring policy, candidate contract, provider usage, evaluation commands, or operator workflow must maintain the relevant guide.

## Current Completion Status

- Milestone 5: active and rewritten.
- Feature A: completed; identity, cardinality, readiness, and replay-safe sidekick cleanup verified.
- Features B-I: planned.
- No new deterministic role-scoring, beam-generation, compact-projection, or rewritten analyzer feature is credited as complete before its new acceptance gates pass.

## Open Questions

No architecture-blocking questions remain. The following are evidence-driven tuning or later operational decisions:

- Exact initial scoring weights within the locked component model.
- Exact five weak bosses in the golden release set.
- Paid analyzer model at release time.
- Whether optional AI-assisted curation earns its cost.
- Beta authentication, persistence, feedback storage, per-user limits, and caching policy.
