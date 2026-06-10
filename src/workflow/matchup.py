"""Boss matchup retrieval and transparent fit rubric helpers."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from .legality import LineupModel
from .mechanics import retrieve_mechanic_references


FitLabel = Literal["high", "medium", "low"]


class BossFacts(BaseModel):
    """Graph-derived boss facts used for matchup-aware recommendations."""

    name: str
    source_url: str
    weak: list[str] = Field(default_factory=list)
    resist: list[str] = Field(default_factory=list)
    null: list[str] = Field(default_factory=list)
    absorb: list[str] = Field(default_factory=list)
    characteristics: str = ""
    mechanic_tags: list[str] = Field(default_factory=list)
    mechanics_text: str = ""


class MatchupRubric(BaseModel):
    """Transparent fit signals for ranking, not win-probability prediction."""

    legality_gate: FitLabel
    boss_matchup_offense: FitLabel
    boss_matchup_defense: FitLabel
    lineup_synergy: FitLabel
    sustain_and_recovery: FitLabel
    mp_sustainability: FitLabel
    sidekick_contribution: FitLabel
    grasta_ore_equipment_readiness: FitLabel
    uncertainty_or_missing_data_penalty: FitLabel
    upgrade_burden_penalty: FitLabel
    confidence: FitLabel
    risk_notes: list[str] = Field(default_factory=list)


class MatchupContext(BaseModel):
    """Combined boss, mechanics, and rubric guidance for the analyzer."""

    boss: BossFacts | None = None
    mechanic_references: list[dict[str, Any]] = Field(default_factory=list)
    rubric: MatchupRubric
    rubric_guidance: list[str]
    citations: list[dict[str, str]] = Field(default_factory=list)
    score_semantics: str = "Fit labels are ranking/navigation signals, not success probabilities."


RUBRIC_GUIDANCE = [
    "Run legality first; illegal lineups are not rankable.",
    "Prioritize boss weakness coverage and penalize resist, null, or absorb conflicts.",
    "Reward mitigation, resistance, cleanse, status handling, healing, and long-fight stability when boss mechanics call for them.",
    "Separate usable facts from upgrade assumptions, missing data, and late-game build assumptions.",
    "Never present fit labels or internal scores as numeric win probability.",
]


def default_rubric(*, has_boss: bool, has_mechanics: bool) -> MatchupRubric:
    """Return conservative baseline labels before a specific lineup is evaluated."""
    risk_notes: list[str] = []
    uncertainty = "low"
    confidence = "medium"
    if not has_boss:
        risk_notes.append("No selected Superboss graph facts were retrieved.")
        uncertainty = "high"
        confidence = "low"
    if not has_mechanics:
        risk_notes.append("No matching MechanicReference rows were retrieved.")
        uncertainty = "medium" if has_boss else "high"
        confidence = "medium" if has_boss else "low"

    return MatchupRubric(
        legality_gate="high",
        boss_matchup_offense="medium" if has_boss else "low",
        boss_matchup_defense="medium" if has_boss else "low",
        lineup_synergy="medium",
        sustain_and_recovery="medium",
        mp_sustainability="medium",
        sidekick_contribution="medium",
        grasta_ore_equipment_readiness="medium",
        uncertainty_or_missing_data_penalty=uncertainty,
        upgrade_burden_penalty="medium",
        confidence=confidence,
        risk_notes=risk_notes,
    )


def evaluate_lineup_fit(
    lineup: LineupModel,
    boss: BossFacts | None,
    *,
    mechanic_references: list[dict[str, Any]] | None = None,
    legality_passed: bool = True,
) -> MatchupRubric:
    """Evaluate a candidate lineup with transparent labels, never probabilities."""
    if not legality_passed:
        return MatchupRubric(
            legality_gate="low",
            boss_matchup_offense="low",
            boss_matchup_defense="low",
            lineup_synergy="low",
            sustain_and_recovery="low",
            mp_sustainability="low",
            sidekick_contribution="low",
            grasta_ore_equipment_readiness="low",
            uncertainty_or_missing_data_penalty="high",
            upgrade_burden_penalty="high",
            confidence="low",
            risk_notes=["Lineup failed the legality gate and should not be recommended."],
        )

    references = mechanic_references or []
    hero_text = " ".join(
        " ".join([hero.name, hero.role, *hero.recommended_skills, *hero.recommended_passives, *hero.grastas])
        for hero in lineup.heroes
    ).lower()
    elements = _known_elements(hero_text)
    risk_notes: list[str] = []

    if boss is None:
        risk_notes.append("Boss affinity facts are missing, so matchup fit is conservative.")
        offense = "low"
        defense = "low"
        uncertainty = "high"
        confidence = "low"
    else:
        weak = _clean_affinity(boss.weak)
        blocked = _clean_affinity([*boss.resist, *boss.null, *boss.absorb])
        weak_hits = sorted(elements & weak)
        blocked_hits = sorted(elements & blocked)
        offense = "low" if blocked_hits else "high" if weak_hits else "low"
        if blocked_hits:
            risk_notes.append(f"Potential affinity conflicts: {', '.join(blocked_hits)}.")
        if not weak_hits:
            risk_notes.append("No explicit boss weakness coverage was visible in the lineup text.")
        defense = _defense_label(hero_text, boss)
        uncertainty = "low" if boss.mechanics_text and references else "medium"
        confidence = "high" if offense == "high" and uncertainty == "low" else "medium"

    upgrade_burden = "high" if any(hero.upgrade_assumptions for hero in lineup.heroes) else "low"

    return MatchupRubric(
        legality_gate="high",
        boss_matchup_offense=offense,
        boss_matchup_defense=defense,
        lineup_synergy=_keyword_label(hero_text, ["zone", "stance", "af", "another force", "buff", "debuff"]),
        sustain_and_recovery=_keyword_label(hero_text, ["heal", "regen", "barrier", "shield", "mitigation", "restore"]),
        mp_sustainability=_keyword_label(hero_text, ["mp", "restore", "cost", "reduction", "regen"]),
        sidekick_contribution="high" if lineup.main_sidekick and lineup.sub_sidekick else "medium" if lineup.main_sidekick else "low",
        grasta_ore_equipment_readiness=_keyword_label(hero_text, ["grasta", "ore", "equipment", "weapon", "armor"]),
        uncertainty_or_missing_data_penalty=uncertainty,
        upgrade_burden_penalty=upgrade_burden,
        confidence=confidence,
        risk_notes=risk_notes,
    )


async def retrieve_matchup_context(driver, query: str) -> MatchupContext:
    """Retrieve selected boss facts and mechanics references from the graph."""
    boss = await retrieve_selected_boss_facts(driver, query)
    mechanic_references: list[dict[str, Any]] = []
    if boss:
        mechanic_references = await retrieve_mechanic_references(
            driver,
            topic_tags=[*boss.mechanic_tags, *_clean_affinity([*boss.weak, *boss.resist, *boss.null, *boss.absorb])],
            applies_to=[
                "boss_counterplay",
                "lineup_recommendation",
                "lineup_legality",
                "sustain",
                "build_context",
            ],
            mechanic_types=["affinity", "support", "status", "sustain", "burst", "sidekick", "build_context"],
            limit=8,
        )

    citations = []
    if boss:
        citations.append({"label": boss.name, "source_url": boss.source_url})
    citations.extend(
        {"label": reference.get("title", reference.get("id", "MechanicReference")), "source_url": reference.get("source_url", "")}
        for reference in mechanic_references
        if reference.get("source_url")
    )

    return MatchupContext(
        boss=boss,
        mechanic_references=mechanic_references,
        rubric=default_rubric(has_boss=boss is not None, has_mechanics=bool(mechanic_references)),
        rubric_guidance=RUBRIC_GUIDANCE,
        citations=citations,
    )


async def retrieve_selected_boss_facts(driver, query: str) -> BossFacts | None:
    """Find the selected Superboss by name mention and return graph facts."""
    if driver is None or not _looks_like_boss_query(query):
        return None

    records, _, _ = await driver.execute_query(
        """
        MATCH (s:Superboss)
        WHERE toLower($query) CONTAINS toLower(s.name)
           OR any(token IN split(toLower(s.name), ' ') WHERE size(token) >= 4 AND toLower($query) CONTAINS token)
        RETURN s {
            .name,
            .source_url,
            .weak,
            .resist,
            .null,
            .absorb,
            .characteristics,
            .mechanic_tags,
            .mechanics_text
        } AS boss
        ORDER BY size(s.name) DESC
        LIMIT 1
        """,
        query=query,
        database_="neo4j",
    )
    if not records:
        return None
    return BossFacts.model_validate(records[0]["boss"])


def context_to_json(context: MatchupContext) -> str:
    """Serialize matchup context compactly for LLM prompt injection."""
    return json.dumps(context.model_dump(), ensure_ascii=False)


def _looks_like_boss_query(query: str) -> bool:
    normalized = query.lower()
    return any(word in normalized for word in ["boss", "superboss", "manifest", "fight", "battle", "matchup"])


def _known_elements(text: str) -> set[str]:
    elements = {
        "fire",
        "water",
        "wind",
        "earth",
        "thunder",
        "shade",
        "crystal",
        "light",
        "dark",
        "null",
        "slash",
        "pierce",
        "blunt",
        "magic",
    }
    return {element for element in elements if element in text}


def _clean_affinity(values: list[str]) -> set[str]:
    return {value.lower() for value in values if value and value.lower() != "unknown"}


def _keyword_label(text: str, keywords: list[str]) -> FitLabel:
    hits = sum(1 for keyword in keywords if keyword in text)
    if hits >= 2:
        return "high"
    if hits == 1:
        return "medium"
    return "low"


def _defense_label(text: str, boss: BossFacts) -> FitLabel:
    boss_text = " ".join([boss.characteristics, boss.mechanics_text, *boss.mechanic_tags]).lower()
    defensive_need = any(
        keyword in boss_text
        for keyword in ["status", "poison", "pain", "stun", "seal", "damage", "fixed", "debuff", "zone"]
    )
    if not defensive_need:
        return "medium"
    return _keyword_label(text, ["heal", "cleanse", "status", "mitigation", "barrier", "resistance", "debuff"])
