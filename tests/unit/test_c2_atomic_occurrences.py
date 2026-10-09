"""Synthetic development regressions for atomic C2 occurrence handling."""

from src.etl.c2_scoped_classification import _classify_unit, _compatibility_mapping
from src.etl.shared_mechanics import (
    MechanicAlias,
    MechanicSourceAnchor,
    SharedMechanicEntry,
    SharedMechanicRegistry,
)
from src.etl.structural_evidence import (
    SourceIdentity,
    StructuralBlock,
    StructuralToken,
    StructuralUnit,
    TraversalLimits,
)
from src.workflow.role_scoring import _proven_capabilities


LIMITS = TraversalLimits(max_depth=3, max_pages_per_root=8, max_frontier_per_root=64)


def _registry(*entries: SharedMechanicEntry) -> SharedMechanicRegistry:
    return SharedMechanicRegistry(entries, version="synthetic-c2-r4")


def _unit(
    fact_id: str,
    title: str,
    source_url: str,
    tokens: list[StructuralToken],
    *,
    entity_name: str = "Example",
    entity_kind: str = "character",
    blocks: list[StructuralBlock] | None = None,
) -> StructuralUnit:
    source = SourceIdentity(
        source_kind=entity_kind,
        source_url=source_url,
        capture_sha256=(fact_id.encode("utf-8").hex() * 2)[:64].ljust(64, "0"),
        capture_path="synthetic-development-input",
    )
    unit_blocks = blocks or [
        StructuralBlock(
            kind="effect",
            order=0,
            ancestry=["skill"],
            location=f"{source_url}/block[0]",
            tokens=tokens,
        )
    ]
    return StructuralUnit(
        unit_id=f"unit:{fact_id}",
        source=source,
        entity_kind=entity_kind,
        entity_name=entity_name,
        record_type="skill",
        title=title,
        section="Active Skill",
        source_fact_id=fact_id,
        family_id=f"family:{fact_id}",
        legacy_description=" ".join(token.text for token in tokens),
        blocks=unit_blocks,
        definition_page_url=source_url,
    )


def _text_token(text: str, location: str, order: int = 0) -> StructuralToken:
    return StructuralToken(kind="text", order=order, text=text, location=location)


def _reference_token(text: str, url: str, location: str, order: int) -> StructuralToken:
    return StructuralToken(
        kind="reference",
        order=order,
        text=text,
        location=location,
        href=url,
        canonical_page_url=url,
    )


def _classify(unit: StructuralUnit, *others: StructuralUnit, registry: SharedMechanicRegistry | None = None):
    witness = {
        "record_id": unit.source_fact_id,
        "record_type": "skill",
        "entity_name": unit.entity_name,
        "source_capture_sha256": unit.source.capture_sha256,
        "source_identity_status": "passed",
        "source_record_selection_status": "passed",
        "source_fixture_status": "passed",
        "source_slice_sha256": "a" * 64,
    }
    return _classify_unit(
        witness,
        unit,
        [unit, *others],
        LIMITS,
        arm="structural_only",
        fidelity_passed=False,
        mechanic_registry=registry or _registry(),
    )


def _effects(result):
    return [row for row in result.occurrences if row.occurrence_kind == "effect"]


def test_compound_effects_keep_magnitude_duration_probability_and_hits_local():
    text = (
        "If Another Zone is active, attacks all enemies with water magic damage "
        "(XXL x5), inflicts Poison (5 turns) at 50% chance, then restores 300 MP "
        "to all allies for 3 turns."
    )
    unit = _unit(
        "skill:example:compound",
        "Compound",
        "https://example.test/wiki/Compound",
        [_text_token(text, "sha256:compound/block[0]/text[0])")],
    )

    effects = _effects(_classify(unit))

    assert len(effects) == 3
    attack, poison, mp_recovery = effects
    assert attack.capability_value == "direct_damage"
    assert attack.hit_count == "5"
    assert attack.magnitude == {}
    assert attack.recipient == "all_enemies"
    assert attack.condition == "If Another Zone is active"
    assert attack.state_reference == "Another Zone"
    assert attack.element == "Water"
    assert attack.attack_type == "Magic"
    assert poison.probability == {"value": "50", "unit": "percent", "raw": "50% chance"}
    assert poison.magnitude == {}
    assert poison.duration_activation["duration_turns"] == "5"
    assert poison.condition == "If Another Zone is active"
    assert mp_recovery.capability_value == "recover_mp"
    assert mp_recovery.recipient == "party"
    assert mp_recovery.duration_activation["duration_turns"] == "3"
    assert mp_recovery.condition == "If Another Zone is active"
    assert all(row.authority == "automatic_candidate" for row in effects)


def test_potency_multiplier_is_not_mistaken_for_attack_hit_count():
    unit = _unit(
        "skill:example:potency",
        "Potency",
        "https://example.test/wiki/Potency",
        [_text_token("Attacks all enemies x1.5", "sha256:potency/block[0]/text[0]")],
    )

    damage = _effects(_classify(unit))[0]

    assert damage.capability_value == "direct_damage"
    assert damage.hit_count == ""
    assert damage.magnitude == {"value": "1.5", "unit": "multiplier", "raw": "x1.5"}


def test_conditions_and_fields_do_not_bleed_between_independent_actions():
    text = (
        "Attacks all enemies for 2 turns if Lunatic is active, then heals one ally "
        "for 3 turns at 40% chance."
    )
    unit = _unit(
        "skill:example:condition-scope",
        "Condition Scope",
        "https://example.test/wiki/Condition_Scope",
        [_text_token(text, "sha256:condition/block[0]/text[0]")],
    )

    attack, healing = _effects(_classify(unit))

    assert attack.capability_value == "direct_damage"
    assert attack.condition == "if Lunatic is active"
    assert attack.duration_activation["duration_turns"] == "2"
    assert healing.capability_value == "heal_hp"
    assert healing.condition == ""
    assert healing.duration_activation["duration_turns"] == "3"
    assert healing.probability["value"] == "40"


def test_ally_damage_and_unsupported_maximum_stats_never_become_boss_offense():
    text = "Deals damage to party members and raises own maximum HP by 20%."
    unit = _unit(
        "skill:example:unsupported-stats",
        "Unsupported Stats",
        "https://example.test/wiki/Unsupported_Stats",
        [_text_token(text, "sha256:stats/block[0]/text[0]")],
    )

    effects = _effects(_classify(unit))
    ally_damage, maximum_hp = effects

    assert ally_damage.semantic_type == "damage_event"
    assert ally_damage.direction == "ally"
    assert ally_damage.capability_value == ""
    assert maximum_hp.semantic_type == "stat_increase"
    assert maximum_hp.semantic_subject == "maximum_hp"
    assert maximum_hp.capability_value == ""
    assert maximum_hp.capability_gap is True
    assert all(not _proven_capabilities(row.as_dict()) for row in effects)
    assert all("placement" not in row.as_dict() for row in effects)
    assert all("progression_unlock" not in row.as_dict() for row in effects)


def test_buffs_recovery_cleansing_resources_and_hit_count_stay_separate():
    text = (
        "Raises the Power and Intelligence of all allies by 30% for 3 turns; "
        "restores HP to one ally; revives one ally; removes status ailments from "
        "the party; consumes 2 Stacks and grants 1 Charge; increases skill hit "
        "count by 2; deals damage based on own maximum HP to all enemies."
    )
    unit = _unit(
        "skill:example:effect-families",
        "Effect Families",
        "https://example.test/wiki/Effect_Families",
        [_text_token(text, "sha256:families/block[0]/text[0]")],
    )

    effects = _effects(_classify(unit))

    buffs = [row for row in effects if row.semantic_type == "stat_increase"]
    assert {row.semantic_subject for row in buffs} == {"power", "intelligence"}
    assert {row.capability_value for row in buffs} == {"power_up", "intelligence_up"}
    assert all(row.magnitude == {"value": "30", "unit": "percent", "raw": "30%"} for row in buffs)
    assert all(row.duration_activation["duration_turns"] == "3" for row in buffs)

    recovery = next(row for row in effects if row.semantic_type == "hp_recovery")
    revival = next(row for row in effects if row.semantic_type == "revive")
    cleanse = next(row for row in effects if row.semantic_type == "status_cleansing")
    assert recovery.capability_value == "heal_hp" and recovery.recipient == "ally"
    assert revival.capability_value == "revive" and revival.recipient == "ally"
    assert cleanse.capability_value == "remove_status_ailment" and cleanse.recipient == "party"

    resource_effects = [row for row in effects if row.semantic_type.startswith("resource_")]
    assert {row.semantic_type for row in resource_effects} == {"resource_consumption", "resource_grant"}
    assert not any(row.capability_value for row in resource_effects)
    hit_count_buff = next(row for row in effects if row.semantic_type == "hit_count_modifier")
    assert hit_count_buff.capability_value == ""
    assert hit_count_buff.hit_count == ""
    assert hit_count_buff.magnitude == {"value": "2", "unit": "count", "raw": "skill hit count by 2"}

    damage = next(row for row in effects if row.semantic_type == "damage_event")
    assert damage.capability_value == "direct_damage"
    assert damage.formula_metadata == {"raw": "based on own maximum HP to all enemies"}
    result = _classify(unit)
    assert not any(row.occurrence_kind == "dependency" for row in result.occurrences if "based on" in row.source_text)


def test_review_mapping_requires_recheck_after_atomic_semantics_change_without_fanout():
    legacy = {
        "occurrence_id": "legacy:one",
        "occurrence_kind": "effect",
        "source_fact_id": "skill:example:reviewed",
        "source_text": "Attacks all enemies",
        "actor": "Example",
        "direction": "enemy",
        "recipient": "all_enemies",
        "recipient_name": "",
        "target_cardinality": "multiple",
        "condition": "",
        "trigger": "",
        "result": "Attacks all enemies",
        "magnitude": {},
        "probability": {},
        "duration_activation": {},
        "element": "",
        "attack_type": "",
        "state_reference": "",
        "capability_value": "direct_damage",
        "dependency_value": "",
        "semantic_type": "",
        "semantic_subject": "",
        "capability_gap": False,
        "hit_count": "",
        "formula_metadata": {},
        "action_timing": "",
    }
    identical = {**legacy, "occurrence_id": "current:one"}
    changed = {**identical, "occurrence_id": "current:two", "hit_count": "5"}
    split = {**identical, "occurrence_id": "current:three"}

    carried = _compatibility_mapping([legacy], [identical])
    changed_mapping = _compatibility_mapping([legacy], [changed])
    split_mapping = _compatibility_mapping([legacy], [identical, split])

    assert carried["mappings"][0]["status"] == "carried_forward"
    assert changed_mapping["mappings"][0]["status"] == "review_required"
    assert changed_mapping["mappings"][0]["candidate_occurrence_ids"] == []
    assert split_mapping["mappings"][0]["status"] == "split_requires_review"
    assert split_mapping["mappings"][0]["candidate_occurrence_ids"] == ["current:one", "current:three"]
    assert split_mapping["silent_fanout"] is False


def test_resolved_child_edges_keep_local_condition_timing_and_source_ownership():
    parent_url = "https://example.test/wiki/Parent"
    child_url = "https://example.test/wiki/Child"
    block_location = "sha256:parent/block[0]"
    tokens = [
        _text_token("If Another Zone is active, replaces the normal action with", f"{block_location}/text[0]", 0),
        _reference_token("Child Skill", child_url, f"{block_location}/link[1]", 1),
        _text_token("at end of turn", f"{block_location}/text[2]", 2),
    ]
    parent = _unit("skill:example:parent", "Parent", parent_url, tokens)
    child = _unit(
        "skill:example:child",
        "Child Skill",
        child_url,
        [],
        blocks=[],
    )

    result = _classify(parent, child)
    edge = next(row for row in result.relationships if row.target_id == child.source_fact_id)

    assert edge.source_fact_id == parent.source_fact_id
    assert edge.source_owner == parent.entity_name
    assert edge.target_kind == "source_fact"
    assert edge.operation == "replaces"
    assert edge.condition == "If Another Zone is active"
    assert edge.timing == "turn_end"
    assert edge.resolution_status == "resolved"
    assert edge.source_occurrence_id
    assert edge.authority == "automatic_candidate"


def test_counter_stack_edge_keeps_parent_local_condition_and_shared_identity():
    parent_url = "https://example.test/wiki/Counter_Parent"
    block_location = "sha256:counter-parent/block[0]"
    tokens = [
        _text_token("When Counter activates, grants 2", f"{block_location}/text[0]", 0),
        _text_token("Stacks", f"{block_location}/name[1]", 1),
    ]
    parent = _unit("skill:example:counter-parent", "Counter Parent", parent_url, tokens)
    anchor = MechanicSourceAnchor(
        anchor_id="stack-anchor",
        source_kind="mechanic_definition",
        source_url=parent_url,
        source_capture_sha256="c" * 64,
        source_location="synthetic:stack-definition",
    )
    stack = SharedMechanicEntry(
        mechanic_id="shared:stack-test",
        mechanic_class="resource",
        definition_status="unavailable",
        definition_source_anchor_id="",
        aliases=(MechanicAlias(kind="name", value="Stacks", source_anchor_id=anchor.anchor_id),),
        source_anchors=(anchor,),
    )

    result = _classify(parent, registry=_registry(stack))
    edge = next(row for row in result.relationships if row.target_kind == "shared_mechanic")
    grant = next(row for row in _effects(result) if row.semantic_type == "resource_grant")

    assert edge.operation == "grants"
    assert edge.target_id == "shared:stack-test"
    assert edge.condition == "When Counter activates"
    assert edge.source_fact_id == parent.source_fact_id
    assert grant.capability_value == ""
    assert grant.semantic_subject == "stack"


def test_prayer_branch_and_echo_child_chain_preserve_each_relationship():
    parent_url = "https://example.test/wiki/Prayer_Parent"
    echo_url = "https://example.test/wiki/Echo_Child"
    followup_url = "https://example.test/wiki/Followup"
    parent_block = "sha256:prayer-parent/block[0]"
    child_block = "sha256:echo-child/block[0]"
    parent_tokens = [
        _text_token("Select", f"{parent_block}/text[0]", 0),
        _text_token("Prayer", f"{parent_block}/name[1]", 1),
        _text_token("or", f"{parent_block}/text[2]", 2),
        _text_token("Song", f"{parent_block}/name[3]", 3),
        _text_token("or activate", f"{parent_block}/text[4]", 4),
        _reference_token("Echo Skill", echo_url, f"{parent_block}/link[5]", 5),
    ]
    child_tokens = [
        _text_token("At end of turn, consumes 1", f"{child_block}/text[0]", 0),
        _reference_token("Echo", "https://example.test/wiki/Echo", f"{child_block}/link[1]", 1),
        _text_token("Stack and activates", f"{child_block}/text[2]", 2),
        _reference_token("Follow-up", followup_url, f"{child_block}/link[3]", 3),
    ]
    parent = _unit("skill:example:prayer-parent", "Prayer Parent", parent_url, parent_tokens)
    child = _unit("skill:example:echo-child", "Echo Skill", echo_url, child_tokens)
    followup = _unit("skill:example:followup", "Follow-up", followup_url, [])
    anchor = MechanicSourceAnchor(
        anchor_id="echo-anchor",
        source_kind="mechanic_definition",
        source_url="https://example.test/wiki/Echo",
        source_capture_sha256="d" * 64,
        source_location="synthetic:echo-definition",
    )
    echo = SharedMechanicEntry(
        mechanic_id="shared:echo-chain",
        mechanic_class="follow_up",
        definition_status="unavailable",
        definition_source_anchor_id="",
        aliases=(MechanicAlias(kind="href", value="https://example.test/wiki/Echo", source_anchor_id=anchor.anchor_id),),
        source_anchors=(anchor,),
    )
    prayer = SharedMechanicEntry(
        mechanic_id="shared:prayer-test",
        mechanic_class="support_choice",
        definition_status="unavailable",
        definition_source_anchor_id="",
        aliases=(MechanicAlias(kind="name", value="Prayer", source_anchor_id=anchor.anchor_id),),
        source_anchors=(anchor,),
    )
    song = SharedMechanicEntry(
        mechanic_id="shared:song-test",
        mechanic_class="support_choice",
        definition_status="unavailable",
        definition_source_anchor_id="",
        aliases=(MechanicAlias(kind="name", value="Song", source_anchor_id=anchor.anchor_id),),
        source_anchors=(anchor,),
    )

    result = _classify(parent, child, followup, registry=_registry(echo, prayer, song))
    prayer_edge = next(
        row for row in result.relationships
        if row.operation == "branches_to" and row.target_id == "shared:prayer-test"
    )
    song_edge = next(row for row in result.relationships if row.target_id == "shared:song-test")
    parent_child = next(row for row in result.relationships if row.target_id == child.source_fact_id)
    child_followup = next(row for row in result.relationships if row.target_id == followup.source_fact_id)
    child_echo = next(
        row for row in result.relationships
        if row.source_fact_id == child.source_fact_id and row.target_kind == "shared_mechanic"
    )

    assert prayer_edge.operation == song_edge.operation == "branches_to"
    assert parent_child.operation == "activates"
    assert parent_child.source_fact_id == parent.source_fact_id
    assert child_followup.source_fact_id == child.source_fact_id
    assert child_followup.operation == "activates"
    assert child_followup.timing == "turn_end"
    assert child_echo.operation == "consumes"
    assert child_echo.timing == "turn_end"
    assert child_echo.target_id == "shared:echo-chain"
    assert not any(row.semantic_type == "resource_consumption" for row in _effects(result))
    child_result = _classify(child, followup, registry=_registry(echo, prayer, song))
    assert sum(row.semantic_type == "resource_consumption" for row in _effects(child_result)) == 1
    assert not any(row.capability_value == "direct_damage" for row in _effects(child_result))


def test_allowlisted_shared_mechanics_remain_identity_edges_without_definition_semantics():
    parent_url = "https://example.test/wiki/Echo_Parent"
    echo_url = "https://example.test/wiki/Echo"
    block_location = "sha256:echo-parent/block[0]"
    tokens = [
        _text_token("Activates", f"{block_location}/text[0]", 0),
        _reference_token("Echo", echo_url, f"{block_location}/link[1]", 1),
        _text_token("at end of turn when Another Zone is active", f"{block_location}/text[2]", 2),
    ]
    parent = _unit("skill:example:echo-parent", "Echo Parent", parent_url, tokens)
    anchor = MechanicSourceAnchor(
        anchor_id="test-anchor",
        source_kind="mechanic_definition",
        source_url=echo_url,
        source_capture_sha256="b" * 64,
        source_location="synthetic:echo-definition",
    )
    echo = SharedMechanicEntry(
        mechanic_id="shared:echo-test",
        mechanic_class="follow_up",
        definition_status="unavailable",
        definition_source_anchor_id="",
        aliases=(MechanicAlias(kind="href", value=echo_url, source_anchor_id=anchor.anchor_id),),
        source_anchors=(anchor,),
    )

    result = _classify(parent, registry=_registry(echo))
    edge = next(row for row in result.relationships if row.target_kind == "shared_mechanic")

    assert edge.source_fact_id == parent.source_fact_id
    assert edge.target_id == "shared:echo-test"
    assert edge.operation == "activates"
    assert edge.definition_status == "unavailable"
    assert edge.condition == "when Another Zone is active"
    assert edge.timing == "turn_end"
    assert edge.authority == "automatic_candidate"
