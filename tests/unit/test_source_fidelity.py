"""Acceptance coverage for the Milestone 6 C1.1 source-fidelity gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.etl.source_fidelity import (
    FIDELITY_DIMENSIONS,
    REQUIRED_ARCHETYPES,
    build_source_fidelity_report,
)


MANIFEST = Path("src/etl/source_fidelity_manifest.json")
ORACLE = Path("src/etl/source_fidelity_oracle.json")
CATALOG = Path("src/etl/kit_catalog.json")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def replay_report() -> dict:
    if not Path("data/raw/characters").exists():
        pytest.skip("accepted raw captures are required for C1.1 replay")
    return build_source_fidelity_report()


@pytest.fixture(scope="module")
def evaluated_report() -> dict:
    if not Path("data/raw/characters").exists():
        pytest.skip("accepted raw captures are required for C1.1 replay")
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    return build_source_fidelity_report(oracle=oracle, include_held_out=True)


def test_manifest_is_deterministic_stratified_and_not_a_percentage_split(manifest: dict):
    assert manifest["selection_policy"]["random_percentage_split"] is False
    assert manifest["selection_policy"]["known_regressions_are_generalization_evidence"] is False
    assert len(manifest["known_regressions"]) == 7
    assert 20 <= len(manifest["development_witnesses"]) <= 30
    assert 20 <= len(manifest["held_out_witnesses"]) <= 25
    assert not (
        {row["witness_id"] for row in manifest["development_witnesses"]}
        & {row["witness_id"] for row in manifest["held_out_witnesses"]}
    )
    for cohort in ("development_witnesses", "held_out_witnesses"):
        covered = {archetype for row in manifest[cohort] for archetype in row["archetypes"]}
        assert set(REQUIRED_ARCHETYPES) <= covered


def test_witnesses_use_real_catalog_fact_and_capture_identities(manifest: dict, catalog: dict):
    facts = {
        str(fact.get("skill_id") or fact.get("passive_skill_id")): record
        for record in catalog["characters"]
        for fact in [*record.get("skills", []), *record.get("passive_skills", [])]
    }
    for cohort in ("known_regressions", "development_witnesses", "held_out_witnesses"):
        for witness in manifest[cohort]:
            if witness["source_kind"] != "character":
                continue
            assert witness["fact_id"] in facts
            assert witness["entity_name"] == facts[witness["fact_id"]]["receipt"]["character_name"]
            assert witness["source_capture_sha256"] == facts[witness["fact_id"]]["receipt"]["source_revision"]
            assert len(witness["source_capture_sha256"]) == 64


def test_source_slice_fixture_is_capture_derived_and_all_witnesses_bind(replay_report: dict):
    fixture = replay_report["witness_replay"]["source_slice_fixture"]
    assert fixture["loaded"] is True
    assert fixture["passed_count"] == 54
    assert fixture["failed_count"] == 0
    assert fixture["unknown_count"] == 0
    for cohort in ("known_regressions", "development", "held_out"):
        rows = replay_report["witness_replay"][cohort]
        assert all(row["source_identity_status"] == "passed" for row in rows)
        assert all(row["source_record_selection_status"] == "passed" for row in rows)
        assert all(row["source_fixture_status"] == "passed" for row in rows)
        assert all(row["record_id"] for row in rows)
        assert all(row["source_slice_sha256"] for row in rows)


def test_known_regressions_are_separate_real_identity_evidence(replay_report: dict):
    rows = replay_report["known_regressions"]
    assert len(rows) == 7
    assert len({row["regression_key"] for row in rows}) == 7
    assert all(row["generalization_evidence"] is False for row in rows)
    assert all(row["record_id"] for row in rows)
    assert {row["entity_name"] for row in rows} == {
        "Iphi",
        "Alma (Another Style)",
        "Tetra (Another Style)",
        "Darunis",
        "Shigure (Extra Style)",
        "Kumos (Another Style)",
        "Anabel (Extra Style)",
    }


def test_full_catalog_replay_and_sidekick_kinds_are_separate(replay_report: dict):
    replay = replay_report["full_catalog_replay"]
    assert replay["character_identity_denominator"] == 367
    assert replay["structural_parse_coverage"]["identities_with_capture"] == 367
    assert replay["structural_parse_coverage"]["identities_with_structural_parse"] == 367
    assert replay_report["legal_kit"] == {
        "canonical_identity_count": 367,
        "complete_receipt_count": 367,
        "ready": True,
        "identity_or_receipt_drift": False,
    }
    kinds = replay_report["sidekick_replay"]["record_kind_coverage"]
    assert replay_report["sidekick_replay"]["sidekick_identity_denominator"] == 25
    for kind in ("sidekick_auto", "sidekick_charge", "sidekick_aura"):
        assert kinds[kind]["admitted_record_count"] > 0
        assert kinds[kind]["structurally_parsed_record_count"] == kinds[kind]["admitted_record_count"]
        assert kinds[kind]["unresolved_record_count"] == 0


def test_all_fidelity_dimensions_are_explicit_and_default_replay_is_oracle_free(replay_report: dict):
    assert replay_report["fidelity_dimensions"]["dimensions"] == list(FIDELITY_DIMENSIONS)
    assert replay_report["fidelity_dimensions"]["unresolved_state"] == "unknown"
    assert replay_report["fidelity_dimensions"]["inapplicable_state"] == "not_applicable"
    assert replay_report["fidelity_dimensions"]["failed_state"] == "failed"
    assert "oracle_evaluation" not in replay_report
    assert replay_report["authority_boundary"] == {
        "automatic_approval": False,
        "capability_materialization": False,
        "fidelity_passed_only_enters_c2": True,
        "unresolved_semantic_attachment_is_unknown": True,
        "unresolved_source_selection_is_unknown": True,
    }


def test_independent_oracle_reports_separate_counts_and_c2_admission(evaluated_report: dict):
    assert evaluated_report["oracle_evaluation"]["known_regressions"]["generalization_evidence"] is False
    development = evaluated_report["oracle_evaluation"]["development"]
    held_out = evaluated_report["oracle_evaluation"]["held_out"]
    assert development["witness_count"] == 26
    assert held_out["witness_count"] == 21
    assert development["independently_adjudicated_effect_occurrence_count"] > 0
    assert development["independently_adjudicated_dependency_occurrence_count"] > 0
    assert held_out["independently_adjudicated_effect_occurrence_count"] > 0
    assert held_out["independently_adjudicated_dependency_occurrence_count"] > 0
    assert all(
        row["c2_admission"] == ("fully_supported" if row["semantic_fidelity_passed"] else "unknown_non_authoritative")
        for row in development["witnesses"] + held_out["witnesses"]
    )
    assert all(set(row["dimensions"]) == set(FIDELITY_DIMENSIONS) for row in development["witnesses"] + held_out["witnesses"])


def test_known_failure_states_and_darunis_conflict_remain_visible(evaluated_report: dict):
    rows = {row["witness_id"]: row for row in evaluated_report["oracle_evaluation"]["known_regressions"]["witnesses"]}
    assert rows["known-iphi-blood-ritual"]["dimensions"]["child_definition_resolution"]["status"] == "unknown"
    assert rows["known-alma-refraction-counter"]["dimensions"]["parent_child_condition_attachment"]["status"] == "failed"
    assert rows["known-darunis-hunters-fangs-conflict"]["oracle_status"] == "source_conflict"
    assert rows["known-darunis-hunters-fangs-conflict"]["dimensions"]["attack_type"]["status"] == "failed"
    assert rows["known-anabel-prayer-child"]["dimensions"]["child_definition_resolution"]["status"] == "unknown"
    assert all(row["generalization_evidence"] is False for row in rows.values())
