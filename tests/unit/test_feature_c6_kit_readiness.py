"""C6 legal-kit, receipt, and replay-boundary regressions."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from src.etl.kit_readiness import (
    CharacterKitReceipt,
    build_receipt,
    validate_catalog_payload,
)
from src.etl.loader import load_kit_receipts, load_skills
from src.etl.models import CharacterRow, PassiveSkillRow, SkillRow
from src.etl.scraper import parse_character_passive_skills, parse_character_skills


class FakeSession:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))


class FakeDriver:
    def __init__(self):
        self.fake_session = FakeSession()

    def session(self):
        return self.fake_session


def character(name="Aldo"):
    return CharacterRow(
        name=name,
        element="Fire",
        weapon="Sword",
        light_shadow="Light",
        personalities=["Sword"],
        detail_url=f"https://example.test/{name}",
    )


def skill(name, *, description="", section="Active Skills", skill_type="Slash"):
    return SkillRow(
        character_name="Aldo",
        name=name,
        description=description,
        section=section,
        skill_type=skill_type,
        source_url="https://example.test/Aldo",
    )


def test_skill_family_and_slot_contract_excludes_basic_attacks_and_passives():
    ordinary = skill("Sword Swing", description="Basic attack: Slash attack on a single enemy (S)")
    active = skill("Sword Swing", description="Slash attack on a single enemy (M)")
    passive = skill("Power Level", section="Passive Skills", skill_type="Passive", description="Power +10%")
    another_zone = skill("Another Zone", skill_type="Zone Buff", description="Awakens the active zone.")

    assert ordinary.slot_eligibility == "ordinary_basic_attack"
    assert active.slot_eligibility == "active_equipable"
    assert ordinary.skill_family_id == active.skill_family_id
    assert passive.slot_eligibility == "not_equipable"
    assert another_zone.slot_eligibility == "not_equipable"


def test_passive_grid_rows_are_not_loaded_as_legal_active_skills():
    soup = BeautifulSoup(
        """
        <article title="Active Skills">
          <div class="character-skill-grid-container">
            <div class="skill-name">Strike</div>
            <div class="character-skill-element-type"><div class="lower-grid">Slash</div></div>
            <div class="skill-description">Slash attack.</div>
          </div>
        </article>
        <article title="Passive Skills">
          <div class="character-skill-grid-container">
            <div class="skill-name">Power Level</div>
            <div class="character-skill-element-type"><div class="lower-grid">Passive</div></div>
            <div class="skill-description">Power +10%.</div>
          </div>
        </article>
        """,
        "html.parser",
    )

    active = parse_character_skills(soup, "Aldo")
    passives = parse_character_passive_skills(soup, "Aldo")

    assert [row.name for row in active] == ["Strike"]
    assert [row.name for row in passives] == ["Power Level"]
    assert passives[0].passive_skill_id


def test_receipt_keeps_legal_untagged_fillers_but_requires_three_families():
    rows = [
        skill("Basic", description="Basic attack: Slash attack."),
        skill("One", description="Slash attack."),
        skill("Two", description="Buff the party."),
        skill("Three", description="Heal the party."),
    ]
    receipt, normalized, _ = build_receipt(
        character(),
        rows,
        [PassiveSkillRow(character_name="Aldo", name="Passive", description="Power +10%")],
        source_artifact_fingerprint="source-a",
    )

    assert receipt.overall_state == "complete"
    assert receipt.active_skill_family_count == 3
    assert all(row.capabilities == [] for row in normalized)
    assert receipt.source_artifact_fingerprint == "source-a"


def test_receipt_reports_source_specific_incomplete_kit():
    receipt, _, _ = build_receipt(
        character("Incomplete"),
        [skill("Only", description="Buff the party.")],
        [],
        source_artifact_fingerprint="source-incomplete",
    )

    assert receipt.overall_state == "failed"
    assert receipt.active_skill_family_count == 1
    assert receipt.diagnostics[0].code == "insufficient_active_skill_families"


def test_durable_catalog_records_exact_corpus_and_is_ready():
    payload = json.loads(Path("src/etl/kit_catalog.json").read_text(encoding="utf-8"))
    report = validate_catalog_payload(payload)

    assert report["receipt_count"] == 367
    assert report["complete_count"] == 367
    assert report["insufficient_family_characters"] == []
    assert report["ready"] is True


def test_catalog_validation_rejects_receipt_drift():
    payload = json.loads(Path("src/etl/kit_catalog.json").read_text(encoding="utf-8"))
    mutated = deepcopy(payload)
    mutated["characters"][0]["receipt"]["active_skill_family_count"] += 1

    with pytest.raises(ValueError, match="receipt drifted"):
        validate_catalog_payload(mutated)


@pytest.mark.asyncio
async def test_kit_loader_persists_receipt_and_skill_family_fields():
    driver = FakeDriver()
    row = skill("Meteor", description="Fire attack.")
    receipt = CharacterKitReceipt(
        character_id=character().character_id,
        character_name="Aldo",
        display_name="Aldo",
        source_url="https://example.test/Aldo",
        source_artifact_fingerprint="source-a",
        source_revision="rev-a",
        active_skill_state="complete",
        active_skill_count=3,
        active_skill_family_count=3,
        active_skill_family_ids=[row.skill_family_id],
        passive_state="verified_absent",
        passive_count=0,
        stellar_awakening_state="not_applicable",
        dependency_state="complete",
        overall_state="complete",
    )

    await load_skills(driver, [row])
    await load_kit_receipts(driver, [receipt])

    skill_query, skill_params = driver.fake_session.calls[0]
    receipt_query, receipt_params = driver.fake_session.calls[1]
    assert "s.skill_family_id = row.skill_family_id" in skill_query
    assert skill_params["rows"][0]["slot_eligibility"] == "active_equipable"
    assert "CharacterKitReceipt" in receipt_query
    assert receipt_params["rows"][0]["diagnostics_json"] == "[]"
