"""Durable invariants for deterministic capability-template lineup generation."""

from src.workflow.lineup_generation import (
    BEAM_WIDTH,
    build_capability_templates,
    generate_lineup_candidates,
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


def generate(*, all_dps=False, setup_dependencies=None, unique_items=False, with_sidekick=False):
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
    )


def test_templates_are_explicit_and_multifunction_heroes_can_cover_multiple_requirements():
    templates = build_capability_templates(boss={"name": "Mimi", "weak": ["Fire"]})

    assert set(templates) == {"burst", "sustain", "hybrid"}
    assert all(template["mandatory"] for template in templates.values())
    result = generate()

    assert result["candidate_count"] >= 1
    first = result["candidates"][0]
    assert "primary_damage" in first["coverage"]["covered_roles"]
    assert "offensive_enablement" in first["coverage"]["covered_roles"]
    assert {"offensive_enablement", "defense_mitigation"}.issubset(first["role_assignments"]["character:0"])


def test_beam_search_is_bounded_deterministic_and_preserves_archetype_diversity():
    first = generate()
    second = generate()

    assert first == second
    assert first["candidate_count"] <= 10
    assert {candidate["archetype"] for candidate in first["candidates"]} == {"burst", "sustain", "hybrid"}
    assert max(row["retained"] for row in first["diagnostics"]["beam_trace"]) <= BEAM_WIDTH
    assert all(row["beam_width"] == BEAM_WIDTH for row in first["diagnostics"]["beam_trace"])
    assert all(candidate["validation"]["valid"] for candidate in first["candidates"])


def test_all_damage_lineups_fail_without_mandatory_coverage():
    result = generate(all_dps=True)

    assert result["status"] == "zero"
    assert result["candidate_count"] == 0
    assert "missing_mandatory_coverage" in result["diagnostics"]["zero_candidate_causes"]


def test_required_setup_and_build_allocation_are_hard_candidate_gates():
    setup_result = generate(all_dps=True, setup_dependencies=["requires_zone"])
    assert setup_result["status"] == "zero"
    assert setup_result["diagnostics"]["rejection_counts"]["mandatory.setup.zone_setup"] > 0

    allocation_result = generate(unique_items=True)
    assert allocation_result["status"] == "zero"
    assert "build_incompatibility" in allocation_result["diagnostics"]["zero_candidate_causes"]


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
