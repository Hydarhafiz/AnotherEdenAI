"""Source-pinned regressions promoted from the consumed Milestone 6 cohort."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.etl.c2_scoped_classification import _effect_semantics
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
    quote = atom["source_anchor"]["quote"].casefold()
    location = atom["source_anchor"]["location"]
    identity = next(row for row in oracle["witnesses"] if row["witness_id"] == witness_id)
    rows = details["predictions_by_arm"]["fidelity_checked"][witness_id]
    matches = [
        row
        for row in rows
        if row.get("occurrence_kind") == atom["occurrence_kind"]
        and row.get("operation") == atom["operation"]
        and row.get("source_fact_id") == identity["fact_id"]
        and row.get("source_capture_sha256") == identity["source_capture_sha256"]
        and row.get("source_span", {}).get("location") == location
        and quote in str(row.get("source_span", {}).get("text") or "").casefold()
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
    assert any(gap.get("former_atom_id") == "E4" for gap in nona["unsupported_mechanics"])
    nona_rows = details["predictions_by_arm"]["fidelity_checked"][nona["witness_id"]]
    assert not any(
        row.get("capability_value") == "apply_kaleido"
        and "change element of type attack buff" in str(row.get("source_text") or "").casefold()
        for row in nona_rows
    )


def test_multihit_label_requires_an_explicit_hit_count_modifier():
    assert ("hit_count_modifier", "multi_hit_action", "hit_count") in _effect_semantics(
        "Increase number of attacks by +3", "enemy"
    )
    assert _effect_semantics("Slash attack on all enemies (XXL x5)", "enemy") == [
        ("damage_event", "direct_damage", "damage")
    ]
    assert _effect_semantics("Water type piercing attack on random enemies x3 (XL)", "enemy") == [
        ("damage_event", "direct_damage", "damage")
    ]


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
