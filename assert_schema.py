"""Post-load assertion script for AnotherEden graph schema.

Exits 0 if all expected node types exist with minimum counts.
Exits 1 with a descriptive message if any check fails.

Usage:
    python assert_schema.py

Environment variables:
    NEO4J_URI   — default bolt://localhost:7687
    NEO4J_AUTH  — default neo4j/anothereden  (user/password format)
"""
import os
import sys

# Verify SCHEMA.md exists before attempting Neo4j connection
schema_path = os.path.join(os.path.dirname(__file__), "SCHEMA.md")
if not os.path.isfile(schema_path):
    print("FAIL: SCHEMA.md missing")
    sys.exit(1)

from neo4j import GraphDatabase
from src.etl.constants import EXPECTED_NODE_COUNTS, NEO4J_URI, NEO4J_AUTH

driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

READINESS_NODE_MINIMUMS = {
    "Skill": 1,
    "PassiveSkill": 1,
    "Sidekick": 1,
    "SidekickSkill": 1,
    "SidekickAura": 1,
    "Superboss": 1,
    "Equipment": 1,
}

SCHEMA_VERSION_LABELS = [
    "Skill",
    "PassiveSkill",
    "Sidekick",
    "SidekickSkill",
    "SidekickAura",
    "Superboss",
    "Equipment",
]

SOURCE_URL_LABELS = [
    "Skill",
    "PassiveSkill",
    "Sidekick",
    "SidekickSkill",
    "SidekickAura",
    "Superboss",
    "Equipment",
]

READINESS_QUERIES = [
    (
        "sidekick association",
        """
        MATCH (:Character)-[:UNLOCKS_SIDEKICK]->(:Sidekick)
        RETURN count(*) AS cnt
        """,
    ),
    (
        "sidekick auto skill",
        """
        MATCH (:Sidekick)-[:HAS_AUTO_SKILL]->(:SidekickSkill {skill_kind: 'auto'})
        RETURN count(*) AS cnt
        """,
    ),
    (
        "sidekick charge skill",
        """
        MATCH (:Sidekick)-[:HAS_CHARGE_SKILL]->(:SidekickSkill {skill_kind: 'charge'})
        RETURN count(*) AS cnt
        """,
    ),
    (
        "sidekick aura",
        """
        MATCH (:Sidekick)-[:HAS_AURA]->(:SidekickAura)
        RETURN count(*) AS cnt
        """,
    ),
    (
        "boss affinity and mechanics",
        """
        MATCH (s:Superboss)
        WHERE size(s.weak) > 0
          AND size(s.resist) > 0
          AND size(s.null) > 0
          AND size(s.absorb) > 0
          AND s.mechanics_text IS NOT NULL
          AND s.mechanics_text <> ''
        RETURN count(*) AS cnt
        """,
    ),
    (
        "baseline equipment context",
        """
        MATCH (e:Equipment)
        WHERE e.source_url IS NOT NULL
          AND e.source_url <> ''
          AND (
            (e.effect_text IS NOT NULL AND e.effect_text <> '')
            OR (e.obtain_text IS NOT NULL AND e.obtain_text <> '')
          )
        RETURN count(*) AS cnt
        """,
    ),
]


def _count(session, cypher: str) -> int:
    record = session.run(cypher).single()
    return record["cnt"] if record else 0


failed = False
try:
    with driver.session() as session:
        for label, min_count in EXPECTED_NODE_COUNTS.items():
            cnt = _count(session, f"MATCH (n:{label}) RETURN count(n) AS cnt")
            if cnt < min_count:
                print(f"FAIL: {label} count {cnt} < expected minimum {min_count}")
                failed = True
            else:
                print(f"OK: {label} = {cnt}")

        for label, min_count in READINESS_NODE_MINIMUMS.items():
            cnt = _count(session, f"MATCH (n:{label}) RETURN count(n) AS cnt")
            if cnt < min_count:
                print(f"FAIL: {label} readiness count {cnt} < expected minimum {min_count}")
                failed = True
            else:
                print(f"OK: {label} readiness = {cnt}")

        for label in SCHEMA_VERSION_LABELS:
            missing = _count(
                session,
                f"MATCH (n:{label}) WHERE n.schema_version IS NULL OR n.schema_version = '' RETURN count(n) AS cnt",
            )
            if missing:
                print(f"FAIL: {label} missing schema_version on {missing} node(s)")
                failed = True
            else:
                print(f"OK: {label} schema_version present")

        for label in SOURCE_URL_LABELS:
            missing = _count(
                session,
                f"MATCH (n:{label}) WHERE n.source_url IS NULL OR n.source_url = '' RETURN count(n) AS cnt",
            )
            if missing:
                print(f"FAIL: {label} missing source_url on {missing} node(s)")
                failed = True
            else:
                print(f"OK: {label} source_url present")

        for name, cypher in READINESS_QUERIES:
            cnt = _count(session, cypher)
            if cnt <= 0:
                print(f"FAIL: golden retrieval query produced no rows: {name}")
                failed = True
            else:
                print(f"OK: golden retrieval query '{name}' = {cnt}")
except Exception as exc:
    print(f"FAIL: Could not connect to Neo4j at {NEO4J_URI} — {exc}")
    sys.exit(1)
finally:
    driver.close()

sys.exit(1 if failed else 0)
