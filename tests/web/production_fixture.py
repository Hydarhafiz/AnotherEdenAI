"""Read-only graph-record fixture from existing reviewed Mushroom pilot sources.

This emulates driver records, not Cypher execution or graph freshness. Runtime
retrieval, scoring, candidate generation and final legality remain real callers.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

from src.etl.capability_taxonomy import import_review_batch, materialize_atomic


REPO = Path(__file__).resolve().parents[2]


class PilotGraphRecords:
    def __init__(self, scratch: Path):
        scenarios = json.loads((REPO / "tests/fixtures/m6_p2/pilot_scenarios.json").read_text())
        scenario = next(
            row for row in scenarios["scenarios"]
            if row["scenario_id"] == "celestial-mushroom-strong-candidates"
        )
        self.roster = scenario["candidate_names"]
        pinned = scenarios["bosses"]["celestial-mushroom"]
        self.boss = {
            "id": "celestial-mushroom", "name": pinned["name"],
            "source_url": pinned["source_url"], **pinned["affinity"],
            **{f"{key}_state": value for key, value in pinned["affinity_state"].items()},
            "mechanics_text": "; ".join(pinned["mechanic_substrings"]),
            "section_bounded": True, "recommendation_ready": True,
            "section_anchor": "Rippling_Forest_.5B1.5D.5B2.5D_.5B3.5D",
            "source_section": pinned["source_section"],
            "required_counters": [], "mechanic_tags": [],
        }
        catalog = json.loads((REPO / "src/etl/kit_catalog.json").read_text())
        selected = [row for row in catalog["characters"] if row["character"]["name"] in self.roster]
        facts = [fact for row in selected for fact in [*row["skills"], *row["passive_skills"]]]
        reviews = scratch / "capability_reviews.json"
        reviews.write_bytes((REPO / "src/etl/capability_reviews.json").read_bytes())
        for batch in (
            "m6_p2_pilot_curated.csv", "m6_p3_toova_ghostly_curated.csv",
            "m6_p3_toova_double_crush_curated.csv", "m6_p3_anabel_holy_mark_curated.csv",
        ):
            import_review_batch(REPO / "src/etl/review_batches" / batch, facts, reviews_path=reviews)

        self.characters = []
        self.skills = []
        self.passives = []
        for record in selected:
            character = deepcopy(record["character"])
            character["id"] = character["character_id"]
            character["traits"] = character["personalities"]
            self.characters.append(character)
            for source, target, id_key in (
                (record["skills"], self.skills, "skill_id"),
                (record["passive_skills"], self.passives, "passive_skill_id"),
            ):
                for fact in source:
                    caps, deps, evidence, version, counts = materialize_atomic(fact, reviews)
                    target.append({
                        **fact, "id": fact[id_key], "character_id": character["id"],
                        "capabilities": caps, "dependencies": deps,
                        "capability_evidence_json": json.dumps(evidence),
                        "capability_artifact_version": version,
                        "capability_diagnostics_json": json.dumps(counts),
                    })
        self.reads = []
        self.legality_reads = 0

    async def execute_query(self, cypher, **parameters):
        assert not re.search(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP)\b", cypher, re.I)
        self.reads.append(cypher)
        if "hero_names" in parameters:
            self.legality_reads += 1
            names = set(parameters["hero_names"])
            characters = [row for row in self.characters if row["name"] in names]
            rows = [{
                "known_characters": [row["name"] for row in characters],
                "known_sidekicks": [],
                "character_rows": [{"character": row["name"], "weapon": row["weapon"]} for row in characters],
                "trait_rows": [{"character": row["name"], "trait": trait} for row in characters for trait in row["traits"]],
                "skill_rows": self._legality_facts(self.skills, names),
                "passive_rows": self._legality_facts(self.passives, names),
                "grasta_rows": [],
            }]
        elif "boss_id" in parameters:
            assert "MATCH (b:Superboss)" in cypher
            rows = [deepcopy(self.boss)] if parameters["boss_id"] == self.boss["name"] else []
        elif "input" in parameters:
            assert "MATCH (c:Character)" in cypher
            key = "canonical" if "AS canonical" in cypher else "name"
            rows = [{key: row["name"]} for row in self.characters if row["name"].casefold() == parameters["input"].casefold()]
        elif "HAS_PASSIVE_SKILL" in cypher:
            rows = [{"fact": row} for row in self.passives if row["character_name"] in parameters["roster"]]
        elif "HAS_SKILL" in cypher:
            rows = [{"fact": row} for row in self.skills if row["character_name"] in parameters["roster"]]
        elif "MATCH (c:Character) WHERE c.name IN $roster" in cypher:
            rows = [{"fact": row} for row in self.characters if row["name"] in parameters["roster"]]
        elif "MATCH (g:Grasta)" in cypher or "MATCH (e:Equipment)" in cypher:
            # No named items: existing generic package assumptions must suffice.
            rows = []
        else:
            raise AssertionError(f"Unexpected fixture query: {cypher}")
        return deepcopy(rows), None, None

    def _legality_facts(self, facts, names):
        return [{
            "character": row["character_name"], "name": row["name"],
            "gated": row.get("requires_stellar_awakened", False),
        } for row in facts if row["character_name"] in names]

    def session(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def run(self, cypher, **parameters):
        assert "MATCH (m:MechanicReference)" in cypher
        self.reads.append(cypher)

        async def records():
            for reference in []:
                yield reference
        return records()
