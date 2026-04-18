---
phase: quick-3
plan: 3
subsystem: infra
tags: [neo4j, docker, apoc, docker-compose]

# Dependency graph
requires: []
provides:
  - NEO4J_PLUGINS=["apoc"] in docker-compose.yml enables APOC auto-download on Neo4j 5.x startup
  - APOC procedure allowlist and unrestricted env vars enable apoc.* procedures after startup
affects: [phase-1, phase-2, phase-3, langchain-neo4j-integration]

# Tech tracking
tech-stack:
  added: [APOC plugin for Neo4j 5.x]
  patterns: [Neo4j 5.x auto-downloads APOC jar at startup when NEO4J_PLUGINS includes "apoc"]

key-files:
  created: []
  modified: [docker-compose.yml]

key-decisions:
  - "NEO4J_PLUGINS=[\"apoc\"] triggers auto-download on Neo4j 5.x container startup — no manual jar required"
  - "Both unrestricted and allowlist env vars required since Neo4j 4.x — without them APOC procedures blocked even if installed"

patterns-established:
  - "Neo4j APOC security: always pair NEO4J_PLUGINS with both NEO4J_dbms_security_procedures_unrestricted and NEO4J_dbms_security_procedures_allowlist"

requirements-completed: [QUICK-3]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Quick Task 3: Add APOC Plugin to Neo4j Docker Container Summary

**NEO4J_PLUGINS=["apoc"] plus procedure allowlist env vars added to docker-compose.yml, enabling langchain_neo4j.Neo4jGraph to call apoc.meta.data without ClientError on Neo4j 5.x**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-15T00:00:00Z
- **Completed:** 2026-03-15T00:03:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Changed `NEO4J_PLUGINS=[]` to `NEO4J_PLUGINS=["apoc"]` so Neo4j 5.x auto-downloads the APOC jar at container startup
- Added `NEO4J_dbms_security_procedures_unrestricted=apoc.*` to allow APOC procedures to execute
- Added `NEO4J_dbms_security_procedures_allowlist=apoc.*` to whitelist APOC procedures (required since Neo4j 4.x)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add APOC plugin and allowlist to docker-compose.yml** - `f371f7f` (feat)

## Files Created/Modified

- `docker-compose.yml` - Added NEO4J_PLUGINS=["apoc"] and two APOC procedure security env vars to neo4j service

## Decisions Made

- Used NEO4J_PLUGINS env var (Neo4j 5.x auto-download mechanism) rather than manually mounting a jar file — simpler, version-managed by Neo4j
- Both `unrestricted` and `allowlist` vars added as a pair — Neo4j docs require both since 4.x for procedures to be callable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Container restart required.** After this commit, restart the Neo4j container for changes to take effect:

```bash
docker compose down && docker compose up -d
```

Wait ~30 seconds, then verify APOC loaded:

```bash
docker compose logs neo4j | grep -i apoc
```

Expect: `APOC version ... initialised`. After that, `Neo4jGraph(...)` should connect without `ClientError: There is no procedure with the name apoc.meta.data registered`.

## Next Phase Readiness

- Once container is restarted, langchain_neo4j.Neo4jGraph can initialize successfully
- Phase 1 Plan 3 (graph schema / agent work) can proceed without the APOC ClientError blocker

---
*Phase: quick-3*
*Completed: 2026-03-15*
