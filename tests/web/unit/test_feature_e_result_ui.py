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
    return {
        "name": name,
        "role": role,
        "grastas": grastas or [],
        "recommended_skills": [f"{name} Skill"],
        "recommended_passives": [f"{name} Passive"],
        "upgrade_assumptions": [],
    }


def _minimal_slot(name: str, role: str) -> dict:
    return {
        "name": name,
        "role": role,
        "grastas": [],
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
    assert "Top 3 Lineup Recommendations" in text
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
    assert "Aldo: Fire T3" in text
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
    assert "Error details" in text
    assert "LLM returned malformed team structure" in text
    assert "recommendation-card" not in html


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
    assert "Top 3 Lineup Recommendations" in rendered
    assert rendered.count('class="recommendation-card"') == 3
    assert "Boss Counterplay" in rendered
    assert captured_state["owned_sidekicks"] == ["Korobo", "Tetra"]
