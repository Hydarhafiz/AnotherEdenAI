"""Durable regression coverage for Feature E build packages and allocation."""

from copy import deepcopy

import pytest

from src.workflow.build_packages import (
    build_build_package,
    build_build_package_options,
    build_packages_for_characters,
    resolve_lineup_allocation,
    validate_build_package,
    validate_lineup_allocation,
)
from src.workflow.candidates import prepare_candidates_node


def character(name="Aldo", *, traits=None, weapon="Sword"):
    return {
        "id": f"character:{name.casefold()}",
        "name": name,
        "display_name": name,
        "weapon": weapon,
        "traits": traits or ["Eastern"],
    }


def grastas():
    return [
        {
            "id": "grasta:unique-sword",
            "name": "Unique Sword Power",
            "display_name": "Unique Sword Power (Eastern)",
            "category": "Attack",
            "tier": 3,
            "personality_req": "Eastern",
            "weapon_group": ["Sword"],
            "effect_text": "Sword damage up",
            "acquisition_class": "unique",
            "max_theoretical_copies": 1,
            "source_url": "https://example.test/grasta/unique",
        },
        {
            "id": "grasta:repeatable",
            "name": "Power of Mind",
            "display_name": "Power of Mind",
            "category": "Support",
            "tier": 2,
            "effect_text": "Power up",
            "acquisition_class": "repeatable",
            "source_url": "https://example.test/grasta/repeatable",
        },
        {
            "id": "grasta:wrong-trait",
            "name": "Wrong Trait",
            "display_name": "Wrong Trait (Dragon)",
            "category": "Attack",
            "tier": 4,
            "personality_req": "Dragon",
            "weapon_group": ["Sword"],
            "effect_text": "Damage up",
        },
    ]


def equipment():
    return [
        {
            "id": "equipment:sword-unique",
            "name": "Unique Sword",
            "equipment_slot": "weapon",
            "category": "Sword",
            "level": 100,
            "source_url": "https://example.test/equipment/sword",
        },
        {
            "id": "equipment:armor-unique",
            "name": "Unique Armor",
            "equipment_slot": "armor",
            "level": 100,
            "source_url": "https://example.test/equipment/armor",
        },
    ]


def role_entity():
    return {
        "role_ids": ["primary_damage", "offensive_enablement"],
        "skill_shortlists": {},
    }


def test_late_game_package_is_compact_labeled_and_source_grounded():
    package = build_build_package(
        character(),
        role_entity=role_entity(),
        grastas=grastas(),
        equipment=equipment(),
        selected_facts=[{"dependencies": ["requires_zone"]}],
    )

    assert package["item_policy"] == "late_game_assumed"
    assert package["ownership_status"] == "unverified"
    assert len(package["grastas"]) == 3
    assert package["weapon"]["id"] == "equipment:sword-unique"
    assert package["armor"]["id"] == "equipment:armor-unique"
    assert "requires_zone" in package["setup_dependencies"]
    assert package["assumptions"]
    assert package["evidence"]
    assert package["citations"]
    assert validate_build_package(package, character=character(), grastas=grastas(), equipment=equipment()) == []


def test_package_excludes_incompatible_grasta_variants_and_supports_generic_fallback():
    package = build_build_package(
        character(traits=["Western"]),
        role_entity=role_entity(),
        grastas=grastas(),
        equipment=equipment(),
    )
    assert "grasta:wrong-trait" not in {item["id"] for item in package["grastas"]}
    assert {item["id"] for item in package["grastas"]} == {"grasta:repeatable"}

    generic = build_build_package(
        character(),
        role_entity=role_entity(),
        grastas=grastas(),
        equipment=equipment(),
        item_policy="generic_only",
    )
    assert generic["item_policy"] == "generic_only"
    assert generic["weapon"]["generic"] is True
    assert generic["armor"]["generic"] is True
    assert all(item["generic"] for item in generic["grastas"])


def test_package_validation_rejects_wrong_compatibility_and_finite_reuse():
    package = build_build_package(character(), role_entity=role_entity(), grastas=grastas(), equipment=equipment())
    package["grastas"] = [grastas()[0]] * 3

    errors = validate_build_package(package, character=character(), grastas=grastas(), equipment=equipment())

    assert any(error["code"] == "cardinality.grasta" for error in errors)

    package["grastas"] = [grastas()[2]] * 3
    errors = validate_build_package(package, character=character(), grastas=grastas(), equipment=equipment())
    assert any(error["code"] == "compatibility.trait" for error in errors)


def test_lineup_allocation_rejects_duplicate_named_equipment_and_unique_grasta():
    first = build_build_package(character("Aldo"), role_entity=role_entity(), grastas=grastas(), equipment=equipment())
    second = build_build_package(character("Ciel"), role_entity=role_entity(), grastas=grastas(), equipment=equipment())
    result = validate_lineup_allocation({"character:aldo": first, "character:ciel": second})

    assert result["valid"] is False
    assert any(error["code"] == "cardinality.lineup" for error in result["errors"])
    assert {item["item_id"] for item in result["allocation"]["items"]}


def test_unknown_named_grasta_is_conservative_and_uses_labelled_generic_slots():
    package = build_build_package(
        character(),
        role_entity=role_entity(),
        grastas=[{
            "id": "grasta:unknown-cardinality",
            "name": "Unknown Cardinality",
            "effect_text": "Power up",
        }],
        equipment=[],
    )

    ids = [item["id"] for item in package["grastas"]]
    assert ids.count("grasta:unknown-cardinality") == 1
    assert package["generic_placeholder_count"] >= 2
    assert sum(item["generic"] for item in package["grastas"]) == 2
    assert all("compatible" in item["display_name"].casefold() for item in package["grastas"] if item["generic"])
    assert validate_build_package(package, character=character(), grastas=[{
        "id": "grasta:unknown-cardinality",
        "name": "Unknown Cardinality",
        "effect_text": "Power up",
    }], equipment=[]) == []


def test_alternative_packages_resolve_finite_copy_collisions_deterministically():
    finite_grastas = [
        {"id": f"grasta:finite-{index}", "name": f"Finite {index}", "acquisition_class": "unique"}
        for index in range(1, 7)
    ]
    options = build_build_package_options(character(), grastas=finite_grastas, equipment=[])

    assert 1 <= len(options) <= 6
    assert options[0]["grasta_ids"] == ["grasta:finite-1", "grasta:finite-2", "grasta:finite-3"]
    assert any(set(option["grasta_ids"]).isdisjoint(options[0]["grasta_ids"]) for option in options[1:])

    result = resolve_lineup_allocation({
        "character:aldo": options,
        "character:ciel": options,
    }, character_ids=["character:aldo", "character:ciel"])

    assert result["valid"] is True
    assert result["selected_package_ids"]
    assert result["search"]["bounded"] is True
    assert result["allocation"]["scope"] == "lineup"
    assert all(item["copies_required"] <= item["copy_limit"] for item in result["allocation"]["items"] if item["copy_limit"] is not None)


def test_lineup_allocation_copy_ledger_resets_between_alternative_lineups():
    finite_grastas = [
        {"id": f"grasta:finite-{index}", "name": f"Finite {index}", "acquisition_class": "unique"}
        for index in range(1, 7)
    ]
    options = build_build_package_options(character(), grastas=finite_grastas, equipment=[])
    packages = {"character:aldo": options, "character:ciel": options}

    first = resolve_lineup_allocation(packages, character_ids=["character:aldo", "character:ciel"])
    second = resolve_lineup_allocation(packages, character_ids=["character:aldo", "character:ciel"])

    assert first == second


def test_lineup_allocation_reports_and_honors_the_search_bound():
    options = build_build_package_options(
        character(),
        grastas=[
            {"id": f"grasta:finite-{index}", "name": f"Finite {index}", "acquisition_class": "unique"}
            for index in range(1, 7)
        ],
        equipment=[],
    )

    result = resolve_lineup_allocation(
        {"character:aldo": options, "character:ciel": options},
        character_ids=["character:aldo", "character:ciel"],
        max_states=1,
    )

    assert result["valid"] is False
    assert result["search"]["states_explored"] == 1
    assert result["search"]["exhausted"] is True
    assert any(error["code"] == "allocation.search_bound" for error in result["errors"])


def test_batch_generation_is_deterministic_and_preserves_unverified_status():
    characters = [character("Aldo"), character("Ciel", traits=["Eastern"], weapon="Bow")]
    first = build_packages_for_characters(
        characters,
        grastas=grastas(),
        equipment=equipment(),
        skills=[],
    )
    second = build_packages_for_characters(
        deepcopy(characters),
        grastas=deepcopy(grastas()),
        equipment=deepcopy(equipment()),
        skills=[],
    )

    assert first == second
    assert all(package["ownership_status"] == "unverified" for package in first.values())
    assert all("alternatives" in package for package in first.values())


@pytest.mark.asyncio
async def test_typed_candidate_projection_excludes_full_item_catalogs():
    characters = [character(f"Hero {index}") for index in range(6)]
    entities = []
    packages = {}
    for value in characters:
        package = build_build_package(value, role_entity=role_entity(), grastas=grastas(), equipment=equipment())
        packages[value["id"]] = package
        entities.append({
            "id": value["id"],
            "name": value["name"],
            "entity_type": "character",
            "eligible": True,
            "role_ids": ["primary_damage"],
            "role_scores": {"primary_damage": 1},
            "evidence": {},
            "skill_shortlists": {},
            "default_package": {},
            "build_package": package,
        })
    result = await prepare_candidates_node({
        "roster": [value["name"] for value in characters],
        "owned_sidekicks": [],
        "item_policy": "late_game_assumed",
        "stellar_awakened": {},
        "typed_retrieval": {
            "request": {"item_policy": "late_game_assumed", "stellar_awakened": {}},
            "characters": characters,
            "skills": [],
            "passives": [],
            "sidekicks": [],
            "boss": {"name": "Mimi", "weak": [], "resist": [], "null": [], "absorb": []},
            "coverage": {"complete": True, "missing_character_names": []},
            "role_scores": {"entities": entities, "build_packages": packages},
        },
    }, None)

    bundle = result["candidate_bundle"]
    assert "grastas" not in bundle
    assert "equipment" not in bundle
    assert all(character["build_package"]["ownership_status"] == "unverified" for character in bundle["characters"])
