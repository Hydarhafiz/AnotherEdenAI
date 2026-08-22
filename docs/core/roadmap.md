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

Milestone 4 is completed for Features A-E. The active milestone is Milestone 5, rewritten around candidate-constrained generation and production cost safety, then corrected on 2026-08-22 after Neo4j-backed H-03 evidence exposed a shared data/package/search/allocation boundary failure.

Milestone 5 maps to `docs/core/milestone.md` and is ordered around:

- Completing and verifying identity, cardinality, and canonical-ID prerequisites.
- Deterministic typed retrieval for the production recommender.
- Reviewed atomic capability/dependency taxonomy, negative fixtures, and reproducible evidence materialization before contextual role scoring.
- Full legal-kit materialization receipts for all 367 canonical MVP character forms/styles, without requiring exhaustive capability proof.
- Hard filtering and contextual role scoring from proven capabilities, separated from legal active-skill package membership.
- One to three boss-aware legal package variants per hero, with a fourth skill slot only for declared Light/Shadow >=80.
- Assumption-based late-game build alternatives with deterministic finite-copy lineup allocation.
- Capability-coverage templates, top-8 role pools, and package-first bounded beam search.
- Compact analyzer projections with at most one bounded swap per lineup.
- A maximum of two analyzer calls, deterministic fallback, and partial-result behavior.
- A recommendation-ready thirty-boss evaluation corpus stratified into ten weak, ten medium, and ten strong wiki-difficulty cases.
- Golden evaluation, provider usage accounting, and paid-call gates.
- Independently witnessed boss-feasibility acceptance cases, deterministic infeasibility certificates, and a separate unchanged fixed-nine-roster stress suite.
- A locked portfolio-preview safeguard contract after the recommendation core is proven; Discord demo and feedback collection remain a later roadmap activity.

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
- Authentication-provider and persistence-technology selection for the approved email-verified portfolio-preview quota contract.

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

- Replace broad-context LLM lineup search with a production-safe backend candidate engine and a compact, bounded strategist LLM, then correct the H-03 boundary so broad roster availability, legal packages, finite allocation, and evaluation claims are independently provable.

Expected artifacts:

- Typed production retrieval independent of PLAN and generated Cypher.
- A five-gate capability program: C1 atomic contracts/review tooling/schema cutover; C2 defensive/setup review; C3 offensive/support review; C4 dependency/condition review; and C5 full replay/drift verification/handoff.
- Correction C6: complete, replay-safe legal active/passive/SA kit receipts for all 367 canonical MVP character forms/styles plus selective high-value capability review.
- Deterministic 45-row CSV review batches, constrained reviewer fields, canonical JSON decisions, negative fixtures, curated overrides, and reproducible Neo4j materialization.
- Contextual RoleScores from proven capabilities and legal skill selection that permits untagged fillers with zero coverage credit.
- Up to three non-dominated boss-aware packages per character; three skill families by default and four only with declared Light/Shadow >=80.
- `late_game_assumed` build alternatives with legality, cardinality evidence, and deterministic matching/backtracking.
- Hard filters, capability templates, top-8 role pools, must-include counter exceptions, package-first beam search, and beam width capped at 50.
- Five to ten diverse legal candidates when available, with partial and zero-candidate contracts.
- Full internal candidate objects and compact analyzer projections.
- One optional one-for-one swap per lineup from backend-supplied choices.
- Maximum two analyzer calls and deterministic degraded fallback.
- Golden deterministic gates and observed provider token/cost reporting.
- Updated reusable ETL and recommendation-validation guidance.
- Beta safety work sequenced after the core engine passes.
- Feature G1 is complete within Milestone 5: the fixed thirty-boss corpus contains ten weak, ten medium, and ten strong canonical identities. Feature H is in progress but blocked at H-03 until C6, D2, E2, and F2 complete.
- Feature H separates independently witnessed boss acceptance from the unchanged common-nine-character stress suite; its ten strategic infeasible cases use valid data-complete requests and deterministic impossibility certificates.

Dependencies:

- Milestone 4 output and legality contracts.
- Correct canonical IDs, item identity, and Grasta acquisition cardinality.
- Curated weak-superboss and mechanics data.
- Completion of Feature C5 after all three human-review phases achieve two consecutive clean 45-row batches before contextual RoleScores or skill shortlists.
- Completion of correction Features C6, D2, E2, and F2 in order before H resumes Neo4j-backed acceptance.

Exit criteria:

- Production recommendations generate legal backend candidates without PLAN, generated Cypher, or LLM retrieval validation.
- Identical parsed facts, review artifacts, and policy versions produce reproducible capability metadata, contextual role scoring, pruning, and candidate order.
- All 367 canonical MVP character forms/styles pass the legal-kit receipt gate.
- Twenty independently witnessed feasible boss cases return at least one legal coverage/allocation-valid lineup; ten valid data-complete infeasible cases return typed diagnostics matching their impossibility certificates without analyzer calls.
- The fixed common-nine-character requests remain a deterministic stress suite and are not used as an unsupported feasibility oracle.
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
- Optional per-character Light/Shadow input with clear three-slot/four-slot consequences.
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

- Deploy the project as a controllable portfolio preview for job hunting, interviews, freelancing, or demos; a broader Discord feedback launch follows only after the preview is stable.

Expected artifacts:

- Deployment and start/stop guidance.
- Email-verified registration and persistent atomic accounting for ten paid logical recommendation requests per user per calendar month.
- Per-IP burst/concurrency controls, an RM50 global monthly hard ceiling, and a global paid-analysis kill switch; deterministic fallback remains available when paid analysis is unavailable.
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
- Full all-superboss coverage beyond the approved thirty-boss stratified Milestone 5 corpus; expand later in versioned batches guided by beta evidence and per-boss readiness gates.
- Sidekick equipment optimization.
- Paid judge calls on normal live requests.
- Always-on production deployment before a controlled need exists.
- Discord demo/reviewer recruitment and public feedback metrics before the stable portfolio preview is evaluated.
- Exhaustive reviewed capability proof for every skill in every character kit.

## Open Questions

The Milestone 5 correction architecture is approved. Provider reasoning settings, scoring-weight tuning, optional AI-assisted suggestions, and the later deployment technology choice remain evidence-driven follow-up decisions; they cannot weaken legal-kit completeness, proven-capability authority, finite allocation, or witnessed H acceptance.
