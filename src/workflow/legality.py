"""Roster and lineup legality contracts for recommendation workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .f2p import augment_with_f2p
from .normalize import normalize_character_name, normalize_roster


SAState = Literal["awakened", "not_awakened", "unknown"]


class RosterInput(BaseModel):
    """Structured player ownership input for lineup recommendation."""

    owned_characters: list[str] = Field(min_length=1)
    stellar_awakened: dict[str, SAState | bool] = Field(default_factory=dict)
    owned_sidekicks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _dedupe_inputs(self) -> "RosterInput":
        self.owned_characters = _dedupe(self.owned_characters)
        self.owned_sidekicks = _dedupe(self.owned_sidekicks)
        return self

    @property
    def available_characters(self) -> list[str]:
        """Owned characters plus permanent free-to-play additions."""
        return augment_with_f2p(self.owned_characters)

    def sa_state_for(self, character_name: str) -> SAState:
        """Return the known Stellar Awakening state, defaulting to unknown."""
        raw = self.stellar_awakened.get(character_name, "unknown")
        if raw is True:
            return "awakened"
        if raw is False:
            return "not_awakened"
        return raw


class CharacterBuild(BaseModel):
    """One recommended hero slot and its legal executable choices."""

    name: str
    role: str
    grastas: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    recommended_passives: list[str] = Field(default_factory=list)
    upgrade_assumptions: list[str] = Field(default_factory=list)


class LineupModel(BaseModel):
    """A legal party shape: 4 frontline heroes, 2 reserve heroes, and sidekicks."""

    frontline: list[CharacterBuild] = Field(min_length=4, max_length=4)
    reserve: list[CharacterBuild] = Field(min_length=2, max_length=2)
    main_sidekick: str | None = None
    sub_sidekick: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> "LineupModel":
        hero_names = [slot.name for slot in self.frontline + self.reserve]
        duplicates = sorted({name for name in hero_names if hero_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate heroes are not legal: {', '.join(duplicates)}")
        if self.main_sidekick and self.sub_sidekick and self.main_sidekick == self.sub_sidekick:
            raise ValueError("main_sidekick and sub_sidekick must be different")
        sidekick_names = {name for name in [self.main_sidekick, self.sub_sidekick] if name}
        sidekick_as_hero = sorted(set(hero_names) & sidekick_names)
        if sidekick_as_hero:
            raise ValueError(f"sidekicks cannot occupy hero slots: {', '.join(sidekick_as_hero)}")
        return self

    @property
    def heroes(self) -> list[CharacterBuild]:
        """All six hero slots in battle order."""
        return [*self.frontline, *self.reserve]


class LegalityContext(BaseModel):
    """Graph-derived facts required to validate a proposed lineup."""

    known_characters: set[str] = Field(default_factory=set)
    known_sidekicks: set[str] = Field(default_factory=set)
    character_skills: dict[str, set[str]] = Field(default_factory=dict)
    character_passives: dict[str, set[str]] = Field(default_factory=dict)
    sa_gated_skills: dict[str, set[str]] = Field(default_factory=dict)
    sa_gated_passives: dict[str, set[str]] = Field(default_factory=dict)
    assumed_available_sidekicks: set[str] = Field(default_factory=set)


class LineupLegalityError(ValueError):
    """Raised when a lineup violates roster, sidekick, skill, or SA gates."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


async def build_roster_input(
    driver,
    *,
    owned_characters: list[str],
    stellar_awakened: dict[str, SAState | bool] | None = None,
    owned_sidekicks: list[str] | None = None,
) -> RosterInput:
    """Normalize structured roster ownership while preserving F2P augmentation."""
    normalized_characters = await normalize_roster(driver, owned_characters)
    normalized_sidekicks = await normalize_sidekicks(driver, owned_sidekicks or [])
    normalized_sa = await _normalize_sa_state(driver, stellar_awakened or {})
    return RosterInput(
        owned_characters=normalized_characters,
        stellar_awakened=normalized_sa,
        owned_sidekicks=normalized_sidekicks,
    )


async def normalize_sidekick_name(driver, input_name: str) -> str | None:
    """Resolve a player-supplied sidekick name to the canonical graph name."""
    records, _, _ = await driver.execute_query(
        """
        MATCH (s:Sidekick)
        WHERE toLower(s.name) = toLower($input)
           OR toLower(s.name) CONTAINS toLower($input)
        RETURN s.name AS canonical
        ORDER BY size(s.name) ASC
        LIMIT 1
        """,
        input=input_name,
        database_="neo4j",
    )
    return records[0]["canonical"] if records else None


async def normalize_sidekicks(driver, sidekicks: list[str]) -> list[str]:
    """Normalize sidekick names and drop unknown entries."""
    normalized = []
    for name in sidekicks:
        canonical = await normalize_sidekick_name(driver, name)
        if canonical:
            normalized.append(canonical)
    return _dedupe(normalized)


async def collect_legality_context(
    driver,
    lineup: LineupModel,
    *,
    assumed_available_sidekicks: set[str] | None = None,
) -> LegalityContext:
    """Collect character, sidekick, skill, passive, and SA gates for a lineup."""
    hero_names = [slot.name for slot in lineup.heroes]
    selected_sidekicks = [name for name in [lineup.main_sidekick, lineup.sub_sidekick] if name]
    sidekick_lookup_names = _dedupe([*selected_sidekicks, *hero_names])

    records, _, _ = await driver.execute_query(
        """
        OPTIONAL MATCH (c:Character)
        WHERE c.name IN $hero_names
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(skill:Skill)
        OPTIONAL MATCH (c)-[:HAS_PASSIVE_SKILL]->(passive:PassiveSkill)
        WITH collect(DISTINCT c.name) AS known_characters,
             collect(DISTINCT {
               character: c.name,
               name: skill.name,
               gated: coalesce(skill.requires_stellar_awakened, false)
             }) AS skill_rows,
             collect(DISTINCT {
               character: c.name,
               name: passive.name,
               gated: coalesce(passive.requires_stellar_awakened, false)
             }) AS passive_rows
        OPTIONAL MATCH (s:Sidekick)
        WHERE s.name IN $sidekick_lookup_names
        RETURN known_characters, skill_rows, passive_rows, collect(DISTINCT s.name) AS known_sidekicks
        """,
        hero_names=hero_names,
        sidekick_lookup_names=sidekick_lookup_names,
        database_="neo4j",
    )
    row = records[0] if records else {}
    return LegalityContext(
        known_characters=set(row.get("known_characters", [])),
        known_sidekicks=set(row.get("known_sidekicks", [])),
        character_skills=_rows_to_name_map(row.get("skill_rows", []), gated=False),
        character_passives=_rows_to_name_map(row.get("passive_rows", []), gated=False),
        sa_gated_skills=_rows_to_name_map(row.get("skill_rows", []), gated=True),
        sa_gated_passives=_rows_to_name_map(row.get("passive_rows", []), gated=True),
        assumed_available_sidekicks=assumed_available_sidekicks or set(),
    )


def validate_lineup_legality(
    lineup: LineupModel | dict[str, Any],
    roster: RosterInput,
    context: LegalityContext,
) -> LineupModel:
    """Validate a lineup against ownership, sidekick, skill, passive, and SA facts."""
    candidate = lineup if isinstance(lineup, LineupModel) else LineupModel.model_validate(lineup)
    allowed_heroes = set(roster.available_characters)
    allowed_sidekicks = set(roster.owned_sidekicks) | context.assumed_available_sidekicks
    errors: list[str] = []

    for hero in candidate.heroes:
        if hero.name not in context.known_characters:
            errors.append(f"unknown or hallucinated character: {hero.name}")
        if hero.name in context.known_sidekicks:
            errors.append(f"sidekick cannot occupy a hero slot: {hero.name}")
        if hero.name not in allowed_heroes:
            errors.append(f"character is not owned or F2P-available: {hero.name}")
        errors.extend(_validate_named_choices(
            owner=hero.name,
            selected=hero.recommended_skills,
            known=context.character_skills.get(hero.name, set()),
            gated=context.sa_gated_skills.get(hero.name, set()),
            roster=roster,
            choice_type="skill",
            upgrade_assumptions=hero.upgrade_assumptions,
        ))
        errors.extend(_validate_named_choices(
            owner=hero.name,
            selected=hero.recommended_passives,
            known=context.character_passives.get(hero.name, set()),
            gated=context.sa_gated_passives.get(hero.name, set()),
            roster=roster,
            choice_type="passive",
            upgrade_assumptions=hero.upgrade_assumptions,
        ))

    for slot_name, sidekick in [("main_sidekick", candidate.main_sidekick), ("sub_sidekick", candidate.sub_sidekick)]:
        if not sidekick:
            continue
        if sidekick not in context.known_sidekicks and sidekick not in context.assumed_available_sidekicks:
            errors.append(f"{slot_name} is not a known sidekick: {sidekick}")
        if sidekick not in allowed_sidekicks:
            errors.append(f"{slot_name} is not owned or assumption-available: {sidekick}")

    if errors:
        raise LineupLegalityError(errors)
    return candidate


async def _normalize_sa_state(
    driver,
    stellar_awakened: dict[str, SAState | bool],
) -> dict[str, SAState | bool]:
    normalized: dict[str, SAState | bool] = {}
    for name, state in stellar_awakened.items():
        canonical = await normalize_character_name(driver, name)
        if canonical:
            normalized[canonical] = state
    return normalized


def _validate_named_choices(
    *,
    owner: str,
    selected: list[str],
    known: set[str],
    gated: set[str],
    roster: RosterInput,
    choice_type: str,
    upgrade_assumptions: list[str],
) -> list[str]:
    errors: list[str] = []
    assumption_text = " ".join(upgrade_assumptions).lower()
    for choice in selected:
        if choice not in known:
            errors.append(f"{owner} does not have recommended {choice_type}: {choice}")
        if choice in gated:
            sa_state = roster.sa_state_for(owner)
            if sa_state == "not_awakened":
                errors.append(f"{owner} cannot use SA-gated {choice_type}: {choice}")
            if sa_state == "unknown" and choice.lower() not in assumption_text:
                errors.append(f"{owner} SA state is unknown for gated {choice_type}: {choice}")
    return errors


def _rows_to_name_map(rows: list[dict[str, Any]], *, gated: bool) -> dict[str, set[str]]:
    mapped: dict[str, set[str]] = {}
    for row in rows:
        character = row.get("character")
        name = row.get("name")
        if not character or not name:
            continue
        if gated and not row.get("gated"):
            continue
        mapped.setdefault(character, set()).add(name)
    return mapped


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped
