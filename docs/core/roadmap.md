# AnotherEdenAI Roadmap

## Executive Summary

AnotherEdenAI is a portfolio project demonstrating production-minded AI engineering in a complex game-recommendation domain. It scrapes and replays Another Eden evidence into Neo4j, deterministically constructs legal boss-aware lineup candidates from a player's available roster, and lets a bounded LLM rank, refine, and explain only supplied candidates.

The intended product claim is:

> AnotherEdenAI generates legal, boss-aware, evidence-backed lineup candidates from the player's available roster and explains why they are strategically plausible.

The recommender is a bounded, auditable navigation system. It does not promise the globally best party, a guaranteed clear, an exact battle outcome, or a numeric win probability.

The program keeps two product paths separate:

- Production recommendation uses typed deterministic retrieval, legal-kit and capability evidence, backend filtering/scoring, bounded candidate generation, compact LLM refinement, and deterministic validation.
- Exploratory GraphRAG may use dynamic planning and generated Cypher for flexible graph questions, but it does not own production lineup legality or candidate search.

## Program Objectives And Success Criteria

- Maintain replayable, auditable ETL and governed recommendation evidence.
- Keep all canonical character forms/styles legally available when owned and data-complete.
- Distinguish legal-kit completeness from conservative capability proof.
- Prevent hallucinated characters, illegal skills, unsupported mechanics, and impossible item allocations.
- Keep retrieval, hard filters, contextual scoring, package construction, candidate search, and final validation deterministic.
- Reserve the LLM for bounded ranking, authorized refinement, and explanation over closed-world candidates.
- Produce strong, plausible, strategically coherent alternatives when the available roster and evidence genuinely support them.
- Preserve explicit unknown and ambiguous states rather than treating missing proof as absence.
- Bound provider calls, tokens, cost, correction, and degradation.
- Present the architecture and evidence clearly in a portfolio frontend and controllable deployment.

Program success does not require exhaustive combat modeling, a full simulator, global optimization, exact damage/turn calculation, or guaranteed gameplay success.

## Current Active Milestone

Milestone 7, Frontend Portfolio Experience, is the active implementation workstream in [milestone.md](milestone.md). On 2026-10-22 the owner explicitly approved extending the completed RR-A/RR-B integration sequencing exception to bounded M7 frontend work. The plan reuses the existing engine, request/job/SSE contract and result cards; implementation starts in a separate chat with M7-1.

Milestone 6 is paused and incomplete. Its P2/P3/H2 gates remain unmet and unchanged; their exact remaining obligations and evidence are retained in the M6 section below. M7 admission bypasses the accepted-M6-baseline dependency for frontend work only. It does not accept M6, authorize conditional P4, qualify a provider, prove live graph freshness or relax M8 release gates. Further curation, ranking development and H2 evaluation remain paused.

M5 closed on 2026-09-14 under its approved scope correction. C2/C2.1 failed semantic acceptance and is stopped; no new classifier repair or held-out cohort is admitted. All 367 owned, data-complete legal forms and the thirty-boss corpus remain supported foundations. The twenty normal-form/two-boss pilot bounds evidence, not legal ownership eligibility.

## Research And Planning Sources

Detailed source identities, historical decisions, supersessions, and unresolved research gaps live in `docs/core/planning-sources.md`. The repository's versioned taxonomy, reviews, gold/negative fixtures, kit catalog, superboss manifest/captures, H acceptance fixtures, and implementation tests remain the authoritative implementation evidence.

## Ordered Major Milestones

### Milestone 1: GraphRAG Foundation

Status: Completed.

Purpose:

- Establish the initial Neo4j graph, ETL pipeline, LangGraph workflow, and FastAPI/HTMX streaming UI.

Key results:

- Character, Trait, Grasta, and Ore graph foundations.
- Initial PLAN -> GENERATE_CYPHER -> VALIDATE -> ANALYZE -> FORMAT workflow.
- Roster-constrained query path and streaming UI.

### Milestone 2: Combat Graph Expansion

Status: Partially completed; its required recommendation prerequisites were delivered through later milestones.

Purpose:

- Expand character data from identity and Grasta compatibility into active skill and passive combat facts.

Key results:

- Cached/resumable ETL foundation.
- Character skills, passives, and Stellar Awakening gating.
- Schema and ETL guidance supporting replay.

### Milestone 3: RAG-Ready ETL Data Coverage

Status: Completed.

Purpose:

- Add factual data needed for legal boss-aware recommendation.

Key results:

- Sidekick identity, skills, auras, and official associations.
- Curated superboss affinity/mechanics facts and MechanicReference corpus.
- Preserved Grasta/Ore facts, baseline equipment context, manifests, and schema assertions.

### Milestone 4: AI Lineup Recommendation Intelligence

Status: Completed.

Purpose:

- Establish the first structured, legal six-hero plus optional sidekick recommendation contract.

Key results:

- Structured roster ownership and Stellar Awakening state.
- Sidekick and skill-slot legality.
- Boss-aware top-three recommendation contract and final legality/factuality gate.
- Compact and expandable result UI.

### Milestone 5: Deterministic Recommendation Engine, Evaluation, And Cost Control

Status: Completed on 2026-09-14 through an approved scope correction after Feature H2.

Purpose:

- Establish a production-safe architecture where deterministic backend logic owns legal retrieval, capability-grounded scoring, package generation, bounded candidate search, legality, validation, fallback, and cost control, while the LLM performs only bounded ranking, refinement, and explanation over supplied legal candidates.

Completed evidence:

- typed production retrieval with no PLAN, generated-Cypher, or retrieval-validation LLM dependency;
- complete legal-kit materialization receipts for all 367 canonical forms/styles;
- versioned capability taxonomy, review artifacts, negative fixtures, curated overrides, and reproducible materialization;
- contextual role scoring from proven facts and legal untagged package fillers with zero capability credit;
- boss-aware skill/build packages, finite item allocation, hard affinity/legality filters, and bounded package-first beam search;
- full backend candidates, compact analyzer projections, closed-world candidate IDs, and at most one backend-authorized swap;
- deterministic validation, one fragment-only correction, degraded fallback, and partial/zero-candidate contracts;
- token, usage, cost, latency, served-model, validation, and failure-accounting structures;
- a committed thirty-boss corpus with twenty witnessed feasible and ten certified infeasible deterministic acceptance cases plus a separate fixed-roster stress suite;
- H1's provisional finding that DeepSeek `reasoning=none`/4k was cheaper and more reliable than `reasoning=low`/8k in the tested scenarios, without changing production settings; and
- H2's human-readable damage-affinity, boss-counter, team-coherence, and setup-executability review framework.

Closure boundary:

- M5 proves architecture, legality, determinism, auditability, bounded behavior, and cost-control mechanisms.
- It does not prove globally optimal lineup generation, guaranteed boss clears, complete strategic interpretation of every skill/passive, exhaustive mechanics coverage, exact turn/damage simulation, or complete best-in-slot optimization.
- Candidate diversity observed in H1/H2 was constrained by a six-character roster plus permanent F2P augmentation, yielding twelve distinct available characters; different candidate IDs/archetypes could still reuse the same six-character set. This is evidence for M6, not an architecture failure.

Approved incomplete-work disposition:

- Former Feature I was not marked complete. Capability/untagged-evidence diagnostics move to M6; frontend presentation moves to M7; portfolio registration, quota, global-spend, kill-switch, and release safeguards move to M8.
- Former paid H-04/H-05/H-07 qualification for all admitted OpenRouter models and the ordered fallback chain was not marked complete. Release-time qualification moves to M8.
- Paid evaluation remains separately authorized and is not required merely to preserve the M5 architecture result.

Historical Features A-H, corrections C6/C6.1/D2/E2/F2/G1.1, and their identifiers remain unchanged in commits, tests, schema, architecture, guides, and planning sources.

### Milestone 6: Reviewed-Knowledge Recommendation Pilot

Status: Paused and incomplete under the owner-approved 2026-10-22 M7 sequencing extension. P1 is complete; P2/P3 acceptance and H2 usefulness remain unmet. This is a change of active workstream, not milestone closure or gate supersession.

Purpose: prove whether trustworthy manual knowledge lets the existing deterministic engine produce useful, explainable, boss-aware legal teams.

Preserved foundations and evidence:

- A-C coverage/extraction-attempt evidence, C1 structure and C1.1 technical source fidelity; 367 legal kits, thirty-boss provenance, reviewed capability materialization and existing scoring/packages/search/allocation/validation/fallback.
- C2.1 failed final validation: effects F1 30.2%, dependencies 0%, combined labels 23.0%, anchors 9/36 and conditions 0/18. It remains unsuccessful/stopped, not jointly accepted. Original C2 continuation and D-G completion obligations were explicitly superseded by the 2026-10-20 reset, not passed. No Test #5, new classifier architecture or reuse of consumed cohorts as fresh validation.
- Frozen report: `artifacts/evidence/feature_c2_final_heldout_report_20261020.json`, SHA-256 `671d208ece253f12444c7d2e22cf0f9ff799e305eb6a3b1ebf819ec622223e54`; source/oracle custody and replay limits: `artifacts/evidence/feature_c2_final_heldout_retention_20261020.json`. Preserve exact source identities, consumed-cohort status and recorded 7 classifier + 1 adapter + 1 evaluator calls; never rerun for preservation.
- `tests/fixtures/m6_p2/pilot_scenarios.json` pins the twenty normal forms, six investigation seeds, boss captures, reviewed source facts and unresolved adjudications. `src/etl/superboss_manifest.json`, the bounded corpus, independent `tests/fixtures/superbosses/live_expected.json`, kit catalog, review batches/overrides and runtime tests remain authority for their respective facts. Scenario seeds are not quality/inadequacy oracles.
- The complete M6 contract, acceptance, retirement dispositions and diagnostic replay details remain recoverable at `git show 49a0d62:docs/core/milestone.md`; current pilot validation instructions remain in [recommendation-validation.md](../guides/recommendation-validation.md#13-reviewed-knowledge-pilot-acceptance). Resume from these sources plus current implementation; do not invent a second active milestone file.

Current feature dispositions:

1. P1 scope reset and immutable failed-experiment preservation is complete.
2. P2 reviewed facts, source-pinned inputs, failed-classifier retirement and manifest-backed source-count assertions are implemented. Full scenario authority and acceptance are not established. Keep source-fidelity/structural evidence, legal kits, taxonomy/reviews/overrides/materialization, independent semantic evaluator and unique source regressions. Do not restore obsolete C2 classifier/report/resolver paths or blanket-delete C2-named supported review artifacts. Historical caches cannot be purged without the source-retention inventory.
3. P3 diagnostic replays and contained affinity, flexible-role and placement-support corrections are implemented. Later replays produced ten candidates in each of the six investigation seeds; this supersedes earlier zero-candidate observations as current candidate-generation evidence, not as strategic acceptance. Primary-damage coverage, heuristic points and label diversity do not prove H2 success. Selected-skill review diagnostics and frontline/reserve-after-switch scopes remain supported.
4. P4 bounded analyzer/end-to-end evaluation remains conditional: deterministic gate B must pass and the owner must separately authorize an exact model/run/cost envelope. Existing two-call/one-authorized-swap bounds and safe fallback remain mandatory. No paid execution is admitted by M7 planning.

Unchanged acceptance and resumption gates:

| Gate | Requirement retained in full |
| --- | --- |
| A: reviewed knowledge | 100% of credited pilot facts have reviewed source provenance and correct material scope; independent fixtures replay; zero unknown-to-absence or unreviewed-to-proof conversions. |
| B: deterministic recommendation | Four independently established positive scenarios each produce at least one candidate passing all four H2 gates. Two independently established inadequate scenarios receive honest insufficiency/infeasibility outcomes. Every returned candidate passes legality, skill/package and finite allocation checks; identical inputs reproduce output; zero analyzer calls. |
| H2 dimensions | Damage affinity/elemental viability, boss-mechanic counter coverage, team synergy/role coherence and setup executability are evaluated independently. Material UNKNOWN/REVIEW never counts as PASS. No H2 positive has been established by the current candidate replays or Stage 1 smoke. |
| Reporting | 100% of measured requests emit funnel, diversity, denominator and unknown-data diagnostics. Record actual unique character/frontline sets and strategic differences; never manufacture alternatives or turn missing proof into absence. No multiple-party quota without independently established alternatives. |
| C: conditional analyzer | Separately authorized only: zero out-of-bundle IDs or unsupported material claims, source-grounded explanations, at most two calls and one authorized swap per lineup, safe deterministic fallback. |
| D: usefulness | Owner reviews selected recommendations against all four H2 gates. Keep deterministic-only findings distinct from measured analyzer/end-to-end evidence. |
| Scenario authority | Freeze independently source-justified outcomes, exact forms/SA/upgrades/Light/Shadow/sidekicks/item policy before observing output. Include all eight automatic F2P forms in inadequacy analysis. Missing knowledge is not gameplay infeasibility; proposed negative seeds are not certificates. |
| Completion | P1-P3, reviewed facts, independently justified scenarios, A/B and owner-reviewed deterministic usefulness, preserved 367-form legality, honest uncertainty and canonical documentation must pass. Conditional paid C/D remain explicitly unmeasured if unauthorized; deterministic-only completion cannot claim LLM quality. |

Rotte Rivel remains a non-passing diagnostic case: marked-slot non-type Magic plus Confuse/Bind has no established counter, Fire Magic against combined Fire weakness/Magic resistance is REVIEW/UNKNOWN, and ordinary mitigation is not proven against HP-halving. Celestial Mushroom has no established four-gate positive either; Venom's Pain/Poison can increase resistance and trigger cleansing/healing. Do not equate the two bosses' evidence or replace one, reduce positive scope or weaken a gate without an explicit owner decision. A source-justified Mushroom-only proposal must retain the four-positive/two-inadequate gate and obtain explicit owner approval before changing the positive-boss scope.

On resumption, first establish source-only scenario authority and report the smallest remaining product decision. Preserve meaningful negative cases: wrong element/type, self-only effect credited to party, absent prerequisites, unowned/SA-gated skill, duplicate hero/skill family, finite-item conflict, unsupported counter, harmful boss interaction and knowledge insufficiency. Record reviewed fact/character counts, corrections/rejections, minutes/person-hours, deterministic latency and candidate/search counts. Authorized paid runs additionally record calls/tokens/latency/served model/cost. Do not claim review-time reduction without independent timing evidence.

Stage 1 integration is complete: `9f0a33e` wires production/exploratory input and `49a0d62` preserves validated fallback-to-format. Planning-time reruns passed 363 workflow/affected-web tests, seven pilot-source tests and the offline Chromium smoke with three degraded recommendations. Fixture-backed records do not prove live Cypher execution, Neo4j freshness, strategic usefulness or paid-provider qualification.

After the retained M6 gates are actually met, the owner chooses a limited MVP, a demonstrated-defect repair or evidence expansion. Reconsider extraction automation only after a trustworthy baseline and measured need. M7 frontend completion and M8 safeguards/provider/release obligations remain independent requirements.

### Milestone 7: Frontend Portfolio Experience

Status: Active workstream; planning approved on 2026-10-22. M7-1 through M7-3 are planned. RR-A/RR-B foundations are complete; remaining frontend acceptance is open.

Purpose: deliver a limited, explainable portfolio MVP on the existing engine: boss and owned forms -> up to three legal candidates when supported -> inspect placement/skills -> understand source-backed reasons, warnings and limitations. Exploratory GraphRAG remains supported.

Implementation order and one completed-feature commit each:

1. M7-1: explain candidates and evidence limits. Reuse cards/skills/builds/citations; expose bounded final-selection evidence, affinities, missing review, harmful Venom/Mushroom interaction, alternative Zone and reserve-switch limitations. Clarify heuristic fit/confidence and deterministic-only status.
2. M7-2: actionable input/result errors and terminal request recovery. Reuse typed issues and POST/job/SSE; handle unavailable candidates, invalid jobs, disconnects and no-result completion without stuck controls or false infeasibility claims.
3. M7-3: guided roster and portfolio demo usability. Explain forms/F2P/default assumptions, add an explicit supported sample roster, and verify mobile/keyboard/readability without redesigning working areas.

Exact feature contracts, exclusions and automated/manual browser acceptance live in [milestone.md](milestone.md). Production selection remains Celestial Mushroom only; Rotte stays diagnostic and unavailable in the selector. The twenty normal forms are a source-pinned demo pool, not a restriction on the 367-form legal catalog.

Dependency disposition: stable M5 architecture and completed Stage 1 integration admit frontend work by explicit owner exception despite the unmet M6 baseline. No positive strategic acceptance is implied. M8 still depends on accepted M6 evidence and completed M7 stability.

Deferred from the earlier broad M7 outline: advanced SA/Light/Shadow/preference editors and inventory work; admin freshness/health dashboards and public provider-cost views. Display current assumptions and missing observations instead. M8 owns the operational visibility necessary for its safeguarded release; no extra infrastructure is introduced here.

Exit: all three features and their recorded UI checks pass; a player can distinguish legal candidates, modeled evidence, assumptions and unknowns, and a recruiter can explain deterministic backend versus bounded LLM responsibilities. Candidate generation, curation, magnitude scoring, H2 strategy validation, optimization, simulation, classifier architecture, chat and deployment are outside M7. No guaranteed clear, battle-strength score, win probability, equal boss-validation claim or release-readiness assertion.

### Milestone 8: Cost-Controlled Deployment

Status: Planned.

Purpose:

- Deploy a controllable portfolio preview for job hunting, interviews, freelancing, or demos; broader community feedback follows only after the preview is stable.

Expected outcomes:

- Deployment and start/stop guidance.
- Email-verified registration and persistent atomic accounting for ten paid logical recommendation requests per user per calendar month.
- Per-IP burst/concurrency controls, an RM50 global monthly hard ceiling, and a global paid-analysis kill switch.
- Deterministic fallback when paid analysis is unavailable.
- Release-time provider/model qualification with captured usage, cost, validation, served-model, and fallback evidence.
- Placeholder-only configuration documentation; secrets remain outside the repository.

Dependencies:

- Stable M5 architecture, accepted M6 pilot evidence and declared coverage limits, and completed M7 frontend/stability work.

Exit criteria:

- The site can be switched on and off for portfolio campaigns.
- Paid endpoints cannot operate as unlimited anonymous services.
- Monthly spend is bounded and auditable.
- Release-time provider configuration passes separately authorized qualification.
- Credentials remain outside repository documents and source.

## Cross-Milestone Constraints

- Scraped/source facts remain separate from derived recommendation judgments.
- Versioned repository artifacts remain canonical for taxonomy, reviews, negative fixtures, overrides, and scoring policy.
- Neo4j capability metadata is reproducible materialized data, not sole authority.
- Legal-kit completeness and capability proof remain separate.
- Unknown evidence is not proven absence.
- Production recommendation retrieval and candidate search remain typed and deterministic.
- Exploratory GraphRAG remains a separate mode.
- Hard legality precedes scoring; deterministic validation follows analyzer refinement.
- Scores are ranking/navigation signals, never success probabilities.
- Same parsed data and artifact versions reproduce materialized evidence and deterministic candidate output.
- Production recommendation uses no PLAN, generated Cypher, retrieval-validation LLM, AI-authored contextual scores, or unbounded roster/catalog projection.
- The analyzer cannot introduce out-of-bundle IDs and may propose at most one backend-authorized swap per lineup.
- Paid evaluation requires deterministic preflight gates and explicit human authorization.
- Schema/data-shape changes update `docs/core/SCHEMA.md`, migrations, and assertions in the owning implementation feature; planning-only wording changes do not change `SCHEMA_VERSION`.
- ETL and recommendation behavior changes update their respective guides.
- Deployment remains optional, bounded, and easy to stop.

## Deferred Or Out Of Scope

- Exact damage, healing, AF, survival, or turn-by-turn simulation.
- Numeric win probability or clear-rate prediction.
- Global lineup optimization or guaranteed victory.
- Full inventory and best-in-slot optimization.
- Exhaustive manual capability review of every skill/passive.
- Treating missing or rejected proposals as proven character-level absence.
- Two backend-authorized swaps until M6 evidence demonstrates value; three or four swaps remain excluded.
- Live AI capability tagging during ETL or recommendation.
- Paid AI judging of normal requests.
- Full superboss-catalog expansion beyond the approved thirty-boss corpus without a separate versioned admission feature.
- Always-on deployment or community beta before the safeguarded portfolio preview is stable.

## Open Questions

- Whether the curated pilot proves useful recommendations and which measured evidence gaps justify expansion.
- Which additional capability families materially change candidate quality for the thirty-boss corpus?
- Whether two backend-authorized swaps improve quality without masking weak candidate generation.
- Which provider/model configuration earns release qualification after deterministic M6 gates and M7 stability work pass.
- Which authentication and persistence technologies best implement the M8 quota and cost-control contract.
