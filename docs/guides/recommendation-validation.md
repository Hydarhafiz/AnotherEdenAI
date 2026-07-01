# Recommendation Validation Guide

Use this guide to verify the Feature C candidate boundary, bounded correction
loop, partial-result behavior, and final graph legality checks.

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

Feature C's focused tests are:

```bash
uv run pytest \
  tests/workflow/test_candidates.py \
  tests/workflow/test_feature_c_correction.py \
  tests/workflow/test_feature_c_partial_output.py \
  tests/workflow/test_graph.py \
  tests/workflow/test_format.py \
  tests/web/unit/test_streaming.py
```

## 3. Inspect graph readiness

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

## 4. Run the Mimi smoke test

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

## 5. Read correction and partial-result diagnostics

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

## 6. Report the result

Record the prompt, roster, sidekicks, SA states, ETL source mode, schema-check
result, rendered archetypes, all counters, warnings/error type, and any rejected
diagnostic code/path/allowed IDs. For each rendered lineup, report any suspect
hero, skill, passive, equipment, Grasta, citation, or Mimi affinity claim.
