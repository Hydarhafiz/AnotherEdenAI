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

#### Feature C2 Defensive Capability Expansion

- Title: Status Effects
  URL: https://www.anothereden.wiki/w/Status_Effects
  Source type: user-provided community wiki mechanics reference
  Date added: 2026-07-08
  Related area: Milestone 5 Features C2-C4 defensive, offensive/support, and dependency vocabulary
  Relevance: Grounds distinct defensive mechanics and the C3 concepts Buff Reversal, Debuff Reversal, Break variants, Expose, Invert, Eagle Eyes, Kaleido, Link, Lunatic Copy/Charge/Mind's Eye, Mental Focus, Overcritical, Overthrow, Singular Focus, and Barrier Pierce. It also records mechanic-specific conditions and consumption behavior that must remain separate from the atomic capability identity.
  Caveats/open questions: Successfully inspected on 2026-07-14. This community-maintained index is suitable for taxonomy planning, but individual Skill/PassiveSkill/Sidekick source text remains the proof for recipient, direction, target, magnitude, duration, stacking, trigger, and dependencies. The page labels some effects as statuses while its own descriptions call some of them buffs; the capability taxonomy must not infer removal/transfer behavior from the page category alone.

- Title: Tank Role
  URL: https://anothereden.wiki/w/Tank_Role
  Source type: user-provided community wiki role/reference page
  Date added: 2026-07-08
  Related area: Milestone 5 Feature C2 Rage/taunt, Cover, Guard, Hold Ground, dodge, Stalk, knockback immunity, and contextual tank-role derivation
  Relevance: Provides candidate examples for expanding atomic tanking capabilities while keeping permanent character-role labels out of ETL.
  Caveats/open questions: The page could not be retrieved through the available browsing path during this planning session. The page is a role-oriented index, so individual Skill/PassiveSkill source text remains authoritative for atomic proof and target semantics.

- Title: Revival Role
  URL: https://anothereden.wiki/w/Revival_Role
  Source type: user-provided community wiki role/reference page
  Date added: 2026-07-08
  Related area: Milestone 5 Feature C2 ally revival, self revival, and sidekick revival coverage
  Relevance: Identifies revival as a defensive recovery mechanic that can materially change lineup recovery but must remain distinct from prevention mechanics such as Hold Ground.
  Caveats/open questions: The page could not be retrieved through the available browsing path during this planning session. Character Skill/PassiveSkill and SidekickSkill review coverage may require separate record-type support, which the current C1 tooling does not provide for sidekicks.

- Title: Sacrificial Heart Stacking
  URL: https://www.anothereden.wiki/w/Sacrificial_Heart_Stacking
  Source type: user-provided community wiki character/mechanics reference
  Date added: 2026-07-08
  Related area: Milestone 5 Feature C2 self and adjacent-ally target scopes
  Relevance: User identified it as evidence that effects may distinguish self, adjacent allies, and combined self-plus-adjacent targeting.
  Caveats/open questions: The page could not be retrieved through the available browsing path; exact source text must be verified from parsed facts or human review before materialization.

- Title: Guiding Vow Rite
  URL: https://www.anothereden.wiki/w/Guiding_Vow_Rite
  Source type: user-provided community wiki character/mechanics reference
  Date added: 2026-07-08
  Related area: Milestone 5 Feature C2 adjacent-ally target scopes
  Relevance: User identified it as another targeted example for effects involving left/right adjacent allies.
  Caveats/open questions: The page could not be retrieved through the available browsing path; exact source text must be verified from parsed facts or human review before materialization.

- Title: Lady Vesper
  URL: https://www.anothereden.wiki/w/Lady_Vesper
  Source type: user-provided community wiki character reference
  Date added: 2026-07-08
  Related area: Milestone 5 Feature C2 self and adjacent-ally target scopes
  Relevance: User identified this character page as containing effects whose target scope is self, adjacent allies, or both.
  Caveats/open questions: The page could not be retrieved through the available browsing path; individual Skill/PassiveSkill text remains the atomic source of truth.

- Title: Assemble
  URL: https://www.anothereden.wiki/w/Assemble
  Source type: user-provided community wiki skill/mechanics reference
  Date added: 2026-07-08
  Related area: Milestone 5 Features C2-C4 conditional target eligibility
  Relevance: User identified it as evidence that an additional effect may apply only when an ally satisfies a condition such as weapon type.
  Caveats/open questions: The page could not be retrieved through the available browsing path. Conditional target eligibility should be reviewed against captured source text and kept separate from basic target scope.

#### Feature C3 Offensive And Support Taxonomy Replan

- Title: Mental Focus (Status Effect)
  URL: https://www.anothereden.wiki/w/Mental_Focus_(Status_Effect)
  Source type: user-provided community wiki mechanics reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 Mental Focus and Max MP scaling
  Relevance: User identified this as the dedicated source for Mental Focus. The accessible Status Effects and Damage Formula pages corroborate that it raises magic damage based on each recipient's Max MP and that the effect has its own stacking/cap behavior.
  Caveats/open questions: The dedicated page could not be retrieved through the available browsing path. Do not lock its exact coefficient, cap, stacking, transfer, or overwrite behavior beyond what the accessible Damage Formula page supports; skill-level magnitude and recipient scope still require captured source evidence.

- Title: Singular Focus
  URL: https://www.anothereden.wiki/w/Singular_Focus
  Source type: user-provided community wiki mechanics reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 Singular Focus and Max MP scaling
  Relevance: User identified this as the dedicated source for Singular Focus. The accessible Status Effects page corroborates the atomic distinction from Mental Focus: Singular Focus increases physical rather than magical damage based on Max MP.
  Caveats/open questions: The dedicated page returned HTTP 403 through the available browsing path, and the accessible Damage Formula page did not contain a Singular Focus section. Exact coefficient, cap, stacking, transfer, and overwrite behavior remain a research gap; skill-level recipient scope and magnitude require captured source evidence.

- Title: Damage Formula
  URL: https://anothereden.wiki/w/Damage_Formula
  Source type: user-provided community wiki mechanics/formula reference already present in this source log
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 weakness multiplier, Mental Focus, Eagle Eyes, Overthrow, Copy, and attack-again semantics
  Relevance: The inspected page distinguishes weakness-multiplier modification from general damage amplification; describes Mental Focus, Eagle Eyes, and Overthrow as separate effects; and distinguishes repeat moves from Copy and conditionally triggered attack-again behavior. These distinctions support atomic capability identities without requiring exact damage simulation.
  Caveats/open questions: The formulas contain mechanic-specific stacking and calculation details that are out of scope for C3 materialization. C3 should capture capability, explicit magnitude/qualifiers, and dependencies only; it must not implement formula evaluation or turn-by-turn simulation. Singular Focus and Overcritical are not detailed on this page.

- Title: Kaleido
  URL: https://www.anothereden.wiki/w/Kaleido
  Source type: user-provided community wiki mechanics reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 element conversion
  Relevance: User identified this as the dedicated Kaleido reference. The accessible Status Effects page corroborates that Kaleido changes a recipient's attacks to a specified element and distinguishes it from attack-type conversion and weakness/resistance changes.
  Caveats/open questions: The dedicated page could not be retrieved through the available browsing path. Exact exclusions, overwrite rules, eligible attack sources, and interactions with Link/Charge must be proven from accessible reference text or captured source fixtures before they become locked mechanics.

- Title: Barrier Piercing
  URL: https://anothereden.wiki/w/Barrier_Piercing
  Source type: user-provided community wiki mechanics reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 barrier bypass, fixed damage, and target-defense bypass boundaries
  Relevance: User identified this as the dedicated source for Barrier Pierce and noted adjacent but distinct fixed-damage and ignore-target-defense topics. The accessible Status Effects page corroborates that Barrier Pierce ignores an enemy Barrier and that barriers have multiple reduction/consumption forms.
  Caveats/open questions: The dedicated page could not be retrieved through the available browsing path. Barrier Pierce, fixed damage, and ignore-target-defense must remain separate capabilities unless source text independently proves each one; exact status-immunity bypass and barrier-consumption interactions require targeted fixtures.

- Title: Divine Vessel
  URL: https://www.anothereden.wiki/w/Divine_Vessel
  Source type: user-provided community wiki skill reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 enemy-directed Buff Reversal
  Relevance: User identified this skill as an example of Buff Reversal applied to enemies, converting supported enemy buffs into corresponding debuffs. The accessible Status Effects page lists the affected classes as non-HP/MP stat increases, type resistance up, type/non-type attack up, equipped-character damage up, and critical damage up.
  Caveats/open questions: The dedicated skill page could not be retrieved through the available browsing path. Captured skill text must prove direction, target, duration, and prerequisites; C3 must not synthesize the converted debuffs as independent facts.

- Title: Lapine Heureuse
  URL: https://anothereden.wiki/w/Lapine_Heureuse
  Source type: user-provided community wiki skill reference
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 self/ally-directed Debuff Reversal
  Relevance: User identified this skill as an example of Debuff Reversal applied to self or party members, converting supported debuffs into corresponding buffs. The accessible Status Effects page lists the affected classes as non-HP/MP stat decreases, type resistance down, type/non-type attack down, equipped-character damage down, and critical damage down.
  Caveats/open questions: The dedicated skill page could not be retrieved through the available browsing path. Captured skill text must prove direction, target, duration, and prerequisites; C3 must not synthesize the converted buffs as independent facts.

- Title: Kaleidoscope
  URL: https://www.anothereden.wiki/w/Kaleidoscope
  Source type: user-provided community wiki skill reference and repository-cached parsed fact
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 Link/add-on attack semantics
  Relevance: The skill describes Link as a Crystal add-on attack after each attacking move, including attack-again moves. This supports a named Link capability with its own element/attack-type qualifiers, recipient scope, duration, and trigger relationship.
  Caveats/open questions: The live page request did not complete through the available browsing path, but equivalent Kaleidoscope text exists in the repository review corpus. Link must not be treated as Copy, attack again, or Chain merely because all may produce additional attacks or moves.

- Title: Lunatic - Copy
  URL: https://www.anothereden.wiki/w/Lunatic_-_Copy
  Source type: user-provided community wiki mechanics reference and repository-cached parsed fact
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 copied skill execution
  Relevance: The supplied reference and cached character facts state that Copy executes skills twice, with the copied execution having distinct MP, AF-gain, combo, move-counting, animation, and retarget behavior. C3 needs the named Copy capability without simulating those consequences.
  Caveats/open questions: The live page request did not complete through the available browsing path. Other effects with similar execution behavior require their own captured evidence and must not be labeled Lunatic Copy solely because they repeat a move.

- Title: Crimson Fire Claw
  URL: https://www.anothereden.wiki/w/Crimson_Fire_Claw
  Source type: user-provided community wiki skill reference and repository-cached parsed fact
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 Chain attacks
  Relevance: The supplied reference and cached Meryt fact identify a Chain Ability that activates when another ally uses a Fire attack, performs a Fire blunt attack, and has a per-turn activation limit. This distinguishes an ally-action-triggered Chain from Link, Copy, and attack-again effects.
  Caveats/open questions: The live page request did not complete through the available browsing path. Element/attack-type trigger eligibility and activation count are orthogonal evidence fields; Chain must not collapse them into its capability identity.

- Title: Turn Order
  URL: https://www.anothereden.wiki/w/Turn_Order
  Source type: user-provided community wiki mechanics/counting reference
  Date added: 2026-07-14
  Related area: Milestone 5 Features C3-C4 move counting, Copy, attack again, Link, and triggered additional moves
  Relevance: User identified this as the cross-cutting counting reference: Copy executions count twice, attack-again executions count as repeated moves, and Link is counted as an additional move. Repository-cached facts independently preserve examples of Copy and attack-again counting behavior.
  Caveats/open questions: The live page request did not complete through the available browsing path. C3 records named capabilities and explicit counting qualifiers only; it does not implement a turn engine, move counter, AF simulation, or trigger scheduler.

- Title: Doomsday Peace and Abaddon's Call
  URL: https://www.anothereden.wiki/w/Doomsday_Peace ; https://www.anothereden.wiki/w/Abaddon%27s_Call
  Source type: user-provided community wiki skill references and repository-cached parsed facts
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 Magic Overcritical
  Relevance: User identified these Mighty AC skills as the current Magic Overcritical examples and supplied the mechanic definition: its chance to double magical critical damage scales with magic critical rate above 100%, becoming guaranteed at the documented threshold. Cached Abaddon's Call text independently contains the same Magic Overcritical behavior.
  Caveats/open questions: The dedicated skill pages could not be retrieved through the available browsing path, and the accessible Status Effects snapshot exposed only physical Overcritical. Treat physical and magical Overcritical as separate capabilities, but preserve this source discrepancy and use captured skill text as the review evidence. C3 does not calculate proc probability or resulting critical damage.

- Title: Lunatic family references
  URL: https://anothereden.wiki/w/Lunatic#Lunatics_type_.28by_source.29 ; https://anothereden.wiki/w/Lunatic/Lunatics ; https://anothereden.wiki/w/Lunatic_-_Charge ; https://anothereden.wiki/w/Lunatic_-_Copy ; https://anothereden.wiki/w/Lunatic_-_Static ; https://anothereden.wiki/w/Lunatic_-_Mind%27s_Eye ; https://anothereden.wiki/w/Lunatic_-_Risktaker ; https://anothereden.wiki/w/Lunatic_-_Sacrifice
  Source type: user-provided community wiki mechanics references
  Date added: 2026-07-14
  Related area: Milestone 5 Features C3-C4 Lunatic activation, type, effects, timing, and limited-use dependencies
  Relevance: The accessible Status Effects page corroborates distinct Charge, Copy, Mind's Eye, Risktaker, Sacrifice, and Static/Discharge variants. Each variant has different explicit effects, while Lunatic activation itself may come from a basic-attack replacement, skill, passive, battle-start effect, or other source.
  Caveats/open questions: The dedicated pages were not retrievable through the available browsing path. C3 should capture Lunatic activation and separately proven atomic outcomes; C4 should own activation prerequisites, source restrictions, limited use, and timing. Exact damage, AF, combo, stat-conversion, self-damage, and turn execution remain outside simulation scope.

- Title: Oh No Help
  URL: https://www.anothereden.wiki/w/Oh_No_Help
  Source type: user-provided community wiki skill reference and repository-cached parsed fact
  Date added: 2026-07-14
  Related area: Milestone 5 Feature C3 channel-agnostic outgoing-damage and healing-effectiveness amplification
  Relevance: The cached source explicitly says that damage and healing of all party members increase by a percentage. This proves a narrow general outgoing-damage increase and a separate healing-effectiveness increase; it does not prove that the skill directly heals HP.
  Caveats/open questions: The dedicated live page could not be retrieved through the available browsing path. Prayer activation, interruption, party-composition scaling, duration, and other gates remain orthogonal C3/C4 evidence and must not be folded into either amplification capability.

#### Feature C3 Seed-Coverage Recovery

- Title: C3 taxonomy/corpus seed-coverage audit
  URL: local `src/etl/capability_taxonomy.json`, local `src/etl/capability_taxonomy.py`, local `data/parsed/**/*.json`, local `src/etl/review_batches/c3_offensive_support_batch_1_replacement.csv`
  Source type: repository implementation and parsed-artifact audit
  Date added: 2026-07-19
  Related area: Milestone 5 Feature C3 targeted seed review, strict atomic coverage, and batch recovery
  Relevance: The current review tooling can export/import generic and legacy migration batches, while the reviewed C3 replacement batch exists outside the canonical review artifact. A targeted C3 seed generator, explicit coverage diagnostics, and overlap-preserving batch refill are required before the reviewed batch can receive clean-batch credit.
  Caveats/open questions: Several C3 families have no usable parsed proposal in the audited corpus. Each gap requires a human-supplied canonical character or sidekick wiki page, exact fact name, and intended atomic capability; a general mechanics page may define semantics but cannot prove a skill-level fixture. No Neo4j materialization is planned until Feature C5.

#### Feature C3 MVP Scope Decision

- Title: C3 MVP taxonomy and expert-beta feedback decision
  URL: local `src/etl/capability_taxonomy.json`, local `src/etl/review_batches/c3_offensive_support_batch_1_replacement.csv`, local `data/parsed/**/*.json`
  Source type: repository audit and user planning decision
  Date added: 2026-07-19
  Related area: Milestone 5 Feature C3 MVP scope and post-MVP taxonomy extension
  Relevance: The active C3 implementation exposes 29 rule families, but four lack unambiguous source-backed seed coverage. The MVP retains 25 active families, retains the four vocabulary names only as reserved terms, and displays selected-lineup untagged facts as non-authoritative diagnostics for expert beta feedback.
  Caveats/open questions: `af_gauge_gain_up`, `invert_weakness_resistance`, `grant_copy`, and residual `follow_up_attack` are deliberately deferred. They need at least two parsed canonical character or sidekick facts and a misleading/cross-family example before a future taxonomy extension can review them.

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

#### Feature C Capability False-Positive Audit

- Title: Skill/passive taxonomy distribution and Sign of Collapse audit
  URL: local `data/parsed/v1.3.0/characters/*.json`, local `src/etl/role_taxonomy.json`, local `src/etl/role_taxonomy.py`
  Source type: repository source and parsed wiki artifacts
  Date added: 2026-07-05
  Related area: Milestone 5 Feature C capability quality gate and Feature D dependency
  Relevance: The 2,255 parsed Skill/PassiveSkill facts contain 1,850 tagged facts, including 577 `zone_setter`, 477 `mitigation_shield_barrier`, and 1,399 `primary_dps` assignments. Sign of Collapse was falsely labeled as zone setting and mitigation because broad patterns matched an awakened-zone prerequisite and enemy resistance reductions. The same description also shows that incidental words inside Link and conditional clauses can create false direct-role evidence.
  Caveats/open questions: Counts describe the current broad-rule prototype, not ground-truth prevalence. Human-reviewed stratified fixtures are required before precision or coverage can be claimed.

- Title: Sign of Collapse source fact
  URL: https://anothereden.wiki/w/Sign_of_Collapse
  Source type: community wiki skill reference and repository-cached parsed fact
  Date added: 2026-07-05
  Related area: direction-aware capability extraction
  Relevance: Grounds the distinction between enemy resistance debuffs, granted Link/Break behavior, and a prerequisite requiring Awakened Torn Earth Stance. It does not prove that the skill deploys a zone or grants party mitigation.
  Caveats/open questions: The repository-cached character artifact is the reproducible test input; the live wiki can change and should be refreshed through normal ETL source attribution.

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

- Planning decision on 2026-07-08: Feature C2 will model distinct, source-provable defensive mechanics rather than ETL-level umbrella labels such as `mitigation`, `healing`, or permanent tank/healer roles. Feature D will deterministically derive contextual coverage and RoleScores from the proven atomic mechanics; the analyzer LLM may explain or rank supplied candidates but may not invent or independently certify mandatory defensive coverage.
- Planning decision on 2026-07-08: Feature C2 will expand atomic capability review and materialization to `SidekickSkill` records so sidekick revive, healing, cleanse, and defensive support can participate in deterministic candidate coverage. This reopens the affected C1 record-type, stable-ID, evidence, diagnostics, graph-materialization, and drift contracts before C2 review resumes; the previously generated C2 batch 2 is superseded and must be regenerated after the vocabulary/tooling revision.
- Planning decision on 2026-07-08: C2 will also review and materialize `SidekickAura` capabilities. Sidekick evidence will record `main_only` availability for auto/charge-skill effects and `main_or_sub` availability for aura effects, together with captured activation conditions; Feature D must respect this placement availability when deriving coverage and scoring sidekick value.
- Planning decision on 2026-07-08: A single Skill, PassiveSkill, SidekickSkill, or SidekickAura may prove multiple distinct atomic facts when its source text independently supports each effect. Barrier and Shield are mutually distinct single capabilities rather than umbrella-plus-subtype duplicates: a Barrier proves `damage_reduction_barrier`, while a temporary HP pool proves `shield`; neither also emits generic `damage_reduction` merely because both reduce HP loss.
- Planning decision on 2026-07-08: Retire the ambiguous `cleanse_status` capability. Use `remove_status_ailment` for removing ailments such as sleep, stun, confusion, betrayal, Poison, or Pain, and `remove_debuff` for removing reductions such as PWR/INT/SPD, defense, or resistance down. A source that explicitly performs both may prove both atomic facts.
- Planning decision on 2026-07-08: Keep immediate HP restoration as `heal_hp` and add `regen_hp` for recurring end-of-turn HP restoration over a stated duration. Do not emit an umbrella `healing` fact. Timing, duration, activation, and other gating conditions remain evidence and dependency concerns rather than additional healing categories.
- Planning decision on 2026-07-08: Model lethal-damage prevention as `hold_ground` and restoration after death as `revive`. Use one direction-aware and target-aware `revive` capability for self, single-ally, and party revival rather than separate capability names; preserve target cardinality in evidence because single-target and team revival have different contextual value. A Guard source also proves `hold_ground` only when its text explicitly grants that mechanic.
- Planning decision on 2026-07-08: Keep `taunt`, `cover`, `guard`, `dodge`, `stalk`, and `knockback_immunity` as distinct C2 atomic capabilities. Taunt increases enemy targeting, Cover intercepts attacks for allies, Guard records the stronger named interception mechanic, dodge avoids incoming attacks, Stalk lowers user target priority, and knockback immunity prevents forced movement into reserve. Guard emits `hold_ground` as an additional fact only when the source explicitly proves it.
- Planning decision on 2026-07-08: Split mitigation into `damage_reduction` for non-Barrier direct reduction, `damage_reduction_barrier` for hit-limited Barrier reduction, and `shield` for temporary HP depleted before normal HP. Resistance-up capabilities remain separate because they modify specific damage categories rather than representing these direct mitigation mechanisms.
- Planning decision on 2026-07-08: Migrate C2 to a new taxonomy/review artifact version without discarding unaffected batch-1 decisions. Proposal identity must be stable across artifact-version changes and evidence must separately record the exact taxonomy version. Decisions whose semantics changed, including Barrier, cleanse, and healing splits, return through a targeted migration-review artifact outside the normal 45-new-proposal batch. The existing batch 2 is superseded and regenerated only after migration and regression gates pass.
- Planning decision on 2026-07-08: Reset C2's clean-batch streak after the vocabulary/tooling migration. Migrated batch-1 decisions remain accumulated evidence but do not count as a clean batch under the expanded contract. After targeted migration review and regressions pass, C2 still requires two fresh consecutive fully reviewed 45-row batches with no new critical false-positive pattern.
- Planning decision on 2026-07-08: Add optional structured evidence qualifiers `magnitude_value`, `magnitude_unit`, `activation_count`, `duration_turns`, and `trigger` for explicit source-backed parameters. Missing values remain unknown rather than zero or inferred. Capability presence determines atomic coverage; Feature D may use reviewed qualifiers for contextual RoleScores and provider ranking without claiming exact damage, healing, or survival simulation.
- Planning decision on 2026-07-08: Replacement C2 review rows will prefill deterministically parsed qualifier proposals and provide constrained correction fields for reviewers. Explicit source values must be approved or corrected rather than silently omitted; genuinely absent values remain blank/unknown. Qualifier validation follows the same immutable-evidence and constrained-import discipline as capability, direction, and target review.
- Planning decision on 2026-07-08: Replace vague ally target scopes with explicit reviewed values for `self`, `single_ally`, `frontline`, and `main_and_reserve`, while retaining applicable enemy, field, zone, and none targets. Whole-lineup effects that include reserve must not be conflated with frontline-only effects; target scope changes contextual coverage and ranking without requiring separate capability names.
- Planning decision on 2026-07-08: Add distinct `self_and_adjacent_allies` and `adjacent_allies` target scopes for left/right formation effects. Conditional recipient requirements such as weapon, element, personality, status, or stack should not create target enum variants; they require separate reviewed eligibility/dependency evidence.

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

- Planning decision on 2026-07-05: Reopen Feature C and block Feature D. Replace broad ETL role assignment with reviewed atomic capability and dependency extraction; contextual character roles are derived only at query time from proven capabilities and matchup/package context.
- Planning decision on 2026-07-05: Replace rather than retain the current Skill/PassiveSkill `role_tags` graph contract. Schema migration removes stale broad-role properties and materializes proven capabilities, dependencies, direction/target evidence, review provenance, and artifact versions.
- Planning decision on 2026-07-05: Use repository-native generated CSV review batches and canonical JSON decisions/gold fixtures. No local review webpage is required.
- Planning decision on 2026-07-05: Preserve approved, corrected, ambiguous, and rejected decisions. Rejected matches are permanent negative regressions; candidate, rejected, dependency-only, and untagged facts cannot satisfy mandatory Feature D coverage.
- Planning decision on 2026-07-05: Review in three phases: mandatory defensive/setup capabilities, offensive/support capabilities, then dependencies/conditions. Each phase passes after all accumulated fixtures pass plus two consecutive batches reveal no new critical false-positive pattern; the initially approximate 40-50-row size was later locked to exactly 45 new decisions per batch.
- Planning decision on 2026-07-05: Split the reopened Feature C into C1-C5 without renumbering downstream milestone features. C1 owns atomic contracts, constrained review tooling, and immediate removal of the old active `role_tags` schema; C2-C4 own the three human-review/correction loops; C5 owns full replay, drift verification, guide completion, and the Feature D handoff.
- Planning decision on 2026-07-05: Each human batch contains exactly 45 new deterministic stratified decisions. Every row requires `approve`, `reject`, `correct`, or `ambiguous`; blank or invalid decisions fail import. Prior decisions and targeted bug reproductions run separately as the complete accumulated regression set.
- Planning decision on 2026-07-05: Each C2-C4 batch pauses at `Awaiting human review`. Codex may propose and import decisions but cannot self-approve them. The human reviews atomic claims from captured source text and consults linked wiki pages only when evidence is unclear; contextual character roles are not assigned in these CSVs.
- Planning decision on 2026-07-05: A critical false-positive pattern is a repeatable error that can falsely satisfy mandatory coverage, reverse ally/enemy or grant/require meaning, omit a zone/SA/status/stack gate, or misclassify damage, defense, sustain, or setup across multiple facts. Discovery resets the phase's two-clean-batch streak.
- Planning decision on 2026-07-14: Feature C3 models `barrier_pierce`, `fixed_damage`, and `ignore_target_defense` as three independent atomic offensive capabilities. None implies either of the others, and C3 records evidence and explicit qualifiers without calculating resulting damage.
- Planning decision on 2026-07-14: Feature C3 reviews each offensive/support capability plus independently evidenced target scope, magnitude, duration, trigger, and stacking fields. Feature C4 separately reviews recipient eligibility and activation dependencies such as weapon/personality/status eligibility, zone, stack, Stellar Awakening, or party-composition requirements. A C3-approved capability with unresolved gating evidence cannot satisfy unconditional mandatory coverage before C4 validates those predicates.
- Planning decision on 2026-07-14: Feature C3 uses distinct capability identities for materially different offensive/support effects while keeping self/party/enemy scope in the orthogonal target field. Weapon, stat, element, and similar bounded variants use constrained qualifiers where the source identifies which weapon type, stat, or element is affected; those qualifiers do not become compound capability names.
- Planning decision on 2026-07-14: Feature C3 emits only the named transformation capabilities for Buff Reversal, Debuff Reversal, Expose, and weakness/resistance inversion. Buff Reversal is enemy-directed and Debuff Reversal is self/ally-directed; neither has a magnitude field unless a source independently provides one. Their possible converted buffs/debuffs or resulting affinity state are descriptive side effects, not synthesized capability facts.
- Planning decision on 2026-07-14: Replanned Feature C3 uses a breaking taxonomy/review-schema `3.0.0` boundary. Proposal IDs remain stable independently of version, unaffected C2 decisions and C2 completion remain preserved, and renamed, split, or semantically changed facts require targeted migration review. The generated unreviewed C3 batch 1 under the narrow draft vocabulary is a superseded non-importable audit artifact; C3 begins at a zero clean-batch streak and requires two fresh consecutive clean 45-row batches after migration review passes.
- Planning decision on 2026-07-14: Feature C3 separates `grant_link`, `grant_copy`, `attack_again`, `chain_attack`, and residual `follow_up_attack` capabilities. The residual follow-up capability applies only when source text explicitly proves a follow-up that is not one of the four named mechanics. Element, attack type, triggering action, activation limit, duration, and recipient are orthogonal evidence; no move-order, AF-gain, chain, or turn execution is simulated.
- Planning decision on 2026-07-14: Feature C3 separates physical and magical Overcritical capabilities because they depend on distinct critical-rate channels. Review captures the named effect, target, duration, trigger, and explicit threshold evidence but does not calculate proc probability or resulting critical damage.
- Planning decision on 2026-07-14: Feature C3 adds `activate_lunatic` with a constrained Lunatic-type qualifier for Charge, Copy, Static/Discharge, Mind's Eye, Risktaker, and Sacrifice. Separately proven outcomes may emit their own atomic capabilities, but Lunatic never becomes a permanent ETL role label. Feature C4 owns activation prerequisites, limited use, SA/source restrictions, and conditional timing; exact damage, AF, combo, stat conversion, self-damage, and turn execution are not simulated.
- Planning decision on 2026-07-14: Feature C3 emits `direct_damage` only when the reviewed source fact itself executes an attack or explicitly deals damage. Pure grants or enablers such as Link, Copy, Kaleido, or attack-again status do not imply direct damage. Compound facts may emit multiple capabilities only when separate source clauses independently prove each effect.
- Planning decision on 2026-07-14: Replace the narrow draft's `ally_damage_up` with `outgoing_damage_up`, emitted only for explicit channel-agnostic outgoing-damage amplification. Target scope represents self, one ally, or party. Power/Intelligence, critical, weapon/element, Focus, Eagle Eyes, Overthrow, weakness multiplier, Overcritical, and AF-specific effects do not imply this capability.
- Planning decision on 2026-07-14: Feature C3 adds `healing_effectiveness_up` for explicit amplification of healing output. A compound phrase such as "damage and healing +20%" may emit both `outgoing_damage_up` and `healing_effectiveness_up`, but neither implies `heal_hp` or `regen_hp`. Prayer/song activation and interruption conditions remain separate dependency evidence.
- Planning decision on 2026-07-14: Taxonomy/review schema 3.0 adds a minimal capture-only stacking contract: optional constrained `stacking_behavior` (`not_applicable`, `stackable`, `overwrites`, or `unknown`) and optional explicit `max_stacks`. Reviewers populate these only when source evidence proves them. Applied stack quantities may use the existing magnitude unit `stacks`; C3 does not calculate accumulated magnitude, schedule consumption, track turns, or simulate rotations.
- Planning decision on 2026-07-14: Feature C3 owns capture and validation of stacking evidence; Feature D owns any deterministic scoring use. Initial scoring must be explicit, conservative, and policy-versioned rather than assuming maximum stacks are reached. The analyzer may explain backend-supplied reviewed stacking facts but cannot invent stack totals, setup turns, or rotation outcomes.
- Planning decision on 2026-07-14: Replace generic `af_support` with four independent Feature C3 capabilities: `af_gauge_restore` for immediate gauge addition, `af_gauge_gain_up` for increased future gauge charging, `af_combo_gain_up` for increased AF combo growth, and `af_damage_up` for explicit damage amplification during AF. None implies another, and no AF duration, combo, or damage simulation is introduced.
- Planning decision on 2026-07-14: Feature C3 retains exactly two consecutive clean deterministic batches of 45 new proposals each. Rare/high-risk named mechanics and misleading negative cases receive explicit decisions in a separate targeted migration/seed-review artifact, then become permanent automatic regression fixtures. These targeted cases do not count toward either 45-row batch or the clean-batch streak, and every targeted fixture must pass before a batch can count as clean.
- Planning decision on 2026-07-14: Feature C3 updates `docs/guides/ETL_GUIDE.md` before generating replacement batch 1, documenting taxonomy 3.0 migration, superseded-batch rejection, targeted seed review, constrained qualifier review, import/correction, and clean-streak recovery. Feature C5 later verifies and finalizes that guide against full replay and materialization.
- Planning decision on 2026-07-14: Feature C3 completion is correctness-based rather than exhaustive-tagging-based. Every defined capability family needs reviewed positive and negative coverage; targeted migration/seed fixtures and all accumulated C2-C3 regressions must pass; and two consecutive clean 45-row batches must complete. Genuinely ambiguous, unsupported, and untagged facts remain reported and non-proven rather than blocking completion or receiving guessed capabilities.
- Planning decision on 2026-07-14: Feature C3 adds `element_damage_up` with a constrained element qualifier and a separate `non_type_damage_up`; neither is Kaleido, channel-agnostic outgoing damage, or equipped-weapon/attack-type amplification.
- Planning clarification on 2026-07-14: Equipment classes (Staff, Sword, Katana, Axe, Lance, Bow, Fists, Hammer), attack types (Slash, Pierce, Blunt, Magic), and elements (Fire, Water, Wind, Earth, Thunder, Shade, Crystal, plus explicit non-type where valid) are separate qualifier domains. Weakness, resistance, Expose, and matching Break semantics use attack type or element as proven by source text, not equipped weapon class. Wiki labels such as "Weapon Break" must not cause the qualifier to be stored as an equipment class.
- Planning decision on 2026-07-14: Feature C3 uses `equipped_weapon_damage_up` for Staff/Sword/Katana/Axe/Lance/Bow/Fists/Hammer eligibility, `attack_type_damage_up` for Slash/Pierce/Blunt/Magic amplification, and `element_damage_up` for elemental amplification. Resistance reduction separates broader physical and magic resistance from attack-type-specific and element-specific resistance. Expose and Break qualifiers use attack type or element, never equipped weapon class.


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

- Verify the dedicated Mental Focus, Singular Focus, Kaleido, Barrier Piercing, reversal skill, Link/Copy/Chain, Magic Overcritical, and Lunatic pages through normal cached ETL refresh or manual review where the planning browser returned 403, cache, safety, or timeout failures. The accessible Status Effects/Damage Formula pages and repository-cached facts support the locked capability identities, but unresolved coefficients, overwrite rules, exclusions, and interaction details remain non-authoritative.
- Resolve the accessible Status Effects snapshot's omission of Magic Overcritical against the user-provided wording and cached Abaddon's Call evidence. Until refreshed source material resolves the page discrepancy, physical and magical Overcritical remain separate reviewed capabilities and no proc probability is calculated.
- Identify at least one captured positive and one misleading negative example for residual `follow_up_attack` that is neither Link, Copy, attack again, nor Chain before that residual capability can become proven; otherwise leave residual follow-up facts candidate/ambiguous without blocking the named execution capabilities.
- Define Feature D's initial conservative, policy-versioned treatment of reviewed stacking evidence. C3 stores explicit stacking behavior and limits but does not assume maximum stacks or mandate a scoring bonus.
- Verify exact wording and edge cases from the user-provided Status Effects, Tank Role, Revival Role, Sacrificial Heart Stacking, Guiding Vow Rite, Lady Vesper, and Assemble pages through normal cached ETL artifacts or manual review because the live pages were not retrievable through the available planning browser. No acceptance criterion depends on unverified live-page wording.
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
