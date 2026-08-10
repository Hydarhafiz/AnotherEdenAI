"""Pydantic v2 ETL boundary models for AnotherEden wiki data.

These models validate scraped rows before they are loaded into Neo4j.
ETL_MODE controls whether invalid rows raise or are silently skipped.
"""
import logging
import hashlib
import unicodedata
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import ETL_SCHEMA_VERSION, STRICT
from .capability_taxonomy import _canonical, materialize_atomic

logger = logging.getLogger(__name__)


TAG_DERIVATION_RULE = "deterministic keyword tags derived from existing name/category/stats text"

_EFFECT_TAG_PATTERNS: tuple[tuple[str, str], ...] = (
    ("element:fire", r"\bfire\b"),
    ("element:water", r"\bwater\b"),
    ("element:wind", r"\bwind\b"),
    ("element:earth", r"\bearth\b"),
    ("element:thunder", r"\bthunder\b"),
    ("element:shade", r"\bshade\b|\bdark\b"),
    ("element:crystal", r"\bcrystal\b"),
    ("element:null", r"\bnull\b"),
    ("attack:slash", r"\bslash\b|katana|sword|blade"),
    ("attack:pierce", r"\bpierce\b|bow|spear"),
    ("attack:blunt", r"\bblunt\b|hammer|fist"),
    ("attack:magic", r"\bmagic\b|staff|tome"),
    ("status:pain", r"\bpain\b"),
    ("status:poison", r"\bpoison\b"),
    ("status:stun", r"\bstun\b"),
    ("status:sleep", r"\bsleep\b"),
    ("combat:critical", r"\bcritical\b|\bcrit\b"),
    ("combat:af", r"\baf\b|another force"),
    ("combat:zone", r"\bzone\b|stance"),
    ("combat:damage", r"\bdamage\b|\bdmg\b"),
    ("combat:heal", r"\bheal\b|restore hp|hp recovery"),
    ("combat:mp", r"\bmp\b"),
    ("combat:barrier", r"\bbarrier\b|shield"),
    ("stat:hp", r"\bhp\b"),
    ("stat:mp", r"\bmp\b"),
    ("stat:pwr", r"\bpwr\b|\bpower\b|\batk\b"),
    ("stat:int", r"\bint\b|intelligence"),
    ("stat:spd", r"\bspd\b|\bspeed\b"),
    ("stat:end", r"\bend\b|endurance"),
    ("stat:spr", r"\bspr\b|spirit"),
    ("stat:luck", r"\bluck\b"),
    ("resistance:type", r"type resistance|all type res"),
    ("resistance:physical", r"physical resistance"),
    ("resistance:magic", r"magic resistance"),
)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _stable_id(prefix: str, *parts: object) -> str:
    normalized = "\x1f".join(
        unicodedata.normalize("NFKC", str(part or "")).strip().casefold()
        for part in parts
    )
    return f"{prefix}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:20]}"


def _character_aliases(name: str) -> list[str]:
    aliases = [name]
    if "," in name:
        base, style = [part.strip() for part in name.split(",", 1)]
        aliases.extend([base, style])
        parenthetical = re.match(r"^(.*?)\s*\(([^)]+)\)$", base)
        if parenthetical:
            aliases.append(f"{parenthetical.group(1)} {parenthetical.group(2)}")
    return _dedupe_preserve_order(aliases)



def derive_effect_tags(*parts: str | None, prefixes: list[str] | None = None) -> list[str]:
    """Build low-risk retrieval tags from text already present in the scraped row."""
    text = " ".join(part or "" for part in parts).lower()
    tags = list(prefixes or [])
    for tag, pattern in _EFFECT_TAG_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            tags.append(tag)
    return _dedupe_preserve_order(tags)


class CharacterRow(BaseModel):
    """Represents a single character row scraped from the Characters wiki page."""

    name: str
    element: str
    weapon: str
    light_shadow: str
    personalities: list[str]
    detail_url: str | None = None
    is_SA: bool = Field(default=False)
    skills: list["SkillRow"] = Field(default_factory=list)
    passive_skills: list["PassiveSkillRow"] = Field(default_factory=list)
    character_id: str = ""
    display_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    @field_validator("personalities", mode="before")
    @classmethod
    def parse_personalities(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return list(v) if v else []

    @field_validator("is_SA", mode="before")
    @classmethod
    def coerce_is_sa(cls, v):
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y", "sa", "stellar"}
        return bool(v)


    def model_post_init(self, __context) -> None:
        if not self.character_id:
            object.__setattr__(self, "character_id", _stable_id("character", self.name, self.detail_url))
        if not self.display_name:
            object.__setattr__(self, "display_name", self.name)
        if not self.aliases:
            object.__setattr__(self, "aliases", _character_aliases(self.name))


class SkillRow(BaseModel):
    """Represents one parsed character skill for graph ingestion."""

    character_name: str
    name: str
    element: str | None = None
    skill_type: str | None = None
    mp: int | None = None
    description: str = ""
    multiplier: float | None = None
    source_url: str | None = None
    section: str | None = None
    requires_stellar_awakened: bool = Field(default=False)
    skill_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    capability_evidence_json: str = "[]"
    capability_artifact_version: str = ""
    capability_diagnostics_json: str = "{}"
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    def model_post_init(self, __context) -> None:
        if not self.skill_id:
            object.__setattr__(self, "skill_id", _stable_id("skill", self.character_name, self.name))
        capabilities, dependencies, evidence, version, diagnostics = materialize_atomic(self.model_dump())
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "capability_evidence_json", _canonical(evidence))
        object.__setattr__(self, "capability_artifact_version", version)
        object.__setattr__(self, "capability_diagnostics_json", _canonical(diagnostics))

    @field_validator("mp", mode="before")
    @classmethod
    def coerce_mp(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, str):
            match = re.search(r"\d+", v)
            return int(match.group(0)) if match else None
        return int(v)

    @field_validator("multiplier", mode="before")
    @classmethod
    def coerce_multiplier(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, str):
            cleaned = v.strip().replace("%", "")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return float(v)

    @field_validator("requires_stellar_awakened", mode="before")
    @classmethod
    def coerce_requires_stellar_awakened(cls, v):
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y", "sa", "stellar", "stellar awakened"}
        return bool(v)


class PassiveSkillRow(BaseModel):
    """Represents one parsed passive or non-executable character mechanic."""

    character_name: str
    name: str
    description: str = ""
    source_url: str | None = None
    section: str | None = None
    passive_type: str | None = None
    requires_stellar_awakened: bool = Field(default=False)
    passive_skill_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    capability_evidence_json: str = "[]"
    capability_artifact_version: str = ""
    capability_diagnostics_json: str = "{}"
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    def model_post_init(self, __context) -> None:
        if not self.passive_skill_id:
            object.__setattr__(
                self,
                "passive_skill_id",
                _stable_id("passive", self.character_name, self.name),
            )
        capabilities, dependencies, evidence, version, diagnostics = materialize_atomic(self.model_dump())
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "capability_evidence_json", _canonical(evidence))
        object.__setattr__(self, "capability_artifact_version", version)
        object.__setattr__(self, "capability_diagnostics_json", _canonical(diagnostics))

    @field_validator("requires_stellar_awakened", mode="before")
    @classmethod
    def coerce_requires_stellar_awakened(cls, v):
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "y", "sa", "stellar", "stellar awakened"}
        return bool(v)


class SidekickSkillRow(BaseModel):
    """Represents one parsed sidekick auto or charge skill."""

    sidekick_name: str
    name: str
    skill_kind: str
    element: str | None = None
    skill_type: str | None = None
    charge_cost: int | None = None
    description: str = ""
    source_url: str | None = None
    section: str | None = None
    sidekick_skill_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    capability_evidence_json: str = "[]"
    capability_artifact_version: str = ""
    capability_diagnostics_json: str = "{}"
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    def model_post_init(self, __context) -> None:
        if not self.sidekick_skill_id:
            object.__setattr__(self, "sidekick_skill_id", _stable_id("sidekick_skill", self.sidekick_name, self.skill_kind, self.name))
        capabilities, dependencies, evidence, version, diagnostics = materialize_atomic(self.model_dump())
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "capability_evidence_json", _canonical(evidence))
        object.__setattr__(self, "capability_artifact_version", version)
        object.__setattr__(self, "capability_diagnostics_json", _canonical(diagnostics))

    @field_validator("skill_kind")
    @classmethod
    def validate_skill_kind(cls, v):
        if v not in {"auto", "charge"}:
            raise ValueError("skill_kind must be auto or charge")
        return v

    @field_validator("charge_cost", mode="before")
    @classmethod
    def coerce_charge_cost(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, str):
            match = re.search(r"-?\d+", v)
            return abs(int(match.group(0))) if match else None
        return abs(int(v))


class SidekickAuraRow(BaseModel):
    """Represents one parsed sidekick aura effect."""

    sidekick_name: str
    name: str
    activation_condition: str | None = None
    effect_text: str = ""
    source_url: str | None = None
    section: str | None = None
    sidekick_aura_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    capability_evidence_json: str = "[]"
    capability_artifact_version: str = ""
    capability_diagnostics_json: str = "{}"
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    def model_post_init(self, __context) -> None:
        if not self.sidekick_aura_id:
            object.__setattr__(self, "sidekick_aura_id", _stable_id("sidekick_aura", self.sidekick_name, self.name))
        capabilities, dependencies, evidence, version, diagnostics = materialize_atomic(self.model_dump())
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "capability_evidence_json", _canonical(evidence))
        object.__setattr__(self, "capability_artifact_version", version)
        object.__setattr__(self, "capability_diagnostics_json", _canonical(diagnostics))


class SidekickRow(BaseModel):
    """Represents a sidekick as a first-class non-hero party member."""

    name: str
    source_url: str
    acquisition_text: str | None = None
    rarity: str | None = None
    main_slot_behavior: str = "Main sidekick can use auto skills, charge skills, and aura effects."
    sub_slot_behavior: str = "Sub sidekick contributes aura-only effects."
    associated_character_names: list[str] = Field(default_factory=list)
    diagnostics_text: str | None = None
    auto_skills: list[SidekickSkillRow] = Field(default_factory=list)
    charge_skills: list[SidekickSkillRow] = Field(default_factory=list)
    auras: list[SidekickAuraRow] = Field(default_factory=list)
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    @field_validator("associated_character_names", mode="before")
    @classmethod
    def parse_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if v else []


class SuperbossIndexRow(BaseModel):
    """Represents one superboss candidate discovered from the Superbosses index."""

    name: str
    source_url: str
    difficulty_tier: str | None = None
    level: int | None = None
    refight_status: str | None = None
    version: str | None = None
    characteristics: str = ""
    canonical_id: str | None = None
    aliases: list[str] = Field(default_factory=list)
    section_anchor: str | None = None
    section_end_anchor: str | None = None
    variant_relationship: str | None = None
    cohort: str | None = None
    support_status: str = "discovered"
    selection_rationale: dict[str, str] = Field(default_factory=dict)


class SuperbossRow(BaseModel):
    """Represents a curated superboss detail row for graph ingestion."""

    name: str
    source_url: str
    difficulty_tier: str | None = None
    cohort: str | None = None
    level: int | None = None
    hp: int | None = None
    weak: list[str] = Field(default_factory=lambda: ["unknown"])
    resist: list[str] = Field(default_factory=lambda: ["unknown"])
    null: list[str] = Field(default_factory=lambda: ["unknown"])
    absorb: list[str] = Field(default_factory=lambda: ["unknown"])
    characteristics: str = ""
    mechanic_tags: list[str] = Field(default_factory=list)
    mechanics_text: str
    canonical_id: str = ""
    aliases: list[str] = Field(default_factory=list)
    section_anchor: str | None = None
    section_end_anchor: str | None = None
    source_section: str | None = None
    section_bounded: bool = False
    affinity_state: dict[str, Literal["confirmed_values", "confirmed_empty", "unknown"]] = Field(default_factory=dict)
    affinity_evidence: dict[str, str] = Field(default_factory=dict)
    affinity_observations: list[dict[str, str | list[str]]] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
    mechanics_evidence: dict[str, str] = Field(default_factory=dict)
    citation_url: str | None = None
    variant_relationship: str | None = None
    selection_rationale: dict[str, str] = Field(default_factory=dict)
    support_status: str = "parsed"
    recommendation_ready: bool = False
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    @field_validator("weak", "resist", "null", "absorb", "mechanic_tags", mode="before")
    @classmethod
    def parse_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in re.split(r"[,;/|]", v) if item.strip()] or ["unknown"]
        return ["unknown"] if v is None else list(v)

    @field_validator("hp", mode="before")
    @classmethod
    def coerce_hp(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, str):
            match = re.search(r"\d[\d,]*", v)
            return int(match.group(0).replace(",", "")) if match else None
        return int(v)

    def model_post_init(self, __context) -> None:
        if not self.canonical_id:
            object.__setattr__(self, "canonical_id", _stable_id("superboss", self.name))
        if not self.aliases:
            object.__setattr__(self, "aliases", [self.name])
        states = dict(self.affinity_state)
        for field in ("weak", "resist", "null", "absorb"):
            if field in states:
                continue
            values = getattr(self, field)
            states[field] = (
                "unknown"
                if values == ["unknown"]
                else "confirmed_values"
                if values
                else "confirmed_empty"
            )
        object.__setattr__(self, "affinity_state", states)


class MechanicReferenceRow(BaseModel):
    """One curated battle-mechanics reference for recommendation RAG."""

    id: str
    title: str
    source_url: str
    source_page: str
    section_path: list[str] = Field(default_factory=list)
    mechanic_type: str
    topic_tags: list[str] = Field(default_factory=list)
    applies_to: list[str] = Field(default_factory=list)
    rules_text: str = ""
    summary: str = ""
    caveats: str = ""
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    @field_validator("section_path", "topic_tags", "applies_to", mode="before")
    @classmethod
    def parse_string_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in re.split(r"[,;/|>]", v) if item.strip()]
        return list(v) if v else []

    def model_post_init(self, __context) -> None:
        if not self.rules_text.strip() and not self.summary.strip():
            raise ValueError("MechanicReferenceRow requires rules_text or summary")


class GrastaRow(BaseModel):
    """Represents a single grasta row scraped from any Grasta wiki page."""

    name: str
    category: str
    tier: int
    stats: str
    personality_req: Optional[str] = None
    is_shareable: bool
    effect_tags: list[str] = Field(default_factory=list)
    weapon_req: Optional[str] = None
    weapon_group: list[str] = Field(default_factory=list)
    source_url: str = ""
    obtain_text: str = ""
    effect_text: str = ""
    source_variant: str = ""
    acquisition_class: str = "unknown"
    max_theoretical_copies: int | None = None
    grasta_id: str = ""
    display_name: str = ""
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    effect_tag_derivation: str = Field(default=TAG_DERIVATION_RULE)

    @field_validator("tier", mode="before")
    @classmethod
    def coerce_tier(cls, v):
        return int(v) if v is not None else 0

    @field_validator("is_shareable", mode="before")
    @classmethod
    def coerce_shareable(cls, v):
        if isinstance(v, str):
            return v == "1"
        return bool(v)

    @field_validator("effect_tags", mode="before")
    @classmethod
    def parse_effect_tags(cls, v):
        if isinstance(v, str):
            return [tag.strip() for tag in re.split(r"[,;/|]", v) if tag.strip()]
        return list(v) if v else []

    @field_validator("weapon_group", mode="before")
    @classmethod
    def parse_weapon_group(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in re.split(r"[,;/|]", v) if item.strip()]
        return list(v) if v else []

    @field_validator("max_theoretical_copies", mode="before")
    @classmethod
    def coerce_max_copies(cls, v):
        if v in (None, ""):
            return None
        return max(1, int(v))

    def model_post_init(self, __context) -> None:
        discriminator = self.personality_req or self.weapon_req or "/".join(self.weapon_group)
        discriminator = discriminator or self.source_variant or f"{self.category} T{self.tier}"
        if not self.display_name:
            object.__setattr__(
                self,
                "display_name",
                f"{self.name} ({discriminator})",
            )
        if not self.grasta_id:
            object.__setattr__(
                self,
                "grasta_id",
                _stable_id(
                    "grasta", self.category, self.tier, self.name,
                    self.personality_req, self.weapon_req,
                    "/".join(self.weapon_group), self.source_variant,
                ),
            )
        if not self.effect_tags:
            object.__setattr__(
                self,
                "effect_tags",
                derive_effect_tags(
                    self.name,
                    self.category,
                    self.stats,
                    self.personality_req,
                    self.weapon_req,
                    self.effect_text,
                    prefixes=[f"category:{self.category.lower()}", f"tier:{self.tier}"],
                ),
            )


class OreRow(BaseModel):
    """Represents a single ore row scraped from the Grasta Ores wiki page."""

    name: str
    stats: str
    source: str
    effect_tags: list[str] = Field(default_factory=list)
    effect_tag_derivation: str = Field(default=TAG_DERIVATION_RULE)

    @field_validator("effect_tags", mode="before")
    @classmethod
    def parse_effect_tags(cls, v):
        if isinstance(v, str):
            return [tag.strip() for tag in re.split(r"[,;/|]", v) if tag.strip()]
        return list(v) if v else []

    def model_post_init(self, __context) -> None:
        if not self.effect_tags:
            object.__setattr__(
                self,
                "effect_tags",
                derive_effect_tags(self.name, self.stats, prefixes=["category:ore"]),
            )


class EquipmentRow(BaseModel):
    """Represents baseline weapon or armor context scraped from equipment indexes."""

    name: str
    equipment_slot: str
    category: str | None = None
    level: int | None = None
    attack: int | None = None
    magic_attack: int | None = None
    defense: int | None = None
    magic_defense: int | None = None
    effect_text: str = ""
    obtain_text: str = ""
    source_url: str
    schema_version: str = Field(default=ETL_SCHEMA_VERSION)

    @field_validator("equipment_slot")
    @classmethod
    def validate_equipment_slot(cls, v):
        if v not in {"weapon", "armor"}:
            raise ValueError("equipment_slot must be weapon or armor")
        return v

    @field_validator("level", "attack", "magic_attack", "defense", "magic_defense", mode="before")
    @classmethod
    def coerce_optional_int(cls, v):
        if v in (None, ""):
            return None
        if isinstance(v, str):
            match = re.search(r"-?\d+", v.replace(",", ""))
            return int(match.group(0)) if match else None
        return int(v)


# ---------------------------------------------------------------------------
# Parse helpers with ETL_MODE toggle
# ---------------------------------------------------------------------------

# Manual overrides for characters with incorrect weapon data on the wiki.
# Applied after CharacterRow.model_validate() using Pydantic v2 model_copy().
# Keys must match the exact data-name attribute value from the wiki HTML.
WEAPON_OVERRIDES: dict[str, str] = {
    "Anabel ES": "Spear",
    "Mazrika": "Axe",
}


def parse_character(raw: dict) -> Optional[CharacterRow]:
    """Validate a raw character dict into a CharacterRow.

    In strict mode (STRICT=True), raises ValidationError on invalid data.
    In lenient mode (STRICT=False), logs a warning and returns None.
    Applies WEAPON_OVERRIDES after validation for characters with incorrect wiki data.
    """
    try:
        char = CharacterRow.model_validate(raw)
        if char.name in WEAPON_OVERRIDES:
            char = char.model_copy(update={"weapon": WEAPON_OVERRIDES[char.name]})
        return char
    except Exception as exc:
        if STRICT:
            raise
        logger.warning("Skipping character %s: %s", raw.get("name"), exc)
        return None


def parse_grasta(raw: dict) -> Optional[GrastaRow]:
    """Validate a raw grasta dict into a GrastaRow.

    Forces personality_req=None for VC category regardless of raw input —
    VC grastas have data-personality='' and the col[2] text is "Character: <name>",
    not a Trait. No REQUIRES_TRAIT edge should ever be created for VC grastas.

    In strict mode raises on invalid data; lenient mode returns None.
    """
    if raw.get("category") == "VC":
        raw = {**raw, "personality_req": None}
    try:
        return GrastaRow.model_validate(raw)
    except Exception as exc:
        if STRICT:
            raise
        logger.warning("Skipping grasta %s: %s", raw.get("name"), exc)
        return None


def parse_ore(raw: dict) -> Optional[OreRow]:
    """Validate a raw ore dict into an OreRow.

    In strict mode raises on invalid data; lenient mode returns None.
    """
    try:
        return OreRow.model_validate(raw)
    except Exception as exc:
        if STRICT:
            raise
        logger.warning("Skipping ore %s: %s", raw.get("name"), exc)
        return None


def parse_equipment(raw: dict) -> Optional[EquipmentRow]:
    """Validate a raw equipment dict into an EquipmentRow."""
    try:
        return EquipmentRow.model_validate(raw)
    except Exception as exc:
        if STRICT:
            raise
        logger.warning("Skipping equipment %s: %s", raw.get("name"), exc)
        return None


def parse_mechanic_reference(raw: dict) -> Optional[MechanicReferenceRow]:
    """Validate a curated mechanic reference row."""
    try:
        return MechanicReferenceRow.model_validate(raw)
    except Exception as exc:
        if STRICT:
            raise
        logger.warning("Skipping mechanic reference %s: %s", raw.get("id"), exc)
        return None
