"""Source-pinned regressions promoted from consumed Fresh Test #2."""

from __future__ import annotations

from collections.abc import Mapping
import json

import pytest

from scripts.evaluate_c2_second_fresh_consumed_development_regressions import evaluate, load_pinned_inputs
from src.etl.capability_taxonomy import load_capability_taxonomy
from src.etl.c2_semantic_evaluation import _base_matches, _maximum_one_to_one, _prediction_capability


@pytest.fixture(scope="module")
def evaluation_bundle():
    return evaluate()


def _oracle_atom(oracle: Mapping, witness_id: str, label: str) -> Mapping:
    witness = next(row for row in oracle["witnesses"] if row["witness_id"] == witness_id)
    return next(atom for atom in witness["atoms"] if atom["atomic_capability_id"] == label)


def _prediction(details: Mapping, witness_id: str, label: str) -> Mapping:
    oracle = details["oracle"]
    witness = next(row for row in oracle["witnesses"] if row["witness_id"] == witness_id)
    atom = _oracle_atom(oracle, witness_id, label)
    expected_identity = json.dumps(
        atom["source_anchor"]["identity"], sort_keys=True, separators=(",", ":")
    )
    rows = details["predictions_by_arm"]["fidelity_checked"][witness_id]
    matches = [
        row
        for row in rows
        if row.get("occurrence_kind") == atom["occurrence_kind"]
        and row.get("operation") == atom["operation"]
        and row.get("source_fact_id") == witness["fact_id"]
        and row.get("source_capture_sha256") == witness["source_capture_sha256"]
        and json.dumps(
            (row.get("source_span") or {}).get("source_anchor"),
            sort_keys=True,
            separators=(",", ":"),
        ) == expected_identity
        and _prediction_capability(row) == str(atom["atomic_capability_id"])
    ]
    assert len(matches) == 1, f"{witness_id} {label} did not produce one anchored canonical prediction"
    return matches[0]


def test_promoted_fixture_keeps_all_pins_and_only_consumed_evidence():
    oracle, witnesses, _units, unit_by_witness = load_pinned_inputs()
    assert oracle["promotion"]["status"] == "consumed_development_regression"
    assert oracle["promotion"]["embedded_html"] is False
    assert oracle["promotion"]["source_oracle_sha256"] == (
        "89d932f00c972762668b305ba2f0d61c1851230894d6b377d1d76b5b3c3d2267"
    )
    assert oracle["promotion"]["source_evaluation_report_sha256"] == (
        "5a292625654835252f127253b8b2401840c013ae65a1a5a23e1c7771cf98e8b6"
    )
    assert len(witnesses) == len(unit_by_witness) == 7
    assert all("fidelity_dimensions" not in row for row in oracle["witnesses"])


def test_every_taxonomy_supported_test2_atom_is_recovered(evaluation_bundle):
    _report, details = evaluation_bundle
    taxonomy = load_capability_taxonomy()
    capabilities = set(taxonomy["capabilities"])
    dependencies = set(taxonomy["dependencies"])

    for witness in details["oracle"]["witnesses"]:
        witness_id = witness["witness_id"]
        predictions = [
            row
            for row in details["predictions_by_arm"]["fidelity_checked"][witness_id]
            if row.get("occurrence_kind") in {"effect", "dependency"}
        ]
        atoms = witness["atoms"]
        edges = [[index for index, atom in enumerate(atoms) if _base_matches(row, atom, witness)] for row in predictions]
        label_edges = [
            [
                index
                for index in edge
                if _prediction_capability(predictions[row_index])
                == str(atoms[index].get("atomic_capability_id") or "").casefold()
            ]
            for row_index, edge in enumerate(edges)
        ]
        label_matches = _maximum_one_to_one(label_edges)
        recovered_atoms = set(label_matches.values())

        for atom_index, atom in enumerate(atoms):
            label = str(atom["atomic_capability_id"])
            allowed = capabilities if atom["occurrence_kind"] == "effect" else dependencies
            assert label in allowed, f"non-taxonomy oracle label: {label}"
            assert atom_index in recovered_atoms, f"{witness_id} did not recover supported label {label}"


def test_test2_misses_and_decomposition_failures_are_fixed(evaluation_bundle):
    report, details = evaluation_bundle
    arm = report["metrics"]
    assert arm["canonical_labels"]["true_positive_count"] == 30
    assert arm["canonical_labels"]["false_positive_count"] == 0
    assert arm["canonical_labels"]["false_negative_count"] == 0
    assert arm["dependencies"]["true_positive_count"] == 7
    assert arm["dependencies"]["false_positive_count"] == 0
    assert arm["dependencies"]["false_negative_count"] == 0
    assert arm["effects"]["true_positive_count"] == 23
    assert arm["effects"]["false_negative_count"] == 0

    expected = (
        ("fresh2-benedict-large-slash", "direct_damage"),
        ("fresh2-ewan-as-roaring-bash", "magic_critical_rate_up"),
        ("fresh2-ewan-as-roaring-bash", "element_damage_up"),
        ("fresh2-iridian-heal-arcus-irus", "direct_damage"),
        ("fresh2-iridian-heal-arcus-irus", "multi_hit_action"),
        ("fresh2-iridian-heal-arcus-irus", "requires_zone"),
        ("fresh2-radias-turn-end-buff", "equipped_weapon_damage_up"),
        ("fresh2-radias-turn-end-buff", "requires_recipient_eligibility"),
        ("fresh2-riica-elimination-ray", "grant_link"),
        ("fresh2-riica-elimination-ray", "remove_status_ailment"),
        ("fresh2-riica-elimination-ray", "recover_mp"),
    )
    for witness_id, label in expected:
        _prediction(details, witness_id, label)

    ewan_attack = _prediction(details, "fresh2-ewan-as-roaring-bash", "direct_damage")
    assert ewan_attack["attack_type"] == "stance_dependent:Slash|Pierce|Blunt|Magic; default Blunt"
    assert ewan_attack["formula_metadata"]["attack_type_selection"] == (
        "Damage type is according to active Stance"
    )

    iridian_rows = details["classifier_rows"]["fresh2-iridian-heal-arcus-irus"]
    assert not any(row.get("capability_value") == "deploy_zone" for row in iridian_rows)
    philo_rows = details["classifier_rows"]["fresh2-philo-as-store-power"]
    assert not any(row.get("capability_value") == "direct_damage" for row in philo_rows)
    consumption = [
        row for row in iridian_rows
        if row.get("semantic_role") == "resource_consumption"
        and row.get("source_text") == "Consumes 5 Charge"
    ]
    assert len(consumption) == 1
    assert consumption[0]["semantic_type"] == "resource_consumption"
    assert consumption[0]["dependency_value"] == ""
    assert consumption[0]["occurrence_kind"] == "gap"
    assert consumption[0]["gap_reason"]
    charge_damage = _prediction(details, "fresh2-iridian-heal-arcus-irus", "direct_damage")
    assert charge_damage["resource_metadata"] == {"charge_cost": "5"}


def test_unlabeled_predictions_follow_explicit_source_gaps(evaluation_bundle):
    report, _details = evaluation_bundle
    classification = report["classification"]
    assert classification["unlabeled_outputs_without_an_explicit_gap_anchor"] == []
    explicit_gaps = classification["explicit_unsupported_gap_outputs"]
    assert len(explicit_gaps) == 9
    assert sum(row["source_text"] == "Consumes 5 Charge" for row in explicit_gaps) == 1
    assert len(classification["unresolved_relationships"]) == 0

    relationship_metrics = report["metrics"]["relationship_groups"]
    assert relationship_metrics["expected_groups"] == 7
    assert relationship_metrics["emitted_groups"] == 7
    assert relationship_metrics["exact_correct_groups"] == 7
    assert relationship_metrics["extra_groups"] == 0
    assert relationship_metrics["unresolved_groups"] == 0


def test_philo_state_relationships_keep_their_parent_occurrence_owner(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "fresh2-philo-as-store-power"
    occurrences = details["classifier_rows"][witness_id]
    occurrence_ids = {row["occurrence_id"] for row in occurrences}
    state_power = _prediction(details, witness_id, "power_up")
    assert state_power["trigger"] == "while_state_active"
    relationships = [
        row
        for row in details["relationships"]
        if row["source_fact_id"] == next(
            witness["fact_id"] for witness in details["oracle"]["witnesses"]
            if witness["witness_id"] == witness_id
        )
        and row["operation"] == "activates"
    ]
    assert len(relationships) == 2
    assert all(row["source_occurrence_id"] in occurrence_ids for row in relationships)
    assert all(row["target_id"] for row in relationships)

    witness = next(
        row for row in details["oracle"]["witnesses"]
        if row["witness_id"] == witness_id
    )
    state_activation = next(
        row for row in witness["semantic_relationships"]
        if row.get("operation") == "activates"
        and row.get("target_name") == "Storing Power State"
    )
    assert state_activation["recipient"] == "user"
    assert "condition" not in state_activation
    assert "trigger" not in state_activation

    stack_requirement = next(
        atom for atom in witness["atoms"]
        if atom["atomic_capability_id"] == "requires_stack"
    )
    assert "less than 3" in stack_requirement["fields"]["condition"]


def test_stellar_burst_branch_state_overrides_parent_link_context(evaluation_bundle):
    _report, details = evaluation_bundle
    revive = _prediction(details, "fresh2-riica-elimination-ray", "revive")
    assert revive["state_reference"] == "Stellar Burst"


def test_riica_frontline_gate_is_not_misused_as_child_effect_recipient(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "fresh2-riica-elimination-ray"
    heal = _prediction(details, witness_id, "heal_hp")
    cleanse = _prediction(details, witness_id, "remove_status_ailment")
    assert heal["recipient"] == "unknown"
    assert cleanse["recipient"] == "unknown"


def test_result_text_is_present_but_test2_oracle_uses_canonical_summaries(evaluation_bundle):
    _report, details = evaluation_bundle
    attack = _prediction(details, "fresh2-benedict-large-slash", "direct_damage")
    atom = _oracle_atom(details["oracle"], "fresh2-benedict-large-slash", "direct_damage")
    assert attack["result"] == "Slash attack on a single enemy (L)"
    assert atom["fields"]["result"] == "Slash attack on a single enemy"
