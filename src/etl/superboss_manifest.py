"""Versioned, bounded Feature G1 superboss source-manifest access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


MANIFEST_PATH = Path(__file__).with_name("superboss_manifest.json")
COHORTS = ("weak", "medium", "strong")
PENDING_FETCH_STATUS = "proposed_pending_live_fetch"
CACHED_REPAIR_STATUS = "cached_pending_repair"
READY_STATUS = "recommendation_ready"


def load_superboss_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load the checked-in manifest without consulting the wiki or credentials."""
    return json.loads(path.read_text(encoding="utf-8"))


def validate_superboss_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return deterministic contract errors; discovery metadata never grants support."""
    errors: list[str] = []
    bosses = manifest.get("bosses", [])
    if len(bosses) != 30:
        errors.append(f"expected exactly 30 manifest records, found {len(bosses)}")
    ids = [row.get("canonical_id") for row in bosses]
    if any(not value for value in ids):
        errors.append("every record requires canonical_id")
    if len(set(ids)) != len(ids):
        errors.append("canonical_id is duplicated")
    cohorts = {cohort: [row for row in bosses if row.get("cohort") == cohort] for cohort in COHORTS}
    for cohort, rows in cohorts.items():
        if len(rows) != 10:
            errors.append(f"{cohort} cohort requires exactly 10 records, found {len(rows)}")
        policy = manifest.get("cohorts", {}).get(cohort, {})
        for row in rows:
            try:
                difficulty = float(row["difficulty_tier"])
                if not policy["difficulty_min"] <= difficulty <= policy["difficulty_max"]:
                    errors.append(f"{row.get('name')} is outside {cohort} difficulty band")
            except (KeyError, TypeError, ValueError):
                errors.append(f"{row.get('name')} has invalid difficulty metadata")
    names_by_cohort: dict[str, set[str]] = {}
    for cohort, rows in cohorts.items():
        names_by_cohort[cohort] = {str(row.get("canonical_id")) for row in rows}
    for index, cohort in enumerate(COHORTS):
        for later in COHORTS[index + 1:]:
            overlap = names_by_cohort[cohort] & names_by_cohort[later]
            if overlap:
                errors.append(f"canonical identity crosses cohorts: {sorted(overlap)}")
    fetch_policy = manifest.get("fetch_policy", {})
    if fetch_policy.get("bounded_detail_page_limit") != 30:
        errors.append("bounded detail-page fetch limit must remain 30")
    if fetch_policy.get("new_candidate_fetch_limit") != 25:
        errors.append("new candidate fetch limit must remain 25")
    if fetch_policy.get("cached_refresh_limit") != 5:
        errors.append("cached weak-boss refresh limit must remain 5")
    pending_count = sum(row.get("support_status") == PENDING_FETCH_STATUS for row in bosses)
    cached_pending_count = sum(row.get("support_status") == CACHED_REPAIR_STATUS for row in bosses)
    ready_count = sum(row.get("support_status") == READY_STATUS for row in bosses)
    if (pending_count, cached_pending_count, ready_count) not in {(25, 5, 0), (0, 0, 30)}:
        errors.append("manifest must be either prefetch (25 pending + 5 cached repair) or final (30 recommendation-ready)")
    if any(not row.get("section_anchor") for row in bosses):
        errors.append("every admitted or pending record requires an explicit section anchor")
    rationale_keys = {"mechanics", "affinity", "parser", "page_section", "discord_beta_review"}
    if any(set(row.get("selection_rationale", {})) != rationale_keys for row in bosses):
        errors.append("every record requires the five diversity selection-rationale fields")
    return errors


def manifest_records(
    *,
    statuses: Iterable[str] | None = None,
    path: Path = MANIFEST_PATH,
) -> list[dict[str, Any]]:
    """Return a copy of the explicit allowlist for a caller-owned bounded run."""
    manifest = load_superboss_manifest(path)
    errors = validate_superboss_manifest(manifest)
    if errors:
        raise ValueError("Invalid superboss source manifest: " + "; ".join(errors))
    allowed = set(statuses) if statuses is not None else None
    return [
        dict(row)
        for row in manifest["bosses"]
        if allowed is None or row.get("support_status") in allowed
    ]


def proposed_live_fetch_records(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    """Return only the 25 records that require the explicit human checkpoint."""
    return manifest_records(statuses={PENDING_FETCH_STATUS}, path=path)
