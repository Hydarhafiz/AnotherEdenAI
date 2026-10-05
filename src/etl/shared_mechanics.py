"""Resolve a small allowlist of shared mechanics without granting authority.

The registry stores mechanic identities and source pointers only.  Resolution
never changes the owning source fact or copies a shared definition's rules into
that fact.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, Sequence

from .structural_evidence import StructuralToken, StructuralUnit


REGISTRY_PATH = Path(__file__).with_name("shared_mechanics_registry.json")
REGISTRY_VERSION = "m6-c2-shared-mechanics-1.0.0"

AliasKind = Literal["href", "name", "icon"]
ResolutionStatus = Literal["resolved", "ambiguous", "unresolved"]
ResolutionBasis = Literal[
    "explicit_href",
    "allowlisted_name",
    "allowlisted_icon",
    "unresolved",
]
DefinitionStatus = Literal["available", "unavailable"]


@dataclass(frozen=True)
class MechanicSourceAnchor:
    anchor_id: str
    source_kind: str
    source_url: str
    source_capture_sha256: str
    source_location: str
    source_fact_id: str = ""
    witness_id: str = ""
    source_slice_sha256: str = ""
    source_span_sha256: str = ""


@dataclass(frozen=True)
class MechanicAlias:
    kind: AliasKind
    value: str
    source_anchor_id: str
    fragment: str = ""
    required_label: str = ""
    required_entity_kind: str = ""
    required_record_types: tuple[str, ...] = ()
    required_reference_urls: tuple[str, ...] = ()
    case_sensitive: bool = False


@dataclass(frozen=True)
class SharedMechanicEntry:
    mechanic_id: str
    mechanic_class: str
    definition_status: DefinitionStatus
    definition_source_anchor_id: str
    aliases: tuple[MechanicAlias, ...]
    source_anchors: tuple[MechanicSourceAnchor, ...]


@dataclass(frozen=True)
class SharedMechanicResolution:
    """One source-local mention linked to a registry identity."""

    parent_source_fact_id: str
    parent_owner_kind: str
    parent_owner_name: str
    parent_capture_sha256: str
    parent_source_url: str
    source_location: str
    source_offset_start: int
    source_offset_end: int
    mention: str
    mechanic_id: str
    mechanic_class: str
    resolution_status: ResolutionStatus
    resolution_basis: ResolutionBasis
    definition_status: DefinitionStatus
    alias_source_anchor_id: str
    definition_source_anchor_id: str
    candidate_mechanic_ids: tuple[str, ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class _AliasMatch:
    entry: SharedMechanicEntry
    alias: MechanicAlias
    basis: ResolutionBasis
    mention: str
    offset_start: int = -1
    offset_end: int = -1


def _clean(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").split())


def _key(value: str) -> str:
    return _clean(value).casefold()


def _phrase_pattern(value: str, *, case_sensitive: bool = False) -> re.Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(rf"(?<!\w){re.escape(_clean(value))}(?!\w)", flags)


class SharedMechanicRegistry:
    """Index a bounded registry by stable ID, exact URL, and exact aliases."""

    def __init__(self, entries: Sequence[SharedMechanicEntry], version: str) -> None:
        by_id: dict[str, SharedMechanicEntry] = {}
        href_aliases: list[tuple[str, str, SharedMechanicEntry, MechanicAlias]] = []
        name_aliases: list[tuple[str, SharedMechanicEntry, MechanicAlias]] = []
        icon_aliases: list[tuple[str, SharedMechanicEntry, MechanicAlias]] = []
        for entry in entries:
            if entry.mechanic_id in by_id:
                raise ValueError(f"duplicate shared mechanic ID: {entry.mechanic_id}")
            by_id[entry.mechanic_id] = entry
            anchors = {anchor.anchor_id for anchor in entry.source_anchors}
            if entry.definition_status == "available" and entry.definition_source_anchor_id not in anchors:
                raise ValueError(f"available definition has no source anchor: {entry.mechanic_id}")
            if entry.definition_status == "unavailable" and entry.definition_source_anchor_id:
                raise ValueError(f"unavailable definition cannot point at a source: {entry.mechanic_id}")
            for alias in entry.aliases:
                if alias.source_anchor_id not in anchors:
                    raise ValueError(f"alias has no source anchor: {entry.mechanic_id}/{alias.value}")
                if alias.kind == "href":
                    href_aliases.append((_clean(alias.value), alias.fragment, entry, alias))
                elif alias.kind == "name":
                    name_aliases.append((alias.value, entry, alias))
                elif alias.kind == "icon":
                    icon_aliases.append((_key(alias.value), entry, alias))
                else:
                    raise ValueError(f"unsupported shared mechanic alias kind: {alias.kind}")
        self.entries = tuple(entries)
        self.version = version
        self.by_id = by_id
        self.href_aliases = tuple(href_aliases)
        self.name_aliases = tuple(name_aliases)
        self.icon_aliases = tuple(icon_aliases)

    def resolve_token(
        self,
        token: StructuralToken,
        unit: StructuralUnit | None,
        *,
        parent_source_fact_id: str = "",
    ) -> tuple[SharedMechanicResolution, ...]:
        """Resolve one captured token, preserving explicit links over labels."""
        matches = self._token_matches(token)
        if not matches:
            reason = "unknown_href" if token.kind == "reference" else "unknown_name"
            if token.kind == "reference" and self._has_allowlisted_label(token.text):
                reason = "explicit_href_not_allowlisted"
            return (
                self._resolution(
                    token,
                    unit,
                    parent_source_fact_id,
                    mention=_clean(token.text),
                    candidates=(),
                    basis="unresolved",
                    reason=reason,
                ),
            )

        grouped: dict[tuple[str, str, int, int], list[_AliasMatch]] = {}
        for match in matches:
            key = (match.mention, match.basis, match.offset_start, match.offset_end)
            grouped.setdefault(key, []).append(match)

        results: list[SharedMechanicResolution] = []
        for (mention, basis, _start, _end), candidates in sorted(grouped.items()):
            results.append(
                self._resolution(
                    token,
                    unit,
                    parent_source_fact_id,
                    mention=mention,
                    candidates=tuple(candidates),
                    basis=basis,
                )
            )
        return tuple(results)

    def resolve_unit_mentions(
        self,
        unit: StructuralUnit,
        *,
        parent_source_fact_id: str = "",
    ) -> list[SharedMechanicResolution]:
        """Return allowlisted mentions without scanning arbitrary prose."""
        resolutions: list[SharedMechanicResolution] = []
        if unit.explicit_definition_aliases:
            title_location = next(
                (
                    f"{block.location.rsplit('/block[', 1)[0]}/skill_name_link"
                    for block in unit.blocks
                    if "/block[" in block.location
                ),
                f"sha256:{unit.source.capture_sha256}/skill_name_link",
            )
            for order, page_url in enumerate(unit.explicit_definition_aliases):
                title_reference = StructuralToken(
                    kind="reference",
                    order=order,
                    text=unit.title,
                    location=title_location,
                    href=page_url,
                    canonical_page_url=page_url,
                )
                resolutions.extend(
                    result
                    for result in self.resolve_token(
                        title_reference,
                        unit,
                        parent_source_fact_id=parent_source_fact_id,
                    )
                    if result.reason not in {"unknown_href", "unknown_name"}
                )
        for block in unit.blocks:
            for token in block.tokens:
                for result in self.resolve_token(
                    token,
                    unit,
                    parent_source_fact_id=parent_source_fact_id,
                ):
                    if result.reason not in {"unknown_href", "unknown_name"}:
                        resolutions.append(result)
        unique: dict[tuple[str, str, str, int, int], SharedMechanicResolution] = {}
        for result in resolutions:
            key = (
                result.source_location,
                result.mention,
                result.resolution_basis,
                result.source_offset_start,
                result.source_offset_end,
            )
            unique.setdefault(key, result)
        return sorted(
            unique.values(),
            key=lambda result: (result.source_location, result.mention, result.mechanic_id),
        )

    def _token_matches(self, token: StructuralToken) -> list[_AliasMatch]:
        matches: list[_AliasMatch] = []
        if token.kind == "reference":
            if not token.canonical_page_url:
                return matches
            target = _clean(token.canonical_page_url)
            fragment = _key(token.fragment or "")
            for alias_target, alias_fragment, entry, alias in self.href_aliases:
                if target != alias_target or fragment != _key(alias_fragment):
                    continue
                matches.append(_AliasMatch(entry, alias, "explicit_href", _clean(token.text)))
            return matches

        if token.kind == "icon":
            identities = {_key(token.icon_identity or ""), _key(token.text)}
            for alias_value, entry, alias in self.icon_aliases:
                if alias_value in identities and alias_value:
                    matches.append(_AliasMatch(entry, alias, "allowlisted_icon", alias.value))
            return matches

        if token.kind == "text":
            source_text = _clean(token.text)
            for alias_value, entry, alias in self.name_aliases:
                matches_alias = (
                    source_text == _clean(alias_value)
                    if alias.case_sensitive
                    else _key(source_text) == _key(alias_value)
                )
                if matches_alias:
                    matches.append(
                        _AliasMatch(
                            entry,
                            alias,
                            "allowlisted_name",
                            source_text,
                            0,
                            len(source_text),
                        )
                    )
        return matches

    def _has_allowlisted_label(self, label: str) -> bool:
        return any(
            _phrase_pattern(alias.value, case_sensitive=alias.case_sensitive).search(label)
            for _alias_value, _entry, alias in self.name_aliases
        )

    @staticmethod
    def _context_status(alias: MechanicAlias, token: StructuralToken, unit: StructuralUnit | None) -> bool | None:
        if alias.required_label:
            if token.kind != "reference":
                return False
            if _key(token.text) != _key(alias.required_label):
                return False

        if alias.required_entity_kind:
            if unit is None or not unit.entity_kind:
                return None
            if _key(unit.entity_kind) != _key(alias.required_entity_kind):
                return False

        if alias.required_record_types:
            if unit is None or not unit.record_type:
                return None
            if unit.record_type not in alias.required_record_types:
                return False

        if alias.required_reference_urls:
            if unit is None:
                return None
            references = {str(reference.canonical_page_url or "") for reference in unit.references()}
            if not set(alias.required_reference_urls).issubset(references):
                return False

        return True

    def _resolution(
        self,
        token: StructuralToken,
        unit: StructuralUnit | None,
        parent_source_fact_id: str,
        *,
        mention: str,
        candidates: tuple[_AliasMatch, ...],
        basis: ResolutionBasis,
        reason: str = "",
    ) -> SharedMechanicResolution:
        potential: list[_AliasMatch] = []
        certain: list[_AliasMatch] = []
        rejected = 0
        for candidate in candidates:
            context = self._context_status(candidate.alias, token, unit)
            if context is False:
                rejected += 1
                continue
            potential.append(candidate)
            if context is True:
                certain.append(candidate)

        candidate_ids = tuple(sorted({candidate.entry.mechanic_id for candidate in potential}))
        identity_id = ""
        identity_class = ""
        alias_anchor_id = ""
        definition_status: DefinitionStatus = "unavailable"
        definition_anchor_id = ""
        status: ResolutionStatus
        result_basis = basis
        if len(candidate_ids) > 1:
            status = "ambiguous"
            reason = "multiple_contextual_identities"
        elif len(candidate_ids) == 1 and not certain:
            status = "unresolved"
            reason = "insufficient_context"
        elif len(candidate_ids) == 1:
            chosen = next(candidate for candidate in certain if candidate.entry.mechanic_id == candidate_ids[0])
            entry = chosen.entry
            identity_id = entry.mechanic_id
            identity_class = entry.mechanic_class
            alias_anchor_id = chosen.alias.source_anchor_id
            definition_status = entry.definition_status
            definition_anchor_id = entry.definition_source_anchor_id
            status = "resolved"
        else:
            status = "unresolved"
            result_basis = "unresolved"
            if not reason:
                reason = "context_mismatch" if rejected else "unknown_name"

        return SharedMechanicResolution(
            parent_source_fact_id=parent_source_fact_id or (unit.source_fact_id if unit and unit.source_fact_id else ""),
            parent_owner_kind=unit.entity_kind if unit else "",
            parent_owner_name=unit.entity_name if unit else "",
            parent_capture_sha256=unit.source.capture_sha256 if unit else "",
            parent_source_url=unit.source.source_url if unit else "",
            source_location=token.location,
            source_offset_start=candidates[0].offset_start if candidates else -1,
            source_offset_end=candidates[0].offset_end if candidates else -1,
            mention=mention,
            mechanic_id=identity_id,
            mechanic_class=identity_class,
            resolution_status=status,
            resolution_basis=result_basis,
            definition_status=definition_status,
            alias_source_anchor_id=alias_anchor_id,
            definition_source_anchor_id=definition_anchor_id,
            candidate_mechanic_ids=candidate_ids,
            reason=reason,
        )


def _required_text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"shared mechanic registry field {key!r} must be non-empty text")
    return value.strip()


def _validated_sha256(value: str, *, field_name: str, optional: bool = False) -> str:
    if optional and not value:
        return value
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"shared mechanic registry field {field_name!r} must be a SHA-256 digest")
    return value


def _load_anchor(raw: dict[str, object]) -> MechanicSourceAnchor:
    anchor = MechanicSourceAnchor(
        anchor_id=_required_text(raw, "anchor_id"),
        source_kind=_required_text(raw, "source_kind"),
        source_url=_required_text(raw, "source_url"),
        source_capture_sha256=_required_text(raw, "source_capture_sha256"),
        source_location=_required_text(raw, "source_location"),
        source_fact_id=str(raw.get("source_fact_id") or ""),
        witness_id=str(raw.get("witness_id") or ""),
        source_slice_sha256=str(raw.get("source_slice_sha256") or ""),
        source_span_sha256=str(raw.get("source_span_sha256") or ""),
    )
    _validated_sha256(anchor.source_capture_sha256, field_name="source_capture_sha256")
    _validated_sha256(anchor.source_slice_sha256, field_name="source_slice_sha256", optional=True)
    _validated_sha256(anchor.source_span_sha256, field_name="source_span_sha256", optional=True)
    return anchor


def _load_alias(raw: dict[str, object]) -> MechanicAlias:
    kind = _required_text(raw, "kind")
    if kind not in {"href", "name", "icon"}:
        raise ValueError(f"unknown shared mechanic alias kind: {kind}")
    return MechanicAlias(
        kind=kind,  # type: ignore[arg-type]
        value=_required_text(raw, "value"),
        source_anchor_id=_required_text(raw, "source_anchor_id"),
        fragment=str(raw.get("fragment") or ""),
        required_label=str(raw.get("required_label") or ""),
        required_entity_kind=str(raw.get("required_entity_kind") or ""),
        required_record_types=tuple(str(value) for value in raw.get("required_record_types", [])),
        required_reference_urls=tuple(str(value) for value in raw.get("required_reference_urls", [])),
        case_sensitive=bool(raw.get("case_sensitive", False)),
    )


@lru_cache(maxsize=4)
def load_shared_mechanic_registry(path: Path = REGISTRY_PATH) -> SharedMechanicRegistry:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported shared mechanic registry schema")
    version = _required_text(payload, "registry_version")
    if version != REGISTRY_VERSION:
        raise ValueError(f"registry version mismatch: expected {REGISTRY_VERSION}, got {version}")
    entries: list[SharedMechanicEntry] = []
    for raw in payload.get("entries", []):
        if not isinstance(raw, dict):
            raise ValueError("shared mechanic registry entries must be objects")
        definition_status = _required_text(raw, "definition_status")
        if definition_status not in {"available", "unavailable"}:
            raise ValueError(f"unknown shared mechanic definition status: {definition_status}")
        anchors = tuple(_load_anchor(anchor) for anchor in raw.get("source_anchors", []))
        entries.append(
            SharedMechanicEntry(
                mechanic_id=_required_text(raw, "mechanic_id"),
                mechanic_class=_required_text(raw, "mechanic_class"),
                definition_status=definition_status,  # type: ignore[arg-type]
                definition_source_anchor_id=str(raw.get("definition_source_anchor_id") or ""),
                aliases=tuple(_load_alias(alias) for alias in raw.get("aliases", [])),
                source_anchors=anchors,
            )
        )
    if not entries:
        raise ValueError("shared mechanic registry must contain at least one admitted identity")
    return SharedMechanicRegistry(entries, version)


def resolve_shared_mechanics(
    unit: StructuralUnit,
    *,
    parent_source_fact_id: str = "",
    registry: SharedMechanicRegistry | None = None,
) -> list[SharedMechanicResolution]:
    """Resolve bounded mentions while leaving every payload on the parent."""
    selected_registry = registry or load_shared_mechanic_registry()
    return selected_registry.resolve_unit_mentions(
        unit,
        parent_source_fact_id=parent_source_fact_id,
    )
