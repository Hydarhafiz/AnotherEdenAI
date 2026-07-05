"""Milestone 5 Feature B typed production retrieval boundary tests."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.workflow.graph import build_production_graph
from src.workflow.legality import RosterInput
from src.workflow.production import (
    ProductionRecommendationRequest,
    ProductionRequestError,
    ProductionRetrievalService,
    RetrievalIssue,
    validate_production_request,
)
from src.web.routes.api import QueryRequest
from src.web.streaming import pipeline_error_payload


def request(**overrides):
    values = {
        "boss_id": "Mimi",
        "roster": ["Aldo", "Ciel"],
        "owned_sidekicks": ["Moke"],
        "stellar_awakened": {"Aldo": True},
        "preferences": "Prefer sustain",
    }
    values.update(overrides)
    return ProductionRecommendationRequest.model_validate(values)


def boss(name="Mimi"):
    return {
        "id": name,
        "name": name,
        "source_url": "https://example.test/mimi",
        "weak": ["Fire"],
        "resist": [],
        "null": [],
        "absorb": [],
        "characteristics": "Test boss",
        "mechanic_tags": ["status"],
        "mechanics_text": "Uses status effects.",
    }


def test_request_is_typed_deduplicated_and_locks_item_policy():
    value = request(
        roster=[" Aldo ", "Aldo", "Ciel"],
        owned_sidekicks=[" Moke ", "Moke"],
    )
    assert value.roster == ["Aldo", "Ciel"]
    assert value.owned_sidekicks == ["Moke"]
    assert value.item_policy == "late_game_assumed"

    with pytest.raises(ValidationError):
        request(item_policy="declared_owned_only")


def test_api_contract_preserves_exploratory_mode_and_accepts_typed_production():
    exploratory = QueryRequest(query="general graph question", roster=["Aldo"])
    production = QueryRequest(
        query="Prefer sustain",
        roster=["Aldo"],
        boss_id="Mimi",
        mode="production",
        stellar_awakened={"Aldo": True},
    )

    assert exploratory.mode == "exploratory"
    assert exploratory.boss_id is None
    assert production.mode == "production"
    assert production.boss_id == "Mimi"
    assert production.item_policy == "late_game_assumed"


def test_missing_boss_uses_typed_request_error():
    with pytest.raises(ProductionRequestError) as exc_info:
        validate_production_request({"roster": ["Aldo"]})

    assert exc_info.value.issues[0].code == "boss.missing"
    assert exc_info.value.issues[0].field == "boss_id"


def test_sse_preserves_typed_retrieval_failure_details():
    error = ProductionRequestError([RetrievalIssue(
        code="boss.unsupported",
        field="boss_id",
        value="Not A Boss",
        message="Unsupported boss ID: Not A Boss",
    )])

    payload = pipeline_error_payload(error)

    assert payload["node"] == "ERROR"
    assert payload["failure_type"] == "boss.unsupported"
    assert payload["issues"][0]["field"] == "boss_id"


@pytest.mark.asyncio
async def test_graph_projection_methods_unpack_aliased_fact_maps():
    driver = AsyncMock()
    driver.execute_query = AsyncMock(side_effect=[
        ([{"fact": {"id": "character:aldo", "name": "Aldo"}}], None, None),
        ([{"fact": {"id": "skill:aldo", "name": "X Slash", "character_name": "Aldo"}}], None, None),
        ([{"fact": {"id": "passive:aldo", "name": "Valor Chant", "character_name": "Aldo"}}], None, None),
        ([{"fact": {"name": "Moke", "skills": [], "auras": []}}], None, None),
        ([{"fact": {"id": "grasta:fire", "name": "Fire"}}], None, None),
        ([{"fact": {"name": "Sword", "equipment_slot": "weapon"}}], None, None),
    ])
    service = ProductionRetrievalService(driver)

    characters = await service.characters(["Aldo"])
    skills, passives = await service.skills_passives(["Aldo"])
    sidekicks = await service.sidekicks(["Moke"])
    grastas = await service.grastas()
    equipment = await service.equipment(["Sword"])

    assert characters[0]["name"] == "Aldo"
    assert skills[0]["character_name"] == "Aldo"
    assert passives[0]["character_name"] == "Aldo"
    assert sidekicks[0]["name"] == "Moke"
    assert grastas[0]["id"] == "grasta:fire"
    assert equipment[0]["equipment_slot"] == "weapon"


@pytest.mark.asyncio
async def test_invalid_boss_fails_deterministically_before_other_retrieval():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value=None)
    service.characters = AsyncMock()

    with pytest.raises(ProductionRequestError) as exc_info:
        await service.retrieve(request(boss_id="Not A Boss"))

    assert exc_info.value.issues[0].code == "boss.unsupported"
    assert exc_info.value.issues[0].field == "boss_id"
    service.characters.assert_not_awaited()


@pytest.mark.asyncio
async def test_preferences_naming_another_boss_return_typed_conflict():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value=boss())
    service.conflicting_bosses = AsyncMock(return_value=["Lavos Core"])

    with pytest.raises(ProductionRequestError) as exc_info:
        await service.retrieve(request(preferences="Build for Lavos Core"))

    assert exc_info.value.issues[0].code == "boss.query_conflict"
    assert exc_info.value.issues[0].value == "Lavos Core"


@pytest.mark.asyncio
async def test_curated_boss_name_conflicts_even_when_graph_has_no_matching_row():
    service = ProductionRetrievalService(AsyncMock())
    service._query = AsyncMock(return_value=[])

    conflicts = await service.conflicting_bosses("Mimi", "Build for Lavos Core")

    assert conflicts == ["Lavos Core"]


@pytest.mark.asyncio
async def test_unresolved_roster_returns_typed_normalization_error():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value=boss())
    service.conflicting_bosses = AsyncMock(return_value=[])

    service.resolve_character = AsyncMock(return_value=[])
    with pytest.raises(ProductionRequestError) as exc_info:
        await service.retrieve(request(roster=["Unknown Hero"]))

    assert exc_info.value.issues[0].code == "roster.unresolved"
    assert exc_info.value.issues[0].value == "Unknown Hero"


@pytest.mark.asyncio
async def test_unresolved_sidekick_returns_typed_normalization_error():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value=boss())
    service.conflicting_bosses = AsyncMock(return_value=[])

    service.resolve_character = AsyncMock(side_effect=[["Aldo"], ["Ciel"]])
    service.resolve_sidekick = AsyncMock(return_value=[])
    with patch("src.workflow.production.build_roster_input", new=AsyncMock()):
        with pytest.raises(ProductionRequestError) as exc_info:
            await service.retrieve(request(owned_sidekicks=["Unknown Buddy"]))

    assert exc_info.value.issues[0].code == "sidekick.unresolved"
    assert exc_info.value.issues[0].value == "Unknown Buddy"


@pytest.mark.asyncio
async def test_one_letter_roster_inputs_cannot_use_exploratory_substring_matching():
    driver = AsyncMock()
    driver.execute_query = AsyncMock(return_value=([], None, None))
    service = ProductionRetrievalService(driver)

    matches = await service.resolve_character("A")

    assert matches == []
    cypher = driver.execute_query.await_args.args[0]
    assert "CONTAINS" not in cypher.upper()


@pytest.mark.asyncio
async def test_typed_retrieval_is_roster_bounded_and_reports_coverage():
    service = ProductionRetrievalService(AsyncMock())
    service.boss = AsyncMock(return_value=boss())
    service.conflicting_bosses = AsyncMock(return_value=[])
    service.characters = AsyncMock(return_value=[
        {"id": "character:aldo", "name": "Aldo", "weapon": "Sword"},
        {"id": "character:ciel", "name": "Ciel", "weapon": "Bow"},
    ])
    service.skills_passives = AsyncMock(return_value=(
        [{"id": "skill:aldo", "character_name": "Aldo"}],
        [{"id": "passive:ciel", "character_name": "Ciel"}],
    ))
    service.sidekicks = AsyncMock(return_value=[{"name": "Moke"}])
    service.grastas = AsyncMock(return_value=[{"id": "grasta:test"}])
    service.equipment = AsyncMock(return_value=[{"name": "Sword", "equipment_slot": "weapon"}])
    service.mechanics = AsyncMock(return_value=[{"id": "status-reference"}])

    roster_input = RosterInput(
        owned_characters=["Aldo", "Ciel"],
        owned_sidekicks=["Moke"],
        stellar_awakened={"Aldo": True},
    )
    service.resolve_character = AsyncMock(side_effect=[["Aldo"], ["Ciel"]])
    service.resolve_sidekick = AsyncMock(return_value=["Moke"])
    with patch(
        "src.workflow.production.build_roster_input",
        new=AsyncMock(return_value=roster_input),
    ), patch(
        "src.workflow.legality.augment_with_f2p",
        side_effect=lambda names: names,
    ):
        result = await service.retrieve(request(preferences="Use only my roster"))

    service.characters.assert_awaited_once_with(["Aldo", "Ciel"])
    service.skills_passives.assert_awaited_once_with(["Aldo", "Ciel"])
    service.sidekicks.assert_awaited_once_with(["Moke"])
    assert result.coverage == {
        "requested_character_count": 2,
        "retrieved_character_count": 2,
        "missing_character_names": [],
        "skill_owner_count": 1,
        "passive_owner_count": 1,
        "requested_sidekick_count": 1,
        "retrieved_sidekick_count": 1,
        "boss_complete": True,
        "complete": True,
    }
    assert {row["name"] for row in result.characters} == {"Aldo", "Ciel"}


def test_production_graph_excludes_plan_generated_cypher_and_validation():
    graph = build_production_graph(driver=AsyncMock())
    nodes = set(graph.get_graph().nodes)

    assert {"production_retrieve", "prepare_candidates", "analyze", "format"} <= nodes
    assert "plan" not in nodes
    assert "superboss_context" not in nodes
    assert "generate_cypher" not in nodes
    assert "validate" not in nodes
