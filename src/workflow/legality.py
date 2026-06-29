"""Roster and lineup legality contracts for recommendation workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .f2p import augment_with_f2p
from .normalize import normalize_character_name, normalize_roster


SAState = Literal["awakened", "not_awakened", "unknown"]

WEAPON_TYPES = {"Sword", "Blade", "Bow", "Spear", "Hammer", "Staff", "Mace", "Tome", "Fist", "Katana", "Axe"}
ARMOR_TYPES = {"Bracelet", "Bangle", "Ring", "Necklace", "Armor", "Weapon"}
GENERIC_EQUIPMENT_PREFIXES = (
    "any ",
    "available ",
    "best available",
    "best ",
    "generic ",
    "matching ",
    "recommended ",
    "suitable ",
    "unspecified",
)
GENERIC_EQUIPMENT_VALUES = (
    {"n/a", "none", "unknown", "unspecified", "any", "best available"}
    | {category.lower() for category in WEAPON_TYPES | ARMOR_TYPES}
)



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
    """One recommended hero slot and its legal executable and build choices."""

    name: str
    role: str
    weapon: str = Field(min_length=1)
    armor: str = Field(min_length=1)
    grastas: list[str] = Field(min_length=3, max_length=3)
    recommended_skills: list[str] = Field(default_factory=list)
    recommended_passives: list[str] = Field(default_factory=list)
    upgrade_assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_build_slots(self) -> "CharacterBuild":
        self.weapon = self.weapon.strip()
        self.armor = self.armor.strip()
        self.grastas = [grasta.strip() for grasta in self.grastas]
        if not self.weapon:
            raise ValueError(f"{self.name} must include one weapon assumption")
        if not self.armor:
            raise ValueError(f"{self.name} must include one armor assumption")
        blank_grastas = [index for index, grasta in enumerate(self.grastas, start=1) if not grasta]
        if blank_grastas:
            raise ValueError(f"{self.name} has blank Grasta slots: {blank_grastas}")
        return self


class LineupModel(BaseModel):
    """A legal party shape: 4 frontline heroes, 2 reserve heroes, and sidekicks."""

    frontline: list[CharacterBuild] = Field(min_length=4, max_length=4)
    reserve: list[CharacterBuild] = Field(min_length=2, max_length=2)
    main_sidekick: str | None = None
    sub_sidekick: str | None = None
    build_notes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

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
        duplicate_weapons = _duplicate_specific_equipment({slot.name: slot.weapon for slot in self.heroes})
        if duplicate_weapons:
            raise ValueError(f"specific weapons cannot repeat within one lineup: {', '.join(duplicate_weapons)}")
        duplicate_armors = _duplicate_specific_equipment({slot.name: slot.armor for slot in self.heroes})
        if duplicate_armors:
            raise ValueError(f"specific armor cannot repeat within one lineup: {', '.join(duplicate_armors)}")
        return self

    @property
    def heroes(self) -> list[CharacterBuild]:
        """All six hero slots in battle order."""
        return [*self.frontline, *self.reserve]


class LegalityContext(BaseModel):
    """Graph-derived facts required to validate a proposed lineup."""

    known_characters: set[str] = Field(default_factory=set)
    known_sidekicks: set[str] = Field(default_factory=set)
    character_weapons: dict[str, str] = Field(default_factory=dict)
    character_traits: dict[str, set[str]] = Field(default_factory=dict)
    character_skills: dict[str, set[str]] = Field(default_factory=dict)
    character_passives: dict[str, set[str]] = Field(default_factory=dict)
    sa_gated_skills: dict[str, set[str]] = Field(default_factory=dict)
    sa_gated_passives: dict[str, set[str]] = Field(default_factory=dict)
    known_grastas: set[str] = Field(default_factory=set)
    grasta_personality_reqs: dict[str, str] = Field(default_factory=dict)
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
    """Collect character, sidekick, skill, passive, Grasta, and SA gates for a lineup."""
    hero_names = [slot.name for slot in lineup.heroes]
    grasta_names = _dedupe([grasta for slot in lineup.heroes for grasta in slot.grastas])
    selected_sidekicks = [name for name in [lineup.main_sidekick, lineup.sub_sidekick] if name]
    sidekick_lookup_names = _dedupe([*selected_sidekicks, *hero_names])

    records, _, _ = await driver.execute_query(
        """
        OPTIONAL MATCH (c:Character)
        WHERE c.name IN $hero_names
        OPTIONAL MATCH (c)-[:HAS_TRAIT]->(trait:Trait)
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(skill:Skill)
        OPTIONAL MATCH (c)-[:HAS_PASSIVE_SKILL]->(passive:PassiveSkill)
        WITH collect(DISTINCT c.name) AS known_characters,
             collect(DISTINCT {
               character: c.name,
               weapon: c.weapon
             }) AS character_rows,
             collect(DISTINCT {
               character: c.name,
               trait: trait.name
             }) AS trait_rows,
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
        WITH known_characters, character_rows, trait_rows, skill_rows, passive_rows,
             collect(DISTINCT s.name) AS known_sidekicks
        OPTIONAL MATCH (g:Grasta)
        WHERE g.name IN $grasta_names
        OPTIONAL MATCH (g)-[:REQUIRES_TRAIT]->(required_trait:Trait)
        RETURN known_characters, character_rows, trait_rows, skill_rows, passive_rows, known_sidekicks,
               collect(DISTINCT {
                 name: g.name,
                 personality_req: required_trait.name
               }) AS grasta_rows
        """,
        hero_names=hero_names,
        grasta_names=grasta_names,
        sidekick_lookup_names=sidekick_lookup_names,
        database_="neo4j",
    )
    row = records[0] if records else {}
    grasta_rows = row.get("grasta_rows", [])
    return LegalityContext(
        known_characters=set(row.get("known_characters", [])),
        known_sidekicks=set(row.get("known_sidekicks", [])),
        character_weapons=_rows_to_value_map(row.get("character_rows", []), "weapon"),
        character_traits=_rows_to_trait_map(row.get("trait_rows", [])),
        character_skills=_rows_to_name_map(row.get("skill_rows", []), gated=False),
        character_passives=_rows_to_name_map(row.get("passive_rows", []), gated=False),
        sa_gated_skills=_rows_to_name_map(row.get("skill_rows", []), gated=True),
        sa_gated_passives=_rows_to_name_map(row.get("passive_rows", []), gated=True),
        known_grastas={row["name"] for row in grasta_rows if row.get("name")},
        grasta_personality_reqs={row["name"]: row["personality_req"] for row in grasta_rows if row.get("name") and row.get("personality_req")},
        assumed_available_sidekicks=assumed_available_sidekicks or set(),
    )


def validate_lineup_legality(
    lineup: LineupModel | dict[str, Any],
    roster: RosterInput,
    context: LegalityContext,
) -> LineupModel:
    """Validate a lineup against ownership, sidekick, skill, passive, build, and SA facts."""
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
        errors.extend(_validate_grasta_compatibility(hero, candidate, context))

    for slot_name, sidekick in [("main_sidekick", candidate.main_sidekick), ("sub_sidekick", candidate.sub_sidekick)]:
        if not sidekick:
            continue
        if sidekick not in context.known_sidekicks and sidekick not in context.assumed_available_sidekicks:
            errors.append(f"{slot_name} is not a known sidekick: {sidekick}")
        if sidekick not in allowed_sidekicks:
            errors.append(f"{slot_name} is not owned or assumption-available: {sidekick}")

    if _lineup_depends_on_pain_poison(candidate) and not _lineup_has_pain_poison_source(candidate):
        errors.append("pain/poison-dependent build assumptions must identify a skill, passive, sidekick, or explicit assumption that applies pain/poison")

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


def _validate_grasta_compatibility(
    hero: CharacterBuild,
    lineup: LineupModel,
    context: LegalityContext,
) -> list[str]:
    errors: list[str] = []
    traits = context.character_traits.get(hero.name, set())
    weapon = context.character_weapons.get(hero.name, "")
    assumption_text = " ".join([
        *hero.upgrade_assumptions,
        *lineup.build_notes,
        *lineup.risks,
    ]).lower()

    for grasta in hero.grastas:
        if grasta not in context.known_grastas:
            if not _is_caveated(grasta, assumption_text):
                errors.append(f"{hero.name} has unverifiable Grasta assumption without caveat: {grasta}")
            continue

        personality_req = context.grasta_personality_reqs.get(grasta)
        if personality_req:
            if personality_req not in traits:
                errors.append(f"{hero.name} lacks required trait for Grasta {grasta}: {personality_req}")
            continue

        weapon_req = _weapon_type_from_grasta_name(grasta)
        if weapon_req:
            if weapon and weapon.lower() != weapon_req.lower():
                errors.append(f"{hero.name} cannot use weapon-type Grasta {grasta}; character weapon is {weapon}")
            continue

    return errors


def _duplicate_specific_equipment(equipment_by_hero: dict[str, str]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for hero, item in equipment_by_hero.items():
        normalized = _specific_equipment_key(item)
        if not normalized:
            continue
        if normalized in seen:
            duplicates.append(f"{item} ({seen[normalized]}, {hero})")
            continue
        seen[normalized] = hero
    return duplicates


def _specific_equipment_key(item: str) -> str | None:
    normalized = " ".join(item.strip().lower().split())
    if not normalized or normalized in GENERIC_EQUIPMENT_VALUES:
        return None
    if normalized.startswith(GENERIC_EQUIPMENT_PREFIXES):
        return None
    return normalized


def _weapon_type_from_grasta_name(grasta: str) -> str | None:
    words = {word.strip("()[],:;+-").lower() for word in grasta.split()}
    for weapon_type in WEAPON_TYPES:
        if weapon_type.lower() in words:
            return weapon_type
    return None


def _lineup_depends_on_pain_poison(lineup: LineupModel) -> bool:
    build_text = " ".join([
        *lineup.build_notes,
        *[grasta for hero in lineup.heroes for grasta in hero.grastas],
    ]).lower()
    return ("pain" in build_text or "poison" in build_text) and ("grasta" in build_text or "multiplier" in build_text or "damage" in build_text)


def _lineup_has_pain_poison_source(lineup: LineupModel) -> bool:
    skill_or_passive_text = " ".join([
        *[skill for hero in lineup.heroes for skill in hero.recommended_skills],
        *[passive for hero in lineup.heroes for passive in hero.recommended_passives],
    ]).lower()
    if "pain" in skill_or_passive_text or "poison" in skill_or_passive_text:
        return True

    assumption_text = " ".join([
        *lineup.build_notes,
        *lineup.risks,
        *[assumption for hero in lineup.heroes for assumption in hero.upgrade_assumptions],
    ]).lower()
    source_terms = ("apply", "applies", "enable", "enables", "inflict", "inflicts", "source", "setter")
    return ("pain" in assumption_text or "poison" in assumption_text) and any(term in assumption_text for term in source_terms)


def _is_caveated(item: str, assumption_text: str) -> bool:
    item_text = item.lower()
    return item_text in assumption_text or any(
        phrase in assumption_text
        for phrase in [
            "compatibility assumed",
            "compatibility cannot be verified",
            "late-game assumption",
            "build assumption",
            "unverified grasta",
            "assumes grasta",
        ]
    )


def _rows_to_value_map(rows: list[dict[str, Any]], value_key: str) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for row in rows:
        character = row.get("character")
        value = row.get(value_key)
        if character and value:
            mapped[character] = value
    return mapped


def _rows_to_trait_map(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    mapped: dict[str, set[str]] = {}
    for row in rows:
        character = row.get("character")
        trait = row.get("trait")
        if character and trait:
            mapped.setdefault(character, set()).add(trait)
    return mapped


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
