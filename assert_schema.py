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

failed = False
try:
    with driver.session() as session:
        for label, min_count in EXPECTED_NODE_COUNTS.items():
            result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
            record = result.single()
            cnt = record["cnt"] if record else 0
            if cnt < min_count:
                print(f"FAIL: {label} count {cnt} < expected minimum {min_count}")
                failed = True
            else:
                print(f"OK: {label} = {cnt}")
except Exception as exc:
    print(f"FAIL: Could not connect to Neo4j at {NEO4J_URI} — {exc}")
    sys.exit(1)
finally:
    driver.close()

sys.exit(1 if failed else 0)
