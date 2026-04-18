# Another Eden AI - GraphRAG Team Builder

## What This Is

A GraphRAG-powered decision support system for Another Eden (JRPG) that helps players build mathematically optimal teams. Users input their roster and ask natural language questions ("What's the highest damage blunt-zone synergy I can make?"), and the system returns validated 4-frontline/2-reserve team compositions with personality and Grasta synergy recommendations.

## Core Value

Players receive mathematically sound team recommendations that strictly follow game rules, constrained by their actual roster, with zero hallucinated mechanics.

## Requirements

### Validated

- ✓ System scrapes character, Grasta, and personality data from anothereden.wiki — Phase 1
- ✓ Scraped data is transformed and loaded into Neo4j graph database — Phase 1
- ✓ Graph models character-personality-Grasta relationships and synergies — Phase 1
- ✓ PLAN agent (Sonnet 4.6) breaks down user query into sub-goals — Phase 2
- ✓ GENERATE_CYPHER agent (Sonnet 4.6) translates plan into Neo4j graph queries — Phase 2
- ✓ VALIDATE agent (Haiku 4.6) verifies query syntax and game rule validity — Phase 2
- ✓ VALIDATE agent triggers retry loop (max 3x) when queries fail — Phase 2
- ✓ ANALYZE agent (Sonnet 4.6) synthesizes query results into final recommendation — Phase 2
- ✓ System constrains recommendations to owned characters + F2P units — Phase 3
- ✓ User can input their roster (owned characters) manually — Phase 3

### Active

**User Interaction:**
- [ ] User can query team compositions in natural language

**Output:**
- [ ] System returns 4-frontline/2-reserve lineup recommendations
- [ ] Recommendations include personality and Grasta synergy matching
- [ ] All recommendations respect game mechanics (no hallucinated abilities)

**Web Interface:**
- [ ] User accesses system through web browser
- [ ] Interface allows roster input and natural language query submission
- [ ] Results are displayed with clear team composition and synergy explanations

### Out of Scope

- **Boss Strategies** — Turn-by-turn superboss guides and HP stopper analysis (deferred to v3)
- **Farming Optimization** — Daily dungeon efficiency and Red/Green key forecasting (deferred to v2)
- **Deep Stat Allocation** — Combinatorial optimization for exact Grasta/Badge stat distribution across team (deferred to v2, v1 only does basic trait matching)
- **Account Integration** — Real-time screen reading, OCR, or game client hooks (users input roster manually)
- **PvP Analysis** — Player-vs-player meta (Another Eden is PvE-only)

## Context

**Problem Space:**
Another Eden is a complex JRPG with hundreds of characters and combinatorial buff/debuff mechanics (Grasta system). Players face "analysis paralysis" when trying to optimize team synergies. Current solutions are outdated spreadsheets that don't account for individual roster constraints.

**Target Users:**
Another Eden playerbase struggling with:
- **Roster Overload**: Too many units, no intuitive way to calculate optimal team synergies
- **Superboss Wall**: End-game bosses require specific strategies (addressed in future versions)
- **Farming Fatigue**: Unclear resource optimization paths (addressed in future versions)

**Technical Environment:**
- Portfolio project demonstrating enterprise-grade MLOps architecture
- Built asynchronously around full-time backend/DevOps work
- Self-funded on moderate monthly salary

## Constraints

- **Tech Stack (Locked)**: Python, Neo4j, LangGraph, Sonnet 4.6, Haiku 4.6 — non-negotiable for portfolio demonstration
- **Local LLM Testing**: `LLM_PROVIDER=ollama` env var routes all LLM calls through Ollama during development to protect API budget; `LLM_PROVIDER=anthropic` (default) uses the locked Sonnet/Haiku models for production and final validation
- **Budget**: Strict API cost controls via retry caps (max 3 iterations on VALIDATE node) and Ollama-first local development to prevent runaway Sonnet 4.6 billing
- **Timeline**: Flexible — phases must be atomic and resumable for async development
- **Data Source**: anothereden.wiki (public wiki scraping)
- **No Opus**: Explicitly excluding Opus 4.6 to prioritize latency and cost efficiency

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph multi-agent architecture (PLAN → GENERATE_CYPHER → VALIDATE → ANALYZE) | Demonstrates agentic workflows for recruiters, provides clear separation of concerns | — Pending |
| Neo4j for game data storage | Graph structure naturally models character-personality-Grasta relationships and synergy traversal | — Pending |
| Sonnet 4.6 for reasoning, Haiku 4.6 for validation | Cost/latency balance — Haiku fast enough for validation, Sonnet needed for complex analysis | — Pending |
| 3x retry cap on VALIDATE node | Hard stop to prevent runaway API costs on personal budget | — Pending |
| Manual roster input (no OCR) | Complexity/scope reduction for v1, defer integration challenges | — Pending |
| Focus on synergy matching only (defer stat optimization) | Atomic v1 scope, establish core pipeline before adding complexity | — Pending |
| LLM provider abstraction via `src/workflow/llm.py` factory | `LLM_PROVIDER` env var toggles between Ollama (local dev) and Anthropic (production) — protects API budget and enables offline development | — Pending |
| AWS App Runner / ECS Fargate deployment via GitHub Actions | MLOps portfolio project must include cloud deployment to demonstrate production-grade CI/CD; automated pipeline on merge to main | — Pending |

---
*Last updated: 2026-04-19 after Phase 3 — validated data pipeline, agentic workflow, and roster filtering requirements*
