# Features Research

## Table Stakes (Must Have — Users Expect These)

### For Any Game Optimizer Tool

| Feature | Why Table Stakes | Complexity |
|---------|-----------------|------------|
| Roster filtering | Recommendations constrained to owned units | Low |
| Game rule accuracy | Zero hallucinated mechanics; wrong = useless | High |
| Response explainability | Users need to understand WHY, not just WHAT | Medium |
| Clear team layout | 4-frontline/2-reserve format players recognize | Low |
| Fast response | Timeouts kill trust; < 15s for full pipeline | Medium |

### For GraphRAG Specifically

| Feature | Why Table Stakes | Complexity |
|---------|-----------------|------------|
| Source attribution | "This synergy is valid because [Grasta name] + [personality]" | Medium |
| Error feedback | "Your roster has no Earth units — here's what's closest" | Medium |
| Retry transparency | User sees "Validating query... (attempt 2/3)" not a black box | Low |

---

## Differentiators (Competitive Advantage)

| Feature | Value | Complexity |
|---------|-------|------------|
| Natural language query | "Best blunt-zone synergy" vs dropdowns | Medium |
| Personality + Grasta graph traversal | Mathematically correct path-finding, not heuristics | High |
| Another Force (AF) synergy awareness | Accounts for AF zone mechanics in recommendations | High |
| Per-character role annotation | Explains "Aldo as AF anchor" vs "Tsukiha as off-element mule" | Medium |
| Graceful degradation | "No perfect match found — here's the closest 3 options" | Medium |

---

## Anti-Features (Deliberately NOT Building in v1)

| Feature | Why Excluded |
|---------|-------------|
| Account OCR / screen reading | Scope creep, fragile, legal grey area |
| Real-time game state sync | No game API, would require client modding |
| PvP meta analysis | Game is PvE-only |
| Exact stat optimization | Combinatorial explosion; save for v2 |
| Social features (sharing builds) | Distraction from core AI pipeline |
| Boss rotation generator | v3 feature; separate data requirements |
| Farming route optimizer | v2 feature; different data model |

---

## Feature Dependency Map

```
Roster Input
    └── Character lookup in Neo4j
            └── Personality retrieval
                    └── GENERATE_CYPHER (synergy query)
                            └── VALIDATE (game rule check)
                                    └── ANALYZE (team assembly)
                                            └── Output formatter
                                                    └── Explainability layer
```

The VALIDATE node is the hardest feature — it needs to catch:
1. Syntactically invalid Cypher queries
2. Queries that return no results (empty roster match)
3. Recommendations that violate game rules (e.g., duplicate Grasta slots)

---

## Analogues from Other Games

| Tool | What it does well | Apply here |
|------|------------------|------------|
| Genshin Impact team builders (e.g., Keqingmains) | Filters by owned characters, shows resonance bonuses | Roster filtering + synergy display |
| Arknights operator planner | Explains *why* a combination works | Explainability layer |
| Final Fantasy Record Keeper guides | Turn-by-turn with conditions | Future boss guide feature (v3) |

Key insight: Game optimizer tools live or die on **accuracy and trust**. A single wrong recommendation destroys credibility. The VALIDATE retry loop is not optional — it's the trust mechanism.

---
*Generated: 2026-03-14 (training knowledge, web search unavailable)*
