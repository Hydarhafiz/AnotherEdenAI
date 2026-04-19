"""Pydantic v2 ETL boundary models for AnotherEden wiki data.

These models validate scraped rows before they are loaded into Neo4j.
ETL_MODE controls whether invalid rows raise or are silently skipped.
"""
import logging
from typing import Optional

from pydantic import BaseModel, field_validator

from .constants import STRICT

logger = logging.getLogger(__name__)


class CharacterRow(BaseModel):
    """Represents a single character row scraped from the Characters wiki page."""

    name: str
    element: str
    weapon: str
    light_shadow: str
    personalities: list[str]

    @field_validator("personalities", mode="before")
    @classmethod
    def parse_personalities(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return list(v) if v else []


class GrastaRow(BaseModel):
    """Represents a single grasta row scraped from any Grasta wiki page."""

    name: str
    category: str
    tier: int
    stats: str
    personality_req: Optional[str] = None
    is_shareable: bool

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


class OreRow(BaseModel):
    """Represents a single ore row scraped from the Grasta Ores wiki page."""

    name: str
    stats: str
    source: str


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
