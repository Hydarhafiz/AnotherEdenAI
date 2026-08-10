"""Feature G1 corpus, source-boundary, and cached weak-boss contract tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from src.etl.models import SuperbossIndexRow
from src.etl.superboss_manifest import manifest_records, proposed_live_fetch_records, validate_superboss_manifest
from src.etl.scraper import parse_superboss_detail
from src.workflow.candidates import _prepare_typed_candidates
from src.workflow.production import ProductionRequestError, ProductionRecommendationRequest, ProductionRetrievalService


ROOT = Path(__file__).parents[2]
MANIFEST_PATH = ROOT / "src" / "etl" / "superboss_manifest.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "superbosses" / "cached_weak_expected.json"
LIVE_EXPECTED_PATH = ROOT / "tests" / "fixtures" / "superbosses" / "live_expected.json"
PRODUCTION_EXPECTED_PATH = ROOT / "tests" / "fixtures" / "superbosses" / "production_expected.json"


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_has_exact_stratified_exit_gate_and_bounded_pending_fetch_scope():
    manifest = _manifest()
    bosses = manifest["bosses"]
    assert len(bosses) == 30
    assert {item["cohort"] for item in bosses} == {"weak", "medium", "strong"}
    assert {item["canonical_id"] for item in bosses}.__len__() == 30
    assert manifest["fetch_policy"]["live_fetch_authorization_required"] is True
    assert manifest["fetch_policy"]["bounded_detail_page_limit"] == 30
    assert manifest["fetch_policy"]["new_candidate_fetch_limit"] == 25
    assert manifest["fetch_policy"]["cached_refresh_limit"] == 5
    assert sum(item["support_status"] == "recommendation_ready" for item in bosses) == 30
    assert sum(item["support_status"] == "proposed_pending_live_fetch" for item in bosses) == 0
    assert sum(item["support_status"] == "cached_pending_repair" for item in bosses) == 0
    assert validate_superboss_manifest(manifest) == []
    assert len(proposed_live_fetch_records()) == 0
    assert len(manifest_records(statuses={"cached_pending_repair"})) == 0

    for cohort, expected_count in (("weak", 10), ("medium", 10), ("strong", 10)):
        rows = [item for item in bosses if item["cohort"] == cohort]
        assert len(rows) == expected_count
        assert all(
            item["difficulty_tier"] is not None
            and manifest["cohorts"][cohort]["difficulty_min"]
            <= float(item["difficulty_tier"])
            <= manifest["cohorts"][cohort]["difficulty_max"]
            for item in rows
        )
        assert all(item["source_url"].startswith("https://anothereden.wiki/w/") for item in rows)
        assert all(set(item["selection_rationale"]) == {
            "mechanics", "affinity", "parser", "page_section", "discord_beta_review"
        } for item in rows)


def test_cached_weak_fixture_round_trips_identity_affinity_and_owned_section():
    manifest_by_name = {item["name"]: item for item in _manifest()["bosses"]}
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(fixture["cases"]) == 5

    for case in fixture["cases"]:
        item = {
            **manifest_by_name[case["name"]],
            "source_url": case["source_url"],
            "support_status": "recommendation_ready",
        }
        soup = BeautifulSoup(
            (FIXTURE_PATH.parent / case["html_file"]).read_text(encoding="utf-8"),
            "html.parser",
        )
        row = parse_superboss_detail(
            soup,
            SuperbossIndexRow.model_validate(item),
            source_url=case["source_url"],
        )
        expected = case["expected"]
        assert row.name == case["name"]
        assert row.canonical_id == case["canonical_id"]
        assert row.section_bounded is expected["section_bounded"]
        assert row.weak == expected["weak"]
        assert row.resist == expected["resist"]
        assert row.null == expected["null"]
        assert row.absorb == expected["absorb"]
        assert row.affinity_state == expected["affinity_state"]
        assert row.recommendation_ready is True
        assert row.provenance["whole_page_fallback"] == "false"
        assert all(fragment.lower() in row.mechanics_text.lower() for fragment in expected["mechanic_substrings"])


def test_unanchored_whole_page_is_not_recommendation_ready():
    soup = BeautifulSoup(
        '<div id="mw-content-text"><h2><span class="mw-headline" id="Boss">Boss</span></h2>'
        '<p>Boss mechanics and affinity facts.</p></div>',
        "html.parser",
    )
    row = parse_superboss_detail(
        soup,
        SuperbossIndexRow.model_validate({
            "name": "Unbounded Boss",
            "source_url": "https://anothereden.wiki/w/Unbounded_Boss",
            "support_status": "recommendation_ready",
        }),
    )
    assert row.section_bounded is False
    assert row.mechanics_text == ""
    assert row.recommendation_ready is False


def test_authorized_live_fixtures_round_trip_all_25_candidates_and_provenance():
    manifest_by_id = {item["canonical_id"]: item for item in _manifest()["bosses"]}
    expected = json.loads(LIVE_EXPECTED_PATH.read_text(encoding="utf-8"))
    assert expected["authority"]
    assert len(expected["cases"]) == 25

    for case in expected["cases"]:
        candidate = {**manifest_by_id[case["canonical_id"]], "support_status": "recommendation_ready"}
        soup = BeautifulSoup(
            (LIVE_EXPECTED_PATH.parent / case["html_file"]).read_text(encoding="utf-8"),
            "html.parser",
        )
        row = parse_superboss_detail(
            soup,
            SuperbossIndexRow.model_validate(candidate),
            source_url=candidate["source_url"],
        )
        assert row.canonical_id == case["canonical_id"]
        assert row.cohort == case["cohort"]
        assert row.section_bounded is True
        assert row.source_section == case["source_section"]
        assert {field: getattr(row, field) for field in ("weak", "resist", "null", "absorb")} == case["affinity"]
        assert row.affinity_state == case["affinity_state"]
        assert row.recommendation_ready is True
        assert row.provenance["whole_page_fallback"] == "false"
        assert row.provenance["source_url"] == candidate["source_url"]
        assert row.citation_url.startswith(candidate["source_url"])
        assert row.mechanics_evidence["section_anchor"] == candidate["section_anchor"]
        if any(value != "unknown" for value in row.affinity_state.values()):
            assert row.affinity_observations
        if case["canonical_id"] in {"demon-spider-menreiki", "true-fornjot"}:
            assert len(row.affinity_observations) >= 1
        assert all(fragment.lower() in row.mechanics_text.lower() for fragment in case["mechanic_substrings"])


def test_compact_projection_carries_boss_identity_section_affinity_states_and_citation():
    bundle = _prepare_typed_candidates({
        "roster": [],
        "boss_id": "Mimi",
        "typed_retrieval": {
            "request": {"item_policy": "late_game_assumed", "stellar_awakened": {}},
            "boss": {
                "id": "mimi",
                "name": "Mimi",
                "aliases": ["Mimi"],
                "source_url": "https://anothereden.wiki/w/Mimi#Toto",
                "section_anchor": "Toto",
                "source_section": "Toto Dreamland",
                "section_bounded": True,
                "citation_url": "https://anothereden.wiki/w/Mimi#Toto",
                "provenance": {"whole_page_fallback": "false"},
                "mechanics_evidence": {"section_anchor": "Toto"},
                "weak": ["unknown"], "resist": ["unknown"], "null": ["unknown"], "absorb": ["unknown"],
                "weak_state": "unknown", "resist_state": "unknown", "null_state": "unknown", "absorb_state": "unknown",
                "recommendation_ready": True,
                "support_status": "recommendation_ready",
                "mechanics_text": "Random actions.",
            },
            "characters": [], "skills": [], "passives": [], "sidekicks": [],
            "grastas": [], "equipment": [], "coverage": {"complete": True},
            "role_scores": {}, "build_packages": {},
            "lineup_candidates": {"candidates": [], "policy_version": "test"},
        },
    })["candidate_bundle"]
    assert bundle["boss"]["id"] == "mimi"
    assert bundle["boss"]["section"]["anchor"] == "Toto"
    assert bundle["boss"]["affinity_states"]["weak"] == "unknown"
    assert bundle["boss"]["citations"][0]["source_url"].endswith("#Toto")
    assert bundle["boss"]["provenance"]["whole_page_fallback"] == "false"
    assert bundle["boss"]["mechanics_evidence"]["section_anchor"] == "Toto"


def test_every_corpus_boss_has_offline_production_outcome_and_degraded_fallback_fixture():
    manifest_by_id = {item["canonical_id"]: item for item in _manifest()["bosses"]}
    fixture = json.loads(PRODUCTION_EXPECTED_PATH.read_text(encoding="utf-8"))
    cases = {item["canonical_id"]: item for item in fixture["cases"]}
    assert fixture["authority"]
    assert fixture["degraded_fallback"]
    assert set(cases) == set(manifest_by_id)
    assert len(cases) == 30

    for canonical_id, expected in cases.items():
        manifest_item = manifest_by_id[canonical_id]
        assert expected["cohort"] == manifest_item["cohort"]
        assert expected["outcome"] in {"feasible", "typed_infeasible"}
        if expected["outcome"] == "typed_infeasible":
            assert expected["typed_issue_code"]
        else:
            assert expected["typed_issue_code"] is None
        bundle = _prepare_typed_candidates({
            "roster": [],
            "boss_id": manifest_item["name"],
            "typed_retrieval": {
                "request": {"item_policy": "late_game_assumed", "stellar_awakened": {}},
                "boss": {
                    "id": canonical_id,
                    "name": manifest_item["name"],
                    "aliases": manifest_item["aliases"],
                    "source_url": manifest_item["source_url"],
                    "citation_url": manifest_item["source_url"],
                    "section_anchor": manifest_item["section_anchor"],
                    "source_section": "fixture section",
                    "section_bounded": True,
                    "recommendation_ready": True,
                    "support_status": "recommendation_ready",
                    "mechanics_text": "fixture mechanics",
                    "provenance": {"whole_page_fallback": "false"},
                    "mechanics_evidence": {"section_anchor": manifest_item["section_anchor"]},
                },
                "characters": [], "skills": [], "passives": [], "sidekicks": [],
                "grastas": [], "equipment": [], "coverage": {"complete": True},
                "role_scores": {}, "build_packages": {},
                "lineup_candidates": {"candidates": [], "policy_version": "fixture"},
            },
        })["candidate_bundle"]
        assert bundle["boss"]["recommendation_ready"] is True
        assert bundle["boss"]["citations"][0]["source_url"] == manifest_item["source_url"]
        assert bundle["boss"]["section"]["anchor"] == manifest_item["section_anchor"]
        assert bundle["boss"]["provenance"]["whole_page_fallback"] == "false"


@pytest.mark.asyncio
async def test_production_rejects_explicitly_unready_boss_before_roster_retrieval():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value={
        "id": "mimi",
        "name": "Mimi",
        "recommendation_ready": False,
        "mechanics_text": "Random actions.",
    })
    service.conflicting_bosses = AsyncMock()
    request = ProductionRecommendationRequest(boss_id="Mimi", roster=["Aldo"])

    with pytest.raises(ProductionRequestError) as exc_info:
        await service.retrieve(request)

    assert exc_info.value.issues[0].code == "boss.unready"
    service.conflicting_bosses.assert_not_awaited()
