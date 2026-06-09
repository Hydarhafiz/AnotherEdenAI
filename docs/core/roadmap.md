# AnotherEdenAI Roadmap

## Executive Summary

AnotherEdenAI is a personal portfolio project that demonstrates production-minded AI engineering for a complex game recommendation domain. The long-term program is to build a cost-aware GraphRAG system that scrapes Another Eden wiki data, stores combat facts in Neo4j, and uses AI agents to recommend legal, boss-aware 6-hero plus 2-sidekick lineups from a player's owned roster.

The portfolio target audience is recruiters, senior managers, and potential freelance clients. The project should show practical judgment: reliable ETL, strict recommendation rules, transparent evaluation, polished UI, and deployment that can be turned on only during job-search or demo periods.

## Program Objectives And Success Criteria

- Build an auditable ETL pipeline that can scrape and replay wiki data through cached artifacts.
- Represent combat data in a graph structure that supports RAG retrieval and legality checks.
- Recommend teams without hallucinating unavailable characters, illegal skills, or unsupported mechanics.
- Keep AI cost controlled through local/free development paths, configurable providers, prompt/context optimization, and paid-model use only where it earns value.
- Present the project through a polished web interface that communicates engineering quality quickly.
- Support low-cost deployment that can be switched on for interviews, demos, freelancing, or job-hunting campaigns and switched off afterward.

## Current Active Milestone

Milestone 3 is completed. The active milestone is now Milestone 4, which begins the AI lineup recommendation intelligence work unlocked by the RAG-ready ETL data foundation.

Milestone 4 focuses on:

- Structured roster ownership, Stellar Awakening, and Light/Shadow rules.
- Legal 6-hero plus main/sub sidekick lineup generation.
- Skill-slot legality and boss-aware recommendation contracts.
- Grasta/Ore and equipment coverage review before recommendation logic depends on them.
- Initial evaluation gates for legality, factuality, and boss-counterplay relevance.

## Ordered Major Milestones

### Milestone 1: GraphRAG Foundation

Status: Completed

Purpose:

- Establish the initial Neo4j graph, core ETL pipeline, LangGraph workflow, and FastAPI/HTMX streaming UI.

Expected artifacts:

- Character, Trait, Grasta, and Ore graph.
- LangGraph PLAN -> GENERATE_CYPHER -> VALIDATE -> ANALYZE -> FORMAT pipeline.
- Roster-constrained query path.
- Streaming web UI and admin ETL trigger.

Exit criteria:

- Existing app runs locally.
- Core workflow tests pass.
- Initial graph can answer roster-constrained Grasta/team-building questions.

### Milestone 2: Combat Graph Expansion

Status: Partially completed

Purpose:

- Expand character data from simple identity and Grasta compatibility into active skill and passive combat data.

Expected artifacts:

- Cached/resumable ETL foundation.
- Character active skills and passive skills.
- Stellar Awakening availability and skill/passive gating.
- Updated schema and ETL guide.

Exit criteria:

- Character detail pages produce graph-native skill/passive data.
- Blocked or partial pages fail quality gates.
- Cached parsed JSON can reload Neo4j.

### Milestone 3: RAG-Ready ETL Data Coverage

Status: Completed

Purpose:

- Add the next factual data layer before AI recommendation implementation.

Expected artifacts:

- Sidekick nodes with structured auto skill, charge skill, aura, and official hero association.
- Curated weak superboss nodes with affinity and mechanics retrieval fields.
- Preserved Grasta/Ore data and lightweight retrieval tags where safe.
- Baseline weapon and armor context.
- Manifest and schema assertions for selected crawl scopes.

Dependencies:

- Existing ETL cache/replay foundation.
- Existing character/skill/passive graph.

Exit criteria:

- Selected crawl scope has 100% pass/fail accountability.
- Curated sidekick and weak-superboss data loads with source attribution.
- Golden graph retrieval queries prove the new RAG structures are usable.

### Milestone 4: AI Lineup Recommendation Intelligence

Status: Active

Purpose:

- Use the expanded graph to recommend legal 6-hero plus 2-sidekick lineups against selected bosses.

Expected artifacts:

- Structured roster model with ownership, Stellar Awakening, and Light/Shadow rules.
- Main/sub sidekick legality.
- Skill-slot legality.
- Boss-aware recommendation contract.
- Grasta/Ore and equipment coverage review before implementation.
- Initial evaluation suite for legality, factuality, and boss-counterplay relevance.

Dependencies:

- Milestone 3 data coverage and RAG readiness.

Exit criteria:

- The system can recommend legal teams for curated bosses using owned roster constraints.
- Recommendations cite graph facts and clearly separate legal lineup, upgrade suggestions, and uncertainty.
- CI catches hallucinated characters, illegal sidekick usage, and skill-slot violations.

### Milestone 5: AI Agent Optimization And Cost Control

Status: Planned

Purpose:

- Improve recommendation quality, latency, and cost efficiency for portfolio demos.

Expected artifacts:

- Configurable generation and judge providers.
- Context selection and prompt compression strategy.
- Two-tier evaluation: cheap local/free gates first, paid judge only after basic gates pass.
- Latency and token/cost reporting.
- Model/provider comparison reports.

Dependencies:

- Stable recommendation contract from Milestone 4.

Exit criteria:

- The system has measurable accuracy and latency baselines.
- Paid model usage is bounded and explainable.
- Evaluation reports show which provider generated and judged each run.

### Milestone 6: Frontend Portfolio Experience

Status: Planned

Purpose:

- Make the site impressive and legible to recruiters and senior managers without hiding the technical substance.

Expected artifacts:

- Polished web UI for roster input, boss selection, recommendation results, source attribution, and pipeline progress.
- Clear demo flows for ETL, graph facts, AI reasoning, and evaluation reports.
- Admin/status views for data freshness and system health.

Dependencies:

- Recommendation flow and evaluation artifacts from prior milestones.

Exit criteria:

- A recruiter can understand the project value within a short demo.
- A senior engineer can inspect evidence, constraints, and failure handling.
- UI communicates cost-aware AI engineering, not only game fandom.

### Milestone 7: Cost-Controlled Deployment

Status: Planned

Purpose:

- Deploy the project only when needed for job hunting, interviews, freelancing, or demos.

Expected artifacts:

- Deployment guide for a low-cost VPS or AWS option.
- Start/stop operational workflow.
- Local Neo4j by default, Dockerized Neo4j for demo deployment where practical.
- Manual or scheduled data refresh that can be disabled.
- Environment documentation using placeholders only, never checked-in secrets.

Dependencies:

- Stable app and frontend demo.

Exit criteria:

- The site can be switched on for portfolio campaigns and switched off afterward.
- Monthly cost remains reasonable for an RM3800/month income constraint.
- The deployment story is credible to recruiters without requiring always-on cloud spend.

## Cross-Milestone Constraints

- Facts scraped from the wiki should remain separate from AI-derived judgments.
- Hard official associations belong in ETL; soft strategic synergy belongs in later agent/evaluation layers.
- Schema changes must update `SCHEMA.md` and schema assertions.
- ETL behavior changes must update `guides/ETL_GUIDE.md`.
- Recommendation features must preserve roster legality and avoid hallucinated mechanics.
- Development should prefer local/offline workflows and cached artifacts.
- Deployment should be optional, easy to stop, and designed around low recurring cost.
- Secrets and credentials must never be committed or documented directly.

## Deferred Or Out-Of-Scope Work

- Full all-superboss scrape before weak-boss seed data is stable.
- Sidekick equipment ingestion before sidekick identity and abilities are useful.
- AI-derived sidekick synergy before official associations are modeled.
- Exact damage calculation before Grasta/Ore/equipment data and evaluation are mature.
- Full battle mechanics ontology before text-rich RAG fields reveal repeated reasoning failures.
- Always-on production deployment before job-hunting or demo need.

## Open Questions

- Which low-cost deployment target will be selected first: a budget VPS, AWS Lightsail, small EC2, or another provider?
- Which model/provider mix gives the best quality/cost tradeoff after the recommendation contract exists?
- How much of the damage formula should become deterministic code versus RAG-supported explanation?
