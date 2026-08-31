"""Durable regression coverage for the Feature D2 skill-package frontier."""

from src.workflow.production import ProductionRecommendationRequest
from src.workflow.role_scoring import derive_contextual_role_scores
from src.web.routes.api import QueryRequest


def _boss(**overrides):
    value = {
        "id": "boss:mimi",
        "name": "Mimi",
        "weak": [],
        "resist": [],
        "null": [],
        "absorb": [],
        "mechanic_tags": [],
        "required_counters": [],
    }
    value.update(overrides)
    return value


def _character(name="Aldo", **overrides):
    value = {"id": f"character:{name.casefold()}", "name": name}
    value.update(overrides)
    return value


def _skill(
    name,
    capabilities=(),
    *,
    family=None,
    rank=1,
    element="Neutral",
    state=None,
    slot="active_equipable",
    sa=False,
    **extra,
):
    value = {
        "id": f"skill:aldo:{name.casefold().replace(' ', '-')}",
        "character_name": "Aldo",
        "name": name,
        "element": element,
        "capabilities": list(capabilities),
        "skill_family_id": family or f"family:{name.casefold().replace(' ', '-')}",
        "upgrade_rank": rank,
        "slot_eligibility": slot,
        "requires_stellar_awakened": sa,
        "capability_artifact_version": "3.1.0",
        "capability_evidence_json": [
            {
                "kind": "capability",
                "value": capability,
                "review_decision": "approve",
                "source_id": f"rule:{capability}",
            }
            for capability in capabilities
        ],
    }
    if state:
        value["review_state"] = state
    value.update(extra)
    return value


def _entity(result):
    return next(item for item in result["entities"] if item["name"] == "Aldo")


def _derive(skills, *, points=None, character=None, boss=None):
    return derive_contextual_role_scores(
        boss=boss or _boss(),
        characters=[character or _character()],
        skills=skills,
        passives=[],
        sidekicks=[],
        stellar_awakened={},
        light_shadow_points=points or {},
    )


def test_legal_untagged_families_make_a_character_package_ready_without_coverage_credit():
    result = _derive([
        _skill("Proven Damage", ["direct_damage"]),
        _skill("Legal Filler One", capabilities=()),
        _skill("Legal Filler Two", capabilities=()),
    ])

    entity = _entity(result)
    package = entity["default_package"]

    assert entity["package_ready"] is True
    assert package["package_size"] == 3
    assert len(package["skill_family_ids"]) == 3
    assert {"skill:aldo:legal-filler-one", "skill:aldo:legal-filler-two"} <= set(package["untagged_skill_ids"])
    assert package["proven_capabilities"] == ["direct_damage"]
    assert package["role_scores"]["primary_damage"] > 0
    assert package["evidence"]["primary_damage"]


def test_family_and_dependency_rules_exclude_illegal_choices_before_package_selection():
    result = _derive([
        _skill("Damage I", ["direct_damage"], family="family:damage", rank=1),
        _skill("Damage II", ["direct_damage"], family="family:damage", rank=2),
        _skill("Ordinary Basic", family="family:basic", slot="ordinary_basic_attack"),
        _skill("Unavailable SA", family="family:sa", sa=True),
        _skill("Locked Manifest", family="family:manifest", requires_manifest="Manifest A", manifest_available=False),
        _skill("Filler", family="family:filler"),
        _skill("Replacement", family="family:replacement", slot="basic_attack_replacement"),
    ])

    entity = _entity(result)
    legal_ids = set(entity["default_package"]["skill_ids"])
    frontier = entity["skill_package_frontier"]

    assert frontier["legal_family_count"] == 3
    assert frontier["package_ready"] is True
    assert "skill:aldo:damage-ii" in legal_ids
    assert "skill:aldo:ordinary-basic" not in legal_ids
    assert "skill:aldo:unavailable-sa" not in legal_ids
    assert "skill:aldo:locked-manifest" not in legal_ids
    assert "skill:aldo:replacement" in legal_ids


def test_fourth_skill_requires_explicit_light_shadow_points_not_sa_or_item_policy():
    skills = [
        _skill(f"Skill {index}", ["direct_damage"] if index == 0 else (), family=f"family:{index}")
        for index in range(4)
    ]

    conservative = _entity(_derive(skills, points={"Aldo": 79}))
    expanded = _entity(_derive(skills, points={"Aldo": 80}))
    sa_only = _entity(_derive(skills, character={**_character(), "is_SA": True}))

    assert conservative["skill_slot_limit"] == 3
    assert conservative["default_package"]["package_size"] == 3
    assert expanded["skill_slot_limit"] == 4
    assert expanded["default_package"]["package_size"] == 4
    assert sa_only["skill_slot_limit"] == 3


def test_multi_role_frontier_is_bounded_distinct_and_not_dominated():
    skills = [
        _skill("Damage", ["direct_damage"], family="family:damage"),
        _skill("Zone", ["deploy_zone"], family="family:zone"),
        _skill("Heal", ["heal_hp"], family="family:heal"),
        _skill("Status Guard", ["grant_status_immunity"], family="family:status"),
        _skill("AF", ["af_combo_gain_up"], family="family:af"),
    ]
    result = _derive(
        skills,
        boss={**_boss(), "required_counters": ["grant_status_immunity"]},
    )
    options = _entity(result)["skill_packages"]

    assert 1 <= len(options) <= 3
    assert len({tuple(option["skill_family_ids"]) for option in options}) == len(options)
    for option in options:
        assert option["legal"] is True
        assert len(option["skill_family_ids"]) == len(set(option["skill_family_ids"]))
        assert set(option["skill_ids"]) & set(option["untagged_skill_ids"]) == set()
    for left in options:
        for right in options:
            if left is right:
                continue
            assert not (
                all(left["role_scores"][role] >= right["role_scores"][role] for role in result["role_dimensions"])
                and left["contextual_score"] >= right["contextual_score"]
                and (
                    left["contextual_score"] > right["contextual_score"]
                    or any(left["role_scores"][role] > right["role_scores"][role] for role in result["role_dimensions"])
                )
            )


def test_production_request_preserves_explicit_light_shadow_points_and_rejects_negative_values():
    request = ProductionRecommendationRequest(
        boss_id="Mimi",
        roster=["Aldo"],
        light_shadow_points={" Aldo ": 80},
    )

    assert request.light_shadow_points == {"Aldo": 80}

    try:
        ProductionRecommendationRequest(
            boss_id="Mimi",
            roster=["Aldo"],
            light_shadow_points={"Aldo": -1},
        )
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("negative Light/Shadow points must be rejected")


def test_api_request_carries_explicit_light_shadow_points_into_the_production_job_contract():
    request = QueryRequest(
        query="Prefer a stable package",
        roster=["Aldo"],
        mode="production",
        boss_id="Mimi",
        light_shadow_points={"Aldo": 80},
    )

    assert request.light_shadow_points == {"Aldo": 80}
