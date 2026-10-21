"""Durable invariants for deterministic capability-template lineup generation."""

from src.workflow.lineup_generation import (
    BEAM_WIDTH,
    build_capability_templates,
    generate_lineup_candidates,
    score_lineup_candidate,
)
from src.workflow.nodes.analyze import _analyze_candidate_bundle


def package(character_id, *, setup_dependencies=None, unique=False):
    item = {
        "id": "equipment:shared" if unique else f"equipment:{character_id}",
        "name": "Shared weapon" if unique else f"Weapon {character_id}",
        "generic": False,
        "copy_limit": 1 if unique else None,
    }
    return {
        "id": f"build-package:{character_id}",
        "weapon": item,
        "armor": {"id": f"armor:{character_id}", "name": "Armor", "generic": True},
        "grastas": [
            {"id": f"grasta:{character_id}:{slot}", "name": "Generic Grasta", "generic": True}
            for slot in range(3)
        ],
        "ores": [],
        "assumptions": [],
        "setup_dependencies": setup_dependencies or [],
    }


def fixture(*, all_dps=False, setup_dependencies=None, unique_items=False, with_sidekick=False):
    characters = []
    entities = []
    for index in range(6):
        entity_id = f"character:{index}"
        roles = {"primary_damage": 4}
        if not all_dps and index == 0:
            roles.update({
                "offensive_enablement": 4,
                "defense_mitigation": 4,
                "zone_setup": 3,
            })
        elif not all_dps and index == 1:
            roles.update({"offensive_enablement": 3})
        elif not all_dps and index == 2:
            roles.update({"defense_mitigation": 3, "recovery_protection": 2})
        elif not all_dps and index == 3:
            roles.update({"recovery_protection": 3, "mp_sustain": 2})
        elif not all_dps and index in {4, 5}:
            roles.update({"reserve_utility": 3, "mp_sustain": 2})
        evidence = {
            role: [{"fact_id": f"fact:{index}:{role}", "capability": role}]
            for role in roles
        }
        characters.append({"id": entity_id, "name": f"Hero {index}"})
        entities.append({
            "id": entity_id,
            "name": f"Hero {index}",
            "entity_type": "character",
            "eligible": True,
            "role_scores": roles,
            "role_ids": list(roles),
            "evidence": evidence,
            "default_package": {"skill_ids": [f"skill:{index}:{slot}" for slot in range(3)]},
            "build_package": package(entity_id, setup_dependencies=setup_dependencies, unique=unique_items),
        })

    if with_sidekick:
        entities.extend([
            {
                "id": "sidekick:moke:main",
                "name": "Moke",
                "entity_type": "sidekick",
                "placement": "main",
                "role_scores": {"boss_counter": 5},
                "role_ids": ["boss_counter"],
                "evidence": {"boss_counter": [{"capability": "grant_status_immunity", "fact_id": "moke:guard"}]},
            },
            {
                "id": "sidekick:moke:sub",
                "name": "Moke",
                "entity_type": "sidekick",
                "placement": "sub",
                "role_scores": {"mp_sustain": 4},
                "role_ids": ["mp_sustain"],
                "evidence": {"mp_sustain": [{"capability": "recover_mp", "fact_id": "moke:mp"}]},
            },
        ])

    role_pools = {
        role: [entity["id"] for entity in entities if entity.get("entity_type") == "character" and role in entity.get("role_ids", [])]
        for role in ("primary_damage", "offensive_enablement", "zone_setup", "defense_mitigation", "recovery_protection", "mp_sustain", "reserve_utility")
    }
    role_scores = {"entities": entities, "role_pools": role_pools}
    if with_sidekick:
        role_scores["required_boss_counters"] = ["grant_status_immunity"]
    return characters, entities, role_scores


def generate(*, all_dps=False, setup_dependencies=None, unique_items=False, with_sidekick=False, max_candidates=10):
    characters, _, role_scores = fixture(
        all_dps=all_dps,
        setup_dependencies=setup_dependencies,
        unique_items=unique_items,
        with_sidekick=with_sidekick,
    )
    sidekicks = [{"id": "sidekick:moke", "name": "Moke"}] if with_sidekick else []
    return generate_lineup_candidates(
        characters=characters,
        sidekicks=sidekicks,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
        max_candidates=max_candidates,
    )


def test_templates_are_explicit_and_multifunction_heroes_can_cover_multiple_requirements():
    templates = build_capability_templates(boss={"name": "Mimi", "weak": ["Fire"]})

    assert set(templates) == {"burst", "sustain", "hybrid"}
    assert all([group["id"] for group in template["mandatory"]] == ["primary_damage"] for template in templates.values())
    assert all(
        {"offensive_enablement", "defense_mitigation", "recovery_protection", "tank_control", "zone_setup"}
        <= set(template["optional"])
        for template in templates.values()
    )
    result = generate()

    assert result["candidate_count"] >= 1
    first = result["candidates"][0]
    assert "primary_damage" in first["coverage"]["covered_roles"]
    assert "offensive_enablement" in first["coverage"]["covered_roles"]
    assert {"offensive_enablement", "defense_mitigation"}.issubset(first["role_assignments"]["character:0"])


def test_boss_weakness_bonus_uses_selected_attack_matchups_not_boss_weakness_presence():
    characters, entities, _ = fixture()
    entity_map = {entity["id"]: entity for entity in entities}
    candidate = {
        "archetype": "burst",
        "character_ids": [character["id"] for character in characters],
        "coverage": {"mandatory": ["primary_damage"], "missing": [], "setup_dependencies": []},
    }

    no_matched_attack = score_lineup_candidate(
        candidate,
        entities=entity_map,
        boss={"name": "Boss", "weak": ["Fire"]},
    )
    candidate["skill_packages"] = {
        "character:0": {
            "primary_damage_weakness_bonus": 3,
            "damage_matchups": [{"fact_id": "skill:fire-slash", "state": "weak"}],
        }
    }
    one_matched_attack = score_lineup_candidate(
        candidate,
        entities=entity_map,
        boss={"name": "Boss", "weak": ["Fire"]},
    )

    assert no_matched_attack["component_scores"]["boss_matchup"] == 24
    assert one_matched_attack["component_scores"]["boss_matchup"] == 27


def test_beam_search_is_bounded_deterministic_and_preserves_archetype_diversity():
    first = generate()
    second = generate()

    assert first == second
    assert first["candidate_count"] <= 10
    assert {candidate["archetype"] for candidate in first["candidates"]} == {"burst", "sustain", "hybrid"}
    assert max(row["retained"] for row in first["diagnostics"]["beam_trace"]) <= BEAM_WIDTH
    assert all(row["beam_width"] == BEAM_WIDTH for row in first["diagnostics"]["beam_trace"])
    assert all(candidate["validation"]["valid"] for candidate in first["candidates"])


def test_generic_role_preferences_do_not_reject_legal_damage_lineups_or_require_three_archetypes():
    result = generate(all_dps=True, max_candidates=1)

    assert result["status"] == "success"
    assert result["candidate_count"] == 1
    assert len(result["missing_archetypes"]) == 2
    assert result["candidates"][0]["coverage"]["mandatory"] == ["primary_damage"]
    assert result["candidates"][0]["coverage"]["missing"] == []


def test_generic_roles_remain_scored_as_preferences_and_explicit_sustain_is_still_required():
    characters, dps_entities, _ = fixture(all_dps=True)
    _, supported_entities, _ = fixture()
    candidate = {
        "archetype": "burst",
        "character_ids": [character["id"] for character in characters],
        "coverage": {"mandatory": ["primary_damage"], "missing": [], "setup_dependencies": []},
    }

    dps_score = score_lineup_candidate(candidate, entities={row["id"]: row for row in dps_entities})
    supported_score = score_lineup_candidate(candidate, entities={row["id"]: row for row in supported_entities})
    generic_sustain = build_capability_templates(boss={"mechanic_tags": ["sustain"]})
    required_sustain = build_capability_templates(boss={"required_counters": ["recover_mp"]})
    generic_sustain_result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Long fight", "mechanic_tags": ["sustain"]},
        role_scores={"entities": dps_entities},
    )
    required_mp_result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "MP counter", "required_counters": ["recover_mp"]},
        role_scores={"entities": dps_entities},
    )

    assert dps_score["component_scores"]["sustain_mitigation"] == 0
    assert supported_score["component_scores"]["sustain_mitigation"] > 0
    assert generic_sustain["sustain"]["requires_mp_sustain"] is False
    assert required_sustain["sustain"]["requires_mp_sustain"] is True
    assert generic_sustain_result["candidate_count"] > 0
    assert required_mp_result["candidate_count"] == 0
    assert required_mp_result["diagnostics"]["rejection_counts"]["mandatory.counter.recover_mp"] > 0


def test_required_setup_and_build_allocation_are_hard_candidate_gates():
    setup_result = generate(all_dps=True, setup_dependencies=["requires_zone"])
    assert setup_result["status"] == "zero"
    assert setup_result["diagnostics"]["rejection_counts"]["mandatory.setup.zone_setup"] > 0

    allocation_result = generate(unique_items=True)
    assert allocation_result["status"] == "zero"
    assert "build_incompatibility" in allocation_result["diagnostics"]["zero_candidate_causes"]


def test_source_established_boss_counter_remains_a_hard_candidate_gate():
    characters, _, role_scores = fixture(all_dps=True)
    role_scores["required_boss_counters"] = ["grant_status_immunity"]

    result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Status boss", "weak": ["Fire"]},
        role_scores=role_scores,
    )

    assert result["candidate_count"] == 0
    assert result["diagnostics"]["rejection_counts"]["mandatory.counter.grant_status_immunity"] > 0


def test_lineup_generation_selects_package_alternatives_before_rejecting_finite_items():
    characters, entities, role_scores = fixture(unique_items=True)
    for entity in entities:
        if entity.get("entity_type") != "character":
            continue
        entity["build_package_options"] = [
            entity["build_package"],
            package(f"{entity['id']}:alternative", unique=False),
        ]

    result = generate_lineup_candidates(
        characters=characters,
        boss={"name": "Mimi", "weak": ["Fire"]},
        role_scores=role_scores,
    )

    assert result["candidate_count"] >= 1
    candidate = result["candidates"][0]
    assert candidate["validation"]["valid"] is True
    assert candidate["allocation_search"]["states_explored"] > 1
    assert any(
        candidate["build_package_ids"][entity_id] != entity["build_package"]["id"]
        for entity_id, entity in ((item["id"], item) for item in entities if item.get("entity_type") == "character")
    )


def test_legal_sidekick_main_contribution_can_satisfy_a_required_counter():
    result = generate(with_sidekick=True)

    assert result["candidate_count"] >= 1
    assert any(candidate["main_sidekick_id"] == "sidekick:moke" for candidate in result["candidates"])
    assert all(candidate["main_sidekick_id"] != candidate["sub_sidekick_id"] for candidate in result["candidates"])


def test_zero_backend_candidates_skip_analyzer_call():
    state = {
        "candidate_bundle": {
            "coverage": {"complete": True},
            "candidate_generation": {
                "status": "zero",
                "candidates": [],
                "diagnostics": {"zero_candidate_causes": ["insufficient_roster"]},
            },
        },
        "retry_count": 0,
    }

    result = _analyze_candidate_bundle(state)

    assert result["analysis_failure"]["type"] == "no_backend_candidates"
    assert result["analyzer_call_count"] == 0
