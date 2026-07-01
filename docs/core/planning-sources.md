# Planning Sources

This file stores source references used during planning discussions. It separates repository-grounded project facts from external game-mechanics references so milestone scope, assumptions, and acceptance criteria stay auditable.

## Milestone 4: AI Lineup Recommendation Intelligence

### Repository Grounding

- Title: AnotherEdenAI roadmap
  URL: local `docs/core/roadmap.md`
  Source type: repository planning document
  Date added: 2026-06-09
  Related area: Milestone 4 scope and roadmap boundaries
  Relevance: Defines Milestone 4 as legal 6-hero plus 2-sidekick lineup recommendation against curated bosses, with roster ownership, Stellar Awakening, Light/Shadow, skill-slot legality, boss-aware contracts, Grasta/Ore and equipment review, and evaluation gates.
  Caveats/open questions: The active Milestone 4 plan now narrows this broad roadmap intent into a recommendation navigation system.

- Title: AnotherEdenAI architecture
  URL: local `docs/core/architecture.md`
  Source type: repository architecture document
  Date added: 2026-06-09
  Related area: ETL, graph, workflow, and web boundaries
  Relevance: Establishes the current Neo4j ETL layer, LangGraph workflow, FastAPI/HTMX web layer, and design priorities for testable recommendation nodes over opaque prompt chains.
  Caveats/open questions: Milestone 4 may require a new mechanics retrieval layer, structured recommendation contract, and evaluation loop.

- Title: Graph schema contract
  URL: local `docs/core/SCHEMA.md`
  Source type: repository schema contract
  Date added: 2026-06-09
  Related area: graph data available to recommendation logic
  Relevance: Documents currently available Character, Skill, PassiveSkill, Sidekick, SidekickSkill, SidekickAura, Superboss, Grasta, Ore, and Equipment nodes plus relationships.
  Caveats/open questions: Battle mechanics reference data is not yet modeled as graph-native nodes or local RAG documents.

- Title: Future ideas
  URL: local `docs/core/future-ideas.md`
  Source type: repository planning backlog
  Date added: 2026-06-09
  Related area: mechanics knowledge base, combat ontology, equipment optimizer, structured recommendation output, full evaluation
  Relevance: Contains deferred concepts directly relevant to Milestone 4, especially Battle Mechanics Knowledge Base and Structured Recommendation Output Contract.
  Caveats/open questions: Several deferred ideas may need partial promotion into Milestone 4 while exact simulation and full optimizer stay out of scope.

### External Game-Mechanics References

- Title: Damage Formula
  URL: https://anothereden.wiki/w/Damage_Formula
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: damage scoring, skill multipliers, enemy weakness/resistance/null/absorb handling, Grasta and weapon multipliers
  Relevance: Primary planning reference for estimating damage potential and affinity interaction in recommendations.
  Caveats/open questions: Exact damage calculation may be too large for Milestone 4; first implementation may use simplified scoring plus cited uncertainty.

- Title: Buffs and Debuffs
  URL: https://anothereden.wiki/w/Buffs_and_Debuffs
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: party support, mitigation, type/physical resistance, stacking rules
  Relevance: Needed so recommendation reasoning can value buffers, debuffers, and mitigation roles without treating all support text equally.
  Caveats/open questions: Need to decide which buff/debuff concepts become deterministic tags versus retrieved text.

- Title: Status Effects
  URL: https://anothereden.wiki/w/Status_Effects
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: boss counterplay, control effects, sustain risk
  Relevance: Needed to reason about status application by characters and bosses, status mitigation, and lineup survivability.
  Caveats/open questions: Boss immunity and status success rates may not be available in current graph data.

- Title: Zones
  URL: https://anothereden.wiki/Zones
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: zone/stance synergy, damage modifiers, Another Force behavior
  Relevance: Needed for team archetype reasoning and zone-compatible lineup recommendations.
  Caveats/open questions: Current schema does not model Zone nodes; Milestone 4 may need a mechanics RAG layer before graph-native zone ontology.

- Title: Battle Mechanics
  URL: https://anothereden.wiki/w/Battle_Mechanics
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: party composition, frontline/reserve rules, sidekick basics, skill types, elements, equipment, turn order
  Relevance: Broad grounding source for legal party rules and basic battle semantics used by recommendations.
  Caveats/open questions: Some sections summarize deeper pages; important topics should link back to their specialized references when used for acceptance criteria.

- Title: Another Force
  URL: https://anothereden.wiki/w/Another_Force
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: burst windows, repeated skill use, AF gauge and speed behavior
  Relevance: Needed to reason about burst damage plans and whether a lineup can plausibly defeat a boss through AF windows.
  Caveats/open questions: Turn-by-turn AF planning may exceed Milestone 4 unless scoped to a simple "AF-compatible" explanation.

- Title: Grasta
  URL: https://anothereden.wiki/w/Grasta#Progression-1
  Source type: community wiki equipment/progression reference
  Date added: 2026-06-09
  Related area: DPS roles, support roles, ore recommendations, personality Grasta, progression gating
  Relevance: Needed for Grasta/Ore recommendation review and for deciding how far build advice should go beyond character lineup selection.
  Caveats/open questions: User also highlighted DPS Roles, Support Roles, Ores Recommendations, and Personality Grastas anchors on the same page; exact inventory and progression ownership may need separate user inputs.

- Title: Stats
  URL: https://anothereden.wiki/w/Stats
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: character stats, derived stats, damage and sustain inputs
  Relevance: Needed if Milestone 4 scores damage or survivability using stat-driven heuristics.
  Caveats/open questions: Current graph has limited character stat coverage; exact numeric scoring may require additional ETL before it can be reliable.

- Title: Healing Formula
  URL: https://anothereden.wiki/w/Healing_Formula
  Source type: community wiki formula reference
  Date added: 2026-06-09
  Related area: healing, regen, sustain scoring
  Relevance: Needed for measuring whether a lineup has credible sustain rather than only weakness coverage and damage.
  Caveats/open questions: Current skill descriptions may identify healing roles, but exact healing values may require stats/equipment assumptions.

- Title: Speed Control
  URL: https://anothereden.wiki/w/Speed_Control
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: preemptive/default/delayed action priority, speed RNG, Falcon/Ambush effects
  Relevance: Needed for boss counterplay recommendations when action order matters.
  Caveats/open questions: Full speed tuning may be deferred unless boss mechanics require first-turn mitigation or setup.

- Title: Stellar Awakening
  URL: https://anothereden.wiki/w/Stellar_Awakening
  Source type: community wiki progression/mechanics reference
  Date added: 2026-06-09
  Related area: Stellar Awakening ownership, gated skills/passives, Stellar Burst
  Relevance: Needed for legality checks and recommendation output that separates usable skills from upgrade suggestions.
  Caveats/open questions: Player-specific Stellar Awakening state needs to be captured in the roster model.

- Title: Turn Order
  URL: https://anothereden.wiki/w/Turn_Order
  Source type: community wiki mechanics reference
  Date added: 2026-06-09
  Related area: action sequencing and turn timing
  Relevance: User identified it as a source for determining action timing.
  Caveats/open questions: The standalone URL did not load during initial Codex inspection; the Battle Mechanics page includes a turn-order section and can serve as the fallback source.

- Title: Sidekick
  URL: https://anothereden.wiki/w/Sidekick
  Source type: community wiki mechanics/reference page
  Date added: 2026-06-09
  Related area: sidekick ownership, main/sub legality, auto skills, charge skills, auras, sidekick equipment
  Relevance: Needed for sidekick legality and recommendation value, including main sidekick full ability access versus sub sidekick aura-only behavior.
  Caveats/open questions: Sidekick equipment remains deferred unless evaluation shows it materially changes recommendation quality.

## Planning Decisions And Research Gaps


### Milestone 5: Evaluation, Optimization, And Cost Control

#### Repository Grounding

- Title: Milestone 4 closeout and Milestone 5 seed scope
  URL: local `docs/core/milestone.md`
  Source type: repository planning document
  Date added: 2026-06-25
  Related area: Milestone 5 evaluation gates, sidekick cleanup, equipment policy, authentication, persistence, and rate limiting
  Relevance: Captures the transition from completed Milestone 4 Features A-E into Milestone 5, including deferred golden weak-boss evals and user-requested improvements.
  Caveats/open questions: Rewritten on 2026-06-25 as the active Milestone 5 plan.

- Title: LLM provider factory
  URL: local `src/workflow/llm.py`
  Source type: repository source file
  Date added: 2026-06-25
  Related area: provider/model selection
  Relevance: Shows OpenRouter is already the default provider path and that provider/model selection is centralized through environment-driven settings.
  Caveats/open questions: Milestone 5 needs clearer role-specific model configuration and provider/model metadata in eval reports.

- Title: Recommendation legality and final validation code
  URL: local `src/workflow/legality.py`, local `src/workflow/nodes/format.py`
  Source type: repository source files
  Date added: 2026-06-25
  Related area: backend guardrails
  Relevance: Existing code already validates roster ownership, sidekick slots, skill/passive existence, Stellar Awakening gates, boss-affinity fidelity, recommendation shape, and no win-probability claims.
  Caveats/open questions: Milestone 5 should audit which prompt guardrails can be reduced once backend tests fully cover fixed constraints.

- Title: Curated weak superboss scope
  URL: local `src/etl/scraper.py`
  Source type: repository source file
  Date added: 2026-06-25
  Related area: golden weak-boss eval set
  Relevance: Defines the current curated weak superboss candidates: Zennon Ogre's Shadow, Flame Eater, Flame Eater female variant, Nameless Girl, Mimi, Cradle System, and Insula Ventorum.
  Caveats/open questions: Milestone 5 still needs to choose the exact five golden eval bosses.

#### External Model And Cost References

- Title: OpenRouter public model metadata API
  URL: https://openrouter.ai/api/v1/models
  Source type: provider API metadata
  Date added: 2026-06-25
  Related area: OpenRouter model selection and cost planning
  Relevance: Public metadata inspected on 2026-06-25 showed `moonshotai/kimi-k2.6` available with structured outputs and tool support, 262144-token context, input pricing around USD 0.66 per 1M tokens, output pricing around USD 3.41 per 1M tokens, and cached-input pricing around USD 0.144 per 1M tokens.
  Caveats/open questions: Pricing, availability, context windows, provider routing, and supported parameters can change. Recheck immediately before release testing or public beta.

- Title: Usage Accounting
  URL: https://openrouter.ai/docs/cookbook/administration/usage-accounting
  Source type: official OpenRouter documentation
  Date added: 2026-06-30
  Related area: Milestone 5 recommendation-run observability, token accounting, and cost gates
  Relevance: Documents that OpenRouter responses automatically include native-tokenizer prompt, completion, reasoning, cached-token, and total-token counts plus charged cost; streaming responses carry usage in the final SSE message, and generation IDs can support later usage audits.
  Caveats/open questions: The application still needs to verify which LangChain response metadata fields preserve this provider usage object, how transport retries are aggregated, and how a missing final streaming usage message is classified.

- Title: Structured Outputs
  URL: https://openrouter.ai/docs/guides/features/structured-outputs
  Source type: official OpenRouter documentation
  Date added: 2026-06-30
  Related area: Milestone 5 analyzer response contract and bounded correction loop
  Relevance: Documents JSON Schema response enforcement for compatible models through response_format, recommends strict schemas, and supports streaming structured output. It also documents explicit failure cases for unsupported models and invalid schemas.
  Caveats/open questions: Structured-output support is model/provider dependent. Release configuration must verify the selected model's supported parameters and require compatible routing; schema enforcement reduces formatting failures but does not replace backend semantic and legality validation.

- Title: Models
  URL: https://openrouter.ai/docs/guides/overview/models
  Source type: official OpenRouter documentation
  Date added: 2026-06-30
  Related area: Milestone 5 model capability filtering, pricing snapshots, and release qualification
  Relevance: Documents the Models API fields for stable model identity, context and completion limits, pricing, supported parameters, and provider metadata. It also supports filtering by capabilities such as structured outputs and sorting by price, latency, throughput, or context size.
  Caveats/open questions: Model inventory, pricing, limits, and supported parameters are mutable external facts. Milestone acceptance should require a captured release-time metadata snapshot rather than hard-code today's catalog claims.


#### Feature B/C Grasta Legality And Build Strategy

- Title: Grasta overview and personality recommendations
  URL: https://anothereden.wiki/Grasta#Personality_Grastas-1
  Source type: community wiki mechanics reference
  Date added: 2026-06-29
  Related area: Milestone 5 Features B-C, personality compatibility, Dormant sharing, and Grasta mules
  Relevance: States that personality Grasta require a matching holder personality, Dormant Ore enables party sharing, and community terminology uses Grasta mule/carrier for reserve holders. It also documents the general rule that Tier 3 Grasta are unique.
  Caveats/open questions: The wiki is community-maintained; exact damage-ranking claims should remain guidance unless separately grounded in formula references.

- Title: Grasta Attack list
  URL: https://anothereden.wiki/w/Grasta_Attack
  Source type: community wiki data/reference page
  Date added: 2026-06-29
  Related area: Milestone 5 Features B-C, Grasta variant identity, acquisition cardinality, weapon/personality triggers, and Pain/Poison conditions
  Relevance: Lists distinct Almighty Power personality variants, matching-personality party sharing, T2 Pain/Poison weapon variants with 30% conditional damage, and explicit infinite-copy markers for exceptional Tier 3 Grasta.
  Caveats/open questions: The current ETL discards variant identity by merging rows on Grasta.name; implementation must preserve personality/weapon discriminator and finite-versus-repeatable acquisition metadata.

- Title: Personality Special Grasta
  URL: https://anothereden.wiki/Grasta#Valor_Chants-0
  Source type: community wiki mechanics reference
  Date added: 2026-06-29
  Related area: personality-gated special Grasta
  Relevance: States that Personality Special Grasta can only be equipped by characters with the matching personality.
  Caveats/open questions: Special-slot Personality Grasta must not be conflated with regular Attack-category Almighty Power variants.

- Title: Grasta setup guide
  URL: https://www.reddit.com/r/AnotherEdenGlobal/comments/j4gv69/grasta_setup_guide/
  Source type: community strategy guide
  Date added: 2026-06-29
  Related area: Pain/Poison setters, multiplicative stacking, and role-oriented build examples
  Relevance: Provides community examples of repeated Pain/Poison multipliers, status-setter dependencies, and role-specific exceptions.
  Caveats/open questions: Older guide with version-specific examples; use for heuristic candidate ranking and test scenarios, not immutable mechanics or current character coverage.

- Title: Recommended Grasta
  URL: https://www.reddit.com/r/AnotherEdenGlobal/comments/eu264p/recommended_grasta/
  Source type: community discussion
  Date added: 2026-06-29
  Related area: early-game and role-based Grasta recommendations
  Relevance: Supplies community context for offensive versus support Grasta choices.
  Caveats/open questions: Old discussion predating later Grasta and Ore systems; weak evidence for current deterministic policy.

- Title: Grasta questions
  URL: https://gamefaqs.gamespot.com/boards/237373-another-eden-the-cat-beyond-time-and-space/78610985
  Source type: community discussion
  Date added: 2026-06-29
  Related area: Tier 3 availability and role-oriented Grasta selection
  Relevance: Captures player questions and community explanations around limited high-tier Grasta and offensive/support setups.
  Caveats/open questions: Archived discussion and secondary evidence; the current wiki should govern acquisition cardinality.

- Title: Grasta, Grasta Enhancements, and You
  URL: https://www.reddit.com/r/AnotherEdenGlobal/comments/s4swv5/grasta_grasta_enhancements_and_you/
  Source type: community strategy discussion
  Date added: 2026-06-29
  Related area: Ore allocation, Pain/Poison build inventory, and specialized fight setups
  Relevance: Provides practical community estimates for Pain/Poison and Dormant Ore allocation across damage dealers.
  Caveats/open questions: Version-dependent and inventory-opinionated; suitable for ranking heuristics, not hard legality.

- Title: Need a rewind on Grasta, badge, and damage setup
  URL: https://www.reddit.com/r/AnotherEdenGlobal/comments/1adst9c/need_a_rewind_on_grasta_badge_and_damage_setup/
  Source type: community strategy discussion
  Date added: 2026-06-29
  Related area: multiplicative Pain/Poison examples and additive support Grasta stacking
  Relevance: Shows a community calculation model that treats Pain/Poison and offensive Ores as multipliers while grouping Max HP, element, and Almighty support bonuses additively.
  Caveats/open questions: The post itself asks unresolved formula questions; do not treat every calculation as authoritative without a formula source.

- Title: Help and Questions weekly megathread
  URL: https://www.reddit.com/r/AnotherEdenGlobal/comments/1f5ny6x/help_questions_weekly_megathread/
  Source type: community support thread
  Date added: 2026-06-29
  Related area: contemporary player build advice
  Relevance: User-provided supporting context for role-based DPS, support, and reserve-mule builds.
  Caveats/open questions: Large mixed-topic thread; no stable authoritative rule should depend on it without a direct supporting comment and corroboration.

- Title: Top auto-attackers discussion
  URL: https://steamcommunity.com/app/1252600/discussions/0/3476233614741453118/
  Source type: community discussion
  Date added: 2026-06-29
  Related area: situational Grasta/Ore examples
  Relevance: Shows practical build examples combining elemental Grasta with Bull's Eye and enemy-count Ores.
  Caveats/open questions: Focused on auto-attack farming rather than superboss lineups; retain only as weak contextual evidence.

#### Feature C Repository Failure Grounding

- Title: Grasta row identity and loader merge audit
  URL: local `src/etl/models.py`, local `src/etl/loader.py`, local `data/parsed/v1.0.0/indexes/grasta_attack.json`
  Source type: repository source and parsed artifacts
  Date added: 2026-06-29
  Related area: Milestone 5 Features B-C, Grasta compatibility and account-copy legality
  Relevance: Parsed artifacts contain many Almighty Power personality variants and Enhance-if-Max-HP variants, while the loader merges every variant as `(:Grasta {name})`. This collapses distinct rows and creates incorrect multi-trait requirements on one node.
  Caveats/open questions: Schema identity must change before compatibility validation or candidate generation can be trusted; migration and replay requirements must be planned.

- Title: Akane Alter canonical-name audit
  URL: local `data/parsed/v1.0.0/indexes/characters.json`, local `data/parsed/v1.0.0/characters/akane_alter_blooming_blade.json`, local `src/workflow/normalize.py`
  Source type: repository source and parsed artifacts
  Date added: 2026-06-29
  Related area: canonical roster identity and analyzer legality
  Relevance: Akane Alter exists as `Akane (Alter),Blooming Blade`; analyzer output shortened it to `Akane (Alter)`, which final legality treated as unknown. This is canonical-name drift, not missing parsed coverage.
  Caveats/open questions: Candidate output should use stable IDs or exact canonical names; fuzzy normalization should remain an input convenience rather than an output repair mechanism.

#### Candidate-Constrained Architecture Replan

- Title: Broad candidate preparation and analyzer projection audit
  URL: local `src/workflow/candidates.py`, local `src/workflow/nodes/analyze.py`
  Source type: repository source files
  Date added: 2026-07-01
  Related area: Milestone 5 deterministic candidate engine rewrite
  Relevance: Current code retrieves the complete eligible roster, all character skills/passives, and all Grasta before prompt projection; the analyzer path permits a 450,000-byte payload and an initial call plus two correction rounds. This proves stable-ID validation concepts exist but does not satisfy the compact scored-candidate architecture.
  Caveats/open questions: The implementation is a superseded prototype. Reusable identity and validation helpers may survive only if they pass the rewritten acceptance gates.

- Title: Generated-Cypher recommendation retrieval audit
  URL: local `src/workflow/nodes/cypher.py`, local `src/workflow/nodes/validate.py`, local `src/workflow/graph.py`
  Source type: repository source files
  Date added: 2026-07-01
  Related area: production recommender retrieval boundary
  Relevance: Shows that current lineup requests still pass through generated Cypher and LLM semantic validation before candidate analysis, adding cost and nondeterministic retrieval to a legality-critical path.
  Caveats/open questions: Dynamic GraphRAG remains useful for exploratory questions but must be separated from production lineup generation.

- Title: Existing legality, candidate, correction, and partial-output tests
  URL: local `src/workflow/legality.py`, local `tests/workflow/test_candidates.py`, local `tests/workflow/test_feature_c_correction.py`, local `tests/workflow/test_feature_c_partial_output.py`
  Source type: repository source and test files
  Date added: 2026-07-01
  Related area: reusable guardrails and regression starting point
  Relevance: Existing tests cover ownership, skills, SA gates, Grasta/equipment legality, stable candidate IDs, independent validation, correction caps, and partial output. They provide regression assets but not role scoring, template generation, bounded beam search, compact-projection leakage, or deterministic degraded fallback coverage.
  Caveats/open questions: Test fixtures must be rewritten or extended around the new full-backend and compact-analyzer contracts.

- Title: Observed failed OpenRouter recommendation run
  URL: unavailable; user-supplied incident measurement
  Source type: user-provided operational observation
  Date added: 2026-07-01
  Related area: Milestone 5 token and cost baseline
  Relevance: A broad-context run with retries consumed approximately 601,000 tokens and ended with no fully valid lineup. It motivates the project policy requiring at least 90% paid-run reduction and a 40,000-token hard analyzer ceiling.
  Caveats/open questions: The run artifact and exact per-attempt usage breakdown were not provided. Preserve it as an approximate baseline and do not rerun the expensive failure merely to recreate it.

#### Planning Decisions

- Planning decision on 2026-07-01: Rewrite and resequence Milestone 5 around deterministic candidate generation and cost control rather than create a new milestone. Preserve completed sidekick cleanup, treat identity/cardinality work as awaiting verification, and classify the current broad candidate implementation as a superseded prototype.
- Planning decision on 2026-07-01: Production lineup recommendations use deterministic typed Neo4j retrieval and do not call PLAN, generated Cypher, or LLM retrieval validation. Dynamic GraphRAG remains a separate exploratory mode.
- Planning decision on 2026-07-01: Backend owns hard rejection, contextual role and skill scoring, build packages, candidate generation, full-lineup scoring, validation, and cost gates. Analyzer owns ranking, bounded strategy refinement, supplied skill choice, and explanation.
- Planning decision on 2026-07-01: Analyzer may propose at most one hero swap per lineup from backend-supplied `allowed_swaps`. Backend re-scores and revalidates it, rejects invalid or lower-scoring swaps, and restores the original candidate.
- Planning decision on 2026-07-01: Use a hybrid role model. A versioned local artifact is canonical for taxonomy, deterministic rules, evidence, confidence, and curated overrides; ETL materializes reproducible Skill/PassiveSkill evidence into Neo4j; query time computes contextual RoleScores.
- Planning decision on 2026-07-01: Initial role labeling uses deterministic rules plus curated overrides. Optional OpenRouter-assisted developer batch suggestions require human review and never run during live recommendations or normal ETL.
- Planning decision on 2026-07-01: Maintain a full internal backend candidate object and a compact analyzer projection containing only referenced legal lineups, shortlists, packages, swaps, constraints, and compact catalogs.
- Planning decision on 2026-07-01: Use a maximum of two analyzer calls: initial plus one fragment-only correction. Invalid analyzer choices fall back to legal backend defaults; total analyzer failure may return clearly labeled legal backend candidates in degraded mode.
- Planning decision on 2026-07-01: Confirmed no-weakness bosses use neutral-matchup scoring without a missing-weakness penalty. Unknown/incomplete affinity lowers confidence; null/absorb primary plans are rejected; primary DPS requires neutral-or-better usable damage.
- Planning decision on 2026-07-01: Skill selection is two-stage: four-to-six per-role shortlists before lineup generation and lineup-aware default three-to-four-skill packages used to prove capability coverage and readiness.
- Planning decision on 2026-07-01: `late_game_assumed` is the required MVP item policy. Backend emits legality-checked build packages with transparent unverified-ownership labels. `declared_owned_only` is deferred; `generic_only` remains fallback-compatible.
- Planning decision on 2026-07-01: Versioned scoring uses top-eight role pools with bounded boss-counter exceptions, capability templates, beam width at most 50 per expansion, full-lineup scoring, deduplication, and diversity filtering to retain up to ten legal candidates.
- Planning decision on 2026-07-01: Burst, sustain, and hybrid templates express mandatory/optional capability coverage rather than rigid hero-role slots. Selected skill/build evidence, legal reserves, and legal sidekick behavior prove coverage.
- Planning decision on 2026-07-01: Sparse inputs produce diagnostics; partial viability returns partial valid results; one to four candidates may reach the analyzer; zero candidates return structured causes without an analyzer call.
- Planning decision on 2026-07-01: Initial analyzer gates are 25k input/4k output for the initial call, 8k input/2k output for correction, 30k cumulative target, and 40k cumulative hard acceptance ceiling. Budget failure uses deterministic degraded fallback.
- Planning decision on 2026-07-01: Paid testing is blocked until deterministic legality, scoring, packages, templates, beam bounds, projection, swaps, partial-output, and offline golden cases pass. Paid judge use is offline and only after deterministic validity.
- Planning decision on 2026-07-01: Plan updates to `docs/guides/ETL_GUIDE.md` and `docs/guides/recommendation-validation.md` during implementation. Authentication, persistence, rate limiting, and deployment safeguards follow the proven recommendation core.


- Planning decision on 2026-06-29: Expanded Feature C must create and maintain docs/guides/recommendation-validation.md covering schema/ETL readiness, candidate inspection, Mimi smoke tests, correction-round diagnostics, partial-result behavior, failure classification, and manual-verification reporting.
- Planning decision on 2026-06-29: Until gamer beta feedback provides stronger role-by-role build evidence, candidate ranking should prefer Pain/Poison Grasta on active damage dealers when a reliable status setter exists and distinct Dormant-shareable Grasta on reserve mules. This is a transparent default heuristic, not hard legality; boss-, role-, or skill-specific exceptions are allowed when explained.
- Superseded planning decision from 2026-06-29: Recommendation correction was capped at two conditional batched rounds after initial analysis, for at most three analyzer calls per request. Superseded on 2026-07-01 by the maximum-two-call policy: initial analysis plus one fragment-only correction. Valid lineups are frozen between rounds; only remaining invalid lineups and precise allowed-candidate feedback are sent for correction. No correction call runs when initial output is fully valid.
- Planning decision on 2026-06-29: Hard recommendation fields must use backend-provided stable candidate IDs rather than model-authored names. Candidate bundles must constrain characters, skills, passives, sidekicks, equipment assumptions, Grasta variants, citations, and boss facts; display names are resolved after validation. Fuzzy name normalization remains an input convenience and must not repair analyzer output.
- Planning decision on 2026-06-29: Every displayed lineup must pass all hard legality checks. After targeted correction retries, invalid lineups are discarded; warnings may explain rejected or replaced proposals but must not present incompatible characters, skills, equipment, or Grasta as part of a valid lineup. Valid lineups may still be returned as a partial result set.
- Planning decision on 2026-06-29: Reopen Feature B as a data-contract prerequisite. Feature B must preserve distinct Grasta variants, personality/weapon discriminators, finite-versus-repeatable acquisition cardinality, and canonical character identities. Feature C will consume those corrected facts for candidate-constrained generation, independent lineup validation, targeted retries, partial valid results, and warnings.
- Planning decision on 2026-06-25: Use free/local models for fast development, including the current `nvidia/nemotron-3-super-120b-a12b:free` OpenRouter path when useful.
- Planning decision on 2026-06-25: Use `moonshotai/kimi-k2.6` as the intended paid OpenRouter model for staging, evaluation, release testing, and controlled beta/demo traffic unless Milestone 5 eval evidence selects a better paid default.
- Planning decision on 2026-06-25: Paid AI judge calls should run for offline evaluation/report generation, not for every live user recommendation.
- Planning decision on 2026-06-25: Start public demo or controlled Discord beta planning with an RM50/month OpenRouter ceiling. If usage hits the ceiling, pause or disable paid calls first, then decide whether increasing the ceiling is worth the portfolio value.
- Planning decision on 2026-06-25: Backend deterministic validation should own fixed guardrails such as 4-frontline/2-reserve shape, no duplicate heroes, sidekick slot legality, owned roster enforcement, skill/passive existence, Stellar Awakening gates, skill-count limits, boss-affinity fidelity, equipment uniqueness when named, and no win-probability claims.
- Planning decision on 2026-06-25: User clarification promoted Feature B from prose-only equipment policy into a build-slot output contract: each character should carry one weapon, one armor, and three Grasta assumptions; weapon and armor uniqueness is per lineup only; Grasta may be reused, including repeated copies; Grasta compatibility and pain/poison-dependent damage setup need deterministic validation where graph data supports it or explicit caveats where it does not. Superseded in part on 2026-06-29: reuse is now governed by exact-variant acquisition cardinality, so unique Tier 3 variants cannot repeat within one lineup.
- Superseded in part on 2026-07-01: The 2026-06-25 policy assigned dynamic hero selection to AI. The backend now generates and scores legal lineups; AI ranks them, chooses from supplied skill shortlists, proposes at most one bounded swap, and explains strategy.
- Planning decision on 2026-06-25: Milestone 5 implementation order should start with sidekick/character cleanup, weapon/armor/Grasta policy, and backend guardrail audit before golden evals and paid OpenRouter/Kimi setup, because deterministic correctness makes paid staging tests cheaper and more meaningful.

#### Research Gaps

- Validate the frontline Pain/Poison and reserve Grasta-mule default with experienced Another Eden players during the planned beta; record counterexamples and revise ranking heuristics without weakening hard compatibility or acquisition-cardinality rules.
- Determine actual token usage and RM cost per recommendation run after context compression.
- Determine whether `moonshotai/kimi-k2.6` remains the best paid model after comparing staging eval outputs against at least one cheaper or stronger OpenRouter alternative.
- Determine per-user and global request limits that keep a 20-30 player Discord beta inside the RM50/month budget.
- Determine the minimum authentication and persistence approach for controlled beta feedback collection.

### Milestone 5 Transition Notes

- Planning decision on 2026-06-24: Milestone 4 is closed for Features A-E. The original Feature F evaluation-gates work moves into Milestone 5 because the recommendation contract, final legality gate, boss-affinity fidelity gate, and compact/expandable UI are now verified.
- Planning decision on 2026-06-24: Milestone 5 should include a data-hygiene task to remove sidekick-name records that also appear as `Character` nodes, using exact name overlap between `Character` and `Sidekick` nodes as the first detection rule before any destructive graph cleanup is implemented.
- Planning decision on 2026-06-24: Milestone 5 should decide whether weapon, armor, and Grasta recommendations remain late-game-access assumptions or become inventory-aware constraints. The seed policy to evaluate is one weapon and one armor use per character per lineup, while Grasta recommendations may be reused many times.
- Planning decision on 2026-06-24: Milestone 5 should evaluate authentication, user data persistence, and rate limiting before live deployment so public traffic cannot create uncontrolled LLM/API spend.

- Planning decision on 2026-06-09: Milestone 4 should treat the provided battle-mechanics references as primary RAG sources that the LLM retrieves before making lineup recommendations. Exact deterministic battle simulation remains out of scope unless a later planning decision adds the required data and tests.
- Planning decision on 2026-06-09: Milestone 4 should scrape/cache the full referenced mechanics pages into project artifacts, then curate section-by-section mechanics chunks for cleaner LLM retrieval. Neo4j or retrieval ingestion should replay from curated local artifacts so mistakes can be corrected without repeated live scraping.
- Planning decision on 2026-06-09: Curated mechanics corpus entries should be stored in Neo4j as `MechanicReference` nodes to improve GraphRAG retrieval, source attribution, scalability, and hallucination resistance.
- Planning decision on 2026-06-09: Manual curation should target a recommendation-focused golden mechanics corpus, not full encyclopedia coverage. Full deterministic battle simulation and exhaustive mechanics modeling should be deferred to a later roadmap item.
- Planning decision on 2026-06-10: First-pass superboss viability measurement should use a transparent rubric that prioritizes boss weakness coverage while also scoring lineup synergy, defensive resistance/mitigation against boss damage, sustain, MP pressure, and upgrade burden.
- Planning decision on 2026-06-10: Recommendation output should prefer top 3 candidate lineups with tradeoffs rather than one "best" lineup. The top set should prefer burst, sustain, and hybrid archetypes when viable, because many superbosses do not require timer-based clears and players may adapt suggestions to their own battle execution.
- Deferred idea on 2026-06-10: Alternative character recommendations may be useful for upgrade and pull planning, including not-owned suggestions, Stellar Awakening-gated suggestions, and recommended skill-slot choices. This should be deferred beyond the current Milestone 4 plan so the active roadmap can focus on top 3 owned-roster lineups for beating selected bosses.
- Planning decision on 2026-06-10: Milestone 4 should position the recommender as a boss-aware team-building navigation tool, not a deterministic prediction tool. Scoring should be used for transparent fit/ranking and explanation, not numeric win probability.
- Planning decision on 2026-06-10: Milestone 4 may assume the target player has general late-game Grasta/Ore/equipment access because superboss recommendation users are expected to be endgame or near-endgame players. Build advice should still mark rare/specific assumptions and avoid requiring explicit full inventory entry.
- Planning decision on 2026-06-10: Milestone 4 roster input should require owned character names and optionally accept Stellar Awakening state and sidekick ownership. Light/Shadow detail can be deferred unless a specific legality or skill-slot requirement makes it necessary.
- Planning decision on 2026-06-10: Milestone 4 should generate detailed structured recommendation data internally while rendering a compact default result. Users should be able to expand lineup and character details to inspect recommended skills, equipment/build notes, sidekick reasoning, boss counterplay, risks, and citations.
- Planning decision on 2026-06-10: Milestone 4 evaluation should prioritize deterministic core legality and factuality tests before recommendation quality judge tests. Quality judging should run only after the recommendation contract can reliably prevent impossible or hallucinated outputs.
- Planning decision on 2026-06-10: Milestone 4 should use a small golden evaluation set of 5 curated weak superbosses. Intermediate and strong superboss evaluation tiers should be designed for future extension but explicitly deferred until the core navigator is stable.
- Determine the minimum deterministic scoring model that can support "can plausibly defeat this superboss" without claiming exact simulation.
- Determine what player roster fields are required beyond ownership: Stellar Awakening state, Light/Shadow amount, sidekick ownership, Grasta/Ore inventory, equipment inventory, manifest/progression unlocks, and preferred assumptions for missing inventory data.
- Determine whether current character skill/passive text is sufficient for extracting role tags such as DPS, healer, cleanse, mitigation, zone setter, pain/poison setter, breaker, AF support, and MP sustain.
- Determine whether additional ETL is needed for character stats, badges, manifest weapons, VC grastas, or sidekick equipment before recommendation quality can be evaluated fairly.

## Source Quality Notes

- Historical Milestone 5 decisions remain in this log for auditability. Where the 2026-07-01 candidate-constrained rewrite conflicts with earlier three-call correction, broad-context generation, or AI-owned hero-search policy, the 2026-07-01 locked decisions supersede the earlier policy.

- The Another Eden Wiki is a community-maintained source. It is appropriate for this portfolio project's game-mechanics planning, but recommendations should cite retrieved source facts and carry uncertainty when data is incomplete.
- Exact damage, healing, speed, and AF calculations are complex and depend on stats, equipment, buffs, debuffs, enemy defenses, and player inventory. Milestone 4 should avoid promising exact battle simulation unless additional data and tests are planned.
