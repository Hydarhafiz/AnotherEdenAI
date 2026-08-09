# Recommendation Validation Guide

Use this guide to verify typed production retrieval, deterministic Feature D
hard filtering and contextual role scoring, plus the legacy exploratory
candidate boundary and final graph legality checks. The broad-context
candidate/analyzer path remains superseded for Features D-G; it is not evidence
of production RoleScores or coverage.

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

## 4. Inspect graph readiness

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

## 5. Run the Mimi smoke test

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

## 6. Read correction and partial-result diagnostics

Progress distinguishes these counters and phases:

- `cypher_retry_count`: retrieval/query repair only.
- `provider_transport_retries`: malformed or failed provider transport.
- `analyzer_call_count`: one initial selection plus corrections; maximum 3.
- `analyzer_correction_rounds`: maximum 2.
- `structured_output_errors`: JSON/normalization failures.
- `candidate_validation_errors`: hard-field code, path, and allowed IDs.
- `final_legality_errors`: graph-backed rejection after formatting.

A fully valid first response must show one analyzer call and zero correction
rounds. Valid lineups must remain unchanged while invalid siblings are corrected.
After the cap, invalid lineups are warnings only. One to three valid lineups
render; missing archetypes are named. Zero valid lineups returns a classified
error such as `analyzer_correction_exhausted`,
`final_legality_exhausted`, or `cypher_retrieval_exhausted`.

## 7. Report the result

Record the prompt, roster, sidekicks, SA states, ETL source mode, schema-check
result, rendered archetypes, all counters, warnings/error type, and any rejected
diagnostic code/path/allowed IDs. For each rendered lineup, report any suspect
hero, skill, passive, equipment, Grasta, citation, or Mimi affinity claim.
