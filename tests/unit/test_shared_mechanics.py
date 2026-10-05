"""Bounded shared-mechanic resolution and ownership regressions for C2-R3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from src.etl.shared_mechanics import (
    MechanicAlias,
    MechanicSourceAnchor,
    SharedMechanicEntry,
    SharedMechanicRegistry,
    load_shared_mechanic_registry,
    resolve_shared_mechanics,
)
from src.etl.structural_evidence import (
    SourceIdentity,
    StructuralBlock,
    StructuralToken,
    StructuralUnit,
    parse_grid_document,
)


ROOT = Path(__file__).parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/structural/c2_r3_shared_mechanics.html"
SOURCE_MAP_PATH = ROOT / "tests/fixtures/source_fidelity/c2_r3_shared_mechanics.json"
TETRA_FIXTURE_PATH = ROOT / "tests/fixtures/structural/c2_r2_tetra_sidekick.html"
SOURCE_MAP = json.loads(SOURCE_MAP_PATH.read_text(encoding="utf-8"))


def _development_unit(witness_id: str, *, entity_kind: str = "character") -> StructuralUnit:
    fixture_bytes = FIXTURE_PATH.read_bytes()
    assert hashlib.sha256(fixture_bytes).hexdigest() == SOURCE_MAP["fixture_sha256"]
    metadata = next(row for row in SOURCE_MAP["records"] if row["witness_id"] == witness_id)
    soup = BeautifulSoup(fixture_bytes, "html.parser")
    container = soup.select_one(metadata["selector"])
    assert container is not None
    source = SourceIdentity(
        source_kind=metadata["source_kind"],
        source_url=metadata["source_url"],
        capture_sha256=metadata["capture_sha256"],
        capture_path=str(FIXTURE_PATH),
    )
    units, diagnostics = parse_grid_document(
        str(container),
        source=source,
        entity_kind=entity_kind,
        entity_name=metadata["entity_name"],
    )
    assert not diagnostics
    assert len(units) == 1
    units[0].source_fact_id = metadata["record_id"]
    return units[0]


def _tetra_units() -> list[StructuralUnit]:
    capture_sha256 = "7df15e6e8c0d199d5f5a1d084e607fecee900c084bdfef3b3356ebcff461f70d"
    source = SourceIdentity(
        source_kind="development_witness",
        source_url="https://anothereden.wiki/w/Tetra_(Another_Style)",
        capture_sha256=capture_sha256,
        capture_path=str(TETRA_FIXTURE_PATH),
    )
    units, diagnostics = parse_grid_document(
        TETRA_FIXTURE_PATH.read_text(encoding="utf-8"),
        source=source,
        entity_kind="sidekick",
        entity_name="Tetra (Another Style)",
    )
    assert not diagnostics
    for unit in units:
        unit.source_fact_id = "sidekick_skill:development-tetra-charge"
    return units


def _synthetic_unit(token: StructuralToken) -> StructuralUnit:
    return StructuralUnit(
        unit_id="unit:test",
        source=SourceIdentity("development_fixture", "https://example.invalid", "a" * 64, "fixture"),
        entity_kind="character",
        entity_name="Test Character",
        record_type="active_skill",
        title="Test Skill",
        section="Skills",
        source_fact_id="skill:test-parent",
        family_id=None,
        legacy_description=token.text,
        blocks=[StructuralBlock("description", 0, [], "fixture/block[0]", [token])],
        definition_page_url="https://example.invalid/w/Test_Skill",
    )


def test_registry_is_bounded_deduplicated_and_source_anchored():
    registry = load_shared_mechanic_registry()
    assert len(registry.entries) == 14
    assert len(registry.by_id) == len(registry.entries)
    assert len(registry.by_id["shared:another-zone"].source_anchors) == 2
    assert registry.by_id["shared:another-zone"].definition_status == "available"
    assert registry.by_id["shared:another-zone"].definition_source_anchor_id == "zones-another-zone-definition"
    assert registry.by_id["shared:prayer"].definition_status == "unavailable"

    mapping = {row["witness_id"]: row for row in SOURCE_MAP["records"]}
    for entry in registry.entries:
        for anchor in entry.source_anchors:
            if anchor.witness_id in mapping:
                source = mapping[anchor.witness_id]
                assert anchor.source_capture_sha256 == source["capture_sha256"]
                assert anchor.source_slice_sha256 == source["source_slice_sha256"]
                assert anchor.source_fact_id == source["record_id"]
                if anchor.anchor_id.endswith("-skill-link"):
                    assert anchor.source_location == source["skill_name_link_location"]


def test_explicit_href_and_allowlisted_text_keep_distinct_provenance():
    unit = _development_unit("development-ciel-lunatic-charge")
    results = resolve_shared_mechanics(unit)

    explicit = [row for row in results if row.mention == "Lunatic"]
    assert len(explicit) == 1
    assert explicit[0].mechanic_id == "shared:lunatic"
    assert explicit[0].resolution_basis == "explicit_href"
    assert explicit[0].resolution_status == "resolved"

    skill_link = [row for row in results if row.mention == "Lunatic - Charge"]
    assert len(skill_link) == 1
    assert skill_link[0].mechanic_id == "shared:lunatic-charge"
    assert skill_link[0].resolution_basis == "explicit_href"
    assert skill_link[0].alias_source_anchor_id == "ciel-lunatic-charge-skill-link"

    charge = [row for row in results if row.mention == "Charge"]
    assert charge
    assert all(row.mechanic_id == "shared:lunatic-charge" for row in charge)
    assert all(row.resolution_basis == "allowlisted_name" for row in charge)
    assert all(row.definition_status == "unavailable" for row in charge)
    assert all(row.parent_source_fact_id == unit.source_fact_id for row in charge)
    assert all("Ciel (Alter)" in row.parent_owner_name for row in charge)


def test_icon_alias_and_global_mechanic_resolution_do_not_move_parent_payload():
    alma = _development_unit("development-alma-kaleidoscope")
    alma_rows = resolve_shared_mechanics(alma)
    linked = [row for row in alma_rows if row.mechanic_id == "shared:barrier-piercing"]
    assert any(row.resolution_basis == "explicit_href" for row in linked)
    assert any(row.resolution_basis == "allowlisted_icon" for row in linked)
    assert all(row.definition_status == "unavailable" for row in linked)

    another_zone = _development_unit("development-claude-es-another-zone")
    zone_rows = resolve_shared_mechanics(another_zone)
    zone = [row for row in zone_rows if row.mechanic_id == "shared:another-zone"]
    assert zone
    assert all(row.resolution_basis == "explicit_href" for row in zone)
    assert all(row.alias_source_anchor_id == "claude-another-zone-skill-link" for row in zone)
    assert zone[0].parent_source_fact_id == another_zone.source_fact_id
    assert zone[0].parent_owner_name == "Claude (Extra Style)"
    assert zone[0].definition_status == "available"
    assert another_zone.legacy_description
    assert all("payload" not in row.as_dict() for row in zone)
    assert all("capability" not in row.as_dict() for row in zone)


def test_sidekick_charge_and_lunatic_charge_resolve_to_separate_identities():
    tetra_rows = [row for unit in _tetra_units() for row in resolve_shared_mechanics(unit)]
    sidekick_charge = [row for row in tetra_rows if row.mention == "Charge"]
    lunatic_rows = [
        row
        for row in resolve_shared_mechanics(_development_unit("development-ciel-lunatic-charge"))
        if row.mention == "Charge"
    ]
    assert sidekick_charge
    assert all(row.mechanic_id == "shared:sidekick-charge" for row in sidekick_charge)
    assert all(row.parent_owner_kind == "sidekick" for row in sidekick_charge)
    assert lunatic_rows
    assert all(row.mechanic_id == "shared:lunatic-charge" for row in lunatic_rows)


def test_unknown_ambiguous_and_unregistered_explicit_links_remain_unresolved():
    registry = load_shared_mechanic_registry()
    unknown = StructuralToken("text", 0, "Unlisted mechanic", "fixture/token[0]")
    unknown_result = registry.resolve_token(unknown, _synthetic_unit(unknown))[0]
    assert unknown_result.resolution_status == "unresolved"
    assert unknown_result.reason == "unknown_name"

    prose = StructuralToken(
        "text",
        1,
        "An explanatory sentence mentions Kaleido in passing",
        "fixture/token[1]",
    )
    prose_result = registry.resolve_token(prose, _synthetic_unit(prose))[0]
    assert prose_result.resolution_status == "unresolved"
    assert prose_result.reason == "unknown_name"

    anchor = MechanicSourceAnchor(
        anchor_id="synthetic",
        source_kind="development_fixture",
        source_url="https://example.invalid/source",
        source_capture_sha256="a" * 64,
        source_location="fixture/block[0]",
    )
    candidates = SharedMechanicRegistry(
        (
            SharedMechanicEntry(
                "shared:test-charge-a", "test", "unavailable", "",
                (MechanicAlias("name", "Charge", "synthetic"),), (anchor,),
            ),
            SharedMechanicEntry(
                "shared:test-charge-b", "test", "unavailable", "",
                (MechanicAlias("name", "Charge", "synthetic"),), (anchor,),
            ),
        ),
        "test-registry",
    )
    charge_token = StructuralToken("text", 2, "Charge", "fixture/token[2]")
    ambiguous = candidates.resolve_token(charge_token, None)[0]
    assert ambiguous.resolution_status == "ambiguous"
    assert ambiguous.candidate_mechanic_ids == ("shared:test-charge-a", "shared:test-charge-b")

    linked_label = StructuralToken(
        "reference",
        3,
        "Charge",
        "fixture/token[3]",
        href="/w/Another_Zone",
        canonical_page_url="https://anothereden.wiki/w/Unregistered_Page",
    )
    explicit_result = registry.resolve_token(linked_label, _synthetic_unit(linked_label))[0]
    assert explicit_result.resolution_status == "unresolved"
    assert explicit_result.resolution_basis == "unresolved"
    assert explicit_result.reason == "explicit_href_not_allowlisted"
