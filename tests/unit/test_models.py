"""Unit tests for Pydantic ETL validation models.

Requirements covered:
- DATA-02: Pydantic strict vs lenient mode validation
"""
import pytest
from unittest.mock import patch
from pydantic import ValidationError


def test_character_strict_mode():
    """Verify that an invalid CharacterRow raises ValidationError in strict mode."""
    import src.etl.constants as constants
    with patch.object(constants, 'STRICT', True):
        from src.etl.models import CharacterRow
        with pytest.raises((ValidationError, Exception)):
            CharacterRow.model_validate({"name": None, "element": "Wind", "weapon": "Sword",
                                         "light_shadow": "Light", "personalities": "Cool"})


def test_character_strict_mode_valid():
    """Verify that a valid CharacterRow is constructed correctly in strict mode."""
    from src.etl.models import CharacterRow
    row = CharacterRow.model_validate({
        "name": "Aldo",
        "element": "Wind",
        "weapon": "Sword",
        "light_shadow": "Light",
        "personalities": "Straw Dummy,Cool",
    })
    assert row.name == "Aldo"
    assert row.element == "Wind"
    assert row.weapon == "Sword"
    assert row.light_shadow == "Light"
    assert row.personalities == ["Straw Dummy", "Cool"]


def test_character_personalities_list_passthrough():
    """Verify that personalities already as a list are accepted."""
    from src.etl.models import CharacterRow
    row = CharacterRow.model_validate({
        "name": "Aldo",
        "element": "Wind",
        "weapon": "Sword",
        "light_shadow": "Light",
        "personalities": ["Cool", "Wild"],
    })
    assert row.personalities == ["Cool", "Wild"]


def test_character_lenient_mode():
    """Verify that an invalid CharacterRow is skipped (returns None) in lenient mode."""
    import src.etl.constants as constants
    import src.etl.models as models_module
    with patch.object(constants, 'STRICT', False):
        with patch.object(models_module, 'STRICT', False):
            from src.etl.models import parse_character
            result = parse_character({"name": None, "element": "Wind", "weapon": "Sword",
                                      "light_shadow": "Light", "personalities": "Cool"})
            assert result is None


def test_grasta_vc_no_personality_req():
    """Verify that a VC GrastaRow has personality_req=None."""
    from src.etl.models import GrastaRow
    row = GrastaRow.model_validate({
        "name": "Proof of Courage",
        "category": "VC",
        "tier": "3",
        "stats": "ATK+10%",
        "personality_req": None,
        "is_shareable": "0",
    })
    assert row.category == "VC"
    assert row.personality_req is None


def test_grasta_vc_parse_forces_personality_none():
    """parse_grasta forces personality_req=None for VC even if input has a value."""
    from src.etl.models import parse_grasta
    result = parse_grasta({
        "name": "Proof of Courage",
        "category": "VC",
        "tier": 3,
        "stats": "ATK+10%",
        "personality_req": "Straw Dummy",
        "is_shareable": False,
    })
    assert result is not None
    assert result.personality_req is None


def test_grasta_non_vc_with_personality_req():
    """Non-VC grasta with personality_req retains it."""
    from src.etl.models import GrastaRow
    row = GrastaRow.model_validate({
        "name": "Courageous Strike",
        "category": "Attack",
        "tier": 2,
        "stats": "ATK+5%",
        "personality_req": "Straw Dummy",
        "is_shareable": True,
    })
    assert row.personality_req == "Straw Dummy"


def test_grasta_tier_coercion():
    """Verify tier is coerced to int from string."""
    from src.etl.models import GrastaRow
    row = GrastaRow.model_validate({
        "name": "Test Grasta",
        "category": "Life",
        "tier": "2",
        "stats": "HP+10%",
        "is_shareable": "1",
    })
    assert row.tier == 2
    assert row.is_shareable is True


def test_ore_row_valid():
    """Verify OreRow model_validate works with correct data."""
    from src.etl.models import OreRow
    row = OreRow.model_validate({
        "name": "AF After Victory Ore",
        "stats": "Restore AF Gauge by 10% on victory",
        "source": "Fog People Vendor (5000 Fog Medals)",
    })
    assert row.name == "AF After Victory Ore"
    assert "AF" in row.stats
    assert "Fog" in row.source


def test_parse_ore_valid():
    """Verify parse_ore returns OreRow on valid data."""
    from src.etl.models import parse_ore
    result = parse_ore({
        "name": "Speed Ore",
        "stats": "SPD+5%",
        "source": "Shop",
    })
    assert result is not None
    assert result.name == "Speed Ore"


def test_grasta_effect_tags_are_derived_from_existing_text():
    """Feature C: Grasta tags are lightweight retrieval metadata, not damage math."""
    from src.etl.models import TAG_DERIVATION_RULE, GrastaRow

    row = GrastaRow.model_validate({
        "name": "Fire Slash Pain Grasta",
        "category": "Attack",
        "tier": "3",
        "stats": "PWR +10 Fire slash damage when target has Pain",
        "personality_req": "Sword",
        "is_shareable": "1",
    })

    assert row.effect_tags == [
        "category:attack",
        "tier:3",
        "element:fire",
        "attack:slash",
        "status:pain",
        "combat:damage",
        "stat:pwr",
    ]
    assert row.effect_tag_derivation == TAG_DERIVATION_RULE
    assert not any(tag.startswith("multiplier:") for tag in row.effect_tags)


def test_grasta_effect_tags_can_be_explicit_without_rederivation():
    """Feature C: replayed parsed artifacts can preserve already-derived tags."""
    from src.etl.models import GrastaRow

    row = GrastaRow.model_validate({
        "name": "Manual Tag Grasta",
        "category": "Support",
        "tier": 2,
        "stats": "INT +10",
        "personality_req": None,
        "is_shareable": True,
        "effect_tags": "custom:one, custom:two",
        "effect_tag_derivation": "fixture supplied",
    })

    assert row.effect_tags == ["custom:one", "custom:two"]
    assert row.effect_tag_derivation == "fixture supplied"


def test_ore_effect_tags_are_derived_with_derivation_clarity():
    """Feature C: Ore tags are derived from name/stats and remain standalone metadata."""
    from src.etl.models import TAG_DERIVATION_RULE, OreRow

    row = OreRow.model_validate({
        "name": "AF Speed Ore",
        "stats": "Restore AF Gauge by 10% on victory and SPD +5",
        "source": "Fog People Vendor",
    })

    assert row.effect_tags == ["category:ore", "combat:af", "stat:spd"]
    assert row.effect_tag_derivation == TAG_DERIVATION_RULE


def test_equipment_row_captures_weapon_baseline_without_optimizer_fields():
    """Feature D: weapons keep baseline attack context and source attribution."""
    from src.etl.models import EquipmentRow

    row = EquipmentRow.model_validate({
        "name": "Lunar Sword",
        "equipment_slot": "weapon",
        "category": "Sword",
        "level": "60",
        "attack": "185",
        "magic_attack": "22",
        "effect_text": "Type attack +10%",
        "obtain_text": "Crafted from Moonlight Forest materials",
        "source_url": "https://anothereden.wiki/w/Weapons",
    })

    assert row.name == "Lunar Sword"
    assert row.equipment_slot == "weapon"
    assert row.category == "Sword"
    assert row.level == 60
    assert row.attack == 185
    assert row.magic_attack == 22
    assert row.defense is None
    assert row.magic_defense is None
    assert row.effect_text == "Type attack +10%"
    assert row.obtain_text.startswith("Crafted")
    assert row.source_url.endswith("/Weapons")
    assert not hasattr(row, "rank_score")
    assert not hasattr(row, "best_in_slot")


def test_equipment_row_captures_armor_baseline_defenses():
    """Feature D: armor keeps survivability context without damage math."""
    from src.etl.models import EquipmentRow

    row = EquipmentRow.model_validate({
        "name": "Dream Ring",
        "equipment_slot": "armor",
        "category": "Ring",
        "level": "55",
        "defense": "138",
        "magic_defense": "166",
        "effect_text": "Restore HP after battle",
        "obtain_text": "Treasure chest",
        "source_url": "https://anothereden.wiki/w/Armor",
    })

    assert row.equipment_slot == "armor"
    assert row.defense == 138
    assert row.magic_defense == 166
    assert row.attack is None
    assert row.magic_attack is None
    assert row.schema_version


def test_parse_equipment_rejects_unknown_slot():
    """Feature D: equipment slot is deliberately limited to weapon or armor."""
    from src.etl.models import EquipmentRow

    with pytest.raises(ValidationError):
        EquipmentRow.model_validate({
            "name": "Mystery Item",
            "equipment_slot": "accessory",
            "source_url": "https://example.test/Equipment",
        })
