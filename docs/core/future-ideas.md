# AnotherEdenAI Future Ideas

This document captures promising ideas intentionally deferred from the active milestone. It is not an implementation contract. Promote items into `milestone.md` only after they are scoped and prioritized.

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
