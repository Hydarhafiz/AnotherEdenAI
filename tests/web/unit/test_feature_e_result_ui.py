"""Feature E tests for compact and expandable recommendation rendering."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.templating import Jinja2Templates


TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "src" / "web" / "templates"


class _TextParser(HTMLParser):
    """Small HTML text collector for template assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.text.append(stripped)


def _visible_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return " ".join(parser.text)


def _slot(name: str, role: str, *, grastas: list[str] | None = None) -> dict:
    values = list(grastas or ["Power of Mind"] )
    while len(values) < 3:
        values.append(values[-1])
    return {
        "name": name,
        "role": role,
        "weapon": "available weapon",
        "armor": "available armor",
        "grastas": values[:3],
        "recommended_skills": [f"{name} Skill"],
        "recommended_passives": [f"{name} Passive"],
        "upgrade_assumptions": [],
    }


def _minimal_slot(name: str, role: str) -> dict:
    return {
        "name": name,
        "role": role,
        "weapon": "available weapon",
        "armor": "available armor",
        "grastas": ["Power of Mind", "Power of Mind", "Power of Mind"],
        "recommended_skills": [],
        "recommended_passives": [],
        "upgrade_assumptions": [],
    }


def _recommendation(archetype: str) -> dict:
    return {
        "archetype": archetype,
        "frontline": [
            _slot("Aldo", "damage anchor", grastas=["Fire T3"]),
            _minimal_slot("Ciel", "healer"),
            _slot("Riica", "support"),
            _slot("Shion", "secondary DPS"),
        ],
        "reserve": [
            _slot("Miyu", "reserve buffer"),
            _slot("Feinne", "reserve healer"),
        ],
        "main_sidekick": "Korobo",
        "sub_sidekick": "Tetra",
        "strategy_summary": f"{archetype.title()} strategy summary.",
        "key_facts": ["Korobo supports the main sidekick slot."],
        "build_notes": ["Assumes common late-game grasta access."],
        "boss_counterplay_notes": ["Exploit Fire weakness and avoid absorb conflicts."],
        "sustain_mp_notes": ["Rotate reserves to stabilize MP."],
        "risks": [
            "Risk one is visible in compact view.",
            "Risk two is also visible in compact view.",
            "Risk three stays in expanded uncertainty details.",
        ],
        "fit_label": "high",
        "confidence_label": "medium",
        "rubric_summary": {"offense": "high - good weakness coverage"},
        "citations": [
            {
                "label": "Flame Eater affinity",
                "source_url": "https://anothereden.wiki/w/Flame_Eater",
            }
        ],
        "synergy_explanation": "Aldo pressure is backed by Fire T3 grasta.",
    }


def _feature_e_result() -> dict:
    return {
        "recommendations": [
            _recommendation("burst"),
            _recommendation("sustain"),
            _recommendation("hybrid"),
        ],
        "archetype_viability_notes": ["All three archetypes are viable."],
        "error": None,
    }


def _render_result(result: dict) -> str:
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    template = templates.env.get_template("partials/result.html")
    return template.render(result=result)


def _make_mock_request() -> MagicMock:
    async def is_disconnected() -> bool:
        return False

    request = MagicMock()
    request.is_disconnected = is_disconnected
    return request


def _make_mock_graph_astream(final_output: dict, captured_state: dict | None = None):
    async def mock_astream(*args, **kwargs):
        if captured_state is not None:
            captured_state.update(args[0])
        yield {"format": {"final_output": final_output}}

    mock_graph = MagicMock()
    mock_graph.astream = mock_astream
    return mock_graph


def test_feature_e_recommendations_render_as_three_compact_cards():
    """Default result view is scannable and shows all three archetypes."""
    html = _render_result(_feature_e_result())
    text = _visible_text(html)

    assert html.count('class="recommendation-card"') == 3
    assert "Lineup Recommendations" in text
    assert "Burst" in text
    assert "Sustain" in text
    assert "Hybrid" in text
    assert "Frontline: Aldo, Ciel, Riica, Shion" in text
    assert "Reserve: Miyu, Feinne" in text
    assert "Sidekicks: main Korobo, sub Tetra" in text
    assert "Fit: high" in text
    assert "Confidence: medium" in text
    assert "Short strategy" in text
    assert "Main risks" in text
    assert "Risk one is visible in compact view." in text


def test_feature_e_recommendations_render_expandable_evidence_sections():
    """Detailed evidence is present inside expandable recommendation details."""
    html = _render_result(_feature_e_result())
    text = _visible_text(html)

    assert "<details class=\"recommendation-card\">" in html
    assert "Character Roles And Placement" in text
    assert "Skills: Aldo Skill" in text
    assert "Skills: none supplied" in text
    assert "Passives: Aldo Passive" in text
    assert "Passives: none supplied" in text
    assert "Assumes: no upgrade assumptions listed" in text
    assert "Build Notes" in text
    assert "Assumes common late-game grasta access." in text
    assert "Aldo: weapon available weapon; armor available armor; Grasta Fire T3" in text
    assert "Sidekick And Key Facts" in text
    assert "Boss Counterplay" in text
    assert "Sustain And MP" in text
    assert "Assumptions And Uncertainty" in text
    assert "Risk three stays in expanded uncertainty details." in text
    assert "Fit Rubric" in text
    assert "Citations" in text
    assert "Flame Eater affinity" in text
    assert "Synergy" in text


def test_feature_e_error_result_uses_graceful_failure_partial():
    """Failed legality/factuality formatting still renders a clear error."""
    html = _render_result(
        {
            "frontline": [],
            "reserve": [],
            "synergy_explanation": "",
            "error": "LLM returned malformed team structure",
        }
    )
    text = _visible_text(html)

    assert "No recommendation found" in text
    assert "The recommendation pipeline could not produce a valid result." in text
    assert "valid Cypher query after 3 attempts" not in text
    assert "Error details" in text
    assert "LLM returned malformed team structure" in text
    assert "recommendation-card" not in html


@pytest.mark.parametrize("degraded", [False, True])
def test_deterministic_only_banner_uses_the_result_contract(degraded):
    result = _feature_e_result()
    result["degraded"] = degraded
    text = _visible_text(_render_result(result))
    assert ("Deterministic-only result" in text) is degraded
    if degraded:
        assert "no successful AI analysis is claimed" in text


def test_production_view_uses_final_evidence_and_hides_unverified_analyzer_prose():
    result = _feature_e_result()
    result["result_presentation"] = {
        "mode": "production",
        "boss_name": "Celestial Mushroom",
        "boss_source": {"label": "Celestial Mushroom source", "source_url": "https://example.test/mushroom"},
        "boss_affinities": [
            {"dimension": "weak", "values": [], "state": "confirmed_empty"},
            {"dimension": "resist", "values": ["Pierce", "Blunt"], "state": "confirmed_values"},
            {"dimension": "null", "values": [], "state": "unknown"},
            {"dimension": "absorb", "values": [], "state": "unknown"},
        ],
        "request_coverage": {
            "status": "available",
            "metrics": {"user_roster_count": 6, "candidate_count": 4, "unique_character_set_count": 2},
            "unknown_data": {"character_sets_unknown": 0},
            "note": "Counts describe search, not final quality.",
        },
        "explanation_limit": "Fit is a heuristic; confidence is represented scorer uncertainty only.",
    }
    rec = result["recommendations"][0]
    rec["strategy_summary"] = "STALE analyzer text about a different lineup."
    rec["synergy_explanation"] = "STALE synergy claim."
    rec["risks"] = ["STALE analyzer risk."]
    rec["presentation"] = {
        "selected_skill_evidence_status": "available",
        "selected_skill_count": 2,
        "joined_skill_count": 2,
        "skills_with_reviewed_capabilities": 1,
        "unreviewed_proposal_count": 3,
        "skills_without_reviewed_capabilities": [],
        "selected_skills": [{
            "character_id": "character:Toova",
            "character_name": "Toova",
            "skill_id": "skill:toova:venom",
            "skill_name": "Venom",
            "placement": "frontline",
            "review_status": "reviewed",
            "source": {"label": "Venom source", "source_url": "https://example.test/toova#Venom"},
            "reviewed_effects": [{
                "capability": "inflict_poison",
                "direction": "enemy",
                "target": "single_enemy",
                "trigger": "",
                "matched_phrase": "Inflicts Poison",
                "source_id": "rule:poison",
                "source_fact_id": "skill:toova:venom",
                "review_decision": "approve",
                "artifact_version": "tax-1",
                "review_artifact_version": "review-1",
            }],
        }],
        "source_effect_coverage": "not_established",
        "candidate": {
            "status": "available",
            "note": "Matches final character and skill IDs.",
            "modeled_roles": {"frontline": ["primary_damage"], "reserve_after_switch": ["reserve_utility"]},
            "modeled_coverage_gaps": ["mandatory.counter.grant_status_immunity"],
            "component_scores": {"boss_matchup": 9},
            "component_score_scope": {"boss_matchup": "Recorded attacks for all selected characters."},
            "scorer_uncertainty_count": 0,
            "scorer_uncertainty_scope": "Affinity states only.",
            "selected_skill_matchups": [{
                "character_name": "Aldo", "skill_id": "skill:aldo:fire", "skill_name": "Fire Slash",
                "placement": "frontline", "elements": ["Fire"], "attack_types": ["Slash"],
                "state": "weak", "evidence_ids": ["skill:aldo:fire"],
            }],
            "selected_skill_matchups_unavailable": False,
        },
        "warnings": [{
            "code": "venom_mushroom_harm",
            "title": "Known harmful interaction",
            "message": "Toova's Venom applies Poison; Celestial Mushroom gains resistance and heals after clearing it.",
            "sources": [
                {"label": "Venom source", "source_url": "https://example.test/toova#Venom"},
                {"label": "Celestial Mushroom source", "source_url": "https://example.test/mushroom"},
            ],
        }],
    }

    html = _render_result(result)
    text = _visible_text(html)

    assert "Validated backend candidate" in text
    assert "Final candidate evidence" in text
    assert "Selected skill evidence" in text
    assert "Toova — Venom" in text
    assert "inflict poison" in text
    assert "Source-effect coverage is not established" in text
    assert "Known harmful interaction" in text
    assert "Alternative Zone options" not in text
    assert "Selected skill affinity evidence" in text
    assert "none listed in the inspected source" in text
    assert "unknown or incomplete (unknown)" in text
    assert "Modeled fit: high" in text
    assert "Scorer confidence: medium" in text
    assert "STALE" not in text
    assert "https://example.test/toova#Venom" in html
    assert "https://example.test/mushroom" in html


def test_production_view_reports_missing_diagnostics_without_zero_or_false_affinity():
    result = _feature_e_result()
    result["result_presentation"] = {
        "mode": "production",
        "boss_name": None,
        "boss_source": None,
        "boss_affinities": [],
        "request_coverage": {"status": "unavailable", "metrics": {}, "unknown_data": {}, "note": "unavailable"},
        "explanation_limit": "Fit is heuristic.",
    }
    for recommendation in result["recommendations"]:
        recommendation.pop("strategy_summary", None)
        recommendation["presentation"] = {
            "selected_skill_evidence_status": "unavailable",
            "selected_skill_count": None,
            "joined_skill_count": 0,
            "skills_with_reviewed_capabilities": None,
            "unreviewed_proposal_count": None,
            "skills_without_reviewed_capabilities": [],
            "selected_skills": [],
            "source_effect_coverage": "not_established",
            "candidate": {
                "status": "unavailable",
                "note": "No exact final backend diagnostic was available.",
                "modeled_roles": {}, "modeled_coverage_gaps": [], "component_scores": {},
                "component_score_scope": {}, "scorer_uncertainty_count": None,
                "scorer_uncertainty_scope": None, "selected_skill_matchups": [],
                "selected_skill_matchups_unavailable": True,
            },
            "warnings": [],
        }

    text = _visible_text(_render_result(result))

    assert "Boss affinity evidence is unavailable" in text
    assert "Request coverage and search-pool diversity diagnostics are unavailable" in text
    assert "Selected-skill review diagnostics are unavailable" in text
    assert "No exact final backend diagnostic was available" in text
    assert "0 of" not in text


@pytest.mark.asyncio
async def test_feature_e_streaming_renders_real_recommendation_template():
    """SSE result event uses the real Feature E result partial shape."""
    from src.web.streaming import pipeline_sse_generator

    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    captured_state = {}
    mock_graph = _make_mock_graph_astream(_feature_e_result(), captured_state)

    with patch("src.web.streaming.build_graph", return_value=mock_graph):
        events = []
        async for event in pipeline_sse_generator(
            query="recommend for Flame Eater",
            roster=["Aldo", "Ciel", "Riica", "Shion", "Miyu", "Feinne"],
            driver=MagicMock(),
            templates=templates,
            request=_make_mock_request(),
            owned_sidekicks=["Korobo", "Tetra"],
        ):
            events.append(event)

    result_events = [event for event in events if event.event == "result"]
    assert len(result_events) == 1
    rendered = result_events[0].raw_data
    assert rendered is not None
    assert "Lineup Recommendations" in rendered
    assert rendered.count('class="recommendation-card"') == 3
    assert "Boss Counterplay" in rendered
    assert captured_state["owned_sidekicks"] == ["Korobo", "Tetra"]
