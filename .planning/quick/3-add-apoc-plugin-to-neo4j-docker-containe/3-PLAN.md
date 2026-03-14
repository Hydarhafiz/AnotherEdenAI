---
phase: quick-3
plan: 3
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
autonomous: true
requirements: [QUICK-3]

must_haves:
  truths:
    - "Neo4j container starts with APOC installed"
    - "langchain_neo4j.Neo4jGraph connects without apoc.meta.data error"
  artifacts:
    - path: "docker-compose.yml"
      provides: "NEO4J_PLUGINS=[\"apoc\"] and APOC procedure allowlist env vars"
      contains: "NEO4J_PLUGINS"
  key_links:
    - from: "docker-compose.yml NEO4J_PLUGINS"
      to: "Neo4j container APOC installation"
      via: "Neo4j 5.x auto-download on startup"
      pattern: "NEO4J_PLUGINS.*apoc"
---

<objective>
Enable the APOC plugin in the Neo4j Docker container so that langchain_neo4j.Neo4jGraph works correctly.

Purpose: `Neo4jGraph(...)` calls `apoc.meta.data` on initialization. Without APOC installed, it raises `ClientError: There is no procedure with the name apoc.meta.data registered`.

Output: Updated docker-compose.yml with APOC plugin declared and procedure allowlist configured.
</objective>

<execution_context>
@/home/shogunix/.claude/get-shit-done/workflows/execute-plan.md
@/home/shogunix/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@docker-compose.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add APOC plugin and allowlist to docker-compose.yml</name>
  <files>docker-compose.yml</files>
  <action>
    Edit the `neo4j` service environment section in docker-compose.yml:

    1. Change `NEO4J_PLUGINS=[]` to `NEO4J_PLUGINS=["apoc"]`
       (Neo4j 5.x will auto-download and install the APOC jar on container startup)

    2. Add two new environment entries after the NEO4J_PLUGINS line:
       ```
       - NEO4J_dbms_security_procedures_unrestricted=apoc.*
       - NEO4J_dbms_security_procedures_allowlist=apoc.*
       ```
       These are required since Neo4j 4.x — without them, APOC procedures are blocked even if installed.

    The final environment block should look like:
    ```yaml
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH:-neo4j/anothereden}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
      - NEO4J_dbms_memory_heap_max__size=512m
    ```

    Do not change any other section of the file.
  </action>
  <verify>
    grep -E "NEO4J_PLUGINS|unrestricted|allowlist" /home/shogunix/AnotherEdenAI/docker-compose.yml
    Expected output shows three lines:
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
  </verify>
  <done>docker-compose.yml contains NEO4J_PLUGINS=["apoc"] and both procedure allowlist vars; no other content changed</done>
</task>

</tasks>

<verification>
After the executor completes the task, the human must restart the Neo4j container for the changes to take effect:

```bash
docker compose down && docker compose up -d
```

Wait ~30 seconds for startup, then confirm APOC is active:

```bash
docker compose logs neo4j | grep -i apoc
```

Expect a line like: `APOC version ... initialised`.

Then rerun the failing code — `Neo4jGraph(...)` should connect without errors.
</verification>

<success_criteria>
- docker-compose.yml has NEO4J_PLUGINS=["apoc"] (not [])
- docker-compose.yml has both APOC procedure security vars
- After human restarts container, Neo4jGraph connects without ClientError
</success_criteria>

<output>
After completion, create `.planning/quick/3-add-apoc-plugin-to-neo4j-docker-containe/3-SUMMARY.md`
</output>
