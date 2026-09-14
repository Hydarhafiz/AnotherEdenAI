"""Feature A request-time funnel and diversity regressions."""

from unittest.mock import AsyncMock, patch

import pytest

from src.workflow.production import ProductionRecommendationRequest, ProductionRetrievalService
from src.workflow.legality import RosterInput
from src.workflow.coverage import build_request_coverage_report, candidate_diversity_report


def _request_fixture():
    characters = [{"id": f"character:{index}", "name": f"Hero {index}"} for index in range(6)]
    entities = [
        {
            "id": character["id"],
            "entity_type": "character",
            "package_ready": True,
            "eligible": index < 5,
            "rejection_reasons": [] if index < 5 else ["primary_damage.null_or_absorb"],
        }
        for index, character in enumerate(characters)
    ]
    role_pools = {
        "primary_damage": [{"entity_id": "character:0"}, {"entity_id": "character:1"}],
        "defense_mitigation": [{"entity_id": "character:2"}],
        "reserve_utility": [{"entity_id": "character:3"}],
    }
    candidates = [
        {
            "id": "lineup:one",
            "character_ids": [f"character:{index}" for index in range(6)],
            "frontline_character_ids": [f"character:{index}" for index in range(4)],
            "archetype": "burst",
            "score": 100,
            "component_scores": {"coverage": 100, "synergy": 4},
        },
        {
            "id": "lineup:two",
            "character_ids": [f"character:{index}" for index in reversed(range(6))],
            "frontline_character_ids": ["character:5", "character:4", "character:3", "character:2"],
            "archetype": "sustain",
            "score": 100,
            "component_scores": {"coverage": 100, "synergy": 4},
        },
    ]
    return {
        "characters": characters,
        "role_scores": {"entities": entities, "role_pools": role_pools},
        "candidate_generation": {"candidates": candidates},
    }


def test_request_report_keeps_funnel_stages_distinct_and_is_deterministic():
    fixture = _request_fixture()
    kwargs = {
        "user_roster": ["Hero 0", "Hero 1"],
        "f2p_augmented_roster": ["Hero 0", "Hero 1", "Hero 2", "Hero 3", "Hero 4", "Hero 5"],
        **fixture,
    }

    first = build_request_coverage_report(**kwargs)
    second = build_request_coverage_report(**kwargs)

    assert first == second
    assert first["metrics"] == {
        "user_roster_count": 2,
        "f2p_augmented_count": 4,
        "distinct_available_count": 6,
        "data_complete_count": 6,
        "boss_eligible_count": 5,
        "role_pool_union_count": 4,
        "candidate_count": 2,
        "unique_character_set_count": 1,
        "unique_frontline_set_count": 2,
        "unique_archetype_count": 2,
    }
    assert first["metric_details"]["data_complete_count"]["denominator_value"] == 6
    assert first["diversity"]["warnings"] == [
        "permutation_only_or_same_character_set",
        "identical_total_score_vector",
        "identical_component_score_vector",
        "archetype_labels_not_strategically_differentiated",
    ]


def test_candidate_diversity_keeps_malformed_character_and_frontline_sets_unknown():
    report = candidate_diversity_report([
        {"character_ids": ["a", "b"], "score": 1},
        {"character_ids": ["a", "b"], "score": 2},
    ])

    assert report["unique_character_set_count"] is None
    assert report["unique_frontline_set_count"] is None
    assert report["unique_archetype_count"] == 1
    assert report["identical_total_scores"] is False
    assert report["character_sets_unknown"] == 2
    assert report["frontline_sets_unknown"] == 2
    assert report["warnings"] == [
        "candidate_character_sets_unknown",
        "candidate_frontline_sets_unknown",
        "candidate_component_score_vectors_unknown",
    ]


def test_request_report_separates_missing_retrieval_and_role_score_unknowns():
    report = build_request_coverage_report(
        user_roster=["Hero 0"],
        f2p_augmented_roster=["Hero 0", "Hero 1", "Hero 2"],
        characters=[{"id": "character:0", "name": "Hero 0"}, {"id": "character:1", "name": "Hero 1"}],
        role_scores={"entities": [{"id": "character:0", "entity_type": "character"}]},
        candidate_generation={"candidates": []},
    )

    assert report["metrics"]["f2p_augmented_count"] == 2
    assert report["unknown_data"] == {
        "available_characters_not_retrieved": 1,
        "retrieved_characters_without_role_scores": 1,
        "readiness_markers_unknown": 1,
        "character_sets_unknown": 0,
        "frontline_sets_unknown": 0,
        "total_scores_unknown": 0,
        "component_score_vectors_unknown": 0,
    }


@pytest.mark.asyncio
async def test_production_retrieval_exposes_the_request_report_without_changing_legacy_coverage():
    fixture = _request_fixture()
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value={
        "id": "boss:test", "name": "Test Boss", "mechanics_text": "Known",
        "recommendation_ready": True,
    })
    service.conflicting_bosses = AsyncMock(return_value=[])
    service.resolve_character = AsyncMock(side_effect=[["Hero 0"], ["Hero 1"]])
    service.resolve_sidekick = AsyncMock(return_value=[])
    service.characters = AsyncMock(return_value=fixture["characters"])
    service.skills_passives = AsyncMock(return_value=([], []))
    service.sidekicks = AsyncMock(return_value=[])
    service.grastas = AsyncMock(return_value=[])
    service.equipment = AsyncMock(return_value=[])
    service.mechanics = AsyncMock(return_value=[])
    roster_input = RosterInput(owned_characters=["Hero 0", "Hero 1"])
    request = ProductionRecommendationRequest(boss_id="test", roster=["Hero 0", "Hero 1"])

    with patch("src.workflow.production.build_roster_input", new=AsyncMock(return_value=roster_input)), \
         patch("src.workflow.legality.augment_with_f2p", side_effect=lambda _values: [character["name"] for character in fixture["characters"]]), \
         patch("src.workflow.production.derive_contextual_role_scores", return_value=fixture["role_scores"]), \
         patch("src.workflow.production.generate_lineup_candidates", return_value=fixture["candidate_generation"]):
        result = await service.retrieve(request)

    assert result.coverage["requested_character_count"] == 6
    assert result.coverage["complete"] is True
    assert result.request_coverage["metrics"]["user_roster_count"] == 2
    assert result.request_coverage["metrics"]["distinct_available_count"] == 6
    assert result.request_coverage["metrics"]["candidate_count"] == 2
