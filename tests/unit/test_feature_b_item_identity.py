"""Regression tests for Feature B item identity and cardinality contracts."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.etl.loader import audit_character_readiness, ensure_constraints, load_grastas, remove_collapsed_legacy_grastas
from src.etl.models import CharacterRow, GrastaRow
from src.workflow.legality import LegalityContext, LineupLegalityError, LineupModel, RosterInput, validate_lineup_legality


class RecordingSession:
    def __init__(self, calls, result=None):
        self.calls, self.result = calls, result

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return self.result


class RecordingDriver:
    def __init__(self, result=None):
        self.calls, self.result = [], result

    def session(self):
        return RecordingSession(self.calls, self.result)


def _grasta(**overrides):
    values = {
        "name": "Almighty Power", "category": "Attack", "tier": 3,
        "stats": "PWR/INT +10", "personality_req": "Dragon", "is_shareable": True,
        "source_url": "https://example.test/grasta", "obtain_text": "1: Reward",
        "acquisition_class": "unique", "max_theoretical_copies": 1,
    }
    values.update(overrides)
    return GrastaRow.model_validate(values)


def _hero(name, grastas):
    return {
        "name": name, "role": "role", "weapon": "available weapon", "armor": "available armor",
        "grastas": grastas, "recommended_skills": [], "recommended_passives": [],
        "upgrade_assumptions": ["Grasta compatibility assumed by fixture."],
    }


def _lineup(first_grastas, second_grastas=None):
    default = ["Power of Mind"] * 3
    return LineupModel.model_validate({
        "frontline": [_hero("Aldo", first_grastas), _hero("Ciel", second_grastas or default),
                      _hero("Miyu", default), _hero("Shion", default)],
        "reserve": [_hero("Feinne", default), _hero("Cyrus", default)],
        "main_sidekick": "Tetra", "sub_sidekick": "Korobo",
    })


def _context(**overrides):
    values = {
        "known_characters": {"Aldo", "Ciel", "Miyu", "Shion", "Feinne", "Cyrus"},
        "known_sidekicks": {"Tetra", "Korobo"}, "known_grastas": {"Power of Mind"},
    }
    values.update(overrides)
    return LegalityContext(**values)


def _roster():
    return RosterInput(owned_characters=["Ciel", "Miyu", "Shion"], owned_sidekicks=["Tetra", "Korobo"])


def test_exact_grasta_variants_have_stable_distinct_ids_and_display_names():
    dragon, eastern, reparsed = _grasta(personality_req="Dragon"), _grasta(personality_req="Eastern"), _grasta(personality_req="Dragon")
    assert dragon.grasta_id == reparsed.grasta_id
    assert dragon.grasta_id != eastern.grasta_id
    assert dragon.display_name == "Almighty Power (Dragon)"
    assert eastern.display_name == "Almighty Power (Eastern)"


def test_weapon_and_source_variants_participate_in_grasta_identity():
    sword = _grasta(name="Enhance if Max HP", personality_req=None, weapon_req="Sword", weapon_group=["Sword"])
    bow = _grasta(name="Enhance if Max HP", personality_req=None, weapon_req="Bow", weapon_group=["Bow"])
    proof_a = _grasta(name="Proof", category="VC", personality_req=None, source_variant="Aldo")
    proof_b = _grasta(name="Proof", category="VC", personality_req=None, source_variant="Guildna")
    assert sword.grasta_id != bow.grasta_id
    assert proof_a.grasta_id != proof_b.grasta_id


def test_character_alias_identity_preserves_full_style_name():
    values = {"name": "Akane (Alter),Blooming Blade", "element": "Fire", "weapon": "Katana",
              "light_shadow": "Shadow", "personalities": ["Eastern"],
              "detail_url": "https://example.test/Blooming_Blade"}
    character, reparsed = CharacterRow.model_validate(values), CharacterRow.model_validate(values)
    assert character.character_id == reparsed.character_id
    assert character.display_name == values["name"]
    assert {values["name"], "Akane (Alter)", "Blooming Blade", "Akane Alter"} <= set(character.aliases)


@pytest.mark.asyncio
async def test_grasta_loader_merges_by_id_and_keeps_variant_trait_edges_isolated():
    driver, dragon, eastern = RecordingDriver(), _grasta(personality_req="Dragon"), _grasta(personality_req="Eastern")
    await load_grastas(driver, [dragon, eastern])
    node_cypher, node_params = driver.calls[0]
    edge_cypher, edge_params = driver.calls[1]
    assert "MERGE (g:Grasta {grasta_id: row.grasta_id})" in node_cypher
    assert "MATCH (g:Grasta {grasta_id: row.grasta_id})" in edge_cypher
    assert {row["grasta_id"] for row in node_params["rows"]} == {dragon.grasta_id, eastern.grasta_id}
    assert {row["personality_req"] for row in edge_params["rows"]} == {"Dragon", "Eastern"}


@pytest.mark.asyncio
async def test_constraints_replace_name_only_grasta_identity():
    driver = RecordingDriver()
    await ensure_constraints(driver)
    statements = [cypher for cypher, _ in driver.calls]
    assert "DROP CONSTRAINT grasta_name IF EXISTS" in statements
    assert any("REQUIRE g.grasta_id IS UNIQUE" in cypher for cypher in statements)
    assert not any("REQUIRE g.name IS UNIQUE" in cypher for cypher in statements)


@pytest.mark.asyncio
async def test_legacy_cleanup_removes_only_nodes_without_exact_identity():
    result = MagicMock()
    result.single = AsyncMock(return_value={"removed": 7})
    driver = RecordingDriver(result=result)
    assert await remove_collapsed_legacy_grastas(driver) == 7
    cypher, params = driver.calls[0]
    assert params == {}
    assert "g.grasta_id IS NULL OR g.grasta_id = ''" in cypher
    assert "DETACH DELETE node" in cypher


@pytest.mark.asyncio
async def test_character_readiness_fails_for_missing_or_nonselectable_targets():
    driver = MagicMock()
    driver.execute_query = AsyncMock(return_value=([{"graph_names": ["Aldo", "Tetra"], "selectable_names": ["Aldo"]}], None, None))
    with pytest.raises(RuntimeError, match="Character coverage/readiness audit failed") as exc_info:
        await audit_character_readiness(driver, ["Aldo", "Tetra", "Akane (Alter),Blooming Blade"])
    assert "Akane (Alter),Blooming Blade" in str(exc_info.value)
    assert "Tetra" in str(exc_info.value)


def test_unique_exact_variant_cannot_be_reused_within_one_lineup():
    unique = "grasta:dragon"
    lineup = _lineup([unique, "Power of Mind", "Power of Mind"], [unique, "Power of Mind", "Power of Mind"])
    context = _context(known_grastas={"Power of Mind", unique}, grasta_copy_limits={unique: 1})
    with pytest.raises(LineupLegalityError, match="copy limit exceeded"):
        validate_lineup_legality(lineup, _roster(), context)


def test_cardinality_allocation_resets_between_alternative_lineups():
    unique = "grasta:dragon"
    context = _context(known_grastas={"Power of Mind", unique}, grasta_copy_limits={unique: 1})
    first = _lineup([unique, "Power of Mind", "Power of Mind"])
    second = _lineup(["Power of Mind"] * 3, [unique, "Power of Mind", "Power of Mind"])
    assert validate_lineup_legality(first, _roster(), context) == first
    assert validate_lineup_legality(second, _roster(), context) == second


def test_distinct_compatible_personality_variants_can_coexist_on_one_character():
    dragon, eastern = "grasta:dragon", "grasta:eastern"
    lineup = _lineup([dragon, eastern, "Power of Mind"])
    context = _context(known_grastas={"Power of Mind", dragon, eastern},
                       character_traits={"Aldo": {"Dragon", "Eastern"}},
                       grasta_personality_reqs={dragon: "Dragon", eastern: "Eastern"},
                       grasta_copy_limits={dragon: 1, eastern: 1})
    assert validate_lineup_legality(lineup, _roster(), context) == lineup


def test_repeatable_weapon_compatible_pain_grasta_is_allowed_with_status_source():
    pain = "grasta:pain-sword"
    lineup = _lineup([pain, pain, pain])
    lineup.frontline[0].recommended_skills = ["Pain Edge"]
    context = _context(known_grastas={"Power of Mind", pain}, character_weapons={"Aldo": "Sword"},
                       character_skills={"Aldo": {"Pain Edge"}}, grasta_weapon_reqs={pain: "Sword"})
    assert validate_lineup_legality(lineup, _roster(), context) == lineup
