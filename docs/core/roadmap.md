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

Milestone 5 closed on 2026-09-14 after Feature H2. Milestone 6, Character Capability Coverage and Candidate Diversity, is active and maps to `docs/core/milestone.md`.

Milestone 6 is ordered around:

- measuring current catalog, strategic-evidence, search-funnel, and diversity coverage before choosing thresholds;
- deriving capability priorities from the committed thirty-boss corpus;
- attempting high-value extraction across all 367 canonical forms/styles;
- reviewing only ambiguous, high-impact, recurring, or acceptance-relevant facts;
- preserving proven, ambiguous, unknown, rejected, and untagged meanings;
- exposing request-time pool and candidate-set diagnostics;
- changing candidate generation only after diagnostics establish the responsible stage; and
- evaluating diverse candidates with H2's four modeled-viability gates.

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

### Milestone 6: Character Capability Coverage And Candidate Diversity

Status: Active.

Purpose:

- Expand recommendation-ready, high-value strategic evidence across all 367 canonical character forms/styles and produce meaningfully diverse boss-specific candidates when the effective roster supports alternatives.

Planned feature sequence:

1. Coverage baseline and metric contract.
2. Boss-to-capability priority matrix.
3. Full-catalog high-value extraction.
4. Selective review, materialization, and coverage closure.
5. Search-funnel and candidate-diversity diagnostics.
6. Evidence-driven candidate-diversity improvements.
7. Controlled four-gate evaluation and milestone closure.

Dependencies:

- Completed M5 deterministic recommendation architecture and evaluation contracts.
- The 367-character legal-kit catalog and conservative capability-proof pipeline.
- The committed thirty-boss corpus and H1/H2 tooling.

Exit direction:

- All 367 remain legal-kit complete and in scope.
- High-value extraction is attempted across the full catalog.
- Unknown and ambiguous evidence remains explicit and non-authoritative.
- Evidence-driven thresholds are selected only after the baseline reports current distributions.
- Coverage spans applicable elements, physical/magic offense, offensive support, zone/setup, mitigation, recovery, status counterplay, AF support, Pain/Poison, and boss counters.
- Controlled alternative-rich rosters yield multiple meaningfully different legal character/frontline sets and coherent archetypes.
- Constrained rosters may return fewer candidates with stage-accountable reasons.
- H2's four gates support plausible evidence-backed candidates with no global-optimality, win-probability, or guaranteed-clear claim.
- No paid analyzer evaluation occurs before deterministic gates pass or without separate authorization.

The detailed executable contract and eventual numeric-threshold checkpoint live in `docs/core/milestone.md`.

### Milestone 7: Frontend Portfolio Experience

Status: Planned.

Purpose:

- Make deterministic recommendation evidence and the exploratory graph experience impressive and legible to recruiters and players.

Expected outcomes:

- Polished roster, boss, sidekick, Stellar Awakening, Light/Shadow, and preference input.
- Clear separation between production recommendation and exploratory GraphRAG.
- Candidate evidence, assumptions, risks, sources, degradation, coverage, and diversity diagnostics.
- Product language that presents plausible evidence-backed candidates rather than a promised best team.
- Admin/status views for data freshness and system health.

Dependencies:

- Stable M5 recommendation architecture.
- Sufficient M6 capability coverage, search observability, and candidate diversity.

Exit criteria:

- A recruiter can understand the deterministic backend/LLM boundary quickly.
- A player can distinguish legal recommendations, modeled evidence, assumptions, and incomplete data.
- A senior engineer can inspect constraints, evidence, failure handling, diversity, and cost controls.

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

- Stable M5 architecture, completed M6 coverage/diversity work, and completed M7 frontend/stability work.

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

- What numeric high-value coverage and diversity thresholds are justified by the M6 Feature A baseline?
- Which additional capability families materially change candidate quality for the thirty-boss corpus?
- Whether two backend-authorized swaps improve quality without masking weak candidate generation.
- Which provider/model configuration earns release qualification after deterministic M6 gates and M7 stability work pass.
- Which authentication and persistence technologies best implement the M8 quota and cost-control contract.
