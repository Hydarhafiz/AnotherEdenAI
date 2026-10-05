"""Source-faithful structural evidence for Milestone 6 Feature C1.

The structures in this module deliberately stop below semantic capability
classification.  They preserve how combat text was arranged and linked so a
later classifier can reason about individual occurrences without treating HTML
nesting, link labels, or generated definitions as combat authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, NavigableString, Tag

from .coverage_baseline import reconcile_catalog_receipts
from .kit_readiness import EXPECTED_CANONICAL_CHARACTER_COUNT, artifact_fingerprint
from .models import stable_skill_family_id


STRUCTURAL_EVIDENCE_VERSION = "m6-c1-1.0.0"
CATALOG_PATH = Path("src/etl/kit_catalog.json")
RAW_CHARACTER_DIR = Path("data/raw/characters")

# These are safety ceilings, not claims about semantic completeness.  The
# report selects limits at or below them from the finite captured topology.
MAX_DEPTH_CEILING = 3
MAX_PAGES_PER_ROOT_CEILING = 8
MAX_FRONTIER_PER_ROOT = 64

_SPACE_RE = re.compile(r"\s+")
_COMBAT_TERMS = re.compile(
    r"\b(?:attack|damage|enemy|party|ally|turn|zone|stance|lunatic|stack|status|"
    r"buff|debuff|resistance|hp|mp|charge|counter|barrier|critical|skill|effect)\b",
    re.IGNORECASE,
)
_EXCLUDED_TERMS = re.compile(
    r"\b(?:gallery|personality|quest|episode|encounter location|how to obtain|"
    r"acquisition|voice actor|biography|story summary)\b",
    re.IGNORECASE,
)


def _clean(value: str) -> str:
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value or "")).strip()


def _key(value: str) -> str:
    return _clean(value).casefold()


def _slugify_title(title: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title.strip()).strip("_").lower()
    return slug or "unknown"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    identity = "\x1f".join(_key(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def canonical_reference_url(href: str, base_url: str) -> tuple[str, str | None]:
    """Return a canonical page URL and a separately retained fragment."""
    absolute = urljoin(base_url, href)
    parsed = urlsplit(absolute)
    path = re.sub(r"/+", "/", unquote(parsed.path)).rstrip("/") or "/"
    page = urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), path, "", ""))
    return page, unquote(parsed.fragment) or None


def definition_page_url(title: str, base_url: str) -> str:
    parsed = urlsplit(base_url)
    wiki_root = urlunsplit((parsed.scheme, parsed.netloc, "/w/", "", ""))
    return urljoin(wiki_root, title.replace(" ", "_"))


@dataclass(frozen=True)
class SourceIdentity:
    source_kind: str
    source_url: str
    capture_sha256: str
    capture_path: str


@dataclass(frozen=True)
class StructuralToken:
    kind: str
    order: int
    text: str
    location: str
    href: str | None = None
    canonical_page_url: str | None = None
    fragment: str | None = None
    title: str | None = None
    icon_identity: str | None = None


@dataclass
class StructuralBlock:
    kind: str
    order: int
    ancestry: list[str]
    location: str
    tokens: list[StructuralToken] = field(default_factory=list)


@dataclass
class StructuralUnit:
    unit_id: str
    source: SourceIdentity
    entity_kind: str
    entity_name: str
    record_type: str
    title: str
    section: str
    source_fact_id: str | None
    family_id: str | None
    legacy_description: str
    blocks: list[StructuralBlock]
    definition_page_url: str
    explicit_definition_aliases: list[str] = field(default_factory=list)
    source_variant_label: str | None = None
    variant_key: str = "unresolved"
    progression_unlock: str | None = None
    requires_equipment: str | None = None

    def text(self) -> str:
        return _clean(" ".join(token.text for block in self.blocks for token in block.tokens))

    def references(self) -> list[StructuralToken]:
        return [
            token
            for block in self.blocks
            for token in block.tokens
            if token.kind == "reference" and token.canonical_page_url
        ]

    def variant_identity(self) -> dict[str, Any]:
        """Return offline source identity without changing the persisted fact ID."""
        family_id = self.family_id or (
            stable_skill_family_id(self.entity_name, self.title)
            if self.entity_kind == "character"
            else _stable_id("source_variant_family", self.entity_name, self.title)
        )
        return {
            "family_id": family_id,
            "variant_key": self.variant_key,
            "identity_key": f"{family_id}:{self.variant_key}",
            "source_label": self.source_variant_label,
            "basis": "explicit_source_selector" if self.source_variant_label else "unresolved",
            "progression_unlock": self.progression_unlock,
            "requires_equipment": self.requires_equipment,
        }

    def as_dict(self, *, include_r2_source_identity: bool = False) -> dict[str, Any]:
        """Serialize the C1 shape by default; R2 source identity is opt-in offline metadata."""
        payload = asdict(self)
        for key in (
            "explicit_definition_aliases",
            "source_variant_label",
            "variant_key",
            "progression_unlock",
            "requires_equipment",
        ):
            payload.pop(key, None)
        result = {
            **{key: value for key, value in payload.items() if key != "source"},
            "source": asdict(self.source),
        }
        if include_r2_source_identity:
            result["explicit_definition_aliases"] = list(self.explicit_definition_aliases)
            result["source_variant"] = self.variant_identity()
        return result


@dataclass(frozen=True)
class TraversalLimits:
    max_depth: int
    max_pages_per_root: int
    max_frontier_per_root: int = MAX_FRONTIER_PER_ROOT


def _section_title(container: Tag) -> str:
    article = container.find_parent("article")
    if article and article.get("title"):
        return _clean(str(article.get("title")))
    previous = container.find_previous(["h2", "h3", "h4"])
    return _clean(previous.get_text(" ", strip=True)) if previous else "Unsectioned combat source"


def _source_variant_label(container: Tag) -> str | None:
    """Read an explicit wiki variant selector adjacent to a collapsible skill row."""
    for attribute in ("data-variant-label", "data-skill-variant", "data-variant"):
        value = _clean(str(container.get(attribute) or ""))
        if value:
            return value
    wrapper = container.find_parent("div", class_="mw-collapsible")
    if wrapper is None or not wrapper.get("id"):
        return None
    selector = wrapper.find_previous_sibling("table")
    if selector is None or selector.get("id") != wrapper.get("id"):
        return None
    cells = selector.find_all(["th", "td"])
    if len(cells) < 2:
        return None
    label = _clean(cells[-1].get_text(" ", strip=True))
    return label or None


def _source_variant_fields(section: str, label: str | None) -> tuple[str, str | None, str | None]:
    if not label:
        return "unresolved", None, None
    normalized = _key(label)
    if "stellar" in _key(section):
        progression_unlock = "Stellar Awakening" if "stellar awakened" in _key(section) else None
        if normalized == "normal":
            return "stellar_normal", progression_unlock, None
        if normalized == "enhanced":
            return "stellar_enhanced", progression_unlock, None
    if normalized in {"normal", "base", "default"}:
        return "base", None, None
    if normalized == "enhanced":
        return "enhanced", None, None
    if normalized == "true manifest unlocked":
        return "true_manifest", "True Manifest", None
    if normalized == "manifest unlocked":
        return "manifest", "Manifest", None
    equipment_match = re.fullmatch(r"equip(?:ped)?\s+(.+)", label.strip(), flags=re.IGNORECASE)
    if equipment_match:
        requirement = _clean(equipment_match.group(1))
        key = "manifest_equipped" if "manifest" in _key(requirement) else f"equipped:{_slugify_title(requirement)}"
        return key, None, requirement
    return f"source_label:{_slugify_title(label)}", None, None


def _explicit_state_replacement(block: StructuralBlock, reference: StructuralToken) -> str | None:
    prefix = _clean(" ".join(token.text for token in block.tokens if token.order < reference.order))
    match = re.search(
        r"(?:^|[.!?]\s*)When\s+in\s+(?P<condition>[^:]+?)\s*:\s*Skill\s+changes\s+to\s*$",
        prefix,
        flags=re.IGNORECASE,
    )
    return _clean(match.group("condition")) if match else None


def _condition_before_charge(text: str, operation_start: int) -> str | None:
    prefix = _clean(text[:operation_start]).strip(" :")
    match = re.search(r"(?:^|[.!?]\s*|\]\s*:?\s*)(When\b.*)$", prefix, flags=re.IGNORECASE)
    if not match:
        return None
    return _clean(match.group(1).strip("[] :")) or None


def extract_sidekick_charge_operations(unit: StructuralUnit) -> list[dict[str, Any]]:
    """Extract explicit sidekick Charge events from their source blocks only."""
    if unit.entity_kind != "sidekick" or unit.record_type not in {"sidekick_auto", "sidekick_charge"}:
        return []
    operations: list[dict[str, Any]] = []
    patterns = (
        ("consumption", re.compile(r"\bconsumes?\s+(?P<amount>\d+)\s+charge\b", re.IGNORECASE)),
        ("gain", re.compile(r"\b(?:stack|gain(?:s)?)\s+(?:\+\s*)?(?P<amount>\d+|one|two)\s+charge\b", re.IGNORECASE)),
        (
            "availability_threshold",
            re.compile(r"\b(?:requires?|needs?|available\s+at|minimum\s+of)\s+(?P<amount>\d+)\s+charge\b", re.IGNORECASE),
        ),
    )
    for block in unit.blocks:
        text = _clean(" ".join(token.text for token in block.tokens if token.kind != "line_break"))
        for operation, pattern in patterns:
            for match in pattern.finditer(text):
                amount_text = match.group("amount").casefold()
                amount = {"one": 1, "two": 2}.get(amount_text, int(amount_text) if amount_text.isdigit() else None)
                operations.append(
                    {
                        "operation": operation,
                        "amount": amount,
                        "unit": "Charge",
                        "resource_id": "sidekick_charge",
                        "resource_owner": {"kind": unit.entity_kind, "name": unit.entity_name},
                        "source_fact_id": unit.source_fact_id,
                        "source_url": unit.source.source_url,
                        "capture_sha256": unit.source.capture_sha256,
                        "source_location": block.location,
                        "source_text": text,
                        "condition": _condition_before_charge(text, match.start()),
                        "authority": "source_explicit_non_authoritative",
                    }
                )
        if unit.record_type == "sidekick_charge" and block.kind == "root" and re.match(r"^Charged\b", text, re.IGNORECASE):
            operations.append(
                {
                    "operation": "action_availability_threshold",
                    "amount": None,
                    "unit": "Charge",
                    "threshold_state": "charged",
                    "resource_id": "sidekick_charge",
                    "resource_owner": {"kind": unit.entity_kind, "name": unit.entity_name},
                    "source_fact_id": unit.source_fact_id,
                    "source_url": unit.source.source_url,
                    "capture_sha256": unit.source.capture_sha256,
                    "source_location": block.location,
                    "source_text": "Charged",
                    "condition": None,
                    "authority": "source_explicit_non_authoritative",
                }
            )
    return operations


def extract_sidekick_aura_fields(unit: StructuralUnit) -> dict[str, Any]:
    """Split an aura condition from its effect blocks using captured structure."""
    if unit.record_type != "sidekick_aura":
        return {"status": "not_applicable", "activation_condition": None, "effect_text": ""}
    condition_block: StructuralBlock | None = None
    condition: str | None = None
    for block in unit.blocks:
        text = _clean(" ".join(token.text for token in block.tokens if token.kind != "line_break"))
        match = re.search(r"Activation\s+condition\s*:\s*(.*)$", text, flags=re.IGNORECASE)
        if match:
            condition = _clean(match.group(1)) or None
            condition_block = block
            break
    effect_blocks = [block for block in unit.blocks if block is not condition_block and block.order > (condition_block.order if condition_block else -1)]
    effect_text = _clean(" ".join(
        " ".join(token.text for token in block.tokens if token.kind != "line_break")
        for block in effect_blocks
    ))
    if condition_block is None or condition is None or not effect_text:
        return {
            "status": "unknown",
            "activation_condition": condition,
            "effect_text": unit.legacy_description,
            "condition_source_location": condition_block.location if condition_block else None,
        }
    return {
        "status": "source_blocks_separated",
        "activation_condition": condition,
        "effect_text": effect_text,
        "condition_source_location": condition_block.location,
        "effect_source_locations": [block.location for block in effect_blocks],
    }


def _direct_content_tokens(
    node: Tag,
    *,
    block_location: str,
    source_url: str,
) -> list[StructuralToken]:
    tokens: list[StructuralToken] = []

    def emit(
        kind: str,
        text: str,
        *,
        href: str | None = None,
        title: str | None = None,
        icon_identity: str | None = None,
    ) -> None:
        cleaned = _clean(text)
        if not cleaned and kind != "line_break":
            return
        page_url = fragment = None
        if href:
            page_url, fragment = canonical_reference_url(href, source_url)
        tokens.append(
            StructuralToken(
                kind=kind,
                order=len(tokens),
                text=cleaned,
                location=f"{block_location}/token[{len(tokens)}]",
                href=href,
                canonical_page_url=page_url,
                fragment=fragment,
                title=_clean(title or "") or None,
                icon_identity=_clean(icon_identity or "") or None,
            )
        )

    def walk(current: Tag | NavigableString) -> None:
        if isinstance(current, NavigableString):
            emit("text", str(current))
            return
        if current.name in {"ul", "ol", "table"}:
            return
        if current.name == "br":
            emit("line_break", "")
            return
        if current.name == "a":
            emit(
                "reference",
                current.get_text(" ", strip=True),
                href=str(current.get("href") or "") or None,
                title=str(current.get("title") or "") or None,
            )
            return
        if current.name == "img":
            emit(
                "icon",
                str(current.get("alt") or current.get("title") or ""),
                icon_identity=str(current.get("alt") or current.get("src") or ""),
            )
            return
        for child in current.children:
            walk(child)

    for child in node.children:
        walk(child)
    return tokens


def structural_blocks(description: Tag, *, source_url: str, unit_location: str) -> list[StructuralBlock]:
    """Preserve ordered root text, list ancestry, table cells, and inline identity."""
    blocks: list[StructuralBlock] = []

    def append_block(node: Tag, kind: str, ancestry: list[str]) -> None:
        location = f"{unit_location}/block[{len(blocks)}]"
        tokens = _direct_content_tokens(node, block_location=location, source_url=source_url)
        if tokens:
            blocks.append(StructuralBlock(kind, len(blocks), list(ancestry), location, tokens))

    append_block(description, "root", [])

    def walk_collections(node: Tag, ancestry: list[str]) -> None:
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            if child.name in {"ul", "ol"}:
                list_kind = "ordered_list" if child.name == "ol" else "unordered_list"
                item_number = 0
                for item in child.find_all("li", recursive=False):
                    item_ancestry = [*ancestry, f"{list_kind}[{item_number}]"]
                    append_block(item, "list_item", item_ancestry)
                    walk_collections(item, item_ancestry)
                    item_number += 1
            elif child.name == "table":
                for row_number, row in enumerate(child.find_all("tr", recursive=False)):
                    for cell_number, cell in enumerate(row.find_all(["th", "td"], recursive=False)):
                        append_block(
                            cell,
                            "table_cell",
                            [*ancestry, f"table_row[{row_number}]", f"cell[{cell_number}]"],
                        )
            else:
                walk_collections(child, ancestry)

    walk_collections(description, [])
    if not blocks:
        location = f"{unit_location}/block[0]"
        blocks.append(
            StructuralBlock(
                "root",
                0,
                [],
                location,
                [StructuralToken("diagnostic", 0, "empty structural description", f"{location}/token[0]")],
            )
        )
    return blocks


def parse_grid_units(
    html: str,
    *,
    source: SourceIdentity,
    entity_kind: str,
    entity_name: str,
) -> list[StructuralUnit]:
    """Parse character or sidekick skill grids into one shared representation."""
    units, _diagnostics = parse_grid_document(
        html,
        source=source,
        entity_kind=entity_kind,
        entity_name=entity_name,
    )
    return units


def parse_grid_document(
    html: str,
    *,
    source: SourceIdentity,
    entity_kind: str,
    entity_name: str,
) -> tuple[list[StructuralUnit], list[dict[str, Any]]]:
    """Parse grid units and retain explicit diagnostics for malformed entries."""
    soup = BeautifulSoup(html, "html.parser")
    units: list[StructuralUnit] = []
    diagnostics: list[dict[str, Any]] = []
    for index, container in enumerate(soup.select("div.character-skill-grid-container")):
        name_node = container.select_one(".skill-name")
        description = container.select_one(".skill-description")
        title = _clean(name_node.get_text(" ", strip=True)) if name_node else ""
        if not title or title.casefold() == "skill name" or description is None:
            diagnostics.append(
                {
                    "source_kind": source.source_kind,
                    "capture_sha256": source.capture_sha256,
                    "location": f"sha256:{source.capture_sha256}/grid[{index}]",
                    "reason": "missing_title" if not title else "missing_description",
                }
            )
            continue
        section = _section_title(container)
        name_link = name_node.find("a", href=True) if name_node else None
        explicit_aliases = []
        if name_link and name_link.get("href"):
            alias_url, _fragment = canonical_reference_url(str(name_link.get("href")), source.source_url)
            explicit_aliases.append(alias_url)
        variant_label = _source_variant_label(container)
        variant_key, progression_unlock, requires_equipment = _source_variant_fields(section, variant_label)
        skill_type_node = container.select_one(".character-skill-element-type .lower-grid")
        skill_type = _clean(skill_type_node.get_text(" ", strip=True)) if skill_type_node else ""
        description_text = _clean(description.get_text(" ", strip=True))
        if entity_kind == "sidekick":
            lowered = description_text.casefold()
            if "aura" in lowered and "activation condition" in lowered:
                record_type = "sidekick_aura"
            elif "charged" in lowered or ("consumes" in lowered and "charge" in lowered):
                record_type = "sidekick_charge"
            else:
                record_type = "sidekick_auto"
        elif skill_type.casefold() == "passive" or "passive skills" in section.casefold():
            record_type = "passive_skill"
        else:
            record_type = "active_skill"
        unit_id = _stable_id("structural_unit", source.capture_sha256, entity_name, record_type, title, str(index))
        location = f"sha256:{source.capture_sha256}/grid[{index}]"
        units.append(
            StructuralUnit(
                unit_id=unit_id,
                source=source,
                entity_kind=entity_kind,
                entity_name=entity_name,
                record_type=record_type,
                title=title,
                section=section,
                source_fact_id=None,
                family_id=None,
                legacy_description=description_text,
                blocks=structural_blocks(description, source_url=source.source_url, unit_location=location),
                definition_page_url=canonical_reference_url(
                    definition_page_url(title, source.source_url), source.source_url
                )[0],
                explicit_definition_aliases=explicit_aliases,
                source_variant_label=variant_label,
                variant_key=variant_key,
                progression_unlock=progression_unlock,
                requires_equipment=requires_equipment,
            )
        )
    return units, diagnostics


def parse_table_row_unit(
    row: Tag,
    *,
    source: SourceIdentity,
    entity_kind: str,
    entity_name: str,
    record_type: str,
    source_fact_id: str,
    title_cell: int = 0,
) -> StructuralUnit:
    """Adapt boss, equipment, or Grasta rows to the shared block contract."""
    cells = row.find_all(["th", "td"], recursive=False)
    if not cells or title_cell >= len(cells):
        raise ValueError("structural table row requires the configured title cell")
    title = _clean(cells[title_cell].get_text(" ", strip=True))
    if not title:
        raise ValueError("structural table row requires a non-empty title")
    unit_id = _stable_id("structural_unit", source.capture_sha256, entity_name, record_type, source_fact_id)
    unit_location = f"sha256:{source.capture_sha256}/row[{source_fact_id}]"
    blocks: list[StructuralBlock] = []
    for cell_number, cell in enumerate(cells):
        location = f"{unit_location}/block[{cell_number}]"
        blocks.append(
            StructuralBlock(
                kind="table_cell",
                order=cell_number,
                ancestry=["table_row[0]", f"cell[{cell_number}]"],
                location=location,
                tokens=_direct_content_tokens(cell, block_location=location, source_url=source.source_url),
            )
        )
    legacy = _clean(" ".join(cell.get_text(" ", strip=True) for cell in cells))
    return StructuralUnit(
        unit_id=unit_id,
        source=source,
        entity_kind=entity_kind,
        entity_name=entity_name,
        record_type=record_type,
        title=title,
        section=_section_title(row),
        source_fact_id=source_fact_id,
        family_id=None,
        legacy_description=legacy,
        blocks=blocks,
        definition_page_url=canonical_reference_url(
            definition_page_url(title, source.source_url), source.source_url
        )[0],
    )


def bind_catalog_facts(
    units: Sequence[StructuralUnit],
    facts: Sequence[Mapping[str, Any]],
) -> tuple[list[StructuralUnit], list[dict[str, str]]]:
    """Bind structure to stable facts without changing IDs or legacy text."""
    candidates: dict[tuple[str, str], list[StructuralUnit]] = defaultdict(list)
    for unit in units:
        candidates[(unit.record_type, _key(unit.title))].append(unit)

    diagnostics: list[dict[str, str]] = []
    bound: list[StructuralUnit] = []
    used: set[str] = set()
    for fact in facts:
        fact_id = str(fact.get("skill_id") or fact.get("passive_skill_id") or "")
        record_type = "passive_skill" if fact.get("passive_skill_id") else "active_skill"
        matches = [
            unit for unit in candidates.get((record_type, _key(str(fact.get("name") or ""))), [])
            if unit.unit_id not in used
        ]
        exact = [unit for unit in matches if _key(unit.legacy_description) == _key(str(fact.get("description") or ""))]
        selected = exact[0] if len(exact) == 1 else matches[0] if len(matches) == 1 else None
        if selected is None:
            diagnostics.append(
                {
                    "source_fact_id": fact_id,
                    "record_type": record_type,
                    "reason": "no_structural_match" if not matches else "ambiguous_structural_match",
                }
            )
            continue
        selected.source_fact_id = fact_id
        selected.family_id = str(fact.get("skill_family_id") or "") or None
        selected.legacy_description = str(fact.get("description") or "")
        used.add(selected.unit_id)
        bound.append(selected)
    return bound, diagnostics


def classify_destination(unit: StructuralUnit) -> str:
    """Classify from captured destination content, never from URL spelling."""
    text = f"{unit.title} {unit.section} {unit.text()}"
    if _EXCLUDED_TERMS.search(text) and not _COMBAT_TERMS.search(text):
        return "excluded_noncombat"
    if _COMBAT_TERMS.search(text):
        return "combat_definition"
    return "unresolved_content_classification"


def destination_index(
    units: Iterable[StructuralUnit],
    *,
    include_explicit_aliases: bool = False,
) -> dict[str, list[StructuralUnit]]:
    index: dict[str, list[StructuralUnit]] = defaultdict(list)
    for unit in units:
        index[unit.definition_page_url].append(unit)
        if include_explicit_aliases:
            for alias in unit.explicit_definition_aliases:
                if alias != unit.definition_page_url:
                    index[alias].append(unit)
    return dict(index)


def audit_reference_topology(
    units: Sequence[StructuralUnit],
    *,
    include_explicit_aliases: bool = False,
) -> dict[str, int]:
    """Inspect the complete finite local graph before selecting traversal limits."""
    index = destination_index(units, include_explicit_aliases=include_explicit_aliases)
    adjacency: dict[str, set[str]] = defaultdict(set)
    occurrence_count = 0
    for unit in units:
        for reference in unit.references():
            occurrence_count += 1
            for target in index.get(str(reference.canonical_page_url), []):
                if classify_destination(target) == "combat_definition":
                    adjacency[unit.unit_id].add(target.unit_id)

    maximum_depth = 0
    maximum_pages = 1
    maximum_out_degree = max((len(value) for value in adjacency.values()), default=0)
    by_id = {unit.unit_id: unit for unit in units}
    for root in units:
        queue = deque([(root.unit_id, 0)])
        visited: set[str] = set()
        pages = {root.source.source_url}
        while queue:
            current, depth = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            maximum_depth = max(maximum_depth, depth)
            for target_id in adjacency.get(current, set()):
                target = by_id[target_id]
                pages.add(target.definition_page_url)
                queue.append((target_id, depth + 1))
        maximum_pages = max(maximum_pages, len(pages))
    return {
        "unit_count": len(units),
        "reference_occurrence_count": occurrence_count,
        "locally_resolvable_edge_count": sum(len(value) for value in adjacency.values()),
        "observed_maximum_depth": maximum_depth,
        "observed_maximum_pages_per_root": maximum_pages,
        "observed_maximum_out_degree": maximum_out_degree,
    }


def select_traversal_limits(topology: Mapping[str, int]) -> TraversalLimits:
    """Add one unit of headroom while staying inside fixed safety ceilings."""
    return TraversalLimits(
        max_depth=min(MAX_DEPTH_CEILING, max(1, int(topology["observed_maximum_depth"]) + 1)),
        max_pages_per_root=min(
            MAX_PAGES_PER_ROOT_CEILING,
            max(2, int(topology["observed_maximum_pages_per_root"]) + 1),
        ),
    )


def resolve_bounded_references(
    roots: Sequence[StructuralUnit],
    all_units: Sequence[StructuralUnit],
    limits: TraversalLimits,
    *,
    include_explicit_aliases: bool = False,
) -> list[dict[str, Any]]:
    """Resolve a deterministic, locally captured, definition-only frontier."""
    index = destination_index(all_units, include_explicit_aliases=include_explicit_aliases)
    outcomes: list[dict[str, Any]] = []
    for root in sorted(roots, key=lambda unit: unit.unit_id):
        frontier = deque([(root, 0)])
        visited_units: set[str] = set()
        visited_pages = {canonical_reference_url(root.source.source_url, root.source.source_url)[0]}
        frontier_additions = 0
        occurrence_number = 0
        while frontier:
            unit, depth = frontier.popleft()
            if unit.unit_id in visited_units:
                continue
            visited_units.add(unit.unit_id)
            for block in unit.blocks:
                for reference in block.tokens:
                    if reference.kind != "reference" or not reference.canonical_page_url:
                        continue
                    occurrence_id = _stable_id(
                        "reference_occurrence", root.unit_id, unit.unit_id, reference.location, str(occurrence_number)
                    )
                    occurrence_number += 1
                    targets = index.get(str(reference.canonical_page_url), [])
                    alias_targets = [
                        target for target in targets
                        if str(reference.canonical_page_url) in target.explicit_definition_aliases
                    ]
                    if include_explicit_aliases and alias_targets:
                        targets = alias_targets
                    resolution_basis = "explicit_source_href_alias" if alias_targets else "captured_title_slug"
                    base = {
                        "root_source_fact_id": root.source_fact_id,
                        "origin_unit_id": unit.unit_id,
                        "occurrence_id": occurrence_id,
                        "occurrence_location": reference.location,
                        "canonical_page_url": reference.canonical_page_url,
                        "fragment": reference.fragment,
                        "depth": depth,
                    }
                    if include_explicit_aliases:
                        base["resolution_basis"] = resolution_basis
                    if not targets:
                        outcomes.append({**base, "status": "access_failure", "reason": "no_admitted_capture"})
                        continue
                    classified = [(target, classify_destination(target)) for target in targets]
                    combat_targets = [target for target, kind in classified if kind == "combat_definition"]
                    if not combat_targets:
                        kinds = sorted({kind for _, kind in classified})
                        status = "excluded" if kinds == ["excluded_noncombat"] else "unresolved_mapping"
                        outcomes.append({**base, "status": status, "reason": ",".join(kinds)})
                        continue
                    variant_match = False
                    if include_explicit_aliases and len(combat_targets) > 1:
                        matching_variants = [
                            candidate
                            for candidate in combat_targets
                            if unit.variant_key != "unresolved" and candidate.variant_key == unit.variant_key
                        ]
                        if len(matching_variants) == 1:
                            combat_targets = matching_variants
                            variant_match = True
                        else:
                            outcomes.append(
                                {
                                    **base,
                                    "status": "unresolved_mapping",
                                    "reason": "ambiguous_source_variant_alias",
                                    "candidate_unit_ids": sorted(candidate.unit_id for candidate in combat_targets),
                                    "candidate_variant_keys": sorted(candidate.variant_key for candidate in combat_targets),
                                }
                            )
                            continue
                    target = sorted(combat_targets, key=lambda item: item.unit_id)[0]
                    target_page = (
                        target.source.source_url
                        if include_explicit_aliases and alias_targets
                        else str(reference.canonical_page_url)
                    )
                    resolved = {
                        **base,
                        "target_unit_id": target.unit_id,
                        "target_source_fact_id": target.source_fact_id,
                    }
                    if include_explicit_aliases:
                        resolved["target_variant_key"] = target.variant_key
                        if variant_match:
                            resolved["resolution_basis"] = "explicit_source_href_alias_and_variant_key"
                    replacement_condition = _explicit_state_replacement(block, reference)
                    if replacement_condition:
                        family_id = str(root.variant_identity()["family_id"])
                        replacement_key = f"state_replacement:{_slugify_title(replacement_condition)}:{target.variant_key}"
                        resolved["variant_relationship"] = {
                            "type": "state_selected_replacement",
                            "family_id": family_id,
                            "variant_key": replacement_key,
                            "identity_key": f"{family_id}:{replacement_key}",
                            "condition": replacement_condition,
                            "target_source_fact_id": target.source_fact_id,
                            "target_variant_key": target.variant_key,
                            "independently_equipable": False,
                        }
                    if target.unit_id in visited_units:
                        outcomes.append({**resolved, "status": "visited", "reason": "definition_already_visited"})
                    elif depth >= limits.max_depth:
                        outcomes.append({**resolved, "status": "depth_budget_exhausted", "reason": "max_depth"})
                    elif target_page not in visited_pages and len(visited_pages) >= limits.max_pages_per_root:
                        outcomes.append({**resolved, "status": "page_budget_exhausted", "reason": "max_pages_per_root"})
                    elif frontier_additions >= limits.max_frontier_per_root:
                        outcomes.append(
                            {
                                **resolved,
                                "status": "frontier_budget_exhausted",
                                "reason": "max_frontier_per_root",
                            }
                        )
                    else:
                        visited_pages.add(target_page)
                        frontier.append((target, depth + 1))
                        frontier_additions += 1
                        outcomes.append({**resolved, "status": "resolved", "reason": "captured_combat_definition"})
    return outcomes


def _catalog_facts(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [*record.get("skills", []), *record.get("passive_skills", [])]


def build_catalog_structural_sidecar(
    catalog_path: Path = CATALOG_PATH,
    raw_character_dir: Path = RAW_CHARACTER_DIR,
) -> dict[str, Any]:
    """Build the generated C1 sidecar from the accepted catalog and local captures."""
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    reconciliation = reconcile_catalog_receipts(catalog, expected_count=EXPECTED_CANONICAL_CHARACTER_COUNT)
    all_units: list[StructuralUnit] = []
    bound_units: list[StructuralUnit] = []
    diagnostics: list[dict[str, str]] = []
    parser_diagnostics: list[dict[str, Any]] = []
    captures: list[dict[str, str]] = []
    for record in sorted(catalog["characters"], key=lambda row: str(row["receipt"]["character_id"])):
        name = str(record["receipt"]["character_name"])
        capture_path = raw_character_dir / f"{_slugify_title(name)}.html"
        if not capture_path.exists():
            diagnostics.extend(
                {
                    "source_fact_id": str(fact.get("skill_id") or fact.get("passive_skill_id") or ""),
                    "record_type": "passive_skill" if fact.get("passive_skill_id") else "active_skill",
                    "reason": "capture_missing",
                }
                for fact in _catalog_facts(record)
            )
            continue
        raw = capture_path.read_bytes()
        sha256 = _sha256_bytes(raw)
        source_url = str(record.get("character", {}).get("detail_url") or record["receipt"].get("source_url") or "")
        source = SourceIdentity("character", source_url, sha256, capture_path.as_posix())
        units, document_diagnostics = parse_grid_document(
            raw.decode("utf-8"), source=source, entity_kind="character", entity_name=name
        )
        bound, mapping_diagnostics = bind_catalog_facts(units, _catalog_facts(record))
        all_units.extend(units)
        bound_units.extend(bound)
        diagnostics.extend(mapping_diagnostics)
        parser_diagnostics.extend(document_diagnostics)
        captures.append({"entity_name": name, "source_url": source_url, "capture_sha256": sha256})

    topology = audit_reference_topology(all_units)
    limits = select_traversal_limits(topology)
    resolutions = resolve_bounded_references(bound_units, all_units, limits)
    mapped_by_kind = Counter(unit.record_type for unit in bound_units)
    unresolved_by_kind = Counter(row["record_type"] for row in diagnostics)
    resolution_states = Counter(row["status"] for row in resolutions)
    sidecar_units = [unit.as_dict() for unit in sorted(bound_units, key=lambda item: str(item.source_fact_id))]
    return {
        "artifact_version": STRUCTURAL_EVIDENCE_VERSION,
        "authority": {
            "generated_capability_authority": False,
            "definitions_grant_capabilities": False,
            "legacy_catalog_is_mutated": False,
            "graph_schema_is_mutated": False,
        },
        "source_identity": {
            "catalog_fingerprint": artifact_fingerprint(catalog),
            "capture_count": len(captures),
            "captures": captures,
        },
        "legal_kit_reconciliation": reconciliation,
        "coverage": {
            "catalog_identity_denominator": len(catalog["characters"]),
            "source_fact_denominator": sum(len(_catalog_facts(record)) for record in catalog["characters"]),
            "bound_source_fact_count": len(bound_units),
            "unresolved_source_fact_count": len(diagnostics),
            "bound_by_source_kind": dict(sorted(mapped_by_kind.items())),
            "unresolved_by_source_kind": dict(sorted(unresolved_by_kind.items())),
            "unresolved_mappings": diagnostics,
            "parser_diagnostics": parser_diagnostics,
        },
        "legacy_equivalence": {
            "bound_fact_ids_preserved": all(unit.source_fact_id for unit in bound_units),
            "family_ids_preserved_where_applicable": all(
                unit.family_id for unit in bound_units if unit.record_type == "active_skill"
            ),
            "legacy_descriptions_retained": all(bool(unit.legacy_description) for unit in bound_units),
        },
        "topology_audit": topology,
        "traversal_limits": asdict(limits),
        "reference_resolution": {
            "occurrence_count": len(resolutions),
            "status_distribution": dict(sorted(resolution_states.items())),
            "occurrences": resolutions,
        },
        "units": sidecar_units,
        "sidecar_digest": _sha256_bytes(
            json.dumps(sidecar_units, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ),
    }


def write_generated_sidecar(destination: Path, **kwargs: Any) -> dict[str, Any]:
    """Write a local generated sidecar; callers must target an ignored path."""
    payload = build_catalog_structural_sidecar(**kwargs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
