# Feature H2 — Human-Readable Recommendation Validation

Source evaluation: `feature-h1-evaluation-v1`  
Reviewed variant: `baseline_a`

> **Bounded claim:** A lineup may be modeled as viable or well-matched according to supplied evidence; this report does not prove a gameplay clear.

**H1 operational finding:** DeepSeek reasoning=none/4k is the provisional operational winner from H1; this does not establish strategic quality or a production setting change.

This is an offline review artifact. It does not make paid calls, change production settings, or guarantee a boss clear.

# H-F01 — Zennon Ogre's Shadow

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10288.0`; boss matchup component: `10.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — hybrid

Score: `10288.0`; boss matchup component: `10.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10288.0`; boss matchup component: `10.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 2 (hybrid)**
Ranking: Candidate 2 (hybrid), Candidate 1 (burst), Candidate 3 (sustain)
Strategy summary: Use the deterministic hybrid backend candidate.
Validation: `FAIL`
**Analyzer recommendation rejected by deterministic validator.**
- The analyzer proposed a swap that is not in the backend-authorized swap list.
Selected skills: Deliverance Sword, Knight's Pride, Deliverance Sword - Counter, Heavenly Dance, Fastening Edge, Culmination Winds, Flame's Serenade, Jewel Concerto
Proposed swaps: frontline.1: unknown character → Unknown character; frontline.3: unknown character → Unknown character; frontline.2: unknown character → Unknown character
Advisories: unknown / not supplied
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `False`
- **same_top_candidate:** `True`
- **same_ranking:** `True`
- **same_swap:** `False`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `False`
- **token_delta:** `2063`
- **cost_delta:** `0.00033008`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 20464; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 20464; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic hybrid backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `1`
- Unique frontline sets: `None`
- Unique archetypes: `3`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[1.0, 1.0, 1.0]`

- CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.
- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.
- ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.
- ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F03 — Cradle System

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — hybrid

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (burst)**
Ranking: Candidate 1 (burst), Candidate 2 (hybrid), Candidate 3 (sustain)
Strategy summary: Use the deterministic burst backend candidate.
Validation: `PASS`
Selected skills: Lunar Caustic, Aether Alchemia, Aether Magia, Flame's Serenade, Jewel Concerto, Creation's Prelude, Deliverance Sword, Knight's Pride
Proposed swaps: reserve.0: unknown character → Unknown character
Advisories: The candidate set is closed-world; no new candidates may be introduced., Backend role assignments and coverage are authoritative and read-only; the analyzer must not alter or reinterpret them., The analyzer must not emit or rely on forbidden fields: coverage_claims, mandatory_coverage, proven_coverage, role_ids, role_scores., All candidate IDs must be referenced exactly as supplied; no substitutions or aliases are permitted., The analyzer may only rank or refine the supplied candidates; it must not generate new lineups or modify character compositions., Refinements are limited to the allowed swap operations defined in the constraints; no other structural changes are permitted.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `True`
- **same_top_candidate:** `True`
- **same_ranking:** `True`
- **same_swap:** `False`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `True`
- **token_delta:** `996`
- **cost_delta:** `0.0011561000000000002`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 20447; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 20019; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic burst backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `1`
- Unique frontline sets: `None`
- Unique archetypes: `3`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[1.0, 1.0, 1.0]`

- CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.
- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.
- ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.
- ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F05 — Nameless Girl

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10432.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — hybrid

Score: `10432.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10432.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (burst)**
Ranking: Candidate 1 (burst), Candidate 2 (hybrid), Candidate 3 (sustain)
Strategy summary: Use the deterministic burst backend candidate.
Validation: `PASS`
Selected skills: Lunar Caustic, Aether Alchemia, Aether Magia, Jewel Concerto, Flame's Serenade, Creation's Prelude, Deliverance Sword, Knight's Pride
Proposed swaps: none reported
Advisories: The candidate data contains malformed JSON structures in several places, including truncated objects, invalid field types, and inconsistent nesting. The analyzer will attempt to parse the data leniently, but any malformed sections will be treated as missing or default values., The candidate IDs are treated as a closed world; no additional candidates will be considered beyond those provided., Backend role assignments and coverage are read-only and will not be modified by the analyzer., The analyzer will not output any fields listed in the forbidden_analyzer_fields set.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `False`
- **same_top_candidate:** `True`
- **same_ranking:** `True`
- **same_swap:** `True`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `False`
- **swap_authorized:** `True`
- **token_delta:** `2423`
- **cost_delta:** `0.00038767999999999995`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 20446; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 20446; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic burst backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `1`
- Unique frontline sets: `None`
- Unique archetypes: `3`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[1.0, 1.0, 1.0]`

- CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.
- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.
- ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.
- ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F08 — Rotte Rivel

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10684.0`; boss matchup component: `32.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — hybrid

Score: `10684.0`; boss matchup component: `32.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10684.0`; boss matchup component: `32.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 2 (hybrid)**
Ranking: Candidate 2 (hybrid), Candidate 1 (burst), Candidate 3 (sustain)
Strategy summary: Use the deterministic hybrid backend candidate.
Validation: `PASS`
Selected skills: Deliverance Sword, Knight's Pride, Deliverance Sword - Counter, Heavenly Dance, Fastening Edge, Culmination Winds, Jewel Concerto, Flame's Serenade
Proposed swaps: frontline.0: unknown character → Unknown character
Advisories: All three lineups share the same core characters and have identical component scores, so the ranking is based on strategic fit against Rotte Rivel., The boss is weak to Fire, so prioritizing Aisha's Fire zone and Fire-based damage dealers is crucial., The boss has strong Wind and Slash attacks, so defensive mitigation from Anabel and Ashtear is important for survival., The boss can inflict confuse and bind on marked slots, so having status cleanse or resistance is beneficial., Item ownership is unverified; the build packages are targets, not guaranteed inventory., The boss has high HP and can heal, so a sustained damage strategy may be necessary.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `True`
- **same_top_candidate:** `False`
- **same_ranking:** `False`
- **same_swap:** `False`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `True`
- **token_delta:** `2271`
- **cost_delta:** `-0.00241957`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 21106; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 21104; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic hybrid backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `1`
- Unique frontline sets: `None`
- Unique archetypes: `3`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[1.0, 1.0, 1.0]`

- CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.
- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.
- ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.
- ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F12 — Berserk Tempered Hound

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10378.0`; boss matchup component: `15.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — burst

Score: `10378.0`; boss matchup component: `15.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — burst

Score: `10378.0`; boss matchup component: `15.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (burst)**
Ranking: Candidate 1 (burst), Candidate 2 (burst), Candidate 3 (burst)
Strategy summary: Use the deterministic burst backend candidate.
Validation: `FAIL`
**Analyzer recommendation rejected by deterministic validator.**
- The analyzer proposed a character ID that is not in the supplied character set.
- An advisory used a role value that is not supported by the backend evidence.
- The analyzer proposed a swap that is not in the backend-authorized swap list.
Selected skills: Lunar Caustic, Aether Alchemia, Aether Magia, Jewel Concerto, Flame's Serenade, Creation's Prelude, Deliverance Sword, Knight's Pride
Proposed swaps: reserve.1: unknown character → Unknown character; reserve.1: unknown character → Unknown character; reserve.1: unknown character → Unknown character
Advisories: All candidates share identical component scores and coverage; ranking is based on strategic fit against the boss's mechanics., The boss nullifies Wind and Earth, resists Water, and has no weaknesses. All candidates rely on Fire/Crystal/None damage, which is not resisted., The boss's 'Knockback Strike' forces a frontline character to reserve, making a strong reserve unit critical for maintaining damage output., The boss's 'Energy Inhibition' drains 50% max MP, so MP management is a concern for all candidates., The boss's 'Systems Restore' removes buffs/debuffs and heals 50% HP, requiring a sustained damage approach or a powerful burst window., The boss overheats after 6 fire hits, becoming weak to physical and neutral to elements; capitalizing on this window is key.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `False`
- **same_top_candidate:** `True`
- **same_ranking:** `True`
- **same_swap:** `False`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `False`
- **swap_authorized:** `False`
- **token_delta:** `-1197`
- **cost_delta:** `0.00636062`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 56424; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 56009; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic burst backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `3`
- Unique frontline sets: `None`
- Unique archetypes: `1`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[0.714, 0.714, 0.714]`

- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F13 — Menreiki

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — sustain

Score: `10434.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — sustain

Score: `10434.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10434.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (sustain)**
Ranking: Candidate 1 (sustain), Candidate 2 (sustain), Candidate 3 (sustain)
Strategy summary: Use the deterministic sustain backend candidate.
Validation: `PASS`
Selected skills: Lunar Caustic, Aether Alchemia, Aether Magia, Deliverance Sword, Knight's Pride, Deliverance Sword - Counter, Flame's Serenade, Jewel Concerto
Proposed swaps: none reported
Advisories: The candidate list contains malformed entries that must be ignored during ranking., The candidate list contains duplicate entries that must be deduplicated before ranking., The candidate list contains entries with missing required fields; these are invalid and must be excluded., The candidate list contains entries with inconsistent role assignments; these are invalid and must be excluded., The candidate list contains entries with inconsistent coverage claims; these are invalid and must be excluded., The candidate list contains entries with inconsistent uncertainty data; these are invalid and must be excluded.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `False`
- **same_top_candidate:** `False`
- **same_ranking:** `False`
- **same_swap:** `True`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `True`
- **token_delta:** `7764`
- **cost_delta:** `0.00124224`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 49780; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 49780; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic sustain backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `3`
- Unique frontline sets: `None`
- Unique archetypes: `1`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[0.714, 0.714, 0.714]`

- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F18 — True Fornjot

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10418.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — burst

Score: `10418.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — hybrid

Score: `10418.0`; boss matchup component: `18.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (burst)**
Ranking: Candidate 1 (burst), Candidate 2 (burst), Candidate 3 (hybrid)
Strategy summary: Use the deterministic burst backend candidate.
Validation: `PASS`
Selected skills: Inferno, Burning Shield, Flame Strike, Flame's Serenade, Jewel Concerto, Creation's Prelude, Deliverance Sword, Knight's Pride
Proposed swaps: none reported
Advisories: Candidate 54031fcf05bbb47e491f is malformed; its role assignments and coverage are inconsistent and cannot be used for ranking., Candidate 0a7ed4a6d08e0afcf3db has a coverage of 100% but relies on unverified item ownership and placeholder items; treat as provisional., Candidate 3313dc2ec4d9a36e933e has incomplete coverage data; its ranking is based on available role assignments only., Candidate 1684fd9f8a6155e4034a is incomplete; its coverage and role assignments are missing, so it is ranked last.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `False`
- **same_top_candidate:** `True`
- **same_ranking:** `True`
- **same_swap:** `False`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `False`
- **token_delta:** `660`
- **cost_delta:** `0.01134883`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 51002; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 50574; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic burst backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `3`
- Unique frontline sets: `None`
- Unique archetypes: `2`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[0.714, 0.714, 0.714]`

- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

# H-F20 — Water Alter Force

Source status: `completed`  
Category: `unclassified`

## Boss Profile

- **Weak:** unknown / not supplied
- **Resist:** unknown / not supplied
- **Null:** unknown / not supplied
- **Absorb:** unknown / not supplied
- **Affinity evidence:** `UNKNOWN`
- **Characteristics:** Not supplied.
- **Mechanics:** Not supplied.
- **Offensive mechanics:** unknown / not supplied
- **Defensive threats:** unknown / not supplied
- **Status effects:** unknown / not supplied
- **Other mechanics:** unknown / not supplied

## Backend Candidates

### Candidate 1 — burst

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, offensive_enablement, survival
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 2 — hybrid

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, setup, offensive_enablement, defensive_reliability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

### Candidate 3 — sustain

Score: `10540.0`; boss matchup component: `24.0`
Mandatory roles: primary_damage, offensive_enablement, stability
Covered roles: boss counter, defense / mitigation, offensive enablement, primary damage, zone setup
Missing roles: unknown / not supplied
Primary damage: unknown / not supplied; boss affinity: `UNKNOWN`
Frontline: Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown); Unknown character (purpose unknown)
Reserve: Unknown character (purpose unknown); Unknown character (purpose unknown)
Capabilities: damage_reduction, damage_reduction_barrier, deploy_zone, direct_damage, inflict_pain
Setup dependencies: requires_another_force, requires_lunatic, requires_pain, requires_poison, requires_zone
Risks: unknown / not supplied

## Analyzer Recommendation

Selected candidate: **Candidate 1 (burst)**
Ranking: Candidate 1 (burst), Candidate 3 (sustain), Candidate 2 (hybrid)
Strategy summary: Use the deterministic burst backend candidate.
Validation: `PASS`
Selected skills: Lunar Caustic, Aether Alchemia, Aether Magia, Flame's Serenade, Jewel Concerto, Creation's Prelude, Deliverance Sword, Knight's Pride
Proposed swaps: none reported
Advisories: The candidate lineup:017f947da82e6b83c732 is missing a required 'archetype' field; treat as 'unknown'., The candidate lineup:017f947da82e6b83c732 has malformed 'character_ids' (contains a role string instead of a character ID); treat as invalid., The candidate lineup:017f947da82e6b83c732 has malformed 'backend_role_assignments' (contains a role string instead of a character ID); treat as invalid., The candidate lineup:017f947da82e6b83c732 has malformed 'skill_package_ids' (contains a role string instead of a character ID); treat as invalid., The candidate lineup:017f947da82e6b83c732 has malformed 'backend_coverage' (contains a role string instead of a character ID); treat as invalid., The candidate lineup:017f947da82e6b83c732 has malformed 'component_scores' (contains a role string instead of a character ID); treat as invalid.
Risks: Item ownership is unverified; the package is a build target, not an inventory claim., Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available., One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable., Only generic item categories are asserted because named catalog items were intentionally omitted., Ore is optional and no specific Ore allocation is required for this package.

## H1 Comparison And Input Budget

- **both_valid:** `True`
- **same_top_candidate:** `True`
- **same_ranking:** `False`
- **same_swap:** `True`
- **candidate_ids_closed_world:** `True`
- **skill_selections_valid:** `True`
- **swap_authorized:** `True`
- **token_delta:** `-389`
- **cost_delta:** `0.0010425599999999999`
- **latency_delta_ms:** `None`
- **Analyzer input budget (baseline_a):** target <= 20000 tokens; observed 21175; status `EXCEEDED`
- **Analyzer input budget (variant_b):** target <= 20000 tokens; observed 21162; status `EXCEEDED`

## Four-Gate Review

### Gate — Damage Affinity / Elemental Viability: `UNKNOWN`

Primary damage element/type is not present in the supplied evidence.

Evidence: unavailable.

### Gate — Boss Mechanic Counter Coverage: `UNKNOWN`

No boss threats with authoritative counter requirements were supplied.

Evidence: unavailable.

### Gate — Team Synergy / Role Coherence: `REVIEW`

Primary win condition: Use the deterministic burst backend candidate.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
| Evidence | `REVIEW` |  |
Warnings:

- Backend scoring reports frontline role overlap.
- One or more selected characters could not be resolved to names.

### Gate — Setup Executability: `FAIL`

Every declared setup dependency is mapped conservatively.

| Evidence item | Status | Supporting detail |
| --- | --- | --- |
| requires_another_force | `REVIEW` | system/player action |
| requires_lunatic | `FAIL` | none found in supplied candidate evidence |
| requires_pain | `REVIEW` | Capability present; provider name unavailable; evidence: capability=inflict_pain; fact_id=skill:8a5a4e1f70487c377725; evidence_id=cap-pain |
| requires_poison | `FAIL` | none found in supplied candidate evidence |
| requires_zone | `REVIEW` | Capability present; provider name unavailable; evidence: capability=deploy_zone; fact_id=skill:575912d04d8a7232ffd1; evidence_id=c6-1-h-witness-aisha-flame-serenade-zone |

## Overall Modeled Viability

**REJECT** (`FAIL`)

At least one modeled gate failed; do not treat this candidate as a supported recommendation.

## Candidate Diversity Audit

- Candidates: `3`
- Unique character sets: `1`
- Unique frontline sets: `None`
- Unique archetypes: `3`
- Identical total scores: `True`
- Identical component scores: `True`
- Character-set Jaccard values: `[1.0, 1.0, 1.0]`

- CANDIDATE_DIVERSITY_WARNING: all candidates contain the same character set.
- CANDIDATE_SCORE_WARNING: all candidates have identical total scores.
- CANDIDATE_SCORE_WARNING: all candidates have identical component-score vectors.
- ORDERING_ONLY_WARNING: candidates differ only by character ordering or placement in supplied data.
- ARCHETYPE_DIFFERENTIATION_WARNING: archetype labels are not materially differentiated by supplied scoring evidence.

## Manual Review

Check only what the supplied evidence supports:

- [ ] Gate 1: primary damage is weak or neutral, with no blocked primary attribute.
- [ ] Gate 2: important boss threats have concrete, evidenced counters.
- [ ] Gate 3: the six-character plan has a clear win condition and role purpose.
- [ ] Gate 4: required setup can be established by a named or explicitly supported provider.
- [ ] I accept the bounded modeled-viability wording; this is not a guaranteed clear.

Reviewer verdict: **Strong candidate / Plausible candidate / Weak candidate / Reject**

Notes: ________________________________________________________________

## Report Limitations

- No combat simulator, turn-by-turn damage calculation, or gameplay clear is performed.
- Missing boss, character, skill, or elemental-taxonomy evidence remains REVIEW or UNKNOWN.
- Projection compression is outside H2 scope; observed input-budget excess is surfaced only.
