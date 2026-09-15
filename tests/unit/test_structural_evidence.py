"""Permanent regressions for source-faithful structural evidence."""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from src.etl.structural_evidence import (
    SourceIdentity,
    TraversalLimits,
    audit_reference_topology,
    build_catalog_structural_sidecar,
    parse_grid_document,
    parse_grid_units,
    parse_table_row_unit,
    resolve_bounded_references,
    select_traversal_limits,
)


FIXTURE_ROOT = Path("tests/fixtures/structural")
MANIFEST_PATH = Path("src/etl/structural_fixture_manifest.json")
EVIDENCE_PATH = Path("artifacts/evidence/feature_c1_structural_evidence.json")


def _fixture_unit(case: dict, entity_kind: str | None = None):
    path = Path(case["fixture"])
    source = SourceIdentity(
        source_kind=case["kind"],
        source_url=case["source_url"],
        capture_sha256=case["source_capture_sha256"],
        capture_path=path.as_posix(),
    )
    return parse_grid_units(
        path.read_text(encoding="utf-8"),
        source=source,
        entity_kind=entity_kind or case["kind"],
        entity_name=case["entity"],
    )


def test_fixture_manifest_pins_named_source_and_fixture_identities():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    names = {case["entity"] for case in manifest["cases"]}
    assert {
        "Darunis",
        "Denny",
        "Iphi",
        "Alma (Another Style)",
        "Anabel (Extra Style)",
        "Shigure (Extra Style)",
        "Tetra (Another Style)",
        "Kumos (Another Style)",
    } <= names
    for case in manifest["cases"]:
        fixture = Path(case["fixture"])
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == case["fixture_sha256"]
        assert len(case["source_capture_sha256"]) == 64
    iphi = next(case for case in manifest["cases"] if case["entity"] == "Iphi")
    assert iphi["required_definitions"] == ["Blood Contract", "Lunatic (Iphi)"]
    assert all(row["admitted_boss"] is False for row in manifest["supplemental_witnesses"])


def test_simple_kits_keep_a_single_plain_block_without_invented_nesting():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for name in ("Darunis", "Denny"):
        case = next(row for row in manifest["cases"] if row["entity"] == name)
        units = _fixture_unit(case)
        assert len(units) == 1
        assert [block.kind for block in units[0].blocks] == ["root"]
        assert units[0].blocks[0].ancestry == []


def test_nested_lists_links_icons_fragments_and_occurrences_remain_traceable():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    case = next(row for row in manifest["cases"] if row["entity"] == "Iphi")
    units = _fixture_unit(case)
    ritual = next(unit for unit in units if unit.title == "Blood Ritual")
    assert [block.ancestry for block in ritual.blocks] == [
        [],
        ["unordered_list[0]"],
        ["unordered_list[0]", "unordered_list[0]"],
        ["unordered_list[1]"],
    ]
    tokens = [token for block in ritual.blocks for token in block.tokens]
    assert any(token.kind == "icon" and token.icon_identity == "Blood Contract Icon.png" for token in tokens)
    lunatic = next(token for token in tokens if token.title == "Lunatic (Iphi)")
    assert lunatic.fragment == "Activation"
    assert lunatic.location.startswith(f"sha256:{case['source_capture_sha256']}/grid[0]/block[")

    outcomes = resolve_bounded_references(
        [ritual], units, TraversalLimits(max_depth=2, max_pages_per_root=4)
    )
    resolved_pages = {row["canonical_page_url"] for row in outcomes if row["status"] == "resolved"}
    assert "https://anothereden.wiki/w/Blood_Contract" in resolved_pages
    assert "https://anothereden.wiki/w/Lunatic_(Iphi)" in resolved_pages
    assert len({row["occurrence_id"] for row in outcomes}) == len(outcomes)


def test_character_and_sidekick_adapters_share_blocks_without_changing_ownership():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for name in ("Alma (Another Style)", "Anabel (Extra Style)", "Shigure (Extra Style)"):
        units = _fixture_unit(next(row for row in manifest["cases"] if row["entity"] == name))
        assert {unit.entity_kind for unit in units} == {"character"}
        assert any(unit.references() for unit in units)
        if name == "Alma (Another Style)":
            assert any(unit.section == "Stellar Awakened Skills" for unit in units)
    for name in ("Tetra (Another Style)", "Kumos (Another Style)"):
        units = _fixture_unit(
            next(row for row in manifest["cases"] if row["entity"] == name), "sidekick"
        )
        expected_types = {"sidekick_charge", "sidekick_aura"}
        if name == "Tetra (Another Style)":
            expected_types.add("sidekick_auto")
        assert {unit.record_type for unit in units} == expected_types
        assert all(unit.entity_name == name for unit in units)


def test_boss_equipment_and_grasta_rows_use_ordered_table_cells():
    html = (FIXTURE_ROOT / "shared_rows.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    source = SourceIdentity("cross_entity", "https://anothereden.wiki/w/", "a" * 64, "fixture")
    kinds = [("boss", "boss_mechanic"), ("equipment", "equipment_effect"), ("grasta", "grasta_effect")]
    for row_id, record_type in kinds:
        unit = parse_table_row_unit(
            soup.select_one(f"#{row_id}"),
            source=source,
            entity_kind=row_id,
            entity_name=row_id,
            record_type=record_type,
            source_fact_id=f"fixture:{row_id}",
        )
        assert [block.order for block in unit.blocks] == [0, 1, 2]
        assert [block.ancestry[-1] for block in unit.blocks] == ["cell[0]", "cell[1]", "cell[2]"]


def test_malformed_grids_and_each_traversal_terminal_are_explicit():
    source = SourceIdentity("character", "https://example.test/w/Root", "b" * 64, "fixture")
    malformed = '<div class="character-skill-grid-container"><div class="skill-name">Broken</div></div>'
    units, diagnostics = parse_grid_document(
        malformed, source=source, entity_kind="character", entity_name="Broken"
    )
    assert units == []
    assert diagnostics[0]["reason"] == "missing_description"

    html = """
    <article title="Active Skills">
      <div class="character-skill-grid-container"><div class="skill-name">Root</div><div class="skill-description">Attack and see <a href="/w/Child">Child</a>, <a href="/w/Missing">Missing</a>, and <a href="/w/Lore">Lore</a>.</div></div>
      <div class="character-skill-grid-container"><div class="skill-name">Child</div><div class="skill-description">Damage; see <a href="/w/Grandchild">Grandchild</a>.</div></div>
      <div class="character-skill-grid-container"><div class="skill-name">Grandchild</div><div class="skill-description">Party attack effect.</div></div>
      <div class="character-skill-grid-container"><div class="skill-name">Lore</div><div class="skill-description">Biography and story summary.</div></div>
    </article>
    """
    graph = parse_grid_units(html, source=source, entity_kind="character", entity_name="Fixture")
    root = next(unit for unit in graph if unit.title == "Root")
    outcomes = resolve_bounded_references(
        [root], graph, TraversalLimits(max_depth=1, max_pages_per_root=2, max_frontier_per_root=8)
    )
    statuses = {row["status"] for row in outcomes}
    assert {"resolved", "access_failure", "excluded", "depth_budget_exhausted"} <= statuses
    page_limited = resolve_bounded_references(
        [root], graph, TraversalLimits(max_depth=3, max_pages_per_root=1, max_frontier_per_root=8)
    )
    assert "page_budget_exhausted" in {row["status"] for row in page_limited}


def test_topology_is_audited_before_bounded_limits_are_selected():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    units = []
    for case in manifest["cases"]:
        if case["kind"] in {"character", "sidekick"}:
            units.extend(_fixture_unit(case, case["kind"]))
    topology = audit_reference_topology(units)
    limits = select_traversal_limits(topology)
    assert topology["unit_count"] == len(units)
    assert limits.max_depth >= 1
    assert limits.max_pages_per_root >= 2


def test_accepted_evidence_preserves_legal_kit_and_authority_boundaries():
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert evidence["legal_kit"]["canonical_identity_count"] == 367
    assert evidence["legal_kit"]["complete_receipt_count"] == 367
    assert evidence["coverage"]["source_fact_denominator"] == 5036
    assert (
        evidence["coverage"]["bound_source_fact_count"]
        + evidence["coverage"]["unresolved_source_fact_count"]
        == 5036
    )
    assert evidence["authority"]["generated_capability_authority"] is False
    assert evidence["authority"]["definitions_grant_capabilities"] is False
    assert evidence["retention"]["generated_sidecar"] == "ignored"
    assert (
        hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
        == evidence["accepted_source_snapshot"]["fixture_manifest_sha256"]
    )


def test_full_catalog_replay_matches_accepted_snapshot_when_captures_are_present():
    if not Path("data/raw/characters/darunis.html").exists():
        return
    report = build_catalog_structural_sidecar()
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert (
        report["source_identity"]["catalog_fingerprint"]
        == evidence["accepted_source_snapshot"]["catalog_fingerprint"]
    )
    assert report["sidecar_digest"] == evidence["accepted_source_snapshot"]["structural_sidecar_digest"]
    assert report["coverage"]["bound_source_fact_count"] == evidence["coverage"]["bound_source_fact_count"]
    assert report["coverage"]["unresolved_source_fact_count"] == evidence["coverage"]["unresolved_source_fact_count"]
    assert (
        report["reference_resolution"]["status_distribution"]
        == evidence["traversal_boundary"]["status_distribution"]
    )
