# AnotherEdenAI Future Ideas

This document captures promising ideas intentionally deferred from the active milestone. It is not an implementation contract. Promote items into `milestone.md` only after they are scoped and prioritized.

## Offensive Taxonomy Extension After MVP Evaluation

Deferred from Milestone 5 Feature C3 to keep the first recommender limited to source-backed, reviewable offensive/support facts.

Idea:

- Reintroduce `af_gauge_gain_up`, `invert_weakness_resistance`, `grant_copy`, and residual `follow_up_attack` as a dedicated taxonomy extension.
- Add the still-unimplemented MVP-deferred offensive/support families only after expert beta evidence identifies that they materially affect recommendation quality.
- Keep every deferred effect untagged and excluded from role scoring and mandatory coverage until it is explicitly reviewed.

Readiness signals:

- MVP golden and expert-beta evaluation identifies a recurring quality gap attributable to an untagged effect.
- Each proposed family has at least two parsed canonical character or sidekick facts, including a positive and a misleading/cross-family example.
- The source evidence settles its narrow atomic meaning, direction, target, qualifiers, and separation from existing capabilities.

## Battle Mechanics Knowledge Base

Deferred from Milestone 2 because boss and character ETL already expands the data surface significantly.

Idea:

- Ingest or curate reference knowledge from wiki pages such as Battle Mechanics, Status Effects, Buffs and Debuffs, Another Force, Zones, Damage Formula, and Healing Formula.
- Convert key mechanics into AI-friendly documentation or structured reference artifacts.
- Use this as grounding context so the LLM understands turn order, affinity precedence, status behavior, zones, AF, and mitigation rules more reliably.

Readiness signals:

- Milestone 2 boss and skill data are loaded and evals show recurring reasoning mistakes caused by missing general mechanics.
- The team knows whether reference docs should live in Neo4j, local JSON/Markdown, vector retrieval, or prompt-injected summaries.

## Normalized Combat Ontology

Deferred from Milestone 2 because Option A text-rich nodes are simpler and safer for first ingestion.

Idea:

- Promote repeated combat facts from text blobs into graph-native nodes or relationships.
- Candidate concepts include buffs, debuffs, statuses, zones, stacks, barriers, revive conditions, AF gauge effects, stopper mechanics, resource drains, and turn triggers.
- Move frequent freeform `mechanic_tags` into an approved controlled vocabulary.

Readiness signals:

- ETL inspection shows stable structures across many character and boss pages.
- Evaluations show that text-only boss/skill descriptions are not enough for accurate retrieval or constraint checking.

## Turn-Level Boss Mechanic Modeling

Deferred from Milestone 2 because only basic `turn_events` JSON is required for now.

Idea:

- Split boss turn scripts into normalized turn or phase entities.
- Model per-turn statuses, buffs, debuffs, zones, AF effects, resource effects, barriers, fixed damage, and cleanse/reset mechanics.
- Support queries such as "find bosses that drain AF on battle start" or "find bosses that apply Confusion before turn 3."

Readiness signals:

- Best-effort `turn_events` JSON is reliable across enough boss pages.
- Tactical evaluation failures require more precise turn timing than aggregate boss fields provide.

## Equipment And Damage Setup Optimizer

Deferred from Milestone 2 because exact damage calculation is complex and inventory-dependent.

Idea:

- Build a dedicated Grasta, Ore, Badge, weapon, armor, and Light/Shadow slot optimizer.
- Prioritize high-impact patterns such as Pain/Poison setups, personality-compatible Grasta, Falcon effects, and extra Grasta/Badge slots at 120/200 Light/Shadow.
- Decide whether ranking is deterministic, LLM-assisted, or hybrid.

Readiness signals:

- Roster, skill, passive, boss, badge, Grasta, and Ore data are stable.
- The project has enough eval coverage to catch hallucinated or illegal equipment recommendations.

## Sidekick Equipment

Deferred from Milestone 3 because sidekick identity, auto skills, charge skills, aura effects, and official character association matter more for the first RAG-ready sidekick model.

Idea:

- Ingest Sidekick Equipment as a dedicated equipment subtype with Might/EQP values, enhancement levels, Lv0/Lv5/Lv10 effects, obtain paths, and upgrade materials.
- Use sidekick equipment for later utility optimization such as status clearing, healing, barrier-piercing attacks, and specialized sidekick support.
- Keep it separate from the first sidekick ETL because its enhancement structure is different from sidekick identity and ability parsing.

Readiness signals:

- Sidekick nodes and ability/aura records are stable.
- AI recommendations are already using main/sub sidekick legality correctly.
- Evaluation shows sidekick equipment would materially change recommendation quality.

## AI-Derived Sidekick Strategic Synergy

Deferred from Milestone 3 because the graph should first capture hard official facts before adding inferred strategic judgments.

Idea:

- Add soft synergy scoring between sidekicks, characters, bosses, zones, statuses, and team archetypes.
- Use sidekick aura, auto skill, charge skill, and boss mechanics to infer "best with" recommendations.
- Keep inferred synergy separate from official `UNLOCKS_SIDEKICK` or association facts, with confidence and evidence fields.

Readiness signals:

- Official sidekick-character association data is loaded and verified.
- Curated boss data and recommendation evaluation exist.
- The AI lineup milestone exposes repeated decisions where sidekick choice changes team quality.

## Structured Recommendation Output Contract

Deferred from Milestone 2 until real ETL data reveals the most stable output shape.

Idea:

- Replace or supplement natural-language output with strict structured fields such as `team`, `role_assignments`, `turn_1_2_skill_plan`, `boss_counterplay`, `backup_lineup`, `upgrade_path`, `confidence`, and `disclaimers`.
- Use Pydantic models to validate recommendation shape before rendering or evaluation.

Readiness signals:

- Milestone 2 recommendations reveal repeated formatting or evaluation ambiguity.
- The project needs stronger CI gates around lineup legality and skill-slot legality.

## Full Reference-Backed Evaluation

Deferred from Milestone 2 because the current eval plan starts with unsupervised LLM-as-a-judge.

Idea:

- Add richer adversarial tests grounded in battle mechanics reference docs.
- Evaluate whether answers correctly apply affinity precedence, zone rules, AF timing, status immunity, boss stoppers, and passive triggers.
- Consider human-reviewed seed cases only for the hardest scenarios if expert knowledge becomes available.

Readiness signals:

- The two-tier eval framework is running and generating useful reports.
- Failures cluster around specific battle-mechanics misunderstandings.

## Alternative Character And Pull-Planning Suggestions

Deferred from Milestone 4 because the active recommendation milestone should first prove legal owned-roster lineup navigation for selected bosses.

Idea:

- Recommend useful not-owned or not-yet-built characters as upgrade inspiration after producing owned-roster lineups.
- Clearly label whether each suggested character is owned, not owned, Stellar Awakening-gated, or dependent on specific skills/equipment.
- Include recommended 3/4 skill selections and the lineup slot or role the character would replace.
- Keep suggestions framed as upgrade targets or role inspiration, not spending advice or banner recommendations.

Readiness signals:

- Milestone 4 owned-roster recommendations are stable and pass legality/factuality gates.
- The recommendation contract can distinguish usable-now picks from upgrade assumptions.
- The UI has room to present upgrade suggestions without confusing them with legal current-lineup recommendations.

## Intermediate And Strong Superboss Evaluation Tiers

Deferred from Milestone 4 because the first navigator should prove legality, mechanics grounding, and useful top-3 recommendations on weak superbosses before expanding difficulty coverage.

Idea:

- Add intermediate and strong superboss eval groups after the weak-boss golden set is reliable.
- Use tier labels such as `weak`, `intermediate`, and `strong` in eval metadata.
- Increase expectations around boss-specific mechanics, stoppers, status handling, turn order, sustain, and execution caveats as tiers get harder.

Readiness signals:

- The 5 weak-boss eval set passes deterministic legality and factuality gates.
- Recommendation quality judge feedback is stable enough to compare improvements across releases.
- Additional boss data has enough mechanics text and affinity coverage to support trustworthy recommendations.

## Deterministic Battle Simulation And Win-Probability Estimation

Deferred from Milestone 4 because the active system is a navigation tool, not a prediction tool.

Idea:

- Build a deterministic or semi-deterministic simulator for damage, healing, buffs/debuffs, speed, AF windows, boss turns, stoppers, MP use, and survival checks.
- Estimate lineup success under explicit assumptions about stats, equipment, Grasta/Ore inventory, skill rotation, boss behavior, and player execution.
- Present probabilities only when backed by validated simulation data and clearly stated assumptions.

Readiness signals:

- Mechanics RAG, lineup legality, and recommendation quality are stable.
- Character stats, enemy stats, equipment, Grasta/Ore, boss turn scripts, and skill effects are sufficiently structured.
- Human-reviewed battle cases or strong replay fixtures exist to validate simulation outputs.
