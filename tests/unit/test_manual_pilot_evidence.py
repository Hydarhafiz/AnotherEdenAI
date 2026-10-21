"""Offline checks for source-pinned Milestone 6 P2 pilot evidence."""

from __future__ import annotations

import hashlib
import json
import csv
from pathlib import Path

from bs4 import BeautifulSoup

from src.etl.capability_taxonomy import import_review_batch, materialize_atomic
from src.workflow.role_scoring import derive_contextual_role_scores


SCENARIO_PATH = Path("tests/fixtures/m6_p2/pilot_scenarios.json")
CATALOG_PATH = Path("src/etl/kit_catalog.json")
REVIEW_PATH = Path("src/etl/review_batches/m6_p2_pilot_curated.csv")
GHOSTLY_REVIEW_PATH = Path("src/etl/review_batches/m6_p3_toova_ghostly_curated.csv")
DOUBLE_CRUSH_REVIEW_PATH = Path("src/etl/review_batches/m6_p3_toova_double_crush_curated.csv")
ANABEL_REVIEW_PATH = Path("src/etl/review_batches/m6_p3_anabel_holy_mark_curated.csv")
POOL_NAMES = [
    "Aldo", "Feinne", "Cyrus", "Deirdre", "Azami", "Gariyu", "Cerrine", "Levia",
    "Shion", "Toova", "Suzette", "Anabel", "Radias", "Prai", "Aisha", "Rosetta",
    "Mariel", "Yuna", "Mana", "Dunarith",
]
F2P_NAMES = ["Aldo", "Feinne", "Cyrus", "Deirdre", "Azami", "Gariyu", "Cerrine", "Levia"]
CURATED_FACT_IDS = {
    "skill:f5bb48646f223cc4a933",
    "skill:51c08cb8679f98867702",
    "skill:a0bd249d960bbff8471a",
    "skill:ceea158929a089cfb655",
    "skill:5db06e02b58de90695aa",
}


def _objects_by_fact_id(catalog: dict) -> dict[str, dict]:
    return {
        str(fact.get("skill_id") or fact.get("passive_skill_id")): fact
        for character in catalog["characters"]
        for fact in [*character.get("skills", []), *character.get("passive_skills", [])]
    }


def test_scenario_pool_and_seed_rosters_match_exact_legal_kit_receipts():
    scenarios = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    by_name = {row["character"]["display_name"]: row for row in catalog["characters"]}
    pool = scenarios["candidate_pool"]
    pool_by_name = {row["name"]: row for row in pool}

    assert len(catalog["characters"]) == 367
    assert scenarios["candidate_pool_count"] == 20
    assert [row["name"] for row in pool] == POOL_NAMES
    assert len(pool_by_name) == 20
    for candidate in pool:
        record = by_name[candidate["name"]]
        character = record["character"]
        receipt = record["receipt"]
        pinned = candidate["legal_kit_receipt"]
        assert candidate["character_id"] == character["character_id"]
        assert candidate["exact_form"] == character["name"] == character["display_name"]
        assert candidate["is_SA"] is False
        assert candidate["is_SA"] == character["is_SA"]
        assert candidate["light_shadow"] == character["light_shadow"]
        assert pinned["overall_state"] == receipt["overall_state"]
        assert pinned["active_skill_state"] == receipt["active_skill_state"]
        assert pinned["passive_state"] == receipt["passive_state"]
        assert pinned["dependency_state"] == receipt["dependency_state"]
        assert pinned["source_url"] == receipt["source_url"]
        assert pinned["source_revision_sha256"] == receipt["source_revision"]
        assert pinned["source_artifact_fingerprint"] == receipt["source_artifact_fingerprint"]
        assert pinned["active_skill_family_count"] == receipt["active_skill_family_count"]

    assert len(scenarios["scenarios"]) == 6
    for scenario in scenarios["scenarios"]:
        assert len(scenario["candidate_names"]) == len(set(scenario["candidate_names"]))
        assert scenario["candidate_ids"] == [
            by_name[name]["character"]["character_id"] for name in scenario["candidate_names"]
        ]
        assert all(name in pool_by_name for name in scenario["candidate_names"])
        assumptions = scenario["loadout_assumptions"]
        assert assumptions["stellar_awakening"].startswith("not credited")
        assert assumptions["manifest_and_true_manifest"].startswith("excluded")
        assert assumptions["sidekicks"]["owned_or_selected"] == []
        assert assumptions["sidekicks"]["contribution_credit"] == "none"
        assert assumptions["selected_skill_package"].startswith("not fixed")
        assert scenario["roster_feasibility"] == "unknown_not_established"

    by_id = {row["scenario_id"]: row for row in scenarios["scenarios"]}
    assert by_id["rotte-rivel-f2p-inadequacy-investigation"]["candidate_names"] == F2P_NAMES
    assert by_id["celestial-mushroom-suzette-inadequacy-investigation"]["candidate_names"] == [
        *F2P_NAMES, "Suzette",
    ]
    assert all(
        row.get("inadequate_outcome_claimed") is False
        for row in scenarios["scenarios"]
        if row["seed_class"] == "inadequacy_investigation"
    )


def test_boss_scenarios_bind_to_independent_fixtures_and_source_capture_bytes():
    scenarios = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(Path("src/etl/superboss_manifest.json").read_text(encoding="utf-8"))
    expected_path = Path("tests/fixtures/superbosses/live_expected.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    manifest_by_id = {row["canonical_id"]: row for row in manifest["bosses"]}
    expected_by_id = {row["canonical_id"]: row for row in expected["cases"]}

    assert scenarios["bosses"].keys() == {"rotte-rivel", "celestial-mushroom"}
    for boss_id, pinned in scenarios["bosses"].items():
        manifest_row = manifest_by_id[boss_id]
        expected_row = expected_by_id[boss_id]
        capture = Path(manifest_row["capture_path"])
        assert pinned["source_url"] == manifest_row["source_url"]
        assert pinned["manifest_capture_sha256"] == manifest_row["capture_sha256"]
        assert pinned["capture_sha256_verified"] == hashlib.sha256(capture.read_bytes()).hexdigest()
        assert pinned["capture_sha256_verified"] == manifest_row["capture_sha256"]
        assert pinned["expected_fixture_path"] == expected_path.as_posix()
        assert pinned["expected_fixture_sha256"] == hashlib.sha256(expected_path.read_bytes()).hexdigest()
        assert pinned["expected_fixture_authority"] == expected["authority"]
        assert pinned["source_section"] == expected_row["source_section"]
        assert pinned["affinity"] == expected_row["affinity"]
        assert pinned["affinity_state"] == expected_row["affinity_state"]
        assert pinned["mechanic_substrings"] == expected_row["mechanic_substrings"]

    for interaction in scenarios["known_boss_interactions"]:
        capture_text = " ".join(
            BeautifulSoup(
                Path(scenarios["bosses"][interaction["boss_id"]]["capture_path"]).read_bytes(),
                "html.parser",
            ).get_text(" ", strip=True).split()
        )
        for quote in interaction["source_quotes"]:
            assert quote.lower() in capture_text.lower()

    gap = next(row for row in scenarios["owner_adjudications"] if row["id"] == "P2-ROTTE-MARKED-SLOTS")
    assert gap["status"] == "review_unknown"
    assert gap["material"] is True
    assert "non-type Magic" in gap["decision"]
    assert "no counter is asserted" in gap["decision"]
    assert all(
        row["four_gate_positive_eligibility"] == "blocked_by_material_review_unknown"
        for row in scenarios["scenarios"]
        if row["boss_id"] == "rotte-rivel" and row["seed_class"] == "positive_candidate"
    )
    assert scenarios["verification_boundary"]["production_status"].startswith(
        "P3 performed a deterministic in-memory 20-form diagnostic"
    )
    assert scenarios["verification_boundary"]["analyzer_calls"] == 0
    assert scenarios["verification_boundary"]["deterministic_recommendation_run_performed"] is True
    assert scenarios["verification_boundary"]["graph_mutation"] is False


def test_curated_review_batch_replays_and_materializes_only_reviewed_exact_facts(tmp_path: Path):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records_by_id = _objects_by_fact_id(catalog)
    records = [records_by_id[fact_id] for fact_id in sorted(CURATED_FACT_IDS)]
    reviews_path = tmp_path / "capability_reviews.json"
    imported = import_review_batch(REVIEW_PATH, records, reviews_path=reviews_path)
    new_ids = {row["proposal_id"] for row in imported["decisions"]}
    with REVIEW_PATH.open(encoding="utf-8", newline="") as stream:
        batch_rows = list(csv.DictReader(stream))
    batch_ids = {row["proposal_id"] for row in batch_rows}
    assert batch_ids <= new_ids
    assert len(batch_rows) == 11
    assert {row["decision"] for row in batch_rows} == {"approve", "correct", "reject"}
    assert sum(row["decision"] == "approve" for row in batch_rows) == 4
    assert sum(row["decision"] == "correct" for row in batch_rows) == 5
    assert sum(row["decision"] == "reject" for row in batch_rows) == 2

    by_record = {str(row.get("skill_id") or row.get("passive_skill_id")): row for row in records}
    def evidence(fact_id: str) -> list[dict]:
        _capabilities, _dependencies, rows, _version, _counts = materialize_atomic(
            by_record[fact_id], reviews_path
        )
        return rows

    rosetta_rows = evidence("skill:f5bb48646f223cc4a933")
    barrier = next(row for row in rosetta_rows if row["value"] == "damage_reduction_barrier")
    immunity = next(row for row in rosetta_rows if row["value"] == "grant_status_immunity")
    heal = next(row for row in rosetta_rows if row["value"] == "heal_hp")
    assert barrier["magnitude_value"] == "30" and barrier["activation_count"] == "3"
    assert barrier.get("qualifiers", {}) == {}
    assert barrier["direction"] == "ally" and barrier["target"] == "main_and_reserve"
    assert immunity["activation_count"] == "3"
    assert immunity["direction"] == "ally" and immunity["target"] == "party"
    assert immunity["magnitude_value"] == "" and immunity.get("qualifiers", {}) == {}
    assert heal["direction"] == "ally" and heal["target"] == "main_and_reserve"
    assert heal["magnitude_value"] == "" and heal["activation_count"] == "" and heal.get("qualifiers", {}) == {}

    yuna_rows = evidence("skill:51c08cb8679f98867702")
    cleanse = next(row for row in yuna_rows if row["value"] == "remove_status_ailment")
    assert cleanse["activation_count"] == "" and cleanse.get("qualifiers", {}) == {}

    toova_rows = evidence("skill:a0bd249d960bbff8471a")
    toova = {row["value"]: row for row in toova_rows}
    assert {"direct_damage", "inflict_pain", "inflict_poison"} <= set(toova)
    assert toova["direct_damage"]["qualifiers"] == {"attack_type": ["Magic"]}

    great_wall = next(
        row for row in evidence("skill:ceea158929a089cfb655") if row["value"] == "direct_damage"
    )
    assert great_wall["qualifiers"]["element"] == ["Earth"]
    assert great_wall["qualifiers"]["attack_type"] == ["Magic"]

    dragon_rows = evidence("skill:5db06e02b58de90695aa")
    dragon = next(row for row in dragon_rows if row["value"] == "direct_damage")
    assert dragon["qualifiers"]["attack_type"] == ["Pierce"]
    assert dragon["qualifiers"]["element"] == ["Wind"]
    assert not any(row["value"] == "requires_status" for row in dragon_rows)
    assert any(
        row["proposal_id"] == "840b17ea2d70c5bc7b75a1ad" and row["decision"] == "reject"
        for row in batch_rows
    )


def test_anabel_holy_mark_review_keeps_damage_reduction_personal_and_conditional(tmp_path: Path):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    anabel = next(
        row for row in catalog["characters"]
        if row["character"]["display_name"] == "Anabel" and not row["character"].get("is_SA")
    )
    holy_mark = next(row for row in anabel["passive_skills"] if row["name"] == "Holy Mark Stacking")
    reviews_path = tmp_path / "capability_reviews.json"

    imported = import_review_batch(ANABEL_REVIEW_PATH, [holy_mark], reviews_path=reviews_path)
    with ANABEL_REVIEW_PATH.open(encoding="utf-8", newline="") as stream:
        decisions = list(csv.DictReader(stream))

    assert len(decisions) == 1
    assert decisions[0]["source_fact_id"] == "passive:c3fbe82c9a081c027401"
    assert decisions[0]["decision"] == "correct"
    assert decisions[0]["corrected_direction"] == "self"
    assert decisions[0]["corrected_target"] == "self"
    assert decisions[0]["corrected_magnitude_value"] == ""
    assert decisions[0]["corrected_trigger"] == ""
    assert any(row["proposal_id"] == decisions[0]["proposal_id"] for row in imported["decisions"])

    capabilities, dependencies, evidence, _version, diagnostics = materialize_atomic(holy_mark, reviews_path)
    mitigation = next(row for row in evidence if row["value"] == "damage_reduction")
    assert capabilities == ["damage_reduction"]
    assert dependencies == []
    assert mitigation["direction"] == "self" and mitigation["target"] == "self"
    assert mitigation["magnitude_value"] == "50" and mitigation["magnitude_unit"] == "percent"
    assert mitigation["trigger"] == "turn_start"
    assert diagnostics["proven"] == 1 and diagnostics["candidate"] == 1
    assert not any(row["value"] == "cover" for row in evidence)
    assert anabel["receipt"]["source_revision"] in decisions[0]["reviewer_notes"]


def test_curated_fact_receipts_match_the_source_catalog_and_reviewed_decisions():
    scenarios = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    source_facts = _objects_by_fact_id(catalog)
    listed = {row["source_fact_id"]: row for row in scenarios["curated_facts"]}
    assert set(listed) == {
        "skill:3bf0d55a753ab920d4c4",
        "skill:575912d04d8a7232ffd1",
        "skill:5b877ddd3737743f9006",
        "skill:2969aa07d12b8d18a8a4",
        *CURATED_FACT_IDS,
    }
    for fact_id, pin in listed.items():
        record = source_facts[fact_id]
        character_record = next(
            row for row in catalog["characters"]
            if row["character"]["display_name"] == pin["character"]
        )
        character = character_record["character"]
        assert pin["fact_name"] == record["name"]
        assert pin["source_quote"] == record["description"]
        assert pin["source_url"] == record["source_url"] == character["detail_url"]
        assert pin["source_revision_sha256"] == character_record["receipt"]["source_revision"]

        capabilities, _dependencies, evidence_rows, _version, _counts = materialize_atomic(record)
        assert capabilities
        assert evidence_rows
        assert all(row["review_decision"] in {"approve", "correct"} for row in evidence_rows)

    aldo = source_facts["skill:3bf0d55a753ab920d4c4"]
    aisha = source_facts["skill:575912d04d8a7232ffd1"]
    aldo_capabilities, _deps, aldo_rows, _version, _counts = materialize_atomic(aldo)
    aisha_capabilities, _deps, aisha_rows, _version, _counts = materialize_atomic(aisha)
    assert "direct_damage" in aldo_capabilities
    assert "deploy_zone" in aisha_capabilities
    assert all(row["source"] == "reviewed_override" for row in [aldo_rows[0], aisha_rows[0]])


def test_ghostly_whisper_review_preserves_attack_and_withholds_unrepresentable_self_heal(tmp_path: Path):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    record = _objects_by_fact_id(catalog)["skill:5b877ddd3737743f9006"]
    imported = import_review_batch(
        GHOSTLY_REVIEW_PATH,
        [record],
        reviews_path=tmp_path / "capability_reviews.json",
    )
    with GHOSTLY_REVIEW_PATH.open(encoding="utf-8", newline="") as stream:
        decisions = list(csv.DictReader(stream))

    assert len(decisions) == 2
    assert {row["decision"] for row in decisions} == {"approve", "reject"}
    assert {row["proposal_id"] for row in decisions} <= {
        row["proposal_id"] for row in imported["decisions"]
    }
    attack = next(row for row in decisions if row["proposed_value"] == "direct_damage")
    heal = next(row for row in decisions if row["proposed_value"] == "heal_hp")
    assert attack["decision"] == "approve"
    assert "5%-of-damage-dealt self-heal is not credited" in attack["reviewer_notes"]
    assert heal["decision"] == "reject"
    assert "withholds proof" in heal["reviewer_notes"]

    capabilities, dependencies, evidence, _version, diagnostics = materialize_atomic(
        record,
        tmp_path / "capability_reviews.json",
    )
    assert capabilities == ["direct_damage"]
    assert dependencies == []
    assert diagnostics["proven"] == 1
    assert diagnostics["rejected"] == 1
    assert len(evidence) == 1
    assert evidence[0]["direction"] == "enemy"
    assert evidence[0]["target"] == "single_enemy"
    assert evidence[0]["qualifiers"]["element"] == ["Earth"]
    assert evidence[0]["qualifiers"]["attack_type"] == ["Magic"]
    assert evidence[0]["review_decision"] == "approve"
    assert evidence[0]["source_fact_id"] == "skill:5b877ddd3737743f9006"


def test_double_crush_review_materializes_source_facts_and_adds_zone_score(tmp_path: Path):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    records_by_id = _objects_by_fact_id(catalog)
    record = records_by_id["skill:2969aa07d12b8d18a8a4"]
    reviews_path = tmp_path / "capability_reviews.json"
    reviews_path.write_bytes(Path("src/etl/capability_reviews.json").read_bytes())

    imported = import_review_batch(
        DOUBLE_CRUSH_REVIEW_PATH,
        [record],
        reviews_path=reviews_path,
    )
    with DOUBLE_CRUSH_REVIEW_PATH.open(encoding="utf-8", newline="") as stream:
        decisions = list(csv.DictReader(stream))

    assert len(decisions) == 3
    assert {row["proposed_value"]: row["decision"] for row in decisions} == {
        "deploy_zone": "approve",
        "direct_damage": "correct",
        "multi_hit_action": "approve",
    }
    assert {row["proposal_id"] for row in decisions} <= {
        row["proposal_id"] for row in imported["decisions"]
    }

    capabilities, dependencies, evidence, version, diagnostics = materialize_atomic(record, reviews_path)
    facts = {row["value"]: row for row in evidence}
    assert set(capabilities) == {"direct_damage", "deploy_zone", "multi_hit_action"}
    assert dependencies == []
    assert version == "3.3.0"
    assert diagnostics["proven"] == 3
    assert diagnostics["candidate"] == 1
    assert facts["direct_damage"]["qualifiers"] == {
        "attack_type": ["Magic"], "element": ["Earth"],
    }
    assert facts["direct_damage"]["magnitude_value"] == ""
    assert facts["multi_hit_action"]["magnitude_value"] == ""
    assert "x2" in facts["multi_hit_action"]["matched_phrase"]
    assert facts["multi_hit_action"]["source_id"] == "m6-p3-toova-double-crush-multi-hit"
    assert facts["deploy_zone"]["source_id"] == "m6-p3-toova-double-crush-deploy-zone"
    assert facts["deploy_zone"]["direction"] == "field"
    assert facts["deploy_zone"]["target"] == "zone"

    toova = next(
        row for row in catalog["characters"]
        if row["character"]["display_name"] == "Toova" and not row["character"]["is_SA"]
    )
    character = dict(toova["character"])
    character["id"] = character["character_id"]
    skills = []
    passives = []
    for source, target in ((toova["skills"], skills), (toova["passive_skills"], passives)):
        for source_fact in source:
            caps, deps, rows, version, counts = materialize_atomic(source_fact, reviews_path)
            target.append({
                **source_fact,
                "capabilities": caps,
                "dependencies": deps,
                "capability_evidence_json": rows,
                "capability_artifact_version": version,
                "capability_diagnostics_json": counts,
            })
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    boss_row = scenario["bosses"]["celestial-mushroom"]
    result = derive_contextual_role_scores(
        boss={
            "id": "celestial-mushroom",
            "name": "Celestial Mushroom",
            **boss_row["affinity"],
            "required_counters": [],
            "mechanic_tags": [],
        },
        characters=[character],
        skills=skills,
        passives=passives,
        sidekicks=[],
        stellar_awakened={"Toova": "not_awakened"},
        light_shadow_points={"Toova": 0},
    )
    entity = next(row for row in result["entities"] if row["name"] == "Toova")
    package = entity["default_package"]
    names_by_id = {fact["skill_id"]: fact["name"] for fact in skills}

    assert entity["skill_slot_limit"] == 3
    assert [names_by_id[skill_id] for skill_id in package["skill_ids"]] == [
        "Double Crush", "Venom", "Great Wall",
    ]
    assert package["role_scores"]["primary_damage"] == 9
    assert package["role_scores"]["offensive_enablement"] == 0
    assert package["role_scores"]["zone_setup"] == 1
    assert package["contextual_score"] == 48
    double_crush_matchup = next(
        row for row in package["damage_matchups"]
        if row["fact_id"] == "skill:2969aa07d12b8d18a8a4"
    )
    assert double_crush_matchup["element"] == ["Earth"]
    assert double_crush_matchup["attack_type"] == ["Magic"]
    assert double_crush_matchup["state"] == "neutral"
    assert package["primary_damage_weakness_bonus"] == 0
