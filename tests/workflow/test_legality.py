"""Feature B tests for roster and party legality contracts."""

import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock

from src.workflow.legality import (
    LegalityContext,
    LineupLegalityError,
    LineupModel,
    RosterInput,
    build_roster_input,
    collect_legality_context,
    validate_lineup_legality,
)


def _hero(name, *, skills=None, passives=None, assumptions=None, weapon="available weapon", armor="available armor", grastas=None):
    return {
        "name": name,
        "role": "role",
        "weapon": weapon,
        "armor": armor,
        "grastas": grastas or ["Power of Mind", "Power of Mind", "Power of Mind"],
        "recommended_skills": skills or [],
        "recommended_passives": passives or [],
        "upgrade_assumptions": ["Grasta compatibility assumed by fixture."] if assumptions is None else assumptions,
    }


def _lineup(*, names=None, main_sidekick="Tetra", sub_sidekick="Korobo", **overrides):
    names = names or ["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"]
    data = {
        "frontline": [_hero(name) for name in names[:4]],
        "reserve": [_hero(name) for name in names[4:]],
        "main_sidekick": main_sidekick,
        "sub_sidekick": sub_sidekick,
    }
    data.update(overrides)
    return LineupModel.model_validate(data)


def _context(
    *,
    heroes=None,
    sidekicks=None,
    weapons=None,
    traits=None,
    skills=None,
    passives=None,
    gated_skills=None,
    gated_passives=None,
    known_grastas=None,
    grasta_reqs=None,
    assumed_sidekicks=None,
):
    return LegalityContext(
        known_characters=set(heroes or ["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"]),
        known_sidekicks=set(sidekicks or ["Tetra", "Korobo"]),
        character_weapons=weapons or {},
        character_traits=traits or {},
        character_skills=skills or {},
        character_passives=passives or {},
        sa_gated_skills=gated_skills or {},
        sa_gated_passives=gated_passives or {},
        known_grastas=set(known_grastas or ["Power of Mind"]),
        grasta_personality_reqs=grasta_reqs or {},
        assumed_available_sidekicks=set(assumed_sidekicks or []),
    )


class TestRosterInput:
    def test_roster_input_dedupes_and_preserves_f2p_augmentation(self):
        roster = RosterInput(owned_characters=["Ciel", "Ciel"], owned_sidekicks=["Tetra", "Tetra"])

        assert roster.owned_characters == ["Ciel"]
        assert roster.owned_sidekicks == ["Tetra"]
        assert "Ciel" in roster.available_characters
        assert "Aldo" in roster.available_characters

    @pytest.mark.asyncio
    async def test_build_roster_input_normalizes_characters_sidekicks_and_sa_state(self):
        driver = MagicMock()
        driver.execute_query = AsyncMock(side_effect=[
            ([{"canonical": "Aldo"}], None, None),
            ([{"canonical": "Ciel"}], None, None),
            ([{"canonical": "Tetra"}], None, None),
            ([{"canonical": "Aldo"}], None, None),
        ])

        roster = await build_roster_input(
            driver,
            owned_characters=["aldo", "ciel"],
            owned_sidekicks=["tetra"],
            stellar_awakened={"aldo": True},
        )

        assert roster.owned_characters == ["Aldo", "Ciel"]
        assert roster.owned_sidekicks == ["Tetra"]
        assert roster.stellar_awakened == {"Aldo": True}


class TestLineupShape:
    def test_accepts_exactly_four_frontline_and_two_reserve(self):
        lineup = _lineup()

        assert len(lineup.frontline) == 4
        assert len(lineup.reserve) == 2

    def test_rejects_invalid_frontline_shape(self):
        with pytest.raises(ValidationError):
            _lineup(frontline=[_hero("Aldo"), _hero("Ciel"), _hero("Miyu")])

    def test_rejects_invalid_reserve_shape(self):
        with pytest.raises(ValidationError):
            _lineup(reserve=[_hero("Feinne")])

    def test_rejects_duplicate_heroes(self):
        with pytest.raises(ValidationError, match="duplicate heroes"):
            _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Aldo", "Cyrus"])

    def test_rejects_same_sidekick_in_both_slots(self):
        with pytest.raises(ValidationError, match="main_sidekick and sub_sidekick"):
            _lineup(main_sidekick="Tetra", sub_sidekick="Tetra")

    def test_rejects_selected_sidekick_as_hero(self):
        with pytest.raises(ValidationError, match="sidekicks cannot occupy hero slots"):
            _lineup(names=["Tetra", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"], main_sidekick="Tetra")


class TestFeatureBBuildPolicy:
    def test_rejects_missing_weapon_or_armor_contract_fields(self):
        hero = _hero("Aldo")
        hero.pop("weapon")

        with pytest.raises(ValidationError, match="weapon"):
            _lineup(frontline=[hero, _hero("Ciel"), _hero("Miyu"), _hero("Shion")])

    def test_rejects_non_three_grasta_slots(self):
        with pytest.raises(ValidationError, match="grastas"):
            _lineup(frontline=[
                _hero("Aldo", grastas=["Power of Mind", "Power of Mind"]),
                _hero("Ciel"),
                _hero("Miyu"),
                _hero("Shion"),
            ])

    def test_rejects_duplicate_specific_weapon_within_one_lineup(self):
        with pytest.raises(ValidationError, match="specific weapons cannot repeat"):
            _lineup(frontline=[
                _hero("Aldo", weapon="Lunar Sword"),
                _hero("Ciel", weapon="Lunar Sword"),
                _hero("Miyu", weapon="available weapon"),
                _hero("Shion", weapon="available weapon"),
            ])

    def test_allows_repeated_weapon_and_armor_categories(self):
        lineup = _lineup(frontline=[
            _hero("Aldo", weapon="Sword", armor="Bracelet"),
            _hero("Ciel", weapon="Sword", armor="Bracelet"),
            _hero("Miyu", weapon="Sword", armor="Bracelet"),
            _hero("Shion", weapon="Sword", armor="Bracelet"),
        ])

        assert [hero.weapon for hero in lineup.frontline] == ["Sword"] * 4
        assert [hero.armor for hero in lineup.frontline] == ["Bracelet"] * 4

    def test_allows_reused_grasta_copies(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", grastas=["Power of Mind", "Power of Mind", "Power of Mind"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])

        result = validate_lineup_legality(lineup, roster, _context())

        assert result.frontline[0].grastas == ["Power of Mind", "Power of Mind", "Power of Mind"]

    def test_accepts_personality_grasta_when_character_has_required_trait(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", grastas=["Power of Fire", "Power of Fire", "Power of Fire"], assumptions=[]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(
            traits={"Aldo": {"Guts"}},
            known_grastas=["Power of Mind", "Power of Fire"],
            grasta_reqs={"Power of Fire": "Guts"},
        )

        result = validate_lineup_legality(lineup, roster, context)

        assert result == lineup

    def test_rejects_personality_grasta_when_required_trait_is_missing(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", grastas=["Power of Fire", "Power of Fire", "Power of Fire"], assumptions=[]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(known_grastas=["Power of Mind", "Power of Fire"], grasta_reqs={"Power of Fire": "Guts"})

        with pytest.raises(LineupLegalityError, match="lacks required trait"):
            validate_lineup_legality(lineup, roster, context)

    def test_rejects_weapon_type_grasta_when_character_weapon_mismatches(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", grastas=["Sword Power Grasta", "Sword Power Grasta", "Sword Power Grasta"], assumptions=[]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(
            weapons={"Aldo": "Bow"},
            known_grastas=["Power of Mind", "Sword Power Grasta"],
        )

        with pytest.raises(LineupLegalityError, match="character weapon is Bow"):
            validate_lineup_legality(lineup, roster, context)

    def test_rejects_unverifiable_grasta_without_caveat(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", grastas=["Mystery Grasta", "Mystery Grasta", "Mystery Grasta"], assumptions=[]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])

        with pytest.raises(LineupLegalityError, match="unverifiable Grasta assumption"):
            validate_lineup_legality(lineup, roster, _context())

    def test_rejects_pain_grasta_plan_without_pain_or_poison_source(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(
            build_notes=["Damage assumes Pain Grasta multiplier."],
            frontline=[
                _hero("Aldo", grastas=["Pain Grasta", "Pain Grasta", "Pain Grasta"], assumptions=["Pain Grasta compatibility assumed."]),
                _hero("Ciel"),
                _hero("Miyu"),
                _hero("Shion"),
            ],
        )
        context = _context(known_grastas=["Power of Mind", "Pain Grasta"])

        with pytest.raises(LineupLegalityError, match="pain/poison-dependent build assumptions"):
            validate_lineup_legality(lineup, roster, context)

    def test_accepts_pain_grasta_plan_with_skill_source(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(
            build_notes=["Damage assumes Pain Grasta multiplier."],
            frontline=[
                _hero("Aldo", skills=["Poison Edge"], grastas=["Pain Grasta", "Pain Grasta", "Pain Grasta"], assumptions=["Pain Grasta compatibility assumed; Poison Edge applies poison."]),
                _hero("Ciel"),
                _hero("Miyu"),
                _hero("Shion"),
            ],
        )
        context = _context(known_grastas=["Power of Mind", "Pain Grasta"], skills={"Aldo": {"Poison Edge"}})

        result = validate_lineup_legality(lineup, roster, context)

        assert result == lineup


class TestLineupLegality:
    def test_accepts_owned_and_f2p_available_heroes(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"])

        result = validate_lineup_legality(lineup, roster, _context())

        assert result == lineup

    def test_rejects_unowned_non_f2p_hero(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"])

        with pytest.raises(LineupLegalityError, match="not owned"):
            validate_lineup_legality(lineup, roster, _context())

    def test_rejects_hallucinated_character(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion", "Phantom"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Phantom"])

        with pytest.raises(LineupLegalityError, match="unknown or hallucinated character"):
            validate_lineup_legality(lineup, roster, _context())

    def test_rejects_sidekick_name_in_hero_slot(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion", "Tetra"], owned_sidekicks=["Korobo"])
        lineup = _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Tetra"], main_sidekick=None)
        context = _context(heroes=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Tetra"], sidekicks=["Tetra", "Korobo"])

        with pytest.raises(LineupLegalityError, match="sidekick cannot occupy a hero slot"):
            validate_lineup_legality(lineup, roster, context)

    def test_rejects_unowned_sidekick(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra"])
        lineup = _lineup(main_sidekick="Tetra", sub_sidekick="Korobo")

        with pytest.raises(LineupLegalityError, match="sub_sidekick is not owned"):
            validate_lineup_legality(lineup, roster, _context())

    def test_accepts_assumption_available_sidekick(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra"])
        lineup = _lineup(main_sidekick="Tetra", sub_sidekick="Korobo")
        context = _context(assumed_sidekicks=["Korobo"])

        result = validate_lineup_legality(lineup, roster, context)

        assert result == lineup

    def test_rejects_unsupported_skill(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", skills=["Dragon God Slash"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])

        with pytest.raises(LineupLegalityError, match="does not have recommended skill"):
            validate_lineup_legality(lineup, roster, _context(skills={"Aldo": {"X Slash"}}))

    def test_accepts_supported_skill(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", skills=["X Slash"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])

        result = validate_lineup_legality(lineup, roster, _context(skills={"Aldo": {"X Slash"}}))

        assert result == lineup

    def test_rejects_known_not_awakened_sa_gated_skill(self):
        roster = RosterInput(
            owned_characters=["Ciel", "Miyu", "Shion"],
            stellar_awakened={"Aldo": False},
            owned_sidekicks=["Tetra", "Korobo"],
        )
        lineup = _lineup(frontline=[
            _hero("Aldo", skills=["Stellar Slash"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(skills={"Aldo": {"Stellar Slash"}}, gated_skills={"Aldo": {"Stellar Slash"}})

        with pytest.raises(LineupLegalityError, match="cannot use SA-gated skill"):
            validate_lineup_legality(lineup, roster, context)

    def test_rejects_unknown_sa_gated_skill_without_upgrade_assumption(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", skills=["Stellar Slash"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(skills={"Aldo": {"Stellar Slash"}}, gated_skills={"Aldo": {"Stellar Slash"}})

        with pytest.raises(LineupLegalityError, match="SA state is unknown"):
            validate_lineup_legality(lineup, roster, context)

    def test_accepts_unknown_sa_gated_skill_when_labeled_as_upgrade_assumption(self):
        roster = RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])
        lineup = _lineup(frontline=[
            _hero("Aldo", skills=["Stellar Slash"], assumptions=["Requires Stellar Slash after Stellar Awakening upgrade", "Grasta compatibility assumed by fixture."]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(skills={"Aldo": {"Stellar Slash"}}, gated_skills={"Aldo": {"Stellar Slash"}})

        result = validate_lineup_legality(lineup, roster, context)

        assert result == lineup

    def test_rejects_known_not_awakened_sa_gated_passive(self):
        roster = RosterInput(
            owned_characters=["Ciel", "Miyu", "Shion"],
            stellar_awakened={"Aldo": "not_awakened"},
            owned_sidekicks=["Tetra", "Korobo"],
        )
        lineup = _lineup(frontline=[
            _hero("Aldo", passives=["Stellar Burst"]),
            _hero("Ciel"),
            _hero("Miyu"),
            _hero("Shion"),
        ])
        context = _context(
            passives={"Aldo": {"Stellar Burst"}},
            gated_passives={"Aldo": {"Stellar Burst"}},
        )

        with pytest.raises(LineupLegalityError, match="cannot use SA-gated passive"):
            validate_lineup_legality(lineup, roster, context)


class TestGraphContextCollection:
    @pytest.mark.asyncio
    async def test_collect_legality_context_looks_up_hero_names_as_possible_sidekicks(self):
        driver = MagicMock()
        driver.execute_query = AsyncMock(return_value=([
            {
                "known_characters": ["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Tetra"],
                "known_sidekicks": ["Tetra"],
                "skill_rows": [],
                "passive_rows": [],
            }
        ], None, None))
        lineup = _lineup(names=["Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Tetra"], main_sidekick=None, sub_sidekick=None)

        context = await collect_legality_context(driver, lineup)

        assert context.known_sidekicks == {"Tetra"}
        kwargs = driver.execute_query.call_args.kwargs
        assert "Tetra" in kwargs["sidekick_lookup_names"]
