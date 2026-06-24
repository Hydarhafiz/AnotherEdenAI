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

- The Another Eden Wiki is a community-maintained source. It is appropriate for this portfolio project's game-mechanics planning, but recommendations should cite retrieved source facts and carry uncertainty when data is incomplete.
- Exact damage, healing, speed, and AF calculations are complex and depend on stats, equipment, buffs, debuffs, enemy defenses, and player inventory. Milestone 4 should avoid promising exact battle simulation unless additional data and tests are planned.
