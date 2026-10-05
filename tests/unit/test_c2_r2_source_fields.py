"""Development-source regressions for C2-R2 ETL and variant identity fixes."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

import src.etl.source_fidelity as source_fidelity
from src.etl.models import SidekickRow, stable_skill_family_id
from src.etl.scraper import _aura_source_fields, parse_sidekick_detail
from src.etl.source_fidelity import _fixture_record_from_character
from src.etl.structural_evidence import (
    SourceIdentity,
    TraversalLimits,
    extract_sidekick_aura_fields,
    extract_sidekick_charge_operations,
    parse_grid_units,
    resolve_bounded_references,
)


ROOT = Path("tests/fixtures/structural")
SOURCE_FIXTURE = Path("tests/fixtures/source_fidelity/c2_r2_source_corrections.json")


def _source_cases() -> dict[str, dict]:
    fixture = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["authority"] == "approved development and known-regression sources only"
    return {Path(row["fixture"]).name: row for row in fixture["records"]}


def _catalog_facts_by_id() -> dict[str, dict]:
    catalog = json.loads(Path("src/etl/kit_catalog.json").read_text(encoding="utf-8"))
    return {
        str(fact.get("skill_id") or fact.get("passive_skill_id")): fact
        for record in catalog["characters"]
        for fact in [*record.get("skills", []), *record.get("passive_skills", [])]
    }


def _units(filename: str):
    case = _source_cases()[filename]
    path = Path(case["fixture"])
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == case["fixture_sha256"]
    source = SourceIdentity(
        source_kind=case["source_kind"],
        source_url=f"https://anothereden.wiki/w/{case['source_entity'].replace(' ', '_')}",
        capture_sha256=case["fixture_sha256"],
        capture_path=path.as_posix(),
    )
    return case, parse_grid_units(
        raw.decode("utf-8"),
        source=source,
        entity_kind=case["source_kind"],
        entity_name=case["source_entity"],
    )


def test_development_fixture_manifest_keeps_original_capture_and_fact_identity():
    cases = _source_cases()
    assert len(cases) == 6
    assert all(len(row["source_capture_sha256"]) == 64 for row in cases.values())
    assert all(row["source_fact_ids"] and row["source_witness_ids"] for row in cases.values())
    assert cases["c2_r2_tetra_sidekick.html"]["source_capture_sha256"] == (
        "7df15e6e8c0d199d5f5a1d084e607fecee900c084bdfef3b3356ebcff461f70d"
    )


def test_sidekick_charge_gain_consumption_and_availability_are_separate():
    _case, units = _units("c2_r2_tetra_sidekick.html")
    auto_unit = next(unit for unit in units if unit.title == "Spark Rebellion")
    charge_unit = next(unit for unit in units if unit.title == "Ruincarnation")
    source = BeautifulSoup((ROOT / "c2_r2_tetra_sidekick.html").read_text(encoding="utf-8"), "html.parser")
    row = parse_sidekick_detail(
        source,
        SidekickRow(name="Tetra (Another Style)", source_url="https://anothereden.wiki/w/Tetra_(Another_Style)"),
    )

    assert auto_unit.record_type == "sidekick_auto"
    assert charge_unit.record_type == "sidekick_charge"
    assert row.auto_skills[0].charge_cost is None
    assert row.charge_skills[0].charge_cost == 8

    auto_operations = extract_sidekick_charge_operations(auto_unit)
    assert [(event["operation"], event["amount"]) for event in auto_operations] == [("gain", 1)]
    assert auto_operations[0]["condition"] == "When the HP of all party members at front is <=80%"
    assert auto_operations[0]["resource_owner"] == {"kind": "sidekick", "name": "Tetra (Another Style)"}
    assert auto_operations[0]["source_fact_id"] is None
    assert auto_operations[0]["unit"] == "Charge"
    assert not any(event["operation"] == "action_availability_threshold" for event in auto_operations)

    charge_operations = extract_sidekick_charge_operations(charge_unit)
    consumption = next(event for event in charge_operations if event["operation"] == "consumption")
    availability = next(event for event in charge_operations if event["operation"] == "action_availability_threshold")
    assert consumption["amount"] == 8
    assert consumption["condition"] is None
    assert availability["amount"] is None
    assert availability["threshold_state"] == "charged"
    assert availability["unit"] == "Charge"
    assert consumption["capture_sha256"] == charge_unit.source.capture_sha256
    assert consumption["source_location"].endswith("/block[0]")


def test_aura_condition_uses_source_blocks_and_keeps_effect_text_separate():
    _case, units = _units("c2_r2_hameow_aura.html")
    aura_unit = next(unit for unit in units if unit.title == "Cross Resonance")
    source = BeautifulSoup((ROOT / "c2_r2_hameow_aura.html").read_text(encoding="utf-8"), "html.parser")
    row = parse_sidekick_detail(source, SidekickRow(name="Hameow", source_url="https://anothereden.wiki/w/Hameow"))

    assert row.auras[0].activation_condition == "When enemy receives slash or magic damage"
    assert row.auras[0].effect_text == "Damage dealt by all party members +10%"
    fields = extract_sidekick_aura_fields(aura_unit)
    assert fields["status"] == "source_blocks_separated"
    assert fields["activation_condition"] == row.auras[0].activation_condition
    assert fields["effect_text"] == row.auras[0].effect_text
    assert fields["condition_source_location"] != fields["effect_source_locations"][0]

    arbitrary = BeautifulSoup(
        "<div><b>Activation condition:</b> When all party members have Power above 50% and Physical resistance below 25%"
        "<ul><li>Grant a barrier</li></ul></div>",
        "html.parser",
    ).div
    condition, effect = _aura_source_fields(arbitrary)
    assert condition == "When all party members have Power above 50% and Physical resistance below 25%"
    assert effect == "Grant a barrier"

    unbounded = BeautifulSoup(
        "<div><b>Activation condition:</b> When an enemy receives damage; Damage dealt by allies rises</div>",
        "html.parser",
    ).div
    condition, effect = _aura_source_fields(unbounded)
    assert condition is None
    assert effect == "Activation condition: When an enemy receives damage; Damage dealt by allies rises"


def test_explicit_same_page_href_alias_resolves_only_to_captured_child():
    case, units = _units("c2_r2_anabel_prayer_alias.html")
    parent = next(unit for unit in units if unit.title == "Knight's Pride")
    child = next(unit for unit in units if unit.title == "Knight's Pride - Prayer")
    parent.source_fact_id, child.source_fact_id = case["source_fact_ids"]
    prayer_url = next(token.canonical_page_url for token in parent.references() if "Prayer" in token.text)
    assert prayer_url in child.explicit_definition_aliases

    without_aliases = resolve_bounded_references(
        [parent], units, TraversalLimits(max_depth=2, max_pages_per_root=4)
    )
    assert next(row for row in without_aliases if row["canonical_page_url"] == prayer_url)["status"] == "access_failure"

    with_aliases = resolve_bounded_references(
        [parent], units, TraversalLimits(max_depth=2, max_pages_per_root=4), include_explicit_aliases=True
    )
    resolved = next(row for row in with_aliases if row["canonical_page_url"] == prayer_url)
    assert resolved["status"] == "resolved"
    assert resolved["resolution_basis"] == "explicit_source_href_alias"
    assert resolved["target_unit_id"] == child.unit_id
    assert resolved["target_source_fact_id"] == "skill:eac6950dc058daaf9941"

    missing_child = resolve_bounded_references(
        [parent], [parent], TraversalLimits(max_depth=2, max_pages_per_root=4), include_explicit_aliases=True
    )
    missing = next(row for row in missing_child if row["canonical_page_url"] == prayer_url)
    assert missing["status"] == "access_failure"
    assert missing["reason"] == "no_admitted_capture"


def test_source_fidelity_binds_alias_target_to_existing_fact_id(tmp_path):
    case, _parsed_units = _units("c2_r2_anabel_prayer_alias.html")
    capture = (ROOT / "c2_r2_anabel_prayer_alias.html").read_bytes()
    fixture_sha = hashlib.sha256(capture).hexdigest()
    catalog = json.loads(Path("src/etl/kit_catalog.json").read_text(encoding="utf-8"))
    record = next(
        row
        for row in catalog["characters"]
        if row["receipt"]["character_name"] == case["source_entity"]
    )
    record = copy.deepcopy(record)
    record["receipt"]["source_revision"] = fixture_sha
    source_dir = tmp_path
    (source_dir / "anabel_extra_style.html").write_bytes(capture)
    witness = {
        "witness_id": "known-anabel-prayer-child",
        "entity_name": case["source_entity"],
        "fact_id": "skill:438aa7e1d0e071c14c43",
        "source_capture_sha256": fixture_sha,
    }

    resolved = _fixture_record_from_character(
        witness,
        {str(record["receipt"]["character_id"]): record},
        raw_character_dir=source_dir,
    )

    assert resolved["source_identity_status"] == "passed"
    assert resolved["source_variant_identity"]["family_id"] == _catalog_facts_by_id()[
        witness["fact_id"]
    ]["skill_family_id"]
    child = next(
        row
        for row in resolved["captured_definition_resolutions"]
        if row.get("resolution_basis") == "explicit_source_href_alias"
    )
    assert child["status"] == "resolved"
    assert child["target_source_fact_id"] == case["source_fact_ids"][1]


def test_known_oracle_child_resolution_requires_the_reviewed_fact_id(tmp_path, monkeypatch):
    case, _parsed_units = _units("c2_r2_anabel_prayer_alias.html")
    capture = (ROOT / "c2_r2_anabel_prayer_alias.html").read_bytes()
    fixture_sha = hashlib.sha256(capture).hexdigest()
    catalog = json.loads(Path("src/etl/kit_catalog.json").read_text(encoding="utf-8"))
    record = next(
        row
        for row in catalog["characters"]
        if row["receipt"]["character_name"] == case["source_entity"]
    )
    record = copy.deepcopy(record)
    record["receipt"]["source_revision"] = fixture_sha
    (tmp_path / "anabel_extra_style.html").write_bytes(capture)
    witness = next(
        row
        for row in json.loads(Path("src/etl/source_fidelity_manifest.json").read_text(encoding="utf-8"))["known_regressions"]
        if row["witness_id"] == "known-anabel-prayer-child"
    )
    witness = {**witness, "source_capture_sha256": fixture_sha}
    monkeypatch.setattr(source_fidelity, "SOURCE_SLICE_FIXTURE_PATH", tmp_path / "no-slice-fixture.json")

    def run(expected_target: str) -> str:
        result = source_fidelity.evaluate_oracle(
            {"known_regressions": [witness], "development_witnesses": [witness]},
            {"characters": [record]},
            {
                "witnesses": [
                    {
                        "witness_id": witness["witness_id"],
                        "dimension_overrides": {
                            "child_definition_resolution": {
                                "status": "passed",
                                "reason": "development fixture expects a captured Prayer child",
                                "target_source_fact_id": expected_target,
                            }
                        },
                    }
                ]
            },
            raw_character_dir=tmp_path,
        )
        return result["known_regressions"]["witnesses"][0]["dimensions"]["child_definition_resolution"]["status"]

    assert run(case["source_fact_ids"][1]) == "passed"
    assert run("skill:unadmitted-target") == "failed"


def test_stellar_variants_keep_one_family_and_source_parameters():
    case, units = _units("c2_r2_anabel_stellar_variants.html")
    aegis = [unit for unit in units if unit.title == "Aegis Boon"]
    family = stable_skill_family_id("Anabel", "Aegis Boon")
    catalog_fact = _catalog_facts_by_id()[case["source_fact_ids"][0]]
    assert catalog_fact["skill_family_id"] == family
    assert {unit.variant_identity()["family_id"] for unit in aegis} == {family}
    for unit in aegis:
        unit.family_id = family
    by_key = {unit.variant_key: unit for unit in aegis}

    assert set(by_key) == {"stellar_normal", "stellar_enhanced"}
    assert by_key["stellar_normal"].variant_identity()["family_id"] == family
    assert by_key["stellar_enhanced"].variant_identity()["family_id"] == family
    assert by_key["stellar_normal"].variant_identity()["identity_key"] != by_key["stellar_enhanced"].variant_identity()["identity_key"]
    assert by_key["stellar_normal"].progression_unlock == "Stellar Awakening"
    assert by_key["stellar_enhanced"].progression_unlock == "Stellar Awakening"
    assert "reduced to 60" in by_key["stellar_normal"].legacy_description
    assert "reduced to 50" in by_key["stellar_enhanced"].legacy_description
    assert "source_variant" not in by_key["stellar_normal"].as_dict()
    assert by_key["stellar_normal"].as_dict(include_r2_source_identity=True)["source_variant"]["variant_key"] == "stellar_normal"


def test_manifest_progression_and_equipment_requirements_remain_distinct():
    case, units = _units("c2_r2_bertrand_progression_variants.html")
    lances = [unit for unit in units if unit.title == "Guardian Lance"]
    family = _catalog_facts_by_id()[case["source_fact_ids"][0]]["skill_family_id"]
    for unit in lances:
        unit.family_id = family
    by_key = {unit.variant_key: unit for unit in lances}

    assert set(by_key) == {"base", "manifest_equipped", "true_manifest"}
    assert all(unit.variant_identity()["family_id"] == family for unit in lances)
    assert by_key["base"].source_variant_label == "Normal"
    assert by_key["manifest_equipped"].requires_equipment == "maxed Manifest"
    assert by_key["manifest_equipped"].progression_unlock is None
    assert by_key["true_manifest"].progression_unlock == "True Manifest"
    assert by_key["true_manifest"].requires_equipment is None


def test_state_selected_replacements_get_parent_family_keys_and_not_equipable_status():
    case, units = _units("c2_r2_cerius_replacements.html")
    parents = [unit for unit in units if unit.title == "Flashing Fletch"]
    family = _catalog_facts_by_id()[case["source_fact_ids"][0]]["skill_family_id"]
    assert parents[0].variant_identity()["family_id"] == family
    for parent in parents:
        parent.family_id = family
    outcomes = resolve_bounded_references(
        parents,
        units,
        TraversalLimits(max_depth=2, max_pages_per_root=4),
        include_explicit_aliases=True,
    )
    replacements = [row["variant_relationship"] for row in outcomes if row.get("variant_relationship")]

    assert {(row["condition"], row["target_variant_key"]) for row in replacements} >= {
        ("Armor Piercer mode", "stellar_normal"),
        ("Armor Piercer mode", "stellar_enhanced"),
        ("Full Round mode", "stellar_normal"),
        ("Full Round mode", "stellar_enhanced"),
    }
    assert all(row["type"] == "state_selected_replacement" for row in replacements)
    assert all(row["family_id"] == family for row in replacements)
    assert all(row["independently_equipable"] is False for row in replacements)
    assert all(row["variant_key"].startswith("state_replacement:") for row in replacements)
    assert len({row["family_id"] for row in replacements}) == 1


def test_variant_heading_without_selector_stays_unresolved():
    source = SourceIdentity("character", "https://anothereden.wiki/w/Example", "a" * 64, "fixture")
    html = (
        '<article title="Stellar Awakened Skills"><div class="character-skill-grid-container">'
        '<div class="skill-name"><a href="/w/Example_Skill">Example Skill</a></div>'
        '<div class="skill-description">Earth attack on all enemies.</div></div></article>'
    )
    unit = parse_grid_units(html, source=source, entity_kind="character", entity_name="Example")[0]
    assert unit.variant_key == "unresolved"
    assert unit.variant_identity()["basis"] == "unresolved"
