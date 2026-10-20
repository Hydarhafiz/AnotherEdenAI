"""Reusable semantic invariants for role-first C2 segmentation."""

from __future__ import annotations

from src.etl.c2_scoped_classification import _classify_unit
from src.etl.c2_semantic_evaluation import (
    ORACLE_SCHEMA_VERSION,
    adapt_c2_report_to_evaluator,
    evaluate_frozen_cohort,
)
from src.etl.structural_evidence import (
    SourceIdentity,
    StructuralBlock,
    StructuralToken,
    StructuralUnit,
    TraversalLimits,
    source_anchor_for_quote,
)


LIMITS = TraversalLimits(max_depth=3, max_pages_per_root=8)


def _token(text: str, location: str, order: int = 0, *, kind: str = "text", **kwargs) -> StructuralToken:
    return StructuralToken(kind=kind, order=order, text=text, location=location, **kwargs)


def _unit(
    fact_id: str,
    text: str,
    *,
    blocks: list[StructuralBlock] | None = None,
    record_type: str = "active_skill",
) -> StructuralUnit:
    capture = (fact_id.encode("utf-8").hex() * 2)[:64].ljust(64, "0")
    source_url = f"https://example.test/wiki/{fact_id.rsplit(':', 1)[-1]}"
    source = SourceIdentity("character", source_url, capture, "synthetic-c2-role-fixture")
    unit_blocks = blocks or [
        StructuralBlock(
            kind="root",
            order=0,
            ancestry=[],
            location=f"sha256:{capture}/grid[0]/block[0]",
            tokens=[_token(text, f"sha256:{capture}/grid[0]/block[0]/token[0]")],
        )
    ]
    return StructuralUnit(
        unit_id=f"unit:{fact_id}",
        source=source,
        entity_kind="character",
        entity_name="Example",
        record_type="skill",
        title="Role First",
        section="Active Skill",
        source_fact_id=fact_id,
        family_id=f"family:{fact_id}",
        legacy_description=text,
        blocks=unit_blocks,
        definition_page_url=source_url,
    )


def _classify(unit: StructuralUnit, *children: StructuralUnit):
    return _classify_unit(
        {
            "record_id": unit.source_fact_id,
            "record_type": "active_skill",
            "entity_name": unit.entity_name,
            "source_capture_sha256": unit.source.capture_sha256,
            "source_identity_status": "passed",
            "source_record_selection_status": "passed",
            "source_fixture_status": "passed",
            "source_slice_sha256": "a" * 64,
        },
        unit,
        [unit, *children],
        LIMITS,
        arm="structural_only",
        fidelity_passed=False,
    )


def _primary(result):
    return [row for row in result.occurrences if row.occurrence_kind in {"effect", "dependency"}]


def test_two_owned_xn_attacks_get_separate_damage_and_multi_hit_pairs():
    unit = _unit(
        "skill:two-attacks",
        "Fire piercing attack x2 and Fire slash attack x2.",
    )

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]

    assert [row.capability_value for row in effects] == [
        "direct_damage",
        "multi_hit_action",
        "direct_damage",
        "multi_hit_action",
    ]
    assert [row.attack_type for row in effects] == ["Piercing", "Piercing", "Slash", "Slash"]
    assert [row.hit_count for row in effects] == ["2", "2", "2", "2"]
    assert effects[0].source_owner_id == effects[1].source_owner_id
    assert effects[2].source_owner_id == effects[3].source_owner_id
    assert effects[0].source_owner_id != effects[2].source_owner_id


def test_n_times_is_an_explicit_hit_count_but_potency_multiplier_is_not():
    repeated = _unit("skill:three-times", "Attacks one enemy 3 times.")
    potency = _unit("skill:potency-only", "Attacks all enemies x1.5.")

    repeated_effects = [row for row in _classify(repeated).occurrences if row.occurrence_kind == "effect"]
    potency_effects = [row for row in _classify(potency).occurrences if row.occurrence_kind == "effect"]

    assert [row.capability_value for row in repeated_effects] == ["direct_damage", "multi_hit_action"]
    assert [row.hit_count for row in repeated_effects] == ["3", "3"]
    assert [row.capability_value for row in potency_effects] == ["direct_damage"]
    assert potency_effects[0].magnitude["unit"] == "multiplier"


def test_conditional_hit_count_updates_one_owned_multi_hit_occurrence():
    unit = _unit(
        "skill:conditional-hits",
        "Attacks one enemy x2; on the second use, 3 hits; on the third or later use, 4 hits.",
    )

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]
    multi_hits = [row for row in effects if row.capability_value == "multi_hit_action"]

    assert len([row for row in effects if row.capability_value == "direct_damage"]) == 1
    assert len(multi_hits) == 1
    assert multi_hits[0].hit_count == "2"
    assert multi_hits[0].result_modifiers["conditional_hit_counts"] == {
        "second_use": "3",
        "third_or_later_use": "4",
    }


def test_formula_and_sequence_segments_cannot_create_parent_damage():
    formula = _unit("skill:formula-note", "Damage = attack x3 based on Light and Shadow.")
    sequence = _unit("skill:sequence-note", "Sequence: repeat the attack x2 on each action.")

    for unit in (formula, sequence):
        effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]
        assert not any(row.capability_value in {"direct_damage", "multi_hit_action"} for row in effects)


def test_resource_consumption_and_creation_do_not_become_stack_requirements():
    unit = _unit(
        "skill:resource-directions",
        "Consumes 1 Divine Wolf, gains 1 Charge, and stacks 5 Pendulum.",
    )

    result = _classify(unit)
    dependencies = [row for row in result.occurrences if row.occurrence_kind == "dependency"]
    resources = [
        row for row in result.occurrences
        if row.occurrence_kind == "gap"
        and row.semantic_type in {"resource_consumption", "resource_grant", "state_creation"}
    ]

    assert not any(row.dependency_value == "requires_stack" for row in dependencies)
    assert {row.semantic_type for row in resources} == {
        "resource_consumption", "resource_grant", "state_creation"
    }
    assert all(row.occurrence_kind == "gap" and row.gap_reason for row in resources)


def test_conditional_potency_modifies_the_owned_attack_without_a_second_effect():
    unit = _unit(
        "skill:conditional-potency",
        "Deals damage to one enemy. Damage is increased by 50% when in Another Zone.",
    )

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]

    assert [row.capability_value for row in effects] == ["direct_damage"]
    assert effects[0].result_modifiers["conditional_potency"] == [
        {
            "source_text": "Damage is increased by 50% when in Another Zone",
            "condition": "when in Another Zone",
            "source_anchor_id": effects[0].result_modifiers["conditional_potency"][0]["source_anchor_id"],
            "magnitude": {"value": "50", "unit": "percent", "raw": "50%"},
        }
    ]


def test_unknown_effect_stays_an_explicit_gap_beside_a_supported_attack():
    unit = _unit(
        "skill:unknown-neighbor",
        "Fire attack on one enemy. Inflict Unlisted Omen on the target.",
    )

    occurrences = _classify(unit).occurrences
    effects = [row for row in occurrences if row.occurrence_kind == "effect"]
    attack = next(row for row in effects if row.capability_value == "direct_damage")
    unsupported = next(row for row in occurrences if row.occurrence_kind == "gap")

    assert attack.capability_value == "direct_damage"
    assert unsupported.capability_value == ""
    assert unsupported.gap_reason
    assert unsupported.semantic_type == "status_or_effect_application"
    assert attack.source_owner_id != unsupported.source_owner_id


def test_child_invocation_does_not_import_child_attacks_into_the_parent():
    parent_fact = "skill:parent-invocation"
    child_fact = "skill:child-attack"
    parent_capture = (parent_fact.encode("utf-8").hex() * 2)[:64].ljust(64, "0")
    parent_location = f"sha256:{parent_capture}/grid[0]/block[0]"
    parent_url = "https://example.test/wiki/Parent"
    child_url = "https://example.test/wiki/Child"
    parent = _unit(
        parent_fact,
        "Activates Child Skill",
        blocks=[
            StructuralBlock(
                kind="root",
                order=0,
                ancestry=[],
                location=parent_location,
                tokens=[
                    _token("Activates", f"{parent_location}/token[0]", order=0),
                    StructuralToken(
                        kind="reference",
                        order=1,
                        text="Child Skill",
                        location=f"{parent_location}/token[1]",
                        href=child_url,
                        canonical_page_url=child_url,
                    ),
                ],
            )
        ],
    )
    parent.source = SourceIdentity("character", parent_url, parent_capture, "synthetic-parent")
    parent.definition_page_url = parent_url
    child = _unit(child_fact, "Fire attack on one enemy x2")
    child.source = SourceIdentity(
        "character", child_url, child.source.capture_sha256, "synthetic-child"
    )
    child.definition_page_url = child_url
    child.title = "Child Skill"

    result = _classify(parent, child)

    assert not any(
        row.capability_value in {"direct_damage", "multi_hit_action"}
        for row in result.occurrences
    )
    assert any(
        edge.source_fact_id == parent_fact and edge.target_id == child_fact
        for edge in result.relationships
    )


def test_nested_branch_inherits_both_conditions_and_sibling_stays_unconditional():
    capture = "b" * 64
    location = f"sha256:{capture}/grid[0]"
    blocks = [
        StructuralBlock(
            "list_item", 0, ["list[0]"], f"{location}/block[0]",
            [_token("If user possesses Divine Wolf", f"{location}/block[0]/token[0]"),],
        ),
        StructuralBlock(
            "list_item", 1, ["list[0]", "list[0]"], f"{location}/block[1]",
            [_token("If target has 20 Miasmic Corrosion", f"{location}/block[1]/token[0]"),],
        ),
        StructuralBlock(
            "list_item", 2, ["list[0]", "list[0]", "list[0]"], f"{location}/block[2]",
            [_token("Deals damage to one enemy", f"{location}/block[2]/token[0]"),],
        ),
        StructuralBlock(
            "list_item", 3, ["list[1]"], f"{location}/block[3]",
            [_token("Restores HP to all allies", f"{location}/block[3]/token[0]"),],
        ),
    ]
    unit = _unit("skill:nested-conditions", "", blocks=blocks)
    unit.source = SourceIdentity("character", unit.source.source_url, capture, "synthetic-c2-role-fixture")

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]
    damage = next(row for row in effects if row.capability_value == "direct_damage")
    recovery = next(row for row in effects if row.capability_value == "heal_hp")

    assert "Divine Wolf" in damage.condition
    assert "20 Miasmic Corrosion" in damage.condition
    assert recovery.condition == ""
    assert {row.dependency_value for row in _classify(unit).occurrences if row.occurrence_kind == "dependency"} == {
        "requires_stack"
    }
    stack_requirements = [
        row for row in _classify(unit).occurrences
        if row.occurrence_kind == "dependency" and row.dependency_value == "requires_stack"
    ]
    assert any(row.magnitude == {
        "comparison": ">=", "resource": "Miasmic Corrosion", "value": 20
    } for row in stack_requirements)


def test_semicolon_condition_chain_keeps_every_gate_on_party_composition():
    unit = _unit(
        "skill:party-composition-condition-chain",
        "When Minalca is at front; only if Outrage is still usable: "
        "Stack one Stigmata on Minalca.",
    )

    composition = next(
        row
        for row in _classify(unit).occurrences
        if row.occurrence_kind == "dependency"
        and row.dependency_value == "party_composition"
    )

    assert composition.condition == (
        "When Minalca is at front; only if Outrage is still usable"
    )
    assert composition.source_span.text == "When Minalca is at front"


def test_owned_mp_restore_does_not_inherit_sibling_consumption_fields():
    unit = _unit(
        "skill:aldos-mp-fields",
        "Restore MP +30. Reduce MP consumption by 35% for 3 turns.",
    )

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]
    restore = next(row for row in effects if row.semantic_type == "mp_recovery")

    assert restore.magnitude["value"] == "30"
    assert "duration_turns" not in restore.duration_activation
    assert all(row.source_owner_id != restore.source_owner_id for row in effects if row is not restore)


def test_end_of_turn_is_timing_and_not_a_dependency():
    unit = _unit("skill:end-turn", "At End of Turn, restores HP to all allies.")

    result = _classify(unit)
    effects = [row for row in result.occurrences if row.occurrence_kind == "effect"]
    dependencies = [row for row in result.occurrences if row.occurrence_kind == "dependency"]

    assert len(effects) == 1
    assert effects[0].trigger in {"turn_end", "end_of_turn"}
    assert not any(row.dependency_value in {"end_of_turn", "requires_stack"} for row in dependencies)


def test_icon_and_link_tokens_are_in_the_exact_anchor_consumed_by_the_evaluator():
    fact_id = "skill:icon-link-attack"
    capture = (fact_id.encode("utf-8").hex() * 2)[:64].ljust(64, "0")
    location = f"sha256:{capture}/grid[0]/block[0]"
    block = StructuralBlock(
        kind="root",
        order=0,
        ancestry=[],
        location=location,
        tokens=[
            _token("Fire type attack on ", f"{location}/token[0]", order=0),
            _token(
                "enemy", f"{location}/token[1]", order=1,
                kind="icon", icon_identity="Enemy Icon.png",
            ),
            StructuralToken(
                kind="reference",
                order=2,
                text="all enemies",
                location=f"{location}/token[2]",
                href="https://example.test/wiki/Enemies",
                canonical_page_url="https://example.test/wiki/Enemies",
            ),
            _token("x2", f"{location}/token[3]", order=3),
        ],
    )
    unit = _unit(fact_id, "", blocks=[block])
    result = _classify(unit)
    occurrences = [row for row in result.occurrences if row.occurrence_kind == "effect"]
    identities = [row.source_span.source_anchor.as_dict() for row in occurrences]
    assert len(identities) == 2
    assert identities[0] == identities[1]
    assert {token["kind"] for token in identities[0]["token_identities"]} == {
        "text", "icon", "reference"
    }

    witness = {
        "witness_id": "icon-link-witness",
        "fact_id": fact_id,
        "source_capture_sha256": capture,
    }
    comparison = {
        "arms": {
            "structural_only": {
                "occurrences": [row.as_dict() for row in occurrences],
                "relationships": [],
            }
        }
    }
    adapted = adapt_c2_report_to_evaluator(comparison, [witness])
    expected_anchor = source_anchor_for_quote(
        source_fact_id=fact_id,
        source_capture_sha256=capture,
        block=block,
        quote="Fire type attack on enemy all enemies x2",
    )
    atoms = [
        {
            "occurrence_kind": "effect",
            "atomic_capability_id": capability,
            "operation": "damage",
            "source_anchor": {
                "location": block.location,
                "quote": "Fire type attack on enemy all enemies x2",
                "identity": expected_anchor.as_dict(),
            },
        }
        for capability in ("direct_damage", "multi_hit_action")
    ]
    oracle = {
        "schema_version": ORACLE_SCHEMA_VERSION,
        "cohort": "synthetic_anchor_invariant",
        "witnesses": [{**witness, "atoms": atoms}],
    }
    report = evaluate_frozen_cohort(adapted["predictions_by_arm"], oracle, [witness])

    assert report["arms"]["structural_only"]["capability_label_precision_recall"]["true_positive_count"] == 2


def test_negated_and_explanatory_attack_mentions_do_not_become_damage_results():
    unit = _unit(
        "skill:non-damage-attack-explanations",
        "Cannot deal with enemies' End-of-Turn attack. "
        "The sequence attacks are not basic attack replacements themselves. "
        "The modifier will not increase their damage.",
    )

    result = _classify(unit)

    assert not any(
        row.capability_value == "direct_damage"
        for row in result.occurrences
        if row.occurrence_kind == "effect"
    )


def test_named_state_stat_line_is_a_power_result():
    unit = _unit("skill:named-state-stat-line", "Catwisp : +20 PWR (max stack 3, +60)")

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]

    assert len(effects) == 1
    assert effects[0].capability_value == "power_up"
    assert effects[0].state_reference == "Catwisp"
    assert effects[0].magnitude["value"] == "20"


def test_unlabeled_percent_mp_result_uses_its_party_recipient():
    unit = _unit("skill:unlabeled-mp-result", "20% MP to party and reserve members")

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]

    assert len(effects) == 1
    assert effects[0].capability_value == "recover_mp"
    assert effects[0].recipient == "party"
    assert effects[0].magnitude["value"] == "20"


def test_generic_and_magic_critical_rates_share_only_the_coordinated_magnitude():
    unit = _unit(
        "skill:coordinated-critical-rates",
        "Increase critical rate and magic critical rate +10%, "
        "fire type attack of user +5%, and Max HP +300 per stack (max stack: x10)",
    )

    effects = [row for row in _classify(unit).occurrences if row.occurrence_kind == "effect"]
    critical = [row for row in effects if row.semantic_type == "critical_support"]

    assert [row.capability_value for row in critical] == [
        "physical_critical_rate_up",
        "magic_critical_rate_up",
    ]
    assert all(row.magnitude.get("value") == "10" for row in critical)
    assert len({row.source_owner_id for row in critical}) == 2
    assert all(row.coordinated_result_group_id for row in critical)


def test_attack_anchor_stops_before_its_formula_annotation():
    unit = _unit(
        "skill:attack-with-formula-note",
        "Shade type magic attack on all enemies (XL, increase skill damage 1.5 times, "
        "1.5x of the standard skill multiplier of 150%)",
    )

    attacks = [
        row for row in _classify(unit).occurrences
        if row.occurrence_kind == "effect" and row.capability_value == "direct_damage"
    ]

    assert len(attacks) == 1
    assert attacks[0].source_span.text == "Shade type magic attack on all enemies"
    assert attacks[0].magnitude.get("tier") == "XL"
    assert attacks[0].formula_metadata
