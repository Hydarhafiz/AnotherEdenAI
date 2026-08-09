"""Typed, deterministic retrieval boundary for production recommendations."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from .legality import SAState, build_roster_input
from .lineup_generation import generate_lineup_candidates
from .mechanics import retrieve_mechanic_references
from .role_scoring import derive_contextual_role_scores
from .state import WorkflowState
from .superboss import find_superboss_context


ItemPolicy = Literal["late_game_assumed", "generic_only"]


class ProductionRecommendationRequest(BaseModel):
    """Legality-bearing input for the production recommender."""

    boss_id: str = Field(min_length=1)
    roster: list[str] = Field(min_length=1)
    owned_sidekicks: list[str] = Field(default_factory=list)
    stellar_awakened: dict[str, SAState | bool] = Field(default_factory=dict)
    item_policy: ItemPolicy = "late_game_assumed"
    preferences: str = ""

    @model_validator(mode="after")
    def _clean(self) -> "ProductionRecommendationRequest":
        self.boss_id = self.boss_id.strip()
        self.roster = _dedupe(self.roster)
        self.owned_sidekicks = _dedupe(self.owned_sidekicks)
        self.preferences = self.preferences.strip()
        return self


class RetrievalIssue(BaseModel):
    code: str
    field: str
    value: str | None = None
    message: str


class ProductionRequestError(ValueError):
    """A deterministic typed request failure, safe to return to callers."""

    def __init__(self, issues: list[RetrievalIssue]):
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


class ProductionRetrieval(BaseModel):
    request: ProductionRecommendationRequest
    boss: dict[str, Any]
    characters: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    passives: list[dict[str, Any]]
    mechanics: list[dict[str, Any]]
    sidekicks: list[dict[str, Any]]
    grastas: list[dict[str, Any]]
    equipment: list[dict[str, Any]]
    coverage: dict[str, Any]
    role_scores: dict[str, Any] = Field(default_factory=dict)
    build_packages: dict[str, Any] = Field(default_factory=dict)
    lineup_candidates: dict[str, Any] = Field(default_factory=dict)


class ProductionRetrievalService:
    """Typed Neo4j reads. User prose is deliberately absent from every query."""

    def __init__(self, driver):
        self.driver = driver

    async def _query(self, cypher: str, **parameters) -> list[dict[str, Any]]:
        records, _, _ = await self.driver.execute_query(
            cypher, database_="neo4j", **parameters
        )
        return [dict(record) for record in records]

    async def boss(self, boss_id: str) -> dict[str, Any] | None:
        rows = await self._query(
            """
MATCH (b:Superboss)
WHERE toLower(b.name) = toLower($boss_id)
RETURN b.name AS id, b.name AS name, b.source_url AS source_url,
       coalesce(b.weak, []) AS weak, coalesce(b.resist, []) AS resist,
       coalesce(b.null, []) AS null, coalesce(b.absorb, []) AS absorb,
       coalesce(b.characteristics, '') AS characteristics,
       coalesce(b.mechanic_tags, []) AS mechanic_tags,
       coalesce(b.mechanics_text, '') AS mechanics_text
LIMIT 1
""",
            boss_id=boss_id,
        )
        return rows[0] if rows else None

    async def conflicting_bosses(self, boss_id: str, preferences: str) -> list[str]:
        if not preferences:
            return []
        rows = await self._query(
            """
MATCH (b:Superboss)
WHERE toLower(b.name) <> toLower($boss_id)
  AND toLower($preferences) CONTAINS toLower(b.name)
RETURN b.name AS name ORDER BY b.name
""",
            boss_id=boss_id,
            preferences=preferences,
        )
        conflicts = [row["name"] for row in rows]
        curated = find_superboss_context(preferences)
        if curated and curated.name.casefold() != boss_id.casefold():
            conflicts.append(curated.name)
        return list(dict.fromkeys(conflicts))

    async def resolve_character(self, input_name: str) -> list[str]:
        """Resolve exact canonical names/aliases; production never uses substrings."""
        rows = await self._query(
            """
MATCH (c:Character)
WHERE toLower(c.name) = toLower($input)
   OR any(alias IN coalesce(c.aliases, []) WHERE toLower(alias) = toLower($input))
RETURN DISTINCT c.name AS name ORDER BY name
""",
            input=input_name,
        )
        return [row["name"] for row in rows]

    async def resolve_sidekick(self, input_name: str) -> list[str]:
        """Resolve an exact canonical sidekick name without fuzzy ownership expansion."""
        rows = await self._query(
            """
MATCH (s:Sidekick)
WHERE toLower(s.name) = toLower($input)
RETURN DISTINCT s.name AS name ORDER BY name
""",
            input=input_name,
        )
        return [row["name"] for row in rows]

    async def characters(self, roster: list[str]) -> list[dict[str, Any]]:
        rows = await self._query(
            """
MATCH (c:Character) WHERE c.name IN $roster
OPTIONAL MATCH (c)-[:HAS_TRAIT]->(t:Trait)
RETURN c{.*, id: c.character_id, traits: collect(DISTINCT t.name)} AS fact ORDER BY fact.name
""",
            roster=roster,
        )
        return [row["fact"] for row in rows]

    async def skills_passives(self, roster: list[str]) -> tuple[list[dict], list[dict]]:
        skills = await self._query(
            """
MATCH (c:Character)-[:HAS_SKILL]->(s:Skill) WHERE c.name IN $roster
RETURN s{.*, id: s.skill_id, character_name: c.name} AS fact ORDER BY fact.character_name, fact.name
""",
            roster=roster,
        )
        skills = [row["fact"] for row in skills]
        passives = await self._query(
            """
MATCH (c:Character)-[:HAS_PASSIVE_SKILL]->(p:PassiveSkill) WHERE c.name IN $roster
RETURN p{.*, id: p.passive_skill_id, character_name: c.name} AS fact ORDER BY fact.character_name, fact.name
""",
            roster=roster,
        )
        passives = [row["fact"] for row in passives]
        return skills, passives

    async def sidekicks(self, names: list[str]) -> list[dict[str, Any]]:
        if not names:
            return []
        rows = await self._query(
            """
MATCH (s:Sidekick) WHERE s.name IN $names
OPTIONAL MATCH (s)-[:HAS_AUTO_SKILL|HAS_CHARGE_SKILL]->(skill:SidekickSkill)
OPTIONAL MATCH (s)-[:HAS_AURA]->(aura:SidekickAura)
RETURN s{.*, skills: collect(DISTINCT skill{.*}), auras: collect(DISTINCT aura{.*})} AS fact
ORDER BY fact.name
""",
            names=names,
        )
        return [row["fact"] for row in rows]

    async def grastas(self) -> list[dict[str, Any]]:
        rows = await self._query(
            """
MATCH (g:Grasta)
OPTIONAL MATCH (g)-[:REQUIRES_TRAIT]->(t:Trait)
RETURN g{.*, id: g.grasta_id, required_trait: t.name} AS fact ORDER BY fact.display_name, fact.name
"""
        )
        return [row["fact"] for row in rows]

    async def equipment(self, weapons: list[str]) -> list[dict[str, Any]]:
        rows = await self._query(
            """
MATCH (e:Equipment)
WHERE e.equipment_slot = 'armor'
   OR (e.equipment_slot = 'weapon' AND e.category IN $weapons)
RETURN e{.*} AS fact ORDER BY fact.equipment_slot, fact.name
""",
            weapons=weapons,
        )
        return [row["fact"] for row in rows]

    async def mechanics(self, boss: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve only mechanics relevant to the selected canonical boss."""
        return await retrieve_mechanic_references(
            self.driver,
            topic_tags=[*boss.get("mechanic_tags", []), *boss.get("weak", [])],
            applies_to=["boss_counterplay", "lineup_recommendation", "lineup_legality"],
        )

    async def retrieve(self, request: ProductionRecommendationRequest) -> ProductionRetrieval:
        boss = await self.boss(request.boss_id)
        if boss is None:
            raise ProductionRequestError([RetrievalIssue(
                code="boss.unsupported", field="boss_id", value=request.boss_id,
                message=f"Unsupported boss ID: {request.boss_id}",
            )])

        conflicts = await self.conflicting_bosses(request.boss_id, request.preferences)
        if conflicts:
            raise ProductionRequestError([RetrievalIssue(
                code="boss.query_conflict", field="preferences", value=conflicts[0],
                message=(f"Selected boss {boss['name']} conflicts with boss named in "
                         f"preferences: {', '.join(conflicts)}"),
            )])

        unresolved = []
        ambiguous = []
        normalized_owned = []
        for name in request.roster:
            matches = await self.resolve_character(name)
            if not matches:
                unresolved.append(name)
            elif len(matches) > 1:
                ambiguous.append((name, matches))
            else:
                normalized_owned.append(matches[0])
        if unresolved:
            raise ProductionRequestError([RetrievalIssue(
                code="roster.unresolved", field="roster", value=name,
                message=f"Unresolved roster character: {name}",
            ) for name in unresolved])
        if ambiguous:
            raise ProductionRequestError([RetrievalIssue(
                code="roster.ambiguous", field="roster", value=name,
                message=f"Ambiguous roster character {name}: {', '.join(matches)}",
            ) for name, matches in ambiguous])

        unresolved_sidekicks = []
        ambiguous_sidekicks = []
        normalized_sidekicks = []
        for name in request.owned_sidekicks:
            matches = await self.resolve_sidekick(name)
            if not matches:
                unresolved_sidekicks.append(name)
            elif len(matches) > 1:
                ambiguous_sidekicks.append((name, matches))
            else:
                normalized_sidekicks.append(matches[0])
        if unresolved_sidekicks:
            raise ProductionRequestError([RetrievalIssue(
                code="sidekick.unresolved", field="owned_sidekicks", value=name,
                message=f"Unresolved owned sidekick: {name}",
            ) for name in unresolved_sidekicks])
        if ambiguous_sidekicks:
            raise ProductionRequestError([RetrievalIssue(
                code="sidekick.ambiguous", field="owned_sidekicks", value=name,
                message=f"Ambiguous owned sidekick {name}: {', '.join(matches)}",
            ) for name, matches in ambiguous_sidekicks])

        roster_input = await build_roster_input(
            self.driver,
            owned_characters=normalized_owned,
            owned_sidekicks=normalized_sidekicks,
            stellar_awakened=request.stellar_awakened,
        )
        normalized = roster_input.available_characters
        characters = await self.characters(normalized)
        found = {row["name"] for row in characters}
        missing = [name for name in normalized if name not in found]
        skills, passives = await self.skills_passives(normalized)
        sidekicks = await self.sidekicks(roster_input.owned_sidekicks)
        grastas = await self.grastas()
        equipment = await self.equipment(sorted({row.get("weapon") for row in characters if row.get("weapon")}))
        mechanics = await self.mechanics(boss)
        role_scores = derive_contextual_role_scores(
            boss=boss,
            characters=characters,
            skills=skills,
            passives=passives,
            sidekicks=sidekicks,
            stellar_awakened=roster_input.stellar_awakened,
            mechanics=mechanics,
            grastas=grastas,
            equipment=equipment,
            item_policy=request.item_policy,
        )
        lineup_candidates = generate_lineup_candidates(
            characters=characters,
            sidekicks=sidekicks,
            boss=boss,
            role_scores=role_scores,
            coverage={"requested_character_count": len(normalized)},
        )
        normalized_request = request.model_copy(update={
            "boss_id": boss["id"], "roster": normalized,
            "owned_sidekicks": roster_input.owned_sidekicks,
            "stellar_awakened": roster_input.stellar_awakened,
        })
        return ProductionRetrieval(
            request=normalized_request, boss=boss, characters=characters,
            skills=skills, passives=passives, mechanics=mechanics,
            sidekicks=sidekicks, grastas=grastas, equipment=equipment,
            coverage={
                "requested_character_count": len(normalized),
                "retrieved_character_count": len(characters),
                "missing_character_names": missing,
                "skill_owner_count": len({row.get("character_name") for row in skills}),
                "passive_owner_count": len({row.get("character_name") for row in passives}),
                "requested_sidekick_count": len(roster_input.owned_sidekicks),
                "retrieved_sidekick_count": len(sidekicks),
                "boss_complete": bool(boss.get("mechanics_text")),
                "complete": not missing,
            },
            role_scores=role_scores,
            build_packages=role_scores.get("build_packages", {}),
            lineup_candidates=lineup_candidates,
        )


async def retrieve_production_context_node(state: WorkflowState, driver) -> dict:
    """Validate typed input and populate state without planner/retrieval LLMs."""
    request = validate_production_request({
        "boss_id": state.get("boss_id"),
        "roster": state.get("roster", []),
        "owned_sidekicks": state.get("owned_sidekicks", []),
        "stellar_awakened": state.get("stellar_awakened", {}),
        "item_policy": state.get("item_policy", "late_game_assumed"),
        "preferences": state.get("user_query", ""),
    })
    result = await ProductionRetrievalService(driver).retrieve(request)
    context = {
        "boss": result.boss,
        "mechanic_references": result.mechanics,
        "citations": [
            {"label": result.boss["name"], "source_url": result.boss.get("source_url")}
        ] if result.boss.get("source_url") else [],
    }
    return {
        "boss_id": result.request.boss_id,
        "roster": result.request.roster,
        "owned_sidekicks": result.request.owned_sidekicks,
        "stellar_awakened": result.request.stellar_awakened,
        "boss_context": json.dumps(context, ensure_ascii=False),
        "typed_retrieval": result.model_dump(),
        "candidate_warnings": [] if result.coverage["complete"] else ["Typed retrieval coverage is incomplete."],
    }


def validate_production_request(payload: dict[str, Any]) -> ProductionRecommendationRequest:
    """Convert Pydantic input failures into the production typed-error contract."""
    try:
        return ProductionRecommendationRequest.model_validate(payload)
    except ValidationError as exc:
        issues = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ())) or "request"
            code = "boss.missing" if location == "boss_id" and error["type"] in {
                "missing", "string_type", "string_too_short"
            } else "request.invalid"
            issues.append(RetrievalIssue(
                code=code,
                field=location,
                value=None,
                message=error["msg"],
            ))
        raise ProductionRequestError(issues) from exc
def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))
