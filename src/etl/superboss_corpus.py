"""Build and validate the committed Feature G1.1 superboss corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .constants import ETL_SCHEMA_VERSION, PARSED_SUPERBOSS_DIR
from .models import SuperbossIndexRow, SuperbossRow
from .scraper import parse_superboss_detail
from .superboss_manifest import (
    CORPUS_VERSION,
    MANIFEST_PATH,
    READY_STATUS,
    load_superboss_manifest,
    validate_superboss_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSER_POLICY_VERSION = "g1.1.0"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _resolve_capture_path(raw_path: str, repository_root: Path) -> Path:
    path = Path(raw_path)
    resolved = path if path.is_absolute() else repository_root / path
    resolved = resolved.resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise ValueError(f"Superboss capture escapes repository root: {raw_path}") from exc
    return resolved


def _manifest_records(manifest_path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    manifest = load_superboss_manifest(manifest_path)
    errors = validate_superboss_manifest(manifest)
    if errors:
        raise ValueError("Invalid superboss source manifest: " + "; ".join(errors))
    records = [
        dict(record)
        for record in manifest["bosses"]
        if record.get("support_status") == READY_STATUS
    ]
    if len(records) != 30:
        raise ValueError(f"G1.1 requires exactly 30 recommendation-ready bosses, found {len(records)}")
    return records


def _capture_records(
    manifest_path: Path = MANIFEST_PATH,
    *,
    repository_root: Path = PROJECT_ROOT,
) -> list[tuple[dict[str, Any], Path, str]]:
    records = _manifest_records(manifest_path)
    seen_paths: set[str] = set()
    captures: list[tuple[dict[str, Any], Path, str]] = []
    for record in records:
        canonical_id = str(record.get("canonical_id") or "")
        capture_path_text = str(record.get("capture_path") or "")
        expected_sha = str(record.get("capture_sha256") or "")
        if not canonical_id or not capture_path_text or not expected_sha:
            raise ValueError(f"Manifest capture metadata is incomplete for {record.get('name')}")
        capture_path = _resolve_capture_path(capture_path_text, repository_root)
        if str(capture_path) in seen_paths:
            raise ValueError(f"Manifest capture path is duplicated: {capture_path_text}")
        seen_paths.add(str(capture_path))
        if capture_path.stem != canonical_id:
            raise ValueError(
                f"Manifest capture filename must be keyed by canonical_id: {canonical_id} -> {capture_path.name}"
            )
        if not capture_path.exists():
            raise FileNotFoundError(f"Missing committed superboss capture for {canonical_id}: {capture_path_text}")
        actual_sha = _sha256_bytes(capture_path.read_bytes())
        if actual_sha != expected_sha:
            raise ValueError(
                f"Superboss capture checksum mismatch for {canonical_id}: "
                f"expected {expected_sha}, found {actual_sha}"
            )
        captures.append((record, capture_path, actual_sha))
    return captures


def _build_row(record: dict[str, Any], capture_path: Path) -> SuperbossRow:
    candidate = SuperbossIndexRow.model_validate(record)
    source_url = str(record["source_url"])
    soup = BeautifulSoup(capture_path.read_text(encoding="utf-8"), "html.parser")
    row = parse_superboss_detail(soup, candidate, source_url=source_url)
    if row.name != record["name"] or row.canonical_id != record["canonical_id"]:
        raise ValueError(
            f"Superboss capture identity mismatch for {record['canonical_id']}: "
            f"parsed {row.canonical_id}/{row.name}"
        )
    if row.source_url != source_url:
        raise ValueError(f"Superboss source URL mismatch for {record['canonical_id']}")
    if row.section_anchor != record.get("section_anchor"):
        raise ValueError(f"Superboss section anchor mismatch for {record['canonical_id']}")
    if row.section_end_anchor != record.get("section_end_anchor"):
        raise ValueError(f"Superboss section end anchor mismatch for {record['canonical_id']}")
    if not row.section_bounded or not row.mechanics_text.strip() or not row.recommendation_ready:
        raise ValueError(f"Superboss capture is not recommendation-ready for {record['canonical_id']}")
    return row


def _payload(record: dict[str, Any], capture_path: Path, capture_sha256: str) -> dict[str, Any]:
    row = _build_row(record, capture_path)
    provenance = {
        **row.provenance,
        "source_capture_path": record["capture_path"],
        "source_capture_sha256": capture_sha256,
        "parser_policy_version": PARSER_POLICY_VERSION,
        "corpus_version": CORPUS_VERSION,
    }
    mechanics_evidence = {
        **row.mechanics_evidence,
        "source_capture_path": record["capture_path"],
        "source_capture_sha256": capture_sha256,
        "parser_policy_version": PARSER_POLICY_VERSION,
        "corpus_version": CORPUS_VERSION,
    }
    row = row.model_copy(update={"provenance": provenance, "mechanics_evidence": mechanics_evidence})
    return {
        "schema_version": ETL_SCHEMA_VERSION,
        "kind": "superboss_detail",
        "source_capture_path": record["capture_path"],
        "source_capture_sha256": capture_sha256,
        "parser_policy_version": PARSER_POLICY_VERSION,
        "corpus_version": CORPUS_VERSION,
        "rows": [row.model_dump(mode="json")],
        "parsed_counts": {
            "superbosses": 1,
            "mechanics_text_chars": len(row.mechanics_text),
            "section_bounded": int(row.section_bounded),
            "recommendation_ready": int(row.recommendation_ready),
        },
        "quality_status": "ok",
    }


def _corpus_fingerprint(artifacts: list[dict[str, Any]]) -> str:
    normalized = [
        {
            "canonical_id": artifact["rows"][0]["canonical_id"],
            "source_capture_path": artifact["source_capture_path"],
            "source_capture_sha256": artifact["source_capture_sha256"],
            "row": artifact["rows"][0],
        }
        for artifact in artifacts
    ]
    normalized.sort(key=lambda value: value["canonical_id"])
    return _sha256_bytes(_canonical_json(normalized).encode("utf-8"))


def validate_parsed_superboss_corpus(
    parsed_dir: Path = PARSED_SUPERBOSS_DIR,
    *,
    manifest_path: Path = MANIFEST_PATH,
    repository_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Fail closed unless parsed artifacts exactly match the manifest captures."""
    captures = _capture_records(manifest_path, repository_root=repository_root)
    expected_filenames = {f"{record['canonical_id']}.json" for record, _, _ in captures}
    actual_filenames = {path.name for path in parsed_dir.glob("*.json")}
    missing = sorted(expected_filenames - actual_filenames)
    extra = sorted(actual_filenames - expected_filenames)
    if missing or extra:
        raise RuntimeError(
            "G1.1 parsed superboss corpus is incomplete: "
            f"missing={missing}, extra={extra}"
        )

    artifacts: list[dict[str, Any]] = []
    rows_by_id: dict[str, SuperbossRow] = {}
    expected_by_id = {record["canonical_id"]: record for record, _, _ in captures}
    for record, _, capture_sha256 in captures:
        canonical_id = record["canonical_id"]
        path = parsed_dir / f"{canonical_id}.json"
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unreadable G1.1 parsed superboss artifact: {path}") from exc
        if artifact.get("schema_version") != ETL_SCHEMA_VERSION:
            raise RuntimeError(f"Stale G1.1 parsed superboss artifact: {path}")
        if artifact.get("kind") != "superboss_detail":
            raise RuntimeError(f"Wrong artifact kind for G1.1 superboss: {path}")
        if artifact.get("source_capture_path") != record["capture_path"]:
            raise RuntimeError(f"Parsed superboss source path mismatch for {canonical_id}")
        if artifact.get("source_capture_sha256") != capture_sha256:
            raise RuntimeError(f"Stale G1.1 superboss capture fingerprint for {canonical_id}")
        if artifact.get("parser_policy_version") != PARSER_POLICY_VERSION:
            raise RuntimeError(f"Stale G1.1 superboss parser policy for {canonical_id}")
        if artifact.get("corpus_version") != CORPUS_VERSION:
            raise RuntimeError(f"Stale G1.1 superboss corpus version for {canonical_id}")
        rows = artifact.get("rows")
        if not isinstance(rows, list) or len(rows) != 1:
            raise RuntimeError(f"G1.1 superboss artifact must contain one row: {canonical_id}")
        try:
            row = SuperbossRow.model_validate(rows[0])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Invalid G1.1 parsed superboss row: {canonical_id}") from exc
        if row.canonical_id in rows_by_id:
            raise RuntimeError(f"Duplicate parsed superboss canonical_id: {row.canonical_id}")
        if row.canonical_id != canonical_id or row.name != record["name"]:
            raise RuntimeError(f"Parsed superboss identity mismatch for {canonical_id}")
        for field in ("source_url", "section_anchor", "section_end_anchor", "cohort"):
            if getattr(row, field) != record.get(field):
                raise RuntimeError(f"Parsed superboss {field} mismatch for {canonical_id}")
        if (
            not row.section_bounded
            or not row.mechanics_text.strip()
            or not row.recommendation_ready
            or row.support_status != READY_STATUS
        ):
            raise RuntimeError(f"Parsed superboss is not recommendation-ready for {canonical_id}")
        counts = artifact.get("parsed_counts", {})
        if (
            counts.get("superbosses") != 1
            or counts.get("mechanics_text_chars") != len(row.mechanics_text)
            or counts.get("section_bounded") != 1
            or counts.get("recommendation_ready") != 1
        ):
            raise RuntimeError(f"Parsed superboss quality counts mismatch for {canonical_id}")
        if canonical_id in rows_by_id:
            raise RuntimeError(f"Duplicate parsed superboss canonical_id: {canonical_id}")
        rows_by_id[canonical_id] = row
        artifacts.append(artifact)

    cohort_counts = {
        cohort: sum(row.cohort == cohort for row in rows_by_id.values())
        for cohort in ("weak", "medium", "strong")
    }
    if cohort_counts != {"weak": 10, "medium": 10, "strong": 10}:
        raise RuntimeError(f"G1.1 parsed superboss cohorts must be 10/10/10: {cohort_counts}")
    return {
        "corpus_version": CORPUS_VERSION,
        "parser_policy_version": PARSER_POLICY_VERSION,
        "artifact_count": len(artifacts),
        "cohort_counts": cohort_counts,
        "corpus_fingerprint": _corpus_fingerprint(artifacts),
        "rows": [rows_by_id[key] for key in sorted(rows_by_id)],
        "manifest": expected_by_id,
    }


def build_superboss_corpus(
    parsed_dir: Path = PARSED_SUPERBOSS_DIR,
    *,
    manifest_path: Path = MANIFEST_PATH,
    repository_root: Path = PROJECT_ROOT,
    clean: bool = False,
) -> dict[str, Any]:
    """Parse committed captures into deterministic schema-current artifacts."""
    captures = _capture_records(manifest_path, repository_root=repository_root)
    expected_filenames = {f"{record['canonical_id']}.json" for record, _, _ in captures}
    if clean:
        parsed_dir.mkdir(parents=True, exist_ok=True)
        for path in parsed_dir.glob("*.json"):
            if path.name not in expected_filenames:
                path.unlink()
    parsed_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for record, capture_path, capture_sha256 in captures:
        artifact = _payload(record, capture_path, capture_sha256)
        output_path = parsed_dir / f"{record['canonical_id']}.json"
        output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts.append(artifact)
    report = validate_parsed_superboss_corpus(
        parsed_dir,
        manifest_path=manifest_path,
        repository_root=repository_root,
    )
    return {key: value for key, value in report.items() if key != "rows" and key != "manifest"}


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="build schema-current parsed superboss artifacts")
    build_parser.add_argument("--parsed-dir", type=Path, default=PARSED_SUPERBOSS_DIR)
    build_parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    build_parser.add_argument("--repository-root", type=Path, default=PROJECT_ROOT)
    build_parser.add_argument("--clean", action="store_true", help="remove stale generated JSON artifacts")
    args = parser.parse_args()
    if args.command == "build":
        report = build_superboss_corpus(
            args.parsed_dir,
            manifest_path=args.manifest,
            repository_root=args.repository_root,
            clean=args.clean,
        )
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
