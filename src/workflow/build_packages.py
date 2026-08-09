"""Deterministic late-game build packages and lineup item allocation.

Feature E keeps item policy on the backend.  A package is a small, explainable
selection of compatible item facts for one character; it is not an inventory
optimizer and it never treats an unverified item as player-owned.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any


BUILD_PACKAGE_POLICY_VERSION = "feature-e-build-package-v1"
ITEM_POLICIES = ("late_game_assumed", "generic_only")
DEFAULT_ITEM_POLICY = "late_game_assumed"


class BuildPackageError(ValueError):
    """Raised when a package cannot be generated under the item policy."""


def build_build_package(
    character: dict[str, Any],
    *,
    role_entity: dict[str, Any] | None = None,
    grastas: list[dict[str, Any]] | None = None,
    equipment: list[dict[str, Any]] | None = None,
    ores: list[dict[str, Any]] | None = None,
    selected_facts: list[dict[str, Any]] | None = None,
    item_policy: str = DEFAULT_ITEM_POLICY,
) -> dict[str, Any]:
    """Generate one compact, deterministic package for ``character``.

    ``late_game_assumed`` may select catalog-backed named items, while
    ``generic_only`` deliberately emits category-level assumptions.  Neither
    policy asserts that the player owns any item.
    """
    if item_policy not in ITEM_POLICIES:
        raise BuildPackageError(f"Unsupported item policy: {item_policy}")

    role_entity = role_entity or {}
    grasta_rows = [row for row in (grastas or []) if isinstance(row, dict)]
    equipment_rows = [row for row in (equipment or []) if isinstance(row, dict)]
    ore_rows = [row for row in (ores or []) if isinstance(row, dict)]
    character_id = _character_id(character)
    character_name = str(character.get("name") or character.get("display_name") or character_id)
    weapon_type = str(character.get("weapon") or "unknown")
    traits = _normalised_values(
        character.get("traits")
        or character.get("character_traits")
        or character.get("personalities")
    )

    weapon = _select_equipment(
        equipment_rows,
        slot="weapon",
        category=weapon_type,
        character_id=character_id,
        item_policy=item_policy,
    )
    armor = _select_equipment(
        equipment_rows,
        slot="armor",
        category="armor",
        character_id=character_id,
        item_policy=item_policy,
    )
    selected_grastas = _select_grastas(
        grasta_rows,
        traits=traits,
        weapon_type=weapon_type,
        character_id=character_id,
        role_entity=role_entity,
        item_policy=item_policy,
    )
    selected_ores = _select_ores(ore_rows, role_entity=role_entity, item_policy=item_policy)

    setup_dependencies = _setup_dependencies(
        selected_grastas,
        selected_facts or [],
        role_entity,
    )
    citations = _citations([weapon, armor, *selected_grastas, *selected_ores], item_policy)
    assumptions = _assumptions(
        item_policy=item_policy,
        weapon=weapon,
        armor=armor,
        grastas=selected_grastas,
        ores=selected_ores,
        traits=traits,
    )
    allocation = _package_allocation([weapon, armor, *selected_grastas, *selected_ores])
    evidence = _package_evidence(
        [weapon, armor, *selected_grastas, *selected_ores],
        role_entity=role_entity,
        item_policy=item_policy,
    )
    role_ids = list(role_entity.get("role_ids") or [])
    package_id = _stable_id(
        "build-package",
        character_id,
        item_policy,
        weapon.get("id"),
        armor.get("id"),
        *[item.get("id") for item in selected_grastas],
        *[item.get("id") for item in selected_ores],
    )
    return {
        "id": package_id,
        "version": BUILD_PACKAGE_POLICY_VERSION,
        "character_id": character_id,
        "character_name": character_name,
        "item_policy": item_policy,
        "ownership_status": "unverified",
        "ownership": "unverified",
        "weapon": weapon,
        "armor": armor,
        "grastas": selected_grastas,
        "ores": selected_ores,
        "weapon_id": weapon.get("id"),
        "armor_id": armor.get("id"),
        "grasta_ids": [item.get("id") for item in selected_grastas],
        "ore_ids": [item.get("id") for item in selected_ores],
        "build_intent": _build_intent(role_ids, selected_ores),
        "assumptions": assumptions,
        "assumption_labels": assumptions,
        "allocation": allocation,
        "setup_dependencies": setup_dependencies,
        "setup_dependency_ids": setup_dependencies,
        "evidence": evidence,
        "citations": citations,
        "citation_ids": [citation["id"] for citation in citations],
        "role_ids": role_ids,
    }


def generate_build_package(*args, **kwargs) -> dict[str, Any]:
    """Compatibility alias for callers that use the feature's verb-first name."""
    return build_build_package(*args, **kwargs)


def build_packages_for_characters(
    characters: list[dict[str, Any]],
    *,
    role_entities: dict[str, dict[str, Any]] | list[dict[str, Any]] | None = None,
    grastas: list[dict[str, Any]] | None = None,
    equipment: list[dict[str, Any]] | None = None,
    ores: list[dict[str, Any]] | None = None,
    skills: list[dict[str, Any]] | None = None,
    item_policy: str = DEFAULT_ITEM_POLICY,
) -> dict[str, dict[str, Any]]:
    """Build packages keyed by stable character ID in deterministic order."""
    entities = _index_entities(role_entities)
    facts_by_owner: dict[str, list[dict[str, Any]]] = {}
    for fact in skills or []:
        owner = str(fact.get("character_name") or "")
        if owner:
            facts_by_owner.setdefault(owner, []).append(fact)

    packages: dict[str, dict[str, Any]] = {}
    for character in sorted(characters, key=lambda row: (_character_id(row), str(row.get("name") or ""))):
        character_id = _character_id(character)
        role_entity = entities.get(character_id) or entities.get(str(character.get("name") or ""), {})
        package = build_build_package(
            character,
            role_entity=role_entity,
            grastas=grastas,
            equipment=equipment,
            ores=ores,
            selected_facts=facts_by_owner.get(str(character.get("name") or ""), []),
            item_policy=item_policy,
        )
        packages[character_id] = package
    return packages


def generate_build_packages(*args, **kwargs) -> dict[str, dict[str, Any]]:
    """Compatibility alias for batch package generation."""
    return build_packages_for_characters(*args, **kwargs)


def validate_build_package(
    package: dict[str, Any],
    *,
    character: dict[str, Any] | None = None,
    grastas: list[dict[str, Any]] | None = None,
    equipment: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return structured package errors without mutating the package."""
    errors: list[dict[str, Any]] = []
    policy = package.get("item_policy")
    if policy not in ITEM_POLICIES:
        errors.append(_error("policy.invalid", "item_policy", f"Unsupported item policy: {policy}"))
    for key in ("weapon", "armor"):
        if not isinstance(package.get(key), dict) or not package[key].get("id"):
            errors.append(_error("shape.item", key, f"{key} package item is required"))
    if not isinstance(package.get("grastas"), list) or len(package.get("grastas", [])) != 3:
        errors.append(_error("shape.grasta", "grastas", "Exactly three Grasta selections are required"))
    for key in ("assumptions", "setup_dependencies", "evidence", "citations"):
        if not isinstance(package.get(key), list):
            errors.append(_error("shape.metadata", key, f"{key} must be a list"))
    if package.get("ownership_status") != "unverified":
        errors.append(_error("ownership.status", "ownership_status", "MVP item ownership must remain unverified"))

    character = character or {}
    traits = _normalised_values(
        character.get("traits")
        or character.get("character_traits")
        or character.get("personalities")
    )
    weapon_type = str(character.get("weapon") or "")
    catalog_grastas = {_item_id(row, "grasta") : row for row in (grastas or []) if isinstance(row, dict)}
    catalog_equipment = {
        _item_id(row, "equipment"): row
        for row in (equipment or [])
        if isinstance(row, dict)
    }

    for slot in ("weapon", "armor"):
        item = package.get(slot)
        if not isinstance(item, dict) or item.get("generic"):
            continue
        catalog_item = catalog_equipment.get(str(item.get("id")))
        if catalog_equipment and catalog_item is None:
            errors.append(_error("id.equipment", slot, f"Unknown named {slot} item: {item.get('id')}"))
            continue
        if catalog_item and str(catalog_item.get("equipment_slot") or "").casefold() != slot:
            errors.append(_error("compatibility.slot", slot, f"Equipment item is not a {slot}"))
        if slot == "weapon" and weapon_type and catalog_item:
            category = str(catalog_item.get("category") or "")
            if category and category.casefold() != weapon_type.casefold():
                errors.append(_error("compatibility.weapon", slot, f"Weapon category {category} does not match {weapon_type}"))

    allocated = Counter()
    for index, item in enumerate(package.get("grastas", []) if isinstance(package.get("grastas"), list) else []):
        if not isinstance(item, dict) or not item.get("id"):
            errors.append(_error("shape.grasta_item", f"grastas.{index}", "Grasta item must contain an ID"))
            continue
        item_id = str(item["id"])
        catalog_item = catalog_grastas.get(item_id)
        if catalog_grastas and not item.get("generic") and catalog_item is None:
            errors.append(_error("id.grasta", f"grastas.{index}", f"Unknown Grasta item: {item_id}"))
            continue
        source = catalog_item or item
        compatibility_errors = _grasta_compatibility_errors(source, traits, weapon_type, known_traits=bool(traits))
        errors.extend(_error(code, f"grastas.{index}", message) for code, message in compatibility_errors)
        allocated[item_id] += 1

    for item_id, count in allocated.items():
        item = catalog_grastas.get(item_id) or next(
            (item for item in package.get("grastas", []) if item.get("id") == item_id),
            {},
        )
        limit = _copy_limit(item)
        if limit is not None and count > limit:
            errors.append(_error(
                "cardinality.grasta",
                "grastas",
                f"Grasta {item_id} requires {count} copies but the limit is {limit}",
            ))

    package_allocation = package.get("allocation")
    if not isinstance(package_allocation, dict):
        errors.append(_error("shape.allocation", "allocation", "Allocation metadata is required"))
    return errors


def validate_lineup_allocation(
    packages: dict[str, dict[str, Any]] | list[dict[str, Any]],
    *,
    character_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Validate finite Grasta and named-equipment reuse across one lineup."""
    package_map = _index_packages(packages)
    selected = character_ids or sorted(package_map)
    errors: list[dict[str, Any]] = []
    totals: dict[str, dict[str, Any]] = {}
    for character_id in selected:
        package = package_map.get(character_id)
        if package is None:
            errors.append(_error("id.package", character_id, f"No build package for {character_id}"))
            continue
        for item in _package_items(package):
            if item.get("generic"):
                continue
            item_id = str(item.get("id") or "")
            if not item_id:
                continue
            record = totals.setdefault(item_id, {
                "item_id": item_id,
                "display_name": item.get("display_name") or item.get("name"),
                "slot": item.get("slot"),
                "copies_required": 0,
                "copy_limit": _copy_limit(item),
                "character_ids": [],
            })
            record["copies_required"] += 1
            record["character_ids"].append(character_id)
            limit = _copy_limit(item)
            if limit is not None:
                record["copy_limit"] = limit
                if record["copies_required"] > limit:
                    errors.append(_error(
                        "cardinality.lineup",
                        character_id,
                        f"{item_id} is allocated {record['copies_required']} times but the limit is {limit}",
                        allowed_ids=[],
                    ))
    return {
        "valid": not errors,
        "errors": errors,
        "allocation": {
            "scope": "lineup",
            "items": [totals[item_id] for item_id in sorted(totals)],
        },
    }


def allocate_lineup_items(*args, **kwargs) -> dict[str, Any]:
    """Compatibility alias for lineup allocation validation."""
    return validate_lineup_allocation(*args, **kwargs)


def validate_lineup_packages(*args, **kwargs) -> dict[str, Any]:
    """Compatibility alias for callers that use package terminology."""
    return validate_lineup_allocation(*args, **kwargs)


def _select_equipment(rows, *, slot, category, character_id, item_policy):
    candidates = []
    for row in rows:
        row_slot = str(row.get("equipment_slot") or row.get("slot") or "").casefold()
        if row_slot != slot:
            continue
        if slot == "weapon":
            row_category = str(row.get("category") or "")
            if row_category and category and row_category.casefold() != category.casefold():
                continue
        if row.get("generic"):
            continue
        candidates.append(_equipment_item(row, slot=slot))
    candidates.sort(key=_equipment_sort_key)
    if item_policy == "late_game_assumed" and candidates:
        return candidates[0]
    label = category if slot == "weapon" and category and category != "unknown" else "available"
    return {
        "id": _stable_id("generic-item", slot, label),
        "display_name": f"{label} {slot} (late-game assumption)",
        "name": f"{label} {slot}",
        "slot": slot,
        "equipment_slot": slot,
        "category": category if category != "unknown" else None,
        "generic": True,
        "ownership_status": "unverified",
        "copy_limit": None,
        "source_url": None,
        "assumption": True,
    }


def _select_grastas(rows, *, traits, weapon_type, character_id, role_entity, item_policy):
    compatible = [
        _grasta_item(row)
        for row in rows
        if _grasta_is_compatible(row, traits, weapon_type)
    ]
    if item_policy == "generic_only":
        compatible = []
    compatible.sort(key=lambda item: _grasta_sort_key(item, role_entity))
    selected: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for item in compatible:
        if item["id"] in counts:
            continue
        limit = _copy_limit(item)
        if limit is not None and limit < 1:
            continue
        selected.append(item)
        counts[item["id"]] += 1
        if len(selected) == 3:
            return selected
    for item in compatible:
        limit = _copy_limit(item)
        while len(selected) < 3 and (limit is None or counts[item["id"]] < limit):
            selected.append(item.copy())
            counts[item["id"]] += 1
        if len(selected) == 3:
            return selected
    for index in range(len(selected), 3):
        selected.append(_generic_grasta(character_id, index + 1))
    return selected


def _select_ores(rows, *, role_entity, item_policy):
    if item_policy == "generic_only" or not rows:
        return []
    ordered = sorted(rows, key=lambda row: (
        -int(row.get("tier") or row.get("level") or 0),
        str(row.get("name") or row.get("id") or "").casefold(),
    ))
    # Ore is optional: one compact build-intent choice is enough for MVP.
    return [_ore_item(ordered[0])] if ordered else []


def _grasta_is_compatible(row, traits, weapon_type):
    required_trait = row.get("required_trait") or row.get("personality_req")
    if required_trait and str(required_trait).casefold() not in traits:
        return False
    weapon_req = row.get("weapon_req")
    if weapon_req and weapon_type and str(weapon_req).casefold() != weapon_type.casefold():
        return False
    weapon_group = _normalised_values(row.get("weapon_group"))
    if weapon_group and weapon_type.casefold() not in weapon_group:
        return False
    return True


def _grasta_compatibility_errors(row, traits, weapon_type, *, known_traits):
    errors = []
    required_trait = row.get("required_trait") or row.get("personality_req")
    if required_trait and not row.get("generic"):
        if not known_traits:
            errors.append(("compatibility.unknown_trait", "Grasta personality compatibility is unverified"))
        elif str(required_trait).casefold() not in traits:
            errors.append(("compatibility.trait", f"Character lacks required Grasta trait {required_trait}"))
    weapon_req = row.get("weapon_req")
    if weapon_req and weapon_type and str(weapon_req).casefold() != weapon_type.casefold():
        errors.append(("compatibility.weapon", f"Grasta requires weapon {weapon_req}, character uses {weapon_type}"))
    weapon_group = _normalised_values(row.get("weapon_group"))
    if weapon_group and weapon_type.casefold() not in weapon_group:
        errors.append(("compatibility.weapon", f"Grasta is not compatible with weapon {weapon_type}"))
    return errors


def _equipment_item(row, *, slot):
    item_id = _item_id(row, "equipment")
    return {
        "id": item_id,
        "display_name": row.get("display_name") or row.get("name") or item_id,
        "name": row.get("name") or row.get("display_name") or item_id,
        "slot": slot,
        "equipment_slot": slot,
        "category": row.get("category"),
        "level": row.get("level"),
        "effect_text": _compact_text(row.get("effect_text")),
        "generic": False,
        "ownership_status": "unverified",
        "copy_limit": _equipment_copy_limit(row),
        "acquisition_class": row.get("acquisition_class", "unknown"),
        "source_url": row.get("source_url"),
    }


def _grasta_item(row):
    item_id = _item_id(row, "grasta")
    return {
        "id": item_id,
        "display_name": row.get("display_name") or row.get("name") or item_id,
        "name": row.get("name") or row.get("display_name") or item_id,
        "category": row.get("category"),
        "tier": row.get("tier"),
        "stats": _compact_text(row.get("stats"), 120),
        "effect_text": _compact_text(row.get("effect_text"), 180),
        "personality_req": row.get("personality_req"),
        "required_trait": row.get("required_trait") or row.get("personality_req"),
        "weapon_req": row.get("weapon_req"),
        "weapon_group": list(row.get("weapon_group") or []),
        "effect_tags": list(row.get("effect_tags") or []),
        "is_shareable": row.get("is_shareable"),
        "acquisition_class": row.get("acquisition_class", "unknown"),
        "max_theoretical_copies": row.get("max_theoretical_copies"),
        "copy_limit": _copy_limit(row),
        "generic": False,
        "ownership_status": "unverified",
        "source_url": row.get("source_url"),
    }


def _generic_grasta(character_id, slot):
    return {
        "id": _stable_id("generic-grasta", character_id, slot),
        "display_name": f"Compatible Grasta slot {slot} (late-game assumption)",
        "name": "Compatible Grasta slot",
        "category": "generic",
        "tier": None,
        "stats": "",
        "effect_text": "Select a compatible late-game Grasta for this slot.",
        "personality_req": None,
        "required_trait": None,
        "weapon_req": None,
        "weapon_group": [],
        "effect_tags": [],
        "is_shareable": True,
        "acquisition_class": "repeatable",
        "max_theoretical_copies": None,
        "copy_limit": None,
        "generic": True,
        "ownership_status": "unverified",
        "source_url": None,
        "assumption": True,
    }


def _ore_item(row):
    item_id = _item_id(row, "ore")
    return {
        "id": item_id,
        "display_name": row.get("display_name") or row.get("name") or item_id,
        "name": row.get("name") or item_id,
        "slot": "ore",
        "stats": _compact_text(row.get("stats"), 120),
        "effect_tags": list(row.get("effect_tags") or []),
        "generic": False,
        "ownership_status": "unverified",
        "copy_limit": _copy_limit(row),
        "source_url": row.get("source_url") or row.get("source"),
    }


def _package_allocation(items):
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        record = by_id.setdefault(item_id, {
            "item_id": item_id,
            "display_name": item.get("display_name") or item.get("name"),
            "slot": item.get("slot") or item.get("equipment_slot") or "grasta",
            "copies_required": 0,
            "copy_limit": _copy_limit(item),
            "generic": bool(item.get("generic")),
        })
        record["copies_required"] += 1
    return {
        "scope": "lineup",
        "items": [by_id[item_id] for item_id in sorted(by_id)],
        "weapon": next((item for item in by_id.values() if item["slot"] == "weapon"), None),
        "armor": next((item for item in by_id.values() if item["slot"] == "armor"), None),
        "grastas": [item for item in by_id.values() if item["slot"] == "grasta"],
        "ores": [item for item in by_id.values() if item["slot"] == "ore"],
    }


def _package_items(package):
    return [
        package.get("weapon") or {},
        package.get("armor") or {},
        *(package.get("grastas") or []),
        *(package.get("ores") or []),
    ]


def _package_evidence(items, *, role_entity, item_policy):
    evidence = []
    for item in items:
        evidence.append({
            "item_id": item.get("id"),
            "kind": "item_fact" if not item.get("generic") else "item_policy_assumption",
            "source_url": item.get("source_url"),
            "ownership_status": "unverified",
        })
    for role_id in role_entity.get("role_ids") or []:
        evidence.append({
            "item_id": None,
            "kind": "role_context",
            "role_id": role_id,
            "policy_version": item_policy,
        })
    return evidence


def _citations(items, item_policy):
    citations = []
    seen = set()
    for item in items:
        url = item.get("source_url")
        if not url or url in seen:
            continue
        seen.add(url)
        citations.append({
            "id": _stable_id("citation", url),
            "label": item.get("display_name") or item.get("name") or "Item source",
            "source_url": url,
            "kind": "item_fact",
        })
    policy_id = _stable_id("citation", "item-policy", item_policy)
    citations.append({
        "id": policy_id,
        "label": f"{item_policy} item policy",
        "source_url": None,
        "kind": "policy",
    })
    return citations


def _assumptions(*, item_policy, weapon, armor, grastas, ores, traits):
    assumptions = ["Item ownership is unverified; the package is a build target, not an inventory claim."]
    if item_policy == "late_game_assumed":
        assumptions.append("Late-game weapon, armor, Grasta, and optional Ore access is assumed where named facts are available.")
    else:
        assumptions.append("Only generic item categories are asserted because named catalog items were intentionally omitted.")
    if any(item.get("generic") for item in [weapon, armor, *grastas, *ores]):
        assumptions.append("One or more item slots use a generic compatible placeholder because exact catalog coverage was unavailable.")
    if not traits and any(item.get("required_trait") for item in grastas):
        assumptions.append("Character traits were not supplied; personality-specific Grasta compatibility remains unverified.")
    if not ores:
        assumptions.append("Ore is optional and no specific Ore allocation is required for this package.")
    return assumptions


def _setup_dependencies(grastas, facts, role_entity):
    dependencies = set()
    raw_values = []
    for fact in [*facts, *[row for row in grastas if isinstance(row, dict)], role_entity]:
        for key in ("dependencies", "setup_dependencies", "requires", "required_capabilities"):
            value = fact.get(key) if isinstance(fact, dict) else None
            if isinstance(value, list):
                raw_values.extend(value)
            elif value:
                raw_values.append(value)
        text = " ".join(str(fact.get(key) or "") for key in ("name", "effect_text", "description", "stats", "effect_tags"))
        lowered = text.casefold()
        for token in ("pain", "poison", "zone", "lunatic", "stellar awakening", "another force"):
            if token in lowered:
                dependencies.add("requires_" + token.replace(" ", "_"))
    for value in raw_values:
        normalized = _dependency_value(value)
        if normalized:
            dependencies.add(normalized)
    return sorted(dependencies)


def _dependency_value(value):
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")
    if not normalized:
        return ""
    return normalized if normalized.startswith("requires_") else f"requires_{normalized}"


def _build_intent(role_ids, ores):
    intent = [f"Support contextual roles: {', '.join(role_ids[:3])}" if role_ids else "Use compatible late-game stats for the assigned role."]
    if ores:
        intent.append("Apply the selected Ore only after confirming the Grasta effect and player inventory.")
    else:
        intent.append("Tune Ore later as an optional build target; no exact optimizer result is asserted.")
    return intent


def _grasta_sort_key(item, role_entity):
    tags = {str(tag).casefold() for tag in item.get("effect_tags") or []}
    text = " ".join(str(item.get(key) or "") for key in ("name", "display_name", "effect_text", "stats")).casefold()
    role_ids = {str(value).casefold() for value in role_entity.get("role_ids") or []}
    score = 0
    if "primary_damage" in role_ids and any(token in text or token in tags for token in ("damage", "power", "attack", "critical")):
        score += 4
    if "offensive_enablement" in role_ids and any(token in text or token in tags for token in ("damage", "critical", "resistance")):
        score += 3
    if "mp_sustain" in role_ids and "mp" in text:
        score += 3
    if "defense_mitigation" in role_ids and any(token in text for token in ("guard", "resistance", "damage reduction", "hp")):
        score += 3
    return (-score, -int(item.get("tier") or 0), str(item.get("id") or ""))


def _equipment_sort_key(item):
    return (
        -int(item.get("level") or 0),
        -int(item.get("attack") or item.get("magic_attack") or item.get("defense") or 0),
        str(item.get("id") or ""),
    )


def _copy_limit(item):
    if item.get("generic"):
        return None
    for key in ("copy_limit", "max_theoretical_copies", "max_copies", "maximum_copies"):
        value = item.get(key)
        if value not in (None, ""):
            try:
                return max(1, int(value))
            except (TypeError, ValueError):
                pass
    acquisition = str(item.get("acquisition_class") or "").casefold()
    if acquisition in {"repeatable", "shareable", "unlimited"}:
        return None
    if acquisition in {"unique", "finite", "limited", "single"} or item.get("is_unique") is True or item.get("unique") is True:
        return 1
    return None


def _equipment_copy_limit(item):
    """Named equipment is single-allocation unless its source says otherwise."""
    explicit = _copy_limit(item)
    if explicit is not None:
        return explicit
    acquisition = str(item.get("acquisition_class") or "").casefold()
    if acquisition in {"repeatable", "shareable", "unlimited"}:
        return None
    return 1


def _item_id(row, prefix):
    return str(row.get("id") or row.get(f"{prefix}_id") or _stable_id(prefix, row.get("equipment_slot") or row.get("category"), row.get("name"), row.get("source_variant")))


def _character_id(character):
    return str(character.get("id") or character.get("character_id") or _stable_id("character", character.get("name") or character.get("display_name")))


def _index_entities(entities):
    if isinstance(entities, dict):
        return entities
    return {
        str(entity.get("id") or entity.get("name")): entity
        for entity in (entities or [])
        if isinstance(entity, dict)
    }


def _index_packages(packages):
    if isinstance(packages, dict):
        return packages
    return {
        str(package.get("character_id")): package
        for package in (packages or [])
        if isinstance(package, dict) and package.get("character_id")
    }


def _normalised_values(value):
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = []
    return {str(item).strip().casefold() for item in values if str(item).strip()}


def _error(code, path, message, *, allowed_ids=None):
    return {"code": code, "path": path, "message": message, "allowed_ids": allowed_ids or []}


def _stable_id(prefix, *parts):
    normalized = "\x1f".join(str(part or "").strip().casefold() for part in parts)
    return f"{prefix}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:20]}"


def _compact_text(value, limit=180):
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
