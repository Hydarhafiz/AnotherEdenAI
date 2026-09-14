# AnotherEdenAI Milestone 6 Plan

## Executive Summary

Status: Active as of 2026-09-14. Milestone 5 is closed through an approved scope correction that preserves its completed architecture and evaluation evidence while explicitly reassigning its uncompleted paid-provider and portfolio-safeguard work.

Milestone 6 expands recommendation-ready, high-value strategic evidence across all 367 canonical character forms/styles and improves meaningful candidate diversity. It does not attempt to model every mechanic, prove a globally optimal team, predict a clear, or replace conservative evidence review with inference.

The product claim is:

> AnotherEdenAI generates legal, boss-aware, evidence-backed lineup candidates from the player's available roster and explains why they are strategically plausible.

Candidates remain bounded, auditable recommendations. They are not guaranteed clears, exact simulations, globally optimal parties, or numeric win probabilities.

## Milestone 5 Transition

Milestone 5 established the production-safe recommendation boundary: deterministic backend code owns typed legal retrieval, legal-kit materialization, capability-grounded scoring, packages, bounded search, finite allocation, validation, fallback, and cost control; the analyzer may only rank, refine, and explain supplied legal candidates within closed-world constraints.

The completed Milestone 5 plan remains recoverable in Git through its final Feature H2 commit. Its concise closure record and explicit scope dispositions live in `docs/core/roadmap.md`, `docs/core/planning-sources.md`, and `CHANGELOG.md`. Ordinary historical Feature A-H identifiers in architecture, schema, tests, guides, sources, and commits remain accurate and are not renumbered.

Milestone 5 did not complete its former Feature I or the former paid OpenRouter H-04/H-05/H-07 multi-model and ordered-fallback gates. On 2026-09-14 the owner approved closing M5 by superseding those exit obligations rather than marking them passed:

- high-value capability and untagged-evidence diagnostics move into Milestone 6;
- frontend presentation work moves to Milestone 7;
- registration, quota, global-spend safeguards, kill-switch behavior, and release-time paid-provider qualification move to Milestone 8; and
- guide maintenance remains an acceptance responsibility of every feature that changes the relevant behavior.

No production behavior, provider configuration, graph data, schema version, or paid-service state changed during this planning transition.

## Purpose And Intended Outcome

Milestone 6 keeps every data-complete canonical form/style legally selectable when present in the effective user roster while attempting high-value capability extraction across the entire catalog. It should give deterministic search enough proven evidence to produce strong, plausible, auditable, and meaningfully different boss-specific candidates when the roster genuinely supports alternatives.

The milestone works from boss requirements toward character evidence:

```text
curated boss mechanics
    -> required and high-value counters
    -> prioritized capability families
    -> full-catalog extraction attempts
    -> proven / ambiguous / unknown evidence
    -> boss-specific legal filtering and scoring
    -> diverse legal lineup candidates
```

The objective is sufficient high-value evidence for reliable candidate generation, not exhaustive interpretation of every low-impact buff, stack nuance, passive, multiplier, interaction, or turn-order edge case.

## Scope

Milestone 6 includes:

- an authoritative baseline of catalog, capability, search-funnel, and candidate-diversity coverage;
- boss-driven prioritization from the existing thirty-boss corpus;
- deterministic high-value capability proposals attempted across all 367 canonical forms/styles;
- selective human review of ambiguous, high-impact, recurring, and boss-acceptance-relevant facts;
- conservative materialization of proven evidence with explicit unknown and ambiguous states;
- request-time pool and candidate-set diagnostics;
- evidence-driven candidate-generation improvements after diagnostics establish the failure mode;
- controlled evaluation rosters that can demonstrate when alternatives do and do not exist; and
- H2's four human-readable modeled-viability gates as the recommendation-quality framework.

All 367 canonical forms/styles remain in scope. Milestone 6 must not replace them with a fixed supported subset of 50-100 characters.

## Non-Goals

- Exhaustive manual review of every skill and passive.
- Full strategic interpretation of every character mechanic.
- A complete combat ontology or exact turn/damage simulator.
- Global six-character optimization or proof of the best possible party.
- Guaranteed victory, clear-rate prediction, or numeric win probability.
- Complete best-in-slot or player-inventory optimization.
- Automatic classification of unresolved evidence as absence.
- Expansion beyond the approved thirty-boss corpus unless separately admitted.
- More than one backend-authorized analyzer hero swap per lineup.
- Paid analyzer evaluation before deterministic coverage and diversity gates pass.
- Production provider, reasoning, token, or fallback configuration changes.
- Frontend implementation, deployment, authentication, quotas, or public beta work.

## Locked Architecture Boundaries

### Legal-Kit Layer

The legal-kit layer remains complete for the current 367-character canonical catalog. It answers whether the exact form/style exists, which active skill families and passives belong to it, whether Stellar Awakening applies, which upgrade families and dependencies exist, and whether IDs and equipability are valid.

A data-complete legal skill remains selectable even when its strategic capability is untagged. Missing capability proof cannot make a legal character or skill illegal.

### Capability-Proof Layer

The capability-proof layer remains conservative and independently versioned. Only reviewed proven facts may contribute contextual scores, mandatory coverage, dependency satisfaction, or boss-counter evidence.

Coverage accounting may expose these semantic states for a `(character, capability)` question:

- `proven_present`: reviewed evidence establishes the capability;
- `proven_absent`: authoritative evidence explicitly establishes absence under a defined complete scope;
- `ambiguous`: relevant evidence exists but does not support a safe conclusion; and
- `unknown`: extraction was not conclusive or no authoritative proof exists.

`proven_absent` must not be inferred from an untagged fact, a rejected classifier proposal, a missing relationship, zero score, or an unsuccessful rule match. Existing proposal/review states such as candidate, rejected, ambiguous, and untagged retain their current meanings; a rejected proposal disproves that proposal, not necessarily the character-level capability.

No schema-version change is authorized by this plan. If implementation later changes persisted graph or artifact shape, that feature must update `docs/core/SCHEMA.md`, migrations, fixtures, and schema assertions together.

## High-Value Capability Scope

Prioritize facts that can materially change lineup selection.

### Primary Offense

- direct damage and primary damage element/type;
- weakness exploitation and resistance/type-resistance reduction;
- damage amplification and offensive stat support;
- critical and magic-critical support;
- Pain/Poison enabling, Break, and AF contribution; and
- major conditional damage dependencies.

### Setup And Strategy

- deploy, awaken, counter, or require zone;
- require Pain, Poison, Lunatic, or Another Force; and
- meaningful stance, resource, position, or setup requirements.

### Defense And Sustain

- offensive-stat debuffs and physical/type resistance;
- damage reduction, barriers, guard, tank, and cover behavior;
- healing, regeneration, MP sustain, and revival where material; and
- status cleanse, immunity, resistance, and other counterplay.

### Boss-Specific Utility

- dispel or buff removal and debuff cleanse;
- zone counterplay and elemental conversion/Kaleido;
- resistance/weakness manipulation; and
- other evidence-backed mechanics that materially affect one or more bosses in the approved corpus.

Low-value self-buffs, exact multiplier interactions, niche stack behavior, and turn-order details may remain unknown unless evaluation shows that they materially affect candidate quality.

## Boss-Driven Prioritization

The committed thirty-boss corpus is the initial evaluation and priority authority. Work begins with each boss's important threats and requirements, maps them to counter capabilities, then identifies catalog facts that can prove those capabilities. Taxonomy breadth is not an end in itself.

The priority matrix must distinguish:

- required counters whose absence invalidates a candidate;
- high-value counters that materially improve modeled viability;
- contextual advantages that affect ranking but are not mandatory; and
- mechanics that current evidence cannot safely model.

An obscure mechanic may remain deferred when it affects no approved acceptance case and does not represent a recurring high-impact gap.

## Human Review Policy

Milestone 6 reuses the existing taxonomy, deterministic proposal, constrained review, negative-fixture, override, provenance, and replay pipeline:

```text
parsed skill/passive facts
    -> deterministic proposal
    -> high-confidence handling permitted by existing policy
       or constrained proposal queue
    -> ambiguous/high-impact review
    -> approve / correct / reject / ambiguous
    -> replay and regression verification
```

Manual attention is limited to ambiguous high-value facts, strategically important exceptions, rule-quality sampling, boss-acceptance facts, and recurring unclassified patterns worth encoding. The owner is not required to inspect thousands of low-value facts or every skill/passive across all 367 forms/styles.

## Coverage Accounting

Feature A must establish exact names and current distributions before numeric milestone thresholds are approved. At minimum the offline catalog report covers:

```text
catalog_characters
legal_kit_complete
high_value_capability_attempted
characters_with_proven_primary_damage
characters_with_offensive_enablement
characters_with_zone_setup
characters_with_mitigation
characters_with_recovery
characters_with_status_counterplay
characters_with_af_support
characters_with_pain_poison_setup
characters_with_boss_counter_evidence
facts_proven
facts_unknown
facts_ambiguous
facts_rejected
```

Request-time reporting covers distinct stages rather than conflating catalog size with candidate count:

```text
user_roster_count
f2p_augmented_count
distinct_available_count
data_complete_count
boss_eligible_count
role_pool_union_count
candidate_count
unique_character_set_count
unique_frontline_set_count
unique_archetype_count
```

Names may follow established repository conventions, but every metric requires a precise definition, source, denominator, and unknown-data policy.

## Candidate Diversity Contract

Diversity must be meaningful rather than cosmetic. When the effective roster and boss constraints support alternatives, returned candidates should not be permutations of the same six characters, opaque IDs over identical score vectors, or the same team relabeled burst/hybrid/sustain.

Diagnostics should include where practical:

- unique six-character sets;
- unique frontline sets;
- unique archetypes with evidence of actual strategic differentiation;
- permutation-only warnings;
- identical score-vector warnings; and
- candidate-set overlap or Jaccard similarity.

The system must not manufacture weaker or incoherent alternatives merely to meet a count. One candidate is acceptable when evidence demonstrates that only one strategically valid team exists. Candidate-generation or scoring changes begin only after the baseline and diagnostics identify the responsible stage.

## Recommendation-Quality Gates

Milestone 6 retains the H2 four-gate framework:

1. **Damage affinity and elemental viability:** primary damage is neutral-or-better, weakness is positive, resistance is penalized, null/absorb is rejected, and explicit boss affinity overrides generic assumptions.
2. **Boss-mechanic counter coverage:** the lineup has evidence-backed answers to required important threats.
3. **Team synergy and role coherence:** the lineup has an identifiable win condition; enablers support it; defense and reserves have a purpose; and zone/element/type choices cohere.
4. **Setup executability:** required zone, Pain, Poison, Lunatic, AF, stance, or analogous dependencies have a provider or valid system action.

There is no fifth guaranteed-clear gate. Allowed conclusions include `high modeled viability`, `well-matched according to modeled evidence`, `plausible boss-aware candidate`, and `strong evidence-backed recommendation`.

## Cost, Analyzer, And Swap Policy

- Deterministic coverage and diversity gates run before any paid analyzer evaluation.
- DeepSeek `reasoning=none` with a 4,000-token output cap remains the provisional initial evaluation baseline from H1; it is not a production-setting change or a strategic-quality oracle.
- Paid evaluation requires separate human authorization and is not automatically required to complete Milestone 6.
- Release-time multi-model and ordered-fallback qualification belongs to Milestone 8.
- The analyzer remains limited to one initial call plus at most one fragment-only correction.
- Each lineup remains limited to at most one backend-authorized hero swap.
- Whether two authorized swaps add value is an evidence-driven future question after Milestone 6 evaluation. Three or four swaps remain out of scope.

## Dependencies

- Completed Milestone 5 deterministic retrieval, legal-kit, capability, package, search, validation, fallback, and evaluation contracts.
- The authoritative 367-character kit catalog and complete legal-kit receipts.
- The committed thirty-boss manifest, source captures, parsed replay, and H acceptance fixtures.
- Existing taxonomy, reviews, gold and negative fixtures, curated overrides, provenance, and replay verification.
- H1/H2 evaluation tooling and four-gate review language.

## Feature Plan

### Feature A: Coverage Baseline And Metric Contract

Status: Completed on 2026-09-14; stopped at the planned threshold-setting human checkpoint.

Type and route: `build` via `builder-executor -> tdd-loop`, with a read-only authority audit if metric sources or state mappings are disputed.

Outcome: Produce reproducible offline catalog and request-time coverage reports with explicit denominators and semantic-state handling.

Acceptance:

- **A-01:** The report reconciles exactly 367 canonical catalog identities with 367 complete legal-kit receipts or fails visibly on drift.
- **A-02:** Every required catalog and request-time metric has a deterministic definition, source, denominator, and unknown-data policy.
- **A-03:** `unknown`, `ambiguous`, rejected proposals, untagged facts, and proven absence are not collapsed.
- **A-04:** Current high-value coverage distributions are recorded without inventing a target threshold.
- **A-05:** Temporary generated reports remain ignored; only reusable tooling, authoritative fixtures, and a concise accepted baseline are retained.

Completion evidence:

- Offline reporting reconciles 367 distinct canonical identities with 367 recomputed complete legal-kit receipts and fails closed on count, identity, duplicate, malformed-record, or receipt drift.
- The versioned metric contract defines the source, denominator, and unknown-data policy for every catalog and request-time metric. Request diagnostics keep roster, newly added F2P identities, distinct availability, legal-package readiness, boss eligibility, role pools, candidate count, set diversity, archetypes, overlap, and unavailable observations separate.
- The accepted threshold-free baseline is `artifacts/evidence/feature_a_coverage_baseline.json`: 329/367 identities currently receive a high-value proposal attempt, while reviewed proof covers 10 primary-damage, 21 offensive-enablement, 12 zone, 16 mitigation, 7 recovery, 6 status-counterplay, 6 AF-support, 4 Pain/Poison, and 18 generic boss-counter identities.
- Proposal-state accounting records 148 proven, 5,103 unknown, 0 ambiguous, and 22 rejected atomic proposal instances alongside 2,208 separately untagged source facts and 0 explicitly proven absences. No unresolved or rejected state becomes character-level absence.
- Generated reports remain ignored under `artifacts/generated/`; no candidate scoring/search, supported-character subset, persisted schema, paid-provider behavior, production configuration, or Neo4j state changed.

Human checkpoint decision (approved 2026-09-14): the accepted Feature A artifact is the immutable before/baseline snapshot for Milestone 6, not the expected final distribution. Features C/D are expected to increase proven strategic coverage while preserving 367/367 legal-kit completeness and every evidence-state distinction. The initial D-G contract is:

- **D:** preserve 367/367 legal-kit completeness and attempt extraction for 367/367; prove at least 96 primary-damage, 48 offensive-enablement, 24 zone, 48 mitigation, 24 recovery, 24 status-counterplay, 24 AF-support, 24 Pain/Poison, and 48 boss-counter identities; prove at least 8 providers in every applicable element/type stratum; permit zero semantic-state collapses.
- **E:** 100% of measured requests emit the required funnel, diversity, denominator, and unknown-data diagnostics; identical inputs are deterministic; zero unavailable observations are silently treated as known.
- **F:** at least 8 independently established alternative-rich cases each retain at least 6 candidates, 3 unique six-character sets, 3 unique frontlines, and 2 materially differentiated archetypes, with maximum pairwise Jaccard similarity 0.714 and zero permutation-only sets, identical component vectors, or false archetype labels. Any constrained-case exemption needs evidence.
- **G:** 20/20 feasible cases produce at least one candidate passing all four H2 gates, 10/10 certified infeasible cases correctly produce zero, and 8/8 alternative-rich cases meet F, with zero illegal or unsupported output.

Feature B may recommend a numeric adjustment only when the committed boss corpus materially proves that a floor is too high, too low, or aimed at the wrong distribution. Any adjustment must be explicitly justified and documented before D; implementation difficulty is never grounds for relaxation. Unknown and untagged counts need not reach zero.

### Feature B: Boss-To-Capability Priority Matrix

Status: Completed on 2026-09-14.

Type and route: `research` via `contract-auditor -> feature-planner`.

Outcome: Map the approved thirty-boss mechanics to required, high-value, contextual, and unresolved counters, then rank capability families by boss impact and current catalog gaps.

Acceptance:

- **B-01:** Every priority traces to committed boss evidence and a defined capability or explicit gap.
- **B-02:** Required counters are separated from ranking-only advantages.
- **B-03:** Unknown boss mechanics remain unresolved rather than becoming inferred requirements.
- **B-04:** The resulting bounded priority matrix drives Feature C; it is not an exhaustive game-mechanics ontology.

Completion evidence:

- `artifacts/evidence/feature_b_boss_capability_priority_matrix.json` maps exactly 30 manifest identities in three 10-boss cohorts to checksum-resolved bounded sections and separates required, high-value, contextual, and unresolved classifications.
- Required counters are limited to explicit hard gates: affinity-safe damage affects all 30; seven bosses require multiple damage modes, seven impose prohibited-action/affinity constraints, six require multi-entity handling, four impose burst deadlines, and three impose hit/action thresholds.
- Ranking priorities are led by status counterplay (25 bosses), mitigation (15 high-value plus 3 contextual), reset resilience (14), fixed/percent-HP response (13 high-value plus 1 contextual), resistance manipulation (10 high-value plus 8 contextual), and enemy-buff control (10). These counts are boss-impact signals, not success probabilities or target coverage counts.
- Eight bosses retain unknown affinity profiles, and bounded source limitations or complex mechanics remain named unresolved gaps. Feature H fixtures are feasibility context only and do not create mechanic authority.
- Feature C receives three bounded priority bands tied to existing atomic capability IDs or explicit gaps. No runtime scoring/search, taxonomy, persisted shape, legal-kit receipt, provider, production configuration, or Neo4j state changed.
- The thirty-boss evidence materially changes extraction order but does not prove a defensible replacement for an approved identity-count floor. The initial D-G numeric contract therefore remains unchanged; AF and Pain/Poison retain deliberately low strategic-breadth floors without becoming boss-mandatory.

### Feature C: Full-Catalog High-Value Extraction

Status: Planned next after completed Feature B.

Type and route: `build` via `builder-executor -> tdd-loop`.

Outcome: Extend deterministic taxonomy/rules and proposal generation for the highest-value gaps, attempt extraction across all 367 forms/styles, and create bounded review queues.

Acceptance:

- **C-01:** Every canonical form/style receives an extraction attempt against the approved high-value family set.
- **C-02:** New rules have source-backed positive, misleading-negative, and regression evidence.
- **C-03:** Ambiguous and high-impact facts enter constrained review; low-value facts need not be manually reviewed.
- **C-04:** Existing reviews, negative fixtures, overrides, provenance, and replay determinism remain intact.
- **C-05:** No generated proposal becomes scoring or mandatory-coverage authority without the existing approved review path.

### Feature D: Selective Review, Materialization, And Coverage Closure

Status: Planned after Feature C.

Type and route: `build` via `builder-executor -> tdd-loop`, with required human review only for the bounded queues admitted by C.

Outcome: Resolve the strategically material review set, replay authoritative artifacts, and meet the evidence-based coverage thresholds approved after Feature A.

Acceptance:

- **D-01:** Reviewed proven facts materialize reproducibly with source and artifact-version provenance.
- **D-02:** Coverage meets the approved thresholds across applicable elements, physical/magic offense, offensive support, zone/setup, mitigation, recovery, status counterplay, AF support, Pain/Poison, and boss-counter evidence.
- **D-03:** Unknown and ambiguous evidence remains explicit and non-authoritative.
- **D-04:** All 367 data-complete forms/styles remain legally selectable; no supported-character subset is introduced.
- **D-05:** Rejected and negative fixtures remain effective against recurring false positives.

### Feature E: Search-Funnel And Diversity Diagnostics

Status: Planned after Feature D.

Type and route: `build` via `builder-executor -> tdd-loop`.

Outcome: Make catalog, roster, eligibility, pool, candidate, and uniqueness stages observable and diagnose cosmetic or collapsed candidate sets.

Acceptance:

- **E-01:** Request diagnostics expose the required funnel counts without equating 367 catalog identities with the effective roster or candidate pool.
- **E-02:** Candidate diagnostics detect permutation-only sets, identical score vectors, repeated character/frontline sets, and falsely differentiated archetype labels.
- **E-03:** Diagnostics distinguish a genuinely constrained roster from diversity lost through retrieval, proof coverage, pruning, packaging, allocation, or beam search.
- **E-04:** Metrics are deterministic for identical inputs and remain bounded in analyzer projections.

### Feature F: Evidence-Driven Candidate Diversity

Status: Planned after Feature E.

Type and route: `build` via `builder-executor -> tdd-loop`.

Outcome: Apply the smallest backend search, pruning, package, or scoring changes justified by E so strategically valid alternatives survive when available.

Acceptance:

- **F-01:** Controlled rosters with independently established alternatives produce the approved number or distribution of unique six-character/frontline sets.
- **F-02:** Archetype differences correspond to different strategic composition, packages, coverage, or win conditions rather than labels alone.
- **F-03:** A one-valid-team case is not padded with weaker, illegal, or incoherent alternatives.
- **F-04:** Legality, finite allocation, affinity rejection, dependency execution, closed-world IDs, deterministic ordering, beam bounds, fallback, and one-swap limits do not regress.
- **F-05:** No analyzer-side search expansion or additional analyzer call is introduced.

### Feature G: Controlled Quality Evaluation And Milestone Closure

Status: Planned after Feature F.

Type and route: `verification-only` via `tdd-loop`; use `release-manager-sync` only after implementation and verification evidence proves the milestone complete.

Outcome: Evaluate coverage and diversity across representative bosses and controlled rosters, apply the H2 gates, reconcile durable documentation/evidence, and close M6.

Acceptance:

- **G-01:** Deterministic coverage/diversity gates meet the evidence-based thresholds approved after A.
- **G-02:** Where controlled rosters support alternatives, candidate output contains meaningfully different legal sets and coherent archetypes; constrained cases explain why fewer candidates exist.
- **G-03:** H2 review finds plausible, evidence-backed candidates across the selected evaluation set using all four gates.
- **G-04:** Output contains no illegal or hallucinated IDs, unsupported capability claims, numeric win probability, guaranteed-clear language, or global-optimality claim.
- **G-05:** No paid call occurs unless deterministic gates pass and the owner separately authorizes the exact run. `reasoning=none`/4k is the initial DeepSeek baseline if such a run is approved.
- **G-06:** Tests, fixtures, scripts, generated reports, and handoff state pass promote-or-purge review; canonical docs and the living roadmap are accurate in the single completion commit.

## Milestone Exit Criteria

Milestone 6 completes only when:

- all 367 canonical forms/styles remain legal-kit complete and legally eligible when owned and data-complete;
- high-value capability extraction has been attempted across the full catalog;
- unknown, ambiguous, rejected, untagged, and proven-absence semantics remain distinct;
- evidence-based thresholds approved after Feature A are met across the strategic coverage dimensions relevant to the thirty-boss corpus;
- boss-eligible pools are large enough to exercise meaningful search where the effective roster and evidence permit;
- controlled alternative-rich rosters produce meaningfully different six-character/frontline sets and coherent archetypes;
- constrained cases are allowed to return fewer candidates with stage-accountable diagnostics;
- the H2 four-gate review supports strong, plausible, auditable recommendations without promising gameplay success;
- legality, deterministic bounds, closed-world IDs, allocation, fallback, token accounting, and the one-swap limit remain intact;
- no paid evaluation preceded deterministic readiness or occurred without separate authorization; and
- durable tests/evidence/documentation are promoted, generated material is purged or ignored, the milestone status is accurate, and each feature owns one focused completion commit.

## Deferred Questions

- Whether up to two backend-authorized swaps materially improves candidate quality without masking weak backend generation. Three or four swaps are not under consideration.
- Whether paid analyzer evaluation adds enough evidence to belong in M6 after deterministic gates pass; release qualification remains M8-owned.
- Whether capability families outside the boss-driven high-value set later earn inclusion.
- How catalog growth beyond the current canonical 367 should be admitted and versioned.
