# Graph Schema Contract
**SCHEMA_VERSION: 1.0.0**
**Status:** Stable — do not modify without incrementing SCHEMA_VERSION and running ETL

## Node Labels and Properties

### Character
- `name` (STRING, unique) — canonical wiki name
- `element` (STRING) — Fire, Water, Wind, Earth, Thunder, Light, Dark, Null
- `weapon` (STRING) — Sword, Blade, Bow, Spear, Hammer, Staff, Mace, Tome, Fist, Katana
- `light_shadow` (STRING) — "Light" or "Shadow"
- `is_SA` (BOOLEAN) — true when Stellar Awakening exists for the game character
- `detail_url` (STRING, nullable) — canonical wiki detail page URL discovered from the Characters index

### Trait
- `name` (STRING, unique) — personality trait name shared by Characters and Grastas

### Grasta
- `name` (STRING, unique) — display name from wiki col[1]; VC grastas: col[1] only (NOT data-name which includes character)
- `category` (STRING) — Attack | Life | Support | Special | VC
- `tier` (INTEGER) — grasta tier level (always read from data-tier; do NOT hard-code VC=4, wiki shows tier=3)
- `stats` (STRING) — stat bonuses from col[3] (e.g., "INT +10 SPD +10")
- `is_shareable` (BOOLEAN) — true if data-share="1"
- `personality_req` (STRING, nullable) — trait name from data-personality; null for VC and weapon-based grastas
- `effect_tags` (LIST<STRING>) — deterministic keyword tags derived from existing Grasta name/category/stats/personality text for retrieval
- `effect_tag_derivation` (STRING) — derivation note for `effect_tags`; tags are not exact damage math

### Ore
- `name` (STRING, unique) — ore display name from col[1]
- `stats` (STRING) — stats/effect from col[2]
- `source` (STRING) — drop location from col[3]
- `effect_tags` (LIST<STRING>) — deterministic keyword tags derived from existing Ore name/stats text for retrieval
- `effect_tag_derivation` (STRING) — derivation note for `effect_tags`; tags are not exact damage math

### Skill
- `character_name` (STRING) — owning Character name from the parsed character row
- `name` (STRING) — skill display name
- `element` (STRING, nullable) — parsed skill element when available
- `skill_type` (STRING, nullable) — parsed active skill type such as Slash, Magic, Buff, Healing, Status, or Zone Buff
- `mp` (INTEGER, nullable) — MP cost when available
- `description` (STRING) — rich Option A text description
- `multiplier` (FLOAT, nullable) — parsed multiplier when available
- `source_url` (STRING, nullable) — source character detail page
- `section` (STRING, nullable) — source page section, e.g. Active Skills or Stellar Awakened Skills
- `requires_stellar_awakened` (BOOLEAN) — true when the skill is gated behind Stellar Awakening
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `(character_name, name)`.

### PassiveSkill
- `character_name` (STRING) — owning Character name from the parsed character row
- `name` (STRING) — passive or mechanic display name
- `description` (STRING) — rich Option A text description
- `source_url` (STRING, nullable) — source character detail page
- `section` (STRING, nullable) — source page section, e.g. Stances/Zones
- `passive_type` (STRING, nullable) — best-effort category such as zone, stance, stack, battle-start, stellar awakening, valor chant, or passive
- `requires_stellar_awakened` (BOOLEAN) — true when the passive is gated behind Stellar Awakening
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `(character_name, name)`.

### Sidekick
- `name` (STRING, unique) — canonical wiki sidekick name
- `source_url` (STRING) — canonical wiki detail page URL
- `acquisition_text` (STRING, nullable) — wiki encounter/acquisition text when available
- `rarity` (STRING, nullable) — sidekick rank such as `3★`, `4★`, `5★`, or style marker when available
- `role_tags` (LIST<STRING>) — raw index role tags when available
- `main_slot_behavior` (STRING) — main sidekick can use auto skills, charge skills, and aura effects
- `sub_slot_behavior` (STRING) — sub sidekick contributes aura-only effects
- `diagnostics_text` (STRING, nullable) — irregular parsed sidekick sections preserved for review
- `schema_version` (STRING) — ETL schema version used for this row

Sidekicks are separate from `Character` nodes. They do not count as frontline or backline heroes.

### SidekickSkill
- `sidekick_name` (STRING) — owning Sidekick name
- `name` (STRING) — skill display name
- `skill_kind` (STRING) — `auto` or `charge`
- `element` (STRING, nullable) — parsed skill element when available
- `skill_type` (STRING, nullable) — parsed sidekick skill type when available
- `charge_cost` (INTEGER, nullable) — charge consumed or generated when available
- `description` (STRING) — source-grounded skill text
- `source_url` (STRING, nullable) — source sidekick detail page
- `section` (STRING, nullable) — source page section
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `(sidekick_name, name, skill_kind)`.

### SidekickAura
- `sidekick_name` (STRING) — owning Sidekick name
- `name` (STRING) — aura display name
- `activation_condition` (STRING, nullable) — best-effort parsed activation condition
- `effect_text` (STRING) — source-grounded aura effect text
- `source_url` (STRING, nullable) — source sidekick detail page
- `section` (STRING, nullable) — source page section
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `(sidekick_name, name)`.

### Superboss
- `name` (STRING, unique) — canonical curated superboss name
- `source_url` (STRING) — wiki detail page URL, including a section anchor when the boss lives on a larger encounter page
- `difficulty_tier` (STRING, nullable) — tier value discovered from the Superbosses index
- `level` (INTEGER, nullable) — numeric level derived from the difficulty tier where available
- `hp` (INTEGER, nullable) — parsed HP value when a clean detail-page field is available
- `weak` (LIST<STRING>) — parsed weakness values, or `["unknown"]` when unavailable
- `resist` (LIST<STRING>) — parsed resistance values, or `["unknown"]` when unavailable
- `null` (LIST<STRING>) — parsed null/immune values, or `["unknown"]` when unavailable
- `absorb` (LIST<STRING>) — parsed absorb values, or `["unknown"]` when unavailable
- `characteristics` (STRING) — source-grounded index characteristic text
- `mechanic_tags` (LIST<STRING>) — lightweight deterministic tags derived from source text for retrieval
- `mechanics_text` (STRING) — source-grounded mechanics text retained for RAG context
- `schema_version` (STRING) — ETL schema version used for this row

Superboss rows are loaded only from curated detail pages that pass quality gates. Index-only candidate facts are discovery metadata, not final graph nodes.

NOTE: Ore nodes are standalone entities. There is no ENHANCES relationship in the graph.
The decision of which Ore to apply to which Grasta is a dynamic player/AI decision handled
by the PLAN and ANALYZE agents at query time (Phase 2/3). Do not add ENHANCES edges.

## Relationship Types

### (:Character)-[:HAS_TRAIT]->(:Trait)
Character equipped with a personality trait. No relationship properties.

### (:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
Grasta requires a personality trait to equip. No relationship properties.
Gate: only created when category != "VC" AND personality_req is not None/empty.

### (:Character)-[:HAS_SKILL]->(:Skill)
Character has an executable active skill or basic attack replacement. No relationship properties.

### (:Character)-[:HAS_PASSIVE_SKILL]->(:PassiveSkill)
Character has a passive skill, stance, zone, battle-start effect, Stellar Awakening passive, or other non-executable mechanic. No relationship properties.

### (:Sidekick)-[:HAS_AUTO_SKILL]->(:SidekickSkill)
Sidekick has an auto skill. Target `SidekickSkill.skill_kind` is `auto`.

### (:Sidekick)-[:HAS_CHARGE_SKILL]->(:SidekickSkill)
Sidekick has a charge skill. Target `SidekickSkill.skill_kind` is `charge`.

### (:Sidekick)-[:HAS_AURA]->(:SidekickAura)
Sidekick has an aura effect. Auras can be contributed by sub sidekicks.

### (:Character)-[:UNLOCKS_SIDEKICK]->(:Sidekick)
Official wiki association or unlock fact between a Character and Sidekick when discoverable from the Sidekick index or detail page.

## Known Counts (from wiki audit 2026-03-14)
- Character nodes: 393
- Grasta nodes: 647 (Attack=231, Life=46, Support=56, Special=4, VC=310)
- Ore nodes: 61
- Trait nodes: varies (union of all character personalities + grasta personality_req values)
- Skill and PassiveSkill counts vary by selected character-detail crawl scope.
- Sidekick, SidekickSkill, and SidekickAura counts vary by selected sidekick crawl scope.
- Superboss counts vary by curated weak-superboss crawl scope.

## Schema Validation
After ETL, `python assert_schema.py` must exit 0.
`get_schema()` from langchain_neo4j.Neo4jGraph must match this document.

## Future Extensions

### OPT-03: AF Zone Mechanics (v2)
<!-- TODO OPT-03 -->
AF synergy in Phase 3 operates through existing HAS_TRAIT and REQUIRES_TRAIT paths.
Zone types are not modeled as nodes. A v2 schema extension would add:
- `(:Zone {type: "Fire"|"Wind"|"Water"|...})` node label
- `(Character|Grasta)-[:SETS_ZONE]->(Zone)` relationship
- `(Character)-[:BENEFITS_FROM_ZONE]->(Zone)` relationship
This extension is deferred to OPT-03. Phase 3 recommendations use trait matching
to infer AF zone synergies without explicit zone nodes.
