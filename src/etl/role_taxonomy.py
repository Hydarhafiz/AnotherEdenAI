"""Deterministic, artifact-backed role tagging and graph drift detection."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

TAXONOMY_PATH = Path(__file__).with_name("role_taxonomy.json")


@lru_cache(maxsize=1)
def load_role_taxonomy() -> dict[str, Any]:
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    roles = taxonomy.get("roles", [])
    if not taxonomy.get("version") or len(roles) != len(set(roles)):
        raise ValueError("Role taxonomy requires a version and unique role vocabulary")
    role_set = set(roles)
    record_types = {"skill", "passive"}
    confidence_levels = {"low", "medium", "high"}
    for rule in taxonomy.get("rules", []):
        if (
            rule.get("role") not in role_set
            or not rule.get("id")
            or not rule.get("pattern")
            or not set(rule.get("record_types", [])).issubset(record_types)
            or not rule.get("record_types")
            or rule.get("confidence") not in confidence_levels
        ):
            raise ValueError(f"Invalid role taxonomy rule: {rule!r}")
        re.compile(rule["pattern"], re.IGNORECASE)
    for override in taxonomy.get("overrides", []):
        if (
            override.get("role") not in role_set
            or not override.get("id")
            or not override.get("record_id")
            or override.get("record_type") not in record_types
            or override.get("confidence") not in confidence_levels
        ):
            raise ValueError(f"Invalid role taxonomy override: {override!r}")
    return taxonomy


def materialize_roles(record_type: str, record: dict[str, Any]) -> tuple[list[str], list[dict[str, str]], str]:
    if record_type not in {"skill", "passive"}:
        raise ValueError(f"Unsupported role record type: {record_type!r}")
    taxonomy = load_role_taxonomy()
    source_id = str(record.get("skill_id") or record.get("passive_skill_id") or "")
    fields = ("name", "description", "skill_type", "passive_type", "section")
    source_text = " ".join(str(record.get(field) or "") for field in fields)
    if record.get("multiplier") is not None:
        source_text += " multiplier"

    matches: dict[str, dict[str, str]] = {}
    for rule in taxonomy.get("rules", []):
        if record_type in rule["record_types"] and re.search(rule["pattern"], source_text, re.IGNORECASE):
            matches[rule["role"]] = {
                "role": rule["role"], "source": "rule", "source_id": rule["id"],
                "source_fact_id": source_id, "confidence": rule["confidence"],
            }
    for override in taxonomy.get("overrides", []):
        if override.get("record_type") == record_type and override.get("record_id") == source_id:
            matches[override["role"]] = {
                "role": override["role"], "source": "override", "source_id": override["id"],
                "source_fact_id": source_id, "confidence": override["confidence"],
            }
    evidence = sorted(matches.values(), key=lambda item: item["role"])
    return [item["role"] for item in evidence], evidence, taxonomy["version"]


def canonical_evidence_json(evidence: list[dict[str, str]]) -> str:
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"))


async def assert_role_materialization(driver, skills: list[Any], passives: list[Any]) -> None:
    expected = {
        row.skill_id: (row.role_tags, row.role_evidence_json, row.role_taxonomy_version)
        for row in skills
    }
    expected.update({
        row.passive_skill_id: (row.role_tags, row.role_evidence_json, row.role_taxonomy_version)
        for row in passives
    })
    if not expected:
        return
    query = """
MATCH (n) WHERE (n:Skill OR n:PassiveSkill)
  AND coalesce(n.skill_id, n.passive_skill_id) IN $ids
RETURN coalesce(n.skill_id, n.passive_skill_id) AS id, n.role_tags AS tags,
       n.role_evidence_json AS evidence, n.role_taxonomy_version AS version
"""
    async with driver.session() as session:
        result = await session.run(query, ids=list(expected))
        actual = {row["id"]: (row["tags"] or [], row["evidence"] or "", row["version"]) async for row in result}
    drift = sorted(key for key, value in expected.items() if actual.get(key) != value)
    if drift:
        raise RuntimeError(f"Role taxonomy materialization drift detected for {len(drift)} records: {drift[:10]}")
