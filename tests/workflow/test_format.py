"""Unit tests for the FORMAT node.

Covers AGENT-06, AGENT-07:
- format_node returns only {"final_output": ...}
- final_output has frontline, reserve, synergy_explanation
- Pydantic TeamOutput validation on output
- Error path: retry_count >= 3 and empty db_results produces error schema
- Error string contains joined validation_errors
"""
import json
import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch

from src.workflow.legality import LegalityContext
from src.workflow.nodes.format import (
    AlternativesOutput,
    RecommendationSetOutput,
    TeamOutput,
    format_and_validate_node,
    format_node,
)

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



@pytest.fixture
def valid_team_json():
    """A valid JSON team recommendation string as ANALYZE would produce.

    Uses 4 frontline + 2 reserve (the Feature B legal lineup shape).
    """
    return json.dumps(_with_feature_b_build_slots({
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3", "ATK Up"]},
            {"name": "Ciel", "role": "healer", "grastas": ["HP Up"]},
            {"name": "Riica", "role": "support", "grastas": ["SPD Up"]},
            {"name": "Shion", "role": "DPS", "grastas": []},
        ],
        "reserve": [
            {"name": "Miyu", "role": "support", "grastas": []},
            {"name": "Feinne", "role": "healer", "grastas": []},
        ],
        "synergy_explanation": "Aldo as fire DPS anchor with Ciel healing, Riica boosting speed, and Miyu reserve support.",
    }))


@pytest.fixture
def success_state(valid_team_json):
    """WorkflowState on the happy path with a valid analysis_result."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo", "Ciel", "Miyu"],
        "plan_strategy": "Find Fire element characters",
        "cypher_query": "MATCH (c:Character) RETURN c",
        "db_results": [{"c.name": "Aldo"}, {"c.name": "Ciel"}],
        "validation_errors": [],
        "retry_count": 0,
        "analysis_result": valid_team_json,
        "alternatives": "",
        "final_output": {},
    }


@pytest.fixture
def error_state():
    """WorkflowState on the error path: retry cap exhausted, no db_results."""
    return {
        "user_query": "best fire team",
        "roster": ["Aldo"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": ["err1", "err2", "err3"],
        "retry_count": 3,
        "analysis_result": "",
        "alternatives": "",
        "final_output": {},
    }


class TestFormatSuccessPath:
    """format_node on the happy path produces a complete, validated team output."""

    def test_format_success_returns_only_final_output(self, success_state):
        """format_node result must have only the 'final_output' key."""
        result = format_node(success_state)
        assert list(result.keys()) == ["final_output"], (
            f"Expected only 'final_output' key, got: {list(result.keys())}"
        )

    def test_format_success_has_required_keys(self, success_state):
        """final_output must have frontline, reserve, and synergy_explanation."""
        result = format_node(success_state)
        final = result["final_output"]
        assert "frontline" in final, "Missing 'frontline' key"
        assert "reserve" in final, "Missing 'reserve' key"
        assert "synergy_explanation" in final, "Missing 'synergy_explanation' key"

    def test_format_success_frontline_is_list(self, success_state):
        """frontline must be a list."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["frontline"], list), (
            f"Expected frontline to be a list, got: {type(result['final_output']['frontline'])}"
        )

    def test_format_success_reserve_is_list(self, success_state):
        """reserve must be a list."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["reserve"], list), (
            f"Expected reserve to be a list, got: {type(result['final_output']['reserve'])}"
        )

    def test_format_success_synergy_explanation_is_str(self, success_state):
        """synergy_explanation must be a string."""
        result = format_node(success_state)
        assert isinstance(result["final_output"]["synergy_explanation"], str), (
            f"Expected synergy_explanation to be a str"
        )

    def test_format_success_validates_with_pydantic(self, success_state):
        """final_output dict must pass TeamOutput.model_validate without raising."""
        result = format_node(success_state)
        # This must not raise
        validated = TeamOutput.model_validate(result["final_output"])
        assert validated is not None

    def test_format_success_slot_has_name_role_grastas(self, success_state):
        """Each item in frontline/reserve must have name, role, and grastas keys."""
        result = format_node(success_state)
        final = result["final_output"]
        for slot in final["frontline"] + final["reserve"]:
            assert "name" in slot, f"Slot missing 'name': {slot}"
            assert "role" in slot, f"Slot missing 'role': {slot}"
            assert "grastas" in slot, f"Slot missing 'grastas': {slot}"

    def test_format_success_no_error_key(self, success_state):
        """Happy path final_output must not have an 'error' key (or error is None)."""
        result = format_node(success_state)
        final = result["final_output"]
        # error key should either be absent or None
        assert final.get("error") is None, (
            f"Expected no error on happy path, got: {final.get('error')}"
        )


class TestFormatErrorPath:
    """format_node error path: retry cap exhausted with no db_results."""

    def test_format_error_path_on_retry_cap(self, error_state):
        """retry_count >= 3 and no db_results must produce error schema."""
        result = format_node(error_state)
        assert list(result.keys()) == ["final_output"], (
            f"Expected only 'final_output' key, got: {list(result.keys())}"
        )
        final = result["final_output"]
        assert "error" in final, "Expected 'error' key in error-path final_output"

    def test_format_error_path_frontline_is_empty(self, error_state):
        """Error path frontline must be []."""
        result = format_node(error_state)
        assert result["final_output"]["frontline"] == [], (
            f"Expected frontline=[] on error path, got: {result['final_output']['frontline']}"
        )

    def test_format_error_path_reserve_is_empty(self, error_state):
        """Error path reserve must be []."""
        result = format_node(error_state)
        assert result["final_output"]["reserve"] == [], (
            f"Expected reserve=[] on error path, got: {result['final_output']['reserve']}"
        )

    def test_format_error_path_synergy_explanation_is_empty_str(self, error_state):
        """Error path synergy_explanation must be empty string."""
        result = format_node(error_state)
        assert result["final_output"]["synergy_explanation"] == "", (
            f"Expected synergy_explanation='' on error path"
        )

    def test_format_error_contains_validation_errors(self, error_state):
        """Error string must contain the joined validation_errors."""
        result = format_node(error_state)
        error_str = result["final_output"]["error"]
        # All validation error strings should be in the error output
        for err in error_state["validation_errors"]:
            assert err in error_str, (
                f"Expected '{err}' to appear in error string. Got: {error_str!r}"
            )

    def test_format_error_path_is_pydantic_valid(self, error_state):
        """Error schema must have the correct keys and types (frontline=[], reserve=[] by design)."""
        result = format_node(error_state)
        final = result["final_output"]
        assert "frontline" in final and isinstance(final["frontline"], list)
        assert "reserve" in final and isinstance(final["reserve"], list)
        assert "synergy_explanation" in final
        assert "error" in final

    def test_format_no_error_path_when_retry_count_2(self, error_state):
        """retry_count=2 (below cap) should NOT trigger error path even with no db_results."""
        state = dict(error_state)
        state["retry_count"] = 2
        state["analysis_result"] = json.dumps(_with_feature_b_build_slots({
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
                {"name": "Shion", "role": "DPS", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
                {"name": "Feinne", "role": "healer", "grastas": []},
            ],
            "synergy_explanation": "test",
        }))
        result = format_node(state)
        final = result["final_output"]
        assert final.get("error") is None, (
            f"retry_count=2 should NOT produce error path output, got: {final.get('error')}"
        )


class TestTeamOutputPydanticModel:
    """Direct tests for the TeamOutput Pydantic model."""

    def test_team_output_valid_structure(self):
        """TeamOutput.model_validate must accept a valid team dict."""
        data = _with_feature_b_build_slots({
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
                {"name": "Shion", "role": "DPS", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
                {"name": "Feinne", "role": "healer", "grastas": []},
            ],
            "synergy_explanation": "Fire synergy.",
        })
        output = TeamOutput.model_validate(data)
        assert output.frontline[0].name == "Aldo"
        assert output.reserve[0].name == "Miyu"
        assert output.synergy_explanation == "Fire synergy."

    def test_team_output_optional_error_field(self):
        """TeamOutput error field is optional and accepts a string value."""
        data = _with_feature_b_build_slots({
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
                {"name": "Shion", "role": "DPS", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
                {"name": "Feinne", "role": "healer", "grastas": []},
            ],
            "synergy_explanation": "",
            "error": "Query failed",
        })
        output = TeamOutput.model_validate(data)
        assert output.error == "Query failed"

    def test_team_output_error_defaults_to_none(self):
        """TeamOutput error field defaults to None when not provided."""
        data = _with_feature_b_build_slots({
            "frontline": [
                {"name": "Aldo", "role": "DPS", "grastas": []},
                {"name": "Ciel", "role": "healer", "grastas": []},
                {"name": "Riica", "role": "support", "grastas": []},
                {"name": "Shion", "role": "DPS", "grastas": []},
            ],
            "reserve": [
                {"name": "Miyu", "role": "support", "grastas": []},
                {"name": "Feinne", "role": "healer", "grastas": []},
            ],
            "synergy_explanation": "test",
        })
        output = TeamOutput.model_validate(data)
        assert output.error is None


def _slot(name="X"):
    return _with_feature_b_build_slots({"name": name, "role": "DPS", "grastas": []})


class TestTeamOutputLengthValidators:
    """Feature B: TeamOutput must enforce exactly 4 frontline and 2 reserve."""

    def test_rejects_two_frontline(self):
        with pytest.raises(ValidationError):
            TeamOutput(
                frontline=[_slot("A"), _slot("B")],
                reserve=[_slot("C")],
                synergy_explanation="too few frontline",
            )

    def test_rejects_five_frontline(self):
        with pytest.raises(ValidationError):
            TeamOutput(
                frontline=[_slot(n) for n in "ABCDE"],
                reserve=[_slot("F")],
                synergy_explanation="too many frontline",
            )

    def test_rejects_zero_reserve(self):
        with pytest.raises(ValidationError):
            TeamOutput(
                frontline=[_slot(n) for n in "ABC"],
                reserve=[],
                synergy_explanation="empty reserve",
            )

    def test_rejects_three_reserve(self):
        with pytest.raises(ValidationError):
            TeamOutput(
                frontline=[_slot(n) for n in "ABC"],
                reserve=[_slot(n) for n in "DEF"],
                synergy_explanation="too many reserve",
            )

    def test_accepts_exact_valid_shape(self):
        t = TeamOutput(
            frontline=[_slot(n) for n in "ABCD"],
            reserve=[_slot(n) for n in "EF"],
            synergy_explanation="valid",
        )
        assert len(t.frontline) == 4
        assert len(t.reserve) == 2


class TestFormatNodeHandlesMalformedTeam:
    """Gap 2: format_node must catch ValidationError AND ValueError and return error schema."""

    def _base_state(self, analysis_result):
        return {
            "user_query": "q",
            "roster": [],
            "plan_strategy": "",
            "cypher_query": "",
            "db_results": [{"x": 1}],
            "analysis_result": analysis_result,
            "alternatives": "",
            "retry_count": 0,
            "validation_errors": [],
        }

    def test_malformed_team_returns_error_schema(self):
        """ValidationError path: valid JSON but wrong shape (2 frontline, 1 reserve)."""
        import json as _json
        bad_analysis = _json.dumps({
            "frontline": [_slot("A"), _slot("B")],   # only 2 — invalid
            "reserve": [_slot("C")],
            "synergy_explanation": "bad shape",
        })
        result = format_node(self._base_state(bad_analysis))
        error = result["final_output"]["error"]
        assert "LLM returned malformed team structure" in error
        assert "frontline: List should have at least 4 items" in error
        assert "reserve: List should have at least 2 items" in error

    def test_completes_two_grasta_slots_with_reusable_copy(self):
        payload = _feature_d_payload()
        payload["recommendations"][0]["frontline"][2]["grastas"] = [
            "Power of Mind",
            "Power of Mind",
        ]

        result = format_node(self._base_state(json.dumps(payload)))

        grastas = result["final_output"]["recommendations"][0]["frontline"][2]["grastas"]
        assert grastas == ["Power of Mind", "Power of Mind", "Power of Mind"]

    def test_extracts_names_from_graph_style_skill_and_passive_records(self):
        payload = _feature_d_payload()
        hero = payload["recommendations"][0]["frontline"][0]
        hero["recommended_skills"] = [
            {"name": "Blaze Sword", "description": "Fire slash attack."}
        ]
        hero["recommended_passives"] = [
            {"name": "Fire Zone", "description": "Deploys Fire Zone."}
        ]

        result = format_node(self._base_state(json.dumps(payload)))

        normalized = result["final_output"]["recommendations"][0]["frontline"][0]
        assert normalized["recommended_skills"] == ["Blaze Sword"]
        assert normalized["recommended_passives"] == ["Fire Zone"]

    def test_rejects_graph_style_choice_without_name(self):
        payload = _feature_d_payload()
        payload["recommendations"][0]["frontline"][0]["recommended_passives"] = [
            {"description": "Missing passive name."}
        ]

        result = format_node(self._base_state(json.dumps(payload)))

        assert "recommended_passives.0" in result["final_output"]["error"]

    def test_does_not_invent_grasta_when_model_supplies_none(self):
        payload = _feature_d_payload()
        payload["recommendations"][0]["frontline"][2]["grastas"] = []

        result = format_node(self._base_state(json.dumps(payload)))

        assert "at least 3 items" in result["final_output"]["error"]

    def test_non_json_llm_response_returns_error_schema(self):
        """ValueError path: _extract_json raises when LLM returns completely non-JSON text."""
        result = format_node(self._base_state("Sorry I cannot help"))
        assert result["final_output"]["error"] == (
            "LLM returned malformed team structure: analyzer did not return a valid JSON object"
        )

    def test_truncated_json_reports_likely_truncation(self):
        result = format_node(self._base_state('{"recommendations": [{"frontline": ['))

        assert result["final_output"]["error"] == (
            "LLM returned malformed team structure: analyzer returned incomplete JSON "
            "(the response appears to be truncated)"
        )


@pytest.fixture
def valid_alternatives_json():
    team = _with_feature_b_build_slots({
        "frontline": [
            {"name": "Aldo", "role": "DPS", "grastas": ["Fire T3"]},
            {"name": "Ciel", "role": "healer", "grastas": ["HP Up"]},
            {"name": "Riica", "role": "support", "grastas": []},
            {"name": "Shion", "role": "DPS", "grastas": []},
        ],
        "reserve": [
            {"name": "Miyu", "role": "support", "grastas": []},
            {"name": "Feinne", "role": "healer", "grastas": []},
        ],
        "synergy_explanation": "Aldo: Fire T3 Grasta (Courage) — boosts Fire damage.",
    })
    return json.dumps({
        "alternatives": [team, team, team],
        "reason": "No Cypher results for highly specific query.",
    })


@pytest.fixture
def alternatives_state(valid_alternatives_json):
    return {
        "user_query": "best fire team",
        "roster": ["Aldo"],
        "plan_strategy": "",
        "cypher_query": "",
        "db_results": [],
        "validation_errors": [],
        "retry_count": 3,
        "analysis_result": "",
        "alternatives": valid_alternatives_json,
        "final_output": {},
    }


class TestFormatAlternativesPath:
    """format_node alternatives path: alternatives key set produces AlternativesOutput."""

    def test_format_alternatives_returns_only_final_output(self, alternatives_state):
        result = format_node(alternatives_state)
        assert list(result.keys()) == ["final_output"]

    def test_format_alternatives_has_alternatives_key(self, alternatives_state):
        result = format_node(alternatives_state)
        assert "alternatives" in result["final_output"], "Missing 'alternatives' key"

    def test_format_alternatives_has_exactly_three(self, alternatives_state):
        result = format_node(alternatives_state)
        assert len(result["final_output"]["alternatives"]) == 3

    def test_format_alternatives_validates_with_pydantic(self, alternatives_state):
        result = format_node(alternatives_state)
        validated = AlternativesOutput.model_validate(result["final_output"])
        assert validated is not None

    def test_format_alternatives_no_error(self, alternatives_state):
        result = format_node(alternatives_state)
        assert result["final_output"].get("error") is None


def _feature_d_team(archetype="burst", *, suffix="A"):
    return _with_feature_b_build_slots({
        "archetype": archetype,
        "frontline": [
            {
                "name": f"Aldo {suffix}",
                "role": "Fire slash DPS",
                "grastas": ["Fire Power Grasta with Bull's Eye Ore"],
                "recommended_skills": ["Dragon God Slash", "Volcano Blade", "X Slash"],
            },
            {
                "name": f"Ciel {suffix}",
                "role": "buff and debuff support",
                "grastas": ["Support Grasta"],
                "recommended_skills": ["Elemental Song", "Heart Break", "Speed Song"],
            },
            {
                "name": f"Riica {suffix}",
                "role": "mitigation and emergency healing",
                "grastas": ["HP Up Grasta"],
                "recommended_skills": ["Guard Protocol", "Power Heal", "Mind Stamp"],
            },
            {
                "name": f"Shion {suffix}",
                "role": "secondary fire slash pressure",
                "grastas": ["Fire Power Grasta"],
                "recommended_skills": ["Phoenix Slash", "Scarlet Blade", "Roaring Slash"],
            },
        ],
        "reserve": [
            {
                "name": f"Miyu {suffix}",
                "role": "reserve slash support",
                "grastas": ["Pain Grasta"],
                "recommended_skills": ["Rune Blade", "Princess Bloom", "Flame Slash"],
            },
            {
                "name": f"Feinne {suffix}",
                "role": "reserve healer",
                "grastas": ["MP Recovery Grasta"],
                "recommended_skills": ["Refresh", "Heal", "Angel Song"],
            },
        ],
        "main_sidekick": "Tetra",
        "sub_sidekick": "Korobo",
        "strategy_summary": f"{archetype.title()} plan that pressures weakness while preserving fallback sustain.",
        "key_facts": ["Aldo has fire slash pressure; Tetra contributes main-slot support."],
        "build_notes": ["Assumes common late-game Pain/Poison Grasta and Bull's Eye Ore access; Poison Edge applies poison as an explicit build assumption for the multiplier setup."],
        "boss_counterplay_notes": ["Targets Fire and Slash weakness while avoiding Water resistance."],
        "sustain_mp_notes": ["Feinne and Riica cover healing while reserve swapping protects MP."],
        "risks": ["Status cleanse timing is still player-executed and uncertain."],
        "fit_label": "high",
        "confidence_label": "medium",
        "rubric_summary": {
            "offense": "high - Fire and Slash cover graph weakness.",
            "defense": "medium - mitigation and healing are present.",
            "synergy": "high - slash pressure and support roles align.",
            "sustain": "medium - recovery exists but timing matters.",
            "mp": "medium - reserve swapping helps MP stability.",
            "sidekick": "high - main and sub sidekick slots contribute.",
            "build_readiness": "medium - assumes common late-game Grasta/Ore access.",
            "upgrade_burden": "low - no SA-only skill is required.",
        },
        "citations": [
            {"label": "Flame Eater", "source_url": "https://example.test/flame-eater"},
            {"label": "Weakness Handling", "source_url": "https://example.test/affinity"},
        ],
        "synergy_explanation": (
            f"Aldo {suffix}: Fire Power Grasta (Courage) - supports fire slash pressure. "
            f"Ciel {suffix}: Support Grasta (Minstrel) - supports buffs and debuffs."
        ),
    })


def _feature_d_payload():
    return {
        "boss_affinity": {
            "weak": ["Fire", "Slash"],
            "resist": ["Water"],
            "null": ["Thunder"],
            "absorb": ["Earth"],
        },
        "archetype_viability_notes": [],
        "recommendations": [
            _feature_d_team("burst", suffix="A"),
            _feature_d_team("sustain", suffix="B"),
            _feature_d_team("hybrid", suffix="C"),
        ],
    }


def _feature_d_roster_names(payload):
    return [
        slot["name"]
        for recommendation in payload["recommendations"]
        for slot in recommendation["frontline"] + recommendation["reserve"]
    ]


def _feature_d_skill_map(payload):
    return {
        slot["name"]: set(slot.get("recommended_skills", []))
        for recommendation in payload["recommendations"]
        for slot in recommendation["frontline"] + recommendation["reserve"]
    }


def _feature_d_grasta_names(payload):
    return {
        grasta
        for recommendation in payload["recommendations"]
        for slot in recommendation["frontline"] + recommendation["reserve"]
        for grasta in slot.get("grastas", [])
    }


def _boss_context_payload():
    return json.dumps({
        "boss": {
            "name": "Flame Eater",
            "source_url": "https://example.test/flame-eater",
            "weak": ["Fire", "Slash"],
            "resist": ["Water"],
            "null": ["Thunder"],
            "absorb": ["Earth"],
            "characteristics": "Weak superboss fixture for recommendation tests.",
            "mechanic_tags": ["weakness", "sustain"],
            "mechanics_text": "Punishes unsupported elements and rewards fire slash pressure.",
        }
    })


class TestFeatureDRecommendationSet:
    """Feature D: format_node validates the top-3 lineup recommendation contract."""

    def _state(self, payload):
        return {
            "analysis_result": json.dumps(payload),
            "db_results": [{"ok": True}],
            "retry_count": 0,
            "alternatives": "",
            "validation_errors": [],
        }

    def test_format_node_accepts_top_three_archetype_recommendations(self):
        result = format_node(self._state(_feature_d_payload()))
        final = result["final_output"]

        validated = RecommendationSetOutput.model_validate(final)
        assert validated.error is None
        assert final["boss_affinity"] == {
            "weak": ["Fire", "Slash"],
            "resist": ["Water"],
            "null": ["Thunder"],
            "absorb": ["Earth"],
        }
        assert [rec["archetype"] for rec in final["recommendations"]] == ["burst", "sustain", "hybrid"]
        for rec in final["recommendations"]:
            assert len(rec["frontline"]) == 4
            assert len(rec["reserve"]) == 2
            assert rec["strategy_summary"]
            assert rec["build_notes"]
            assert rec["boss_counterplay_notes"]
            assert rec["sustain_mp_notes"]
            assert rec["risks"]
            assert rec["citations"]
            assert rec["fit_label"] in {"high", "medium", "low"}
            assert rec["confidence_label"] in {"high", "medium", "low"}

    def test_fills_missing_citations_from_grounded_boss_context(self):
        payload = _feature_d_payload()
        for recommendation in payload["recommendations"]:
            recommendation["citations"] = []

        state = self._state(payload)
        state["boss_context"] = _boss_context_payload()
        result = format_node(state)

        for recommendation in result["final_output"]["recommendations"]:
            assert recommendation["citations"] == [{
                "label": "Flame Eater",
                "source_url": "https://example.test/flame-eater",
            }]

    def test_still_rejects_missing_citations_without_grounded_context(self):
        payload = _feature_d_payload()
        for recommendation in payload["recommendations"]:
            recommendation["citations"] = []

        result = format_node(self._state(payload))

        assert "each recommendation must include source citations" in result["final_output"]["error"]

    def test_rejects_missing_required_feature_d_detail(self):
        payload = _feature_d_payload()
        payload["recommendations"][0]["build_notes"] = []

        result = format_node(self._state(payload))

        assert "each recommendation must include build notes" in result["final_output"]["error"]

    def test_allows_archetype_variants_only_with_viability_notes(self):
        payload = _feature_d_payload()
        payload["recommendations"] = [
            _feature_d_team("burst", suffix="A"),
            _feature_d_team("burst", suffix="B"),
            _feature_d_team("hybrid", suffix="C"),
        ]
        payload["archetype_viability_notes"] = [
            "Sustain is weaker because the boss punishes long setup; second burst variant is provided."
        ]

        result = format_node(self._state(payload))

        assert result["final_output"].get("error") is None
        assert [rec["archetype"] for rec in result["final_output"]["recommendations"]] == ["burst", "burst", "hybrid"]

    def test_rejects_archetype_variants_without_viability_notes(self):
        payload = _feature_d_payload()
        payload["recommendations"][1]["archetype"] = "burst"

        result = format_node(self._state(payload))

        assert "variant recommendations require archetype_viability_notes" in result["final_output"]["error"]


class TestBossAffinityFidelityGate:
    """Feature C: final output boss affinities must remain equal to graph facts."""

    @staticmethod
    def _context(payload):
        return LegalityContext(
            known_characters=set(_feature_d_roster_names(payload)),
            known_sidekicks={"Tetra", "Korobo"},
            character_skills=_feature_d_skill_map(payload),
            known_grastas=_feature_d_grasta_names(payload),
        )

    @staticmethod
    def _state(payload):
        return {
            "analysis_result": json.dumps(payload),
            "boss_context": _boss_context_payload(),
            "roster": _feature_d_roster_names(payload),
            "owned_sidekicks": ["Tetra", "Korobo"],
            "db_results": [{"ok": True}],
            "retry_count": 0,
            "alternatives": "",
            "validation_errors": [],
        }

    @pytest.mark.asyncio
    async def test_matching_affinity_passes_case_and_order_insensitive(self):
        payload = _feature_d_payload()
        payload["boss_affinity"] = {
            "weak": ["slash", "FIRE"],
            "resist": ["water"],
            "null": ["THUNDER"],
            "absorb": ["earth"],
        }
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(payload),
        ):
            result = await format_and_validate_node(self._state(payload), driver)

        assert result["final_output"].get("error") is None

    @pytest.mark.asyncio
    async def test_mismatched_affinity_is_blocked_before_rendering(self):
        payload = _feature_d_payload()
        payload["boss_affinity"]["weak"] = ["Water"]
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(payload),
        ):
            result = await format_and_validate_node(self._state(payload), driver)

        final = result["final_output"]
        assert final["frontline"] == []
        assert final["reserve"] == []
        assert "boss affinity facts do not match graph facts" in final["error"]
        assert "recommendation_set.weak" in final["error"]

    @pytest.mark.asyncio
    async def test_empty_affinity_matches_graph_unknown_sentinel(self):
        payload = _feature_d_payload()
        payload["boss_affinity"] = {
            "weak": [],
            "resist": [],
            "null": [],
            "absorb": [],
        }
        state = self._state(payload)
        boss_context = json.loads(state["boss_context"])
        for field in ("weak", "resist", "null", "absorb"):
            boss_context["boss"][field] = ["unknown"]
        state["boss_context"] = json.dumps(boss_context)
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(payload),
        ):
            result = await format_and_validate_node(state, driver)

        assert result["final_output"].get("error") is None

    @pytest.mark.asyncio
    async def test_empty_affinity_output_is_blocked_when_graph_has_facts(self):
        payload = _feature_d_payload()
        payload["boss_affinity"] = {}
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(payload),
        ):
            result = await format_and_validate_node(self._state(payload), driver)

        assert "boss affinity facts do not match graph facts" in result["final_output"]["error"]
        assert "recommendation_set.weak" in result["final_output"]["error"]


class TestProductionLegalityGate:
    """The production FORMAT wrapper blocks graph- or roster-illegal LLM output."""

    @staticmethod
    def _context(*, skills=None):
        return LegalityContext(
            known_characters={"Aldo", "Ciel", "Riica", "Shion", "Miyu", "Feinne"},
            character_skills=skills or {},
            known_grastas={"Fire T3", "ATK Up", "HP Up", "SPD Up", "Power of Mind"},
        )

    @pytest.mark.asyncio
    async def test_legal_lineup_passes_before_final_output(self, success_state):
        state = dict(success_state)
        state["roster"] = ["Aldo", "Ciel", "Riica", "Shion", "Miyu", "Feinne"]
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(),
        ) as collect_context:
            result = await format_and_validate_node(state, driver)

        assert result["final_output"].get("error") is None
        collect_context.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unowned_llm_character_is_blocked(self, success_state):
        state = dict(success_state)
        state["roster"] = ["Aldo", "Ciel"]
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(),
        ):
            result = await format_and_validate_node(state, driver)

        final = result["final_output"]
        assert final["frontline"] == []
        assert final["reserve"] == []
        assert "not owned or F2P-available" in final["error"]

    @pytest.mark.asyncio
    async def test_unsupported_skill_is_blocked(self, success_state):
        payload = json.loads(success_state["analysis_result"])
        payload["frontline"][0]["recommended_skills"] = ["Imaginary Slash"]
        state = dict(success_state)
        state["analysis_result"] = json.dumps(payload)
        state["roster"] = ["Aldo", "Ciel", "Riica", "Shion", "Miyu", "Feinne"]
        driver = MagicMock()

        with patch(
            "src.workflow.nodes.format.collect_legality_context",
            new_callable=AsyncMock,
            return_value=self._context(skills={"Aldo": {"X Slash"}}),
        ):
            result = await format_and_validate_node(state, driver)

        assert "does not have recommended skill: Imaginary Slash" in result["final_output"]["error"]
