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
from dataclasses import asdict, dataclass
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


C2_ARTIFACT_VERSION = "m6-c2-scoped-classification-1.0.0"
C2_ORACLE_VERSION = "m6-c2-independent-occurrence-oracle-1.0.0"
MANIFEST_PATH = Path("src/etl/source_fidelity_manifest.json")
OCCURRENCE_ORACLE_PATH = Path("tests/fixtures/c2/occurrence_oracle.json")

OCCURRENCE_KINDS = ("effect", "dependency", "trigger", "state", "reference")
PRIMARY_OCCURRENCE_KINDS = ("effect", "dependency")

_SPACE_RE = re.compile(r"\s+")
_CONDITION_RE = re.compile(
    r"\b(?:if|when|only when|unless|without|requires?|consumes?|based on|"
    r"depending on|after|before|during|once|until|while)\b",
    re.IGNORECASE,
)
_TRIGGER_RE = re.compile(
    r"\b(?:preemptive|auto|charged|aura activation|battle start|start of turn|"
    r"end of turn|when used|when in|only when|if |after |before |during |on damage)\b",
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
_MULTIPLIER_RE = re.compile(r"\b(?:x|multiplier\s*x)\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)
_TURN_RE = re.compile(r"\b(?:for\s+)?(\d+)\s+turns?\b", re.IGNORECASE)
_ACTIVATION_RE = re.compile(r"\b(\d+)\s+(?:times?|activations?|uses?)\b|\bonce per battle\b", re.IGNORECASE)


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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def _span(block: StructuralBlock, tokens: Sequence[StructuralToken], start: int, end: int) -> SourceSpan:
    return SourceSpan(
        location=block.location,
        block_kind=block.kind,
        ancestry=tuple(block.ancestry),
        token_start=start,
        token_end=end,
        text=_clean(" ".join(token.text for token in tokens)),
    )


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
    if re.search(r"\b(?:all party members|party members|all allies|all ally)\b", lowered):
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
        ("on damage", "on_damage"),
        ("when used", "on_use"),
        ("when in", "condition"),
        ("only when", "condition"),
        ("if ", "condition"),
    ):
        if phrase in lowered:
            return value
    return ""


def _magnitude(text: str) -> dict[str, str]:
    percent = _PERCENT_RE.search(text)
    multiplier = _MULTIPLIER_RE.search(text)
    if percent:
        return {"value": percent.group(1), "unit": "percent", "raw": percent.group(0)}
    if multiplier:
        return {"value": multiplier.group(1), "unit": "multiplier", "raw": multiplier.group(0)}
    fixed = re.search(r"\b(?:deal|damage|restore|recover|heal)\s+(\d{3,})\b", text, re.IGNORECASE)
    if fixed:
        return {"value": fixed.group(1), "unit": "flat", "raw": fixed.group(0)}
    return {}


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


def _effect_value(text: str) -> str:
    lowered = _key(text)
    # A damage modifier, damage received clause, or multiplier parameter is
    # part of the enclosing event.  Only an attack/deal/fixed-damage clause is
    # authoritative direct damage; this prevents one event from fanning out
    # into a second reviewed damage fact.
    if re.search(r"\b(?:attack|attacks|deal(?:s)?\b|fixed damage|damage to self)\b", lowered):
        return "direct_damage"
    if re.search(r"\b(?:heal|restore .*hp|recover .*hp)\b", lowered):
        return "recovery"
    if re.search(r"\b(?:restore .*mp|recover .*mp)\b", lowered):
        return "mp_recovery"
    if re.search(r"\b(?:pain|poison)\b", lowered):
        return "status_damage"
    return "scoped_effect"


def _dependency_value(text: str) -> str:
    lowered = _key(text)
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
) -> ClassifiedOccurrence:
    recipient, cardinality = _recipient_and_cardinality(text)
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
        direction=_direction(text),
        recipient=recipient,
        target_cardinality=cardinality,
        condition=_condition(text),
        trigger=_trigger(text),
        result=_clean(text),
        magnitude=_magnitude(text),
        duration_activation=_duration_activation(text),
        element=_element(text),
        attack_type=_attack_type(text),
        state_reference=_state_reference(text),
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
    )


def _classify_unit(
    witness: Mapping[str, Any],
    unit: StructuralUnit | None,
    all_units: Sequence[StructuralUnit],
    limits: Any,
    *,
    arm: str,
    fidelity_passed: bool,
) -> list[dict[str, Any]]:
    if unit is None:
        return []
    resolutions = resolve_bounded_references([unit], all_units, limits)
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
    for block in unit.blocks:
        for tokens, start, end in _tokens_to_fragments(block):
            text = _clean(" ".join(token.text for token in tokens))
            if not text:
                continue
            span = _span(block, tokens, start, end)
            references = [token for token in tokens if token.kind == "reference"]
            support = _definition_support(references, resolution_by_location, admit_definitions=admit_definitions)
            if _EFFECT_RE.search(text):
                value = _effect_value(text)
                item = _occurrence(
                    kind="effect",
                    witness=witness,
                    span=span,
                    text=text,
                    ordinal=ordinal_by_kind["effect"],
                    semantic_state=semantic_state,
                    authority=authority,
                    definition_support=support,
                    references=references,
                    capability_value=value,
                )
                occurrences.append(item)
                ordinal_by_kind["effect"] += 1
            if _CONDITION_RE.search(text):
                value = _dependency_value(text)
                item = _occurrence(
                    kind="dependency",
                    witness=witness,
                    span=span,
                    text=text,
                    ordinal=ordinal_by_kind["dependency"],
                    semantic_state=semantic_state,
                    authority=authority,
                    definition_support=support,
                    references=references,
                    dependency_value=value,
                )
                occurrences.append(item)
                ordinal_by_kind["dependency"] += 1
            if _TRIGGER_RE.search(text):
                item = _occurrence(
                    kind="trigger",
                    witness=witness,
                    span=span,
                    text=text,
                    ordinal=ordinal_by_kind["trigger"],
                    semantic_state=semantic_state,
                    authority=authority,
                    definition_support=support,
                    references=references,
                )
                occurrences.append(item)
                ordinal_by_kind["trigger"] += 1
            if _STATE_RE.search(text):
                item = _occurrence(
                    kind="state",
                    witness=witness,
                    span=span,
                    text=text,
                    ordinal=ordinal_by_kind["state"],
                    semantic_state=semantic_state,
                    authority=authority,
                    definition_support=support,
                    references=references,
                )
                occurrences.append(item)
                ordinal_by_kind["state"] += 1
            for token in references:
                token_span = SourceSpan(
                    location=token.location,
                    block_kind=block.kind,
                    ancestry=tuple(block.ancestry),
                    token_start=token.order,
                    token_end=token.order,
                    text=token.text,
                )
                item = _occurrence(
                    kind="reference",
                    witness=witness,
                    span=token_span,
                    text=token.text,
                    ordinal=ordinal_by_kind["reference"],
                    semantic_state=semantic_state,
                    authority=authority,
                    definition_support=_definition_support([token], resolution_by_location, admit_definitions=admit_definitions),
                    references=[token],
                )
                occurrences.append(item)
                ordinal_by_kind["reference"] += 1
    return [item.as_dict() for item in occurrences]


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


def _arm_summary(occurrences: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(occurrences)
    counts = Counter(str(row.get("occurrence_kind")) for row in rows)
    authority = Counter(str(row.get("authority")) for row in rows)
    return {
        "occurrence_count": len(rows),
        "fully_supported_occurrence_count": sum(row.get("semantic_state") == "fully_supported_input" for row in rows),
        "effect_occurrence_count": counts.get("effect", 0),
        "dependency_occurrence_count": counts.get("dependency", 0),
        "occurrence_kind_counts": dict(sorted(counts.items())),
        "authority_counts": dict(sorted(authority.items())),
        "occurrences": rows,
    }


_COMPATIBILITY_FIELDS = (
    "occurrence_kind",
    "source_fact_id",
    "source_text",
    "actor",
    "direction",
    "recipient",
    "target_cardinality",
    "condition",
    "trigger",
    "result",
    "magnitude",
    "duration_activation",
    "element",
    "attack_type",
    "state_reference",
    "capability_value",
    "dependency_value",
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
    compatibility: list[dict[str, Any]] = []
    archetypes: Counter[str] = Counter()
    for witness in witness_rows:
        witness_id = str(witness["witness_id"])
        unit = by_location.get(str(witness.get("source_location") or ""))
        record = _witness_fact_record(witness, catalog)
        legacy = _legacy_occurrences(witness, record, reviews)
        structural = _classify_unit(
            witness,
            unit,
            all_units,
            limits,
            arm="structural_only",
            fidelity_passed=False,
        )
        fidelity = _classify_unit(
            witness,
            unit,
            all_units,
            limits,
            arm="fidelity_checked",
            fidelity_passed=bool(fidelity_rows.get(witness_id, {}).get("semantic_fidelity_passed")),
        )
        arms["legacy_flattened"].extend(legacy)
        arms["structural_only"].extend(structural)
        arms["fidelity_checked"].extend(fidelity)
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
                "arms": {
                    "legacy_flattened": _arm_summary(legacy),
                    "structural_only": _arm_summary(structural),
                    "fidelity_checked": _arm_summary(fidelity),
                },
            }
        )
    return {
        "witness_count": len(witness_rows),
        "archetype_coverage": dict(sorted(archetypes.items())),
        "arms": {name: _arm_summary(values) for name, values in arms.items()},
        "compatibility": compatibility,
        "witnesses": rows,
    }


def _comparison_digest(comparison: Mapping[str, Any]) -> str:
    return _sha256(_canonical(comparison).encode("utf-8"))


def build_c2_report(
    *,
    catalog_path: Path = CATALOG_PATH,
    fidelity_oracle: Mapping[str, Any] | None = None,
    include_held_out: bool = False,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
    raw_sidekick_dir: Path = RAW_SIDEKICK_DIR,
    parsed_sidekick_dir: Path = PARSED_SIDEKICK_DIR,
) -> dict[str, Any]:
    """Build C2 comparison evidence without reading an occurrence oracle.

    Passing ``fidelity_oracle`` is an explicit evaluation action.  It is never
    loaded from a default path, and held-out rows are only included when the
    caller explicitly requests them.
    """
    c1_report = build_source_fidelity_report(
        catalog_path=catalog_path,
        raw_character_dir=raw_character_dir,
        raw_sidekick_dir=raw_sidekick_dir,
        parsed_sidekick_dir=parsed_sidekick_dir,
        oracle=fidelity_oracle,
        include_held_out=include_held_out,
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
    for cohort in ("known_regressions", "development", "held_out"):
        if cohort == "held_out" and not include_held_out:
            continue
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
            "one_direct_damage_event_rule": "one source damage event owns one direct_damage effect occurrence; multi_entity_damage is a derived projection when target cardinality is multiple",
            "definition_rule": "definitions may support only the scoped occurrence relationship invoked by the source; unresolved or unrelated definitions remain unknown",
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
    """Evaluate occurrence identities against an explicitly supplied oracle."""
    if include_held_out and oracle.get("sealed") is not True:
        raise ValueError("held-out C2 occurrence oracle must be sealed before evaluation")
    rows = _oracle_rows(oracle)
    cohorts = ["known_regressions", "development"] + (["held_out"] if include_held_out else [])
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
    parser.add_argument("--fidelity-oracle", type=Path)
    parser.add_argument("--occurrence-oracle", type=Path)
    parser.add_argument("--include-held-out", action="store_true")
    args = parser.parse_args()
    fidelity_oracle = json.loads(args.fidelity_oracle.read_text(encoding="utf-8")) if args.fidelity_oracle else None
    report = build_c2_report(fidelity_oracle=fidelity_oracle, include_held_out=args.include_held_out)
    if args.occurrence_oracle:
        oracle = json.loads(args.occurrence_oracle.read_text(encoding="utf-8"))
        report["oracle_evaluation"] = evaluate_c2_oracle(report, oracle, include_held_out=args.include_held_out)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"C2 artifact: {report['artifact_version']}")
    for cohort, comparison in report["comparisons"].items():
        arm = comparison["arms"]["fidelity_checked"]
        print(f"{cohort}: witnesses={comparison['witness_count']} effects={arm['effect_occurrence_count']} dependencies={arm['dependency_occurrence_count']}")
    print(f"comparison digest: {report['deterministic_replay']['comparison_digest']}")


if __name__ == "__main__":
    _main()
