"""Source-pinned regressions promoted from the consumed Milestone 6 cohort."""

from __future__ import annotations

from collections.abc import Mapping
import json

import pytest

from src.etl.c2_scoped_classification import _dependency_values, _effect_semantics, _is_prerequisite
from scripts.evaluate_c2_consumed_development_regressions import evaluate, load_pinned_inputs


@pytest.fixture(scope="module")
def evaluation_bundle():
    return evaluate()


def _oracle_atom(oracle: Mapping, witness_id: str, atom_id: str) -> Mapping:
    witness = next(row for row in oracle["witnesses"] if row["witness_id"] == witness_id)
    return next(atom for atom in witness["atoms"] if atom["atom_id"] == atom_id)


def _prediction(details: Mapping, witness_id: str, atom_id: str) -> Mapping:
    oracle = details["oracle"]
    atom = _oracle_atom(oracle, witness_id, atom_id)
    expected_identity = json.dumps(
        atom["source_anchor"]["identity"], sort_keys=True, separators=(",", ":")
    )
    identity = next(row for row in oracle["witnesses"] if row["witness_id"] == witness_id)
    rows = details["predictions_by_arm"]["fidelity_checked"][witness_id]
    matches = [
        row
        for row in rows
        if row.get("occurrence_kind") == atom["occurrence_kind"]
        and row.get("operation") == atom["operation"]
        and row.get("source_fact_id") == identity["fact_id"]
        and row.get("source_capture_sha256") == identity["source_capture_sha256"]
        and json.dumps(
            (row.get("source_span") or {}).get("source_anchor"),
            sort_keys=True,
            separators=(",", ":"),
        ) == expected_identity
    ]
    capability_key = "dependency_value" if atom["occurrence_kind"] == "dependency" else "capability_value"
    matches = [row for row in matches if row.get(capability_key) == atom["atomic_capability_id"]]
    assert len(matches) == 1, f"{witness_id} {atom_id} did not produce exactly one anchored canonical prediction"
    return matches[0]


def test_promoted_fixture_keeps_the_approved_pins_and_excludes_html():
    oracle, witnesses, _units, unit_by_witness = load_pinned_inputs()
    assert oracle["promotion"]["status"] == "consumed_development_regression"
    assert oracle["promotion"]["embedded_html"] is False
    assert len(witnesses) == 7
    assert len(unit_by_witness) == 7
    assert [row["fact_id"] for row in witnesses] == [row["fact_id"] for row in oracle["witnesses"]]


def test_reproduced_supported_mechanic_misses_are_now_regressions(evaluation_bundle):
    _report, details = evaluation_bundle

    # Type attack buffs retain their element, recipient, and direction.
    aisha = _prediction(details, "m6-heldout-aisha-waters-nocturne", "E2")
    assert (aisha["direction"], aisha["recipient"], aisha["element"]) == ("ally", "party", "Water")

    # A repeated attack is one multi-hit action, regardless of the number of hits.
    otoha = _prediction(details, "m6-heldout-otoha-as-surging-scratch", "E2")
    assert otoha["hit_count"] == "2"
    assert otoha["direction"] == "enemy"
    assert otoha["recipient"] == "all_enemies"

    # Nona's conditional +3 attack count modifies the preceding random-enemy attack.
    nona_hit = _prediction(details, "m6-heldout-nona-as-castigo", "E2")
    assert (nona_hit["direction"], nona_hit["recipient"], nona_hit["element"], nona_hit["attack_type"]) == (
        "enemy", "random_enemies", "Water", "Piercing"
    )

    # Nona's supported buff and Kaleido stay separate; E4 remains metadata only.
    _prediction(details, "m6-heldout-nona-as-castigo", "E3")
    nona_kaleido = _prediction(details, "m6-heldout-nona-as-castigo", "E5")
    assert (nona_kaleido["direction"], nona_kaleido["recipient"]) == ("self", "self")
    nona = next(row for row in details["oracle"]["witnesses"] if row["witness_id"] == "m6-heldout-nona-as-castigo")
    assert any(
        note.get("former_atom_id") == "E4"
        for note in nona["reviewed_unscored_mechanics"]
    )
    nona_rows = details["predictions_by_arm"]["fidelity_checked"][nona["witness_id"]]
    assert not any(
        row.get("capability_value") == "apply_kaleido"
        and "change element of type attack buff" in str(row.get("source_text") or "").casefold()
        for row in nona_rows
    )


def test_otoha_pwr_stack_grants_a_self_power_up(evaluation_bundle):
    _report, details = evaluation_bundle
    power = _prediction(details, "m6-heldout-otoha-as-surging-scratch", "E3")
    assert (power["direction"], power["recipient"]) == ("self", "self")


def test_otoha_catwisp_application_is_expected_and_creation_gap_remains(evaluation_bundle):
    report, details = evaluation_bundle
    witness_id = "m6-heldout-otoha-as-surging-scratch"
    witness = next(row for row in details["oracle"]["witnesses"] if row["witness_id"] == witness_id)
    assert witness["entity_name"] == "Otoha (Another Style)"
    assert witness["fact_id"] == "skill:0f340a5404f853049fd9"

    relationships = witness["semantic_relationships"]
    assert len(relationships) == 1
    relation = relationships[0]
    assert relation["operation"] == "applies_state"
    assert relation["recipient"] == "user"
    assert relation["target_kind"] == "named_state"
    assert relation["target_name"] == "Catwisp"
    assert relation["trigger"] == "own_action"
    assert "condition" not in relation
    assert "target_id" not in relation
    assert "targets" not in relation
    assert relation["source_anchor"]["quote"] == "Stack 1 Catwisp on user"
    assert relation["source_anchor"]["location"].endswith("/grid[8]/block[2]")
    assert relation["source_anchor"]["identity"]["source_fact_id"] == witness["fact_id"]
    assert (
        relation["source_anchor"]["identity"]["source_capture_sha256"]
        == witness["source_capture_sha256"]
    )
    assert (
        relation["source_anchor"]["identity"]["anchor_id"]
        == "src:fed9f28c11918ea3f4dfdf5963404ac7"
    )

    gaps = witness["unsupported_gaps"]
    catwisp_gap = next(gap for gap in gaps if gap["gap_id"] == "gap-otoha-catwisp-state-creation")
    assert catwisp_gap["gap_type"] == "unsupported_state_creation"
    assert catwisp_gap["mechanic"] == "catwisp_stack_creation"
    assert catwisp_gap["source_anchor"]["identity"] == relation["source_anchor"]["identity"]

    assert report["relationships"]["expected_count"] == 2
    assert report["relationships"]["groups"]["expected_groups"] == 2


def test_otoha_continuation_cost_and_interruption_stay_sequence_metadata(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-otoha-as-surging-scratch"
    rows = details["predictions_by_arm"]["fidelity_checked"][witness_id]

    assert not any(
        row["occurrence_kind"] == "effect"
        and "does not consume mp" in str(row.get("source_span", {}).get("text") or "").casefold()
        for row in rows
    )
    assert not any(
        row["occurrence_kind"] == "dependency"
        and row["dependency_value"] == "requires_status"
        and "interrupted by status effect" in str(row.get("source_span", {}).get("text") or "").casefold()
        for row in rows
    )
    assert not any(
        row["occurrence_kind"] == "state"
        and row["state_reference"].casefold() == "status"
        and "interrupted by status effect" in str(row.get("source_span", {}).get("text") or "").casefold()
        for row in rows
    )

    action = _prediction(details, witness_id, "E1")
    assert action["sequence_metadata"] == {
        "mode": "automatic_continuation",
        "action_count": "3",
        "manual_activation_mp_cost": "normal_skill_cost_applies",
        "automatic_continuation_mp_cost": "no_additional_mp",
        "interruption": "unless interrupted by status effect",
    }
    assert not any(
        row["occurrence_kind"] == "effect"
        and row["capability_value"] == "multi_hit_action"
        and "increase skill multiplier and number of hits based" in str(row.get("source_span", {}).get("text") or "").casefold()
        for row in rows
    )


def test_harle_skill_multiplier_explanations_attach_to_direct_damage(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-harle-lunairetic"
    damage = _prediction(details, witness_id, "E1")
    assert damage["state_reference"] == "Power Levels"
    assert "1.5x of the standard skill multiplier" in damage["formula_metadata"]["skill_damage_multiplier"]
    assert "Power Levels" in damage["formula_metadata"]["stack_scaling"]

    rows = details["predictions_by_arm"]["fidelity_checked"][witness_id]
    assert not any(
        row["occurrence_kind"] == "effect"
        and row["operation"] == "increase"
        and (
            "increase skill damage" in str(row.get("source_span", {}).get("text") or "").casefold()
            or "multiplier increases based on number" in str(row.get("source_span", {}).get("text") or "").casefold()
        )
        for row in rows
    )


def test_passive_zone_timing_and_condition_apply_to_each_child_effect(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-claude-es-another-zone-heal"
    for atom_id in ("E1", "E2"):
        effect = _prediction(details, witness_id, atom_id)
        assert effect["condition"] == "When in Another Zone"
        assert effect["trigger"] == "turn_end"
    dependency = _prediction(details, witness_id, "D1")
    assert dependency["dependency_value"] == "requires_zone"
    assert dependency["condition"] == "When in Another Zone"


def test_paired_resistance_properties_share_the_explicit_magnitude(evaluation_bundle):
    _report, details = evaluation_bundle
    physical = _prediction(details, "m6-heldout-jilya-invasion-glow", "E2")
    assert (physical["direction"], physical["recipient"]) == ("enemy", "all_enemies")
    assert "-10%" in physical["result"]


def test_dependency_conditions_keep_source_case_and_threshold_sign(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-jilya-invasion-glow"
    charge = _prediction(details, witness_id, "D2")
    frontline = _prediction(details, witness_id, "D3")
    assert charge["condition"] == "When Charge is 5+"
    assert frontline["condition"] == "When Nilya is on the frontline"


def test_compound_dependency_atoms_keep_distinct_source_spans(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-jilya-invasion-glow"
    charge = _prediction(details, witness_id, "D2")
    frontline = _prediction(details, witness_id, "D3")
    assert charge["source_span"]["text"] == "Charge is 5+"
    assert frontline["source_span"]["text"] == "Nilya is on the frontline"


def test_named_state_and_resource_references_keep_the_source_name(evaluation_bundle):
    _report, details = evaluation_bundle
    expected = (
        ("m6-heldout-otoha-as-surging-scratch", "E3", "Catwisp"),
        ("m6-heldout-nona-as-castigo", "E2", "Devotion"),
        ("m6-heldout-nona-as-castigo", "D1", "Devotion"),
        ("m6-heldout-nona-as-castigo", "D2", "Devotion"),
        ("m6-heldout-nona-as-castigo", "E5", "Kaleido"),
        ("m6-heldout-claude-es-another-zone-heal", "D1", "Another Zone"),
        ("m6-heldout-jilya-invasion-glow", "D1", "Crystalline Stance"),
        ("m6-heldout-jilya-invasion-glow", "D2", "Charge"),
        ("m6-heldout-harle-lunairetic", "E1", "Power Levels"),
        ("m6-heldout-melissa-hornet-hail-enhanced", "E2", "Elemental Break"),
        ("m6-heldout-melissa-hornet-hail-enhanced", "D1", "Stellar Awakening"),
    )
    for witness_id, atom_id, state_name in expected:
        assert _prediction(details, witness_id, atom_id)["state_reference"] == state_name


def test_untyped_critical_rate_remains_an_unlabeled_unsupported_gap(evaluation_bundle):
    _report, details = evaluation_bundle
    rows = details["classifier_rows"]["m6-heldout-nona-as-castigo"]
    critical_rate = [
        row for row in rows
        if "critical rate of all party members +100%" in str(row.get("source_text") or "").casefold()
    ]
    assert len(critical_rate) == 1
    assert critical_rate[0]["semantic_type"] == "critical_support"
    assert critical_rate[0]["capability_value"] == ""


def test_skill_use_and_prerequisite_fields_are_attached_without_auto_gap_leakage(evaluation_bundle):
    _report, details = evaluation_bundle
    for witness_id, atom_ids in (
        ("m6-heldout-aisha-waters-nocturne", ("E1", "E2")),
        ("m6-heldout-nona-as-castigo", ("E1", "E2", "E3", "E5")),
        ("m6-heldout-harle-lunairetic", ("E1",)),
        ("m6-heldout-melissa-hornet-hail-enhanced", ("E1", "E2")),
    ):
        for atom_id in atom_ids:
            assert _prediction(details, witness_id, atom_id)["trigger"] == "on_skill_use"

    for witness_id, atom_ids in (
        ("m6-heldout-otoha-as-surging-scratch", ("E1", "E2")),
        ("m6-heldout-jilya-invasion-glow", ("E1", "E2", "E3")),
    ):
        for atom_id in atom_ids:
            assert _prediction(details, witness_id, atom_id)["trigger"] == ""

    melissa_id = "m6-heldout-melissa-hornet-hail-enhanced"
    for atom_id in ("E1", "E2"):
        effect = _prediction(details, melissa_id, atom_id)
        assert effect["condition"] == "Skill requires Stellar Awakening"
    prerequisite = _prediction(details, melissa_id, "D1")
    assert (prerequisite["recipient"], prerequisite["direction"]) == ("self", "self")


def test_multihit_label_requires_an_explicit_hit_count_modifier():
    assert ("hit_count_modifier", "multi_hit_action", "hit_count") in _effect_semantics(
        "Increase number of attacks by +3", "enemy"
    )
    assert _effect_semantics("Slash attack on all enemies (XXL x5)", "enemy") == [
        ("damage_event", "direct_damage", "damage"),
        ("multi_hit_action", "multi_hit_action", "hit_count"),
    ]
    assert _effect_semantics("Water type piercing attack on random enemies x3 (XL)", "enemy") == [
        ("damage_event", "direct_damage", "damage"),
        ("multi_hit_action", "multi_hit_action", "hit_count"),
    ]


def test_resource_cost_and_interruption_language_stay_out_of_capability_labels():
    assert _effect_semantics(
        "Skill automatically used for 3 actions (does not consume MP)", "unknown"
    ) == []
    assert _effect_semantics(
        "Earth type Slash attack on all enemies (does not consume MP)", "enemy"
    ) == [("damage_event", "direct_damage", "damage")]
    assert not _is_prerequisite("unless interrupted by status effect")
    assert _dependency_values("unless interrupted by status effect") == []


def test_party_and_stack_dependencies_remain_independent_and_branch_scoped(evaluation_bundle):
    _report, details = evaluation_bundle
    nona_id = "m6-heldout-nona-as-castigo"
    jilya_id = "m6-heldout-jilya-invasion-glow"
    _prediction(details, nona_id, "D1")
    nona_stack = _prediction(details, nona_id, "D2")
    assert nona_stack["dependency_value"] == "requires_stack"
    _prediction(details, jilya_id, "D1")
    jilya_stack = _prediction(details, jilya_id, "D2")
    jilya_party = _prediction(details, jilya_id, "D3")
    assert jilya_stack["dependency_value"] == "requires_stack"
    assert jilya_party["dependency_value"] == "party_composition"

    condition = _oracle_atom(details["oracle"], nona_id, "D1")["fields"]["condition"]["value"].casefold()
    assert all(condition in str(row.get("condition") or "").casefold() for row in (
        _prediction(details, nona_id, "E2"),
        _prediction(details, nona_id, "E5"),
    ))
    assert not _prediction(details, nona_id, "E3")["condition"]


def test_melissa_stellar_burst_replacement_resolves_to_matching_child(evaluation_bundle):
    _report, details = evaluation_bundle
    witness_id = "m6-heldout-melissa-hornet-hail-enhanced"
    edge = _prediction(details, witness_id, "E3")["relationships"]
    assert len(edge) == 1
    relationship = edge[0]
    assert relationship["target_kind"] == "source_fact"
    assert relationship["target_id"] == "skill:106444a0b9cd8608139e"
    assert relationship["operation"] == "replaces"
    assert relationship["timing"] == "on_stellar_burst"
    assert relationship["resolution_status"] == "resolved"
    assert relationship["source_fact_id"] == "skill:6932bc4961a6857153f3"
    assert all(
        row["source_fact_id"] == "skill:6932bc4961a6857153f3"
        for row in details["predictions_by_arm"]["fidelity_checked"][witness_id]
    )


def test_cohort_metrics_improve_without_scoring_metadata_gaps_as_new_labels(evaluation_bundle):
    report, _details = evaluation_bundle
    effects = report["metrics"]["effects"]
    dependencies = report["metrics"]["dependencies"]
    labels = report["metrics"]["canonical_labels"]
    assert effects["true_positive_count"] >= 16
    assert effects["false_positive_count"] <= 12
    assert effects["false_negative_count"] <= 2
    assert dependencies["true_positive_count"] >= 6
    assert dependencies["false_negative_count"] <= 1
    assert labels["true_positive_count"] >= 20
    assert report["relationships"]["unresolved_count"] < 12
