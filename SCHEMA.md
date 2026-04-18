# Graph Schema Contract
**SCHEMA_VERSION: 1.0.0**
**Status:** Stable — do not modify without incrementing SCHEMA_VERSION and running ETL

## Node Labels and Properties

### Character
- `name` (STRING, unique) — canonical wiki name
- `element` (STRING) — Fire, Water, Wind, Earth, Thunder, Light, Dark, Null
- `weapon` (STRING) — Sword, Blade, Bow, Spear, Hammer, Staff, Mace, Tome, Fist, Katana
- `light_shadow` (STRING) — "Light" or "Shadow"

### Trait
- `name` (STRING, unique) — personality trait name shared by Characters and Grastas

### Grasta
- `name` (STRING, unique) — display name from wiki col[1]; VC grastas: col[1] only (NOT data-name which includes character)
- `category` (STRING) — Attack | Life | Support | Special | VC
- `tier` (INTEGER) — grasta tier level (always read from data-tier; do NOT hard-code VC=4, wiki shows tier=3)
- `stats` (STRING) — stat bonuses from col[3] (e.g., "INT +10 SPD +10")
- `is_shareable` (BOOLEAN) — true if data-share="1"
- `personality_req` (STRING, nullable) — trait name from data-personality; null for VC and weapon-based grastas

### Ore
- `name` (STRING, unique) — ore display name from col[1]
- `stats` (STRING) — stats/effect from col[2]
- `source` (STRING) — drop location from col[3]

NOTE: Ore nodes are standalone entities. There is no ENHANCES relationship in the graph.
The decision of which Ore to apply to which Grasta is a dynamic player/AI decision handled
by the PLAN and ANALYZE agents at query time (Phase 2/3). Do not add ENHANCES edges.

## Relationship Types

### (:Character)-[:HAS_TRAIT]->(:Trait)
Character equipped with a personality trait. No relationship properties.

### (:Grasta)-[:REQUIRES_TRAIT]->(:Trait)
Grasta requires a personality trait to equip. No relationship properties.
Gate: only created when category != "VC" AND personality_req is not None/empty.

## Known Counts (from wiki audit 2026-03-14)
- Character nodes: 393
- Grasta nodes: 647 (Attack=231, Life=46, Support=56, Special=4, VC=310)
- Ore nodes: 61
- Trait nodes: varies (union of all character personalities + grasta personality_req values)

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
