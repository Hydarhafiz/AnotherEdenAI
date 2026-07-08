"""Milestone 5 Feature C1 atomic capability and review regressions."""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from src.etl.capability_taxonomy import (
    BATCH_SIZE,
    assert_capability_materialization,
    diagnostics,
    generate_review_batch,
    import_review_batch,
    load_capability_taxonomy,
    load_gold_fixtures,
    load_reviews,
    materialize_atomic,
    propose,
)
from src.etl.constants import SCHEMA_VERSION
from src.etl.loader import load_passive_skills, load_sidekicks, load_skills, remove_stale_role_materialization
from src.etl.models import PassiveSkillRow, SidekickAuraRow, SidekickRow, SidekickSkillRow, SkillRow


class AsyncRows:
    def __init__(self, rows):
        self._rows = rows

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for row in self._rows:
            yield row


class Session:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return AsyncRows(self.rows)


class Driver:
    def __init__(self, rows=None):
        self.session_instance = Session(rows)

    def session(self):
        return self.session_instance


def fact(index=0, description="Heals all allies"):
    return {
        "skill_id": f"skill-{index}",
        "character_name": "Mariel",
        "name": f"Pure Cradle {index}",
        "description": description,
        "skill_type": "Healing",
        "source_url": f"https://example.test/skills/{index}",
    }


def write_reviews(path: Path, decisions=()):
    path.write_text(
        json.dumps({"artifact_version": "test", "decisions": list(decisions)}),
        encoding="utf-8",
    )


def review_csv(path: Path, transform):
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = rows[0].keys()
    transform(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_taxonomy_declares_atomic_vocabularies_semantics_and_negative_patterns():
    taxonomy = load_capability_taxonomy()

    assert taxonomy["artifact_version"]
    assert {"deploy_zone", "heal_hp", "direct_damage", "grant_link"} <= set(taxonomy["capabilities"])
    assert {"requires_zone", "requires_stellar_awakened", "limited_use"} <= set(taxonomy["dependencies"])
    assert {"ally", "enemy", "self", "field", "none"} <= set(taxonomy["directions"])
    assert all("negative_patterns" in rule for rule in taxonomy["rules"])
    assert all(rule["value"] not in {"primary_dps", "buffer", "zone_setter"} for rule in taxonomy["rules"])


def test_safety_cutover_removes_old_materializer_and_bumps_schema():
    assert importlib.util.find_spec("src.etl.role_taxonomy") is None
    assert "role_tags" not in SkillRow.model_fields
    assert "role_tags" not in PassiveSkillRow.model_fields
    assert "role_tags" not in SidekickRow.model_fields
    assert SCHEMA_VERSION == "1.5.0"


def test_direction_aware_rules_distinguish_grant_from_dependency_and_negative_patterns():
    proposals = propose(fact(description="Deploy a Fire Zone, inflict Break, and grant Link to all allies."))
    semantics = {(row["proposed_value"], row["proposed_direction"], row["proposed_target"]) for row in proposals}

    assert ("deploy_zone", "field", "zone") in semantics
    assert ("inflict_break", "enemy", "single_enemy") in semantics
    assert ("grant_link", "ally", "party") in semantics
    assert not propose(fact(description="Requires an awakened zone and requires Link."), phase="offensive_support")
    dependencies = {row["proposed_value"] for row in propose(fact(description="Requires an awakened zone."))}
    assert "requires_awakened_zone" in dependencies
    assert "deploy_zone" not in dependencies
    assert "awaken_zone" not in dependencies


def test_models_are_initially_sparse_and_replay_deterministically():
    first = SkillRow.model_validate(fact())
    replay = SkillRow.model_validate(first.model_dump())

    assert first.capabilities == first.dependencies == []
    assert first.capability_evidence_json == "[]"
    assert first.capability_artifact_version == load_capability_taxonomy()["artifact_version"]
    assert replay.model_dump() == first.model_dump()
    assert json.loads(first.capability_diagnostics_json) == {
        "ambiguous": 0, "candidate": 1, "proposed": 1, "proven": 0,
        "rejected": 0, "reviewed": 0, "untagged": 0,
    }


@pytest.mark.parametrize(
    ("decision", "expected_capabilities", "diagnostic"),
    [("approve", ["heal_hp"], "proven"), ("reject", [], "rejected"), ("ambiguous", [], "ambiguous")],
)
def test_only_approved_or_corrected_reviews_become_authoritative(tmp_path, decision, expected_capabilities, diagnostic):
    proposal = propose(fact())[0]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews, [{**proposal, "decision": decision, "reviewer": "alice", "reviewer_notes": "checked"}])

    capabilities, dependencies, evidence, _, counts = materialize_atomic(fact(), reviews)

    assert capabilities == expected_capabilities
    assert dependencies == []
    assert counts[diagnostic] == 1
    if evidence:
        assert evidence[0] == {
            "activation_count": "", "availability": "not_applicable",
            "artifact_version": load_capability_taxonomy()["artifact_version"],
            "direction": "ally", "kind": "capability", "matched_phrase": "Heals",
            "duration_turns": "", "magnitude_unit": "", "magnitude_value": "",
            "review_decision": "approve", "reviewer": "alice", "reviewer_notes": "checked",
            "review_artifact_version": "test",
            "source": "reviewed_rule", "source_fact_id": "skill-0",
            "source_id": "cap-heal", "target": "party", "trigger": "none", "value": "heal_hp",
        }


def test_corrected_review_requires_and_materializes_complete_atomic_semantics(tmp_path):
    proposal = propose(fact())[0]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews, [{
        **proposal, "decision": "correct", "corrected_kind": "dependency",
        "corrected_value": "requires_status", "corrected_direction": "enemy",
        "corrected_target": "single_enemy", "reviewer": "bob", "reviewer_notes": "condition only",
    }])

    capabilities, dependencies, evidence, _, _ = materialize_atomic(fact(), reviews)

    assert capabilities == []
    assert dependencies == ["requires_status"]
    assert evidence[0]["review_decision"] == "correct"
    assert evidence[0]["direction"] == "enemy"


def test_batch_export_is_deterministic_stratified_and_has_reference(tmp_path):
    records = [fact(index) for index in range(BATCH_SIZE)]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews)
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    rows = generate_review_batch(records, phase="defensive_setup", batch_number=2, seed=17, output=first, reviews_path=reviews)
    generate_review_batch(reversed(records), phase="defensive_setup", batch_number=2, seed=17, output=second, reviews_path=reviews)

    assert len(rows) == BATCH_SIZE
    assert first.read_bytes() == second.read_bytes()
    reference = json.loads((tmp_path / "first.reference.json").read_text(encoding="utf-8"))
    assert set(reference["allowed_values"]) == {
        "decision", "kind", "capability", "dependency", "direction", "target",
        "availability", "magnitude_unit", "trigger",
    }
    assert "source_url" in reference["field_guidance"]
    with first.open(encoding="utf-8", newline="") as handle:
        exported = list(csv.DictReader(handle))
    assert all(row["source_text"] and row["source_url"] for row in exported)
    assert all(row["decision"] == "" for row in exported)


def test_batch_generation_refuses_partial_batches(tmp_path):
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews)

    with pytest.raises(ValueError, match="exactly 45"):
        generate_review_batch([fact()], phase="defensive_setup", batch_number=1, seed=0, output=tmp_path / "batch.csv", reviews_path=reviews)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda rows: rows[0].update(decision=""), "Blank or invalid decision"),
        (lambda rows: rows[0].update(decision="invented"), "Blank or invalid decision"),
        (lambda rows: rows[0].update(source_text="edited"), "Immutable review evidence was edited"),
        (lambda rows: rows[0].update(source_fact_id="drifted"), "source-ID drift"),
        (lambda rows: rows[0].update(decision="correct", corrected_kind="capability", corrected_value="invented", corrected_direction="ally", corrected_target="party"), "Malformed correction"),
    ],
)
def test_review_import_rejects_invalid_or_edited_rows(tmp_path, mutation, message):
    records = [fact(index) for index in range(BATCH_SIZE)]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews)
    batch = tmp_path / "batch.csv"
    generate_review_batch(records, phase="defensive_setup", batch_number=1, seed=0, output=batch, reviews_path=reviews)
    review_csv(batch, lambda rows: [row.update(decision="approve", reviewer="alice") for row in rows])
    review_csv(batch, lambda rows: mutation(rows))

    with pytest.raises(ValueError, match=message):
        import_review_batch(batch, records, reviews_path=reviews)


def test_review_import_preserves_all_decisions_notes_and_excludes_reviewed_proposals(tmp_path):
    records = [fact(index) for index in range(BATCH_SIZE)]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews)
    batch = tmp_path / "batch.csv"
    generate_review_batch(records, phase="defensive_setup", batch_number=1, seed=0, output=batch, reviews_path=reviews)
    states = ("approve", "reject", "correct", "ambiguous")

    def complete(rows):
        for index, row in enumerate(rows):
            row.update(decision=states[index % 4], reviewer="reviewer", reviewer_notes=f"note-{index}")
            if row["decision"] == "correct":
                row.update(corrected_kind="capability", corrected_value="barrier", corrected_direction="ally", corrected_target="party")

    review_csv(batch, complete)
    artifact = import_review_batch(batch, records, reviews_path=reviews)

    assert len(artifact["decisions"]) == BATCH_SIZE
    assert set(row["decision"] for row in artifact["decisions"]) == set(states)
    assert all(row["reviewer_notes"] for row in artifact["decisions"])
    with pytest.raises(ValueError, match="only 0 unreviewed proposals"):
        generate_review_batch(records, phase="defensive_setup", batch_number=2, seed=0, output=tmp_path / "next.csv", reviews_path=reviews)


def test_diagnostics_report_review_states_per_capability(tmp_path):
    records = [fact(0), fact(1), fact(2)]
    proposals = [propose(record)[0] for record in records]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews, [
        {**proposals[0], "decision": "approve", "reviewer": "a"},
        {**proposals[1], "decision": "reject", "reviewer": "a"},
    ])

    report = diagnostics(records, reviews)

    assert report["totals"] == {
        "ambiguous": 0, "candidate": 1, "proposed": 3, "proven": 1,
        "rejected": 1, "reviewed": 2, "untagged": 0,
    }
    assert report["per_value"]["heal_hp"] == {
        "candidate": 1, "proposed": 3, "proven": 1, "rejected": 1, "reviewed": 2,
    }


def test_review_and_gold_artifacts_validate_stable_unique_ids(tmp_path):
    reviews = tmp_path / "reviews.json"
    gold = tmp_path / "gold.json"
    write_reviews(reviews, [{"proposal_id": "same"}, {"proposal_id": "same"}])
    gold.write_text(json.dumps({"artifact_version": "test", "fixtures": [{"proposal_id": "same"}, {"proposal_id": "same"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate proposal IDs"):
        load_reviews(reviews)
    with pytest.raises(ValueError, match="duplicate proposal IDs"):
        load_gold_fixtures(gold)


@pytest.mark.asyncio
async def test_loaders_write_atomic_metadata_and_remove_broad_role_properties():
    driver = Driver()
    skill = SkillRow.model_validate(fact())
    passive = PassiveSkillRow(character_name="Aldo", name="Zone Condition", description="Requires an awakened zone.")

    await load_skills(driver, [skill])
    await load_passive_skills(driver, [passive])
    await remove_stale_role_materialization(driver)

    skill_query, skill_params = driver.session_instance.calls[0]
    passive_query, passive_params = driver.session_instance.calls[1]
    cleanup_query, _ = driver.session_instance.calls[2]
    assert "s.capability_artifact_version = row.capability_artifact_version" in skill_query
    assert "p.capability_evidence_json = row.capability_evidence_json" in passive_query
    assert "REMOVE s.role_tags, s.role_evidence_json, s.role_taxonomy_version" in skill_query
    assert "REMOVE p.role_tags, p.role_evidence_json, p.role_taxonomy_version" in passive_query
    assert "REMOVE n.role_tags, n.role_evidence_json, n.role_taxonomy_version" in cleanup_query
    assert skill_params["rows"][0]["capabilities"] == []
    assert passive_params["rows"][0]["dependencies"] == []


@pytest.mark.asyncio
async def test_graph_drift_detection_accepts_exact_materialization_and_schema():
    skill = SkillRow.model_validate(fact())
    graph_rows = [{
        "id": skill.skill_id, "capabilities": skill.capabilities, "dependencies": skill.dependencies,
        "evidence": skill.capability_evidence_json, "version": skill.capability_artifact_version,
        "diagnostics": skill.capability_diagnostics_json, "schema_version": skill.schema_version,
    }]

    await assert_capability_materialization(Driver(graph_rows), [skill], [])


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["capabilities", "dependencies", "evidence", "version", "diagnostics", "schema_version"])
async def test_graph_drift_detection_fails_for_each_contract_field(changed):
    skill = SkillRow.model_validate(fact())
    graph_row = {
        "id": skill.skill_id, "capabilities": skill.capabilities, "dependencies": skill.dependencies,
        "evidence": skill.capability_evidence_json, "version": skill.capability_artifact_version,
        "diagnostics": skill.capability_diagnostics_json, "schema_version": skill.schema_version,
    }
    graph_row[changed] = ["drift"] if changed in {"capabilities", "dependencies"} else "drift"

    with pytest.raises(RuntimeError, match="Atomic capability graph drift detected"):
        await assert_capability_materialization(Driver([graph_row]), [skill], [])


def test_sidekick_facts_have_stable_ids_placement_and_qualifier_proposals():
    skill = SidekickSkillRow(
        sidekick_name="Tetra", name="Restorative Ray", skill_kind="auto",
        description="Heals all allies by 30% for 3 turns.",
    )
    aura = SidekickAuraRow(
        sidekick_name="Tetra", name="Evening Recovery",
        activation_condition="At turn end", effect_text="Restore party MP.",
    )

    skill_proposal = propose(skill.model_dump())[0]
    aura_proposal = propose(aura.model_dump())[0]
    expected = hashlib.sha256(
        f"sidekick_skill|{skill.sidekick_skill_id}|{skill_proposal['rule_id']}".encode()
    ).hexdigest()[:24]

    assert skill.sidekick_skill_id.startswith("sidekick_skill:")
    assert aura.sidekick_aura_id.startswith("sidekick_aura:")
    assert skill_proposal["proposal_id"] == expected
    assert skill_proposal["proposed_availability"] == "main_only"
    assert skill_proposal["proposed_magnitude_value"] == "30"
    assert skill_proposal["proposed_magnitude_unit"] == "percent"
    assert skill_proposal["proposed_duration_turns"] == "3"
    assert aura_proposal["proposed_availability"] == "main_or_sub"
    assert aura_proposal["proposed_trigger"] == "turn_end"


def test_legacy_taxonomy_version_proposal_id_remains_reviewed(tmp_path):
    proposal = propose(fact())[0]
    legacy = {**proposal, "proposal_id": "legacy-version-bound-id", "decision": "approve"}
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews, [legacy])

    capabilities, _, evidence, _, diagnostics_count = materialize_atomic(fact(), reviews)

    assert capabilities == ["heal_hp"]
    assert evidence[0]["source_fact_id"] == fact()["skill_id"]
    assert diagnostics_count["reviewed"] == 1


def test_review_import_validates_sidekick_placement_and_qualifier_corrections(tmp_path):
    records = [
        SidekickSkillRow(
            sidekick_name=f"Sidekick {index}", name="Heal", skill_kind="auto",
            description="Heals all allies by 20% for 2 turns.",
        ).model_dump()
        for index in range(BATCH_SIZE)
    ]
    reviews = tmp_path / "reviews.json"
    write_reviews(reviews)
    batch = tmp_path / "sidekick.csv"
    generate_review_batch(records, phase="defensive_setup", batch_number=1, seed=3, output=batch, reviews_path=reviews)

    def complete(rows):
        for row in rows:
            row.update(
                decision="correct", corrected_kind="capability", corrected_value="heal_hp",
                corrected_direction="ally", corrected_target="frontline",
                corrected_availability="main_only", corrected_magnitude_value="25",
                corrected_magnitude_unit="percent", corrected_activation_count="2",
                corrected_duration_turns="3", corrected_trigger="turn_end", reviewer="alice",
            )

    review_csv(batch, complete)
    artifact = import_review_batch(batch, records, reviews_path=reviews)
    assert len(artifact["decisions"]) == BATCH_SIZE

    review_csv(batch, lambda rows: rows[0].update(corrected_availability="reserve_only"))
    with pytest.raises(ValueError, match="Invalid corrected availability"):
        import_review_batch(batch, records, reviews_path=reviews)


@pytest.mark.asyncio
async def test_sidekick_loader_and_drift_gate_cover_atomic_contract():
    sidekick = SidekickRow(
        name="Tetra", source_url="https://example.test/tetra",
        auto_skills=[SidekickSkillRow(
            sidekick_name="Tetra", name="Heal", skill_kind="auto", description="Heals all allies",
        )],
        auras=[SidekickAuraRow(
            sidekick_name="Tetra", name="Aura", effect_text="Restore MP at turn end",
        )],
    )
    driver = Driver()
    await load_sidekicks(driver, [sidekick])

    sidekick_query, _ = driver.session_instance.calls[0]
    skill_query, skill_params = driver.session_instance.calls[1]
    aura_query, aura_params = driver.session_instance.calls[2]
    assert "s.role_tags = row.role_tags" not in sidekick_query
    assert "skill.sidekick_skill_id = row.sidekick_skill_id" in skill_query
    assert "aura.sidekick_aura_id = row.sidekick_aura_id" in aura_query
    assert skill_params["rows"][0]["capability_artifact_version"]
    assert aura_params["rows"][0]["capability_diagnostics_json"]

    rows = []
    for record_id, row in (
        (sidekick.auto_skills[0].sidekick_skill_id, sidekick.auto_skills[0]),
        (sidekick.auras[0].sidekick_aura_id, sidekick.auras[0]),
    ):
        rows.append({
            "id": record_id, "capabilities": row.capabilities, "dependencies": row.dependencies,
            "evidence": row.capability_evidence_json, "version": row.capability_artifact_version,
            "diagnostics": row.capability_diagnostics_json, "schema_version": row.schema_version,
        })
    await assert_capability_materialization(Driver(rows), [], [], [sidekick])
