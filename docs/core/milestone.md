# AnotherEdenAI Milestone 6 Plan

## Executive Summary

Status: Active as of 2026-09-14. Milestone 5 is closed through an approved scope correction that preserves its completed architecture and evaluation evidence while explicitly reassigning its uncompleted paid-provider and portfolio-safeguard work.

Milestone 6 expands recommendation-ready, high-value strategic evidence across all 367 canonical character forms/styles and improves meaningful candidate diversity. It does not attempt to model every mechanic, prove a globally optimal team, predict a clear, or replace conservative evidence review with inference.

Current checkpoint as of 2026-10-05: A-C and C1 are complete; C1.1 and C2 are technically implemented and verified, with human acceptance still pending. The 24-witness exploratory human review is complete. C2-R1's seven-witness evaluation boundary and aggregate-only paired BEFORE baseline are verified for its single feature commit; R2-R4 have not started. C2 remains non-authoritative and its exit checkpoint is not accepted. Feature D is blocked/unstarted. Preserve completed work and the D-G numeric contracts.

Approved continuation: C2-R1 evaluation freeze → C2-R2 ETL/source corrections → C2-R3 minimal shared mechanics → C2-R4 scoped occurrence corrections → C2-R5 frozen evaluation and small human verification → explicit C1.1/C2 acceptance → D → E → F → G. This is a bounded repair of C1.1/C2, not a restart or a new project design.

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
- structural evidence plus bounded combat-reference traversal, followed by an explicit source-semantic fidelity gate;
- scoped classification and a stratified, independently adjudicated comparison of extraction accuracy and review effort;
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

Status: Completed on 2026-09-14. Its accepted extraction baseline is preserved; the approved 2026-09-15 revisions insert C1/C1.1/C2 before the Feature D review handoff.

Type and route: `build` via `builder-executor -> tdd-loop`.

Outcome: Extend deterministic taxonomy/rules and proposal generation for the highest-value gaps, attempt extraction across all 367 forms/styles, and create bounded review queues.

Acceptance:

- **C-01:** Every canonical form/style receives an extraction attempt against the approved high-value family set.
- **C-02:** New rules have source-backed positive, misleading-negative, and regression evidence.
- **C-03:** Ambiguous and high-impact facts enter constrained review; low-value facts need not be manually reviewed.
- **C-04:** Existing reviews, negative fixtures, overrides, provenance, and replay determinism remain intact.
- **C-05:** No generated proposal becomes scoring or mandatory-coverage authority without the existing approved review path.

Completion evidence:

- `src/etl/capability_taxonomy.json` is versioned at 3.2.0 with 72 deterministic rules and 79 capability values. It retains the original 25 active Milestone 5 offensive families and adds 17 source-backed Feature C rules covering typed/scoped damage, multi-entity and multi-hit actions, enemy buff removal, resistance/stat directions, zone removal, fixed-damage response, burst windows, repeatable setup, and party status/speed support.
- `artifacts/evidence/feature_c_high_value_extraction.json` attempts the approved priority set across all 367 canonical identities and records 367/367 complete legal-kit receipts. The run covers 5,036 skill/passive facts and produces 8,341 high-value proposal instances: 68 proven from previously reviewed evidence, 8,267 unknown, 6 rejected, 0 ambiguous, 0 proven absent, and 0 untagged within the proposal set; 1,016 source facts remain separately untagged.
- All 17 new rules have durable source-backed positive, misleading-negative, and regression fixtures: 51 checks against stable catalog fact IDs and canonical source URLs. The report identifies all 17 new rule families as source-provable extraction coverage, while reviewed proof for those new rules remains empty by design until Feature D.
- P0/P1/P2 ordering comes directly from the accepted Feature B matrix. High-impact, explicit-ambiguous, recurring, and boss-acceptance-relevant queues are deterministic and capped at 45 rows each; no low-value exhaustive manual queue is created.
- Existing review decisions (323 IDs), gold/negative fixtures (12 IDs), taxonomy overrides (9), the immutable Feature A baseline fingerprint and metrics, proposal IDs, direction/target/availability/qualifier fields, and replay digest are preserved. A second identical pass produces the same proposal digest.
- Generated proposals are marked non-authoritative. No scoring, mandatory coverage, retrieval, search, packaging/allocation, persisted schema, provider/live refresh, production configuration, Neo4j state, or supported-character subset changed. Feature D must perform the bounded human review and normal approve/correct/reject/ambiguous materialization path.

### Feature C1: Structural Evidence And Bounded References

Status: Completed on 2026-09-15.

Type and route: `build` via `builder-executor -> tdd-loop`; refine the contained parser and traversal contract with `feature-planner` before execution.

Outcome: Preserve the combat-bearing source arrangement and relevant definition links in a separately versioned structural sidecar bound to existing source-fact IDs and pinned captures.

Scope: Character active/passive/SA and sidekick auto/charge/aura adapters share a small ordered block/token representation. Preserve section/tab context, list ancestry, table cells, meaningful line boundaries, inline links and icon identity. Definitions, conditions, results and exceptions are interpretations of source structure, not automatic meanings of HTML nesting. Include bounded mechanics-child resolution and small boss/equipment generalization fixtures.

Non-goals: Broad semantic classification, automatic approval, graph migration, full equipment/badge ingestion, new supported bosses, exhaustive ontology, formula execution, paid providers, frontend or production mutation.

Entry gate: Use the accepted C catalog and A/B/C evidence; reconcile source captures to catalog provenance and inventory relevant link topology before choosing traversal limits.

Acceptance:

- **C1-01:** Structural blocks and inline references retain order, parent context and traceable locations in checksum-identified sources. Unsupported/malformed structures produce explicit diagnostics; simple kits do not require artificial semantic nesting.
- **C1-02:** Sidecar bindings preserve existing fact and family identities, legacy descriptions, legal-kit output and 367/367 completeness. Structural coverage reports denominators and unresolved mappings by source kind; failed mappings never become absence.
- **C1-03:** Combat-bearing child references are retained and either resolved to captured definitions or explicitly unresolved. Canonical page deduplication preserves fragments and occurrence context; destination classification uses source content rather than URL spelling alone.
- **C1-04:** Traversal starts from admitted combat fields and follows only definition/restriction dependencies needed for interpretation. A deterministic frontier, visited set and explicit page/depth budgets bound work; exclusion, access failure and budget exhaustion are distinguishable. Audit actual topology before selecting numeric limits. Lore, galleries, acquisition walkthroughs and unrelated entity lists do not expand the frontier.
- **C1-05:** Fixtures cover Darunis/Denny, Iphi, Alma AS, Anabel ES, Shigure ES, Tetra AS and Kumos AS; named resource and Lunatic-family definitions require captured evidence. Existing manifest bosses and cached equipment/Grasta rows test shared structural handling. An-ki Dingir and Edaxian Zennon are supplemental witnesses only, pending capture, and do not enter the thirty-boss corpus.
- **C1-06:** Preserve entity ownership versus mechanic definitions, role/index discovery and strategy authority boundaries. Keep reusable authoritative fixtures and source identities; ignore generated sidecars and crawl/comparison output. No generated definition becomes capability authority.

Exit and human checkpoints: Traceable structural output, legacy-equivalence evidence and a documented traversal boundary are required before C1.1. Ask only for a material source conflict, a required definition that cannot be established, or a reopened architecture boundary. Unresolved lower-value links may remain explicit. One completed-feature commit contains durable implementation, fixtures and necessary documentation.

Completion evidence:

- The versioned `m6-c1-1.0.0` offline sidecar preserves ordered root/list/table blocks, ancestry, sections, line breaks, inline references, fragments, icon identities and checksum-qualified locations without assigning semantic meaning to nesting.
- The accepted 367-capture replay reconciles 367/367 complete legal-kit receipts and binds 4,863 of 5,036 existing facts without changing their IDs, families or legacy descriptions. The remaining 173 mappings (9 active, 164 passive) are explicit unknown diagnostics and never become absence.
- The finite captured topology was inventoried before traversal limits were selected: 5,634 structural units, 6,554 reference occurrences, 15,384 locally resolvable edges, observed connected extremes of depth 18 and 49 canonical definition pages, and maximum out-degree 99. Per-root work is therefore capped at depth 3, eight pages and 64 frontier additions; resolution, exclusion, missing capture, visited nodes and each budget exhaustion remain distinct.
- Permanent source-pinned fixtures cover Darunis, Denny, Iphi, Alma AS, Anabel ES, Shigure ES, Tetra AS and Kumos AS, including captured Blood Contract and Lunatic-family definitions. Shared table-cell handling is covered for an admitted boss witness plus cached equipment and Grasta rows. An-ki Dingir and Edaxian Zennon remain non-admitted pending-capture witnesses.
- The generated sidecar and crawl/comparison output remain ignored. Only reusable parsing/reporting code, compact fixtures and their source identities, the accepted digest/summary, operator guidance and regressions are retained. No capability approval, graph/schema, legal-kit, discovery/index, boss-strategy, provider, frontend or production behavior changed.

Post-completion audit disposition, approved 2026-09-15: C1 remains completed for ordered structural preservation, character-fact binding, bounded traversal and explicit unresolved states. Its fixture manifest and completion evidence do not establish semantic fidelity: separately authored fixture content was not proven equivalent to the pinned captures, the full sidecar replay contained character units but no production sidekick units, and real replay left required Iphi Lunatic and Anabel ES Prayer links unresolved. C1.1 supersedes the affected fixture-authority and semantic-completeness claims without rewriting the C1 implementation or historical commit.

### Feature C1.1: Source Fidelity And Authoritative Witnesses

Status: Technical implementation and verification complete on 2026-09-15. Human acceptance remains pending. C2 was subsequently implemented; the source/field issues found during its 24-witness review require bounded remediation before joint C1.1/C2 acceptance and Feature D.

Type and route: `build` via `builder-executor -> tdd-loop`; use `feature-planner` to finalize the stratified witness manifest and exact fidelity artifact contract, with a required read-only source-authority audit during verification.

Outcome: Establish a reproducible source-semantic record for every occurrence admitted to C2, with complete source identity, structure, effect text, scoped relationships and explicit child-definition status. Structural binding alone is not semantic success.

Scope: Reconcile checksum-pinned captures, selected page/section/record, parsed facts, catalog IDs and structural units across character active/passive/SA records and sidekick auto/charge/aura records. Preserve exact or reproducibly extracted source slices, resolve admitted local child aliases, and report semantic fidelity by dimension. Build a deterministic witness manifest organized by source/mechanic archetype rather than random character percentage.

Non-goals: Capability classification, proposal approval or materialization, broad ontology expansion, scoring/search changes, exact simulation, full equipment/BiS ingestion, new bosses, provider/frontend work, or incidental persisted-schema migration.

Acceptance:

- **C1.1-01:** Every admitted semantic record identifies the correct capture checksum, source page, section, source row/unit and real fact ID. Exact or reproducibly extracted source content is compared to the capture; a checksum attached to separately rewritten fixture prose is insufficient.
- **C1.1-02:** Fidelity is reported independently for source-record selection, effect completeness and order, parent/child condition attachment, actor, recipient, trigger, result, magnitude/parameter, duration/activation, element, attack type, mechanic/resource references and admitted child-definition resolution. Failed or inapplicable dimensions remain explicit and never count as semantic success.
- **C1.1-03:** Full automatic replay covers all 367 canonical character identities and separately reports every admitted sidekick record kind. It preserves 367/367 legal-kit completeness and reports structural parse coverage, fact binding, source identity, unresolved mappings, relevant-link and child-definition resolution, failures and deterministic replay. Human sampling never substitutes for this replay.
- **C1.1-04:** The seven known Iphi, Alma AS, Tetra AS, Darunis, Shigure ES, Kumos AS and Anabel ES failures become permanent development regressions with real source/fact identities. They prove their distinct defects but provide no independent generalization claim. The unsupported Darunis `Hunter's Fangs`/Wind expectation remains an explicit source conflict until an admitted source establishes it.
- **C1.1-05:** A deterministic stratified manifest selects approximately 20-30 additional development witnesses across materially different source and semantic structures. Selection is coverage-driven, may be inspected during implementation, and records both witness count and independently adjudicated effect/dependency occurrence count.
- **C1.1-06:** The manifest reserves approximately 20-25 additional held-out witnesses whose adjudicated oracle is isolated from rule design and tuning until evaluation. Where the corpus permits, every material archetype has both development and held-out representation. The combined target is roughly 50-60 witnesses including the seven regressions, but acceptance depends on demonstrated archetype coverage rather than that number or any catalog percentage.
- **C1.1-07:** Required archetypes include, where present: simple legacy skills; modern nested conditions; SA skills/passives and Stellar Burst conditions; counters; zones/Another Zone/Radical Zone; stacks and character resources; Lunatic variants; named child definitions; buffs/debuffs and resistance manipulation; status mechanics; healing/revival; Guard/Cover/Hold Ground; Pain/Poison; recipient eligibility and position/frontline conditions; multi-hit/multi-target attacks; and sidekick auto, charge and aura records. Missing or collapsed strata are reported before C2.
- **C1.1-08:** Only fidelity-passed occurrences may enter C2 as fully supported inputs. Unresolved source selection, identity, semantic attachment or required definition remains unknown/non-authoritative. No automatic approval, materialized capability, graph mutation or legal-kit change occurs.

Exit and human checkpoint: Technical completion supplies replay and witness evidence, not blanket semantic acceptance. Human acceptance remains pending where source conflicts, unresolved definitions or failed attachments remain. C2-R2 must correct the reviewed structured-field defects and C2-R1 must reconcile historical oracle labels before the C2-R5 joint checkpoint. Preserve the original implementation commit and source identities.

Completion evidence:

- `src/etl/source_fidelity_manifest.json` is a deterministic, non-percentage witness manifest with seven named regressions, 26 additional development witnesses, and 21 held-out witnesses. All required source/mechanic archetypes present in the accepted corpus are represented in both development and held-out strata, including separate sidekick auto, charge, and aura records.
- `tests/fixtures/source_fidelity/source_slice_manifest.json` binds all 54 witnesses to real source/fact IDs, checksum-qualified captures, source grid locations, and reproducible source-slice digests. Rewritten prose is not used as source authority. The separate sealed oracle records 40/30 independently adjudicated effect occurrences and 23/16 independently adjudicated dependency occurrences for development/held-out cohorts respectively.
- Full automatic replay covers 367/367 canonical character identities, 4,863 bound facts and 173 explicit unresolved mappings, with 367/367 structural parses and unchanged 367/367 complete legal-kit receipts. The separate sidekick replay covers 25 parsed sidekicks with 28 auto, 18 charge, and 41 aura records. Link, child-definition, source-selection, parse, and budget failures remain explicit.
- The seven regressions use real Iphi, Alma AS, Tetra AS, Darunis, Shigure ES, Kumos AS, and Anabel ES identities and are excluded from generalization evidence. Iphi Lunatic and Anabel Prayer remain unresolved child-definition states; Alma counter attachment remains a failed legacy regression; Darunis `Hunter's Fangs`/Wind remains an explicit source conflict; Tetra/Kumos sidekick record-kind coverage and the remaining named regressions are independently visible.
- Fidelity dimensions are reported separately for source-record selection, source identity, effect completeness/order, parent-child condition attachment, actor, recipient, trigger, result, magnitude/parameter, duration/activation, element, attack type, mechanic/resource references, and child-definition resolution. Only fully passed applicable dimensions are admitted as fully supported C2 inputs; no capability approval, materialization, graph/schema, legal-kit, scoring/search, provider, frontend, or production behavior changed.
- Technical evidence is `artifacts/evidence/feature_c1_1_source_fidelity.json`; generated replay output remains ignored. The full replay is deterministic with digest `8c2a3dbd645a78d084adc282ff9b77497b1eaa79b7a05b78471d0272401de7aa`. C2 subsequently ran; neither technical report resolves the outstanding human acceptance checkpoint.

### Feature C2: Scoped Classification And Review-Reduction Evaluation

Status: Initial implementation and verification complete on 2026-09-15. Exploratory human review complete at 24/54 witnesses. Remediation is planned below but not implemented; C2 remains non-authoritative and its checkpoint is not accepted. Feature D remains blocked/unstarted. Historical occurrence metrics do not establish semantic accuracy or review reduction.

Type and route: `build` via `builder-executor -> tdd-loop`; use `feature-planner` for the contained occurrence-identity and comparison contract, with a read-only compatibility audit where review meaning is disputed.

Outcome: Convert fidelity-passed source records into individually attributable effect, dependency, trigger, state and reference occurrences; generate boss-prioritized proposals from those occurrences; preserve review compatibility; and demonstrate whether the result reduces correction work before D.

Scope: Use the C1.1 fidelity contract for the existing boss-prioritized high-value families. Bind actor, recipient, target cardinality, condition, trigger, result, magnitude, duration/activation, element, attack type, source span and admitted definition support to separate attributable occurrences. Distinguish repeated effects, activation/state/dependency relationships, definitions and exceptions; preserve real fact identities, existing review authority and materialization compatibility through explicit occurrence mapping.

Non-goals: Automatic approval, one capability ID per named resource, taxonomy expansion without boss-driven evidence, formula simulation, scoring/search changes, broad equipment/boss extraction, or a schema migration merely to store intermediate evidence.

Acceptance:

- **C2-01:** Consume only C1.1 fidelity-passed records as fully supported inputs; preserve failed or unresolved records as explicit unknowns. Source-backed occurrences verify recipient/direction, actor, trigger, result, magnitude/duration/activation, element/type, nested conditions and dependency/state/result separation. Definitions support only the invoked scoped relationship and never grant unrelated or unconditional effects.
- **C2-02:** Existing IDs and decisions carry forward only to one source- and field-identical occurrence. Splits have explicit old-to-new mappings; approvals never silently fan out. Changed recipient, condition, timing, parameter, source meaning, alias or identity requires review. Preserve explicit clears, overrides, gold/negative fixtures and rejection protection; unresolved compatibility cannot silently alter authoritative output.
- **C2-03:** Compare the legacy flattened parser/classifier, C1 structural parsing without child resolution, and fidelity-checked structural parsing with admitted definitions and scoped classification from the same checksum-pinned raw records. Preserve committed C as historical context rather than an experimental oracle; source refresh remains a separate experiment.
- **C2-04:** The seven known regressions remain implementation-visible and are reported separately from generalization evidence. Development may use only the stratified development set. Held-out source identities and archetype assignments may be known for manifest integrity, but its independently adjudicated semantic oracle remains isolated until evaluation and cannot tune rules after unsealing without invalidating and replacing the held-out cohort.
- **C2-05:** Report development witness count, held-out witness count, development effect/dependency occurrence count, held-out effect/dependency occurrence count and archetype/family coverage. Report occurrence precision/recall; every C1.1 fidelity dimension; field, condition and relationship-attachment errors; correction actions; blinded human-review time per accepted occurrence; effort toward D floors; prior-review regressions; complete-catalog structural/link diagnostics; and deterministic digests.
- **C2-06:** Represent each executed damage event once as the authoritative `direct_damage` occurrence with its target cardinality. Derive/query-project `multi_entity_damage` when that cardinality proves multiple targets, retaining Feature B/boss compatibility without creating a second authoritative reviewed fact for the same event. Audit downstream consumers and preserve supported query behavior before removing or adapting any legacy materialization.
- **C2-07:** Distinguish automatically extracted, fully supported proposals from reviewed proven facts. Unknown counts, approximate witness targets and capped 45-row queues cannot establish correctness, generalization or review reduction. Demonstrate benefit on held-out occurrences without weakening safety gates; do not invent a percentage target.
- **C2-08:** Preserve 367/367 legal-kit completeness and every semantic state. Existing authoritative evidence is retained or explicitly reviewed for supersession. Separate historical baseline assertions from mutable current-review invariants in tests. Retain only reusable regressions, authoritative fixtures/manifests and accepted comparison evidence.

Exit and human checkpoint: Present measured benefit, source gaps, semantic migration and remaining review burden for acceptance before D. If benefit is not demonstrated, revisit rollout instead of declaring review reduction or relaxing coverage floors. One completed-feature commit contains the verified change and durable evaluation evidence.

Completion evidence:

- `src/etl/c2_scoped_classification.py` and `scripts/report_feature_c2.py` provide an offline, deterministic three-arm comparison over the same C1.1 checksum-pinned source records. Occurrences retain real fact identity, capture SHA, source span, semantic fields, explicit definition support and non-authoritative states; the taxonomy, review corpus, schema, graph, scoring and legal-kit paths are unchanged.
- `tests/fixtures/c2/occurrence_oracle.json` is a separately authored historical oracle. The original evaluation kept known regressions outside generalization evidence and reported 26 development witnesses / 40 effects / 23 dependencies separately from 21 held-out witnesses / 30 effects / 16 dependencies. Normal classification does not read that oracle, but the evaluation and its acceptance tests have already used it. Its `sealed` flag does not prove a fresh evaluation boundary.
- `artifacts/evidence/feature_c2_scoped_classification.json` records all three arms, explicit legacy-to-current compatibility decisions, field/condition/relationship error and correction-action fields, prior-review regression fields, per-occurrence review-time status, D-floor effort fields, full-catalog diagnostics, and deterministic digests. The source-fidelity replay remains 367/367 canonical identities with 367/367 legal-kit receipts and separate sidekick auto/charge/aura coverage.
- On the held-out occurrence oracle, the fidelity-checked arm records recall `0.9348` versus the legacy arm's `0.7609`, while precision is `0.3707` versus `0.6604`; this is measurable source-occurrence recall benefit with a precision trade-off, not proof of review reduction. All held-out review-time rows are `not_measured`, and the artifact's `review_reduction_claim` is false.
- `artifacts/evidence/feature_c2_human_review.md` records 24 corrections: seven known regressions, fourteen development witnesses and three originally held-out Gunce witnesses. At that exploratory-review checkpoint, twelve development and eighteen previously evaluated, unreviewed held-out witnesses remained. C2-R1 later retired the full prior validation cohort after source exposure could not be bounded. Recurring failures justify the bounded remediation below; the review did not change rules or grant authoritative capabilities.
- The historical evaluator matches fact/kind/ordinal occurrence IDs, with expected IDs often generated from counts. It does not require correct capability labels, recipients or attachments for a true positive. Preserve the `0.9348` recall / `0.3707` precision result as historical occurrence-count evidence; it cannot establish high-accuracy atomic capabilities or role taxonomy.

### Bounded C1.1/C2 Remediation — Approved 2026-10-04

Status: Planning revision explicitly approved by the owner on 2026-10-04. C2-R1 is the active authorized feature on the `tdd-loop` route; R2-R4 production fixes require its frozen evaluation boundary first. Plan approval does not accept C1.1/C2 or unblock D. Do not restart C1/C1.1/C2, resume sequential review of all 54 witnesses, implement D, or add backend/frontend/deployment work unrelated to these defects.

The 24 reviews establish recurring failure classes across skills, passives, Stellar/progression variants and sidekicks. They do not estimate catalog-wide error rates. The normal path remains pinned capture → faithful source record → atomic occurrences and typed relationships → non-authoritative capability proposals → explicit review → downstream role evidence. Fix the first layer that loses meaning; do not compensate for a parser defect with classifier exceptions.

For remediation, R1 supersedes the initial C1.1-05–07 and C2-04–05 cohort/isolation/evaluation contracts; their original counts remain historical evidence. All existing source-fidelity, review-authority and compatibility safety gates still apply.

#### Layer Ownership And Bounded Scope

| Layer | Admitted correction and evidence | Owner |
| --- | --- | --- |
| C1/C1.1 source/ETL/schema | Separate conditional Charge generation from consumption and action threshold; separate aura activation blocks from effect text; reconcile same-page child/href aliases; preserve Stellar Normal/Enhanced and base/Manifest/True Manifest source variants within one family. Tetra/Gunce, Anabel Prayer, Aldo/Anabel and Bertrand supply regressions. | C2-R2 |
| C2 occurrence/classification/decomposition | Split compound effects; bind actor, named recipient/direction, timing, duration, magnitude, hit count and conditions to their own effects; separate formulas/count rules, action replacement, resource operations and damage; retain typed activation/counter/mode/stack/replacement edges and resolved child IDs. The reviewed examples supply tests of general rules. | C2-R4 |
| Canonical/shared mechanic registry/resolution | Give reviewed recurring mechanics controlled identities and source-backed definitions; distinguish explicit links from allowlisted name/icon aliases; keep local parameters and character ownership separate from shared definitions. | C2-R3 |
| Evaluation/oracle | Reclassify exposed witnesses, freeze replacement coverage, correct development source/oracle conflicts and historical failure labels, replace ordinal-only semantic scoring with independently adjudicated atomic matching and dimension checks. | C2-R1, C2-R5 |
| Downstream role-scoring safety only if required | Verify candidates cannot reach authoritative scoring and ally-targeted harm cannot establish boss offense. `_proven_capabilities` filters review states/evidence but permits legacy bare capabilities without evidence; `_usable_primary` does not itself check recipient. Trace real callers before deciding whether a small guard is necessary. Parser/classifier repair remains upstream; no role weights, coverage closure or D materialization are admitted. | C2-R4 verification; narrow guard only for a demonstrated reachable gap |

Use source grammar, record structure and controlled data, never character/skill-name dispatch. Local names, parameters and relationships may be explicit source data. Do not turn unknown chance, target, formula range, unavailable definition or exception into a guessed value. Apply existing repository quality commands proportionally; installing tools or broad cleanup is outside this pass.

#### Minimal Shared Mechanic Contract

One small offline registry/resolver extends existing structural references and mechanics sources; it does not introduce a graph-wide ontology or a capability ID for each name. Freeze its admitted inventory from reviewed evidence during C2-R1; add only definitions needed by those regressions:

- support mechanisms: Prayer and Song;
- recurring statuses/modifiers: Break, Hold Ground, Rage/taunt, Barrier Pierce, Kaleido, and Skill Hit Count modification;
- Lunatic family and reviewed variants, including Charge and Mind's Eye; Copy/Attack Again identities where required by reviewed counting rules;
- Another Zone and the reviewed named Stance/Zone identities, with only the source-backed distinctions needed for activation and conditions;
- separate identities for status-ailment cleansing and ordinary-debuff removal, and a Sidekick Charge resource distinct from `Lunatic - Charge`.

Registry entries contain a stable mechanic ID/class, approved scoped aliases or URLs/icons, source capture/section/span and definition-resolution status. Reuse one global definition across invocations. A recognized name without an admitted definition may have an identity but remains unresolved; identity never proves its rules. Same spelling in different families, especially Charge, requires contextual disambiguation. Explicit href resolution preserves its target provenance; controlled name/icon resolution records the matched alias and basis, and never scans arbitrary emphasized/bold/plain text into mechanics or silently contradicts a link.

Parent occurrences retain their local trigger, recipient, element, duration, magnitude, condition, probability and cost. Character-specific Counters, modes, Prayer/Song payloads and stacks retain local source-fact IDs connected by typed relations, rather than becoming universal mechanics. Shared definitions are not character-owned skills and cannot grant every definition effect to each invoker. General documentation links remain documentation references. Preserve operation distinctions such as activates, grants, consumes, requires, scales-with, awakens and replaces; implement only relations exercised by the reviewed chains.

#### C2-R1: Freeze Evaluation And Repair The Oracle Contract

Type and route: `evidence-remediation` via `tdd-loop`. Entry: human approval of this planning revision. Exit: a checksum-pinned boundary and independent evaluation contract frozen before R2-R4 implementation. One completed-feature commit owns the manifest, evaluator/oracle corrections, isolation checks and documentation.

- **C2-R1-01:** Keep all seven known regressions separate from generalization evidence. Treat the fourteen reviewed development witnesses and three reviewed Gunce witnesses as development/regression evidence; retain the other twelve development witnesses for development coverage. **Execution evidence:** the seven known regressions remain a distinct cohort, and all reviewed Gunce identities are in development. The final manifest records 57 development witnesses, including all prior validation identities retired after exposure could not be bounded and all interim replacement candidates.
- **C2-R1-02:** Protect the eighteen unreviewed witness IDs listed in the human-review closure from further semantic inspection, per-witness result access or tuning. They are previously evaluated validation, not pristine unseen evidence. Audit exposure using identities, cohort metadata and access history only, including overlap with reviewed parent/child/source slices. Reclassify any additional exposed slices before freezing; do not inspect their semantics to justify retaining them. **Execution disposition:** an interim source excerpt surfaced and a later unscoped search returned truncated content-bearing output, so the exposed subset could not be bounded. All identities from the original validation cohort were retired to development; none is represented as protected. The seven owner-confirmed fresh identities in the current freeze replace that cohort for prospective validation.
- **C2-R1-03:** Select fresh replacement witnesses from pinned captures, at minimum restoring the removed sidekick auto/charge/aura coverage. Add only the fresh witnesses needed to fill demonstrated gaps. Prefer unreviewed source families/entities and record shared-definition overlap. Freeze exact IDs, capture/slice checksums, strata, expected atomic matching rules, exclusions and the independent oracle hash before production fixes. An evaluation owner outside remediation rule design holds the fresh semantic oracle and adjudicates from pinned sources without classifier output; if that separation is unavailable, stop at the evaluation-boundary checkpoint rather than inventing independence. **Execution evidence:** the seven accepted replacement identities, record types, source fact IDs/paths, capture/slice hashes, coverage tags, and overlap audit are in the metadata-only freeze. Re-resolution verified all 64 development/fresh capture hashes, source-slice hashes, and locations; it found zero exact capture or source-slice overlaps between the seven fresh records and development. It recomputed 72 fresh/development shared-reference pairs and four within-cohort pairs. The owner-approved policy allows shared mechanics/references, so these do not disqualify distinct captures/slices. Radical Zone is `shared_mechanic`, not passive; Yuna — Turn Start Status Immunity fills the passive stratum. Thillelille (Another Style) — Battle Start Koakh Stacking remains separately recorded as an unscored initial-resource taxonomy gap. The owner completed the independent seven-witness source-only adjudication and supplied the sealed-oracle digest, now frozen in the manifest.
- **C2-R1-04:** Demonstrate protected validation coverage for simple skill, complex multi-effect skill, passive, Stellar/state-driven variant, sidekick auto, charge and aura, shared mechanic, parent/child relation, and condition/state-heavy mechanic. One witness may cover several strata; report gaps and definition dependencies rather than assuming the remaining eighteen are sufficient. Report original validation and fresh replacement results separately as well as combined. Reserve the R5 human-sample identities now and keep them out of tuning; unused development witnesses may be reserved without relabeling them independent held-out evidence. **Execution disposition:** the original cohort has only its historical ordinal diagnostic and no corrected independent semantic baseline. R1 reports the fresh semantic baseline separately; an original-plus-fresh combined semantic result is unavailable and must not be synthesized from incomparable evidence. All seven accepted fresh identities are reserved for R5. The ten required strata are covered; `stack_or_resource_state` is optional diagnostic metadata for Andante only and does not expand the acceptance floor.
- **C2-R1-05:** Reconcile development oracles against complete source spans and human decisions: Hunter Shoot has attack plus resistance reduction; Alma's historical attachment failure is not proof that its current link resolver fails; passing text completeness does not establish faithful Charge/aura/variant fields. Retain genuine unresolved Iphi/Prayer/source conflicts until evidence resolves them. Never rewrite a protected oracle to fit remediation output.
- **C2-R1-06:** Define semantic true positives by independent atomic mechanic/capability identity, operation and scoped source anchor, using one-to-one matching rather than generated ordinal IDs. Report capability-label precision/recall separately from effect/dependency occurrence metrics; generic `scoped_effect` is not a correct capability label. Measure field/relationship correctness separately, including unresolved fidelity inputs in coverage denominators. Keep the old occurrence metric as a historical diagnostic. Run the pre-remediation implementation under the same corrected evaluator for a paired baseline; the evaluation owner seals protected results without exposing them to tuning. Ordinary remediation tests/reports must not open protected oracles or semantic rows; existing `include_held_out=True` tests need isolation. Full-catalog integrity replay may process protected sources automatically, but exposes only aggregate structural diagnostics during tuning. Once unsealed, any subsequent access invalidates that validation cohort and requires replacement. **Execution evidence:** the versioned evaluator and aggregate-only runner produced `artifacts/evidence/feature_c2_pre_remediation_baseline.json` against the final frozen manifest and owner-held digest. The artifact contains only aggregate results for the three C2 arms, with no per-witness rows or semantic values.

Current R1 execution boundary: `artifacts/evidence/feature_c2_evaluation_freeze.json` is the metadata-only cohort manifest. It separates seven known regressions, 57 development witnesses, and seven fresh protected witnesses. The 57 development witnesses include the reviewed Gunce records and every identity from the prior validation cohort; those identities were conservatively retired after source exposure could not be bounded. No member of the original eighteen-witness unreviewed validation subset is represented as protected. The seven fresh records use distinct pinned captures and source slices, cover all ten required strata, and are reserved for the R5 human sample. Radical Zone covers `shared_mechanic` rather than `passive`; Yuna — Turn Start Status Immunity covers `passive`. `stack_or_resource_state` is optional diagnostic metadata for Andante only. Thillelille (Another Style) — Battle Start Koakh Stacking remains a separately recorded, unscored taxonomy gap. The owner completed source-only adjudication without classifier output; the owner-controlled atomic oracle remains outside the repository and conversation, and only its digest is frozen in the manifest. The aggregate-only BEFORE baseline is produced and committed with R1. C2-R1 is complete after its single feature commit; R2-R4 remain unstarted.

Isolation limitation: the repository cannot prevent a process running as the same OS user from opening the owner's private oracle. The private directory/file permissions and external location reduce accidental access but are not a same-user security boundary. The pinned source captures also remain in the repository, and the committed manifest exposes their paths and hashes to preserve cohort identity; R1 cannot technically hide those source bytes from a workspace reader. Ordinary reports/tests are restricted to development data, and the owner-run baseline rejects an oracle path inside the repository and returns aggregate-only metrics. R2-R4 must not open the fresh source locations, access the owner path, or run the owner evaluator; the human owner runs aggregate evaluation at R5 after remediation is frozen. Any earlier access invalidates the fresh cohort.

#### C2-R2: Correct Source Fields And Variant Identity

Type and route: `build` via `builder-executor -> tdd-loop`; contained contract refinement with `feature-planner`, read-only `contract-auditor` before changing source identity/review compatibility or persisted contracts. Entry: R1 freeze. Exit: source-backed parser/model corrections and fidelity regressions, in one completed-feature commit.

- **C2-R2-01:** Parse gain, consumption and action-availability threshold independently, with units, owner, source and effect-local conditions. Conditional `+1 Charge` is never `charge_cost: 1`. Preserve real 5/8-Charge consumption; do not infer threshold from cost or create a new requirement for an auto action. Aura activation uses source block boundaries rather than a keyword list that swallows effect text; `aura → activation condition → effects` admits arbitrary source-supported conditions without invented category limits.
- **C2-R2-02:** Resolve captured same-page children against explicit href aliases without inventing missing definitions. Preserve family identity while making source variants addressable through an explicit variant key: Stellar Normal/Enhanced, base/Manifest/True Manifest, and state-selected replacement forms. Retain source-specific parameters and availability requirements; do not treat replacement forms as independently owned/equipable skills. Distinguish progression unlock from ongoing equipment requirements. Enhanced-as-runtime-default for awakened characters without board allocation is recorded for later downstream admission, not implemented here.
- **C2-R2-03:** Add source-backed positive and misleading-negative regressions for every reviewed structured defect, including field separation and variant collisions. Retain descriptions, source checksums and mappings to existing fact/family IDs; changed semantics require explicit re-review, never approval fan-out. Verify deterministic full-catalog and sidekick replay and 367/367 legal-kit completeness. A corrected parsed field must not silently change reviewed materialization. Prefer the existing offline evidence boundary; any necessary persisted-shape migration requires separate explicit admission and schema documentation before execution.

#### C2-R3: Add Controlled Shared Mechanic Resolution

Type and route: `build` via `builder-executor -> tdd-loop`, with `feature-planner` for the bounded registry contract. Entry: R2 source identity/alias corrections. Exit: the minimal registry contract above is exercised by reviewed examples with ambiguity, unknown-name and unavailable-definition negatives. One completed-feature commit owns implementation, source mappings and regressions.

- **C2-R3-01:** Resolve explicit links and allowlisted unlinked names/icons with distinct provenance. Deduplicate shared definitions, keep local payloads on parents, separate Sidekick Charge from Lunatic Charge, and retain unresolved/ambiguous outcomes.
- **C2-R3-02:** Preserve source ownership: global definitions such as Another Zone do not become the hosting character's direct damage or capability. No broad text matcher, automatic capability approval, whole-rulebook ingestion or new graph labels are admitted.

#### C2-R4: Repair Atomic Occurrences And Relationship Handoff

Type and route: `build` via `builder-executor -> tdd-loop`, with `feature-planner` for contained decomposition/relationship ambiguity and `contract-auditor` for changed review semantics. Entry: R2/R3 contracts. Exit: general source-backed rules fix the reviewed high-impact classes without character-specific dispatch. One completed-feature commit includes any demonstrably necessary narrow scoring guard.

- **C2-R4-01:** Decompose independent attack, buff/debuff, recovery/revive, cleansing, resource and status effects; attach each magnitude, duration, hit count, probability, recipient and condition locally. Preserve true action-level timing separately. Distinguish `(XXL x5)` attack hits from potency multipliers; formula/counting inputs are metadata, not damage or activation requirements. Action-slot replacement, hit-count buffs, stack grants and shared-definition clauses are not immediate attacks. Preserve unknown fields explicitly. Map to existing taxonomy IDs only when their meaning matches; unsupported effects such as maximum-stat increases remain typed non-authoritative semantic facts and reported capability gaps. Any new capability value requires demonstrated boss-priority need and explicit contained admission, not a guessed label or character role.
- **C2-R4-02:** Preserve typed edges with resolved target fact/mechanic IDs and edge-local conditions/timing. Cover Counter → stack/passive, mode → skill replacement, Prayer/Song local branches, and parent → Echo → end-of-turn child activation/consumption. Do not flatten child behavior into unconditional parent effects or double-count repeated consumption. Conditional branches and replacements stay in one conceptual family; mutually exclusive modes remain explicit where supported.
- **C2-R4-03:** One executed damage event has one `direct_damage` occurrence; multi-target projection remains derived/query-compatible. Existing approvals carry forward only through one source- and semantic-identical occurrence. Splits, changed aliases/variants/recipients/conditions/parameters require mapping and re-review. Preserve explicit clears, rejection protection, overrides and unique prior-review regression behavior.
- **C2-R4-04:** Keep all new occurrences non-authoritative. Verify real input/materialization/scoring boundaries for candidates, unknowns, ally harm, child definitions, placement and progression. Add a small fail-closed guard only if a supported caller can violate the reviewed-proven or enemy-offense boundary; otherwise preserve scoring code. Do not tune role dimensions, weights, search, D coverage or runtime variant defaults.

#### C2-R5: Evaluate Once, Sample Human Corrections, Stop For Acceptance

Type and route: `verification-only` via `tdd-loop`, with required human verification and acceptance. Entry: R2-R4 development regressions pass and implementation is frozen. Exit: a single feature commit contains durable comparison evidence, any reusable verification coverage and accurate checkpoint status; unresolved acceptance remains pending rather than being marked passed.

- **C2-R5-01:** Run known/development regressions first, then let the evaluation owner unseal the protected cohort once. Compare pre/post remediation plus the legacy/structural-only/fidelity-checked arms on identical captures and the same corrected oracle. Report TP/FP/FN, precision/recall, witness and independently adjudicated atomic counts, family/stratum results, unknown/fidelity-excluded inputs and coverage, prior-review compatibility, full-catalog diagnostics and deterministic digests. Historical `0.9348`/`0.3707` metrics remain separately labeled; changed cohorts/oracles cannot be compared as if denominators were unchanged.
- **C2-R5-02:** Score decomposition, actor/recipient/direction, effect-local conditions, timing, magnitude/duration, hit count, formula/counting classification, parent/child edges, canonical resolution, ETL fields, variant identity and sidekick placement/resource semantics against independent expected fields. Report pass/fail/unknown/inapplicable denominators; prefilled oracle error counts are not measured implementation checks. Occurrence recall alone cannot establish high-accuracy capabilities or role taxonomy.
- **C2-R5-03:** Use the R1-reserved small post-fix human sample: target 8-10 witnesses covering the ten required strata with overlap and at least one example of each reviewed high-impact failure class. Use reserved, unreviewed development or fresh witnesses; describe development samples honestly. Review complete source spans and exact atomic corrections. Record blinded per-accepted-occurrence time only if conducting a timing study; otherwise mark review time unmeasured and make no review-reduction claim. Do not restart exhaustive 54-witness review.
- **C2-R5-04:** Present recall retention, precision gain, semantic/field/relationship failures, correction burden and unresolved mechanics for explicit joint C1.1/C2 acceptance. This checkpoint may accept semantic remediation without claiming timed review reduction; any such disposition must be recorded explicitly. Plan approval, passing tests or a verification commit never accepts C2 or authorizes D. A failed result returns a bounded diagnosis; no tuning against the unsealed cohort.

#### Remediation Exit Criteria And Retention

- Preserve recall on the paired, corrected semantic oracle: no aggregate recall loss relative to its pre-remediation run and no loss of a previously detected high-impact supported capability. Treat the historical approximately `0.9348` recall as context, not a transferable target when the oracle or cohort changes. Report any lost detections explicitly; a material loss fails the checkpoint.
- Precision must improve meaningfully: fewer semantic false positives and fewer required corrections across multiple predeclared recurring failure classes at retained recall, not an isolated ordinal/count change or suppression of difficult inputs. Freeze the matching/materiality rule in R1 before fixes. No defensible absolute percentage follows from the 24 exploratory witnesses; do not impose 95% or claim statistical generalization from this small cohort.
- Every reviewed high-impact failure class and known structured ETL defect has source-backed positive and misleading-negative regression coverage, with zero known high-impact regressions. Genuine source/definition gaps remain unknown and visible rather than requiring invented resolutions to make tests green.
- Preserve 367/367 legal-kit completeness and deterministic character/sidekick replay; report parsing, binding, source identity, child resolution, unresolved mappings and separate auto/charge/aura denominators. Unreviewed candidates contribute zero authoritative role or mandatory-coverage evidence.
- Keep the existing production taxonomy/review/materialization path as the authoritative path until explicit acceptance and D admission. The corrected offline occurrence path becomes canonical for proposals/evaluation; retire superseded offline helpers/tests within their owning repair. Keep legacy/structural-only comparison arms for the supported experiment, not as alternative production authority. Any temporary review-identity adapter needs an explicit exit condition and D removal owner.
- Retain independent source fixtures, frozen cohort metadata, reusable regressions and accepted comparison summaries; preserve historical evidence in its original commit. Generated replays, timing scratch work and handoffs remain ignored. Commit once per genuinely completed remediation feature, with no workflow-transition commits.

### Feature D: Selective Review, Materialization, And Coverage Closure

Status: Blocked/unstarted. Starts only after C2-R1–R5 and explicit human acceptance of the remediated C1.1/C2 fidelity, compatibility, evaluation and remaining review burden. Approval of the remediation plan alone does not unblock D.

Type and route: `build` via `builder-executor -> tdd-loop`, with required human review for the bounded strategically material queues produced through C2.

Outcome: Resolve the fidelity-passed, structurally grounded material review set, including changed-semantic occurrences, replay authoritative artifacts, and meet the evidence-based coverage thresholds approved after Feature A.

Acceptance:

- **D-01:** Reviewed proven facts materialize reproducibly with source and artifact-version provenance.
- **D-02:** Coverage meets the approved thresholds across applicable elements, physical/magic offense, offensive support, zone/setup, mitigation, recovery, status counterplay, AF support, Pain/Poison, and boss-counter evidence.
- **D-03:** Unknown and ambiguous evidence remains explicit and non-authoritative.
- **D-04:** All 367 data-complete forms/styles remain legally selectable; no supported-character subset is introduced.
- **D-05:** Rejected and negative fixtures remain effective against recurring false positives.
- **D-06:** Materialized evidence traces to the admitted source spans, definition captures and extraction versions. Prior approvals survive only through verified unchanged meaning or explicit re-review; unresolved links or interpretations grant no authority. Persisted-shape changes, if actually necessary, require explicit schema admission rather than an incidental migration.

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
- C1's structural guarantees remain valid, C1.1 establishes source-semantic fidelity with stratified witnesses plus deterministic full-catalog replay, and C2's held-out classification benefit, compatibility evidence and remaining review burden are accepted before D;
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

- Comprehensive equipment/badge effect ingestion, broad boss admission, a globally complete mechanic ontology and exact formula execution remain outside C1.1/C2. Supplemental source witnesses do not expand supported entity scope.
- Whether any future automatic approval policy is defensible remains outside M6; structure alone never authorizes a proposal.

- Whether up to two backend-authorized swaps materially improves candidate quality without masking weak backend generation. Three or four swaps are not under consideration.
- Whether paid analyzer evaluation adds enough evidence to belong in M6 after deterministic gates pass; release qualification remains M8-owned.
- Whether capability families outside the boss-driven high-value set later earn inclusion.
- How catalog growth beyond the current canonical 367 should be admitted and versioned.
