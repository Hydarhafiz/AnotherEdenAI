"""Source-scoped occurrence classification and comparison for Milestone 6 C2.

This module is intentionally an offline evidence layer.  It consumes the
checksum-pinned captures and real fact identities admitted by C1.1, but it
does not mutate the capability taxonomy, review artifact, legal-kit catalog,
graph schema, or runtime scoring path.  The optional oracle is only read by an
explicit evaluation call; normal classification never depends on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .capability_taxonomy import load_reviews, propose
from .kit_readiness import EXPECTED_CANONICAL_CHARACTER_COUNT, artifact_fingerprint
from .source_fidelity import (
    FIDELITY_DIMENSIONS,
    CATALOG_PATH,
    PARSED_SIDEKICK_DIR,
    RAW_CHARACTER_DIR,
    RAW_SIDEKICK_DIR,
    build_source_fidelity_report,
)
from .structural_evidence import (
    SourceIdentity,
    StructuralBlock,
    StructuralToken,
    StructuralUnit,
    audit_reference_topology,
    bind_catalog_facts,
    parse_grid_document,
    resolve_bounded_references,
    select_traversal_limits,
)
from .shared_mechanics import (
    REGISTRY_VERSION,
    SharedMechanicRegistry,
    resolve_shared_mechanics,
)


C2_ARTIFACT_VERSION = "m6-c2-scoped-classification-1.3.0"
C2_ORACLE_VERSION = "m6-c2-independent-occurrence-oracle-1.0.0"
MANIFEST_PATH = Path("artifacts/evidence/feature_c2_evaluation_freeze.json")

OCCURRENCE_KINDS = ("effect", "dependency", "trigger", "state", "reference")
PRIMARY_OCCURRENCE_KINDS = ("effect", "dependency")

_SPACE_RE = re.compile(r"\s+")
_CONDITION_RE = re.compile(
    r"\b(?:if|when|only when|unless|without|requires?|consumes?|based on|"
    r"depending on|after|before|during|once|until|while)\b",
    re.IGNORECASE,
)
_STATE_RE = re.compile(
    r"\b(?:stance|zone|lunatic|stack|stacks|blood contract|charge|status|"
    r"barrier|shield|link|copy|hold ground|counter|another zone|radical zone)\b",
    re.IGNORECASE,
)
_EFFECT_RE = re.compile(
    r"\b(?:attack|attacks|damage|damages|restore|recover|heal|grant|give|activate|"
    r"inflict|increase|decrease|reduce|remove|revive|apply|deal|take|add|deploy|"
    r"awaken|replace|stack)\b|(?:[+-]\s*\d|\d+\s*%)",
    re.IGNORECASE,
)
_ELEMENT_RE = re.compile(r"\b(?:fire|water|wind|earth|thunder|shade|crystal|non-type)\b", re.IGNORECASE)
_ATTACK_TYPE_RE = re.compile(r"\b(?:slash|piercing|pierce|blunt|magic|physical)\b", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)\s*%")
_PROBABILITY_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability)\b", re.IGNORECASE)
_MULTIPLIER_RE = re.compile(r"\b(?:x|multiplier\s*x)\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)
_TURN_RE = re.compile(r"\b(?:for\s+)?(\d+)\s+turns?\b", re.IGNORECASE)
_ACTIVATION_RE = re.compile(r"\b(\d+)\s+(?:times?|activations?|uses?)\b|\bonce per battle\b", re.IGNORECASE)
_ACTION_HEAD_RE = re.compile(
    r"\b(?:attacks?|deals?|inflicts?|applies?|increases?|raises?|boosts?|"
    r"decreases?|reduces?|lowers?|restores?|recovers?|heals?|revives?|"
    r"removes?|cleanses?|grants?|gains?|adds?|consumes?|spends?|deploys?|"
    r"activates?|awakens?|replaces?|converts?|changes?|sets?|takes?|"
    r"copies?|follows?\s+up|performs?)\b",
    re.IGNORECASE,
)
_LEADING_CONDITION_RE = re.compile(
    r"\s*(?P<condition>(?:only\s+)?(?:if|when|unless|after|before|during|while)\b[^,;.]*)"
    r"(?:[,;.]\s*|\s+(?=(?:the\s+)?(?:user|skill|effect)\b))",
    re.IGNORECASE,
)
_TRAILING_CONDITION_RE = re.compile(
    r"\b(?:only\s+when|when|if|unless|provided\s+that|while|after|before|requires?|must|needs?)\b[^,;]*$",
    re.IGNORECASE,
)
_ACTION_TIMING_RE = re.compile(
    r"\b(?:preemptive|auto(?:matic)?|charged|aura activation|battle start|"
    r"start of turn|end of turn|turn start|turn end|when used|on damage)\b",
    re.IGNORECASE,
)
_HIT_COUNT_RE = re.compile(
    r"\b(?:xxl|xl|l|m|s)\s*[x×]\s*(\d+)(?![\d.])\b|"
    r"\b(?:attacks?|hits?)\b[^.;]*?\b[x×]\s*(\d+)(?![\d.])\b",
    re.IGNORECASE,
)
_FORMULA_RE = re.compile(r"\b(?:based on|depending on|according to|scales? with)\b[^.;,]*", re.IGNORECASE)
_REPLACEMENT_RE = re.compile(r"\b(?:replace|replaces|replacing|replacement|change(?:s|d)? into)\b", re.IGNORECASE)
_RESOURCE_OPERATION_RE = re.compile(
    r"\b(?:consume(?:s|d)?|spend(?:s|ing)?|use(?:s|d)?)\b[^.;]*\b(?:charge|stack|mp|resource)s?\b|"
    r"\b(?:grant(?:s|ed)?|gain(?:s|ed)?|add(?:s|ed)?|give(?:s|n)?)\b[^.;]*\b(?:charge|stack)s?\b",
    re.IGNORECASE,
)
_KNOWN_STAT_CAPABILITIES = {
    "power": "power_up",
    "intelligence": "intelligence_up",
    "speed": "speed_up",
    "luck": "luck_up",
}
_CAPABILITY_GAP_SEMANTIC_TYPES = frozenset(
    {
        "stat_increase",
        "stat_decrease",
        "damage_modifier",
        "defensive_effect",
        "unsupported_effect",
        "status_or_effect_application",
        "removal",
    }
)
_STAT_WORD_RE = re.compile(r"\b(?:power|intelligence|speed|luck|max(?:imum)?\s+hp|max(?:imum)?\s+mp)\b", re.IGNORECASE)


def _clean(value: str) -> str:
    return _SPACE_RE.sub(" ", value or "").strip()


def _key(value: str) -> str:
    return _clean(value).casefold()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower() or "unknown"


def _fact_id(fact: Mapping[str, Any]) -> str:
    return str(
        fact.get("skill_id")
        or fact.get("passive_skill_id")
        or fact.get("sidekick_skill_id")
        or fact.get("sidekick_aura_id")
        or ""
    )


def _record_type_from_witness(witness: Mapping[str, Any]) -> str:
    value = str(witness.get("record_type") or "")
    return {
        "active_skill": "skill",
        "passive_skill": "passive",
        "sidekick_auto": "sidekick_skill",
        "sidekick_charge": "sidekick_skill",
        "sidekick_aura": "sidekick_aura",
    }.get(value, value)


def _fact_key(record_type: str) -> str:
    return {
        "active_skill": "skill_id",
        "passive_skill": "passive_skill_id",
        "sidekick_auto": "sidekick_skill_id",
        "sidekick_charge": "sidekick_skill_id",
        "sidekick_aura": "sidekick_aura_id",
    }.get(record_type, "skill_id")


@dataclass(frozen=True)
class SourceSpan:
    location: str
    block_kind: str
    ancestry: tuple[str, ...]
    token_start: int
    token_end: int
    text: str
    character_start: int | None = None
    character_end: int | None = None


@dataclass(frozen=True)
class ClassifiedOccurrence:
    occurrence_id: str
    occurrence_kind: str
    source_fact_id: str
    record_type: str
    entity_name: str
    source_capture_sha256: str
    source_url: str
    source_span: SourceSpan | None
    source_text: str
    actor: str
    direction: str
    recipient: str
    target_cardinality: str
    condition: str
    trigger: str
    result: str
    magnitude: Mapping[str, str]
    duration_activation: Mapping[str, str]
    element: str
    attack_type: str
    state_reference: str
    definition_support: str
    semantic_state: str
    authority: str
    capability_value: str = ""
    dependency_value: str = ""
    legacy_proposal_id: str = ""
    derived_projection: str = ""
    semantic_type: str = ""
    hit_count: str = ""
    formula_metadata: Mapping[str, str] = field(default_factory=dict)
    action_timing: str = ""
    semantic_subject: str = ""
    condition_source_span: SourceSpan | None = None
    timing_source_span: SourceSpan | None = None
    probability: Mapping[str, str] = field(default_factory=dict)
    recipient_name: str = ""
    capability_gap: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClassifiedRelationship:
    relationship_id: str
    source_fact_id: str
    source_owner: str
    source_occurrence_id: str
    target_kind: str
    target_id: str
    operation: str
    condition: str
    timing: str
    source_span: SourceSpan
    resolution_status: str
    resolution_detail: str
    resolution_basis: str
    definition_status: str
    candidate_target_ids: tuple[str, ...]
    semantic_state: str
    authority: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClassifiedUnit:
    occurrences: tuple[ClassifiedOccurrence, ...]
    relationships: tuple[ClassifiedRelationship, ...]


@dataclass(frozen=True)
class _SourceAtom:
    text: str
    effect_text: str
    character_start: int
    character_end: int
    condition: str = ""
    condition_start: int | None = None
    condition_end: int | None = None
    action_timing: str = ""
    timing_start: int | None = None
    timing_end: int | None = None


@dataclass(frozen=True)
class _AtomContext:
    block: StructuralBlock
    fragment_text: str
    token_positions: tuple[tuple[StructuralToken, int, int], ...]
    atom: _SourceAtom
    selected_tokens: tuple[StructuralToken, ...]
    source_span: SourceSpan
    condition_span: SourceSpan | None
    timing_span: SourceSpan | None


def _stable_occurrence_id(source_fact_id: str, kind: str, span: SourceSpan | None, ordinal: int) -> str:
    # The source span is retained as immutable evidence on the occurrence.  The
    # ID itself stays stable across comparison arms so a source-fact/kind/sequence
    # mapping can be audited without silently copying a legacy proposal ID.
    identity = f"{source_fact_id}|{kind}|{ordinal}"
    return f"occ:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def _source_ok(witness: Mapping[str, Any]) -> bool:
    return all(
        witness.get(key) == "passed"
        for key in ("source_identity_status", "source_record_selection_status", "source_fixture_status")
    ) and bool(witness.get("source_slice_sha256"))


def _tokens_to_fragments(block: StructuralBlock) -> list[tuple[list[StructuralToken], int, int]]:
    fragments: list[tuple[list[StructuralToken], int, int]] = []
    current: list[StructuralToken] = []
    start = 0
    for index, token in enumerate(block.tokens):
        if token.kind == "line_break":
            if current:
                fragments.append((current, start, index - 1))
            current = []
            start = index + 1
            continue
        current.append(token)
    if current:
        fragments.append((current, start, len(block.tokens) - 1))
    return fragments


def _direction(text: str) -> str:
    lowered = _key(text)
    if re.search(r"\b(?:enemy|enemies|boss|opponent)\b", lowered):
        return "enemy"
    if re.search(r"\b(?:ally|allies|party|party members|frontline)\b", lowered):
        return "ally"
    if re.search(r"\b(?:user|self|own)\b", lowered):
        return "self"
    if re.search(r"\b(?:zone|stance|field)\b", lowered):
        return "field"
    return "unknown"


def _recipient_and_cardinality(text: str) -> tuple[str, str]:
    lowered = _key(text)
    if re.search(r"\b(?:all enemies|each enemy|all opponents)\b", lowered):
        return "all_enemies", "multiple"
    if re.search(r"\b(?:a single enemy|single enemy|one enemy)\b", lowered):
        return "single_enemy", "single"
    if re.search(r"\b(?:all party members|party members|the party|all allies|all ally)\b", lowered):
        return "party", "multiple"
    if re.search(r"\b(?:frontline|front line)\b", lowered):
        return "frontline", "multiple"
    if re.search(r"\b(?:adjacent allies|left and right)\b", lowered):
        return "adjacent_allies", "multiple"
    if re.search(r"\b(?:an ally|one ally|single ally|ally)\b", lowered):
        return "ally", "single"
    if re.search(r"\b(?:user|self|own)\b", lowered):
        return "self", "single"
    return "unknown", "unknown"


def _named_recipient(text: str, references: Sequence[StructuralToken]) -> str:
    lowered = _key(text)
    for token in references:
        label = _key(token.text)
        if label and re.search(rf"\b(?:to|for|target(?:s|ing)?)\s+(?:the\s+)?{re.escape(label)}\b", lowered):
            return _clean(token.text)
    return ""


def _condition(text: str) -> str:
    match = _CONDITION_RE.search(text)
    return _clean(text[match.start() :]) if match else ""


def _trigger(text: str) -> str:
    lowered = _key(text)
    for phrase, value in (
        ("preemptive", "preemptive"),
        ("auto", "auto"),
        ("charged", "charged"),
        ("aura activation", "aura_activation"),
        ("battle start", "battle_start"),
        ("start of turn", "turn_start"),
        ("end of turn", "turn_end"),
        ("turn start", "turn_start"),
        ("turn end", "turn_end"),
        ("on damage", "on_damage"),
        ("when used", "on_use"),
    ):
        if phrase in lowered:
            return value
    return ""


def _magnitude(text: str) -> dict[str, str]:
    percent = _PERCENT_RE.search(text)
    probability = _PROBABILITY_RE.search(text)
    multiplier = _MULTIPLIER_RE.search(text)
    hit_count = _hit_count(text)
    if percent and (not probability or percent.start() != probability.start()):
        return {"value": percent.group(1), "unit": "percent", "raw": percent.group(0)}
    if multiplier and not hit_count:
        return {"value": multiplier.group(1), "unit": "multiplier", "raw": multiplier.group(0)}
    count = re.search(
        r"\b(?:hit count|number of hits|skill hits?)\b[^.;]*?\b(?:by|to)\s+(\d+)\b",
        text,
        re.IGNORECASE,
    )
    if count:
        return {"value": count.group(1), "unit": "count", "raw": count.group(0)}
    fixed = re.search(r"\b(?:deal|damage|restore|recover|heal)\s+(\d{3,})\b", text, re.IGNORECASE)
    if fixed:
        return {"value": fixed.group(1), "unit": "flat", "raw": fixed.group(0)}
    return {}


def _probability(text: str) -> dict[str, str]:
    match = _PROBABILITY_RE.search(text)
    if not match:
        return {}
    return {"value": match.group(1), "unit": "percent", "raw": match.group(0)}


def _duration_activation(text: str) -> dict[str, str]:
    duration = _TURN_RE.search(text)
    activation = _ACTIVATION_RE.search(text)
    result: dict[str, str] = {}
    if duration:
        result["duration_turns"] = duration.group(1)
    if activation:
        result["activation"] = activation.group(1) if activation.group(1) else "once_per_battle"
    if re.search(r"\bcurrent turn only\b", text, re.IGNORECASE):
        result["duration"] = "current_turn"
    return result


def _element(text: str) -> str:
    match = _ELEMENT_RE.search(text)
    return match.group(0).title() if match else ""


def _attack_type(text: str) -> str:
    match = _ATTACK_TYPE_RE.search(text)
    if not match:
        return ""
    value = match.group(0).casefold()
    return "Piercing" if value in {"piercing", "pierce"} else value.title()


def _hit_count(text: str) -> str:
    match = _HIT_COUNT_RE.search(text)
    if not match or not re.search(r"\b(?:attack|attacks|hit|hits)\b", text, re.IGNORECASE):
        return ""
    return next((value for value in match.groups() if value), "")


def _formula_metadata(text: str) -> dict[str, str]:
    match = _FORMULA_RE.search(text)
    return {"raw": _clean(match.group(0))} if match else {}


def _has_effect(text: str) -> bool:
    if _formula_metadata(text) and not _ACTION_HEAD_RE.search(text):
        return False
    return bool(_ACTION_HEAD_RE.search(text) or _EFFECT_RE.search(text))


def _effect_semantics(text: str, direction: str) -> list[tuple[str, str, str]]:
    lowered = _key(text)
    if _REPLACEMENT_RE.search(lowered) and re.search(r"\b(?:skill|action|slot|move)\b", lowered):
        return [("action_replacement", "", "skill_action")]
    if re.search(r"\b(?:hit count|number of hits|skill hits?)\b", lowered):
        return [("hit_count_modifier", "", "hit_count")]
    if _RESOURCE_OPERATION_RE.search(lowered):
        operation = "resource_consumption" if re.search(r"\b(?:consume|spend|use)", lowered) else "resource_grant"
        resource = next((value for value in ("charge", "stack", "mp") if re.search(rf"\b{value}s?\b", lowered)), "unknown_resource")
        return [(operation, "", resource)]
    if re.search(r"\b(?:revive|revives|revived|reviving)\b", lowered):
        capability = "revive" if direction in {"ally", "self"} else ""
        return [("revive", capability, "ally" if direction == "ally" else "self_or_unknown")]
    if re.search(r"\b(?:remove|removes|removing|cleanse|cleanses|cleansing)\b", lowered):
        if direction in {"ally", "self"}:
            if re.search(r"\b(?:status ailments?|ailments?)\b", lowered):
                return [("status_cleansing", "remove_status_ailment", "status_ailment")]
            if re.search(r"\bdebuffs?\b", lowered):
                return [("debuff_cleansing", "remove_debuff", "debuff")]
        return [("removal", "", "unknown_removal_target")]
    if re.search(r"\b(?:heal|heals|healing|restore|restores|recover|recovers)\b", lowered):
        if re.search(r"\b(?:mp|magic points?)\b", lowered):
            capability = "recover_mp" if direction in {"ally", "self"} else ""
            return [("mp_recovery", capability, "mp")]
        if re.search(r"\b(?:hp|health points?)\b", lowered) or re.search(r"\bheal(?:s|ing)?\b", lowered):
            capability = "heal_hp" if direction in {"ally", "self"} else ""
            return [("hp_recovery", capability, "hp")]
    if re.search(r"\b(?:inflict|inflicts|apply|applies|grant|grants)\b", lowered):
        if direction == "enemy":
            for status, capability in (
                ("pain", "inflict_pain"),
                ("poison", "inflict_poison"),
                ("break", "inflict_break"),
            ):
                if re.search(rf"\b{status}\b", lowered):
                    return [("status_infliction", capability, status)]
        if direction in {"ally", "self"} and re.search(r"\bstatus immunity\b", lowered):
            return [("status_immunity", "grant_status_immunity", "status_ailment")]
        return [("status_or_effect_application", "", "unknown_status_or_target")]
    if re.search(r"\b(?:deploy|deploys|deployed|deploying)\b[^.;]*\bzone\b", lowered):
        return [("zone_deployment", "deploy_zone", "zone")]
    if re.search(r"\b(?:awaken|awakens|awakened|awakening)\b[^.;]*\bzone\b", lowered):
        return [("zone_awakening", "awaken_zone", "zone")]
    if re.search(r"\b(?:decrease|decreases|reduce|reduces|lower|lowers)\b[^.;]*\bresistance\b", lowered):
        if direction == "enemy":
            for property_name, capability in (
                ("physical", "physical_resistance_down"),
                ("magic", "magic_resistance_down"),
                ("element", "element_resistance_down"),
                ("attack type", "attack_type_resistance_down"),
            ):
                if property_name in lowered:
                    return [("resistance_reduction", capability, property_name.replace(" ", "_"))]
            return [("resistance_reduction", "enemy_resistance_down", "resistance")]
    if direction in {"ally", "self"} and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts)\b[^.;]*\bresistance\b", lowered):
        return [("resistance_increase", "ally_resistance_up", "resistance")]
    if direction in {"ally", "self"} and re.search(r"\b(?:damage reduction|reduce damage (?:taken|received)|damage taken)\b", lowered):
        return [("damage_mitigation", "damage_reduction", "damage_received")]
    if direction in {"ally", "self"} and re.search(r"\bbarrier\b", lowered):
        return [("damage_mitigation", "damage_reduction_barrier", "barrier")]
    if direction in {"ally", "self"} and re.search(r"\bshield\b", lowered):
        return [("damage_mitigation", "shield", "shield")]
    if re.search(r"\bcritical rate\b", lowered) and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts)\b", lowered):
        if direction in {"ally", "self"}:
            if "physical" in lowered:
                return [("critical_support", "physical_critical_rate_up", "physical_critical_rate")]
            if "magic" in lowered:
                return [("critical_support", "magic_critical_rate_up", "magic_critical_rate")]
    if (
        re.search(r"\b(?:attacks|deals|deal)\b", lowered)
        or re.search(r"\battack\s+(?:all|each|a|an|single|enemy|enemies|opponent|opponents)\b", lowered)
        or re.search(r"\b(?:fixed damage|performs?\s+(?:an?\s+)?attack)\b", lowered)
    ):
        capability = "direct_damage" if direction == "enemy" else ""
        return [("damage_event", capability, "damage")]
    stat_matches = list(_STAT_WORD_RE.finditer(lowered))
    if stat_matches and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts|up)\b", lowered):
        stats = list(dict.fromkeys(re.sub(r"\s+", " ", match.group(0).casefold()) for match in stat_matches))
        return [
            (
                "stat_increase",
                _KNOWN_STAT_CAPABILITIES.get(stat, "") if direction in {"ally", "self"} else "",
                stat.replace(" ", "_"),
            )
            for stat in stats
        ]
    if stat_matches and re.search(r"\b(?:decrease|decreases|reduce|reduces|lower|lowers|down)\b", lowered):
        stats = list(dict.fromkeys(re.sub(r"\s+", " ", match.group(0).casefold()) for match in stat_matches))
        return [("stat_decrease", "", stat.replace(" ", "_")) for stat in stats]
    if re.search(r"\b(?:outgoing damage|damage dealt)\b", lowered) and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts|up)\b", lowered):
        capability = "outgoing_damage_up" if direction in {"ally", "self"} else ""
        return [("damage_modifier", capability, "outgoing_damage")]
    if re.search(r"\b(?:damage received|damage taken|damage reduction|barrier|shield)\b", lowered):
        return [("defensive_effect", "", "damage_mitigation")]
    return [("unsupported_effect", "", "unknown")]


def _dependency_value(text: str) -> str:
    lowered = _key(text)
    if _formula_metadata(text):
        return ""
    if re.search(r"\b(?:zone|stance)\b", lowered):
        return "requires_zone_or_stance"
    if "lunatic" in lowered:
        return "requires_lunatic_or_variant"
    if re.search(r"\b(?:stack|stacks|charge)\b", lowered):
        return "requires_resource_state"
    if re.search(r"\b(?:blood contract|status|frontline|party member|ally)\b", lowered):
        return "recipient_or_state_condition"
    if re.search(r"\b(?:once per battle|limited|consumes?)\b", lowered):
        return "activation_constraint"
    return "scoped_condition"


def _trim_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split_action_ranges(text: str, start: int, end: int) -> list[tuple[int, int]]:
    matches = [match for match in _ACTION_HEAD_RE.finditer(text, start, end)]
    boundaries: list[int] = []
    previous_end = matches[0].end() if matches else start
    for match in matches[1:]:
        between = text[previous_end:match.start()]
        connector = re.search(r"(?:,\s*(?:and|then)?\s*|\s+(?:and|then)\s+)$", between, re.IGNORECASE)
        if connector:
            boundaries.append(previous_end + connector.start())
        previous_end = match.end()
    if not boundaries:
        return [_trim_range(text, start, end)]
    ranges: list[tuple[int, int]] = []
    previous = start
    for boundary in boundaries:
        left_start, left_end = _trim_range(text, previous, boundary)
        if left_start < left_end:
            ranges.append((left_start, left_end))
        action = next((match.start() for match in matches if match.start() >= boundary), boundary)
        previous = action
    right_start, right_end = _trim_range(text, previous, end)
    if right_start < right_end:
        ranges.append((right_start, right_end))
    return ranges


def _source_atoms(text: str) -> list[_SourceAtom]:
    """Split a source fragment at clear action boundaries and retain local context."""
    atoms: list[_SourceAtom] = []
    segment_start = 0
    segment_ranges: list[tuple[int, int]] = []
    for separator in re.finditer(r";|(?<!\d)\.(?!\d)", text):
        segment_ranges.append((segment_start, separator.start()))
        segment_start = separator.end()
    segment_ranges.append((segment_start, len(text)))
    for segment_start, segment_end in segment_ranges:
        start, end = _trim_range(text, segment_start, segment_end)
        if start == end:
            continue

        condition = ""
        condition_start: int | None = None
        condition_end: int | None = None
        condition_match = _LEADING_CONDITION_RE.match(text, start, end)
        body_start = start
        if condition_match and _trigger(condition_match.group("condition")) != "on_use":
            condition = _clean(condition_match.group("condition"))
            condition_start = condition_match.start("condition")
            condition_end = condition_match.end("condition")
            body_start = condition_match.end()

        timing = ""
        timing_start: int | None = None
        timing_end: int | None = None
        timing_match = _ACTION_TIMING_RE.search(text, body_start, end)
        first_action = _ACTION_HEAD_RE.search(text, body_start, end)
        if timing_match and (first_action is None or timing_match.start() < first_action.start()):
            timing = _trigger(timing_match.group(0))
            timing_start = timing_match.start()
            timing_end = timing_match.end()
            body_start = timing_match.end()
            while body_start < end and (text[body_start].isspace() or text[body_start] in ",:"):
                body_start += 1

        body_start, body_end = _trim_range(text, body_start, end)
        has_action = bool(_ACTION_HEAD_RE.search(text, body_start, body_end))
        if not has_action and _CONDITION_RE.search(text[start:end]) and not _formula_metadata(text[start:end]):
            trigger = _trigger(text[start:end])
            is_trigger = bool(trigger)
            atoms.append(
                _SourceAtom(
                    text=_clean(text[start:end]),
                    effect_text="",
                    character_start=start,
                    character_end=end,
                    condition="" if is_trigger else _clean(text[start:end]),
                    condition_start=None if is_trigger else start,
                    condition_end=None if is_trigger else end,
                    action_timing=trigger,
                    timing_start=start if is_trigger else None,
                    timing_end=end if is_trigger else None,
                )
            )
            continue
        for action_start, action_end in _split_action_ranges(text, body_start, body_end):
            local_condition = condition
            local_condition_start = condition_start
            local_condition_end = condition_end
            effect_end = action_end
            trailing = _TRAILING_CONDITION_RE.search(text, action_start, action_end)
            if trailing and trailing.start() > action_start:
                trailing_text = _clean(trailing.group(0))
                trailing_timing = _trigger(trailing_text)
                if trailing_timing == "on_use":
                    timing = trailing_timing
                    timing_start = trailing.start()
                    timing_end = trailing.end()
                else:
                    local_condition = trailing_text
                    local_condition_start = trailing.start()
                    local_condition_end = trailing.end()
                effect_end = trailing.start()
            effect_start, effect_end = _trim_range(text, action_start, effect_end)
            if effect_start == effect_end:
                continue
            effect_text = _clean(text[effect_start:effect_end])
            atoms.append(
                _SourceAtom(
                    text=effect_text,
                    effect_text=effect_text,
                    character_start=effect_start,
                    character_end=effect_end,
                    condition=local_condition,
                    condition_start=local_condition_start,
                    condition_end=local_condition_end,
                    action_timing=timing or _trigger(effect_text),
                    timing_start=timing_start,
                    timing_end=timing_end,
                )
            )

    return atoms


def _state_reference(text: str) -> str:
    match = _STATE_RE.search(text)
    return match.group(0) if match else ""


def _definition_support(
    references: Sequence[StructuralToken],
    resolution_by_location: Mapping[str, Mapping[str, Any]],
    *,
    admit_definitions: bool,
) -> str:
    if not references:
        return "not_applicable"
    statuses = [str(resolution_by_location.get(token.location, {}).get("status", "access_failure")) for token in references]
    if admit_definitions and any(status in {"resolved", "visited"} for status in statuses):
        return "admitted"
    if any(status in {"access_failure", "unresolved_mapping", "depth_budget_exhausted", "page_budget_exhausted", "frontier_budget_exhausted"} for status in statuses):
        return "unresolved"
    if all(status == "excluded" for status in statuses):
        return "excluded"
    return "not_admitted"


def _occurrence(
    *,
    kind: str,
    witness: Mapping[str, Any],
    span: SourceSpan | None,
    text: str,
    ordinal: int,
    semantic_state: str,
    authority: str,
    definition_support: str,
    references: Sequence[StructuralToken] = (),
    capability_value: str = "",
    dependency_value: str = "",
    legacy_proposal_id: str = "",
    effect_text: str | None = None,
    condition: str | None = None,
    action_timing: str | None = None,
    semantic_type: str = "",
    hit_count: str = "",
    formula_metadata: Mapping[str, str] | None = None,
    semantic_subject: str = "",
    condition_source_span: SourceSpan | None = None,
    timing_source_span: SourceSpan | None = None,
    probability: Mapping[str, str] | None = None,
    state_reference: str | None = None,
    capability_gap: bool = False,
) -> ClassifiedOccurrence:
    scoped_text = effect_text if effect_text is not None else text
    recipient, cardinality = _recipient_and_cardinality(scoped_text)
    return ClassifiedOccurrence(
        occurrence_id=_stable_occurrence_id(str(witness["record_id"]), kind, span, ordinal),
        occurrence_kind=kind,
        source_fact_id=str(witness["record_id"]),
        record_type=str(witness.get("record_type") or ""),
        entity_name=str(witness.get("entity_name") or ""),
        source_capture_sha256=str(witness.get("source_capture_sha256") or witness.get("capture_sha256") or ""),
        source_url=str(witness.get("source_url") or ""),
        source_span=span,
        source_text=_clean(text),
        actor=str(witness.get("entity_name") or "source_owner"),
        direction=_direction(scoped_text),
        recipient=recipient,
        recipient_name=_named_recipient(scoped_text, references),
        target_cardinality=cardinality,
        condition=_condition(text) if condition is None else condition,
        trigger=_trigger(text) if action_timing is None else action_timing,
        result=_clean(scoped_text),
        magnitude=_magnitude(scoped_text),
        duration_activation=_duration_activation(scoped_text),
        element=_element(scoped_text),
        attack_type=_attack_type(scoped_text),
        state_reference=_state_reference(scoped_text) if state_reference is None else state_reference,
        definition_support=definition_support,
        semantic_state=semantic_state,
        authority=authority,
        capability_value=capability_value,
        dependency_value=dependency_value,
        legacy_proposal_id=legacy_proposal_id,
        derived_projection=(
            "multi_entity_damage"
            if kind == "effect" and capability_value == "direct_damage" and cardinality == "multiple"
            else ""
        ),
        semantic_type=semantic_type,
        hit_count=hit_count,
        formula_metadata=dict(formula_metadata or {}),
        action_timing=action_timing or "",
        semantic_subject=semantic_subject,
        condition_source_span=condition_source_span,
        timing_source_span=timing_source_span,
        probability=dict(probability or _probability(scoped_text)),
        capability_gap=capability_gap,
    )


def _render_fragment_tokens(
    tokens: Sequence[StructuralToken],
) -> tuple[str, list[tuple[StructuralToken, int, int]]]:
    pieces: list[str] = []
    positions: list[tuple[StructuralToken, int, int]] = []
    length = 0
    for token in tokens:
        value = _clean(token.text)
        if not value:
            continue
        if pieces:
            pieces.append(" ")
            length += 1
        start = length
        pieces.append(value)
        length += len(value)
        positions.append((token, start, length))
    return "".join(pieces), positions


def _range_span(
    block: StructuralBlock,
    positions: Sequence[tuple[StructuralToken, int, int]],
    start: int,
    end: int,
    text: str,
) -> SourceSpan:
    selected = [token for token, token_start, token_end in positions if token_start < end and token_end > start]
    if not selected:
        selected = [token for token, _token_start, _token_end in positions]
    return SourceSpan(
        location=block.location,
        block_kind=block.kind,
        ancestry=tuple(block.ancestry),
        token_start=min((token.order for token in selected), default=-1),
        token_end=max((token.order for token in selected), default=-1),
        text=_clean(text),
        character_start=start,
        character_end=end,
    )


def _fragment_atoms(
    block: StructuralBlock,
    tokens: Sequence[StructuralToken],
    start: int,
    end: int,
    text: str | None = None,
    token_positions: Sequence[tuple[StructuralToken, int, int]] | None = None,
) -> list[_AtomContext]:
    fragment_text, rendered_positions = (
        (text, list(token_positions))
        if text is not None and token_positions is not None
        else _render_fragment_tokens(tokens)
    )
    contexts: list[_AtomContext] = []
    for atom in _source_atoms(fragment_text):
        selected = tuple(
            token
            for token, token_start, token_end in rendered_positions
            if token_start < atom.character_end and token_end > atom.character_start
        )
        source_span = _range_span(
            block,
            rendered_positions,
            atom.character_start,
            atom.character_end,
            atom.text,
        )
        condition_span = None
        if atom.condition_start is not None and atom.condition_end is not None:
            condition_span = _range_span(
                block,
                rendered_positions,
                atom.condition_start,
                atom.condition_end,
                atom.condition,
            )
        timing_span = None
        if atom.timing_start is not None and atom.timing_end is not None:
            timing_span = _range_span(
                block,
                rendered_positions,
                atom.timing_start,
                atom.timing_end,
                _clean(fragment_text[atom.timing_start:atom.timing_end]),
            )
        contexts.append(
            _AtomContext(
                block=block,
                fragment_text=fragment_text,
                token_positions=tuple(rendered_positions),
                atom=atom,
                selected_tokens=selected,
                source_span=source_span,
                condition_span=condition_span,
                timing_span=timing_span,
            )
        )
    return contexts


def _unit_atom_contexts(unit: StructuralUnit) -> list[_AtomContext]:
    contexts: list[_AtomContext] = []
    for block in unit.blocks:
        for tokens, start, end in _tokens_to_fragments(block):
            contexts.extend(_fragment_atoms(block, tokens, start, end))
    return contexts


def _reference_context(
    contexts: Sequence[_AtomContext],
    token: StructuralToken,
) -> tuple[_AtomContext | None, int | None, int | None]:
    for context in contexts:
        for positioned_token, start, end in context.token_positions:
            if positioned_token.location != token.location or positioned_token.order != token.order:
                continue
            atom = context.atom
            if atom.character_start <= start < atom.character_end:
                return context, start, end
            if (
                atom.condition_start is not None
                and atom.condition_end is not None
                and atom.condition_start <= start < atom.condition_end
            ):
                return context, start, end
            if atom.timing_start is not None and atom.timing_end is not None and atom.timing_start <= start < atom.timing_end:
                return context, start, end
    return None, None, None


def _relationship_operation(text: str, target_text: str) -> str:
    lowered = _key(text)
    target = _key(target_text)
    target_start = lowered.find(target) if target else -1
    before_target = lowered[:target_start] if target_start >= 0 else lowered
    verbs = (
        (r"\b(?:choose|chooses|select|selects|branch|branches)\b", "branches_to"),
        (r"\b(?:replace|replaces|replaced|replacing|replacement)\b", "replaces"),
        (r"\b(?:require|requires|required)\b", "requires"),
        (r"\b(?:activate|activates|activated|activating)\b", "activates"),
        (r"\b(?:awaken|awakens|awakened|awakening)\b", "awakens"),
        (r"\b(?:grant|grants|granted|gain|gains|gained|add|adds|added)\b", "grants"),
        (r"\b(?:consume|consumes|consumed|spend|spends|spent)\b", "consumes"),
        (r"\bscales?\s+with\b", "scales_with"),
    )
    latest: tuple[int, str] | None = None
    for pattern, operation in verbs:
        for match in re.finditer(pattern, before_target):
            latest = max(latest or (match.start(), operation), (match.start(), operation))
    if latest is None:
        return "references"
    verb_position, operation = latest
    return operation if len(before_target) - verb_position <= 40 else "references"


def _relationship_id(
    source_fact_id: str,
    target_kind: str,
    target_id: str,
    candidates: Sequence[str],
    operation: str,
    source_span: SourceSpan,
    condition: str,
    timing: str,
) -> str:
    identity = _canonical(
        [
        source_fact_id,
            target_kind,
            target_id,
            sorted(candidates),
            operation,
            source_span.location,
            source_span.token_start,
            source_span.character_start,
            condition,
            timing,
        ]
    )
    return f"rel:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def _source_occurrence_for_reference(
    occurrences: Sequence[ClassifiedOccurrence],
    context: _AtomContext | None,
    token_start: int | None,
    token_end: int | None,
) -> str:
    if context is None or token_start is None or token_end is None:
        return ""
    for occurrence in occurrences:
        for span in (occurrence.source_span, occurrence.condition_source_span, occurrence.timing_source_span):
            if (
                span is not None
                and span.location == context.block.location
                and span.character_start is not None
                and span.character_end is not None
                and span.character_start < token_end
                and span.character_end > token_start
            ):
                return occurrence.occurrence_id
    return ""


def _classify_relationships(
    *,
    witness: Mapping[str, Any],
    root: StructuralUnit,
    resolutions: Sequence[Mapping[str, Any]],
    unit_by_id: Mapping[str, StructuralUnit],
    contexts: Mapping[str, Sequence[_AtomContext]],
    occurrences: Sequence[ClassifiedOccurrence],
    semantic_state: str,
    authority: str,
    mechanic_registry: SharedMechanicRegistry | None,
) -> list[ClassifiedRelationship]:
    contexts_by_unit = {key: list(value) for key, value in contexts.items()}
    origin_ids = {str(row.get("origin_unit_id") or root.unit_id) for row in resolutions}
    origin_ids.add(root.unit_id)
    for origin_id in origin_ids:
        origin = unit_by_id.get(origin_id)
        if origin is not None and origin_id not in contexts_by_unit:
            contexts_by_unit[origin_id] = _unit_atom_contexts(origin)

    relationships: dict[str, ClassifiedRelationship] = {}

    def add_relationship(
        *,
        source_fact_id: str,
        source_owner: str,
        source_occurrence_id: str,
        target_kind: str,
        target_id: str,
        candidate_target_ids: Sequence[str],
        operation: str,
        condition: str,
        timing: str,
        source_span: SourceSpan,
        resolution_status: str,
        resolution_detail: str,
        resolution_basis: str,
        definition_status: str,
    ) -> None:
        relation_id = _relationship_id(
            source_fact_id,
            target_kind,
            target_id,
            candidate_target_ids,
            operation,
            source_span,
            condition,
            timing,
        )
        relationships.setdefault(
            relation_id,
            ClassifiedRelationship(
                relationship_id=relation_id,
                source_fact_id=source_fact_id,
                source_owner=source_owner,
                source_occurrence_id=source_occurrence_id,
                target_kind=target_kind,
                target_id=target_id,
                operation=operation,
                condition=condition,
                timing=timing,
                source_span=source_span,
                resolution_status=resolution_status,
                resolution_detail=resolution_detail,
                resolution_basis=resolution_basis,
                definition_status=definition_status,
                candidate_target_ids=tuple(sorted(set(candidate_target_ids))),
                semantic_state=semantic_state,
                authority=authority,
            ),
        )

    for row in resolutions:
        if row.get("status") == "excluded":
            # General documentation links remain ordinary references.
            continue
        origin_id = str(row.get("origin_unit_id") or root.unit_id)
        origin = unit_by_id.get(origin_id, root)
        token = next(
            (
                candidate
                for block in origin.blocks
                for candidate in block.tokens
                if candidate.kind == "reference" and candidate.location == row.get("occurrence_location")
            ),
            None,
        )
        if token is None:
            continue
        context, token_start, token_end = _reference_context(contexts_by_unit.get(origin_id, ()), token)
        local_text = context.atom.text if context else token.text
        operation = "replaces" if row.get("variant_relationship") else _relationship_operation(local_text, token.text)
        variant = row.get("variant_relationship") or {}
        condition = str(variant.get("condition") or (context.atom.condition if context else ""))
        timing = context.atom.action_timing if context else ""
        block = next((block for block in origin.blocks if any(item.location == token.location for item in block.tokens)), None)
        if block is None:
            continue
        source_span = SourceSpan(
            location=token.location,
            block_kind=block.kind,
            ancestry=tuple(block.ancestry),
            token_start=token.order,
            token_end=token.order,
            text=token.text,
            character_start=token_start,
            character_end=token_end,
        )
        target_id = str(row.get("target_source_fact_id") or "")
        target_kind = "source_fact" if target_id else "unresolved"
        candidate_unit_ids = [str(value) for value in row.get("candidate_unit_ids", [])]
        candidates = [
            str(unit_by_id[candidate].source_fact_id)
            for candidate in candidate_unit_ids
            if candidate in unit_by_id and unit_by_id[candidate].source_fact_id
        ]
        add_relationship(
            source_fact_id=str(origin.source_fact_id or witness.get("record_id") or ""),
            source_owner=origin.entity_name or str(witness.get("entity_name") or ""),
            source_occurrence_id=_source_occurrence_for_reference(occurrences, context, token_start, token_end),
            target_kind=target_kind,
            target_id=target_id,
            candidate_target_ids=candidates,
            operation=operation,
            condition=condition,
            timing=timing,
            source_span=source_span,
            resolution_status=str(row.get("status") or "unresolved"),
            resolution_detail=str(row.get("reason") or ""),
            resolution_basis=str(row.get("resolution_basis") or "captured_reference"),
            definition_status="not_applicable",
        )

    for origin_id in sorted(origin_ids):
        origin = unit_by_id.get(origin_id)
        if origin is None:
            continue
        for mention in resolve_shared_mechanics(
            origin,
            parent_source_fact_id=str(origin.source_fact_id or witness.get("record_id") or ""),
            registry=mechanic_registry,
        ):
            context_token = next(
                (
                    token
                    for block in origin.blocks
                    for token in block.tokens
                    if token.location == mention.source_location
                ),
                None,
            )
            context, token_start, token_end = (
                _reference_context(contexts_by_unit.get(origin_id, ()), context_token)
                if context_token is not None
                else (None, None, None)
            )
            block = next(
                (block for block in origin.blocks if any(token.location == mention.source_location for token in block.tokens)),
                None,
            )
            if block is None:
                continue
            source_span = SourceSpan(
                location=mention.source_location,
                block_kind=block.kind,
                ancestry=tuple(block.ancestry),
                token_start=context_token.order if context_token else -1,
                token_end=context_token.order if context_token else -1,
                text=mention.mention,
                character_start=(token_start + mention.source_offset_start) if token_start is not None and mention.source_offset_start >= 0 else token_start,
                character_end=(token_start + mention.source_offset_end) if token_start is not None and mention.source_offset_end >= 0 else token_end,
            )
            target_id = mention.mechanic_id if mention.resolution_status == "resolved" else ""
            target_kind = "shared_mechanic" if target_id else "unresolved"
            operation_text = context.atom.text if context else mention.mention
            add_relationship(
                source_fact_id=mention.parent_source_fact_id or str(origin.source_fact_id or witness.get("record_id") or ""),
                source_owner=mention.parent_owner_name or origin.entity_name,
                source_occurrence_id=_source_occurrence_for_reference(occurrences, context, token_start, token_end),
                target_kind=target_kind,
                target_id=target_id,
                candidate_target_ids=mention.candidate_mechanic_ids,
                operation=_relationship_operation(operation_text, mention.mention),
                condition=context.atom.condition if context else "",
                timing=context.atom.action_timing if context else "",
                source_span=source_span,
                resolution_status=mention.resolution_status,
                resolution_detail=mention.reason,
                resolution_basis=mention.resolution_basis,
                definition_status=mention.definition_status,
            )

    return sorted(relationships.values(), key=lambda row: row.relationship_id)


def _classify_unit(
    witness: Mapping[str, Any],
    unit: StructuralUnit | None,
    all_units: Sequence[StructuralUnit],
    limits: Any,
    *,
    arm: str,
    fidelity_passed: bool,
    mechanic_registry: SharedMechanicRegistry | None = None,
) -> ClassifiedUnit:
    if unit is None:
        return ClassifiedUnit((), ())
    resolutions = resolve_bounded_references(
        [unit],
        all_units,
        limits,
        include_explicit_aliases=True,
    )
    resolution_by_location = {str(row["occurrence_location"]): row for row in resolutions}
    source_passed = _source_ok(witness)
    if arm == "fidelity_checked":
        semantic_state = "fully_supported_input" if source_passed and fidelity_passed else "unknown_non_authoritative"
        authority = "fully_supported_input_non_authoritative" if semantic_state == "fully_supported_input" else "unknown_non_authoritative"
        admit_definitions = True
    elif arm == "structural_only":
        semantic_state = "structural_only_non_authoritative"
        authority = "automatic_candidate"
        admit_definitions = False
    else:
        semantic_state = "legacy_non_authoritative"
        authority = "automatic_candidate"
        admit_definitions = False

    occurrences: list[ClassifiedOccurrence] = []
    ordinal_by_kind: Counter[str] = Counter()
    seen_dependencies: set[tuple[str, str, int | None, int | None]] = set()
    seen_triggers: set[tuple[str, str, int | None, int | None]] = set()
    seen_states: set[tuple[str, str, int | None, int | None]] = set()
    unit_contexts: dict[str, list[_AtomContext]] = {}

    for block in unit.blocks:
        for tokens, start, end in _tokens_to_fragments(block):
            text, token_positions = _render_fragment_tokens(tokens)
            if not text:
                continue
            contexts = _fragment_atoms(block, tokens, start, end, text, token_positions)
            unit_contexts.setdefault(unit.unit_id, []).extend(contexts)
            for context in contexts:
                atom = context.atom
                selected_tokens = context.selected_tokens
                atom_span = context.source_span
                condition_span = context.condition_span
                timing_span = context.timing_span
                references = [token for token in selected_tokens if token.kind == "reference"]
                support = _definition_support(references, resolution_by_location, admit_definitions=admit_definitions)
                effect_text = atom.effect_text
                direction = _direction(effect_text)
                if _has_effect(effect_text):
                    for semantic_type, capability, subject in _effect_semantics(effect_text, direction):
                        occurrences.append(
                            _occurrence(
                                kind="effect",
                                witness=witness,
                                span=atom_span,
                                text=atom.text,
                                effect_text=effect_text,
                                ordinal=ordinal_by_kind["effect"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                capability_value=capability,
                                condition=atom.condition,
                                action_timing=atom.action_timing,
                                semantic_type=semantic_type,
                                hit_count=_hit_count(effect_text),
                                formula_metadata=_formula_metadata(effect_text),
                                semantic_subject=subject,
                                condition_source_span=condition_span,
                                timing_source_span=timing_span,
                                probability=_probability(effect_text),
                                state_reference=_state_reference(atom.condition) or _state_reference(effect_text),
                                capability_gap=(
                                    not capability
                                    and semantic_type in _CAPABILITY_GAP_SEMANTIC_TYPES
                                ),
                            )
                        )
                        ordinal_by_kind["effect"] += 1

                if atom.condition:
                    condition_key = (atom_span.location, atom.condition, atom.condition_start, atom.condition_end)
                    if condition_key not in seen_dependencies:
                        seen_dependencies.add(condition_key)
                        condition_references = [
                            token for token, token_start, token_end in token_positions
                            if atom.condition_start is not None
                            and token_start < (atom.condition_end or token_end)
                            and token_end > atom.condition_start
                            and token.kind == "reference"
                        ]
                        occurrences.append(
                            _occurrence(
                                kind="dependency",
                                witness=witness,
                                span=condition_span or atom_span,
                                text=atom.condition,
                                ordinal=ordinal_by_kind["dependency"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=_definition_support(
                                    condition_references,
                                    resolution_by_location,
                                    admit_definitions=admit_definitions,
                                ),
                                references=condition_references,
                                effect_text=atom.condition,
                                condition=atom.condition,
                                action_timing="",
                                dependency_value=_dependency_value(atom.condition),
                                semantic_type="condition",
                                condition_source_span=condition_span,
                            )
                        )
                        ordinal_by_kind["dependency"] += 1

                if atom.action_timing:
                    trigger_key = (atom_span.location, atom.action_timing, atom.timing_start, atom.timing_end)
                    if trigger_key not in seen_triggers:
                        seen_triggers.add(trigger_key)
                        timing_text = timing_span.text if timing_span else atom.action_timing
                        occurrences.append(
                            _occurrence(
                                kind="trigger",
                                witness=witness,
                                span=timing_span or atom_span,
                                text=timing_text,
                                effect_text=timing_text,
                                ordinal=ordinal_by_kind["trigger"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                condition="",
                                action_timing=atom.action_timing,
                                semantic_type="action_timing",
                                timing_source_span=timing_span,
                            )
                        )
                        ordinal_by_kind["trigger"] += 1

                state_text = atom.condition or effect_text or atom.text
                state_reference = _state_reference(state_text)
                if state_reference:
                    state_key = (atom_span.location, state_reference, atom.character_start, atom.character_end)
                    if state_key not in seen_states:
                        seen_states.add(state_key)
                        occurrences.append(
                            _occurrence(
                                kind="state",
                                witness=witness,
                                span=condition_span or atom_span,
                                text=state_reference,
                                effect_text=state_reference,
                                ordinal=ordinal_by_kind["state"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                condition=atom.condition,
                                action_timing="",
                                semantic_type="state_reference",
                            )
                        )
                        ordinal_by_kind["state"] += 1

            for token, token_start, token_end in token_positions:
                if token.kind != "reference":
                    continue
                token_span = SourceSpan(
                    location=token.location,
                    block_kind=block.kind,
                    ancestry=tuple(block.ancestry),
                    token_start=token.order,
                    token_end=token.order,
                    text=token.text,
                    character_start=token_start,
                    character_end=token_end,
                )
                occurrences.append(
                    _occurrence(
                        kind="reference",
                        witness=witness,
                        span=token_span,
                        text=token.text,
                        ordinal=ordinal_by_kind["reference"],
                        semantic_state=semantic_state,
                        authority=authority,
                        definition_support=_definition_support([token], resolution_by_location, admit_definitions=admit_definitions),
                        references=[token],
                        semantic_type="source_reference",
                    )
                )
                ordinal_by_kind["reference"] += 1

    unit_by_id = {candidate.unit_id: candidate for candidate in all_units}
    unit_by_id[unit.unit_id] = unit
    relationships = _classify_relationships(
        witness=witness,
        root=unit,
        resolutions=resolutions,
        unit_by_id=unit_by_id,
        contexts=unit_contexts,
        occurrences=occurrences,
        semantic_state=semantic_state,
        authority=authority,
        mechanic_registry=mechanic_registry,
    )
    return ClassifiedUnit(tuple(occurrences), tuple(relationships))


def _catalog_facts(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [*record.get("skills", []), *record.get("passive_skills", [])]


def _load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_structural_corpus(
    catalog: Mapping[str, Any],
    *,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
) -> tuple[dict[str, StructuralUnit], list[StructuralUnit], dict[str, int], Any]:
    all_units: list[StructuralUnit] = []
    bound_units: list[StructuralUnit] = []
    by_location: dict[str, StructuralUnit] = {}
    for record in sorted(catalog.get("characters", []), key=lambda row: str(row["receipt"]["character_id"])):
        name = str(record["receipt"]["character_name"])
        path = raw_character_dir / f"{_slugify(name)}.html"
        if not path.exists():
            continue
        raw = path.read_bytes()
        source = SourceIdentity(
            source_kind="character",
            source_url=str(record.get("character", {}).get("detail_url") or record["receipt"].get("source_url") or ""),
            capture_sha256=_sha256(raw),
            capture_path=path.as_posix(),
        )
        units, _ = parse_grid_document(raw.decode("utf-8"), source=source, entity_kind="character", entity_name=name)
        bound, _ = bind_catalog_facts(units, _catalog_facts(record))
        all_units.extend(units)
        bound_units.extend(bound)
        for unit in units:
            if unit.blocks:
                by_location[unit.blocks[0].location] = unit
    for path in sorted(parsed_sidekick_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows") or []
        if not rows:
            continue
        row = rows[0]
        source_path = raw_sidekick_dir / f"{path.stem}.html"
        if not source_path.exists():
            continue
        raw = source_path.read_bytes()
        source = SourceIdentity(
            source_kind="sidekick",
            source_url=str(row.get("source_url") or ""),
            capture_sha256=_sha256(raw),
            capture_path=source_path.as_posix(),
        )
        units, _ = parse_grid_document(
            raw.decode("utf-8"),
            source=source,
            entity_kind="sidekick",
            entity_name=str(row.get("name") or path.stem),
        )
        all_units.extend(units)
        for unit in units:
            if unit.blocks:
                by_location[unit.blocks[0].location] = unit
    topology = audit_reference_topology(all_units)
    limits = select_traversal_limits(topology)
    return by_location, all_units, topology, limits


def _witness_fact_record(witness: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    record_type = str(witness.get("record_type") or "")
    if str(witness.get("source_kind")) == "character":
        for record in catalog.get("characters", []):
            if str(record["receipt"].get("character_name")) != str(witness.get("entity_name")):
                continue
            for fact in _catalog_facts(record):
                if _fact_id(fact) == str(witness.get("fact_id")):
                    return dict(fact)
    source_key = _fact_key(record_type)
    result = {
        source_key: str(witness.get("fact_id") or ""),
        "name": str(witness.get("fact_name") or witness.get("title") or ""),
        "description": str(witness.get("legacy_description") or ""),
        "character_name": str(witness.get("entity_name") or ""),
        "sidekick_name": str(witness.get("entity_name") or ""),
        "source_url": str(witness.get("source_url") or ""),
        "section": str(witness.get("section") or ""),
        "skill_kind": str(witness.get("record_type") or ""),
    }
    return result


def _review_state(proposal: Mapping[str, Any], reviews: Mapping[str, Any]) -> tuple[str, str]:
    proposal_id = str(proposal["proposal_id"])
    decisions = {str(row.get("proposal_id")): row for row in reviews.get("decisions", [])}
    legacy = {
        (str(row.get("record_type")), str(row.get("source_fact_id")), str(row.get("rule_id"))): row
        for row in reviews.get("decisions", [])
    }
    decision = decisions.get(proposal_id) or legacy.get(
        (str(proposal.get("record_type")), str(proposal.get("source_fact_id")), str(proposal.get("rule_id")))
    )
    if decision is None:
        return "candidate", "automatic_candidate"
    value = str(decision.get("decision") or "")
    return {
        "approve": "proven",
        "correct": "proven",
        "reject": "rejected",
    }.get(value, value or "candidate"), "reviewed_proven" if value in {"approve", "correct"} else "non_authoritative"


def _legacy_occurrences(witness: Mapping[str, Any], record: Mapping[str, Any], reviews: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    ordinal: Counter[str] = Counter()
    for proposal in propose(dict(record)):
        kind = "effect" if proposal["proposed_kind"] == "capability" else "dependency"
        review_state, authority = _review_state(proposal, reviews)
        occurrence = _occurrence(
            kind=kind,
            witness=witness,
            span=None,
            text=str(proposal.get("matched_phrase") or proposal.get("source_text") or ""),
            ordinal=ordinal[kind],
            semantic_state=review_state,
            authority=authority,
            definition_support="not_applicable",
            capability_value=str(proposal.get("proposed_value") or "") if kind == "effect" else "",
            dependency_value=str(proposal.get("proposed_value") or "") if kind == "dependency" else "",
            legacy_proposal_id=str(proposal["proposal_id"]),
        )
        result.append(occurrence.as_dict())
        ordinal[kind] += 1
    return result


def _arm_summary(
    occurrences: Iterable[Mapping[str, Any]],
    relationships: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    rows = list(occurrences)
    relation_rows = list(relationships)
    counts = Counter(str(row.get("occurrence_kind")) for row in rows)
    authority = Counter(str(row.get("authority")) for row in rows)
    return {
        "occurrence_count": len(rows),
        "fully_supported_occurrence_count": sum(row.get("semantic_state") == "fully_supported_input" for row in rows),
        "capability_gap_occurrence_count": sum(row.get("occurrence_kind") == "effect" and row.get("capability_gap") is True for row in rows),
        "effect_occurrence_count": counts.get("effect", 0),
        "dependency_occurrence_count": counts.get("dependency", 0),
        "occurrence_kind_counts": dict(sorted(counts.items())),
        "authority_counts": dict(sorted(authority.items())),
        "relationship_count": len(relation_rows),
        "occurrences": rows,
        "relationships": relation_rows,
    }


_COMPATIBILITY_FIELDS = (
    "occurrence_kind",
    "source_fact_id",
    "source_text",
    "actor",
    "direction",
    "recipient",
    "recipient_name",
    "target_cardinality",
    "condition",
    "trigger",
    "result",
    "magnitude",
    "probability",
    "duration_activation",
    "element",
    "attack_type",
    "state_reference",
    "capability_value",
    "dependency_value",
    "semantic_type",
    "semantic_subject",
    "capability_gap",
    "hit_count",
    "formula_metadata",
    "action_timing",
)


def _compatibility_mapping(
    legacy: Sequence[Mapping[str, Any]],
    current: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Make every old proposal's carry-forward decision explicit.

    A legacy proposal is never copied by position or by capability value.  It
    can carry forward only when every source/semantic field available in both
    arms is identical and exactly one destination exists.  A one-to-many
    candidate set is retained as an explicit split requiring review.
    """
    mappings: list[dict[str, Any]] = []
    destination_counts: Counter[str] = Counter()
    for old in legacy:
        candidates = [
            new
            for new in current
            if all(old.get(field) == new.get(field) for field in _COMPATIBILITY_FIELDS)
        ]
        if len(candidates) == 1:
            status = "carried_forward"
            destination_counts[str(candidates[0]["occurrence_id"])] += 1
        elif len(candidates) > 1:
            status = "split_requires_review"
        else:
            status = "review_required"
        mappings.append(
            {
                "legacy_proposal_id": old.get("legacy_proposal_id"),
                "source_fact_id": old.get("source_fact_id"),
                "legacy_occurrence_kind": old.get("occurrence_kind"),
                "candidate_occurrence_ids": [str(row["occurrence_id"]) for row in candidates],
                "status": status,
                "review_state_preserved": old.get("semantic_state"),
                "authority_preserved": old.get("authority"),
            }
        )
    return {
        "mappings": mappings,
        "carried_forward_count": sum(row["status"] == "carried_forward" for row in mappings),
        "split_requires_review_count": sum(row["status"] == "split_requires_review" for row in mappings),
        "review_required_count": sum(row["status"] == "review_required" for row in mappings),
        "destination_fanout": {
            destination: count for destination, count in sorted(destination_counts.items()) if count > 1
        },
        "silent_fanout": False,
        "review_authority_unchanged": True,
    }


def _fidelity_rows(report: Mapping[str, Any], cohort: str) -> dict[str, Mapping[str, Any]]:
    evaluation = report.get("oracle_evaluation", {})
    return {str(row["witness_id"]): row for row in evaluation.get(cohort, {}).get("witnesses", [])}


def _build_comparison(
    *,
    c1_report: Mapping[str, Any],
    catalog: Mapping[str, Any],
    by_location: Mapping[str, StructuralUnit],
    all_units: Sequence[StructuralUnit],
    limits: Any,
    cohort: str,
    reviews: Mapping[str, Any],
) -> dict[str, Any]:
    fidelity_rows = _fidelity_rows(c1_report, cohort)
    witness_rows = list(c1_report["witness_replay"].get(cohort, []))
    rows: list[dict[str, Any]] = []
    arms: dict[str, list[dict[str, Any]]] = {"legacy_flattened": [], "structural_only": [], "fidelity_checked": []}
    relationships: dict[str, list[dict[str, Any]]] = {"legacy_flattened": [], "structural_only": [], "fidelity_checked": []}
    compatibility: list[dict[str, Any]] = []
    archetypes: Counter[str] = Counter()
    for witness in witness_rows:
        witness_id = str(witness["witness_id"])
        unit = by_location.get(str(witness.get("source_location") or ""))
        record = _witness_fact_record(witness, catalog)
        legacy = _legacy_occurrences(witness, record, reviews)
        structural_result = _classify_unit(
            witness,
            unit,
            all_units,
            limits,
            arm="structural_only",
            fidelity_passed=False,
        )
        fidelity_result = _classify_unit(
            witness,
            unit,
            all_units,
            limits,
            arm="fidelity_checked",
            fidelity_passed=bool(fidelity_rows.get(witness_id, {}).get("semantic_fidelity_passed")),
        )
        structural = [row.as_dict() for row in structural_result.occurrences]
        fidelity = [row.as_dict() for row in fidelity_result.occurrences]
        structural_relationships = [row.as_dict() for row in structural_result.relationships]
        fidelity_relationships = [row.as_dict() for row in fidelity_result.relationships]
        arms["legacy_flattened"].extend(legacy)
        arms["structural_only"].extend(structural)
        arms["fidelity_checked"].extend(fidelity)
        relationships["structural_only"].extend(structural_relationships)
        relationships["fidelity_checked"].extend(fidelity_relationships)
        compatibility.append(
            {
                "witness_id": witness_id,
                "mapping": _compatibility_mapping(legacy, fidelity),
            }
        )
        for archetype in witness.get("archetypes", []):
            archetypes[str(archetype)] += 1
        rows.append(
            {
                "witness_id": witness_id,
                "entity_name": witness.get("entity_name"),
                "fact_id": witness.get("fact_id"),
                "record_type": witness.get("record_type"),
                "archetypes": list(witness.get("archetypes", [])),
                "source_identity_status": witness.get("source_identity_status"),
                "source_record_selection_status": witness.get("source_record_selection_status"),
                "source_fixture_status": witness.get("source_fixture_status"),
                "c1_fidelity_status": (
                    "passed" if fidelity_rows.get(witness_id, {}).get("semantic_fidelity_passed") else "not_evaluated_or_not_passed"
                ),
                "c1_fidelity_dimensions": fidelity_rows.get(witness_id, {}).get("dimensions", {}),
                "definition_resolution": {
                    "reference_count": sum(1 for row in fidelity if row["occurrence_kind"] == "reference"),
                    "admitted_count": sum(1 for row in fidelity if row.get("definition_support") == "admitted"),
                    "unresolved_count": sum(1 for row in fidelity if row.get("definition_support") == "unresolved"),
                },
                "shared_mechanic_resolutions": [
                    item.as_dict()
                    for item in resolve_shared_mechanics(
                        unit,
                        parent_source_fact_id=str(witness.get("record_id") or ""),
                    )
                ] if unit is not None else [],
                "arms": {
                    "legacy_flattened": _arm_summary(legacy),
                    "structural_only": _arm_summary(structural, structural_relationships),
                    "fidelity_checked": _arm_summary(fidelity, fidelity_relationships),
                },
            }
        )
    return {
        "witness_count": len(witness_rows),
        "archetype_coverage": dict(sorted(archetypes.items())),
        "arms": {
            name: _arm_summary(values, relationships[name])
            for name, values in arms.items()
        },
        "compatibility": compatibility,
        "witnesses": rows,
    }


def _comparison_digest(comparison: Mapping[str, Any]) -> str:
    return _sha256(_canonical(comparison).encode("utf-8"))


def build_c2_report(
    *,
    catalog_path: Path = CATALOG_PATH,
    fidelity_oracle: Mapping[str, Any] | None = None,
    manifest_path: Path = MANIFEST_PATH,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
) -> dict[str, Any]:
    """Build development-only C2 comparison evidence.

    Protected validation rows and the owner-held semantic oracle are not read
    by routine reports.  The explicit owner evaluation has a separate entry
    point that returns aggregate results only.
    """
    c1_report = build_source_fidelity_report(
        catalog_path=catalog_path,
        manifest_path=manifest_path,
        raw_character_dir=raw_character_dir,
        raw_sidekick_dir=raw_sidekick_dir,
        parsed_sidekick_dir=parsed_sidekick_dir,
        oracle=fidelity_oracle,
    )
    catalog = _load_catalog(catalog_path)
    by_location, all_units, topology, limits = _load_structural_corpus(
        catalog,
        raw_character_dir=raw_character_dir,
        raw_sidekick_dir=raw_sidekick_dir,
        parsed_sidekick_dir=parsed_sidekick_dir,
    )
    reviews = load_reviews()
    comparisons: dict[str, Any] = {}
    for cohort in ("known_regressions", "development"):
        comparisons[cohort] = _build_comparison(
            c1_report=c1_report,
            catalog=catalog,
            by_location=by_location,
            all_units=all_units,
            limits=limits,
            cohort=cohort,
            reviews=reviews,
        )
    digest_payload = {
        "artifact_version": C2_ARTIFACT_VERSION,
        "catalog_fingerprint": artifact_fingerprint(catalog),
        "source_fidelity_digest": c1_report["deterministic_replay"]["replay_digest"],
        "comparisons": comparisons,
    }
    report: dict[str, Any] = {
        "artifact_version": C2_ARTIFACT_VERSION,
        "authority": {
            "source_fidelity_artifact": "C1.1 accepted source-fidelity report and manifests",
            "legacy_baseline": "committed Feature C extraction report only; historical context, not an oracle",
            "occurrence_oracle": "separate explicit evaluation input; never read by normal classification",
            "catalog_fingerprint": artifact_fingerprint(catalog),
            "automatic_approval": False,
            "capability_materialization": False,
            "graph_schema_mutated": False,
            "legal_kit_mutated": False,
            "source_refresh": False,
        },
        "comparison_contract": {
            "same_checksum_pinned_inputs": True,
            "arms": [
                "legacy_flattened",
                "structural_only",
                "fidelity_checked",
            ],
            "occurrence_kinds": list(OCCURRENCE_KINDS),
            "primary_occurrence_kinds": list(PRIMARY_OCCURRENCE_KINDS),
            "atomic_fields_are_effect_local": [
                "condition",
                "action_timing",
                "recipient",
                "recipient_name",
                "magnitude",
                "probability",
                "hit_count",
                "duration_activation",
            ],
            "unmapped_semantics_are_capability_gaps": True,
            "relationship_contract": {
                "target_kinds": ["source_fact", "shared_mechanic", "unresolved"],
                "local_condition_and_timing": True,
                "unresolved_targets_remain_unresolved": True,
                "definition_semantics_are_not_copied": True,
                "authority": "non_authoritative",
            },
            "one_direct_damage_event_rule": "one source damage event owns one direct_damage effect occurrence; multi_entity_damage is a derived projection when target cardinality is multiple",
            "definition_rule": "definitions may support only the scoped occurrence relationship invoked by the source; unresolved or unrelated definitions remain unknown",
        },
        "shared_mechanic_contract": {
            "registry_version": REGISTRY_VERSION,
            "resolution_is_non_authoritative": True,
            "local_payload_owner": "parent source fact",
            "unavailable_definition_never_becomes_semantics": True,
            "registry_deduplicates_by_mechanic_id": True,
            "graph_labels_added": False,
        },
        "manifest": c1_report["manifest"],
        "witness_replay": c1_report["witness_replay"]["source_slice_fixture"],
        "comparisons": comparisons,
        "full_catalog_diagnostics": {
            "legal_kit": c1_report["legal_kit"],
            "full_catalog_replay": c1_report["full_catalog_replay"],
            "sidekick_replay": c1_report["sidekick_replay"],
            "topology_audit": c1_report["topology_audit"],
            "traversal_limits": c1_report["traversal_limits"],
            "replayed_unit_count": len(all_units),
            "replayed_topology": topology,
            "selected_limits": asdict(limits),
        },
        "fidelity_dimensions": {
            "dimensions": list(FIDELITY_DIMENSIONS),
            "source_fidelity_evaluation_present": "oracle_evaluation" in c1_report,
            "unresolved_state": "unknown_non_authoritative",
            "failed_state": "failed_non_authoritative",
            "inapplicable_state": "not_applicable",
            "fully_supported_rule": "source identity and selection pass, every applicable C1.1 dimension passes, and occurrence source fields remain attributable",
        },
        "authority_boundary": {
            "fidelity_passed_only_enters_fully_supported_arm": True,
            "automatic_approval": False,
            "reviewed_proven_facts_unchanged": True,
            "unknown_non_authoritative": True,
            "no_schema_migration": True,
        },
        "known_regression_policy": {
            "reported_separately": True,
            "excluded_from_generalization": True,
            "count": len(c1_report["witness_replay"].get("known_regressions", [])),
        },
        "deterministic_replay": {
            "source_fidelity_digest": c1_report["deterministic_replay"]["replay_digest"],
            "comparison_digest": _comparison_digest(comparisons),
            "same_input_same_digest": True,
            "generated_output": "caller-selected evidence path; scratch output remains ignored",
        },
    }
    return report


def _oracle_rows(oracle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = oracle.get("witnesses", {})
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    return {str(row["witness_id"]): row for row in raw}


def _primary_occurrences(arm: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [row for row in arm.get("occurrences", []) if row.get("occurrence_kind") in PRIMARY_OCCURRENCE_KINDS]


def _expected_occurrence_ids(expected: Mapping[str, Any], witness: Mapping[str, Any]) -> list[str]:
    explicit = [str(value) for value in expected.get("expected_occurrence_ids", [])]
    if explicit:
        return explicit
    fact_id = str(witness.get("fact_id") or "")
    result: list[str] = []
    for kind, key in (
        ("effect", "expected_effect_occurrence_count"),
        ("dependency", "expected_dependency_occurrence_count"),
    ):
        result.extend(
            _stable_occurrence_id(fact_id, kind, None, index)
            for index in range(int(expected.get(key, 0)))
        )
    return result


def _metric_counts(predicted: Sequence[Mapping[str, Any]], expected_ids: Sequence[str]) -> dict[str, Any]:
    predicted_ids = {str(row.get("occurrence_id")) for row in predicted}
    expected = {str(value) for value in expected_ids}
    true_positive = len(predicted_ids & expected)
    false_positive = len(predicted_ids - expected)
    false_negative = len(expected - predicted_ids)
    return {
        "predicted_count": len(predicted_ids),
        "expected_count": len(expected),
        "true_positive_count": true_positive,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "precision": true_positive / len(predicted_ids) if predicted_ids else 0.0,
        "recall": true_positive / len(expected) if expected else 1.0 if not predicted_ids else 0.0,
    }


def _evaluate_arm(
    comparison: Mapping[str, Any],
    oracle_rows: Mapping[str, Mapping[str, Any]],
    arm_name: str,
) -> dict[str, Any]:
    """Evaluate one comparison arm against the same independently authored rows."""
    arm = comparison.get("arms", {}).get(arm_name, {})
    aggregate = Counter()
    witness_results: list[dict[str, Any]] = []
    predicted_effect_count = predicted_dependency_count = 0
    for witness in comparison.get("witnesses", []):
        witness_id = str(witness["witness_id"])
        expected = oracle_rows.get(witness_id, {})
        expected_ids = _expected_occurrence_ids(expected, witness)
        predicted = [
            item
            for item in arm.get("occurrences", [])
            if str(item.get("source_fact_id")) == str(witness.get("fact_id"))
            and (
                arm_name != "fidelity_checked"
                or item.get("semantic_state") == "fully_supported_input"
            )
        ]
        primary_predicted = _primary_occurrences({"occurrences": predicted})
        metrics = _metric_counts(primary_predicted, expected_ids)
        aggregate.update(metrics)
        predicted_effect_count += sum(row.get("occurrence_kind") == "effect" for row in primary_predicted)
        predicted_dependency_count += sum(row.get("occurrence_kind") == "dependency" for row in primary_predicted)
        witness_results.append(
            {
                "witness_id": witness_id,
                "expected_occurrence_ids": expected_ids,
                "occurrence_metrics": metrics,
            }
        )
    predicted_count = aggregate["predicted_count"]
    expected_count = aggregate["expected_count"]
    true_positive = aggregate["true_positive_count"]
    return {
        "authority": (
            "reviewed_and_legacy_compatible" if arm_name == "legacy_flattened" else "non_authoritative_comparison"
        ),
        "fully_supported_filter": arm_name == "fidelity_checked",
        "predicted_effect_occurrence_count": predicted_effect_count,
        "predicted_dependency_occurrence_count": predicted_dependency_count,
        "occurrence_precision_recall": {
            "predicted_count": predicted_count,
            "expected_count": expected_count,
            "true_positive_count": true_positive,
            "false_positive_count": aggregate["false_positive_count"],
            "false_negative_count": aggregate["false_negative_count"],
            "precision": true_positive / predicted_count if predicted_count else 0.0,
            "recall": true_positive / expected_count if expected_count else 1.0 if not predicted_count else 0.0,
        },
        "witnesses": witness_results,
    }


def evaluate_c2_oracle(
    report: Mapping[str, Any],
    oracle: Mapping[str, Any],
    *,
    include_held_out: bool = False,
) -> dict[str, Any]:
    """Return the historical ordinal metric for development cohorts only."""
    if include_held_out:
        raise ValueError("the historical ordinal evaluator is disabled for protected validation")
    rows = _oracle_rows(oracle)
    allowed_ids = {
        str(witness["witness_id"])
        for cohort in ("known_regressions", "development")
        for witness in report.get("comparisons", {}).get(cohort, {}).get("witnesses", [])
    }
    if set(rows) - allowed_ids:
        raise ValueError("historical ordinal oracle contains identities outside known/development cohorts")
    cohorts = ["known_regressions", "development"]
    cohort_results: dict[str, Any] = {}
    for cohort in cohorts:
        comparison = report["comparisons"].get(cohort, {})
        fidelity_arm = comparison.get("arms", {}).get("fidelity_checked", {})
        arm_evaluations = {
            arm_name: _evaluate_arm(comparison, rows, arm_name)
            for arm_name in ("legacy_flattened", "structural_only", "fidelity_checked")
        }
        witness_results: list[dict[str, Any]] = []
        aggregate = Counter()
        field_errors = condition_errors = relationship_errors = correction_actions = 0
        prior_review_regressions: list[str] = []
        measured_seconds = 0.0
        measured_occurrences = 0
        review_time_statuses: Counter[str] = Counter()
        for witness in comparison.get("witnesses", []):
            witness_id = str(witness["witness_id"])
            expected = rows.get(witness_id, {})
            expected_ids = _expected_occurrence_ids(expected, witness)
            predicted = [
                item
                for item in fidelity_arm.get("occurrences", [])
                if str(item.get("source_fact_id")) == str(witness.get("fact_id"))
                and item.get("semantic_state") == "fully_supported_input"
            ]
            primary_predicted = _primary_occurrences({"occurrences": predicted})
            metrics = _metric_counts(primary_predicted, expected_ids)
            aggregate.update(
                {
                    "predicted_count": metrics["predicted_count"],
                    "expected_count": metrics["expected_count"],
                    "true_positive_count": metrics["true_positive_count"],
                    "false_positive_count": metrics["false_positive_count"],
                    "false_negative_count": metrics["false_negative_count"],
                }
            )
            field_errors += len(expected.get("field_errors", []))
            condition_errors += len(expected.get("condition_errors", []))
            relationship_errors += len(expected.get("relationship_errors", []))
            correction_actions += len(expected.get("correction_actions", []))
            prior_review_regressions.extend(str(value) for value in expected.get("prior_review_regressions", []))
            seconds = expected.get("blinded_review_seconds")
            if isinstance(seconds, (int, float)):
                measured_seconds += float(seconds)
                measured_occurrences += len(expected_ids)
                review_time_statuses["measured"] += 1
            else:
                review_time_statuses[str(expected.get("review_time_status", "not_measured"))] += 1
            witness_results.append(
                {
                    "witness_id": witness_id,
                    "expected_occurrence_ids": expected_ids,
                    "occurrence_metrics": metrics,
                    "field_errors": expected.get("field_errors", []),
                    "condition_errors": expected.get("condition_errors", []),
                    "relationship_errors": expected.get("relationship_errors", []),
                    "correction_actions": expected.get("correction_actions", []),
                    "prior_review_regressions": expected.get("prior_review_regressions", []),
                    "review_time_status": expected.get("review_time_status", "not_measured"),
                    "blinded_review_seconds": seconds,
                    "d_floor_effort": expected.get("d_floor_effort", "not_measured"),
                }
            )
        predicted_count = aggregate["predicted_count"]
        expected_count = aggregate["expected_count"]
        tp = aggregate["true_positive_count"]
        fp = aggregate["false_positive_count"]
        fn = aggregate["false_negative_count"]
        cohort_results[cohort] = {
            "witness_count": comparison.get("witness_count", 0),
            "generalization_evidence": cohort != "known_regressions",
            "oracle_missing_witness_ids": sorted(
                str(witness["witness_id"])
                for witness in comparison.get("witnesses", [])
                if str(witness["witness_id"]) not in rows
            ),
            "independently_adjudicated_effect_occurrence_count": sum(
                int(rows.get(str(witness["witness_id"]), {}).get("expected_effect_occurrence_count", 0))
                if not rows.get(str(witness["witness_id"]), {}).get("expected_effect_occurrence_ids")
                else len(rows.get(str(witness["witness_id"]), {}).get("expected_effect_occurrence_ids", []))
                for witness in comparison.get("witnesses", [])
            ),
            "independently_adjudicated_dependency_occurrence_count": sum(
                int(rows.get(str(witness["witness_id"]), {}).get("expected_dependency_occurrence_count", 0))
                if not rows.get(str(witness["witness_id"]), {}).get("expected_dependency_occurrence_ids")
                else len(rows.get(str(witness["witness_id"]), {}).get("expected_dependency_occurrence_ids", []))
                for witness in comparison.get("witnesses", [])
            ),
            "occurrence_precision_recall": {
                "predicted_count": predicted_count,
                "expected_count": expected_count,
                "true_positive_count": tp,
                "false_positive_count": fp,
                "false_negative_count": fn,
                "precision": tp / predicted_count if predicted_count else 0.0,
                "recall": tp / expected_count if expected_count else 1.0 if not predicted_count else 0.0,
            },
            "arm_evaluations": arm_evaluations,
            "field_error_count": field_errors,
            "condition_error_count": condition_errors,
            "relationship_attachment_error_count": relationship_errors,
            "correction_action_count": correction_actions,
            "prior_review_regressions": sorted(set(prior_review_regressions)),
            "review_time": {
                "status_counts": dict(sorted(review_time_statuses.items())),
                "measured_total_seconds": measured_seconds if measured_occurrences else None,
                "measured_accepted_occurrence_count": measured_occurrences,
                "seconds_per_accepted_occurrence": measured_seconds / measured_occurrences if measured_occurrences else None,
            },
            "d_floor_effort": {
                "status": "reported_by_oracle",
                "values": {
                    witness_id: rows.get(witness_id, {}).get("d_floor_effort", "not_measured")
                    for witness_id in sorted(rows)
                    if witness_id in {str(item["witness_id"]) for item in comparison.get("witnesses", [])}
                },
            },
            "witnesses": witness_results,
        }
    return {
        "oracle_version": oracle.get("oracle_version", C2_ORACLE_VERSION),
        "sealed": bool(oracle.get("sealed")),
        "known_regressions_excluded_from_generalization": True,
        "cohorts": cohort_results,
        "benefit": {
            "held_out_evaluated": "held_out" in cohort_results,
            "review_effort_is_authoritative_only_when_measured": True,
            "known_regression_rows_not_counted": True,
            "occurrence_metrics_available": "held_out" in cohort_results,
            "review_reduction_claim": False,
            "status": "measured" if cohort_results.get("held_out", {}).get("review_time", {}).get("measured_accepted_occurrence_count") else "not_measured",
        },
    }


def write_c2_report(destination: Path, **kwargs: Any) -> dict[str, Any]:
    report = build_c2_report(**kwargs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _main() -> None:
    parser = argparse.ArgumentParser(description="Build or evaluate Milestone 6 C2 scoped-classification evidence")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_c2_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"C2 artifact: {report['artifact_version']}")
    for cohort, comparison in report["comparisons"].items():
        arm = comparison["arms"]["fidelity_checked"]
        print(f"{cohort}: witnesses={comparison['witness_count']} effects={arm['effect_occurrence_count']} dependencies={arm['dependency_occurrence_count']}")
    print(f"comparison digest: {report['deterministic_replay']['comparison_digest']}")


if __name__ == "__main__":
    _main()
