"""Superboss mechanics context injection for analysis-time reasoning."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from .state import WorkflowState


class HPStopper(BaseModel):
    """One HP stopper threshold and its combat consequence."""

    threshold_percent: int = Field(ge=1, le=99)
    effect: str


class SuperbossMechanics(BaseModel):
    """Curated mechanics payload for a superboss."""

    name: str
    aliases: list[str] = Field(default_factory=list)
    hp_stoppers: list[HPStopper]
    elemental_zones: list[str]
    notes: list[str] = Field(default_factory=list)


SUPERBOSS_FIXTURES: list[dict[str, Any]] = [
    {
        "name": "Lavos Core",
        "aliases": ["lavos"],
        "hp_stoppers": [
            {"threshold_percent": 75, "effect": "changes weakness profile and punishes mono-element burst"},
            {"threshold_percent": 25, "effect": "prepares a high-damage fixed attack on the next turn"},
        ],
        "elemental_zones": ["Fire", "Water"],
        "notes": ["Prefer flexible mitigation and avoid spending all AF before the 25% stopper."],
    },
    {
        "name": "True Manifest Gariyu",
        "aliases": ["gariyu manifest", "true manifest gariyu"],
        "hp_stoppers": [
            {"threshold_percent": 50, "effect": "re-enters Fire Zone and increases incoming fire pressure"},
        ],
        "elemental_zones": ["Fire"],
        "notes": ["Water-resistant supports and zone overwrite options are high value."],
    },
]

SUPERBOSSES = [SuperbossMechanics.model_validate(item) for item in SUPERBOSS_FIXTURES]


def find_superboss_context(query: str) -> SuperbossMechanics | None:
    """Return curated superboss mechanics when the user query names a fixture."""
    normalized = query.lower()
    for boss in SUPERBOSSES:
        names = [boss.name, *boss.aliases]
        if any(name.lower() in normalized for name in names):
            return boss
    return None


def inject_superboss_context_node(state: WorkflowState) -> dict:
    """LangGraph-compatible node that writes boss_context when available."""
    boss = find_superboss_context(state.get("user_query", ""))
    if boss is None:
        return {"boss_context": ""}
    return {"boss_context": json.dumps(boss.model_dump(), ensure_ascii=False)}
