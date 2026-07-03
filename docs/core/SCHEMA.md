# Graph Schema Contract
**SCHEMA_VERSION: 1.2.0**
**Status:** Stable — do not modify without incrementing SCHEMA_VERSION and running ETL

## Node Labels and Properties

### Character
- `name` (STRING, unique) — canonical wiki name
- `character_id` (STRING, unique candidate identity) — stable identity derived from name and detail URL
- `display_name` (STRING) — full canonical roster/display name
- `aliases` (LIST<STRING>) — accepted inputs that resolve back to the canonical name
- `element` (STRING) — Fire, Water, Wind, Earth, Thunder, Light, Dark, Null
- `weapon` (STRING) — Sword, Blade, Bow, Spear, Hammer, Staff, Mace, Tome, Fist, Katana
- `light_shadow` (STRING) — "Light" or "Shadow"
- `is_SA` (BOOLEAN) — true when Stellar Awakening exists for the game character
- `detail_url` (STRING, nullable) — canonical wiki detail page URL discovered from the Characters index
- `schema_version` (STRING) — ETL schema version used for this row

### Trait
- `name` (STRING, unique) — personality trait name shared by Characters and Grastas

### Grasta
- `grasta_id` (STRING, unique) — stable exact-variant identity
- `name` (STRING) — shared base name from the wiki
- `display_name` (STRING) — compatibility-disambiguated recommendation label
- `category` (STRING) — Attack | Life | Support | Special | VC
- `tier` (INTEGER) — grasta tier level from data-tier
- `stats` (STRING) — stat bonuses from the source row
- `is_shareable` (BOOLEAN) — true if data-share="1"
- `personality_req` (STRING, nullable) — exact personality compatibility discriminator
- `weapon_req` (STRING, nullable) — exact required weapon when one weapon flag is set
- `weapon_group` (LIST<STRING>) — all compatible weapon flags from the source row
- `source_url`, `obtain_text`, `effect_text` (STRING) — source-grounded context
- `source_variant` (STRING) — optional discriminator when other identity fields collide
- `acquisition_class` (STRING) — unique | finite | repeatable | unknown
- `max_theoretical_copies` (INTEGER, nullable) — exact-variant account ceiling when known
- `schema_version` (STRING) — ETL schema version used for this row
- `effect_tags` (LIST<STRING>) — deterministic retrieval tags
- `effect_tag_derivation` (STRING) — derivation note; tags are not exact damage math

### Ore
- `name` (STRING, unique) — ore display name from col[1]
- `stats` (STRING) — stats/effect from col[2]
- `source` (STRING) — drop location from col[3]
- `effect_tags` (LIST<STRING>) — deterministic keyword tags derived from existing Ore name/stats text for retrieval
- `effect_tag_derivation` (STRING) — derivation note for `effect_tags`; tags are not exact damage math

### Equipment
- `name` (STRING) — equipment display name from the weapon or armor index
- `equipment_slot` (STRING) — `weapon` or `armor`
- `category` (STRING, nullable) — weapon or armor type/category when available
- `level` (INTEGER, nullable) — level or tier value when available
- `attack` (INTEGER, nullable) — weapon attack baseline when available
- `magic_attack` (INTEGER, nullable) — weapon magic attack baseline when available
- `defense` (INTEGER, nullable) — armor defense baseline when available
- `magic_defense` (INTEGER, nullable) — armor magic defense baseline when available
- `effect_text` (STRING) — source-grounded equipment effect text for RAG retrieval
- `obtain_text` (STRING) — source-grounded obtain/source text
- `source_url` (STRING) — wiki index URL used for the row
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `(equipment_slot, name)`.

Equipment nodes provide baseline context only. They do not encode best-in-slot ranking, optimizer scores, exact damage math, or survivability calculations.

### Skill
- `skill_id` (STRING, unique) — stable backend candidate identity derived from canonical owner and skill name
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

Uniqueness: `skill_id` and `(character_name, name)`.

### PassiveSkill
- `passive_skill_id` (STRING, unique) — stable backend candidate identity derived from canonical owner and passive name
- `character_name` (STRING) — owning Character name from the parsed character row
- `name` (STRING) — passive or mechanic display name
- `description` (STRING) — rich Option A text description
- `source_url` (STRING, nullable) — source character detail page
- `section` (STRING, nullable) — source page section, e.g. Stances/Zones
- `passive_type` (STRING, nullable) — best-effort category such as zone, stance, stack, battle-start, stellar awakening, valor chant, or passive
- `requires_stellar_awakened` (BOOLEAN) — true when the passive is gated behind Stellar Awakening
- `schema_version` (STRING) — ETL schema version used for this row

Uniqueness: `passive_skill_id` and `(character_name, name)`.

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

Query-time ownership contract:

- `GET /api/entities` returns separate `characters`, `sidekicks`, and `grastas` name lists.
- `POST /api/query` accepts `query`, `roster`, and optional `owned_sidekicks`.
- Selected sidekick names are normalized against `Sidekick` nodes before retrieval.
- Recommendation retrieval and output may use only selected owned sidekicks. An empty selection keeps main/sub sidekick slots empty and must be represented as a risk or assumption rather than inferred ownership.

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

### MechanicReference
- `id` (STRING, unique) — stable curated mechanics reference identifier
- `title` (STRING) — display title for the reference
- `source_url` (STRING) — wiki mechanics source URL used for citation
- `source_page` (STRING) — source page name
- `section_path` (LIST<STRING>) — curated section path within the source page
- `mechanic_type` (STRING) — broad category such as party, sidekick, affinity, damage, sustain, support, status, zone, burst, turn_order, progression_gate, or build_context
- `topic_tags` (LIST<STRING>) — retrieval tags for recommendation grounding
- `applies_to` (LIST<STRING>) — recommendation concerns this reference supports
- `rules_text` (STRING) — curated rules or recommendation-grounding text
- `summary` (STRING) — compact retrieval summary
- `caveats` (STRING) — scope limits or uncertainty notes
- `schema_version` (STRING) — ETL schema version used for this row

MechanicReference nodes are manually curated from cached mechanics source pages and loaded as standalone RAG references. They ground recommendation reasoning but do not implement deterministic damage, healing, speed, or turn-by-turn simulation.

NOTE: Ore nodes are standalone entities. There is no ENHANCES relationship in the graph.
The decision of which Ore to apply to which Grasta is a dynamic player/AI decision handled
by the PLAN and ANALYZE agents at query time (Phase 2/3). Do not add ENHANCES edges.

NOTE: Equipment nodes are standalone baseline context records. There are no Equipment recommendation, ranking, build, or equip relationships in the graph for Milestone 3.

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
- Equipment nodes: 888 (weapon=664, armor=224 from verified ETL run 2026-06-09)
- MechanicReference nodes: 12 golden Milestone 4 references in the first curated corpus
- Trait nodes: varies (union of all character personalities + grasta personality_req values)
- Skill and PassiveSkill counts vary by selected character-detail crawl scope.
- Sidekick, SidekickSkill, and SidekickAura counts vary by selected sidekick crawl scope.
- Superboss counts vary by curated weak-superboss crawl scope.

## Schema Validation
After ETL, `python assert_schema.py` must exit 0.
`get_schema()` from langchain_neo4j.Neo4jGraph must match this document.

The post-load assertion gate also verifies Milestone 3 RAG-readiness coverage:
- stable, unique `character_id`, `skill_id`, `passive_skill_id`, and `grasta_id` values
- schema 1.2 identity freshness and visible missing character, skill, passive, boss, mechanics, and item coverage
- minimum loaded counts for `Skill`, `PassiveSkill`, `Sidekick`, `SidekickSkill`, `SidekickAura`, `Superboss`, and `Equipment`
- minimum loaded count for `MechanicReference`
- `schema_version` presence on milestone-added structured labels
- wiki `source_url` attribution where the source exists
- golden retrieval paths for sidekick associations, sidekick auto/charge skills, sidekick auras, boss affinities and mechanics text, and baseline equipment context
- no exact `Character.name`/`Sidekick.name` overlap remains after the Milestone 5 sidekick cleanup gate
- golden retrieval paths for weakness handling, main/sub sidekick behavior, Stellar Awakening gating, speed/turn order, sustain, and Grasta/Ore setup

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
