# AnotherEdenAI Roadmap

## Executive Summary

AnotherEdenAI is a personal portfolio project demonstrating production-minded AI engineering for a complex game-recommendation domain. The long-term program builds a cost-aware system that scrapes Another Eden wiki data, stores combat facts in Neo4j, and recommends legal, boss-aware six-hero plus optional two-sidekick lineups from a player's owned roster.

The program now separates two product paths:

- Production lineup recommendation uses deterministic typed retrieval, backend filtering and scoring, bounded candidate generation, compact LLM refinement, and deterministic validation.
- Exploratory GraphRAG may retain dynamic planning and Cypher generation for flexible graph questions, but it does not own production lineup legality.

The portfolio target audience is recruiters, senior managers, and potential freelance clients. The system should demonstrate reliable ETL, auditable recommendation logic, strict legality, measurable evaluation, bounded AI cost, transparent degradation, and a deployment that can be enabled only for job-search or demo periods.

## Program Objectives And Success Criteria

- Build an auditable ETL pipeline that can scrape and replay wiki data through cached artifacts.
- Represent combat facts in Neo4j while keeping derived recommendation policy reproducible from versioned repository artifacts.
- Recommend teams without hallucinating unavailable characters, illegal skills, unsupported mechanics, or impossible item allocations.
- Keep deterministic search, role scoring, candidate generation, and validation in the backend.
- Reserve the LLM for strategy-level ranking, bounded refinement, skill choice from shortlists, and explanation.
- Keep AI cost controlled through compact projections, preflight budgets, provider usage accounting, free/local development paths, and paid-model use only where it earns value.
- Present the project through a polished web interface that communicates engineering quality quickly.
- Support low-cost deployment that can be switched on for interviews, demos, freelancing, or job-hunting campaigns and switched off afterward.

Program success requires deterministic candidate generation without production PLAN/Cypher LLM calls, 100% hard legality on golden fixtures, partial valid output instead of all-or-nothing failure, and paid analyzer usage within the locked Milestone 5 token ceilings.

## Current Active Milestone

Milestone 4 is completed for Features A-E. The active milestone is Milestone 5, rewritten around candidate-constrained generation and production cost safety.

Milestone 5 maps to `docs/core/milestone.md` and is ordered around:

- Completing and verifying identity, cardinality, and canonical-ID prerequisites.
- Deterministic typed retrieval for the production recommender.
- Reviewed atomic capability/dependency taxonomy, negative fixtures, and reproducible evidence materialization before contextual role scoring.
- Hard filtering, contextual role scoring, and role-aware skill packaging.
- Assumption-based late-game build packages.
- Capability-coverage templates, top-8 role pools, and bounded beam search.
- Compact analyzer projections with at most one bounded swap per lineup.
- A maximum of two analyzer calls, deterministic fallback, and partial-result behavior.
- Golden evaluation, provider usage accounting, and paid-call gates.
- Authentication, persistence, rate limiting, and deployment safeguards only after the recommendation core is proven.

## Research References

Detailed source and repository-grounding notes live in `docs/core/planning-sources.md`.

Most important current references:

- OpenRouter Usage Accounting for provider-reported prompt, completion, reasoning, cached, total-token, and cost data.
- OpenRouter Structured Outputs for strict JSON Schema response contracts on compatible models.
- OpenRouter Models documentation for release-time capability, pricing, and limit snapshots.
- Another Eden mechanics and Grasta references already recorded for affinity handling, role evidence, setup dependencies, and item legality.
- The existing workflow, legality, candidate, evaluation, architecture, and schema files inspected during Milestone 5 replanning.

## Open Research Gaps

- Real prompt, completion, reasoning, cache, and cost distributions after the compact projection is implemented.
- Golden-fixture and experienced-player evidence for initial scoring weights and must-include counter exceptions.
- Whether the intended paid model remains the best quality/cost choice at release time.
- Whether an optional OpenRouter-assisted curation batch materially improves low-confidence role-tag coverage.
- Per-user and global request limits for a controlled 20-30-player beta.
- Minimum authentication and persistence design for beta feedback and budget enforcement.

These gaps may tune weights, providers, or later beta safeguards. They do not block deterministic architecture implementation.

## Ordered Major Milestones

### Milestone 1: GraphRAG Foundation

Status: Completed.

Purpose:

- Establish the initial Neo4j graph, ETL pipeline, LangGraph workflow, and FastAPI/HTMX streaming UI.

Expected artifacts:

- Character, Trait, Grasta, and Ore graph.
- Initial PLAN -> GENERATE_CYPHER -> VALIDATE -> ANALYZE -> FORMAT workflow.
- Roster-constrained query path.
- Streaming web UI and admin ETL trigger.

Dependencies:

- None; this is the foundation milestone.

Exit criteria:

- Existing app runs locally.
- Core workflow tests pass.
- Initial graph answers roster-constrained graph questions.

### Milestone 2: Combat Graph Expansion

Status: Partially completed.

Purpose:

- Expand character data from identity and Grasta compatibility into active skill and passive combat facts.

Expected artifacts:

- Cached/resumable ETL foundation.
- Character active skills and passive skills.
- Stellar Awakening availability and gating.
- Updated schema and ETL guidance.

Dependencies:

- Milestone 1 graph, ETL, and workflow foundation.

Exit criteria:

- Character detail pages produce graph-native skill/passive data.
- Blocked or partial pages fail quality gates.
- Cached parsed JSON can reload Neo4j.

### Milestone 3: RAG-Ready ETL Data Coverage

Status: Completed.

Purpose:

- Add the factual data needed before legal boss-aware recommendation.

Expected artifacts:

- Sidekick identity, skills, auras, and official associations.
- Curated weak-superboss affinity and mechanics facts.
- MechanicReference corpus.
- Preserved Grasta/Ore data and baseline equipment context.
- Manifest and schema assertions.

Dependencies:

- Milestone 2 cached ETL and character combat data.

Exit criteria:

- Selected crawl scope has pass/fail accountability.
- Curated sidekick and superboss data loads with attribution.
- Golden retrieval queries prove the structures are usable.

### Milestone 4: AI Lineup Recommendation Intelligence

Status: Completed.

Purpose:

- Establish the first structured, legal six-hero plus optional sidekick recommendation contract.

Expected artifacts:

- Structured roster ownership and Stellar Awakening state.
- Sidekick and skill-slot legality.
- Boss-aware top-three recommendation contract.
- Final factuality and legality gate.
- Compact and expandable result UI.

Dependencies:

- Milestone 3 RAG-ready combat, sidekick, boss, mechanics, and build facts.

Exit criteria:

- Curated boss recommendations use owned/F2P constraints.
- Output separates lineup, assumptions, risks, and uncertainty.
- Tests catch hallucinated characters, illegal slots, affinity drift, and numeric win-probability claims.

### Milestone 5: Deterministic Recommendation Engine, Evaluation, And Cost Control

Status: Active.

Purpose:

- Replace broad-context LLM lineup search with a production-safe backend candidate engine and a compact, bounded strategist LLM.

Expected artifacts:

- Typed production retrieval independent of PLAN and generated Cypher.
- A five-gate capability program: C1 atomic contracts/review tooling/schema cutover; C2 defensive/setup review; C3 offensive/support review; C4 dependency/condition review; and C5 full replay/drift verification/handoff.
- Deterministic 45-row CSV review batches, constrained reviewer fields, canonical JSON decisions, negative fixtures, curated overrides, and reproducible Neo4j materialization.
- Contextual RoleScores and role-aware skill shortlists.
- `late_game_assumed` build packages with legality and cardinality evidence.
- Hard filters, capability templates, top-8 role pools, must-include counter exceptions, and beam width capped at 50.
- Five to ten diverse legal candidates when available, with partial and zero-candidate contracts.
- Full internal candidate objects and compact analyzer projections.
- One optional one-for-one swap per lineup from backend-supplied choices.
- Maximum two analyzer calls and deterministic degraded fallback.
- Golden deterministic gates and observed provider token/cost reporting.
- Updated reusable ETL and recommendation-validation guidance.
- Beta safety work sequenced after the core engine passes.

Dependencies:

- Milestone 4 output and legality contracts.
- Correct canonical IDs, item identity, and Grasta acquisition cardinality.
- Curated weak-superboss and mechanics data.
- Completion of Feature C5 after all three human-review phases achieve two consecutive clean 45-row batches before contextual RoleScores or skill shortlists.

Exit criteria:

- Production recommendations generate legal backend candidates without PLAN, generated Cypher, or LLM retrieval validation.
- Identical parsed facts, review artifacts, and policy versions produce reproducible capability metadata, contextual role scoring, pruning, and candidate order.
- Golden feasible cases return at least one legal coverage-valid lineup; infeasible cases return typed diagnostics.
- Analyzer sees only compact referenced candidates and cannot introduce out-of-bundle IDs.
- Paid golden runs remain below the 40k cumulative analyzer-token ceiling and demonstrate at least a 90% reduction from the recorded ~601k-token failed baseline.
- Provider/model metadata, usage, cost, validation, and degradation are auditable.
- No numeric win probability or guaranteed-clear claim is produced.

### Milestone 6: Frontend Portfolio Experience

Status: Planned.

Purpose:

- Make deterministic recommendation evidence and the exploratory graph experience impressive and legible to recruiters and players.

Expected artifacts:

- Polished input for roster, boss, sidekicks, SA state, and recommendation preferences.
- Clear separation between production recommender and exploratory GraphRAG.
- Candidate score explanations, assumptions, sources, risks, degradation, and pipeline progress.
- Admin/status views for data freshness and system health.

Dependencies:

- Milestone 5 recommendation engine and evaluation artifacts.

Exit criteria:

- A recruiter understands the backend/LLM boundary quickly.
- A player can distinguish legal recommendations from assumptions and incomplete data.
- A senior engineer can inspect constraints, evidence, failure handling, and cost controls.

### Milestone 7: Cost-Controlled Deployment

Status: Planned.

Purpose:

- Deploy the project only when needed for job hunting, interviews, freelancing, controlled beta, or demos.

Expected artifacts:

- Deployment and start/stop guidance.
- Authentication, persistence, per-user/global rate limits, and monthly budget enforcement.
- Local Neo4j by default and practical demo deployment.
- Disableable refresh and paid-recommendation paths.
- Placeholder-only environment documentation.

Dependencies:

- Stable app, frontend, recommendation gates, and beta safety plan.

Exit criteria:

- The site can be switched on and off for portfolio campaigns.
- Paid endpoints cannot run as unlimited anonymous services.
- Monthly spend remains bounded and explainable.
- Secrets and credentials remain outside repository documents and source.

## Cross-Milestone Constraints

- Facts scraped from sources remain separate from derived recommendation judgments.
- Versioned repository artifacts are canonical for atomic capability/dependency rules, reviewed decisions, negative fixtures, overrides, and scoring policy.
- Neo4j capability metadata is reproducible materialized data, not the sole source of truth.
- Hard official associations and proven atomic skill/passive capabilities belong in ETL; contextual character role scores and strategy belong in the recommendation engine.
- Production recommendation retrieval is typed and deterministic.
- Dynamic GraphRAG remains a separate exploratory mode.
- Hard legality precedes scoring; backend validation follows every analyzer refinement.
- Scores are ranking/navigation signals, never win probabilities.
- Same parsed data plus the same artifact versions must reproduce role metadata and deterministic candidate output.
- Golden baseline/current comparisons should use captured artifacts or isolated worktrees when code branches must be compared; the 601k paid failure is not rerun merely to recreate a baseline.
- Schema changes update `docs/core/SCHEMA.md` and schema assertions during implementation.
- ETL behavior changes update `docs/guides/ETL_GUIDE.md`.
- Recommendation behavior changes update `docs/guides/recommendation-validation.md`.
- Development defaults to local/offline fixtures and free/local models; paid tests run only after deterministic gates pass.
- Deployment remains optional and easy to stop.

## Deferred Or Out-Of-Scope Work

- Exact deterministic damage or healing simulation.
- Full turn-by-turn battle simulation.
- Numeric win probability or clear-rate prediction.
- Full inventory and best-in-slot optimization.
- Required `declared_owned_only` item mode in the first implementation.
- Two or more analyzer hero swaps per lineup until evaluation proves value without cost or legality regression.
- Live AI role tagging during ETL or recommendation.
- Mandatory AI-assisted role labeling for initial acceptance.
- Full all-superboss coverage and intermediate/strong evaluation tiers.
- Sidekick equipment optimization.
- Paid judge calls on normal live requests.
- Always-on production deployment before a controlled need exists.

## Open Questions

Feature D remains architecture-blocked until the reopened Feature C capability review passes its three ordered phases. Provider choice, scoring-weight tuning, optional AI-assisted suggestions, and beta limits remain evidence-driven follow-up decisions recorded as research gaps.
