"""Tests for Feature C boss matchup retrieval and fit rubric."""

from __future__ import annotations

import json

import pytest

from src.workflow.legality import CharacterBuild, LineupModel
from src.workflow.matchup import (
    BossFacts,
    default_rubric,
    evaluate_lineup_fit,
    retrieve_matchup_context,
)
from src.workflow.nodes.format import format_node


def _with_feature_b_build_slots(value):
    if isinstance(value, dict):
        updated = {key: _with_feature_b_build_slots(child) for key, child in value.items()}
        if "name" in updated and "role" in updated:
            updated.setdefault("weapon", "available weapon")
            updated.setdefault("armor", "available armor")
            grastas = list(updated.get("grastas") or ["Power of Mind"])
            while len(grastas) < 3:
                grastas.append(grastas[-1] if grastas else "Power of Mind")
            updated["grastas"] = grastas[:3]
        return updated
    if isinstance(value, list):
        return [_with_feature_b_build_slots(item) for item in value]
    return value


class AsyncRecordStream:
    def __init__(self, records):
        self._records = list(records)

    def __aiter__(self):
        self._iter = iter(self._records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class RecordingSession:
    def __init__(self, calls, records):
        self.calls = calls
        self.records = records

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))
        return AsyncRecordStream(self.records)


class RecordingDriver:
    def __init__(self, *, boss_records, mechanic_records):
        self.execute_calls = []
        self.session_calls = []
        self.boss_records = boss_records
        self.mechanic_records = mechanic_records

    async def execute_query(self, cypher, **params):
        self.execute_calls.append((cypher, params))
        return self.boss_records, None, None

    def session(self):
        return RecordingSession(self.session_calls, self.mechanic_records)


def _build(name: str, role: str, *, grastas=None, recommended_skills=None, upgrade_assumptions=None) -> CharacterBuild:
    values = list(grastas or ["Power of Mind"])
    while len(values) < 3:
        values.append(values[-1])
    return CharacterBuild(
        name=name,
        role=role,
        weapon="available weapon",
        armor="available armor",
        grastas=values[:3],
        recommended_skills=recommended_skills or [],
        upgrade_assumptions=upgrade_assumptions or [],
    )

def _lineup(*, main_sidekick: str | None = "Tetra", sub_sidekick: str | None = "Korobo") -> LineupModel:
    return LineupModel(
        frontline=[
            _build(
                "Aldo",
                "Fire slash DPS with AF burst",
                grastas=["Fire Power Grasta", "Bull's Eye Ore"],
                recommended_skills=["Fire Slash"],
            ),
            _build("Feinne", "healer with status cleanse and MP restore", recommended_skills=["Heal", "Cleanse"]),
            _build("Riica", "mitigation support and barrier", recommended_skills=["Guard Protocol"]),
            _build("Ciel", "buff and debuff support", recommended_skills=["Elemental Song"]),
        ],
        reserve=[
            _build("Miyu", "slash zone backup", recommended_skills=["Rune Blade"]),
            _build("Shion", "fire slash reserve DPS", recommended_skills=["Phoenix Slash"]),
        ],
        main_sidekick=main_sidekick,
        sub_sidekick=sub_sidekick,
    )


def _boss(**overrides) -> BossFacts:
    payload = {
        "name": "Flame Eater",
        "source_url": "https://example.test/flame-eater",
        "weak": ["Fire", "Slash"],
        "resist": ["Water"],
        "null": ["Thunder"],
        "absorb": ["Earth"],
        "characteristics": "Uses status pressure and fixed damage.",
        "mechanic_tags": ["status", "fixed-damage", "weakness"],
        "mechanics_text": "Applies poison and fixed damage; mitigation and cleanse are valuable.",
    }
    payload.update(overrides)
    return BossFacts.model_validate(payload)


def test_evaluate_lineup_fit_rewards_weakness_and_defensive_counterplay():
    rubric = evaluate_lineup_fit(
        _lineup(),
        _boss(),
        mechanic_references=[{"id": "status-cleanse", "summary": "Cleanse status effects."}],
    )

    assert rubric.legality_gate == "high"
    assert rubric.boss_matchup_offense == "high"
    assert rubric.boss_matchup_defense == "high"
    assert rubric.sustain_and_recovery == "high"
    assert rubric.mp_sustainability == "high"
    assert rubric.sidekick_contribution == "high"
    assert rubric.grasta_ore_equipment_readiness == "high"
    assert rubric.uncertainty_or_missing_data_penalty == "low"
    assert rubric.confidence == "high"
    assert not any("probability" in note.lower() for note in rubric.risk_notes)


def test_evaluate_lineup_fit_penalizes_affinity_conflicts_and_upgrade_burden():
    lineup = _lineup(main_sidekick=None, sub_sidekick=None)
    lineup.frontline[0].role = "Water magic DPS"
    lineup.frontline[0].recommended_skills = ["Waterfall"]
    lineup.frontline[0].upgrade_assumptions = ["Requires Stellar Awakening for Waterfall."]

    rubric = evaluate_lineup_fit(lineup, _boss(weak=["Fire"], resist=["Water"]), mechanic_references=[])

    assert rubric.boss_matchup_offense == "low"
    assert rubric.sidekick_contribution == "low"
    assert rubric.upgrade_burden_penalty == "high"
    assert rubric.uncertainty_or_missing_data_penalty == "medium"
    assert any("affinity conflicts: water" in note.lower() for note in rubric.risk_notes)


def test_missing_boss_data_lowers_confidence_and_adds_risk_note():
    rubric = evaluate_lineup_fit(_lineup(), None)

    assert rubric.boss_matchup_offense == "low"
    assert rubric.boss_matchup_defense == "low"
    assert rubric.uncertainty_or_missing_data_penalty == "high"
    assert rubric.confidence == "low"
    assert rubric.risk_notes == ["Boss affinity facts are missing, so matchup fit is conservative."]


def test_default_rubric_has_required_feature_c_categories():
    rubric = default_rubric(has_boss=True, has_mechanics=False)
    dumped = rubric.model_dump()

    assert set(dumped) == {
        "legality_gate",
        "boss_matchup_offense",
        "boss_matchup_defense",
        "lineup_synergy",
        "sustain_and_recovery",
        "mp_sustainability",
        "sidekick_contribution",
        "grasta_ore_equipment_readiness",
        "uncertainty_or_missing_data_penalty",
        "upgrade_burden_penalty",
        "confidence",
        "risk_notes",
    }
    assert dumped["uncertainty_or_missing_data_penalty"] == "medium"
    assert dumped["confidence"] == "medium"
    assert dumped["risk_notes"] == ["No matching MechanicReference rows were retrieved."]


@pytest.mark.asyncio
async def test_retrieve_matchup_context_queries_boss_facts_and_mechanic_references():
    boss = {
        "boss": {
            "name": "Flame Eater",
            "source_url": "https://example.test/flame-eater",
            "weak": ["Fire", "Slash"],
            "resist": ["Water"],
            "null": ["Thunder"],
            "absorb": ["Earth"],
            "characteristics": "Status pressure.",
            "mechanic_tags": ["status", "weakness"],
            "mechanics_text": "Cleanse and mitigation matter.",
        }
    }
    reference = {
        "reference": {
            "id": "weakness-resist-null-absorb",
            "title": "Weakness, Resist, Null, And Absorb Handling",
            "source_url": "https://example.test/affinity",
            "topic_tags": ["weakness"],
        }
    }
    driver = RecordingDriver(boss_records=[boss], mechanic_records=[reference])

    context = await retrieve_matchup_context(driver, "Build a boss matchup for Flame Eater")

    assert context.boss is not None
    assert context.boss.weak == ["Fire", "Slash"]
    assert context.boss.resist == ["Water"]
    assert context.boss.null == ["Thunder"]
    assert context.boss.absorb == ["Earth"]
    assert context.mechanic_references == [reference["reference"]]
    assert context.citations == [
        {"label": "Flame Eater", "source_url": "https://example.test/flame-eater"},
        {"label": "Weakness, Resist, Null, And Absorb Handling", "source_url": "https://example.test/affinity"},
    ]

    boss_cypher, boss_params = driver.execute_calls[0]
    assert "MATCH (s:Superboss)" in boss_cypher
    assert all(field in boss_cypher for field in [".weak", ".resist", ".null", ".absorb", ".mechanics_text"])
    assert boss_params == {"query": "Build a boss matchup for Flame Eater", "database_": "neo4j"}

    mechanics_cypher, mechanics_params = driver.session_calls[0]
    assert "MATCH (m:MechanicReference)" in mechanics_cypher
    assert "weakness" in mechanics_params["topic_tags"]
    assert "fire" in mechanics_params["topic_tags"]
    assert "boss_counterplay" in mechanics_params["applies_to"]


@pytest.mark.asyncio
async def test_retrieve_matchup_context_recognizes_defeat_intent_for_mimi():
    boss = {
        "boss": {
            "name": "Mimi",
            "source_url": "https://anothereden.wiki/w/Mimi",
            "weak": ["unknown"],
            "resist": ["unknown"],
            "null": ["unknown"],
            "absorb": ["unknown"],
            "characteristics": "Weak superboss.",
            "mechanic_tags": ["sustain"],
            "mechanics_text": "Mimi uses physical and Earth attacks.",
        }
    }
    driver = RecordingDriver(boss_records=[boss], mechanic_records=[])

    context = await retrieve_matchup_context(driver, "Create lineups to defeat Mimi")

    assert context.boss is not None
    assert context.boss.name == "Mimi"
    assert context.citations[0] == {
        "label": "Mimi",
        "source_url": "https://anothereden.wiki/w/Mimi",
    }
    assert driver.execute_calls[0][1]["query"] == "Create lineups to defeat Mimi"


def test_format_node_preserves_rubric_output_shape_and_boss_affinity():
    payload = _with_feature_b_build_slots({
        "frontline": [
            {"name": "Aldo", "role": "Fire slash DPS", "grastas": ["Fire Power Grasta"]},
            {"name": "Feinne", "role": "healer", "grastas": []},
            {"name": "Riica", "role": "mitigation", "grastas": []},
            {"name": "Ciel", "role": "support", "grastas": []},
        ],
        "reserve": [
            {"name": "Miyu", "role": "slash backup", "grastas": []},
            {"name": "Shion", "role": "fire reserve", "grastas": []},
        ],
        "main_sidekick": "Tetra",
        "sub_sidekick": "Korobo",
        "fit_label": "high",
        "confidence_label": "medium",
        "rubric_summary": {
            "offense": "high - Fire and Slash cover graph weakness.",
            "defense": "medium - mitigation is present but status risk remains.",
            "synergy": "medium - slash roles align.",
            "sustain": "high - healing is present.",
            "mp": "medium - MP sustain is plausible.",
            "sidekick": "high - main and sub sidekicks selected.",
            "build_readiness": "medium - assumes common Grasta/Ore access.",
            "upgrade_burden": "low - no SA assumptions.",
        },
        "boss_affinity": {"weak": ["Fire", "Slash"], "resist": ["Water"], "null": ["Thunder"], "absorb": ["Earth"]},
        "risks": ["Status handling depends on cleanse timing."],
        "citations": [{"label": "Flame Eater", "source_url": "https://example.test/flame-eater"}],
        "synergy_explanation": "Aldo: Fire Power Grasta (Courage) - supports Fire pressure.",
    })

    result = format_node({"analysis_result": json.dumps(payload), "db_results": [{"ok": True}], "retry_count": 0})

    final = result["final_output"]
    assert final["fit_label"] == "high"
    assert final["confidence_label"] == "medium"
    assert final["boss_affinity"] == payload["boss_affinity"]
    assert set(final["rubric_summary"]) == {
        "offense",
        "defense",
        "synergy",
        "sustain",
        "mp",
        "sidekick",
        "build_readiness",
        "upgrade_burden",
    }
    assert final["citations"] == payload["citations"]
    assert final["error"] is None


def test_format_node_rejects_numeric_win_probability_language():
    payload = _with_feature_b_build_slots({
        "frontline": [
            {"name": "Aldo", "role": "Fire slash DPS", "grastas": []},
            {"name": "Feinne", "role": "healer", "grastas": []},
            {"name": "Riica", "role": "mitigation", "grastas": []},
            {"name": "Ciel", "role": "support", "grastas": []},
        ],
        "reserve": [
            {"name": "Miyu", "role": "slash backup", "grastas": []},
            {"name": "Shion", "role": "fire reserve", "grastas": []},
        ],
        "fit_label": "high",
        "confidence_label": "high",
        "rubric_summary": {"offense": "80% win chance from Fire weakness."},
        "synergy_explanation": "Aldo: Fire Power Grasta (Courage) - supports Fire pressure.",
    })

    result = format_node({"analysis_result": json.dumps(payload), "db_results": [{"ok": True}], "retry_count": 0})

    assert "recommendations must not present numeric win probability" in result["final_output"]["error"]
