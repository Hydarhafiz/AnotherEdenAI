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
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .capability_taxonomy import load_capability_taxonomy, load_reviews, propose
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
    SourceAnchor,
    SourceIdentity,
    StructuralBlock,
    StructuralToken,
    StructuralUnit,
    audit_reference_topology,
    bind_catalog_facts,
    parse_grid_document,
    resolve_bounded_references,
    render_structural_tokens,
    select_traversal_limits,
    source_anchor_from_range,
    source_anchor_for_quote,
)
from .shared_mechanics import (
    REGISTRY_VERSION,
    SharedMechanicRegistry,
    load_shared_mechanic_registry,
    resolve_shared_mechanics,
)


C2_ARTIFACT_VERSION = "m6-c2-scoped-classification-1.6.0"
C2_ORACLE_VERSION = "m6-c2-independent-occurrence-oracle-1.0.0"
MANIFEST_PATH = Path("artifacts/evidence/feature_c2_evaluation_freeze.json")

OCCURRENCE_KINDS = ("effect", "dependency", "gap", "trigger", "state", "reference")
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
_RESISTANCE_PROPERTY_RE = re.compile(
    r"\b(?:physical|magic|element|attack type|type|slash|piercing|pierce|blunt)\s+resistance\b",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(?<!\w)([+-]?\s*)(\d+(?:\.\d+)?)\s*%")
_PROBABILITY_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability)\b", re.IGNORECASE)
_MULTIPLIER_RE = re.compile(
    r"\b(?:x|multiplier\s*x)\s*(\d+(?:\.\d+)?)\b|"
    r"\b(\d+(?:\.\d+)?)\s*x\b",
    re.IGNORECASE,
)
_TURN_RE = re.compile(r"\b(?:for\s+)?(\d+)\s+turns?\b", re.IGNORECASE)
_ACTIVATION_RE = re.compile(r"\b(\d+)\s+(?:times?|activations?|uses?)\b|\bonce per battle\b", re.IGNORECASE)
_ACTION_HEAD_RE = re.compile(
    r"\b(?:attacks?|deals?|inflict(?:s|ed|ing)?|appl(?:y|ies|ied|ying)|"
    r"increas(?:e|es|ed|ing)|rais(?:e|es|ed|ing)|boost(?:s|ed|ing)?|"
    r"decreas(?:e|es|ed|ing)|reduc(?:e|es|ed|ing)|lowers?|"
    r"restor(?:e|es|ed|ing)|recover(?:s|ed|ing)?|heal(?:s|ed|ing)?|"
    r"reviv(?:e|es|ed|ing)|remov(?:e|es|ed|ing)|cleans(?:e|es|ed|ing)|"
    r"grant(?:s|ed|ing)?|giv(?:e|es|en|ing)|gain(?:s|ed|ing)?|"
    r"add(?:s|ed|ing)?|consum(?:e|es|ed|ing)|spend(?:s|ing)?|"
    r"deploy(?:s|ed|ing)?|activat(?:e|es|ed|ing)|awaken(?:s|ed|ing)?|"
    r"replac(?:e|es|ed|ing)|convert(?:s|ed|ing)?|chang(?:e|es|ed|ing)|"
    r"set(?:s|ting)?|stack(?:s|ed|ing)?|tak(?:e|es|en|ing)|"
    r"cop(?:y|ies|ied|ying)|follows?\s+up|perform(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
_ATTACK_RESULT_RE = re.compile(
    r"\battack(?:s)?\s+(?:on|against|to)\s+"
    r"(?:all|each|single|a|an|one|random(?:ly selected)?|enemy|enemies|opponent|opponents)\b"
    r"(?:\s+(?:enemy|enemies|opponent|opponents))?",
    re.IGNORECASE,
)
_ATTACK_TIER_ONLY_SUFFIX_RE = re.compile(
    r"\s*\(\s*(?:XXL|XL|L|M|S|ignores\s+(?:the\s+)?target[’']s\s+defense)\s*\)\s*[.,;:]?\s*$",
    re.IGNORECASE,
)
_COMPOUND_EFFECT_START_RE = re.compile(
    r"(?:\s+and\s+|,\s*(?:and\s+)?)"
    r"(?=(?:power|intelligence|speed|luck|max(?:imum)?\s+hp)\b|"
    r"(?:(?:fire|water|wind|earth|thunder|shade|crystal|non-type)\s+type\s+)?"
    r"(?:slash|piercing|pierce|blunt|magic|physical)\s+attack\b|"
    r"(?:physical|magic|element|attack type|slash|piercing|pierce|blunt|type)\s+resistance\b|"
    r"(?:damage dealt|outgoing damage)\b|"
    r"(?:fire|water|wind|earth|thunder|shade|crystal|non-type)\s+type attack\b|"
    r"(?:(?:physical|magic)\s+)?critical rate\b|"
    r"\d+(?:\.\d+)?\s*%\s*mp\b)",
    re.IGNORECASE,
)
_NAMED_STATE_EFFECT_START_RE = re.compile(
    r"\s+(?=(?:[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})\s*:\s*"
    r"(?i:increase|increased|physical|magic|fire|water|wind|earth|thunder|shade|crystal|\+))"
)
_RESOURCE_COST_START_RE = re.compile(
    r"\s+to\s+(?:do|deal)\s+(?=(?:(?:fire|water|wind|earth|thunder|shade|crystal|non-type)\s+type\s+)?"
    r"(?:(?:slash|piercing|pierce|blunt|magic|physical)\s+)*"
    r"(?:fixed damage|damage|attack|attacks)\b)",
    re.IGNORECASE,
)
_SELF_POTENCY_STAT_LINE_RE = re.compile(
    r"^\s*[a-z][\w'-]*(?:\s+[a-z][\w'-]*){0,2}\s*:\s*"
    r"\+\s*\d+(?:\.\d+)?\s*PWR\b",
    re.IGNORECASE,
)
_BRACKET_CONDITION_RE = re.compile(
    r"\s*\[(?P<condition>(?:only\s+)?(?:if|when|unless|after|before|during|while)\b[^\]]*)\]"
    r"\s*[:,;]?\s*",
    re.IGNORECASE,
)
_LEADING_CONDITION_RE = re.compile(
    r"\s*(?P<condition>(?:only\s+)?(?:if|when|unless|after|before|during|while)\b"
    r"[^,.:]*(?:;\s*(?:only\s+)?(?:if|when|unless|after|before|during|while)\b[^,.:]*)*|"
    r"in\s+(?:[A-Z][\w'-]*(?:\s*[/,]\s*(?:or\s+)?[A-Z][\w'-]*){0,4})\s+stance)"
    r"(?:[:,;. ]\s*|\s+(?=(?:the\s+)?(?:user|skill|effect)\b))",
    re.IGNORECASE,
)
_TRAILING_CONDITION_RE = re.compile(
    r"\b(?:(?:the\s+)?skill\s+requires?|only\s+when|only\s+if|when|if|unless|provided\s+that|while|after|before|requires?|must|needs?)\b[^;]*$",
    re.IGNORECASE,
)
_ACTION_TIMING_RE = re.compile(
    r"\b(?:preemptive|charged|aura activation|battle start|"
    r"start of turn|end of turn|turn start|turn end|when used|on damage|"
    r"after each (?:attacking )?move)\b",
    re.IGNORECASE,
)
_RELATIONSHIP_GROUP_HEADER_RE = re.compile(
    r"\b(?:skills?|moves?|actions?)\s*:\s*$",
    re.IGNORECASE,
)
_HIT_COUNT_RE = re.compile(
    r"\b(?:attacks?|hits?)\b[^.;]*?\b[x×]\s*(\d+)(?!\d|\.\d)",
    re.IGNORECASE,
)
_FORMULA_RE = re.compile(
    r"\b(?:based on|depending on|according to|scales? with|increases? from)\b[^.;,]*",
    re.IGNORECASE,
)
_SKILL_DAMAGE_MULTIPLIER_RE = re.compile(
    r"\bincrease\s+skill\s+damage\s+\d+(?:\.\d+)?\s+times?\b|"
    r"\b\d+(?:\.\d+)?x\s+of\s+the\s+standard\s+skill\s+multiplier\b",
    re.IGNORECASE,
)
_STACK_MULTIPLIER_RE = re.compile(
    r"\b(?:skill\s+)?multiplier\s+increases?\s+(?:based\s+on|per)\b",
    re.IGNORECASE,
)
_CRITICAL_DAMAGE_RE = re.compile(
    r"\bcritical\s+damage\s+[+-]\s*\d+(?:\.\d+)?\s*%\b|"
    r"\bdamage\s+[+-]\s*\d+(?:\.\d+)?\s*%\s+when\s+critical\b",
    re.IGNORECASE,
)
_ELEMENT_OVERRIDE_RE = re.compile(
    r"\belement\s+type\s+changes?\s+to\s+(?:the\s+)?type\s+of\s+(?:the\s+)?deployed\s+zone\b",
    re.IGNORECASE,
)
_RESOURCE_COST_METADATA_RE = re.compile(
    r"\b(?:does\s+not|doesn't|do\s+not|don't|without)\s+"
    r"(?:consume|use|cost)\s+(?:any\s+)?(?:additional\s+)?(?:mp|magic\s+points?)\b|"
    r"\bno\s+(?:additional\s+)?(?:mp|magic\s+points?)\s+cost\b",
    re.IGNORECASE,
)
_RESOURCE_COST_RE = re.compile(
    r"\b(?:consume(?:s|d)?|spend(?:s|ing)?)\s+(\d+)\s+(charge|stacks?|mp)\b",
    re.IGNORECASE,
)
_DAMAGE_SCALING_RE = re.compile(
    r"\b(?:damage|skill multiplier)\s+increases?\s+from\s+(?:the\s+)?(?:number|amount)\b",
    re.IGNORECASE,
)
_NON_EFFECT_METADATA_RE = re.compile(
    r"^\s*(?:changes?\s+name\s+to\b|"
    r"(?:attack(?:\s+again)?|counterattack)\s+moves?\s+(?:are\s+)?each\s+counted\b|"
    r"all\s+buffs?\s+on\s+(?:the\s+)?character\s+apply\s+to\b|"
    r"buff\s+and\s+link\s+apply\s+(?:to\s+)?(?:the\s+)?main\s+and\s+reserve\b|"
    r"element\s+type\s+changes?\s+to\s+(?:the\s+)?type\s+of\s+(?:the\s+)?deployed\s+zone\b|"
    r"critical\s+damage\s+[+-]\s*\d+(?:\.\d+)?\s*%|"
    r"(?:critical\s+)?damage\s+[+-]\s*\d+(?:\.\d+)?\s*%\s+when\s+critical\b|"
    r"can\s+change\s+(?:element|weapon\s+type)\b[^.;]*|"
    r"af\s+gauge\s+charge\s+[+-]\s*\d+(?:\.\d+)?\s*%\s*,?\s*combo\s+charge\s+[+-]\s*\d+(?:\.\d+)?\s*%|"
    r"[A-Z][\w'-]*\s*:\s*[\w'-]+\s+add-on\s+attack\b|"
    r"skill\s+multiplier\s+increases?\s+per\s+[\w'-]+\s+stacked\b)",
    re.IGNORECASE,
)
_NEGATED_ACTION_RE = re.compile(
    r"\b(?:cannot|can\s+not|can't|does\s+not|doesn't|do\s+not|don't|will\s+not|won't|"
    r"would\s+not|unable\s+to)\s+"
    r"(?:deal(?:\s+with)?|perform|make|execute|increase|raise|boost|attack|inflict|apply|remove|restore|recover)\b",
    re.IGNORECASE,
)
_NEGATED_COPULAR_PREDICATE_RE = re.compile(
    r"\b(?:is|are|was|were|be|being|been)\s+(?:not|never)\b",
    re.IGNORECASE,
)
_SEQUENCE_INTERRUPTION_RE = re.compile(
    r"\b(?:unless|until)\b[^.;]*\b(?:interrupted|stopped|cancelled|canceled)\b"
    r"[^.;]*\bstatus(?:\s+(?:effect|ailment))?\b",
    re.IGNORECASE,
)
_AUTOMATIC_SEQUENCE_RE = re.compile(
    r"\bautomatically\s+(?:used|performed|continued)\s+for\s+(\d+)\s+"
    r"(?:actions?|uses?)\b",
    re.IGNORECASE,
)
_REPEATED_ACTION_BRANCH_RE = re.compile(
    r"\b(?:each|every)\s+(?:repeated\s+)?action\b", re.IGNORECASE
)
_REPLACEMENT_RE = re.compile(r"\b(?:replace|replaces|replacing|replacement|change(?:s|d)? into)\b", re.IGNORECASE)
_RESOURCE_OPERATION_RE = re.compile(
    r"\b(?:consume(?:s|d)?|spend(?:s|ing)?|use(?:s|d)?)\b[^.;]*\b(?:charge|stack|mp|resource)s?\b|"
    r"\b(?:grant(?:s|ed)?|gain(?:s|ed)?|add(?:s|ed)?|give(?:s|n)?)\b[^.;]*\b(?:charge|stack)s?\b",
    re.IGNORECASE,
)
_RESOURCE_CONSUMPTION_RE = re.compile(r"\b(?:consume(?:s|d)?|spend(?:s|ing)?)\s+(?:one|a|an|\d+)?\s*[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}\b", re.IGNORECASE)
_RESOURCE_GAIN_RE = re.compile(r"\b(?:gain(?:s|ed)?|grant(?:s|ed)?|add(?:s|ed)?|create(?:s|d)?|generate(?:s|d)?)\s+(?:one|a|an|\+?\d+)?\s*(?:charge|stacks?|pendulum|divine wolf)\b|\bstacks?\s+\+?\d+\s+[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}", re.IGNORECASE)
_NAMED_STATE_REQUIREMENT_RE = re.compile(
    r"\b(?:user|target|enemy|ally)\s+(?:has|have|possesses?|holds?)\s+"
    r"(?P<count>\d+\s+)?(?P<state>(?-i:[A-Z])[\w'-]*(?:\s+(?-i:[A-Z])[\w'-]*){0,2})",
    re.IGNORECASE,
)
_STACK_THRESHOLD_RE = re.compile(
    r"\b(?P<count>\d+)\s+(?P<state>[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})\s+"
    r"(?:are|is)\s+stacks?\b|"
    r"\b(?:the\s+)?(?:user|target|enemy|ally)\s+(?:has|have|possesses?|holds?)\s+"
    r"(?P<owned_count>\d+)\s+(?P<owned_state>[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})\b",
    re.IGNORECASE,
)
_NEGATIVE_STATUS_CONDITION_RE = re.compile(
    r"\b(?:without|lacks?|does not have|doesn't have|has no|not affected by)\b[^.;]*"
    r"\b(?:status|ailment|pain|poison|debuff|effect)\b",
    re.IGNORECASE,
)
_NEGATIVE_STATE_ABSENCE_RE = re.compile(
    r"^\s*(?:when|if|unless)\s+(?:the\s+)?(?:user|target|enemy|ally)?\s*not\s+in\b",
    re.IGNORECASE,
)
_NEGATIVE_STATE_ABSENCE_ANY_RE = re.compile(
    r"\b(?:when|if|unless)\s+(?:the\s+)?(?:user|target|enemy|ally)?\s*not\s+in\b",
    re.IGNORECASE,
)
_STACK_CREATION_RE = re.compile(
    r"\b(?i:stacks?)\s+(?:\+?\d+\s+)?[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3}"
    r"(?:\s+(?i:on|to)\s+(?i:self|user|target|enemy|ally|[A-Z][\w'-]*))?\b"
)
_ANAPHORIC_TARGET_RE = re.compile(r"\b(?:that|same|those)\s+(?:enemy|enemies|target|targets|ally|allies|recipient|character)\b", re.IGNORECASE)
_STATE_CREATION_RE = re.compile(r"\b(?:create|creates|created|summon|summons|summoned)\b[^.;]*\b(?:state|stack|stacks|status|zone|stance|barrier|shield)\b", re.IGNORECASE)
_SEQUENCE_TEXT_RE = re.compile(
    r"\b(?:sequence|automatically\s+(?:used|performed|continued)|each\s+repeated\s+action|"
    r"on\s+each\s+action|next\s+use|second\s+use|third\s+or\s+later\s+use|"
    r"perform\s+the\s+following\s+moves?\s+in\s+succession|"
    r"counted\s+as\s*\+\s*\d+\s+moves?)\b",
    re.IGNORECASE,
)
_HIT_COUNT_MODIFIER_RE = re.compile(
    r"\b(?:hit count|number of attacks|number of (?:piercing|pierce|slash|blunt|magic|physical)\s+hits?|number of hits|\d+\s+hits?)\b",
    re.IGNORECASE,
)
_MAX_STACK_METADATA_RE = re.compile(
    r"\bmax(?:imum)?\s+stacks?\s*:?\s*(?:x\s*)?(?P<value>\d+)\b",
    re.IGNORECASE,
)
_STACK_COUNT_LIST_RE = re.compile(
    r"\b(?:number\s+stacked|number\s+of\s+stacks?)\s*:\s*"
    r"\d+(?:\s*>\s*\d+)+",
    re.IGNORECASE,
)
_TYPE_ATTACK_BUFF_DOUBLING_RE = re.compile(
    r"\btype\s+attack\s+buff\s+(?:is\s+)?doubled\b[^.;]*\b(?:for|if|when|on)\b",
    re.IGNORECASE,
)
_RESULT_EFFECT_POTENCY_RE = re.compile(
    r"\b(?P<subjects>power(?:\s+and\s+speed)?|speed(?:\s+and\s+power)?)\s+"
    r"effect\s+(?:increases?|is\s+increased|raised|boosted)\b",
    re.IGNORECASE,
)
_EACH_PART_FORMULA_RE = re.compile(
    r"\badd\b[^.;]*\bto\s+(?:the\s+)?total\s+multiplier\s+of\s+each\s+part\b",
    re.IGNORECASE,
)
_RESULT_MODIFIER_RE = re.compile(
    r"\b(?:damage|potency|power)\s+(?:is\s+)?(?:increased|reduced|raised|lowered|boosted)\b[^.;]*\b(?:if|when|on|during|based on)\b|"
    + _TYPE_ATTACK_BUFF_DOUBLING_RE.pattern,
    re.IGNORECASE,
)
_EXPLICIT_RESULT_PROPERTY_RE = re.compile(
    r"\b(?:critical rate|(?:physical|magic|element|type|attack type) resistance|"
    r"equipped characters?['’]?\s+damage|damage dealt|outgoing damage|damage taken|"
    r"(?:mp|resource) consumption|power|intelligence|speed|luck)"
    r"\b[^.;]*?[+-]\s*\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)
_ZONE_DESCRIPTION_RE = re.compile(
    r"\b(?:it\s+)?(?:changes?|varies?)\s+(?:damage|damage values?|damage dealt)\b"
    r"[^.;]*\b(?:based on|according to|depending on)\b[^.;]*\b(?:zone|stance|field)\b",
    re.IGNORECASE,
)
_ZONE_PROPERTY_METADATA_RE = re.compile(
    r"\b(?:unaffected by further zone changes|zone cannot be overwritten|"
    r"zone can still be removed|after duration ends,? zone is removed|"
    r"duration cannot be extended by attempting to reactivate)",
    re.IGNORECASE,
)
_ELEMENT_CONVERSION_METADATA_RE = re.compile(
    r"(?:\b(?:element(?:\s+type)?\s+(?:changes?|converts?)\s+to|"
    r"(?:zone|stance|field)\s+(?:changes?|converts?)\s+element(?:\s+type)?\s+to)\b[^.;]*"
    r"\b(?:target|enemy|elemental weakness|weakness)\b|"
    r"\bchange\s+(?:the\s+)?element\s+of\s+(?:the\s+)?type\s+attack\s+buff\b[^.;]*\baccording to\b|"
    r"\bchange\s+(?:the\s+)?element\s+of\s+(?:the\s+)?user'?s?\s+attacks?\s+to\s+(?:the\s+)?target'?s?\s+element\b|"
    r"\bskills?\s+from\s+equipment\s+also\s+change\b)",
    re.IGNORECASE,
)
_KNOWN_STAT_CAPABILITIES = {
    "power": "power_up",
    "intelligence": "intelligence_up",
    "speed": "speed_up",
    "luck": "luck_up",
}
_KNOWN_STAT_DECREASE_CAPABILITIES = {
    "power": "power_down",
    "intelligence": "intelligence_down",
    "speed": "speed_down",
    "luck": "luck_down",
}
_TAXONOMY = load_capability_taxonomy()
_CAPABILITY_IDS = frozenset(_TAXONOMY["capabilities"])
_DEPENDENCY_IDS = frozenset(_TAXONOMY["dependencies"])
_STAT_WORD_RE = re.compile(r"\b(?:power|pwr|intelligence|speed|luck|max(?:imum)?\s+hp|max(?:imum)?\s+mp)\b", re.IGNORECASE)
_OPERATION_PATTERNS = (
    ("damage", re.compile(r"\b(?:attack|attacks|deal(?:s)?|fixed damage)\b", re.I)),
    ("restore", re.compile(r"\b(?:heal|restore|recover)\b", re.I)),
    ("apply", re.compile(r"\b(?:apply|inflict|give|grant)\b", re.I)),
    ("increase", re.compile(r"\b(?:increase|raise|up)\b|\+\s*\d", re.I)),
    ("decrease", re.compile(r"\b(?:decrease|reduce|lower|down)\b|-\s*\d", re.I)),
    ("remove", re.compile(r"\b(?:remove|clear|dispel)\b", re.I)),
    ("activate", re.compile(r"\b(?:activate|deploy|awaken)\b", re.I)),
    ("consume", re.compile(r"\bconsume(?:s|d)?\b", re.I)),
    ("require", re.compile(r"\b(?:requires?|needs?)\b", re.I)),
)
_OPERATION_BY_SEMANTIC_TYPE = {
    "action_replacement": "replace",
    "critical_support": "increase",
    "damage_event": "damage",
    "damage_mitigation": "apply",
    "damage_modifier": "increase",
    "attack_type_damage_up": "increase",
    "element_damage_increase": "increase",
    "burst_window": "replace",
    "debuff_cleansing": "remove",
    "hp_recovery": "restore",
    "hit_count_modifier": "modify",
    "link_grant": "grant",
    "multi_hit_action": "damage",
    "lunatic_activation": "activate",
    "mp_recovery": "restore",
    "resistance_increase": "increase",
    "resistance_reduction": "decrease",
    "resource_consumption": "consume",
    "resource_grant": "grant",
    "revive": "revive",
    "stat_decrease": "decrease",
    "stat_increase": "increase",
    "status_cleansing": "remove",
    "status_immunity": "apply",
    "status_infliction": "apply",
    "status_or_effect_application": "apply",
    "zone_deployment": "activate",
    "zone_awakening": "activate",
}
_DURATIONLESS_RESULT_TYPES = frozenset(
    {
        "damage_event",
        "multi_hit_action",
        "hp_recovery",
        "revive",
        "resource_consumption",
        "resource_grant",
        "state_creation",
        "lunatic_activation",
    }
)


class SemanticRole(str, Enum):
    EFFECT_RESULT = "effect_result"
    CONDITION = "condition"
    TRIGGER_TIMING = "trigger_timing"
    FORMULA = "formula"
    RESOURCE_GAIN = "resource_gain"
    RESOURCE_CONSUMPTION = "resource_consumption"
    STATE_CREATION = "state_creation"
    SEQUENCE = "sequence"
    CHILD_INVOCATION = "child_invocation"
    RELATIONSHIP_METADATA = "relationship_metadata"
    COST_ACTIVATION_METADATA = "cost_activation_metadata"
    RESULT_MODIFIER = "result_modifier"
    UNKNOWN = "unknown"


def _is_relationship_role(role: SemanticRole) -> bool:
    return role in {SemanticRole.CHILD_INVOCATION, SemanticRole.RELATIONSHIP_METADATA}


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
    text: str
    character_start: int | None = None
    character_end: int | None = None
    source_anchor: SourceAnchor | None = None

    @property
    def token_start(self) -> int:
        if self.source_anchor and self.source_anchor.token_start >= 0:
            return self.source_anchor.token_start
        return min((token.order for token in self.source_anchor.token_identities), default=-1) if self.source_anchor else -1

    @property
    def token_end(self) -> int:
        if self.source_anchor and self.source_anchor.token_end >= 0:
            return self.source_anchor.token_end
        return max((token.order for token in self.source_anchor.token_identities), default=-1) if self.source_anchor else -1


@dataclass(frozen=True)
class ClassifiedOccurrence:
    occurrence_id: str
    occurrence_kind: str
    operation: str
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
    sequence_metadata: Mapping[str, str] = field(default_factory=dict)
    resource_metadata: Mapping[str, str] = field(default_factory=dict)
    result_modifiers: Mapping[str, Any] = field(default_factory=dict)
    action_timing: str = ""
    semantic_subject: str = ""
    condition_source_span: SourceSpan | None = None
    timing_source_span: SourceSpan | None = None
    probability: Mapping[str, str] = field(default_factory=dict)
    recipient_name: str = ""
    semantic_role: str = SemanticRole.UNKNOWN.value
    source_owner_id: str = ""
    branch_context: tuple[str, ...] = ()
    action_owner_id: str = ""
    coordinated_result_group_id: str = ""
    modifier_source_spans: tuple[SourceSpan, ...] = ()
    gap_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClassifiedRelationship:
    relationship_id: str
    source_fact_id: str
    source_owner: str
    source_owner_id: str
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
    semantic_role: str = ""

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
    action_start: int | None = None
    action_end: int | None = None
    conjunction_before: str = ""
    coordinated_result_group_id: str = ""
    shared_modifier_text: str = ""
    shared_modifier_start: int | None = None
    shared_modifier_end: int | None = None


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
    modifier_span: SourceSpan | None = None
    semantic_role: SemanticRole = SemanticRole.UNKNOWN
    owner_id: str = ""
    action_owner_id: str = ""
    branch_context: tuple[str, ...] = ()


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
    if _SELF_POTENCY_STAT_LINE_RE.search(text):
        return "self"
    if re.search(r"\bequipped characters?\b", lowered):
        return "ally"
    if re.search(r"\b(?:to|for)\s+(?:the\s+)?user\b|\buser's\b", lowered):
        return "self"
    if re.search(r"\b(?:enemy|enemies|boss|opponent)\b", lowered):
        return "enemy"
    if re.search(r"\b(?:inflict|apply)\b[^.;]*\brage\b", lowered) or re.search(
        r"\bresistance\s*-\s*\d", lowered
    ):
        return "enemy"
    if re.search(r"\b(?:remove|removes|removing|cleanse|cleanses|cleansing)\b[^.;]*\bdebuffs?\b", lowered):
        return "self"
    if re.search(r"\b(?:ally|allies|party|party members|frontline)\b", lowered):
        return "ally"
    if re.search(r"\bis at front\b|\bis on the frontline\b", lowered):
        return "ally"
    if re.search(r"\b(?:user|self|own)\b", lowered):
        return "self"
    if re.search(r"\b(?:restore|restores|recover|recovers|heal|heals)\b[^.;]*\b(?:mp|hp|health|magic points?)\b", lowered):
        return "self"
    if _STAT_WORD_RE.search(text) and re.search(
        r"\b(?:increase|increases|raise|raises|boost|boosts)\b|\+\s*\d",
        text,
        re.IGNORECASE,
    ):
        return "self"
    if re.search(r"\bcritical rate\b", text, re.IGNORECASE) and re.search(
        r"\b(?:increase|increases|raise|raises|boost|boosts)\b|\+\s*\d",
        text,
        re.IGNORECASE,
    ):
        return "self"
    if re.search(r"\b(?:zone|stance|field)\b", lowered):
        return "field"
    return "unknown"


def _recipient_and_cardinality(text: str) -> tuple[str, str]:
    lowered = _key(text)
    if _SELF_POTENCY_STAT_LINE_RE.search(text):
        return "self", "single"
    equipped_weapons = re.search(
        r"\b((?:sword|axe|katana)(?:\s*[,/]\s*(?:sword|axe|katana))*)\s+equipped\s+characters?\b",
        lowered,
    )
    if equipped_weapons:
        weapons = [part.strip().title() for part in re.split(r"\s*[,/]\s*", equipped_weapons.group(1))]
        weapon_list = ", ".join(weapons[:-1]) + (f", or {weapons[-1]}" if len(weapons) > 1 else weapons[0])
        return f"characters equipped with {weapon_list}", "multiple"
    if re.search(r"\bequipped characters?\b", lowered):
        return "equipped_characters", "multiple"
    if re.search(r"\b(?:to|for)\s+(?:the\s+)?user\b|\buser's\b", lowered):
        return "self", "single"
    if re.search(r"\brandom(?:ly selected)? enemies\b", lowered):
        return "random_enemies", "multiple"
    if re.search(r"\b(?:deploy(?:s|ed|ing)?\b[^.;]*\b(?:zone|stance)|zone|stance)\b", lowered):
        return "zone", "single"
    if re.search(r"\b(?:an ally\b[^.;]*\bon the front ?line|[\w'-]+\s+is on the frontline)\b", lowered):
        return "frontline", "single"
    named_front = re.search(
        r"\b(?!(?i:when|if|while|after|before)\b)([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)\s+is at front\b",
        text,
    )
    if named_front:
        return named_front.group(1), "single"
    if re.search(r"\b(?:all enemies|each enemy|all opponents)\b", lowered):
        return "all_enemies", "multiple"
    if re.search(r"\b(?:a single enemy|single enemy|one enemy)\b", lowered):
        return "single_enemy", "single"
    if re.search(
        r"\b(?:all party members|party members|the party|all allies|all ally|party and reserve members)\b",
        lowered,
    ):
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


def _recipient_context(text: str) -> str:
    """Remove prerequisite clauses before inheriting a shared result target."""
    return re.sub(
        r"\b(?:only\s+when|if|when|unless)\b[^,;:.]*[:,;:.]?\s*",
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _shared_attack_target(text: str) -> str:
    """Return a unique attack target shared by coordinated result clauses."""
    if not re.search(r"\battack\b[^.;]*\b(?:and|then)\b", text, re.IGNORECASE):
        return ""
    target_patterns = (
        r"\ball enemies\b",
        r"\beach enemy\b",
        r"\ball opponents\b",
        r"\brandom enemies\b",
        r"\ba single enemy\b",
        r"\bsingle enemy\b",
        r"\bone enemy\b",
    )
    matches = [
        (match.group(0), _recipient_and_cardinality(match.group(0))[0])
        for pattern in target_patterns
        for match in re.finditer(pattern, text, re.IGNORECASE)
    ]
    recipients = {recipient for _text, recipient in matches}
    if len(recipients) != 1:
        return ""
    return max((value for value, _recipient in matches), key=len)


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
    if re.search(r"\bstatuses?\b[^.;]*\bend(?:s|ed)?\s+after\b", lowered):
        return ""
    if re.search(r"\breceives?\b[^.;]*\bdamage\b", lowered):
        return "on_damage"
    if re.search(r"\b(?:when used\s+(?:in|during|durring)|when in|durr?ing)\s+stellar burst\b", lowered):
        return "on_stellar_burst"
    if re.search(r"\bafter\s+each\s+(?:attacking\s+)?move\b", lowered):
        return "after_each_attacking_move"
    for phrase, value in (
        ("preemptive", "preemptive"),
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
    max_stacks = _MAX_STACK_METADATA_RE.search(text)
    result_text = _MAX_STACK_METADATA_RE.sub(" ", text)
    state_stat = re.search(
        r"^\s*[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}\s*:\s*"
        r"(?P<value>[+-]?\s*\d+(?:\.\d+)?)\s*(?P<stat>PWR|Power|Intelligence|Speed|Luck)\b",
        result_text,
        re.IGNORECASE,
    )
    if state_stat:
        value = re.sub(r"\s+", "", state_stat.group("value")).lstrip("+")
        result = {
            "value": value,
            "unit": "flat",
            "raw": _clean(state_stat.group(0)),
        }
        if max_stacks:
            result["max_stacks"] = max_stacks.group("value")
        return result

    move_values = list(_PERCENT_RE.finditer(text))
    if (
        len(move_values) > 1
        and re.search(r"\btype\s+attack\b", text, re.IGNORECASE)
        and re.search(r"\\|/", text)
        and re.search(r"\bmoves?\b", text, re.IGNORECASE)
    ):
        return {
            "move_count_to_percent": {
                str(index): f"{match.group(2)}%"
                for index, match in enumerate(move_values, start=1)
            }
        }
    percent = _PERCENT_RE.search(result_text)
    probability = _PROBABILITY_RE.search(result_text)
    hit_count_match = _HIT_COUNT_RE.search(text)
    hit_count = hit_count_match.group(1) if hit_count_match else ""
    multiplier = next(
        (
            match
            for match in _MULTIPLIER_RE.finditer(result_text)
            if not hit_count_match
            or match.end() <= hit_count_match.start()
            or match.start() >= hit_count_match.end()
        ),
        None,
    )
    tier = re.search(r"\b(XXL|XL|L|M|S)\b", result_text, re.IGNORECASE)
    maximum_total = re.search(
        r"\bmax(?:imum)?\s+total\s*:?\s*([+-]?\d+(?:\.\d+)?\s*%)|"
        r"\bmax(?:imum)?\s+stack\b[^.;]*?(-\s*\d+(?:\.\d+)?\s*%)",
        text,
        re.IGNORECASE,
    )
    pwr_per_stack = re.search(r"\b([+-]?\d+(?:\.\d+)?)\s+PWR\s+per\s+stack\b", text, re.IGNORECASE)
    if pwr_per_stack:
        result = {"value": pwr_per_stack.group(1), "unit": "PWR_per_stack"}
        if max_stacks:
            result["max_stacks"] = max_stacks.group("value")
        if maximum_total:
            total = next(value for value in maximum_total.groups() if value)
            result["maximum_total"] = _clean(total).lstrip("- ")
        return result
    if percent and (not probability or percent.start(2) != probability.start()):
        sign = percent.group(1).strip()
        value = percent.group(2)
        if re.search(r"\bper\s+stack\b", text, re.IGNORECASE) or max_stacks:
            result = {"value": value, "unit": "percent_per_stack"}
            if max_stacks:
                result["max_stacks"] = max_stacks.group("value")
            if maximum_total:
                total = next(value for value in maximum_total.groups() if value)
                result["maximum_total"] = _clean(total).lstrip("- ")
            return result
        return {"value": value, "unit": "percent", "raw": f"{sign}{value}%"}
    if multiplier and not hit_count and not tier:
        return {"value": next(value for value in multiplier.groups() if value), "unit": "multiplier", "raw": multiplier.group(0)}
    count = re.search(
        r"\b(?:hit count|number of hits|skill hits?)\b[^.;]*?\b(?:by|to)\s+(\d+)\b",
        text,
        re.IGNORECASE,
    )
    if count:
        return {"value": count.group(1), "unit": "count", "raw": count.group(0)}
    if hit_count or tier:
        result = {}
        if hit_count:
            result["hit_count"] = hit_count
        if tier:
            result["tier"] = tier.group(1).upper()
        if multiplier:
            result["multiplier"] = next(value for value in multiplier.groups() if value)
        return result
    fixed_mp_hp_restore = re.search(
        r"\b(?:restore|recover|heal)\b[^.;]*?\b(?:mp|hp|health|magic points?)\b\s*"
        r"([+-]?\s*\d+(?:\.\d+)?)\b",
        result_text,
        re.IGNORECASE,
    )
    if fixed_mp_hp_restore:
        value = re.sub(r"\s+", "", fixed_mp_hp_restore.group(1)).lstrip("+")
        unit = "flat_mp" if re.search(r"\b(?:mp|magic points?)\b", fixed_mp_hp_restore.group(0), re.IGNORECASE) else "flat"
        result = {"value": value, "unit": unit, "raw": fixed_mp_hp_restore.group(1)}
        if max_stacks:
            result["max_stacks"] = max_stacks.group("value")
        return result
    fixed = re.search(r"\b(?:deal|damage|restore|recover|heal)\s+(\d{3,})\b", result_text, re.IGNORECASE)
    if fixed:
        unit = "flat_mp" if re.search(r"\b(?:mp|magic points?)\b", result_text, re.IGNORECASE) else "flat"
        result = {"value": fixed.group(1), "unit": unit, "raw": fixed.group(0)}
        if max_stacks:
            result["max_stacks"] = max_stacks.group("value")
        return result
    if max_stacks:
        return {"max_stacks": max_stacks.group("value")}
    return {}


def _probability(text: str) -> dict[str, str]:
    match = _PROBABILITY_RE.search(text)
    if not match:
        return {}
    return {"value": match.group(1), "unit": "percent", "raw": match.group(0)}


def _duration_activation(text: str) -> dict[str, str]:
    duration = _TURN_RE.search(text)
    move_duration = re.search(r"\b(?:for\s+)?(\d+)\s+moves?\b", text, re.IGNORECASE)
    activation = _ACTIVATION_RE.search(text)
    result: dict[str, str] = {}
    if duration:
        result["duration_turns"] = duration.group(1)
    if move_duration:
        result["duration_moves"] = move_duration.group(1)
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


def _stance_dependent_attack_type(
    text: str,
    blocks: Sequence[StructuralBlock],
) -> tuple[str, str]:
    source_text = " ".join(" ".join(token.text for token in block.tokens) for block in blocks)
    formula = re.search(
        r"\bdamage\s+type\s+is\s+according\s+to\s+active\s+stance\b",
        source_text,
        re.IGNORECASE,
    )
    if not formula:
        return "", ""
    alternatives = re.search(
        r"\b(slash(?:\s*/\s*(?:pierce|piercing|blunt|magic))+)\s+attack\b",
        text,
        re.IGNORECASE,
    )
    if not alternatives:
        return "", ""
    attack_types = [
        "Pierce" if part.casefold() in {"pierce", "piercing"} else part.title()
        for part in re.split(r"\s*/\s*", alternatives.group(1))
    ]
    default = re.search(
        r"\b(slash|pierce|piercing|blunt|magic)\s+without\s+active\s+stance\b",
        source_text,
        re.IGNORECASE,
    )
    value = "stance_dependent:" + "|".join(dict.fromkeys(attack_types))
    if default:
        default_type = "Pierce" if default.group(1).casefold() in {"pierce", "piercing"} else default.group(1).title()
        value += f"; default {default_type}"
    return value, _clean(formula.group(0))


def _hit_count(text: str) -> str:
    for pattern in (
        r"\b(?:attacks?|hits?)\b[^.;]*?\b[x×]\s*(\d+)(?!\d|\.\d)",
        r"\b(?:attacks?|hits?)\b[^.;()]*?\b(\d+)\s+times?\b",
        r"\b(\d+)\s+hits?\b",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _formula_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    match = _FORMULA_RE.search(text)
    if match:
        metadata["raw"] = _clean(match.group(0))
    if _SKILL_DAMAGE_MULTIPLIER_RE.search(text):
        metadata["skill_damage_multiplier"] = _clean(text)
    if _STACK_MULTIPLIER_RE.search(text):
        metadata["stack_scaling"] = _clean(text)
    if _DAMAGE_SCALING_RE.search(text):
        metadata["damage_scaling"] = _clean(text)
    if _CRITICAL_DAMAGE_RE.search(text):
        metadata["critical_damage_modifier"] = _clean(text)
    if _ELEMENT_OVERRIDE_RE.search(text):
        metadata["element_override"] = _clean(text)
    if re.search(r"\bcan\s+change\s+(?:element|weapon\s+type)\b", text, re.IGNORECASE):
        metadata["attack_type_element_override"] = _clean(text)
    if re.search(
        r"\b(?:non-type|fire|water|wind|earth|thunder|shade|crystal)\s+attacks?\s+become\s+"
        r"(?:elemental|[a-z]+(?:-type)?)\b",
        text,
        re.IGNORECASE,
    ):
        metadata["attack_type_element_override"] = _clean(text)
    if re.search(r"\baf\s+gauge\s+charge\b[^.;]*\bcombo\s+charge\b", text, re.IGNORECASE):
        metadata["fixed_link_resource_charge"] = _clean(text)
    if not re.search(
        r"\bequipped characters?['’]?\s+damage\b[^.;]*[+-]\s*\d",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"\b(?:increased\s+damage\s+based\s+on|debuff\s+amount\s+increases?\s+from|"
        r"buff\s+amount\s+increases?\s+from|"
        r"damage\s+[+-]\s*\d+(?:\.\d+)?\s*%|counted\s+twice)(?=\W|$)",
        text,
        re.IGNORECASE,
    ) or _STACK_COUNT_LIST_RE.search(text) or _EACH_PART_FORMULA_RE.search(text):
        metadata["result_scaling_note"] = _clean(text)
    return metadata


def _formula_tier_magnitude(formula_text: str, effect_text: str) -> dict[str, Any]:
    tiers = re.search(
        r"\b(?:effect|buff|damage)(?:'s)?\s+power\s+is\s+based\s+on\s+number\s*"
        r"\(\s*(?P<tiers>\d+(?:\s*[/\\,]\s*\d+)+)\s*\)\s+of\s+"
        r"(?P<category>[\w'-]+(?:\s+[\w'-]+)?)\s+moves?\s+used\b",
        formula_text,
        re.IGNORECASE,
    )
    if not tiers:
        return {}
    numbers = re.findall(r"\d+", tiers.group("tiers"))
    percentages = list(_PERCENT_RE.finditer(effect_text))
    if not numbers or len(numbers) != len(percentages):
        return {}
    category = re.sub(r"[^a-z0-9]+", "_", tiers.group("category").casefold()).strip("_")
    values = {
        number: f"{percentage.group(2)}%"
        for number, percentage in zip(numbers, percentages, strict=True)
    }
    return {f"by_{category}_moves_used": values}


def _resource_metadata(text: str) -> dict[str, str]:
    match = _RESOURCE_COST_RE.search(text)
    if not match:
        return {}
    resource = match.group(2).casefold()
    key = {"stack": "stack_cost", "stacks": "stack_cost", "charge": "charge_cost", "mp": "mp_cost"}[resource]
    return {key: match.group(1)}


def _sequence_metadata(unit: StructuralUnit) -> tuple[dict[str, str], tuple[str, ...]]:
    """Retain automatic sequence resource and interruption scope on its repeated-action branch."""
    sequence_header = next(
        (
            " ".join(token.text for token in block.tokens)
            for block in unit.blocks
            if _AUTOMATIC_SEQUENCE_RE.search(" ".join(token.text for token in block.tokens))
        ),
        "",
    )
    action_branch = next(
        (
            tuple(block.ancestry)
            for block in unit.blocks
            if _REPEATED_ACTION_BRANCH_RE.search(" ".join(token.text for token in block.tokens))
        ),
        (),
    )
    if not sequence_header:
        return {}, ()

    match = _AUTOMATIC_SEQUENCE_RE.search(sequence_header)
    metadata = {"mode": "automatic_continuation"}
    if match:
        metadata["action_count"] = match.group(1)
    if _RESOURCE_COST_METADATA_RE.search(sequence_header):
        metadata["manual_activation_mp_cost"] = "normal_skill_cost_applies"
        metadata["automatic_continuation_mp_cost"] = "no_additional_mp"
    interruption = _SEQUENCE_INTERRUPTION_RE.search(sequence_header)
    if interruption:
        metadata["interruption"] = _clean(interruption.group(0))
    return metadata, action_branch


def _is_formula_explanation(text: str) -> bool:
    lowered = _key(text)
    if re.search(
        r"\bequipped characters?['’]?\s+damage\b[^.;]*[+-]\s*\d",
        text,
        re.IGNORECASE,
    ):
        return False
    multiplier_note = _SKILL_DAMAGE_MULTIPLIER_RE.search(text)
    if multiplier_note and not _ACTION_HEAD_RE.search(text[:multiplier_note.start()]):
        return True
    if re.search(r"\b(?:damage|skill multiplier)\s*[:=]", lowered):
        return True
    if re.search(r"\bskill multiplier\s+[+-]\s*\d+(?:\.\d+)?\s*%", lowered):
        return True
    if _formula_metadata(text) and re.search(r"\b(?:skill )?multiplier\b", lowered):
        return True
    if _STACK_MULTIPLIER_RE.search(text):
        return True
    if _DAMAGE_SCALING_RE.search(text):
        return True
    if re.search(
        r"\b(?:increased\s+damage\s+based\s+on|debuff\s+amount\s+increases?\s+from|"
        r"buff\s+amount\s+increases?\s+from|"
        r"damage\s+[+-]\s*\d+(?:\.\d+)?\s*%|counted\s+twice)(?=\W|$)",
        text,
        re.IGNORECASE,
    ) or _STACK_COUNT_LIST_RE.search(text) or _EACH_PART_FORMULA_RE.search(text):
        return True
    return bool(
        re.search(r"\badd\b[^.;]*\b(?:light|shadow)\b[^.;]*\bbase multiplier\b", lowered)
    )


def _semantic_role(
    atom: _SourceAtom,
    references: Sequence[StructuralToken],
    *,
    shared_definition_source: bool,
) -> SemanticRole:
    text = atom.effect_text or atom.text
    if (
        _ZONE_DESCRIPTION_RE.search(text)
        or _ZONE_PROPERTY_METADATA_RE.search(text)
        or _ELEMENT_CONVERSION_METADATA_RE.search(text)
    ):
        return SemanticRole.RELATIONSHIP_METADATA
    attack_result = _ATTACK_RESULT_RE.search(text)
    formula_start = min(
        (
            match.start()
            for pattern in (_SKILL_DAMAGE_MULTIPLIER_RE, _STACK_MULTIPLIER_RE, _FORMULA_RE)
            if (match := pattern.search(text)) is not None
        ),
        default=len(text),
    )
    attack_precedes_formula = bool(attack_result and attack_result.end() <= formula_start)
    if (
        _is_formula_explanation(text) and not attack_precedes_formula
    ) or (
        _formula_metadata(text)
        and not _ACTION_HEAD_RE.search(text)
        and not attack_result
    ):
        return SemanticRole.FORMULA
    modifier_text = f"{text} {atom.condition}".strip()
    if (
        _HIT_COUNT_MODIFIER_RE.search(modifier_text)
        or _RESULT_MODIFIER_RE.search(modifier_text)
        or _RESULT_EFFECT_POTENCY_RE.search(modifier_text)
        or re.search(
            r"\b(?:intelligence|critical rate)\s+(?:and\s+\w+\s+)?effect\s+"
            r"(?:increases?|is increased|raised|boosted)\b",
            modifier_text,
            re.IGNORECASE,
        )
    ):
        return SemanticRole.RESULT_MODIFIER
    max_stack_metadata = _MAX_STACK_METADATA_RE.search(text)
    stack_free_text = _MAX_STACK_METADATA_RE.sub(" ", text)
    if (
        max_stack_metadata
        and not _ACTION_HEAD_RE.search(stack_free_text)
        and not _ATTACK_RESULT_RE.search(stack_free_text)
        and not _SELF_POTENCY_STAT_LINE_RE.search(stack_free_text)
        and not _EXPLICIT_RESULT_PROPERTY_RE.search(stack_free_text)
    ):
        return SemanticRole.RESULT_MODIFIER
    explicit_child_relation = bool(
        references
        and not re.search(r"\bin\s+link\b", text, re.IGNORECASE)
        and any(
            _relationship_operation(text, token.text) in {"activates", "replaces", "branches_to"}
            for token in references
        )
    )
    relationship_group_header = bool(
        references
        and re.search(r"\b(?:skills?|moves?|actions?)\s*:\s*$", text, re.IGNORECASE)
        and any(_relationship_operation(text, token.text) in {"activates", "replaces", "branches_to"} for token in references)
    )
    if references and (
        explicit_child_relation
        or relationship_group_header
        or _SEQUENCE_TEXT_RE.search(text)
    ):
        return SemanticRole.CHILD_INVOCATION
    if _SEQUENCE_TEXT_RE.search(text) or _SEQUENCE_INTERRUPTION_RE.search(text):
        return SemanticRole.SEQUENCE
    if _RESOURCE_CONSUMPTION_RE.search(text) or re.search(r"\b(?:consume|spend)\b[^.;]*\b(?:charge|stacks?|mp|resource)\b", text, re.IGNORECASE):
        return SemanticRole.RESOURCE_CONSUMPTION
    if _STACK_CREATION_RE.search(text) or _STATE_CREATION_RE.search(text):
        return SemanticRole.STATE_CREATION
    if _RESOURCE_GAIN_RE.search(text) or (
        _RESOURCE_OPERATION_RE.search(text)
        and re.search(r"\b(?:grant|gain|add|create|generate|stack)\b", text, re.IGNORECASE)
    ):
        return SemanticRole.RESOURCE_GAIN
    if _CRITICAL_DAMAGE_RE.search(text) or re.search(
        r"\b(?:reduce|reduces|reduced|decrease|decreases|decreased)\s+(?:mp|resource) consumption\b|"
        r"\b(?:mp|resource) consumption\b[^.;]*[+-]\s*\d+(?:\.\d+)?\s*%?",
        text,
        re.IGNORECASE,
    ):
        return SemanticRole.COST_ACTIVATION_METADATA

    has_effect_result = bool(
        re.search(
            r"\bequipped characters?['’]?\s+damage\b[^.;]*[+-]\s*\d",
            text,
            re.IGNORECASE,
        )
        or re.search(r"\b(?:can\s+)?use\b[^.;]*\bagain\b", text, re.IGNORECASE)
        or _SELF_POTENCY_STAT_LINE_RE.search(text)
        or re.match(r"\s*\d+(?:\.\d+)?\s*%\s*mp\b", text, re.IGNORECASE)
        or _ACTION_HEAD_RE.search(text)
        or attack_result
        or _EXPLICIT_RESULT_PROPERTY_RE.search(text)
        or (
            _COORDINATED_RESULT_SUBJECT_RE.search(text)
            and (
                _COORDINATED_RESULT_VALUE_RE.search(text)
                or re.search(r"\b(?:increase|increases|raise|raises|boost|boosts)\b", text, re.IGNORECASE)
            )
        )
    )
    if _NON_EFFECT_METADATA_RE.match(text) or _NEGATED_ACTION_RE.search(text) or _NEGATED_COPULAR_PREDICATE_RE.search(text):
        has_effect_result = False
    if re.match(r"\s*(?:requires?|needs?|must)\b", text, re.IGNORECASE):
        return SemanticRole.CONDITION
    if atom.action_timing and not has_effect_result:
        return SemanticRole.TRIGGER_TIMING
    if atom.condition and not atom.effect_text:
        return SemanticRole.CONDITION
    if atom.condition and not has_effect_result:
        return SemanticRole.CONDITION
    if has_effect_result:
        return SemanticRole.EFFECT_RESULT
    if references and shared_definition_source:
        return SemanticRole.RELATIONSHIP_METADATA
    if atom.action_timing:
        return SemanticRole.TRIGGER_TIMING
    if atom.condition:
        return SemanticRole.CONDITION
    return SemanticRole.UNKNOWN


def _semantic_outputs(
    role: SemanticRole,
    text: str,
    direction: str,
    context_text: str = "",
    coordinated_context_text: str = "",
) -> list[tuple[str, str, str]]:
    stellar_replacement = bool(
        role == SemanticRole.CHILD_INVOCATION
        and re.search(r"\bwhen used in stellar burst\b", text, re.IGNORECASE)
        and re.search(r"\bperform\b[^.;]*\binstead\b", text, re.IGNORECASE)
    )
    if role == SemanticRole.EFFECT_RESULT or stellar_replacement:
        return _effect_semantics(
            text,
            direction,
            context_text or text,
            coordinated_context_text,
        )
    if role == SemanticRole.RESOURCE_CONSUMPTION:
        return [("resource_consumption", "", _resource_subject(text))]
    if role == SemanticRole.RESOURCE_GAIN:
        return [("resource_grant", "", _resource_subject(text))]
    if role == SemanticRole.STATE_CREATION:
        return [("state_creation", "", _resource_subject(text))]
    if role == SemanticRole.COST_ACTIVATION_METADATA:
        return [("unsupported_cost_modifier", "", "mp_consumption")]
    return []


def _is_prerequisite(text: str) -> bool:
    lowered = _key(text)
    if not lowered or re.search(r"\bif explicitly stated\b", lowered):
        return False
    if _SEQUENCE_INTERRUPTION_RE.search(text):
        return False
    if re.search(r"\b(?:receives?\b[^.;]*\bdamage|used (?:during|in))\b", lowered):
        return False
    if re.match(r"\s*(?:after|before|during|while|until)\b", lowered):
        return False
    if re.match(r"\s*in\s+(?:[\w'-]+\s*[/,]\s*)*[\w'-]+\s+stance\b", lowered):
        return True
    if _NAMED_STATE_REQUIREMENT_RE.search(text):
        return True
    return bool(
        re.match(r"\s*(?:(?:the\s+)?skill\s+requires?|if|unless|only when|only if|when|requires?|needs?|must)\b", lowered)
        or re.search(r"\b(?:once per battle|only once per character|limited uses?)\b", lowered)
    )


def _effect_semantics(
    text: str,
    direction: str,
    context_text: str = "",
    coordinated_context_text: str = "",
) -> list[tuple[str, str, str]]:
    lowered = _key(text)
    if _RESOURCE_COST_METADATA_RE.search(text):
        without_cost_note = _RESOURCE_COST_METADATA_RE.sub(" ", text)
        if not _ACTION_HEAD_RE.search(without_cost_note) and not _EFFECT_RE.search(without_cost_note):
            return []
        lowered = _key(without_cost_note)
    if re.search(r"\bwhen used in stellar burst\b[^.;]*\bperform\b[^.;]*\binstead\b", lowered):
        return [("burst_window", "burst_window", "stellar_burst")]
    if re.search(r"\b(?:grant|grants|apply|applies)\s+kaleido\b", lowered):
        return [("status_or_effect_application", "apply_kaleido", "kaleido")]
    if re.search(r"\b(?:activate|activates|activated|activating)\s+lunatic\b", lowered):
        return [("lunatic_activation", "activate_lunatic", "lunatic")]
    if re.search(r"\bbarrier\s+pierc(?:e|ing)\b|\bpierc(?:e|es)\s+barriers?\b", lowered):
        return [("status_or_effect_application", "barrier_pierce", "barrier_pierce")]
    if re.search(r"\b(?:activate|activates|activated|activating)\b[^.;]*\bin\s+link\b", lowered):
        return [("link_grant", "grant_link", "link")]
    enemy_context = direction == "enemy" or bool(
        re.search(r"\b(?:enemy|enemies|opponent|opponents)\b", context_text, re.IGNORECASE)
    )
    if enemy_context and (
        re.search(r"\bdispel(?:s|led|ling)?\b[^.;]*\bbuffs?\b", lowered)
        or re.search(r"\bremove(?:s|d|ing)?\b[^.;]*\bbuffs?\b[^.;]*\b(?:enemies|target)\b", lowered)
    ):
        return [("debuff_cleansing", "enemy_buff_dispel", "buffs")]
    if _REPLACEMENT_RE.search(lowered) and re.search(
        r"\b(?:skill|action|slot|move|basic attack)\b", lowered
    ):
        return [("action_replacement", "", "skill_action")]
    if re.search(r"\b(?:hit count|number of hits|number of attacks|skill hits?)\b", lowered):
        return [("hit_count_modifier", "multi_hit_action", "hit_count")]
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
    if direction in {"ally", "self"} and re.search(
        r"\brestore\s+(?:all\s+)?statuses\b", lowered
    ):
        return [("status_cleansing", "remove_status_ailment", "status_ailment")]
    if re.search(r"\b(?:heal|heals|healing|restore|restores|recover|recovers)\b", lowered):
        if re.search(r"\b(?:mp|magic points?)\b", lowered):
            capability = "recover_mp" if direction in {"ally", "self"} else ""
            return [("mp_recovery", capability, "mp")]
        if re.search(r"\b(?:hp|health points?)\b", lowered) or re.search(r"\bheal(?:s|ing)?\b", lowered):
            capability = "heal_hp" if direction in {"ally", "self"} else ""
            return [("hp_recovery", capability, "hp")]
    if direction in {"ally", "self"} and re.search(r"^\s*\d+(?:\.\d+)?\s*%\s*mp\b", lowered):
        return [("mp_recovery", "recover_mp", "mp")]
    if direction in {"ally", "self"} and re.search(r"\b(?:give|grant|apply)\b[^.;]*\blink\b", lowered):
        return [("link_grant", "grant_link", "link")]
    if direction in {"ally", "self"} and re.search(r"\b(?:give|grant|apply)\b[^.;]*\bshield\b", lowered):
        return [("damage_mitigation", "shield", "shield")]
    if direction in {"ally", "self"} and re.search(
        r"\b(?:give|gives|grant|grants|granted|apply|applies|applied)\b[^.;]*\bhold ground\b",
        lowered,
    ):
        return [("status_or_effect_application", "hold_ground", "hold_ground")]
    if re.search(r"\b(?:inflict|inflicts|apply|applies|grant|grants)\b", lowered):
        if re.search(r"\belemental\s+break\b", lowered):
            return [("status_infliction", "inflict_break", "break")]
        if direction == "enemy":
            for status, capability in (
                ("rage", "taunt"),
                ("pain", "inflict_pain"),
                ("poison", "inflict_poison"),
                ("break", "inflict_break"),
            ):
                if re.search(rf"\b{status}\b", lowered):
                    return [("status_infliction", capability, status)]
        if direction in {"ally", "self"} and re.search(r"\bstatus immunity\b", lowered):
            return [("status_immunity", "grant_status_immunity", "status_ailment")]
        return [("status_or_effect_application", "", "unknown_status_or_target")]
    if re.search(
        r"\bdeploy(?:s|ing)?\s+(?:(?:a|an|the)\s+)?"
        r"(?:[a-z][\w'-]*\s+){0,3}(?:zone|stance)\b",
        lowered,
    ):
        return [("zone_deployment", "deploy_zone", "zone")]
    if re.search(r"\b(?:awaken|awakens|awakened|awakening)\b[^.;]*\bzone\b", lowered):
        return [("zone_awakening", "awaken_zone", "zone")]
    if re.search(r"\bresistance\b", lowered) and (
        direction == "enemy"
        or re.search(r"(?:decrease|decreases|reduce|reduces|lower|lowers|down)|-\s*\d", lowered)
    ):
        if direction not in {"ally", "self"}:
            for property_name, capability in (
                ("physical", "physical_resistance_down"),
                ("magic", "magic_resistance_down"),
                ("element", "element_resistance_down"),
                ("attack type", "attack_type_resistance_down"),
                ("slash", "attack_type_resistance_down"),
                ("piercing", "attack_type_resistance_down"),
                ("pierce", "attack_type_resistance_down"),
                ("blunt", "attack_type_resistance_down"),
            ):
                if property_name in lowered:
                    return [("resistance_reduction", capability, property_name.replace(" ", "_"))]
            return [("resistance_reduction", "enemy_resistance_down", "resistance")]
    if direction in {"ally", "self"} and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts)\b[^.;]*\bresistance\b|\bresistance\b[^.;]*\+\s*\d", lowered):
        return [("resistance_increase", "ally_resistance_up", "resistance")]
    if direction in {"ally", "self"} and re.search(r"\b(?:damage reduction|reduce damage (?:taken|received)|damage taken)\b", lowered):
        return [("damage_mitigation", "damage_reduction", "damage_received")]
    if direction in {"ally", "self"} and re.search(r"\bbarrier\b", lowered):
        return [("damage_mitigation", "damage_reduction_barrier", "barrier")]
    if direction in {"ally", "self"} and re.search(r"\bshield\b", lowered):
        return [("damage_mitigation", "shield", "shield")]
    if re.search(r"\bcritical rate\b", lowered) and (
        re.search(r"\b(?:increase|increases|raise|raises|boost|boosts)\b", lowered)
        or re.search(r"[+]\s*\d", lowered)
    ):
        if direction in {"ally", "self"}:
            if "magic" in lowered:
                return [("critical_support", "magic_critical_rate_up", "magic_critical_rate")]
            if "physical" in lowered:
                return [("critical_support", "physical_critical_rate_up", "physical_critical_rate")]
            if re.search(r"\bmagic\s+critical rate\b", context_text, re.IGNORECASE):
                return [("critical_support", "physical_critical_rate_up", "physical_critical_rate")]
            if re.search(r"\bmagic\s+critical rate\b", coordinated_context_text, re.IGNORECASE):
                return [("critical_support", "physical_critical_rate_up", "physical_critical_rate")]
            return [("critical_support", "", "untyped_critical_rate")]
    if direction in {"ally", "self"} and re.search(
        r"\b(?:fire|water|wind|earth|thunder|shade|crystal|non-type)\s+type attack\s+of\s+"
        r"(?:the\s+)?(?:user|self|all\s+party members|party members|allies)\b",
        lowered,
    ) and (re.search(r"[+-]\s*\d", lowered) or _PERCENT_RE.search(text)):
        return [("element_damage_increase", "element_damage_up", "element_damage")]
    if direction in {"ally", "self"} and re.search(
        r"\btype\s+attack\b[^.;]*?(?:[+-]\s*\d|increas|boost|rais)",
        lowered,
    ):
        return [("attack_type_damage_up", "attack_type_damage_up", "attack_type_damage")]
    if direction == "ally" and re.search(r"\bequipped characters?['’]?\s+damage\b", lowered) and (
        re.search(r"[+-]\s*\d", lowered) or re.search(r"\bincreases?\b", lowered)
    ):
        return [("damage_modifier", "equipped_weapon_damage_up", "equipped_weapon_damage")]
    if (
        re.search(r"\b(?:attacks|deals|deal)\b", lowered)
        or re.search(r"\battack\b", lowered)
        or re.search(r"\battack\s+(?:on\s+)?(?:all|each|a|an|single|random|enemy|enemies|opponent|opponents)\b", lowered)
        or re.search(r"\b(?:fixed damage|performs?\s+(?:an?\s+)?attack)\b", lowered)
    ):
        capability = "direct_damage" if direction == "enemy" or direction == "unknown" else ""
        result = [("damage_event", capability, "damage")]
        hit_count = _hit_count(text)
        if hit_count and int(hit_count) > 1:
            result.append(("multi_hit_action", "multi_hit_action", "hit_count"))
        return result
    stat_matches = list(_STAT_WORD_RE.finditer(lowered))
    if stat_matches and re.search(r"\b(?:increase|increases|raise|raises|boost|boosts|up)\b|\+\s*\d", lowered):
        stats = list(dict.fromkeys(
            "power" if match.group(0).casefold() == "pwr" else re.sub(r"\s+", " ", match.group(0).casefold())
            for match in stat_matches
        ))
        return [
            (
                "stat_increase",
                _KNOWN_STAT_CAPABILITIES.get(stat, "") if direction in {"ally", "self"} else "",
                stat.replace(" ", "_"),
            )
            for stat in stats
        ]
    if stat_matches and re.search(r"\b(?:decrease|decreases|reduce|reduces|lower|lowers|down)\b", lowered):
        stats = list(dict.fromkeys(
            "power" if match.group(0).casefold() == "pwr" else re.sub(r"\s+", " ", match.group(0).casefold())
            for match in stat_matches
        ))
        return [
            (
                "stat_decrease",
                _KNOWN_STAT_DECREASE_CAPABILITIES.get(stat, "") if direction in {"ally", "self"} else "",
                stat.replace(" ", "_"),
            )
            for stat in stats
        ]
    if re.search(r"\b(?:outgoing damage|damage dealt)\b", lowered) and re.search(
        r"\b(?:increase|increases|raise|raises|boost|boosts|up)\b|\+\s*\d",
        lowered,
    ):
        capability = "outgoing_damage_up" if direction in {"ally", "self"} else ""
        return [("damage_modifier", capability, "outgoing_damage")]
    if re.search(r"\b(?:damage received|damage taken|damage reduction|barrier|shield)\b", lowered):
        return [("defensive_effect", "", "damage_mitigation")]
    return [("unsupported_effect", "", "unknown")]


def _dependency_values(text: str) -> list[tuple[str, str]]:
    lowered = _key(text)
    if (
        _RESOURCE_CONSUMPTION_RE.search(text)
        or _RESOURCE_GAIN_RE.search(text)
        or _STACK_CREATION_RE.search(text)
        or _STATE_CREATION_RE.search(text)
        or re.search(
            r"\b(?:mp|resource) consumption\s+(?:reduction|reduced|decreased|down)\b",
            text,
            re.IGNORECASE,
        )
    ):
        return []
    if _NEGATIVE_STATUS_CONDITION_RE.search(text) or _NEGATIVE_STATE_ABSENCE_RE.search(text):
        return [("unsupported_condition", _clean(text))]
    if _SEQUENCE_INTERRUPTION_RE.search(text):
        return []
    if _formula_metadata(text):
        return []
    values: list[tuple[str, str]] = []
    if re.search(r"\bend of turn\b", lowered):
        return []
    awakened = re.search(r"\bawakened zone\b", text, re.IGNORECASE)
    stance = re.search(
        r"\b(?:[a-z][\w'-]*(?:\s+[a-z][\w'-]*){0,2})(?:/(?:[a-z][\w'-]*)){0,4}\s+stance\b",
        text,
        re.IGNORECASE,
    )
    zone = re.search(r"\b(?:another\s+)?zone\b", text, re.IGNORECASE)
    if awakened:
        values.append(("requires_awakened_zone", awakened.group(0)))
    elif stance or zone:
        match = stance or zone
        values.append(("requires_zone", match.group(0)))

    charge_threshold = re.search(
        r"\bcharge\s+(?:is\s+)?(?:at least\s+)?\d+\+?(?=\s|$)",
        text,
        re.IGNORECASE,
    )
    stack_matches = list(re.finditer(r"\b([a-z][\w'-]*)\s+stacks?\b", text, re.IGNORECASE))
    devotion_stack = next(
        (match for match in reversed(stack_matches) if match.group(1).casefold() == "devotion"),
        None,
    )
    stack_reference = charge_threshold or devotion_stack or (stack_matches[-1] if stack_matches else None)
    stack_threshold = _STACK_THRESHOLD_RE.search(text)
    named_state = _NAMED_STATE_REQUIREMENT_RE.search(text)
    if stack_threshold:
        state_name = stack_threshold.group("state") or stack_threshold.group("owned_state") or "stack"
        values.append(("requires_stack", _clean(state_name)))
    elif named_state and not stack_reference:
        values.append(("requires_stack", _clean(named_state.group("state"))))
    if (stack_reference or re.search(r"\bstacks?\b", lowered)) and not any(
        value == "requires_stack" for value, _scope in values
    ):
        values.append(("requires_stack", stack_reference.group(0) if stack_reference else "stack"))

    status = re.search(r"\bstatus(?: ailment)?\b", text, re.IGNORECASE)
    if status:
        values.append(("requires_status", status.group(0)))
    stellar = re.search(r"\bstellar (?:awakened|awakening)\b", text, re.IGNORECASE)
    if stellar:
        values.append(("requires_stellar_awakened", stellar.group(0)))
    if re.search(
        r"\b(?:sidekick activation|sidekick is active|sidekick active|activate sidekick)\b",
        text,
        re.IGNORECASE,
    ):
        values.append(("requires_sidekick_activation", "sidekick activation"))

    party = re.search(r"\ban ally\b[^;:]*\bon the front ?line\b", text, re.IGNORECASE) or re.search(
        r"\b[\w'-]+\s+is on the frontline\b", text, re.IGNORECASE
    ) or re.search(r"\b(?:frontline|front line|party composition|at front)\b", text, re.IGNORECASE)
    if party:
        values.append(("party_composition", party.group(0)))
    elif re.search(r"\b(?:party members?|allies|recipients?|equipped characters?)\b", lowered) or re.search(
        r"\b(?:eligible|eligibility|equipped)\b", lowered
    ):
        values.append(("requires_recipient_eligibility", "recipient eligibility"))
    if re.search(r"\b(?:once per battle|once per character|limited use|limited uses?)\b", lowered):
        values.append(("limited_use", "limited use"))
    return list(dict.fromkeys(values))


def _dependency_value(text: str) -> str:
    values = _dependency_values(text)
    if values:
        return values[0][0]
    if re.search(r"\bend of turn\b", _key(text)):
        return "end_of_turn"
    return ""


def _dependency_magnitude(text: str, dependency_value: str) -> dict[str, Any]:
    if dependency_value != "requires_stack":
        return {}
    comparison = re.search(
        r"\bless\s+than\s+(\d+)\s+(.+?)\s+stacks?\b",
        text,
        re.IGNORECASE,
    )
    if comparison:
        return {
            "comparison": "<",
            "resource": _clean(comparison.group(2)),
            "value": int(comparison.group(1)),
        }
    threshold = _STACK_THRESHOLD_RE.search(text)
    if threshold:
        count = threshold.group("count") or threshold.group("owned_count")
        state = threshold.group("state") or threshold.group("owned_state")
        if count:
            return {
                "comparison": ">=",
                "resource": _clean(state or "stack"),
                "value": int(count),
            }
    return {}


def _operation_for_occurrence(kind: str, text: str, semantic_type: str) -> str:
    known_operation = _OPERATION_BY_SEMANTIC_TYPE.get(semantic_type)
    if known_operation:
        return known_operation
    lowered = _key(text)
    if kind in {"dependency", "gap"} and semantic_type == "condition":
        if re.search(r"\bconsume(?:s|d)?\b", lowered):
            return "consume"
        if re.search(r"\b(?:requires?|needs?)\b", lowered):
            return "require"
        if re.search(r"\b(?:if|when|unless|only when|after|before|during)\b", lowered):
            return "conditional"
        if re.match(r"\s*in\s+(?:[\w'-]+\s*[/,]\s*)*[\w'-]+\s+stance\b", lowered):
            return "conditional"
    for operation, pattern in _OPERATION_PATTERNS:
        if pattern.search(lowered):
            return operation
    return "unknown"


def _trim_range(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _split_action_ranges(text: str, start: int, end: int) -> list[tuple[int, int]]:
    if _SEQUENCE_TEXT_RE.search(text, start, end) or _SEQUENCE_INTERRUPTION_RE.search(text, start, end):
        return [_trim_range(text, start, end)]
    formula_matches = [
        match
        for pattern in (_SKILL_DAMAGE_MULTIPLIER_RE, _STACK_MULTIPLIER_RE, _FORMULA_RE)
        if (match := pattern.search(text, start, end)) is not None
    ]
    formula_start = min((match.start() for match in formula_matches), default=end)
    matches = [
        match
        for match in _ACTION_HEAD_RE.finditer(text, start, end)
        if match.start() < formula_start
    ]
    compound_matches = list(_COMPOUND_EFFECT_START_RE.finditer(text, start, end))
    splits: set[tuple[int, int]] = {
        (match.start(), match.end())
        for match in compound_matches
        if not re.search(
            r"\b(?:power|intelligence|speed|luck)\s*$",
            text[max(start, match.start() - 50):match.start()],
            re.IGNORECASE,
        )
    }
    splits.update(
        (match.start(), match.end())
        for match in _NAMED_STATE_EFFECT_START_RE.finditer(text, start, end)
        if _ACTION_HEAD_RE.search(text[start:match.start()])
    )
    splits.update((match.start(), match.end()) for match in _RESOURCE_COST_START_RE.finditer(text, start, end))
    attack_result = _ATTACK_RESULT_RE.search(text, start, formula_start)
    if formula_matches and attack_result and attack_result.end() < end:
        # Keep the primary attack anchor at its asserted target phrase. The
        # following formula/tier annotation remains a sibling segment and can
        # contribute structured metadata through the local fragment.
        splits.add((attack_result.end(), attack_result.end()))
    previous_end = matches[0].end() if matches else start
    for match in matches[1:]:
        between = text[previous_end:match.start()]
        connector = re.search(
            r",\s*(?:and|then)?\s*|\s+(?:and|then)\s+",
            between,
            re.IGNORECASE,
        )
        if connector:
            splits.add((previous_end + connector.start(), previous_end + connector.end()))
        previous_end = match.end()
    if not splits:
        return [_trim_range(text, start, end)]
    ranges: list[tuple[int, int]] = []
    previous = start
    for left_end, right_start in sorted(splits):
        if left_end <= previous or right_start >= end:
            continue
        left_start, left_end = _trim_range(text, previous, left_end)
        if left_start < left_end:
            ranges.append((left_start, left_end))
        previous = right_start
    right_start, right_end = _trim_range(text, previous, end)
    if right_start < right_end:
        ranges.append((right_start, right_end))
    return ranges


_COORDINATED_RESULT_VALUE_RE = re.compile(
    r"(?:[+-]\s*\d+(?:\.\d+)?\s*%?|\b[x×]\s*\d+(?:\.\d+)?\b|"
    r"\b\d+\s+times?\b|\b(?:XXL|XL|L|M|S)\b)",
    re.IGNORECASE,
)
_COORDINATED_RESULT_SUBJECT_RE = re.compile(
    r"\b(?:power|intelligence|speed|luck|max(?:imum)?\s+hp|mp|hp|mp\s+consumption|"
    r"damage|attack|resistance|critical rate|barrier|shield|buffs?|debuffs?|link|element)\b",
    re.IGNORECASE,
)
_SHARED_DURATION_SUFFIX_RE = re.compile(
    r"(?:\(\s*(?:for\s+)?\d+\s+turns?\s*\)?|(?:for\s+)?\d+\s+turns?)\s*$",
    re.IGNORECASE,
)
_SHARED_DURATION_RE = re.compile(
    r"(?:\(\s*(?:for\s+)?\d+\s+turns?\s*\)?|(?:for\s+)?\d+\s+turns?)",
    re.IGNORECASE,
)
_SHARED_DURATION_STACK_TAIL_RE = re.compile(
    r"\(\s*(?:for\s+)?\d+\s+turns?\s*\)?\s+"
    r"max(?:imum)?\s+stacks?\s*:?\s*\d+.*$",
    re.IGNORECASE,
)
_SHARED_STACK_SUFFIX_RE = re.compile(r"\(\s*max(?:imum)?\s+stack\s*:?\s*x?\s*\d+\s*\)\s*$", re.IGNORECASE)
_ROLE_BOUNDARY_RE = re.compile(
    r",\s*(?:and\s+|then\s+|but\s+)?|\s+(?:and|then|but)\s+",
    re.IGNORECASE,
)


_SOURCE_RESOURCE_PREDICATE_RE = re.compile(
    r"\s*(?:consume|consumes|consumed|spend|spends|spent|gain|gains|gained|"
    r"grant|grants|granted|add|adds|added|create|creates|created|generate|generates|"
    r"generated|stack|stacks|stacked)\b",
    re.IGNORECASE,
)


def _source_clause_is_complete(text: str) -> bool:
    """Recognize a syntactically complete clause for source-boundary splitting."""
    clause = text.strip(" .,:;()")
    if not clause or _NEGATED_ACTION_RE.search(clause) or _NEGATED_COPULAR_PREDICATE_RE.search(clause):
        return False
    if _SEQUENCE_TEXT_RE.search(clause) or _SEQUENCE_INTERRUPTION_RE.search(clause):
        return False
    if _RESOURCE_CONSUMPTION_RE.search(clause) or _RESOURCE_GAIN_RE.search(clause):
        return True
    if _EXPLICIT_RESULT_PROPERTY_RE.search(clause):
        return True
    if _STACK_CREATION_RE.search(clause) or _STATE_CREATION_RE.search(clause):
        label = re.search(r"\b[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}\s*:\s*", clause)
        if label and _ACTION_HEAD_RE.search(clause[label.end():]) and not _COORDINATED_RESULT_VALUE_RE.search(clause[label.end():]):
            return False
        return True
    attack_result = _ATTACK_RESULT_RE.search(clause)
    formula_start = min(
        (
            match.start()
            for pattern in (_SKILL_DAMAGE_MULTIPLIER_RE, _STACK_MULTIPLIER_RE, _FORMULA_RE)
            if (match := pattern.search(clause)) is not None
        ),
        default=len(clause),
    )
    if _is_formula_explanation(clause) and not (attack_result and attack_result.end() <= formula_start):
        return False
    has_predicate = bool(_ACTION_HEAD_RE.search(clause) or attack_result or _SOURCE_RESOURCE_PREDICATE_RE.search(clause))
    has_value = bool(_COORDINATED_RESULT_VALUE_RE.search(clause))
    has_subject = bool(_COORDINATED_RESULT_SUBJECT_RE.search(clause))
    has_applied_object = bool(
        re.search(r"\b(?:on|to|against|with|from)\b|\b(?:poison|pain|rage|break|status|debuff|buff|shield|link)\b", clause, re.IGNORECASE)
    )
    return has_predicate and (has_value or has_subject or has_applied_object)


def _shared_result_suffix(text: str, start: int, end: int) -> re.Match[str] | None:
    duration = _SHARED_DURATION_SUFFIX_RE.search(text, start, end)
    stack = _SHARED_STACK_SUFFIX_RE.search(text, start, end)
    duration_stack_tail = _SHARED_DURATION_STACK_TAIL_RE.search(text, start, end)
    matches = [
        match
        for match in (duration_stack_tail, duration, stack)
        if match is not None
    ]
    return min(matches, key=lambda match: match.start()) if matches else None


def _coordinated_result_ranges(
    text: str,
    start: int,
    end: int,
) -> list[tuple[int, int, str, str, str, int | None, int | None]]:
    """Build neutral owner ranges around independent local clauses.

    Clause boundaries follow predicates and owned result fields rather than
    effect-looking text. Coordinated modifiers remain attached to the result
    group, and a resource cost followed by an action gets distinct owners.
    """
    sequence_match = re.search(
        r"\s+to\s+(?=perform\s+the\s+following\s+moves?\s+in\s+succession\b)",
        text[start:end],
        re.IGNORECASE,
    )
    action_match = re.search(r"\s+to\s+(?:do|deal|make)\s+", text[start:end], re.IGNORECASE)
    boundary_match = sequence_match or action_match
    if boundary_match:
        boundary_start = start + boundary_match.start()
        boundary_end = start + boundary_match.end()
        left_text = text[start:boundary_start]
        right_text = text[boundary_end:end]
        if _RESOURCE_CONSUMPTION_RE.search(left_text):
            suffix = _shared_result_suffix(text, boundary_end, end)
            content_end = suffix.start() if suffix else end
            right_ranges = _coordinated_result_ranges(text, boundary_end, content_end) if content_end > boundary_end else []
            result = [(start, boundary_start, "", "", "", None, None)]
            for a, b, conjunction, group_id, _shared, _ss, _se in (
                right_ranges or [(boundary_end, content_end, "to", "", "", None, None)]
            ):
                result.append(
                    (
                        a,
                        b,
                        conjunction or "to",
                        group_id or (f"group:{start}:{end}" if suffix else ""),
                        text[suffix.start():suffix.end()] if suffix else "",
                        suffix.start() if suffix else None,
                        suffix.end() if suffix else None,
                    )
                )
            return result

    semantic_end = end
    skill_requirement = re.search(
        r"\b(?:the\s+)?skill\s+requires?\b[^;]*$",
        text[start:end],
        re.IGNORECASE,
    )
    if skill_requirement and start + skill_requirement.start() > start:
        semantic_end = start + skill_requirement.start()
    suffix = _shared_result_suffix(text, start, semantic_end)
    content_end = suffix.start() if suffix else semantic_end
    connectors = list(_ROLE_BOUNDARY_RE.finditer(text, start, content_end))
    boundaries: list[tuple[int, int, str]] = []
    part_start = start
    for index, connector in enumerate(connectors):
        next_start = connectors[index + 1].start() if index + 1 < len(connectors) else content_end
        left_text = text[part_start:connector.start()]
        right_text = text[connector.end():next_start]
        left_complete = _source_clause_is_complete(left_text)
        right_complete = _source_clause_is_complete(right_text)
        right_starts_resource_operation = bool(_SOURCE_RESOURCE_PREDICATE_RE.match(right_text))
        if left_complete and (
            right_complete
            or right_starts_resource_operation
        ):
            conjunction_match = re.search(r"\b(and|then|but)\b", connector.group(0), re.IGNORECASE)
            conjunction = conjunction_match.group(1).casefold() if conjunction_match else "then"
            boundaries.append((connector.start(), connector.end(), conjunction))
            part_start = connector.end()

    # A named state label followed by a result description is a structural
    # boundary even when the source author omits punctuation between them.
    label_start = start
    for label in re.finditer(r"\b[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}\s*:\s*(?=[A-Z])", text, re.IGNORECASE):
        if label.start() <= start or label.start() >= content_end:
            continue
        if _STACK_CREATION_RE.search(text[label_start:label.end()]) or _STATE_CREATION_RE.search(text[label_start:label.end()]):
            boundaries.append((label.end(), label.end(), "label"))
            label_start = label.end()

    boundaries.sort(key=lambda row: row[0])
    deduped: list[tuple[int, int, str]] = []
    seen_positions: set[tuple[int, int]] = set()
    for left, right, connector in boundaries:
        if (left, right) in seen_positions:
            continue
        seen_positions.add((left, right))
        deduped.append((left, right, connector))
    if not deduped:
        return [(start, end, "", "", "", None, None)]

    group_id = f"group:{start}:{end}"
    cuts: list[tuple[int, int, str]] = []
    previous_end = start
    for left, right, conjunction in deduped:
        cuts.append((previous_end, left, "" if previous_end == start else conjunction))
        previous_end = right
    cuts.append((previous_end, content_end, "" if previous_end == start else deduped[-1][2]))
    result: list[tuple[int, int, str, str, str, int | None, int | None]] = []
    for index, (part_start, part_end, conjunction_before) in enumerate(cuts):
        part_start, part_end = _trim_range(text, part_start, part_end)
        if part_start >= part_end:
            continue
        cost_property = re.search(r"\b(?:mp|resource) consumption\b", text[part_start:part_end], re.IGNORECASE)
        if cost_property and re.match(
            r"\s*(?:reduce|reduces|reduced|decrease|decreases|decreased)\b",
            text[part_start:part_end],
            re.IGNORECASE,
        ):
            part_start += cost_property.start()
        shared_text = text[suffix.start():suffix.end()] if suffix else ""
        shared_start = suffix.start() if suffix else None
        shared_end = suffix.end() if suffix else None
        result.append(
            (
                part_start,
                part_end,
                conjunction_before,
                group_id,
                shared_text,
                shared_start,
                shared_end,
            )
        )
    return result


def _source_atoms(text: str) -> list[_SourceAtom]:
    """Split a source fragment at clear action boundaries and retain local context."""
    atoms: list[_SourceAtom] = []
    segment_start = 0
    segment_ranges: list[tuple[int, int]] = []
    for separator in re.finditer(
        r";|(?<!\d)\.(?!\d)(?!png\b)|(?<=\d)\.(?!\d)(?!png\b)(?=\s+[A-Z])",
        text,
        re.IGNORECASE,
    ):
        if separator.group(0) == ";":
            prefix = text[segment_start:separator.start()]
            suffix = text[separator.end():]
            prior_condition = _LEADING_CONDITION_RE.match(prefix.rstrip() + ".")
            prior_condition_is_complete = bool(
                prior_condition
                and prior_condition.end() == len(prefix.rstrip()) + 1
                and not _ACTION_HEAD_RE.search(prefix)
                and not _ATTACK_RESULT_RE.search(prefix)
                and not _SOURCE_RESOURCE_PREDICATE_RE.search(prefix)
            )
            if prior_condition_is_complete and _LEADING_CONDITION_RE.match(suffix):
                continue
            kaleido_application = re.search(r"\bgrant\s+kaleido\b", prefix, re.IGNORECASE) and re.match(
                r"\s*change user's element based on element of the ally with devotion\b",
                suffix,
                re.IGNORECASE,
            )
            kaleido_buff_metadata = re.search(r"\bkaleido\s*$", prefix, re.IGNORECASE) and re.match(
                r"\s*change element of type attack buff according to\b",
                suffix,
                re.IGNORECASE,
            )
            if kaleido_application or kaleido_buff_metadata:
                continue
        segment_ranges.append((segment_start, separator.start()))
        segment_start = separator.end()
    segment_ranges.append((segment_start, len(text)))
    for segment_start, segment_end in segment_ranges:
        start, end = _trim_range(text, segment_start, segment_end)
        if start == end:
            continue

        aura_condition = re.match(
            r"\s*aura activation condition\s*:\s*(?P<condition>.+)$",
            text[start:end],
            re.IGNORECASE,
        )
        if aura_condition:
            condition_start = start + aura_condition.start("condition")
            condition_end = start + aura_condition.end("condition")
            event_condition = _clean(text[condition_start:condition_end])
            atoms.append(
                _SourceAtom(
                    text=_clean(text[start:end]),
                    effect_text="",
                    character_start=start,
                    character_end=end,
                    condition=event_condition,
                    condition_start=condition_start,
                    condition_end=condition_end,
                    action_timing=_trigger(event_condition),
                    timing_start=start,
                    timing_end=start + aura_condition.start("condition") - 1,
                )
            )
            continue

        condition = ""
        condition_start: int | None = None
        condition_end: int | None = None
        condition_match = _BRACKET_CONDITION_RE.match(text, start, end) or _LEADING_CONDITION_RE.match(text, start, end)
        body_start = start
        if condition_match and _trigger(condition_match.group("condition")) != "on_use":
            condition = _clean(condition_match.group("condition"))
            condition_start = condition_match.start("condition")
            condition_end = condition_match.end("condition")
            body_start = condition_match.end()

        leading_trigger = _trigger(condition)
        timing = (
            leading_trigger
            if leading_trigger in {"on_stellar_burst", "after_each_attacking_move"}
            else ""
        )
        timing_start: int | None = condition_start if timing else None
        timing_end: int | None = condition_end if timing else None
        if leading_trigger == "after_each_attacking_move":
            condition = ""
            condition_start = None
            condition_end = None
        timing_match = _ACTION_TIMING_RE.search(text, body_start, end)
        first_action = _ACTION_HEAD_RE.search(text, body_start, end)
        if timing_match and (first_action is None or timing_match.start() < first_action.start()):
            timing = _trigger(timing_match.group(0))
            timing_start = timing_match.start()
            timing_end = timing_match.end()
            body_start = timing_match.end()
            while body_start < end and (text[body_start].isspace() or text[body_start] in ",:"):
                body_start += 1
            if not condition:
                post_timing_condition = _LEADING_CONDITION_RE.match(text, body_start, end)
                if post_timing_condition and _trigger(post_timing_condition.group("condition")) != "on_use":
                    condition = _clean(post_timing_condition.group("condition"))
                    condition_start = post_timing_condition.start("condition")
                    condition_end = post_timing_condition.end("condition")
                    body_start = post_timing_condition.end()

        body_start, body_end = _trim_range(text, body_start, end)
        automatic_prefix = re.match(
            r"(?:auto(?:matically)?|automatically)\s+(?=(?:inflict|apply|activate|restore|recover|grant|perform)\b)",
            text[body_start:body_end],
            re.IGNORECASE,
        )
        if automatic_prefix:
            body_start += automatic_prefix.end()
        leading_conjunction = re.match(r"(?:and|then)\s+", text[body_start:body_end], re.IGNORECASE)
        if leading_conjunction:
            body_start += leading_conjunction.end()
        body_start, body_end = _trim_range(text, body_start, body_end)
        body_text = text[body_start:body_end]
        if re.match(r"\s*(?:(?:the\s+)?skill\s+)?(?:requires?|needs?|must)\b", body_text, re.IGNORECASE):
            condition_text = _clean(body_text)
            atoms.append(
                _SourceAtom(
                    text=_clean(text[start:end]),
                    effect_text="",
                    character_start=start,
                    character_end=end,
                    condition=condition_text,
                    condition_start=body_start,
                    condition_end=body_end,
                    action_timing=timing,
                    timing_start=timing_start,
                    timing_end=timing_end,
                )
            )
            continue
        has_action_syntax = bool(
            _ACTION_HEAD_RE.search(body_text)
            or _ATTACK_RESULT_RE.search(body_text)
            or _SOURCE_RESOURCE_PREDICATE_RE.search(body_text)
        )
        has_non_condition_syntax = bool(
            has_action_syntax
            or _EXPLICIT_RESULT_PROPERTY_RE.search(body_text)
            or _formula_metadata(text[start:end])
            or _SEQUENCE_TEXT_RE.search(text[start:end])
            or _SEQUENCE_INTERRUPTION_RE.search(text[start:end])
            or _HIT_COUNT_MODIFIER_RE.search(text[start:end])
            or _RESULT_MODIFIER_RE.search(text[start:end])
            or _RESULT_EFFECT_POTENCY_RE.search(text[start:end])
        )
        if (
            not has_non_condition_syntax
            and _CONDITION_RE.search(text[start:end])
        ):
            trigger = _trigger(text[start:end])
            is_trigger = bool(trigger)
            residual_condition = (
                _LEADING_CONDITION_RE.match(text, body_start, end)
                if is_trigger and body_start < end
                else None
            )
            if not condition and residual_condition:
                condition = _clean(residual_condition.group("condition"))
                condition_start = residual_condition.start("condition")
                condition_end = residual_condition.end("condition")
            atoms.append(
                _SourceAtom(
                    text=_clean(text[start:end]),
                    effect_text="",
                    character_start=start,
                    character_end=end,
                    condition=condition if is_trigger else _clean(text[start:end]),
                    condition_start=condition_start if is_trigger and condition else start,
                    condition_end=condition_end if is_trigger and condition else end,
                    action_timing=trigger,
                    timing_start=timing_start if is_trigger else None,
                    timing_end=timing_end if is_trigger else None,
                )
            )
            continue
        action_segments: list[tuple[int, int, str, str, str, int | None, int | None]] = []
        for (
            result_start,
            result_end,
            conjunction_before,
            group_id,
            shared_modifier_text,
            shared_modifier_start,
            shared_modifier_end,
        ) in _coordinated_result_ranges(text, body_start, body_end):
            result_ranges = _split_action_ranges(text, result_start, result_end)
            action_segments.extend(
                (
                    action_start,
                    action_end,
                    conjunction_before if index == 0 else "and",
                    group_id,
                    shared_modifier_text,
                    shared_modifier_start,
                    shared_modifier_end,
                )
                for index, (action_start, action_end) in enumerate(result_ranges)
            )
        action_ranges = [(action_start, action_end) for action_start, action_end, *_ in action_segments]
        shared_suffix_start = max(
            (
                index
                for index, segment in enumerate(action_segments)
                if index > 0 and segment[2] == "then"
            ),
            default=0,
        )
        segment_metadata = {
            (action_start, action_end): (
                conjunction_before,
                group_id,
                shared_modifier_text,
                shared_modifier_start,
                shared_modifier_end,
            )
            for action_start, action_end, conjunction_before, group_id, shared_modifier_text, shared_modifier_start, shared_modifier_end in action_segments
        }
        shared_skill_requirement = _TRAILING_CONDITION_RE.search(text, start, end)
        if (
            shared_skill_requirement
            and not re.match(
                r"\s*(?:the\s+)?skill\s+requires?\b",
                shared_skill_requirement.group(0),
                re.IGNORECASE,
            )
        ):
            shared_skill_requirement = None
        for range_index, (action_start, action_end) in enumerate(action_ranges):
            (
                conjunction_before,
                coordinated_group_id,
                shared_modifier_text,
                shared_modifier_start,
                shared_modifier_end,
            ) = segment_metadata[(action_start, action_end)]
            if shared_modifier_text and range_index < shared_suffix_start:
                shared_modifier_text = ""
                shared_modifier_start = None
                shared_modifier_end = None
            local_condition = condition
            local_condition_start = condition_start
            local_condition_end = condition_end
            if shared_skill_requirement and not local_condition:
                local_condition = _clean(shared_skill_requirement.group(0))
                local_condition_start = shared_skill_requirement.start()
                local_condition_end = shared_skill_requirement.end()
            effect_end = action_end
            trailing = _TRAILING_CONDITION_RE.search(text, action_start, action_end)
            if trailing and trailing.start() > action_start:
                trailing_text = _clean(trailing.group(0)).strip("() ")
                if not shared_skill_requirement or trailing.start() != shared_skill_requirement.start():
                    trailing_timing = _trigger(trailing_text)
                    if trailing_timing in {"on_use", "on_stellar_burst", "after_each_attacking_move"}:
                        timing = trailing_timing
                        timing_start = trailing.start()
                        timing_end = trailing.end()
                    else:
                        local_condition = (
                            f"{local_condition}; {trailing_text}" if local_condition else trailing_text
                        )
                        local_condition_start = local_condition_start or trailing.start()
                        local_condition_end = trailing.end()
                effect_end = trailing.start()
                if effect_end > action_start and text[effect_end - 1] == "(":
                    effect_end -= 1
            effect_start, effect_end = _trim_range(text, action_start, effect_end)
            if effect_start == effect_end:
                continue
            effect_text = _clean(text[effect_start:effect_end])
            semantic_effect_text = effect_text
            resistance_property = re.fullmatch(
                r"(?:physical|magic|element|attack type|slash|piercing|pierce|blunt)\s+resistance",
                effect_text,
                re.IGNORECASE,
            )
            if resistance_property and range_index + 1 < len(action_ranges):
                next_start, next_end = action_ranges[range_index + 1]
                next_effect_text = _clean(text[next_start:next_end])
                next_property = re.match(
                    r"(?:physical|magic|element|attack type|slash|piercing|pierce|blunt)\s+resistance\b",
                    next_effect_text,
                    re.IGNORECASE,
                )
                negative_value = re.search(r"-\s*\d+(?:\.\d+)?\s*%", next_effect_text)
                if next_property and negative_value:
                    semantic_effect_text = _clean(
                        f"{effect_text}{next_effect_text[next_property.end():]}"
                    )
            atoms.append(
                _SourceAtom(
                    text=effect_text,
                    effect_text=semantic_effect_text,
                    character_start=effect_start,
                    character_end=effect_end,
                    condition=local_condition,
                    condition_start=local_condition_start,
                    condition_end=local_condition_end,
                    action_timing=timing or _trigger(effect_text),
                    timing_start=timing_start,
                    timing_end=timing_end,
                    action_start=segment_start,
                    action_end=segment_end,
                    conjunction_before=conjunction_before,
                    coordinated_result_group_id=coordinated_group_id,
                    shared_modifier_text=shared_modifier_text,
                    shared_modifier_start=shared_modifier_start,
                    shared_modifier_end=shared_modifier_end,
                )
            )

    return atoms


def _state_reference(text: str) -> str:
    text = re.sub(
        r"^\s*(?:only\s+)?(?:when|if|unless|while|during|after|before)\s+(?:in\s+)?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    stance_list = re.search(
        r"\b((?:[A-Z][\w'-]*(?:\s*[/,]\s*(?:or\s+)?[A-Z][\w'-]*){1,4})\s+Stance)\b",
        text,
    )
    if stance_list:
        return stance_list.group(1)
    named_state = re.search(
        r"\b([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)*\s+"
        r"(?:Stance|Zone|Awakening|Break|Levels|Burst))\b",
        text,
    )
    if named_state:
        return named_state.group(1)
    named_resource = re.search(
        r"^\s*([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})\s*:\s*"
        r"[+-]?\s*\d+(?:\.\d+)?\s+PWR\b",
        text,
    )
    if named_resource:
        return named_resource.group(1)
    named_effect_state = re.search(
        r"^\s*([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})\s*:\s*"
        r"(?:increase|increase[d]?|physical|magic|fire|water|wind|earth|thunder|shade|crystal|\+)",
        text,
        re.IGNORECASE,
    )
    if named_effect_state:
        return named_effect_state.group(1)
    stack_grant = re.search(
        r"\b(?i:stacks?)\s+(?!\d+\b)([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)?)\b",
        text,
    )
    if stack_grant:
        return stack_grant.group(1)
    named_stack = re.search(
        r"\b(?!max\b|maximum\b|per\b)((?:[A-Z][\w'-]*\s+){0,2}[A-Z][\w'-]*)\s+stacks?\b",
        text,
    )
    if named_stack:
        return named_stack.group(1)
    if re.search(r"\b(?:max(?:imum)?\s+stack|per\s+stack)\b", text, re.IGNORECASE):
        return ""
    granted_state = re.search(
        r"\b(?:grants?|gives?|applies?)\s+([A-Z][\w'-]*)\b",
        text,
        re.IGNORECASE,
    )
    if granted_state:
        return granted_state.group(1)
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
    magnitude: Mapping[str, Any] | None = None,
    formula_metadata: Mapping[str, str] | None = None,
    sequence_metadata: Mapping[str, str] | None = None,
    resource_metadata: Mapping[str, str] | None = None,
    result_modifiers: Mapping[str, Any] | None = None,
    semantic_subject: str = "",
    attack_type_override: str = "",
    condition_source_span: SourceSpan | None = None,
    timing_source_span: SourceSpan | None = None,
    probability: Mapping[str, str] | None = None,
    state_reference: str | None = None,
    field_context: str = "",
    semantic_role: SemanticRole | str = SemanticRole.UNKNOWN,
    source_owner_id: str = "",
    branch_context: Sequence[str] = (),
    action_owner_id: str = "",
    coordinated_result_group_id: str = "",
    modifier_source_spans: Sequence[SourceSpan] = (),
    duration_activation_override: Mapping[str, str] | None = None,
    gap_reason: str = "",
) -> ClassifiedOccurrence:
    scoped_text = effect_text if effect_text is not None else text
    result_text = _clean(scoped_text)
    if semantic_type == "damage_mitigation" and semantic_subject == "shield":
        result_text = re.sub(
            r"^.*?\b(?:give|grant|apply)\s+shield\s+to\s+user\b",
            "Shield on user",
            result_text,
            flags=re.IGNORECASE,
        )
        result_text = re.sub(r"(?<=\d)\s+HP\b", "", result_text, flags=re.IGNORECASE)
        result_text = re.sub(r"\s*\(\s*\d+\s+turns?\s*\)\s*$", "", result_text, flags=re.IGNORECASE)
        result_text = _clean(result_text)
    recipient, cardinality = _recipient_and_cardinality(scoped_text)
    direction = _direction(scoped_text)
    if semantic_type == "burst_window":
        recipient, cardinality, direction = "self", "single", "self"
    if semantic_type == "enemy_buff_dispel" and recipient == "unknown":
        recipient, cardinality = "single_enemy", "single"
    if field_context:
        recipient_context = _recipient_context(field_context)
        inherited_recipient, inherited_cardinality = _recipient_and_cardinality(recipient_context)
        if recipient == "unknown":
            recipient = inherited_recipient
            cardinality = inherited_cardinality
        if direction == "unknown":
            direction = _direction(recipient_context)
    canonical_capability = capability_value if capability_value in _CAPABILITY_IDS else ""
    canonical_dependency = dependency_value if dependency_value in _DEPENDENCY_IDS else ""
    capability_gap = (kind == "effect" and not canonical_capability) or (
        kind == "gap" and not dependency_value
    )
    dependency_gap = (kind == "dependency" and not canonical_dependency) or (
        kind == "gap" and bool(dependency_value) and not canonical_dependency
    )
    occurrence_kind = "gap" if capability_gap or dependency_gap else kind
    if occurrence_kind == "gap" and not gap_reason:
        gap_reason = (
            "unsupported capability semantics"
            if capability_gap
            else "unsupported dependency semantics"
        )
    if canonical_capability == "inflict_break" and direction == "unknown":
        direction = "enemy"
        if recipient == "unknown":
            recipient, cardinality = "single_enemy", "single"
    state_reference_value = (
        _state_reference(condition or scoped_text)
        if state_reference is None
        else state_reference
    )
    if kind == "dependency" and canonical_dependency == "party_composition":
        direction = "self"
        recipient = "party_composition"
        cardinality = "single"
    if (
        kind == "dependency"
        and canonical_dependency == "requires_zone"
        and state_reference_value
        and not re.search(r"[/,]", state_reference_value)
    ):
        recipient = state_reference_value
        cardinality = "single"
    return ClassifiedOccurrence(
        occurrence_id=_stable_occurrence_id(str(witness["record_id"]), occurrence_kind, span, ordinal),
        occurrence_kind=occurrence_kind,
        operation=_operation_for_occurrence(occurrence_kind, text, semantic_type),
        source_fact_id=str(witness["record_id"]),
        record_type=str(witness.get("record_type") or ""),
        entity_name=str(witness.get("entity_name") or ""),
        source_capture_sha256=str(witness.get("source_capture_sha256") or witness.get("capture_sha256") or ""),
        source_url=str(witness.get("source_url") or ""),
        source_span=span,
        source_text=_clean(text),
        actor=str(witness.get("entity_name") or "source_owner"),
        direction=direction,
        recipient=recipient,
        recipient_name=_named_recipient(scoped_text, references),
        target_cardinality=cardinality,
        condition=_condition(text) if condition is None else condition,
        trigger=_trigger(text) if action_timing is None else action_timing,
        result=result_text,
        magnitude=dict(magnitude or _magnitude(scoped_text)),
        duration_activation=dict(duration_activation_override or _duration_activation(scoped_text)),
        element=_element(scoped_text) or _element(field_context),
        attack_type=attack_type_override or _attack_type(scoped_text) or _attack_type(field_context),
        state_reference=state_reference_value,
        definition_support=definition_support,
        semantic_state=semantic_state,
        authority=authority,
        capability_value=canonical_capability,
        dependency_value=canonical_dependency,
        legacy_proposal_id=legacy_proposal_id,
        derived_projection=(
            "multi_entity_damage"
            if occurrence_kind == "effect" and canonical_capability == "direct_damage" and cardinality == "multiple"
            else ""
        ),
        semantic_type=semantic_type,
        hit_count=hit_count,
        formula_metadata=dict(formula_metadata or {}),
        sequence_metadata=dict(sequence_metadata or {}),
        resource_metadata=dict(resource_metadata or {}),
        result_modifiers=dict(result_modifiers or {}),
        action_timing=action_timing or "",
        semantic_subject=semantic_subject,
        condition_source_span=condition_source_span,
        timing_source_span=timing_source_span,
        probability=dict(probability or _probability(scoped_text)),
        semantic_role=(semantic_role.value if isinstance(semantic_role, SemanticRole) else str(semantic_role)),
        source_owner_id=source_owner_id,
        branch_context=tuple(branch_context),
        action_owner_id=action_owner_id,
        coordinated_result_group_id=coordinated_result_group_id,
        modifier_source_spans=tuple(modifier_source_spans),
        gap_reason=gap_reason,
    )


def _resource_subject(text: str) -> str:
    match = re.search(
        r"\b(?:consume|spend|use|gain|grant|add|stack)(?:s|d|ing)?\s+"
        r"(?:one|a|an|\+?\d+)?\s*(?P<resource>[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return "unknown_resource"
    value = _clean(match.group("resource"))
    return re.split(r"\b(?:to|for|on|and|then|when|if)\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()


def _conditional_hit_counts(text: str) -> dict[str, str]:
    counts = list(re.finditer(r"\b(?P<count>\d+)\s+hits?\b", text, re.IGNORECASE))
    if not counts:
        return {}
    lowered = _key(text)
    result: dict[str, str] = {}
    for count in counts:
        prefix = lowered[:count.start()]
        use_matches = list(re.finditer(
            r"\b(?P<ordinal>first|second|third(?:\s+or\s+later)?|"
            r"\d+(?:st|nd|rd|th)(?:\s*\+)?)\s+use\b",
            prefix,
        ))
        if not use_matches:
            key = "conditional"
        else:
            ordinal = use_matches[-1].group("ordinal").casefold().replace(" ", "")
            if ordinal.startswith("third+") or ordinal in {"3rd+", "thirdorlater"}:
                key = "third_or_later_use"
            elif ordinal in {"first", "1st"}:
                key = "first_use"
            elif ordinal in {"second", "2nd"}:
                key = "second_use"
            elif ordinal in {"third", "3rd"}:
                key = "third_use"
            else:
                ordinal_number = re.sub(r"\D", "", ordinal)
                key = f"use_{ordinal_number}"
        result[key] = count.group("count")
    return result


def _apply_result_modifier(
    occurrences: list[ClassifiedOccurrence],
    owner_id: str,
    text: str,
    source_span: SourceSpan,
    condition: str = "",
    condition_source_span: SourceSpan | None = None,
) -> bool:
    if not owner_id:
        return False

    def support_spans(row: ClassifiedOccurrence) -> tuple[SourceSpan, ...]:
        existing = list(row.modifier_source_spans)
        anchor = source_span.source_anchor.anchor_id if source_span.source_anchor else ""
        if not any(
            (item.source_anchor.anchor_id if item.source_anchor else "") == anchor
            and item.text == source_span.text
            for item in existing
        ):
            existing.append(source_span)
        return tuple(existing)

    def append_modifier(row: ClassifiedOccurrence, key: str) -> dict[str, Any]:
        current = dict(row.result_modifiers)
        values = list(current.get(key) or [])
        values.append(
            {
                "source_text": _clean(text),
                "condition": condition,
                "source_anchor_id": (
                    source_span.source_anchor.anchor_id if source_span.source_anchor else ""
                ),
            }
        )
        current[key] = values
        return current

    def updated_condition(row: ClassifiedOccurrence) -> tuple[str, str]:
        parts = [part for part in (row.condition, condition) if part]
        merged = "; ".join(dict.fromkeys(parts))
        state = row.state_reference or _state_reference(condition)
        return merged, state

    effect_potency = _RESULT_EFFECT_POTENCY_RE.search(text)
    if effect_potency:
        subjects = {
            word.casefold()
            for word in re.findall(r"\b(?:power|speed)\b", effect_potency.group("subjects"), re.IGNORECASE)
        }
        matches = [
            index
            for index, row in enumerate(occurrences)
            if (row.source_owner_id == owner_id or row.action_owner_id == owner_id)
            and row.occurrence_kind == "effect"
            and row.semantic_type == "stat_increase"
            and row.semantic_subject.casefold() in subjects
        ]
        if not matches:
            return False
        for index in matches:
            row = occurrences[index]
            current = append_modifier(row, "effect_potency")
            current["effect_potency"][-1]["magnitude"] = _magnitude(text)
            occurrences[index] = replace(
                row,
                result_modifiers=current,
                modifier_source_spans=support_spans(row),
            )
        return True

    hit_counts = _conditional_hit_counts(text)
    if hit_counts:
        matches = [
            index
            for index, row in enumerate(occurrences)
            if row.source_owner_id == owner_id
            and row.occurrence_kind == "effect"
            and row.semantic_type == "multi_hit_action"
        ]
        if len(matches) != 1:
            return False
        index = matches[0]
        row = occurrences[index]
        current = dict(row.result_modifiers)
        current_counts = dict(current.get("conditional_hit_counts") or {})
        current_counts.update(hit_counts)
        current["conditional_hit_counts"] = current_counts
        current = append_modifier(row, "conditional_hit_modifiers")
        current["conditional_hit_counts"] = current_counts
        merged_condition, state_reference = updated_condition(row)
        occurrences[index] = replace(
            row,
            result_modifiers=current,
            condition=merged_condition,
            condition_source_span=condition_source_span or row.condition_source_span,
            state_reference=state_reference,
            modifier_source_spans=support_spans(row),
        )
        return True

    hit_delta = re.search(
        r"\bnumber of (?:attacks|hits|(?:piercing|pierce|slash|blunt|magic|physical)\s+hits)\s+by\s+\+?(?P<increment>\d+)\b",
        text,
        re.IGNORECASE,
    )
    if hit_delta:
        attack_type_hint = re.search(r"\b(piercing|pierce|slash|blunt|magic|physical)\s+hits?\b", text, re.IGNORECASE)
        canonical_attack_type = ""
        if attack_type_hint:
            canonical_attack_type = {
                "pierce": "piercing",
                "piercing": "piercing",
            }.get(attack_type_hint.group(1).casefold(), attack_type_hint.group(1).casefold())
        matches = [
            index for index, row in enumerate(occurrences)
            if row.source_owner_id == owner_id
            and row.occurrence_kind == "effect"
            and row.semantic_type == "multi_hit_action"
            and (not canonical_attack_type or row.attack_type.casefold() == canonical_attack_type)
        ]
        if len(matches) != 1:
            return False
        index = matches[0]
        row = occurrences[index]
        increment = int(hit_delta.group("increment"))
        base_count = int(row.hit_count) if row.hit_count.isdigit() else 0
        merged_condition, state_reference = updated_condition(row)
        current = dict(row.result_modifiers)
        current.update(
            {
                "conditional_increment": str(increment),
                "conditional_total": str(base_count + increment),
            }
        )
        current = append_modifier(row, "conditional_hit_modifiers")
        current.update(
            {
                "conditional_increment": str(increment),
                "conditional_total": str(base_count + increment),
            }
        )
        occurrences[index] = replace(
            row,
            result_modifiers=current,
            condition=merged_condition,
            condition_source_span=condition_source_span or row.condition_source_span,
            state_reference=state_reference,
            modifier_source_spans=support_spans(row),
        )
        return True

    max_stack = _MAX_STACK_METADATA_RE.search(text)
    if max_stack:
        matches = [
            index
            for index, row in enumerate(occurrences)
            if (row.source_owner_id == owner_id or row.action_owner_id == owner_id)
            and row.occurrence_kind == "effect"
            and row.semantic_type in {
                "stat_increase",
                "element_damage_increase",
                "critical_support",
                "resistance_reduction",
                "resistance_increase",
            }
        ]
        if matches:
            for index in matches:
                row = occurrences[index]
                current = append_modifier(row, "stack_limit_modifiers")
                occurrences[index] = replace(
                    row,
                    magnitude={**dict(row.magnitude), "max_stacks": max_stack.group("value")},
                    result_modifiers=current,
                    modifier_source_spans=support_spans(row),
                )
            return True
        return False

    if _TYPE_ATTACK_BUFF_DOUBLING_RE.search(text):
        matches = [
            index
            for index, row in enumerate(occurrences)
            if (row.source_owner_id == owner_id or row.action_owner_id == owner_id)
            and row.occurrence_kind == "effect"
            and row.semantic_type == "element_damage_increase"
        ]
        if not matches:
            return False
        condition_match = re.search(r"\bfor\s+(.+)$", text, re.IGNORECASE)
        for index in matches:
            row = occurrences[index]
            current = append_modifier(row, "conditional_potency")
            modifier = current["conditional_potency"][-1]
            modifier["magnitude"] = {"value": "2", "unit": "multiplier", "raw": "doubled"}
            if condition_match:
                modifier["condition"] = f"for {condition_match.group(1).strip(' .;')}"
            occurrences[index] = replace(
                row,
                result_modifiers=current,
                modifier_source_spans=support_spans(row),
            )
        return True

    if not _RESULT_MODIFIER_RE.search(text):
        return False
    matches = [
        index
        for index, row in enumerate(occurrences)
        if row.source_owner_id == owner_id
        and row.occurrence_kind == "effect"
        and row.semantic_type == "damage_event"
    ]
    if len(matches) != 1:
        return False
    index = matches[0]
    row = occurrences[index]
    current = append_modifier(row, "conditional_potency")
    current["conditional_potency"][-1]["magnitude"] = _magnitude(text)
    merged_condition, state_reference = updated_condition(row)
    occurrences[index] = replace(
        row,
        result_modifiers=current,
        condition=merged_condition,
        condition_source_span=condition_source_span or row.condition_source_span,
        state_reference=state_reference,
        modifier_source_spans=support_spans(row),
    )
    return True


def _result_owner_for_modifier(
    occurrences: Sequence[ClassifiedOccurrence],
    context: _AtomContext,
    branch_context: Sequence[str],
    text: str,
) -> str:
    if _RESULT_EFFECT_POTENCY_RE.search(text):
        allowed_types = {"stat_increase"}
    elif _HIT_COUNT_MODIFIER_RE.search(text):
        allowed_types = {"multi_hit_action"}
    elif _MAX_STACK_METADATA_RE.search(text):
        allowed_types = {
            "stat_increase",
            "element_damage_increase",
            "critical_support",
            "resistance_reduction",
            "resistance_increase",
        }
    elif _TYPE_ATTACK_BUFF_DOUBLING_RE.search(text):
        allowed_types = {"element_damage_increase"}
    elif _RESULT_MODIFIER_RE.search(text):
        allowed_types = {"damage_event"}
    else:
        allowed_types = {
            "damage_event",
            "multi_hit_action",
            "stat_increase",
            "element_damage_increase",
            "resistance_reduction",
            "resistance_increase",
        }

    if (
        _MAX_STACK_METADATA_RE.search(text)
        or _TYPE_ATTACK_BUFF_DOUBLING_RE.search(text)
        or _RESULT_EFFECT_POTENCY_RE.search(text)
        or _HIT_COUNT_MODIFIER_RE.search(text)
        or _EACH_PART_FORMULA_RE.search(text)
    ):
        modifier_types = allowed_types
        related = [
            row
            for row in occurrences
            if row.occurrence_kind == "effect"
            and row.semantic_type in modifier_types
            and row.source_owner_id
            and (
                row.source_span.location != context.block.location
                or row.source_span.character_end is None
                or row.source_span.character_end <= context.atom.character_start
            )
        ]
        attack_type_hint = re.search(r"\b(piercing|pierce|slash|blunt|magic|physical)\b", text, re.IGNORECASE)
        if attack_type_hint and _HIT_COUNT_MODIFIER_RE.search(text):
            canonical_attack_type = {
                "pierce": "piercing",
                "piercing": "piercing",
            }.get(attack_type_hint.group(1).casefold(), attack_type_hint.group(1).casefold())
            related = [
                row for row in related if row.attack_type.casefold() == canonical_attack_type
            ]
        if _EACH_PART_FORMULA_RE.search(text):
            attack_types = {
                {"pierce": "piercing", "piercing": "piercing"}.get(
                    match.group(1).casefold(), match.group(1).casefold()
                )
                for match in re.finditer(r"\b(piercing|pierce|slash|blunt|magic|physical)\b", text, re.IGNORECASE)
            }
            related = [row for row in related if row.attack_type.casefold() in attack_types]
        if context.action_owner_id:
            same_action = [
                row for row in related if row.action_owner_id == context.action_owner_id
            ]
            if same_action:
                related = same_action
        if len(related) > 1:
            action_owners = {row.action_owner_id for row in related if row.action_owner_id}
            if len(action_owners) == 1:
                return next(iter(action_owners))
        if len(related) == 1:
            return related[0].source_owner_id
        if related:
            selected_related = max(
                related,
                key=lambda row: (
                    len(row.source_span.ancestry),
                    row.source_span.character_end or -1,
                ),
            )
            return selected_related.source_owner_id

    candidates: list[ClassifiedOccurrence] = []
    for row in occurrences:
        span = row.source_span
        if (
            row.occurrence_kind != "effect"
            or row.semantic_type not in allowed_types
            or not row.source_owner_id
            or tuple(span.ancestry) != tuple(context.block.ancestry[:len(span.ancestry)])
            or tuple(row.branch_context) != tuple(branch_context[:len(row.branch_context)])
        ):
            continue
        if span.location == context.block.location and (
            span.character_end is None
            or span.character_end > context.atom.character_start
        ):
            continue
        candidates.append(row)
    if not candidates and _MAX_STACK_METADATA_RE.search(text) and context.action_owner_id:
        action_candidates = [
            row
            for row in occurrences
            if row.occurrence_kind == "effect"
            and row.semantic_type in allowed_types
            and row.action_owner_id == context.action_owner_id
        ]
        if len(action_candidates) > 1:
            return context.action_owner_id
        if len(action_candidates) == 1:
            return action_candidates[0].source_owner_id
    if not candidates and _TYPE_ATTACK_BUFF_DOUBLING_RE.search(text):
        result_candidates = [
            row
            for row in occurrences
            if row.occurrence_kind == "effect"
            and row.semantic_type == "element_damage_increase"
            and row.source_owner_id
        ]
        if len(result_candidates) == 1:
            return result_candidates[0].source_owner_id
    if not candidates:
        return ""
    selected = max(
        candidates,
        key=lambda row: (
            len(row.source_span.ancestry),
            row.source_span.character_end or -1,
        ),
    )
    return selected.source_owner_id


def _inherit_coordinated_result_fields(occurrences: list[ClassifiedOccurrence]) -> None:
    """Share a trailing value only across adjacent same-role results in one group."""
    by_group: dict[str, list[int]] = {}
    for index, row in enumerate(occurrences):
        if row.coordinated_result_group_id:
            by_group.setdefault(row.coordinated_result_group_id, []).append(index)

    for indices in by_group.values():
        indices.sort(
            key=lambda index: (
                occurrences[index].source_span.character_start
                if occurrences[index].source_span and occurrences[index].source_span.character_start is not None
                else -1
            )
        )
        for position, index in enumerate(indices):
            row = occurrences[index]
            if row.occurrence_kind != "effect" or row.semantic_type != "critical_support":
                continue
            if row.magnitude.get("value"):
                continue
            neighboring = [
                candidate_index
                for candidate_index in indices[max(0, position - 1):position + 2]
                if candidate_index != index
                and occurrences[candidate_index].occurrence_kind == "effect"
                and occurrences[candidate_index].semantic_type == row.semantic_type
                and occurrences[candidate_index].magnitude.get("value")
                and tuple(occurrences[candidate_index].branch_context) == tuple(row.branch_context)
            ]
            if len(neighboring) != 1:
                continue
            source = occurrences[neighboring[0]]
            inherited = {
                key: source.magnitude[key]
                for key in ("value", "unit", "raw")
                if key in source.magnitude
            }
            modifiers = dict(row.result_modifiers)
            modifiers["shared_group_magnitude"] = {
                "source_owner_id": source.source_owner_id,
                "source_anchor_id": (
                    source.source_span.source_anchor.anchor_id
                    if source.source_span and source.source_span.source_anchor
                    else ""
                ),
            }
            support_spans = list(row.modifier_source_spans)
            if source.source_span is not None and source.source_span not in support_spans:
                support_spans.append(source.source_span)
            occurrences[index] = replace(
                row,
                magnitude={**dict(row.magnitude), **inherited},
                result_modifiers=modifiers,
                modifier_source_spans=tuple(support_spans),
            )


def _render_fragment_tokens(
    tokens: Sequence[StructuralToken],
) -> tuple[str, list[tuple[StructuralToken, int, int]]]:
    return render_structural_tokens(tokens)


def _range_span(
    block: StructuralBlock,
    positions: Sequence[tuple[StructuralToken, int, int]],
    start: int,
    end: int,
    text: str,
    *,
    source_fact_id: str,
    source_capture_sha256: str,
) -> SourceSpan:
    cleaned_text = _clean(text)
    selected = [token for token, token_start, token_end in positions if token_start < end and token_end > start]
    try:
        # Resolve semantic spans against the complete structural block so the
        # token offsets do not depend on which fragment produced the span.
        anchor = source_anchor_for_quote(
            source_fact_id=source_fact_id,
            source_capture_sha256=source_capture_sha256,
            block=block,
            quote=cleaned_text,
        )
    except ValueError:
        anchor = source_anchor_from_range(
            source_fact_id=source_fact_id,
            source_capture_sha256=source_capture_sha256,
            block=block,
            positions=positions,
            start=start,
            end=end,
        )
    return SourceSpan(
        location=block.location,
        block_kind=block.kind,
        ancestry=tuple(block.ancestry),
        text=cleaned_text,
        character_start=start,
        character_end=end,
        source_anchor=anchor,
    )


def _coordinated_stat_completion(
    context: _AtomContext,
    contexts: Sequence[_AtomContext],
    *,
    source_fact_id: str,
    source_capture_sha256: str,
) -> tuple[str, SourceSpan] | None:
    """Share an explicitly written stat value with a preceding coordinated stat label."""
    atom = context.atom
    if not atom.coordinated_result_group_id:
        return None
    source_text = atom.effect_text or atom.text
    current_stat = re.fullmatch(
        r"\s*(?P<stat>power|pwr|intelligence|speed|luck|max(?:imum)?\s+hp|max(?:imum)?\s+mp)\s*",
        source_text,
        re.IGNORECASE,
    )
    if not current_stat:
        return None
    siblings = sorted(
        (
            candidate
            for candidate in contexts
            if candidate is not context
            and candidate.atom.coordinated_result_group_id == atom.coordinated_result_group_id
            and candidate.atom.character_start > atom.character_start
        ),
        key=lambda candidate: candidate.atom.character_start,
    )
    for sibling in siblings:
        sibling_text = sibling.atom.effect_text or sibling.atom.text
        sibling_stat = _STAT_WORD_RE.search(sibling_text)
        if not sibling_stat:
            continue
        value = _COORDINATED_RESULT_VALUE_RE.search(sibling_text, sibling_stat.end())
        if not value:
            continue
        suffix = sibling_text[sibling_stat.end():]
        suffix = re.sub(
            r"\s*(?:\(\s*(?:for\s+)?\d+\s+turns?\s*\)?|(?:for\s+)?\d+\s+turns?)\s*$",
            "",
            suffix,
            flags=re.IGNORECASE,
        )
        if not suffix.strip():
            continue
        completed_text = f"{current_stat.group('stat')}{suffix}"
        value_start = sibling.atom.character_start + value.start()
        value_end = sibling.atom.character_start + value.end()
        value_span = _range_span(
            context.block,
            context.token_positions,
            value_start,
            value_end,
            context.fragment_text[value_start:value_end],
            source_fact_id=source_fact_id,
            source_capture_sha256=source_capture_sha256,
        )
        return completed_text, value_span
    return None


def _is_zone_definition_unit(unit: StructuralUnit) -> bool:
    """Recognize a zone-definition heading whose child rows describe the mechanic."""
    return any(
        block.kind == "root"
        and re.match(
            r"\s*awakens?\s+any\b[^:]*\bzones?\s*:\s*$",
            render_structural_tokens(block.tokens)[0],
            re.IGNORECASE,
        )
        for block in unit.blocks
    )


def _fragment_atoms(
    block: StructuralBlock,
    tokens: Sequence[StructuralToken],
    start: int,
    end: int,
    text: str | None = None,
    token_positions: Sequence[tuple[StructuralToken, int, int]] | None = None,
    source_fact_id: str = "",
    source_capture_sha256: str = "",
) -> list[_AtomContext]:
    fragment_text, rendered_positions = (
        (text, list(token_positions))
        if text is not None and token_positions is not None
        else _render_fragment_tokens(tokens)
    )
    semantic_characters = list(fragment_text)
    for token, token_start, token_end in rendered_positions:
        if token.kind == "icon":
            semantic_characters[token_start:token_end] = " " * (token_end - token_start)
    semantic_text = "".join(semantic_characters)
    contexts: list[_AtomContext] = []
    for atom in _source_atoms(semantic_text):
        if atom.coordinated_result_group_id:
            atom = replace(
                atom,
                coordinated_result_group_id=(
                    f"{block.location}:{start}:{end}:{atom.coordinated_result_group_id}"
                ),
            )
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
            source_fact_id=source_fact_id,
            source_capture_sha256=source_capture_sha256,
        )
        condition_span = None
        if atom.condition_start is not None and atom.condition_end is not None:
            condition_span = _range_span(
                block,
                rendered_positions,
                atom.condition_start,
                atom.condition_end,
                atom.condition,
                source_fact_id=source_fact_id,
                source_capture_sha256=source_capture_sha256,
            )
        timing_span = None
        if atom.timing_start is not None and atom.timing_end is not None:
            timing_span = _range_span(
                block,
                rendered_positions,
                atom.timing_start,
                atom.timing_end,
                _clean(fragment_text[atom.timing_start:atom.timing_end]),
                source_fact_id=source_fact_id,
                source_capture_sha256=source_capture_sha256,
            )
        modifier_span = None
        if atom.shared_modifier_start is not None and atom.shared_modifier_end is not None:
            modifier_span = _range_span(
                block,
                rendered_positions,
                atom.shared_modifier_start,
                atom.shared_modifier_end,
                atom.shared_modifier_text,
                source_fact_id=source_fact_id,
                source_capture_sha256=source_capture_sha256,
            )
        action_start = atom.action_start if atom.action_start is not None else atom.character_start
        action_end = atom.action_end if atom.action_end is not None else atom.character_end
        action_span = _range_span(
            block,
            rendered_positions,
            action_start,
            action_end,
            fragment_text[action_start:action_end],
            source_fact_id=source_fact_id,
            source_capture_sha256=source_capture_sha256,
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
                modifier_span=modifier_span,
                action_owner_id=(
                    action_span.source_anchor.anchor_id
                    if action_span.source_anchor is not None
                    else source_span.source_anchor.anchor_id if source_span.source_anchor is not None else ""
                ),
            )
        )
    return contexts


def _unit_atom_contexts(unit: StructuralUnit, source_fact_id: str = "") -> list[_AtomContext]:
    contexts: list[_AtomContext] = []
    fact_id = source_fact_id or str(unit.source_fact_id or "")
    for block in unit.blocks:
        for tokens, start, end in _tokens_to_fragments(block):
            contexts.extend(
                _fragment_atoms(
                    block,
                    tokens,
                    start,
                    end,
                    source_fact_id=fact_id,
                    source_capture_sha256=unit.source.capture_sha256,
                )
            )
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
    if re.search(r"\bperform\b[^.;]*\binstead\b", lowered):
        return "replaces"
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
    return operation if len(before_target) - verb_position <= 80 else "references"


def _relationship_id(
    source_fact_id: str,
    source_owner_id: str,
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
            source_owner_id,
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
    reference_locations = {
        token.location
        for token, start, end in context.token_positions
        if token.kind == "reference" and start < token_end and end > token_start
    }
    for occurrence in occurrences:
        for span in (occurrence.source_span, occurrence.condition_source_span, occurrence.timing_source_span):
            if (
                span is not None
                and span.location in {context.block.location, *reference_locations}
                and span.character_start is not None
                and span.character_end is not None
                and span.character_start < token_end
                and span.character_end > token_start
            ):
                return occurrence.occurrence_id
    return ""


def _relationship_source_span(context: _AtomContext, target_text: str = "") -> SourceSpan:
    if (
        context.atom.condition_start is not None
        and context.atom.character_start is not None
        and context.atom.character_end is not None
        and _trigger(context.atom.condition) == "on_stellar_burst"
        and re.search(r"\bperform\b[^.;]*\binstead\b", context.atom.text, re.IGNORECASE)
    ):
        start = min(context.atom.condition_start, context.atom.character_start)
        end = context.atom.character_end
        anchor = context.source_span.source_anchor
        return _range_span(
            context.block,
            context.token_positions,
            start,
            end,
            context.fragment_text[start:end],
            source_fact_id=anchor.source_fact_id if anchor else "",
            source_capture_sha256=anchor.source_capture_sha256 if anchor else "",
        )
    sequence = _SEQUENCE_TEXT_RE.search(context.atom.text)
    if sequence:
        start = context.atom.character_start + sequence.start()
        end = context.atom.character_start + sequence.end()
        return _range_span(
            context.block,
            context.token_positions,
            start,
            end,
            context.atom.text[sequence.start():sequence.end()],
            source_fact_id=context.source_span.source_anchor.source_fact_id
            if context.source_span.source_anchor
            else "",
            source_capture_sha256=context.source_span.source_anchor.source_capture_sha256
            if context.source_span.source_anchor
            else "",
        )
    target_start = context.atom.text.casefold().find(target_text.casefold()) if target_text else -1
    if target_start >= 0:
        operation_matches = list(
            re.finditer(
                r"\b(?:activate(?:s|d|ing)?|replace(?:s|d|ing)?|choose|chooses|select|selects|branch|branches)\b",
                context.atom.text[:target_start],
                re.IGNORECASE,
            )
        )
        if operation_matches:
            start = context.atom.character_start + operation_matches[-1].start()
            end = context.atom.character_start + target_start + len(target_text)
            if (
                operation_matches[-1].group(0).casefold().startswith("activate")
                and re.search(r"\bon\s+(?:the\s+)?user\b", context.atom.text[target_start + len(target_text):], re.IGNORECASE)
            ):
                end = context.atom.character_end
            return _range_span(
                context.block,
                context.token_positions,
                start,
                end,
                context.fragment_text[start:end],
                source_fact_id=context.source_span.source_anchor.source_fact_id
                if context.source_span.source_anchor
                else "",
                source_capture_sha256=context.source_span.source_anchor.source_capture_sha256
                if context.source_span.source_anchor
                else "",
            )
    return context.source_span


def _relationship_branch_condition(text: str, target_text: str) -> str:
    target_start = text.casefold().find(target_text.casefold()) if target_text else -1
    if target_start < 0:
        return ""
    prefix = text[:target_start]
    operations = list(
        re.finditer(
            r"\b(?:activate(?:s|d|ing)?|replace(?:s|d|ing)?|choose|chooses|select|selects|branch|branches)\b",
            prefix,
            re.IGNORECASE,
        )
    )
    if not operations:
        return ""
    condition_prefix = prefix[:operations[-1].start()]
    branch = re.search(r"([^:;,.]{1,60}):\s*$", condition_prefix)
    return _clean(branch.group(1)) if branch else ""


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

    relationships: dict[str, ClassifiedRelationship] = {}
    shared_resolutions_by_origin = {
        origin_id: resolve_shared_mechanics(
            unit_by_id[origin_id],
            parent_source_fact_id=str(
                unit_by_id[origin_id].source_fact_id or witness.get("record_id") or ""
            ),
            registry=mechanic_registry,
        )
        for origin_id in sorted(origin_ids)
        if origin_id in unit_by_id
    }
    resolved_shared_locations = {
        origin_id: {
            row.source_location
            for row in rows
            if row.resolution_status == "resolved"
        }
        for origin_id, rows in shared_resolutions_by_origin.items()
    }
    for origin_id in origin_ids - contexts_by_unit.keys():
        origin = unit_by_id.get(origin_id)
        if origin is None:
            continue
        source_fact_id = str(origin.source_fact_id or witness.get("record_id") or "")
        shared_locations = resolved_shared_locations.get(origin_id, set())
        contexts_by_unit[origin_id] = []
        for context in _unit_atom_contexts(origin, source_fact_id):
            references = [
                token
                for token in context.selected_tokens
                if token.kind == "reference" and token.location not in shared_locations
            ]
            anchor = context.source_span.source_anchor
            condition_anchor = (
                context.condition_span.source_anchor
                if context.condition_span is not None
                else None
            )
            branch_context = (
                (condition_anchor.anchor_id,)
                if context.atom.condition
                and _is_prerequisite(context.atom.condition)
                and condition_anchor is not None
                else ()
            )
            contexts_by_unit[origin_id].append(
                replace(
                    context,
                    semantic_role=_semantic_role(
                        context.atom,
                        references,
                        shared_definition_source=False,
                    ),
                    owner_id=anchor.anchor_id if anchor is not None else "",
                    branch_context=branch_context,
                )
            )

    def add_relationship(
        *,
        source_fact_id: str,
        source_owner: str,
        source_owner_id: str,
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
        semantic_role: str,
    ) -> None:
        if not source_occurrence_id and source_owner_id:
            candidates = [
                row
                for row in occurrences
                if row.source_fact_id == source_fact_id
                and row.source_owner_id == source_owner_id
            ]
            representative = next(
                (
                    row for row in candidates
                    if row.semantic_role in {
                        SemanticRole.CHILD_INVOCATION.value,
                        SemanticRole.RELATIONSHIP_METADATA.value,
                    }
                ),
                None,
            )
            representative = representative or next(
                (row for row in candidates if row.occurrence_kind in OCCURRENCE_KINDS),
                None,
            )
            representative = representative or next(iter(candidates), None)
            source_occurrence_id = representative.occurrence_id if representative else ""
        relation_id = _relationship_id(
            source_fact_id,
            source_owner_id,
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
                source_owner_id=source_owner_id,
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
                semantic_role=semantic_role,
            ),
        )

    for row in resolutions:
        if row.get("status") == "excluded":
            # General documentation links remain ordinary references.
            continue
        origin_id = str(row.get("origin_unit_id") or root.unit_id)
        if (
            not row.get("target_source_fact_id")
            and str(row.get("occurrence_location") or "")
            in resolved_shared_locations.get(origin_id, set())
        ):
            continue
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
        reference_context, token_start, token_end = _reference_context(
            contexts_by_unit.get(origin_id, ()), token
        )
        relationship_context = reference_context
        if relationship_context is None or not _is_relationship_role(relationship_context.semantic_role):
            ancestry = tuple(reference_context.block.ancestry) if reference_context else ()
            relationship_context = max(
                (
                    candidate
                    for candidate in contexts_by_unit.get(origin_id, ())
                    if candidate.semantic_role == SemanticRole.CHILD_INVOCATION
                    and len(candidate.block.ancestry) < len(ancestry)
                    and ancestry[:len(candidate.block.ancestry)] == tuple(candidate.block.ancestry)
                    and (
                        _RELATIONSHIP_GROUP_HEADER_RE.search(candidate.atom.text)
                        or _SEQUENCE_TEXT_RE.search(candidate.atom.text)
                    )
                    and (
                        not _SEQUENCE_TEXT_RE.search(candidate.atom.text)
                        or candidate.block.location == reference_context.block.location
                    )
                ),
                key=lambda candidate: len(candidate.block.ancestry),
                default=None,
            )
        if relationship_context is None or not _is_relationship_role(relationship_context.semantic_role):
            continue
        if reference_context is relationship_context and re.search(
            rf"\b{re.escape(token.text)}\s+(?:skills?|moves?|actions?)\s*:\s*$",
            relationship_context.atom.text,
            re.IGNORECASE,
        ):
            continue
        block = next(
            (block for block in origin.blocks if any(item.location == token.location for item in block.tokens)),
            None,
        )
        if block is None:
            continue
        block_text, _block_positions = _render_fragment_tokens(block.tokens)
        operation = "replaces" if row.get("variant_relationship") else _relationship_operation(
            relationship_context.atom.text,
            token.text,
        )
        if _SEQUENCE_TEXT_RE.search(relationship_context.atom.text):
            operation = "executes_sequence"
        variant = row.get("variant_relationship") or {}
        condition = str(
            variant.get("condition")
            or _relationship_branch_condition(relationship_context.atom.text, token.text)
            or relationship_context.atom.condition
        )
        timing = relationship_context.atom.action_timing
        if (
            not timing
            and _SEQUENCE_TEXT_RE.search(relationship_context.atom.text)
            and str(witness.get("record_type") or "") in {"active_skill", "skill"}
        ):
            timing = "on_skill_use"
        if (
            not timing
            and _RELATIONSHIP_GROUP_HEADER_RE.search(relationship_context.atom.text)
            and str(witness.get("record_type") or "") in {"active_skill", "skill"}
        ):
            timing = "on_skill_use"
        anchor_positions = (
            reference_context.token_positions
            if reference_context
            else render_structural_tokens(block.tokens)[1]
        )
        anchor_range = next(
            (
                (token_start, token_end)
                for selected, token_start, token_end in anchor_positions
                if selected.location == token.location and selected.order == token.order
            ),
            (0, len(_clean(token.text))),
        )
        origin_fact_id = str(origin.source_fact_id or witness.get("record_id") or "")
        source_anchor = source_anchor_from_range(
            source_fact_id=origin_fact_id,
            source_capture_sha256=origin.source.capture_sha256,
            block=block,
            positions=anchor_positions,
            start=anchor_range[0],
            end=anchor_range[1],
        )
        token_source_span = SourceSpan(
            location=token.location,
            block_kind=block.kind,
            ancestry=tuple(block.ancestry),
            text=token.text,
            character_start=anchor_range[0],
            character_end=anchor_range[1],
            source_anchor=source_anchor,
        )
        source_span = _relationship_source_span(relationship_context, token.text)
        candidate_unit_ids = [str(value) for value in row.get("candidate_unit_ids", [])]
        candidates = [
            str(unit_by_id[candidate].source_fact_id)
            for candidate in candidate_unit_ids
            if candidate in unit_by_id and unit_by_id[candidate].source_fact_id
        ]
        target_id = str(row.get("target_source_fact_id") or "")
        resolution_status = str(row.get("status") or "unresolved")
        resolution_detail = str(row.get("reason") or "")
        resolution_basis = str(row.get("resolution_basis") or "captured_reference")
        if (
            not target_id
            and origin.unit_id == root.unit_id
            and resolution_status == "unresolved_mapping"
            and resolution_detail == "ambiguous_source_variant_alias"
            and root.source_variant_label
            and re.search(r"\bstellar burst\b", block_text, re.IGNORECASE)
            and re.search(r"\bperform\b[^.;]*\binstead\b", block_text, re.IGNORECASE)
        ):
            child_candidates = [
                unit_by_id[candidate]
                for candidate in candidate_unit_ids
                if candidate in unit_by_id
                and _key(unit_by_id[candidate].title) == _key(token.text)
                and unit_by_id[candidate].source_variant_label
                and re.search(
                    rf"\b{re.escape(_key(root.source_variant_label))}\b",
                    _key(unit_by_id[candidate].source_variant_label),
                )
                and re.search(r"\bstellar burst\b", _key(unit_by_id[candidate].source_variant_label))
                and unit_by_id[candidate].source_fact_id
            ]
            if len(child_candidates) == 1:
                target_id = str(child_candidates[0].source_fact_id)
                candidates = [target_id]
                resolution_status = "resolved"
                resolution_detail = ""
                resolution_basis = "parent_variant_and_stellar_burst_context"
        target_kind = "source_fact" if target_id else "unresolved"
        add_relationship(
            source_fact_id=origin_fact_id,
            source_owner=origin.entity_name or str(witness.get("entity_name") or ""),
            source_owner_id=relationship_context.owner_id or source_anchor.anchor_id,
            source_occurrence_id=(
                _source_occurrence_for_reference(occurrences, reference_context, token_start, token_end)
                if reference_context is relationship_context
                else ""
            ),
            target_kind=target_kind,
            target_id=target_id,
            candidate_target_ids=candidates,
            operation=operation,
            condition=condition,
            timing=timing,
            source_span=source_span,
            resolution_status=resolution_status,
            resolution_detail=resolution_detail,
            resolution_basis=resolution_basis,
            definition_status="not_applicable",
            semantic_role=relationship_context.semantic_role.value,
        )

    for origin_id in sorted(origin_ids):
        origin = unit_by_id.get(origin_id)
        if origin is None:
            continue
        for mention in shared_resolutions_by_origin.get(origin_id, ()):
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
            if context is None:
                continue
            semantic_role = context.semantic_role
            if semantic_role == SemanticRole.EFFECT_RESULT:
                source_text = context.atom.effect_text or context.atom.text
                semantic_outputs = _semantic_outputs(
                    semantic_role,
                    source_text,
                    _direction(source_text),
                    context.fragment_text,
                )
                if any(capability in _CAPABILITY_IDS for _kind, capability, _subject in semantic_outputs):
                    continue
                semantic_role = SemanticRole.RELATIONSHIP_METADATA
                context = replace(context, semantic_role=semantic_role)
            if context.semantic_role == SemanticRole.UNKNOWN:
                local_text = context.atom.effect_text or context.atom.text
                if _relationship_operation(local_text, mention.mention) != "references":
                    context = replace(
                        context,
                        semantic_role=SemanticRole.RELATIONSHIP_METADATA,
                    )
            block = next(
                (block for block in origin.blocks if any(token.location == mention.source_location for token in block.tokens)),
                None,
            )
            if block is None:
                continue
            child_link_at_mention = any(
                row.get("target_source_fact_id")
                and row.get("occurrence_location") == mention.source_location
                for row in resolutions
            )
            if child_link_at_mention:
                continue
            operation_text, _block_positions = _render_fragment_tokens(block.tokens)
            local_operation_text = context.atom.effect_text or context.atom.text
            operation = _relationship_operation(local_operation_text, mention.mention)
            if operation == "references":
                operation = _relationship_operation(operation_text, mention.mention)
            if (
                context.semantic_role == SemanticRole.RESOURCE_CONSUMPTION
                and mention.mechanic_class == "sidekick_resource"
                and operation in {"consumes", "spends"}
            ):
                continue
            if operation == "references" or (
                not _is_relationship_role(context.semantic_role)
                and semantic_role not in {
                    SemanticRole.UNKNOWN,
                    SemanticRole.RESOURCE_GAIN,
                    SemanticRole.RESOURCE_CONSUMPTION,
                    SemanticRole.STATE_CREATION,
                }
                and not re.search(
                    r"\b(?:select|selects|choose|chooses|branch|branches|activate|activates|"
                    r"replace|replaces|grant|grants|gain|gains|add|adds|consume|consumes|spend|spends)\b",
                    local_operation_text,
                    re.IGNORECASE,
                )
            ):
                continue
            anchor_positions = context.token_positions if context else render_structural_tokens(block.tokens)[1]
            anchor_range = (
                (token_start + mention.source_offset_start, token_start + mention.source_offset_end)
                if token_start is not None and token_end is not None and mention.source_offset_start >= 0
                else (token_start or 0, token_end or len(_clean(mention.mention)))
            )
            origin_fact_id = str(origin.source_fact_id or witness.get("record_id") or "")
            source_anchor = source_anchor_from_range(
                source_fact_id=origin_fact_id,
                source_capture_sha256=origin.source.capture_sha256,
                block=block,
                positions=anchor_positions,
                start=anchor_range[0],
                end=anchor_range[1],
            )
            source_span = SourceSpan(
                location=mention.source_location,
                block_kind=block.kind,
                ancestry=tuple(block.ancestry),
                text=mention.mention,
                character_start=anchor_range[0],
                character_end=anchor_range[1],
                source_anchor=source_anchor,
            )
            target_id = mention.mechanic_id if mention.resolution_status == "resolved" else ""
            target_kind = "shared_mechanic" if target_id else "unresolved"
            add_relationship(
                source_fact_id=mention.parent_source_fact_id or origin_fact_id,
                source_owner=mention.parent_owner_name or origin.entity_name,
                source_owner_id=(context.owner_id if context and context.owner_id else source_anchor.anchor_id),
                source_occurrence_id=_source_occurrence_for_reference(occurrences, context, token_start, token_end),
                target_kind=target_kind,
                target_id=target_id,
                candidate_target_ids=mention.candidate_mechanic_ids,
                operation=operation,
                condition=context.atom.condition if context else "",
                timing=context.atom.action_timing if context else "",
                source_span=source_span,
                resolution_status=mention.resolution_status,
                resolution_detail=mention.reason,
                resolution_basis=mention.resolution_basis,
                definition_status=mention.definition_status,
                semantic_role=(
                    context.semantic_role.value
                    if _is_relationship_role(context.semantic_role)
                    else SemanticRole.RELATIONSHIP_METADATA.value
                ),
            )

    # Some relationships are stated as local operations rather than links to
    # another source fact. Keep those relations tied to the exact operation
    # span and only emit the roles expressed by the source wording.
    root_fact_id = str(root.source_fact_id or witness.get("record_id") or "")
    for context in contexts_by_unit.get(root.unit_id, ()):
        atom_text = context.atom.effect_text or context.atom.text
        stack_state = re.search(
            r"\bstack\s+(?:(?P<count>\d+)\s+)?(?P<state>[A-Z][\w'-]*)\s+"
            r"on\s+(?P<recipient>self|user|enemy|ally|[A-Z][\w'-]*)\b",
            atom_text,
            re.IGNORECASE,
        )
        relation_specs: list[tuple[str, str, str, int, int, str]] = []
        if stack_state:
            phrase_start = stack_state.start()
            phrase_end = stack_state.end()
            source_end = context.atom.character_start + phrase_end
            if source_end < len(context.fragment_text) and context.fragment_text[source_end] == ".":
                phrase_end += 1
            operation = "applies_state" if stack_state.group("count") else "stacks"
            condition = _clean(context.atom.condition).strip(" :;,. ")
            condition = re.sub(r"^(?:when|if)\s+", "", condition, flags=re.IGNORECASE)
            if not condition and str(witness.get("record_type") or "") in {"active_skill", "skill"}:
                condition = "on skill use"
            relation_specs.append(
                (
                    operation,
                    condition,
                    "named_state",
                    phrase_start,
                    phrase_end,
                    SemanticRole.RELATIONSHIP_METADATA.value,
                )
            )

        if re.search(r"\bboth statuses\b[^.;]*\bend after\b", atom_text, re.IGNORECASE):
            lifecycle_condition = "after pain/poison damage"
            if re.search(
                r"\bcannot\s+(?:deal with|handle)\s+(?:the\s+)?(?:enemies'?|enemy'?s?)\s+"
                r"end-of-turn attacks?\b",
                context.fragment_text,
                re.IGNORECASE,
            ):
                lifecycle_condition += "; not after enemy end-of-turn attacks"
            relation_specs.append(
                (
                    "child_lifecycle",
                    lifecycle_condition,
                    "named_state",
                    0,
                    len(atom_text),
                    SemanticRole.RELATIONSHIP_METADATA.value,
                )
            )

        embedded_mechanic = re.match(
            r"\s*Link\s*:\s*(?P<definition>.+?)\s*$",
            context.fragment_text,
            re.IGNORECASE,
        )
        if embedded_mechanic:
            relation_specs.append(
                (
                    "defines_embedded_mechanic",
                    "on skill use" if str(witness.get("record_type") or "") in {"active_skill", "skill"} else "",
                    "embedded_mechanic",
                    embedded_mechanic.start("definition"),
                    embedded_mechanic.end("definition"),
                    SemanticRole.RELATIONSHIP_METADATA.value,
                )
            )

        for operation, condition, target_kind, local_start, local_end, semantic_role in relation_specs:
            start = context.atom.character_start + local_start
            end = context.atom.character_start + local_end
            source_text = context.fragment_text[start:end]
            source_span = _range_span(
                context.block,
                context.token_positions,
                start,
                end,
                source_text,
                source_fact_id=root_fact_id,
                source_capture_sha256=root.source.capture_sha256,
            )
            source_owner_id = context.owner_id or (
                context.source_span.source_anchor.anchor_id
                if context.source_span.source_anchor
                else ""
            )
            source_occurrence_id = next(
                (
                    occurrence.occurrence_id
                    for occurrence in occurrences
                    if occurrence.source_owner_id == source_owner_id
                ),
                "",
            )
            add_relationship(
                source_fact_id=root_fact_id,
                source_owner=root.entity_name or str(witness.get("entity_name") or ""),
                source_owner_id=source_owner_id,
                source_occurrence_id=source_occurrence_id,
                target_kind=target_kind,
                target_id="",
                candidate_target_ids=(),
                operation=operation,
                condition=condition,
                timing="",
                source_span=source_span,
                resolution_status="resolved",
                resolution_detail="",
                resolution_basis="explicit_source_operation",
                definition_status="embedded" if target_kind == "embedded_mechanic" else "not_applicable",
                semantic_role=semantic_role,
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
    if arm not in {"fidelity_checked", "structural_only"}:
        raise ValueError(f"unsupported classification arm: {arm}")
    if arm == "fidelity_checked":
        semantic_state = "fully_supported_input" if source_passed and fidelity_passed else "unknown_non_authoritative"
        authority = "fully_supported_input_non_authoritative" if semantic_state == "fully_supported_input" else "unknown_non_authoritative"
        admit_definitions = True
    else:
        semantic_state = "structural_only_non_authoritative"
        authority = "automatic_candidate"
        admit_definitions = False

    occurrences: list[ClassifiedOccurrence] = []
    ordinal_by_kind: Counter[str] = Counter()
    seen_dependencies: set[tuple[str, str, int | None, int | None, str]] = set()
    seen_triggers: set[tuple[str, str, int | None, int | None]] = set()
    seen_unsupported_condition_gaps: set[str] = set()
    seen_states: set[tuple[str, str, int | None, int | None]] = set()
    unit_contexts: dict[str, list[_AtomContext]] = {}
    pending_condition = ""
    pending_condition_span: SourceSpan | None = None
    pending_action_timing = ""
    pending_state_reference = ""
    pending_global_timing = ""
    pending_global_timing_span: SourceSpan | None = None
    active_state_reference = ""
    active_state_direction = ""
    branch_conditions: list[tuple[tuple[str, ...], str, SourceSpan]] = []
    unit_target_context = ""
    has_automatic_sequence = any(
        re.search(
            r"\bautomatically\s+used\s+for\s+\d+\s+actions\b",
            " ".join(token.text for token in block.tokens),
            re.IGNORECASE,
        )
        for block in unit.blocks
    )
    sequence_metadata, repeated_action_branch = _sequence_metadata(unit)
    registry = mechanic_registry or load_shared_mechanic_registry()
    zone_definition_source = _is_zone_definition_unit(unit)
    source_fact_id = str(witness.get("record_id") or unit.source_fact_id or "")
    witness_id = str(witness.get("witness_id") or "")
    shared_definition_source = zone_definition_source or any(
        entry.definition_status == "available"
        and anchor.source_fact_id == source_fact_id
        and anchor.witness_id == witness_id
        and any(alias.source_anchor_id == anchor.anchor_id for alias in entry.aliases)
        for entry in registry.entries
        for anchor in entry.source_anchors
    )
    shared_mechanic_locations = {
        mention.source_location
        for mention in resolve_shared_mechanics(
            unit,
            parent_source_fact_id=source_fact_id,
            registry=registry,
        )
        if mention.resolution_status == "resolved"
    }

    for block in unit.blocks:
        previous_target_context = ""
        active_block_state_reference = ""
        inherited_branches = sorted(
            (
                row for row in branch_conditions
                if len(block.ancestry) > len(row[0])
                and tuple(block.ancestry[:len(row[0])]) == row[0]
            ),
            key=lambda row: len(row[0]),
        )
        inherited_condition = "; ".join(dict.fromkeys(row[1] for row in inherited_branches))
        inherited_branch_context = tuple(
            row[2].source_anchor.anchor_id
            for row in inherited_branches
            if row[2].source_anchor is not None
        )
        for tokens, start, end in _tokens_to_fragments(block):
            text, token_positions = _render_fragment_tokens(tokens)
            if not text:
                continue
            contexts = _fragment_atoms(
                block,
                tokens,
                start,
                end,
                text,
                token_positions,
                source_fact_id=source_fact_id,
                source_capture_sha256=unit.source.capture_sha256,
            )
            unit_contexts.setdefault(unit.unit_id, [])
            pending_resource_metadata: dict[str, str] = {}
            consume_pending_condition = False
            for context in contexts:
                atom = context.atom
                selected_tokens = context.selected_tokens
                atom_span = context.source_span
                condition_span = context.condition_span
                timing_span = context.timing_span
                references = [token for token in selected_tokens if token.kind == "reference"]
                equipment_replacement_text = f"{atom.text} {atom.condition}".strip()
                if re.search(
                    r"\b(?:overwritten|replaced|replaces?)\b[^.;]*\bequipment\b[^.;]*"
                    r"\bbasic attack\b|\bequipment\b[^.;]*\b(?:overwritten|replaced|replaces?)\b"
                    r"[^.;]*\bbasic attack\b",
                    equipment_replacement_text,
                    re.IGNORECASE,
                ):
                    effect_text = _clean(equipment_replacement_text)
                    atom = replace(atom, effect_text=effect_text)
                    span_start = atom.character_start
                    span_end = atom.condition_end or atom.character_end
                    atom_span = _range_span(
                        context.block,
                        context.token_positions,
                        span_start,
                        span_end,
                        context.fragment_text[span_start:span_end],
                        source_fact_id=source_fact_id,
                        source_capture_sha256=unit.source.capture_sha256,
                    )
                    context = replace(context, atom=atom, source_span=atom_span)
                relationship_references = [
                    token
                    for token in references
                    if token.location not in shared_mechanic_locations
                ]
                support = _definition_support(references, resolution_by_location, admit_definitions=admit_definitions)
                effect_text = atom.effect_text
                role = _semantic_role(
                    atom,
                    relationship_references,
                    shared_definition_source=shared_definition_source,
                )
                if role == SemanticRole.CHILD_INVOCATION:
                    for resource_pattern, resource_semantic_type in (
                        (_RESOURCE_CONSUMPTION_RE, "resource_consumption"),
                        (_RESOURCE_GAIN_RE, "resource_grant"),
                    ):
                        for resource_match in resource_pattern.finditer(atom.text):
                            resource_start = atom.character_start + resource_match.start()
                            resource_end = atom.character_start + resource_match.end()
                            resource_text = context.fragment_text[resource_start:resource_end]
                            resource_span = _range_span(
                                context.block,
                                context.token_positions,
                                resource_start,
                                resource_end,
                                resource_text,
                                source_fact_id=source_fact_id,
                                source_capture_sha256=unit.source.capture_sha256,
                            )
                            occurrences.append(
                                _occurrence(
                                    kind="gap",
                                    witness=witness,
                                    span=resource_span,
                                    text=resource_text,
                                    effect_text=resource_text,
                                    ordinal=ordinal_by_kind["gap"],
                                    semantic_state=semantic_state,
                                    authority=authority,
                                    definition_support=support,
                                    references=references,
                                    condition=atom.condition,
                                    action_timing=atom.action_timing,
                                    semantic_type=resource_semantic_type,
                                    semantic_subject=_resource_subject(resource_text),
                                    semantic_role=SemanticRole.RESOURCE_CONSUMPTION
                                    if resource_semantic_type == "resource_consumption"
                                    else SemanticRole.RESOURCE_GAIN,
                                    source_owner_id=context.owner_id,
                                    branch_context=context.branch_context,
                                    action_owner_id=context.action_owner_id,
                                    gap_reason="resource operation has no canonical capability value",
                                )
                            )
                            ordinal_by_kind["gap"] += 1
                if not shared_definition_source:
                    for negative_match in re.finditer(
                        r"\b(?:when|if|unless)\s+(?:the\s+)?(?:user|target|enemy|ally)?\s*"
                        r"not\s+in\b[^.;]*",
                        context.fragment_text,
                        re.IGNORECASE,
                    ):
                        negative_text = _clean(negative_match.group(0)).rstrip(":;,. ")
                        if _NEGATIVE_STATE_ABSENCE_ANY_RE.search(atom.condition):
                            continue
                        negative_span = _range_span(
                            context.block,
                            context.token_positions,
                            negative_match.start(),
                            negative_match.end(),
                            context.fragment_text[negative_match.start():negative_match.end()],
                            source_fact_id=source_fact_id,
                            source_capture_sha256=unit.source.capture_sha256,
                        )
                        negative_anchor_id = (
                            negative_span.source_anchor.anchor_id
                            if negative_span.source_anchor is not None
                            else ""
                        )
                        if not negative_anchor_id or negative_anchor_id in seen_unsupported_condition_gaps:
                            continue
                        seen_unsupported_condition_gaps.add(negative_anchor_id)
                        owner_anchor = context.source_span.source_anchor
                        occurrences.append(
                            _occurrence(
                                kind="gap",
                                witness=witness,
                                span=negative_span,
                                text=negative_text,
                                effect_text=negative_text,
                                ordinal=ordinal_by_kind["gap"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                dependency_value="unsupported_condition",
                                semantic_type="condition",
                                condition=negative_text,
                                condition_source_span=negative_span,
                                semantic_role=SemanticRole.CONDITION,
                                source_owner_id=(
                                    context.action_owner_id
                                    or (owner_anchor.anchor_id if owner_anchor is not None else negative_anchor_id)
                                ),
                                branch_context=inherited_branch_context,
                                action_owner_id=context.action_owner_id,
                                gap_reason="negative-status absence condition has no canonical dependency value",
                            )
                        )
                        ordinal_by_kind["gap"] += 1
                if zone_definition_source:
                    role = SemanticRole.RELATIONSHIP_METADATA
                coordinated_value_span = None
                coordinated_stat = _coordinated_stat_completion(
                    context,
                    contexts,
                    source_fact_id=source_fact_id,
                    source_capture_sha256=unit.source.capture_sha256,
                )
                if coordinated_stat:
                    if role in {SemanticRole.UNKNOWN, SemanticRole.CONDITION}:
                        role = SemanticRole.EFFECT_RESULT
                    if role == SemanticRole.EFFECT_RESULT:
                        effect_text, coordinated_value_span = coordinated_stat
                if (
                    role == SemanticRole.EFFECT_RESULT
                    and any(token.location in shared_mechanic_locations for token in references)
                ):
                    shared_activation = _semantic_outputs(
                        role,
                        effect_text or atom.text,
                        _direction(effect_text or atom.text),
                        context.fragment_text,
                    )
                    if not any(
                        capability in _CAPABILITY_IDS
                        for _kind, capability, _subject in shared_activation
                    ):
                        role = SemanticRole.RELATIONSHIP_METADATA
                anchor = atom_span.source_anchor
                owner_id = anchor.anchor_id if anchor is not None else ""
                branch_context = inherited_branch_context
                if atom.condition and _is_prerequisite(atom.condition) and condition_span and condition_span.source_anchor:
                    branch_context = (*branch_context, condition_span.source_anchor.anchor_id)
                attachable_roles = {
                    SemanticRole.FORMULA,
                    SemanticRole.SEQUENCE,
                    SemanticRole.RESULT_MODIFIER,
                }
                if role in attachable_roles:
                    modifier_owner = _result_owner_for_modifier(
                        occurrences,
                        context,
                        branch_context,
                        f"{effect_text or atom.text} {atom.condition}".strip(),
                    )
                    if modifier_owner:
                        owner_id = modifier_owner
                context = replace(
                    context,
                    semantic_role=role,
                    owner_id=owner_id,
                    branch_context=branch_context,
                )
                unit_contexts[unit.unit_id].append(context)
                if role == SemanticRole.RESOURCE_CONSUMPTION:
                    pending_resource_metadata.update(_resource_metadata(effect_text or atom.text))
                effect_sequence_metadata = (
                    sequence_metadata
                    if repeated_action_branch
                    and tuple(block.ancestry[:len(repeated_action_branch)]) == repeated_action_branch
                    else {}
                )
                direction = _direction(effect_text)
                inherited_state_direction = False
                labelled_state_reference = (
                    _state_reference(effect_text)
                    if re.match(r"\s*[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2}\s*:", effect_text)
                    else ""
                )
                if (
                    direction == "unknown"
                    and labelled_state_reference
                    and labelled_state_reference == active_state_reference
                    and active_state_direction in {"ally", "self"}
                ):
                    direction = active_state_direction
                    inherited_state_direction = True
                if (
                    direction == "unknown"
                    and active_state_reference
                    and active_state_direction in {"ally", "self"}
                    and active_state_reference.casefold() in context.fragment_text.casefold()
                    and re.search(
                        r"\b(?:critical rate|power|pwr|intelligence|speed|luck|max(?:imum)?\s+hp|"
                        r"damage dealt|outgoing damage)\b",
                        effect_text,
                        re.IGNORECASE,
                    )
                ):
                    direction = active_state_direction
                    inherited_state_direction = True
                has_effect = role in {
                    SemanticRole.EFFECT_RESULT,
                    SemanticRole.RESOURCE_GAIN,
                    SemanticRole.RESOURCE_CONSUMPTION,
                    SemanticRole.STATE_CREATION,
                    SemanticRole.COST_ACTIVATION_METADATA,
                } or (
                    role == SemanticRole.CHILD_INVOCATION
                    and re.search(r"\bstellar burst\b", atom.condition, re.IGNORECASE)
                    and re.search(r"\bperform\b[^.;]*\binstead\b", effect_text, re.IGNORECASE)
                )
                condition_parts = [*([inherited_condition] if inherited_condition else [])]
                if atom.condition and atom.condition not in condition_parts:
                    condition_parts.append(atom.condition)
                effect_condition = "; ".join(condition_parts)
                effect_condition_span = condition_span or (
                    inherited_branches[-1][2] if inherited_branches else None
                )
                if direction == "unknown" and effect_condition:
                    direction = _direction(effect_condition)
                if (
                    _direction(effect_text) == "unknown"
                    and previous_target_context
                    and re.search(
                        r"\b(?:inflict(?:s|ed|ing)?|appl(?:y|ies|ied|ying)|grant(?:s|ed|ing)?)\b",
                        effect_text,
                        re.IGNORECASE,
                    )
                ):
                    direction = _direction(previous_target_context)
                effect_timing = atom.action_timing
                effect_timing_span = timing_span
                if has_effect and pending_condition:
                    if not effect_condition:
                        effect_condition = pending_condition
                        effect_condition_span = pending_condition_span
                    if not effect_timing:
                        effect_timing = pending_action_timing
                        effect_timing_span = pending_condition_span
                    consume_pending_condition = True
                if has_effect and not effect_timing and pending_action_timing:
                    effect_timing = pending_action_timing
                    effect_timing_span = pending_condition_span
                    consume_pending_condition = True
                if has_effect and pending_global_timing and not effect_timing:
                    effect_timing = pending_global_timing
                    effect_timing_span = pending_global_timing_span
                if (
                    has_effect
                    and not effect_timing
                    and (labelled_state_reference or active_block_state_reference)
                ):
                    effect_timing = "while_state_active"
                if (
                    has_effect
                    and not effect_timing
                    and witness.get("record_type") == "active_skill"
                    and not has_automatic_sequence
                ):
                    effect_timing = "on_skill_use"

                if direction == "unknown" and previous_target_context and _ANAPHORIC_TARGET_RE.search(effect_text):
                    direction = _direction(previous_target_context)
                if role == SemanticRole.RESULT_MODIFIER:
                    modifier_text = f"{atom.text} {atom.condition}".strip()
                    modifier_span = atom_span
                    modifier_condition = effect_condition
                    modifier_condition_span = effect_condition_span
                    if _HIT_COUNT_MODIFIER_RE.search(modifier_text) and _conditional_hit_counts(context.fragment_text):
                        modifier_text = context.fragment_text
                        modifier_span = _range_span(
                            context.block,
                            context.token_positions,
                            atom.character_start,
                            len(context.fragment_text),
                            context.fragment_text[atom.character_start:],
                            source_fact_id=source_fact_id,
                            source_capture_sha256=unit.source.capture_sha256,
                        )
                        consecutive = re.search(
                            r"\bwhen\s+used\s+consecutively\b",
                            context.fragment_text,
                            re.IGNORECASE,
                        )
                        if consecutive:
                            modifier_condition = _clean(consecutive.group(0))
                            modifier_condition_span = _range_span(
                                context.block,
                                context.token_positions,
                                consecutive.start(),
                                consecutive.end(),
                                consecutive.group(0),
                                source_fact_id=source_fact_id,
                                source_capture_sha256=unit.source.capture_sha256,
                            )
                    modifier_attached = _apply_result_modifier(
                        occurrences,
                        context.owner_id,
                        modifier_text,
                        modifier_span,
                        condition=modifier_condition,
                        condition_source_span=modifier_condition_span,
                    )
                    hit_delta = re.search(
                        r"\bnumber of (?:attacks|hits|(?:piercing|pierce|slash|blunt|magic|physical)\s+hits)\s+by\s+\+?(?P<increment>\d+)\b",
                        modifier_text,
                        re.IGNORECASE,
                    )
                    if not modifier_attached and hit_delta:
                        occurrences.append(
                            _occurrence(
                                kind="effect",
                                witness=witness,
                                span=atom_span,
                                text=modifier_text,
                                effect_text=modifier_text,
                                ordinal=ordinal_by_kind["effect"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                capability_value="multi_hit_action",
                                semantic_type="hit_count_modifier",
                                magnitude={
                                    "value": hit_delta.group("increment"),
                                    "unit": "additional_hits",
                                },
                                result_modifiers={
                                    "conditional_increment": hit_delta.group("increment"),
                                    "modifier_without_base_hit_owner": True,
                                },
                                condition=effect_condition or atom.condition,
                                condition_source_span=effect_condition_span,
                                semantic_role=role,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                action_owner_id=context.action_owner_id,
                                coordinated_result_group_id=atom.coordinated_result_group_id,
                                modifier_source_spans=(atom_span,),
                            )
                        )
                        ordinal_by_kind["effect"] += 1
                    elif not modifier_attached:
                        occurrences.append(
                            _occurrence(
                                kind="gap",
                                witness=witness,
                                span=atom_span,
                                text=modifier_text,
                                effect_text=modifier_text,
                                ordinal=ordinal_by_kind["effect"],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                condition=atom.condition,
                                action_timing=atom.action_timing,
                                semantic_type="unsupported_result_modifier",
                                magnitude=_magnitude(modifier_text),
                                result_modifiers={"unresolved_owner": True},
                                semantic_role=role,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                action_owner_id=context.action_owner_id,
                                coordinated_result_group_id=atom.coordinated_result_group_id,
                                modifier_source_spans=(atom_span,),
                                gap_reason="conditional result modifier has no unique supported result owner",
                            )
                        )
                        ordinal_by_kind["gap"] += 1

                if has_effect:
                    semantic_source = effect_text
                    if role in {SemanticRole.EFFECT_RESULT, SemanticRole.CHILD_INVOCATION} and (
                        effect_condition
                        and re.search(r"\bstellar burst\b", effect_condition, re.IGNORECASE)
                        and re.search(r"\bperform\b[^.;]*\binstead\b", effect_text, re.IGNORECASE)
                    ):
                        semantic_source = f"{effect_condition}: {effect_text}"
                    coordinated_context = " ".join(
                        _clean(candidate.atom.effect_text or candidate.atom.text)
                        for candidate in contexts
                        if atom.coordinated_result_group_id
                        and candidate.atom.coordinated_result_group_id
                        == atom.coordinated_result_group_id
                    )
                    for semantic_type, capability, subject in _semantic_outputs(
                        role,
                        semantic_source,
                        direction,
                        effect_text if atom.coordinated_result_group_id else context.fragment_text,
                        coordinated_context,
                    ):
                        occurrence_kind = "effect" if capability else "gap"
                        inherited_target = (
                            previous_target_context or unit_target_context
                            if semantic_type in {"resistance_reduction", "status_infliction"}
                            and _recipient_and_cardinality(effect_text)[0] == "unknown"
                            and _ANAPHORIC_TARGET_RE.search(effect_text)
                            else ""
                        )
                        if (
                            occurrence_kind == "effect"
                            and not inherited_target
                            and semantic_type in {"critical_support", "element_damage_increase", "stat_increase", "damage_modifier"}
                            and _recipient_and_cardinality(effect_text)[0] == "unknown"
                            and _ANAPHORIC_TARGET_RE.search(effect_text)
                        ):
                            inherited_target = previous_target_context
                        value = ""
                        occurrence_magnitude = _magnitude(effect_text)
                        if (
                            not occurrence_magnitude
                            and _ATTACK_RESULT_RE.search(effect_text)
                            and _formula_metadata(context.fragment_text)
                        ):
                            occurrence_magnitude = _formula_tier_magnitude(
                                context.fragment_text,
                                effect_text,
                            )
                        if semantic_type == "multi_hit_action":
                            occurrence_magnitude = {"hit_count": _hit_count(effect_text)}
                        state_context = (
                            _state_reference(effect_text)
                            or _state_reference(effect_condition)
                            or (
                                _state_reference(previous_target_context)
                                if _ANAPHORIC_TARGET_RE.search(effect_text)
                                else ""
                            )
                        )
                        max_stack = re.search(
                            r"\bmax(?:imum)?\s+stack\s*:?\s*(?:x\s*)?(\d+)\b",
                            f"{effect_text} {effect_condition}",
                            re.IGNORECASE,
                        )
                        if (
                            semantic_type in {"critical_support", "element_damage_increase"}
                            and state_context
                            and max_stack
                            and occurrence_magnitude.get("unit") == "percent"
                        ):
                            occurrence_magnitude = {
                                **occurrence_magnitude,
                                "unit": "percent_per_stack",
                                "max_stacks": max_stack.group(1),
                            }
                        if role in {
                            SemanticRole.RESOURCE_CONSUMPTION,
                            SemanticRole.RESOURCE_GAIN,
                            SemanticRole.STATE_CREATION,
                        }:
                            occurrence_resource_metadata = {}
                        else:
                            occurrence_resource_metadata = dict(pending_resource_metadata)
                            pending_resource_metadata.clear()
                        occurrence_formula_metadata = _formula_metadata(context.fragment_text)
                        attack_type_override = ""
                        if semantic_type == "damage_event" and capability == "direct_damage":
                            attack_type_override, attack_type_formula = _stance_dependent_attack_type(
                                effect_text,
                                unit.blocks,
                            )
                            if attack_type_formula:
                                occurrence_formula_metadata["attack_type_selection"] = attack_type_formula
                        occurrence_span = atom_span
                        if semantic_type == "damage_event" and capability == "direct_damage":
                            tier_only_suffix = _ATTACK_TIER_ONLY_SUFFIX_RE.search(effect_text)
                            if tier_only_suffix:
                                span_start = atom.character_start
                                span_end = span_start + tier_only_suffix.start()
                                occurrence_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    span_start,
                                    span_end,
                                    context.fragment_text[span_start:span_end],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                        if semantic_type == "multi_hit_action":
                            owning_damage = next(
                                (
                                    row
                                    for row in reversed(occurrences)
                                    if row.occurrence_kind == "effect"
                                    and row.semantic_type == "damage_event"
                                    and row.capability_value == "direct_damage"
                                    and row.source_owner_id == context.owner_id
                                ),
                                None,
                            )
                            if owning_damage is not None:
                                occurrence_span = owning_damage.source_span
                        shared_recipient_context = ""
                        if (
                            semantic_type in {"hp_recovery", "mp_recovery", "revive"}
                            and not atom.coordinated_result_group_id
                            and _recipient_and_cardinality(effect_text)[0] == "unknown"
                            and _recipient_and_cardinality(_recipient_context(context.fragment_text))[0] != "unknown"
                        ):
                            shared_recipient_context = _recipient_context(context.fragment_text)
                        if (
                            semantic_type in {"resistance_reduction", "status_infliction"}
                            and _recipient_and_cardinality(effect_text)[0] == "unknown"
                        ):
                            shared_recipient_context = _shared_attack_target(context.fragment_text)
                        if (
                            semantic_type == "burst_window"
                            and atom.condition_start is not None
                            and atom.character_start is not None
                        ):
                            span_start = min(atom.condition_start, atom.character_start)
                            occurrence_span = _range_span(
                                context.block,
                                context.token_positions,
                                span_start,
                                atom.character_end,
                                context.fragment_text[span_start:atom.character_end],
                                source_fact_id=source_fact_id,
                                source_capture_sha256=unit.source.capture_sha256,
                            )
                        if semantic_type in {"resistance_reduction", "resistance_increase"}:
                            resistance_property = _RESISTANCE_PROPERTY_RE.search(effect_text)
                            if resistance_property:
                                anchor_start = atom.character_start + resistance_property.start()
                                anchor_end = atom.character_start + resistance_property.end()
                                occurrence_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    anchor_start,
                                    anchor_end,
                                    context.fragment_text[anchor_start:anchor_end],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                        shared_duration_applies = bool(
                            atom.shared_modifier_text
                            and _SHARED_DURATION_RE.search(atom.shared_modifier_text)
                            and semantic_type not in _DURATIONLESS_RESULT_TYPES
                        )
                        shared_stack_match = _MAX_STACK_METADATA_RE.search(atom.shared_modifier_text)
                        shared_stack_applies = bool(
                            shared_stack_match
                            and semantic_type in {
                                "stat_increase",
                                "element_damage_increase",
                                "critical_support",
                                "resistance_reduction",
                            }
                        )
                        if shared_stack_applies and shared_stack_match:
                            occurrence_magnitude = {
                                **occurrence_magnitude,
                                "max_stacks": shared_stack_match.group("value"),
                            }
                        occurrences.append(
                            _occurrence(
                                kind=occurrence_kind,
                                witness=witness,
                                span=occurrence_span,
                                text=atom.text,
                                effect_text=effect_text,
                                ordinal=ordinal_by_kind[occurrence_kind],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=support,
                                references=references,
                                capability_value=capability,
                                dependency_value=value,
                                condition=effect_condition,
                                action_timing=effect_timing,
                                semantic_type=semantic_type,
                                hit_count=_hit_count(effect_text),
                                formula_metadata=occurrence_formula_metadata,
                                sequence_metadata=effect_sequence_metadata,
                                resource_metadata=occurrence_resource_metadata,
                                semantic_subject=subject,
                                attack_type_override=attack_type_override,
                                condition_source_span=effect_condition_span,
                                timing_source_span=effect_timing_span,
                                probability=_probability(effect_text),
                                state_reference=(
                                    _state_reference(effect_text)
                                    or _state_reference(effect_condition)
                                    or (
                                        _state_reference(previous_target_context)
                                        if _ANAPHORIC_TARGET_RE.search(effect_text)
                                        else ""
                                    )
                                    or pending_state_reference
                                    or active_state_reference
                                ),
                                magnitude=occurrence_magnitude,
                                field_context=(
                                    shared_recipient_context
                                    or inherited_target
                                    or (active_state_direction if inherited_state_direction else "")
                                ),
                                semantic_role=role,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                result_modifiers=(
                                    {
                                        "shared_modifiers": [
                                            *(
                                                [{
                                                    "kind": "duration",
                                                    "source_text": _SHARED_DURATION_RE.search(
                                                        atom.shared_modifier_text
                                                    ).group(0),
                                                    "group_id": atom.coordinated_result_group_id,
                                                }]
                                                if shared_duration_applies
                                                else []
                                            ),
                                            *(
                                                [{
                                                    "kind": "max_stacks",
                                                    "source_text": _MAX_STACK_METADATA_RE.search(
                                                        atom.shared_modifier_text
                                                    ).group(0),
                                                    "group_id": atom.coordinated_result_group_id,
                                                    "result_text": atom.shared_modifier_text,
                                                }]
                                                if shared_stack_applies and shared_stack_match
                                                else []
                                            ),
                                        ]
                                    }
                                    if (shared_duration_applies or shared_stack_applies)
                                    and atom.coordinated_result_group_id
                                    else {}
                                ),
                                action_owner_id=context.action_owner_id,
                                coordinated_result_group_id=atom.coordinated_result_group_id,
                                modifier_source_spans=tuple(
                                    span
                                    for span in (
                                        coordinated_value_span,
                                        context.modifier_span
                                        if (shared_duration_applies or shared_stack_applies)
                                        else None,
                                    )
                                    if span is not None
                                ),
                                duration_activation_override={
                                    **_duration_activation(effect_text),
                                    **(
                                        _duration_activation(atom.shared_modifier_text)
                                        if shared_duration_applies
                                        else {}
                                    ),
                                },
                                gap_reason=(
                                    "recognized semantic result has no canonical taxonomy value"
                                    if occurrence_kind == "gap"
                                    else ""
                                ),
                            )
                        )
                        ordinal_by_kind[occurrence_kind] += 1
                        if semantic_type == "damage_event" and capability == "direct_damage":
                            unit_target_context = effect_text
                    if any(
                        dependency_id == "requires_recipient_eligibility"
                        for dependency_id, _scope in _dependency_values(effect_text)
                    ):
                        recipient_scope = _recipient_and_cardinality(effect_text)[0]
                        equipment = re.match(r"characters equipped with (.+)", recipient_scope, re.IGNORECASE)
                        if equipment:
                            equipment_text = equipment.group(1)
                            dependency_condition = f"recipient has {equipment_text} equipped"
                            dependency_key = (
                                atom_span.location,
                                dependency_condition,
                                atom.character_start,
                                atom.character_end,
                                "requires_recipient_eligibility",
                            )
                            if dependency_key not in seen_dependencies:
                                seen_dependencies.add(dependency_key)
                                occurrences.append(
                                    _occurrence(
                                        kind="dependency",
                                        witness=witness,
                                        span=atom_span,
                                        text=f"When {dependency_condition}",
                                        effect_text=f"Recipient is equipped with {equipment_text}",
                                        ordinal=ordinal_by_kind["dependency"],
                                        semantic_state=semantic_state,
                                        authority=authority,
                                        definition_support=support,
                                        references=references,
                                        condition=dependency_condition,
                                        action_timing="",
                                        dependency_value="requires_recipient_eligibility",
                                        semantic_type="condition",
                                        field_context=effect_text,
                                        state_reference="",
                                        condition_source_span=atom_span,
                                        semantic_role=role,
                                        source_owner_id=context.owner_id,
                                        branch_context=context.branch_context,
                                        action_owner_id=context.action_owner_id,
                                    )
                                )
                                ordinal_by_kind["dependency"] += 1
                    if _recipient_and_cardinality(effect_text)[0] != "unknown":
                        previous_target_context = effect_text
                    if labelled_state_reference:
                        active_state_reference = labelled_state_reference
                        active_block_state_reference = labelled_state_reference

                relationship_condition = (
                    has_effect
                    and bool(re.search(r"\bactivate(?:s|d|ing)?\b", effect_text, re.IGNORECASE))
                    and bool(references)
                )
                if atom.condition and _is_prerequisite(atom.condition) and not shared_definition_source:
                    dependency_condition = _clean(atom.condition).rstrip(":;,. ")
                    condition_references = [
                        token for token, token_start, token_end in token_positions
                        if atom.condition_start is not None
                        and token_start < (atom.condition_end or token_end)
                        and token_end > atom.condition_start
                        and token.kind == "reference"
                    ]
                    existing_condition_values = {
                        value for value, _scope in _dependency_values(dependency_condition)
                    }
                    has_unknown_active_state_condition = bool(
                        re.match(
                            r"\s*(?:when|if|unless)\s+(?:the\s+)?"
                            r"[\w'-]+(?:\s+[\w'-]+){0,2}\s+is\s+active\b",
                            dependency_condition,
                            re.IGNORECASE,
                        )
                    )
                    if (
                        not existing_condition_values
                        and has_unknown_active_state_condition
                        and atom.condition_start is not None
                    ):
                        unsupported_condition_key = (
                            atom_span.location,
                            dependency_condition,
                            atom.condition_start,
                            atom.condition_end,
                        )
                        if unsupported_condition_key not in seen_dependencies:
                            seen_dependencies.add(unsupported_condition_key)
                            unsupported_condition_span = condition_span or _range_span(
                                context.block,
                                context.token_positions,
                                atom.condition_start,
                                atom.condition_end or atom.condition_start,
                                atom.condition,
                                source_fact_id=source_fact_id,
                                source_capture_sha256=unit.source.capture_sha256,
                            )
                            occurrences.append(
                                _occurrence(
                                    kind="gap",
                                    witness=witness,
                                    span=unsupported_condition_span,
                                    text=dependency_condition,
                                    effect_text=dependency_condition,
                                    ordinal=ordinal_by_kind["gap"],
                                    semantic_state=semantic_state,
                                    authority=authority,
                                    definition_support=support,
                                    references=condition_references,
                                    condition=dependency_condition,
                                    action_timing="",
                                    semantic_type="condition",
                                    condition_source_span=unsupported_condition_span,
                                    semantic_role=SemanticRole.CONDITION,
                                    source_owner_id=context.action_owner_id or context.owner_id,
                                    branch_context=context.branch_context,
                                    action_owner_id=context.action_owner_id,
                                    gap_reason="prerequisite condition has no canonical dependency value",
                                )
                            )
                            ordinal_by_kind["gap"] += 1
                    if "unsupported_condition" not in existing_condition_values and atom.condition_start is not None:
                        for negative_match in re.finditer(
                            r"(?:^|;)\s*(?P<condition>(?:when|if|unless)\s+(?:the\s+)?(?:user|target|enemy|ally)?\s*not\s+in\b[^;]*)",
                            atom.condition,
                            re.IGNORECASE,
                        ):
                            negative_text = _clean(negative_match.group("condition")).rstrip(":;,. ")
                            relative_start = negative_match.start("condition")
                            relative_end = negative_match.end("condition")
                            negative_span = _range_span(
                                context.block,
                                context.token_positions,
                                atom.condition_start + relative_start,
                                atom.condition_start + relative_end,
                                atom.condition[relative_start:relative_end],
                                source_fact_id=source_fact_id,
                                source_capture_sha256=unit.source.capture_sha256,
                            )
                            negative_key = (
                                atom_span.location,
                                negative_text,
                                negative_span.character_start,
                                negative_span.character_end,
                                "unsupported_condition",
                            )
                            if negative_key in seen_dependencies:
                                continue
                            seen_dependencies.add(negative_key)
                            occurrences.append(
                                _occurrence(
                                    kind="gap",
                                    witness=witness,
                                    span=negative_span,
                                    text=negative_text,
                                    ordinal=ordinal_by_kind["gap"],
                                    semantic_state=semantic_state,
                                    authority=authority,
                                    definition_support=support,
                                    references=condition_references,
                                    effect_text=negative_text,
                                    condition=negative_text,
                                    action_timing="",
                                    dependency_value="unsupported_condition",
                                    semantic_type="condition",
                                    condition_source_span=negative_span,
                                    semantic_role=SemanticRole.CONDITION,
                                    source_owner_id=context.owner_id,
                                    branch_context=context.branch_context,
                                    action_owner_id=context.action_owner_id,
                                    gap_reason="negative-status absence condition has no canonical dependency value",
                                )
                            )
                            ordinal_by_kind["gap"] += 1
                    for dependency_value, dependency_scope in _dependency_values(dependency_condition):
                        local_condition = dependency_condition
                        compound_dependency = bool(
                            re.search(r"\band\b", dependency_condition, re.IGNORECASE)
                        )
                        if compound_dependency:
                            local_condition = f"When {dependency_scope.strip(' :;,.')}"
                        dependency_span = condition_span or atom_span
                        if dependency_value == "party_composition" and atom.condition_start is not None:
                            party_scope = re.search(
                                r"(?:^|;)\s*(?P<condition>(?:when\s+)?[^;]*?\b(?:frontline|front\s+line|at\s+front|party\s+composition)\b)",
                                atom.condition,
                                re.IGNORECASE,
                            )
                            if party_scope:
                                scoped_condition = party_scope.group("condition")
                                party_clause = re.search(
                                    r"\band\s+(?P<condition>(?:(?:when|if)\s+)?"
                                    r"[^;]*?\b(?:frontline|front\s+line|at\s+front|party\s+composition)\b)",
                                    atom.condition,
                                    re.IGNORECASE,
                                ) if compound_dependency else None
                                if party_clause:
                                    scoped_condition = party_clause.group("condition")
                                    scope_start = atom.condition_start + party_clause.start("condition")
                                    scope_end = atom.condition_start + party_clause.end("condition")
                                else:
                                    scoped_condition = (
                                        dependency_condition
                                        if ";" in dependency_condition
                                        else party_scope.group("condition")
                                    )
                                    scope_start = atom.condition_start + party_scope.start("condition")
                                    scope_end = atom.condition_start + party_scope.end("condition")
                                local_condition = _clean(scoped_condition).rstrip(":;,. ")
                                if compound_dependency and not re.match(r"(?:when|if)\b", local_condition, re.IGNORECASE):
                                    local_condition = f"When {local_condition}"
                                dependency_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    scope_start,
                                    scope_end,
                                    atom.condition[scope_start - atom.condition_start:scope_end - atom.condition_start],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                        if dependency_value == "requires_zone" and ";" in atom.condition and atom.condition_start is not None:
                            for clause_match in re.finditer(r"[^;]+", atom.condition):
                                clause_text = _clean(clause_match.group(0)).rstrip(":;,. ")
                                if not any(value == "requires_zone" for value, _scope in _dependency_values(clause_text)):
                                    continue
                                scope_start = atom.condition_start + clause_match.start()
                                scope_end = atom.condition_start + clause_match.end()
                                local_condition = clause_text
                                dependency_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    scope_start,
                                    scope_end,
                                    atom.condition[clause_match.start():clause_match.end()],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                                break
                        if dependency_value == "requires_stellar_awakened" and atom.condition_start is not None:
                            stellar_requirement = re.search(
                                r"\brequires?\s+stellar\s+(?:awakening|awakened)\b",
                                atom.condition,
                                re.IGNORECASE,
                            )
                            if stellar_requirement:
                                scope_start = atom.condition_start + stellar_requirement.start()
                                scope_end = atom.condition_start + stellar_requirement.end()
                                dependency_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    scope_start,
                                    scope_end,
                                    atom.condition[stellar_requirement.start():stellar_requirement.end()],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                        if compound_dependency:
                            scope_match = re.search(
                                re.escape(dependency_scope.strip(" :;,.")),
                                atom.condition,
                                re.IGNORECASE,
                            )
                            if scope_match and atom.condition_start is not None:
                                scope_start = atom.condition_start + scope_match.start()
                                scope_end = atom.condition_start + scope_match.end()
                                dependency_span = _range_span(
                                    context.block,
                                    context.token_positions,
                                    scope_start,
                                    scope_end,
                                    atom.condition[scope_match.start():scope_match.end()],
                                    source_fact_id=source_fact_id,
                                    source_capture_sha256=unit.source.capture_sha256,
                                )
                        condition_key = (
                            atom_span.location,
                            local_condition,
                            atom.condition_start,
                            atom.condition_end,
                            dependency_value,
                        )
                        if condition_key in seen_dependencies:
                            continue
                        seen_dependencies.add(condition_key)
                        if dependency_value == "unsupported_condition" and context.action_owner_id:
                            gap_owners = [
                                index
                                for index, row in enumerate(occurrences)
                                if row.occurrence_kind == "gap"
                                and row.action_owner_id == context.action_owner_id
                            ]
                            if gap_owners:
                                for index in gap_owners:
                                    row = occurrences[index]
                                    conditions = [
                                        part
                                        for part in (row.condition, local_condition)
                                        if part
                                    ]
                                    modifier_spans = list(row.modifier_source_spans)
                                    if dependency_span not in modifier_spans:
                                        modifier_spans.append(dependency_span)
                                    occurrences[index] = replace(
                                        row,
                                        condition="; ".join(dict.fromkeys(conditions)),
                                        condition_source_span=dependency_span,
                                        modifier_source_spans=tuple(modifier_spans),
                                    )
                                continue
                        field_context = dependency_condition
                        if dependency_value == "requires_stack" and re.match(r"\s*charge\b", dependency_scope, re.IGNORECASE):
                            field_context = "self"
                        elif dependency_value == "requires_stellar_awakened":
                            field_context = "self"
                        dependency_kind = (
                            "dependency" if dependency_value in _DEPENDENCY_IDS else "gap"
                        )
                        occurrences.append(
                            _occurrence(
                                kind=dependency_kind,
                                witness=witness,
                                span=dependency_span,
                                text=atom.condition,
                                ordinal=ordinal_by_kind[dependency_kind],
                                semantic_state=semantic_state,
                                authority=authority,
                                definition_support=_definition_support(
                                    condition_references,
                                    resolution_by_location,
                                    admit_definitions=admit_definitions,
                                ),
                                references=condition_references,
                                effect_text=dependency_scope,
                                condition=local_condition,
                                action_timing="",
                                dependency_value=dependency_value,
                                semantic_type="condition",
                                magnitude=_dependency_magnitude(dependency_condition, dependency_value),
                                condition_source_span=dependency_span,
                                field_context=field_context,
                                semantic_role=SemanticRole.CONDITION,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                action_owner_id=context.action_owner_id,
                                gap_reason=(
                                    "recognized condition has no canonical dependency value"
                                    if dependency_kind == "gap"
                                    else ""
                                ),
                            )
                        )
                        ordinal_by_kind[dependency_kind] += 1

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
                                semantic_role=SemanticRole.TRIGGER_TIMING,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                action_owner_id=context.action_owner_id,
                            )
                        )
                        ordinal_by_kind["trigger"] += 1

                if atom.action_timing and not has_effect and block.kind != "root":
                    trigger_text = re.sub(
                        r"^aura activation condition\s*:\s*",
                        "",
                        _clean(atom.text),
                        flags=re.IGNORECASE,
                    ).rstrip(":")
                    if trigger_text and atom.action_timing == "after_each_attacking_move":
                        pending_condition = ""
                        pending_condition_span = atom_span
                        pending_action_timing = atom.action_timing
                        pending_state_reference = _state_reference(atom.text)
                        active_state_reference = pending_state_reference or active_state_reference
                    elif trigger_text:
                        pending_condition = trigger_text
                        pending_condition_span = atom_span
                        pending_action_timing = (
                            "" if atom.action_timing == "on_use" else atom.action_timing
                        )
                        if atom.action_timing == "on_stellar_burst":
                            pending_condition = "during Stellar Burst"
                if (
                    atom.condition
                    and not has_effect
                    and _is_prerequisite(atom.condition)
                    and not shared_definition_source
                ):
                    branch_condition = _clean(atom.condition).rstrip(":;,. ")
                    branch_span = condition_span or atom_span
                    branch = (tuple(block.ancestry), branch_condition, branch_span)
                    if branch not in branch_conditions:
                        branch_conditions.append(branch)
                if block.kind == "root" and atom.action_timing:
                    if re.match(
                        r"\s*aura activation condition\s*:",
                        atom.text,
                        re.IGNORECASE,
                    ):
                        pending_condition = atom.condition
                        pending_condition_span = condition_span or atom_span
                        pending_action_timing = atom.action_timing
                        pending_state_reference = _state_reference(atom.condition)
                        active_state_reference = pending_state_reference or active_state_reference
                    elif atom.action_timing == "aura_activation" and atom.condition:
                        pending_condition = atom.condition
                        pending_condition_span = condition_span or atom_span
                        pending_action_timing = _trigger(atom.condition)
                    else:
                        pending_global_timing = atom.action_timing
                        pending_global_timing_span = timing_span or atom_span

                state_text = (
                    atom.condition
                    or (effect_text or atom.text)
                    if role != SemanticRole.RELATIONSHIP_METADATA
                    else ""
                )
                formula_text = atom.text if role == SemanticRole.FORMULA else effect_text
                formula_note = _formula_metadata(formula_text)
                if role == SemanticRole.FORMULA and formula_note and context.owner_id:
                    tier = re.search(r"\b(XXL|XL|L|M|S)\b", formula_text, re.IGNORECASE)
                    for occurrence_index in range(len(occurrences) - 1, -1, -1):
                        previous_occurrence = occurrences[occurrence_index]
                        tiered_magnitude = _formula_tier_magnitude(
                            formula_text,
                            previous_occurrence.source_text,
                        )
                        if (
                            previous_occurrence.occurrence_kind == "effect"
                            and (
                                previous_occurrence.source_owner_id == context.owner_id
                                or previous_occurrence.action_owner_id == context.owner_id
                                or (
                                    context.action_owner_id
                                    and previous_occurrence.action_owner_id == context.action_owner_id
                                )
                            )
                            and (
                                previous_occurrence.capability_value in {"direct_damage", "grant_link"}
                                or tiered_magnitude
                                or (
                                    formula_note.get("result_scaling_note")
                                    and previous_occurrence.semantic_type in {
                                        "resistance_reduction",
                                        "resistance_increase",
                                    }
                                )
                            )
                        ):
                            merged_formula = dict(previous_occurrence.formula_metadata)
                            merged_formula.update(formula_note)
                            magnitude = dict(tiered_magnitude or previous_occurrence.magnitude)
                            if tier and previous_occurrence.capability_value == "direct_damage":
                                magnitude["tier"] = tier.group(1).upper()
                            modifier_spans = list(previous_occurrence.modifier_source_spans)
                            if atom_span not in modifier_spans:
                                modifier_spans.append(atom_span)
                            occurrences[occurrence_index] = replace(
                                previous_occurrence,
                                formula_metadata=merged_formula,
                                magnitude=magnitude,
                                modifier_source_spans=tuple(modifier_spans),
                            )
                            if not _EACH_PART_FORMULA_RE.search(formula_text):
                                break
                state_reference = (
                    ""
                    if _SEQUENCE_INTERRUPTION_RE.search(state_text)
                    else _state_reference(state_text)
                )
                if state_reference:
                    if direction in {"ally", "self"}:
                        active_state_direction = direction
                        if role == SemanticRole.STATE_CREATION:
                            active_state_reference = state_reference
                    if re.search(
                        r"\b(?:skill\s+)?(?:multiplier|damage)\s+increases?\s+based on\b",
                        state_text,
                        re.IGNORECASE,
                    ):
                        for occurrence_index in range(len(occurrences) - 1, -1, -1):
                            previous_occurrence = occurrences[occurrence_index]
                            if (
                                previous_occurrence.occurrence_kind == "effect"
                                and previous_occurrence.capability_value == "direct_damage"
                                and previous_occurrence.state_reference == ""
                                and previous_occurrence.source_fact_id == source_fact_id
                            ):
                                occurrences[occurrence_index] = replace(
                                    previous_occurrence,
                                    state_reference=state_reference,
                                )
                                break
                    state_span = condition_span or atom_span
                    state_key = (
                        state_span.location,
                        state_reference,
                        state_span.character_start,
                        state_span.character_end,
                    )
                    if state_key not in seen_states:
                        seen_states.add(state_key)
                        occurrences.append(
                            _occurrence(
                                kind="state",
                                witness=witness,
                                span=state_span,
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
                                semantic_role=role,
                                source_owner_id=context.owner_id,
                                branch_context=context.branch_context,
                                action_owner_id=context.action_owner_id,
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
                    text=token.text,
                    character_start=token_start,
                    character_end=token_end,
                    source_anchor=source_anchor_from_range(
                        source_fact_id=source_fact_id,
                        source_capture_sha256=unit.source.capture_sha256,
                        block=block,
                        positions=token_positions,
                        start=token_start,
                        end=token_end,
                    ),
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
                        semantic_role=role,
                        source_owner_id=context.owner_id,
                        branch_context=context.branch_context,
                        action_owner_id=context.action_owner_id,
                    )
                )
                ordinal_by_kind["reference"] += 1

            if consume_pending_condition:
                pending_condition = ""
                pending_condition_span = None
                pending_action_timing = ""
                pending_state_reference = ""
    deduplicated_occurrences: list[ClassifiedOccurrence] = []
    gap_index_by_anchor: dict[str, int] = {}
    for row in occurrences:
        anchor = row.source_span.source_anchor
        anchor_id = anchor.anchor_id if anchor is not None else ""
        if row.occurrence_kind == "gap" and row.semantic_type == "condition" and anchor_id in gap_index_by_anchor:
            index = gap_index_by_anchor[anchor_id]
            previous = deduplicated_occurrences[index]
            if previous.source_owner_id == previous.action_owner_id and row.source_owner_id != row.action_owner_id:
                deduplicated_occurrences[index] = row
            continue
        if row.occurrence_kind == "gap" and row.semantic_type == "condition" and anchor_id:
            gap_index_by_anchor[anchor_id] = len(deduplicated_occurrences)
        deduplicated_occurrences.append(row)
    occurrences = deduplicated_occurrences
    _inherit_coordinated_result_fields(occurrences)
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
        "effect_occurrence_count": counts.get("effect", 0),
        "dependency_occurrence_count": counts.get("dependency", 0),
        "explicit_gap_occurrence_count": counts.get("gap", 0),
        "occurrence_kind_counts": dict(sorted(counts.items())),
        "authority_counts": dict(sorted(authority.items())),
        "relationship_count": len(relation_rows),
        "occurrences": rows,
        "relationships": relation_rows,
    }


_COMPATIBILITY_FIELDS = (
    "occurrence_kind",
    "operation",
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
    "hit_count",
    "formula_metadata",
    "sequence_metadata",
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
            "occurrence_operation_is_explicit": True,
            "unmapped_semantics_are_explicit_taxonomy_gaps": True,
            "relationship_contract": {
                "target_kinds": ["source_fact", "shared_mechanic", "unresolved"],
                "local_condition_and_timing": True,
                "unresolved_targets_remain_unresolved": True,
                "definition_semantics_are_not_copied": True,
                "report_adapter_owner_key": "source_occurrence_id",
                "unattached_rows_are_retained_as_unresolved": True,
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
