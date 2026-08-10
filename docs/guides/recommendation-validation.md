# Recommendation Validation Guide

Use this guide to verify typed production retrieval, deterministic Feature D
hard filtering and contextual role scoring, Feature F backend lineup generation,
the Feature G compact analyzer boundary, plus the legacy exploratory candidate
boundary and final graph legality checks.
The broad-context candidate/analyzer path is not evidence of production
RoleScores, coverage, beam bounds, or backend candidate legality.

## 1. Prepare the local services

Run commands from the repository root. Use the project environment rather than
bare Python or pytest.

```bash
docker compose up -d
uv run python assert_schema.py
```

`assert_schema.py` must exit successfully. If the graph is absent or stale, load
it before testing:

```bash
uv run python -m src.etl.run_etl
uv run python assert_schema.py
```

The ETL command is the full orchestrator, but it does not always have to scrape.
When current parsed artifacts already exist, use:

```bash
ETL_SOURCE_MODE=parsed uv run python -m src.etl.run_etl
```

Use live/full scraping only when the cached source data is missing or must be
refreshed. See [ETL_GUIDE.md](ETL_GUIDE.md) for crawl scopes and browser
requirements.

## 2. Run automated checks

The local suite does not require Neo4j:

```bash
uv run pytest -m "not integration" --tb=short
```

With Neo4j running and the schema loaded, run the full suite:

```bash
uv run pytest --tb=short
```

Feature D's focused deterministic checks are:

```bash
uv run pytest \
  tests/workflow/test_lineup_generation.py \
  tests/workflow/test_analyzer.py \
  tests/workflow/test_role_scoring.py \
  tests/workflow/test_feature_b_production.py \
  tests/workflow/test_matchup.py \
  tests/workflow/test_legality.py
```

## 3. Inspect Feature D role-score output

`ProductionRetrieval.role_scores` is backend-owned output for later candidate
generation. It records the `policy_version`, capability artifact versions, the
only valid role IDs, per-entity score breakdowns, reviewed evidence, explicit
rejection reasons, and deterministic role pools. Its fixed dimensions are
`primary_damage`, `offensive_enablement`, `zone_setup`,
`defense_mitigation`, `recovery_protection`, `tank_control`, `af_support`,
`mp_sustain`, `boss_counter`, and `reserve_utility`.

Check that null/absorb-only and no-neutral-or-better primary damage candidates
are rejected before a normal pool is built. A required recorded boss counter
may appear after position eight only with `counter_exception: true`. Each
character shortlist contains no unavailable or non-proven skill and is capped
at six choices; the backend default package selects three or four IDs when that
many legal choices exist. Candidate, rejected, ambiguous, dependency-only, and
untagged facts are diagnostics, not score or coverage evidence.

The analyzer is not an input to this contract: it cannot author role IDs,
RoleScores, evidence, pool membership, or coverage.

## 4. Inspect Feature F backend candidates

`ProductionRetrieval.lineup_candidates` is the deterministic backend result
consumed by typed candidate preparation. It contains the versioned capability
templates, scoring policy, legal candidate objects, component breakdowns,
assumptions, allocation validation, pruning reasons, and structured diagnostics.
It must be inspected before any analyzer refinement is considered.

Run the durable offline checks:

```bash
uv run pytest tests/workflow/test_lineup_generation.py
```

Pass conditions:

- Burst, sustain, and hybrid have explicit mandatory and optional capability
  groups; one multifunction hero may satisfy multiple proven groups.
- Candidate expansion is deterministic and every beam step retains at most 50
  partial combinations.
- Each returned candidate has six distinct heroes, four frontline heroes, two
  reserves, a selected three-to-four-skill package, a validated build
  allocation, component scores, and any assumption/uncertainty penalties.
- Sidekick contributions respect main/sub placement and never consume hero
  slots.
- Exact and near-duplicate strategies are removed while distinct archetypes are
  retained when legal; the result contains no more than ten candidates.
- Sparse or infeasible input returns a typed partial/zero result with dominant
  causes. A zero-candidate result records zero analyzer calls.

No analyzer response can add a hero, package, skill, sidekick, capability, or
coverage claim to this backend result. Compact projection and bounded analyzer
refinement are the subsequent Feature G boundary.

## 5. Inspect Feature G compact projection and refinement

Run the offline Feature G contract checks:

```bash
.venv/bin/pytest -q tests/workflow/test_analyzer.py
```

Pass conditions:

- The projection contains only referenced backend candidates, selected hero
  skill/passive/package facts, boss facts, legal swaps, constraints, and
  citations; rejected roster entries and broad catalogs are absent.
- DeepSeek and OpenRouter adapters emit the same structured-output request and
  normalized response/usage/error envelope. The provider and model are
  explicit per run, and no key or credential is read or stored by the adapter.
- Analyzer responses cannot author candidate IDs, RoleScores, role IDs,
  mandatory coverage, or out-of-bundle skill/swap IDs. Display-role wording is
  advisory only.
- One initial call plus one fragment-only correction is the hard cap. Valid
  fragments are frozen; lower-scoring or invalid swaps/packages restore the
  deterministic backend default.
- Provider failure or skipped refinement returns one to three legal backend
  candidates with a clear degraded label and zero transport retries.

No paid provider call or live all-boss scrape is part of Feature G. Those
actions require the named Post-Feature-G Human Checkpoint.

## 6. Inspect graph readiness

In Neo4j Browser, confirm Mimi has a source and affinity/mechanics facts:

```cypher
MATCH (b)
WHERE b.name = 'Mimi'
RETURN labels(b), properties(b);
```

Confirm the owned roster resolves to canonical character records and that skills,
passives, traits, and stable IDs are present:

```cypher
MATCH (c:Character)
WHERE c.name IN $roster
OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
OPTIONAL MATCH (c)-[:HAS_PASSIVE_SKILL]->(p:PassiveSkill)
OPTIONAL MATCH (c)-[:HAS_TRAIT]->(t:Trait)
RETURN c.name, c.display_name, c.character_id,
       count(DISTINCT s), count(DISTINCT p), collect(DISTINCT t.name)
ORDER BY c.name;
```

Replace `$roster` with the roster under test. Missing roster entries must appear
as candidate-coverage warnings; they must not silently disappear because of a
row limit.

For a suspicious Grasta, inspect both the convenience property and relationship:

```cypher
MATCH (g:Grasta)
WHERE g.name = $grasta_name OR g.display_name = $grasta_name
OPTIONAL MATCH (g)-[:REQUIRES_TRAIT]->(t:Trait)
RETURN g.grasta_id, g.name, g.display_name, g.personality_req,
       g.weapon_req, g.acquisition_class, g.max_theoretical_copies,
       collect(DISTINCT t.name) AS required_traits;
```

The relationship is the normalized graph constraint. A raw
`personality_req = 'Amnesia'` with an empty projected array is not sufficient
to prove compatibility unless the candidate builder can resolve the requirement.

## 7. Run the Mimi smoke test

Start the app:

```bash
uv run fastapi dev src/web/app.py
```

Open `http://localhost:8000`, enter the exact owned roster used for Feature B,
include owned sidekicks and Stellar Awakening states, then submit the historical
prompt. If that prompt is unavailable, use the repository baseline:

> Create lineups to defeat Mimi.

Pass conditions:

- At least one recommendation renders; one or two are valid partial success.
- Every rendered lineup has exactly four frontline and two reserve heroes.
- Every hero is owned or permanently F2P-available and appears only once.
- Skills, passives, sidekicks, equipment, and Grasta come from graph candidates.
- Named unique equipment is not reused illegally.
- Grasta satisfy weapon/personality/cardinality constraints.
- Pain/Poison Grasta have a selected or explained status source.
- Mimi affinity claims match the graph and citations are present.
- No numeric win probability or unsupported exact damage claim appears.

## 8. Read correction and partial-result diagnostics

Progress distinguishes these counters and phases:

- `cypher_retry_count`: retrieval/query repair only.
- `provider_transport_retries`: malformed or failed provider transport.
- `analyzer_call_count`: provider calls made after backend candidate generation;
  a Feature F zero-candidate result must leave this at 0. The later compact
  projection/refinement feature owns the final analyzer call cap.
- `analyzer_correction_rounds`: Feature G maximum 1; the legacy exploratory
  correction path may still report its historical maximum of 2.
- `structured_output_errors`: JSON/normalization failures.
- `candidate_validation_errors`: hard-field code, path, and allowed IDs.
- `final_legality_errors`: graph-backed rejection after formatting.

A fully valid first response must show one analyzer call and zero correction
rounds. Valid lineups must remain unchanged while invalid siblings are corrected.
After the cap, invalid lineups are warnings only. One to three valid lineups
render; missing archetypes are named. Zero valid lineups returns a classified
error such as `analyzer_correction_exhausted`,
`final_legality_exhausted`, or `cypher_retrieval_exhausted`.

## 9. Report the result

Record the prompt, roster, sidekicks, SA states, ETL source mode, schema-check
result, rendered archetypes, all counters, warnings/error type, and any rejected
diagnostic code/path/allowed IDs. For each rendered lineup, report any suspect
hero, skill, passive, equipment, Grasta, citation, or Mimi affinity claim.

## 10. Verify the Feature G1 thirty-boss corpus

Feature G1 is a fixed, explicit corpus rather than an all-boss crawl. The
authoritative source manifest is `src/etl/superboss_manifest.json`; its final
state contains exactly ten weak (1.0-4.0), ten medium (4.5-8.8), and ten
strong (9.0-12.0) canonical IDs. Each record carries aliases, an exact detail
URL, a section anchor, cohort, variant relationship, five selection-rationale
fields, and `recommendation_ready` status. A canonical ID may appear in only
one cohort.

Run the deterministic corpus checks:

```bash
.venv/bin/pytest -q tests/unit/test_superboss_corpus.py
```

The parser fixtures in `tests/fixtures/superbosses/` are durable source-bound
replays: `cached_weak_expected.json` covers the five repaired cached bosses,
`live_expected.json` covers the twenty-five authorized detail captures, and
`production_expected.json` covers feasible, typed-infeasible, compact, cited,
and degraded offline outcomes. These fixtures are independent of parser output
and remain under the same single feature commit as the manifest.

Pass conditions for every boss are canonical identity/alias resolution,
explicit bounded section ownership, affinity state separation
(`confirmed_values`, `confirmed_empty`, or `unknown`), mechanics evidence and
source citation, deterministic replay, production readiness, compact projection
of the boss facts, and a typed degraded fallback. Unknown affinity is preserved
as uncertainty; it is never promoted to a weakness or resistance by inference.
Whole-page mechanics fallback cannot make a boss recommendation-ready.

Do not refresh or expand this corpus from the index during ordinary validation.
Live refreshes require a new bounded human checkpoint, and Feature H / paid
provider calls remain outside this gate.
