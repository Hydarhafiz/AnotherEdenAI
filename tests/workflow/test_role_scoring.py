"""Durable regression coverage for deterministic contextual role scoring."""

from copy import deepcopy

from src.workflow.role_scoring import ROLE_DIMENSIONS, derive_contextual_role_scores


def boss(**overrides):
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


def fact(owner, name, capabilities, *, element="Neutral", fact_id=None, sa=False, state=None, evidence=True):
    value = {
        "id": fact_id or f"skill:{owner}:{name}",
        "character_name": owner,
        "name": name,
        "element": element,
        "capabilities": capabilities,
        "requires_stellar_awakened": sa,
        "capability_artifact_version": "3.1.0",
    }
    if state:
        value["review_state"] = state
    if evidence:
        value["capability_evidence_json"] = [
            {"kind": "capability", "value": capability, "review_decision": "approve", "source_id": f"rule:{capability}"}
            for capability in capabilities
        ]
    return value


def character(name):
    return {"id": f"character:{name.casefold()}", "name": name}


def entity(result, name):
    return next(value for value in result["entities"] if value["name"] == name and value["entity_type"] == "character")


def test_hard_filters_reject_null_absorb_and_missing_primary_damage_before_role_pools():
    result = derive_contextual_role_scores(
        boss=boss(null=["Fire"], absorb=["Water"]),
        characters=[character("NullFire"), character("AbsorbWater"), character("Utility"), character("NoSetup"), {**character("ItemIllegal"), "item_legal": False}, character("Neutral")],
        skills=[
            fact("NullFire", "Flame", ["direct_damage"], element="Fire"),
            fact("AbsorbWater", "Wave", ["direct_damage"], element="Water"),
            fact("Utility", "Heal", ["heal_hp"]),
            {**fact("NoSetup", "Blocked Setup", ["direct_damage"]), "setup_satisfied": False},
            fact("ItemIllegal", "Legal Damage", ["direct_damage"]),
            fact("Neutral", "Slash", ["direct_damage"], element="Neutral"),
        ],
        passives=[], sidekicks=[], stellar_awakened={},
    )

    assert entity(result, "NullFire")["rejection_reasons"] == ["primary_damage.null_or_absorb"]
    assert entity(result, "AbsorbWater")["rejection_reasons"] == ["primary_damage.null_or_absorb"]
    assert entity(result, "Utility")["eligible"] is True
    assert entity(result, "NoSetup")["eligible"] is True
    assert entity(result, "ItemIllegal")["eligible"] is False
    assert [row["entity_id"] for row in result["role_pools"]["primary_damage"]] == ["character:neutral"]


def test_boss_counter_exceptions_preserve_required_counters_beyond_top_eight():
    characters = [character(f"Hero{index}") for index in range(9)]
    skills = [
        fact(hero["name"], "Damage", ["direct_damage", "grant_status_immunity"], fact_id=f"skill:{index}")
        for index, hero in enumerate(characters)
    ]

    result = derive_contextual_role_scores(
        boss=boss(required_counters=["grant_status_immunity"]),
        characters=characters, skills=skills, passives=[], sidekicks=[], stellar_awakened={},
    )

    pool = result["role_pools"]["boss_counter"]
    assert len(pool) == 9
    assert [row["entity_id"] for row in pool][-1] == "character:hero8"
    assert pool[-1]["counter_exception"] is True


def test_fixed_dimensions_are_backend_owned_and_vary_with_sa_boss_and_placement():
    skills = [
        fact("Aldo", "Neutral Slash", ["direct_damage"], element="Neutral"),
        fact("Aldo", "Stellar AF", ["af_damage_up"], sa=True),
    ]
    sidekick = {
        "id": "sidekick:moke", "name": "Moke",
        "skills": [{
            "id": "sidekick-skill:moke", "name": "Main Guard", "availability": "main_only",
            "capabilities": ["damage_reduction"],
            "capability_evidence_json": [{"kind": "capability", "value": "damage_reduction", "review_decision": "approve"}],
        }],
        "auras": [{
            "id": "sidekick-aura:moke", "name": "Sub MP", "availability": "main_or_sub",
            "capabilities": ["recover_mp"],
            "capability_evidence_json": [{"kind": "capability", "value": "recover_mp", "review_decision": "approve"}],
        }],
    }
    unawakened = derive_contextual_role_scores(
        boss=boss(), characters=[character("Aldo")], skills=skills, passives=[], sidekicks=[sidekick], stellar_awakened={"Aldo": False},
    )
    awakened = derive_contextual_role_scores(
        boss=boss(required_counters=["af_damage_up"]), characters=[character("Aldo")], skills=skills, passives=[], sidekicks=[sidekick], stellar_awakened={"Aldo": True},
    )

    assert awakened["role_dimensions"] == list(ROLE_DIMENSIONS)
    assert set(entity(awakened, "Aldo")["role_scores"]) == set(ROLE_DIMENSIONS)
    assert entity(awakened, "Aldo")["role_scores"]["af_support"] > entity(unawakened, "Aldo")["role_scores"]["af_support"]
    main = next(value for value in awakened["entities"] if value["id"] == "sidekick:moke:main")
    sub = next(value for value in awakened["entities"] if value["id"] == "sidekick:moke:sub")
    assert main["role_scores"]["defense_mitigation"] > sub["role_scores"]["defense_mitigation"]
    assert main["role_scores"] != sub["role_scores"]
    assert sub["role_scores"]["mp_sustain"] > 0
    assert all(not key.startswith("ai_") for key in awakened["entities"][0])


def test_non_proven_and_dependency_only_facts_never_create_coverage_or_role_evidence():
    result = derive_contextual_role_scores(
        boss=boss(),
        characters=[character("Safe")],
        skills=[
            fact("Safe", "Damage", ["direct_damage"]),
            fact("Safe", "Candidate Heal", ["heal_hp"], state="candidate"),
            fact("Safe", "Rejected Guard", ["guard"], state="rejected"),
            fact("Safe", "Ambiguous MP", ["recover_mp"], state="ambiguous"),
            {"id": "skill:Safe:dependency", "character_name": "Safe", "name": "Dependency", "dependencies": ["requires_zone"]},
        ],
        passives=[], sidekicks=[], stellar_awakened={},
    )

    scores = entity(result, "Safe")["role_scores"]
    assert scores["recovery_protection"] == scores["tank_control"] == scores["mp_sustain"] == 0
    assert entity(result, "Safe")["evidence"]["recovery_protection"] == []


def test_shortlists_and_default_packages_are_available_bounded_and_reproducible():
    skills = [
        fact("Aldo", f"Skill{index}", ["direct_damage", "outgoing_damage_up"], fact_id=f"skill:aldo:{index}", sa=index == 6)
        for index in range(7)
    ]
    kwargs = {
        "boss": boss(weak=["Fire"]), "characters": [character("Aldo")], "skills": skills,
        "passives": [], "sidekicks": [], "stellar_awakened": {"Aldo": False},
        "policy_version": "feature-d-test-v1",
    }

    first = derive_contextual_role_scores(**kwargs)
    second = derive_contextual_role_scores(**deepcopy(kwargs))
    aldo = entity(first, "Aldo")

    assert first == second
    assert first["policy_version"] == "feature-d-test-v1"
    assert first["artifact_versions"] == ["3.1.0"]
    assert len(aldo["skill_shortlists"]["primary_damage"]) == 6
    assert "skill:aldo:6" not in {row["skill_id"] for row in aldo["skill_shortlists"]["primary_damage"]}
    assert 3 <= aldo["default_package"]["package_size"] <= 4
    assert len(aldo["default_package"]["skill_ids"]) == aldo["default_package"]["package_size"]
