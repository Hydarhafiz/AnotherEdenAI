"""Regression tests for the bounded, deterministic G1.1 superboss replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.etl.loader import load_superbosses, reconcile_superboss_corpus
from src.etl.models import SuperbossRow
from src.etl.pipeline import CrawlConfig, _build_manifest_superboss_targets
from src.etl.superboss_corpus import (
    build_superboss_corpus,
    validate_parsed_superboss_corpus,
)


ROOT = Path(__file__).parents[2]
MANIFEST_PATH = ROOT / "src" / "etl" / "superboss_manifest.json"


def _build(tmp_path: Path) -> Path:
    parsed_dir = tmp_path / "parsed" / "superbosses"
    report = build_superboss_corpus(
        parsed_dir,
        manifest_path=MANIFEST_PATH,
        repository_root=ROOT,
    )
    assert report["artifact_count"] == 30
    assert report["cohort_counts"] == {"weak": 10, "medium": 10, "strong": 10}
    return parsed_dir


def test_build_is_complete_and_byte_stable(tmp_path):
    parsed_dir = _build(tmp_path)
    first = {
        path.name: path.read_bytes()
        for path in sorted(parsed_dir.glob("*.json"))
    }
    first_report = validate_parsed_superboss_corpus(
        parsed_dir,
        manifest_path=MANIFEST_PATH,
        repository_root=ROOT,
    )
    second_report = build_superboss_corpus(
        parsed_dir,
        manifest_path=MANIFEST_PATH,
        repository_root=ROOT,
    )
    second = {
        path.name: path.read_bytes()
        for path in sorted(parsed_dir.glob("*.json"))
    }

    assert first == second
    assert first_report["corpus_fingerprint"] == second_report["corpus_fingerprint"]


def test_validator_rejects_missing_extra_and_stale_artifacts(tmp_path):
    parsed_dir = _build(tmp_path)
    missing_path = parsed_dir / "mimi.json"
    missing_path.unlink()
    with pytest.raises(RuntimeError, match="incomplete"):
        validate_parsed_superboss_corpus(
            parsed_dir,
            manifest_path=MANIFEST_PATH,
            repository_root=ROOT,
        )

    _build(tmp_path)
    extra_path = parsed_dir / "not-in-manifest.json"
    extra_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="incomplete"):
        validate_parsed_superboss_corpus(
            parsed_dir,
            manifest_path=MANIFEST_PATH,
            repository_root=ROOT,
        )

    extra_path.unlink()
    artifact_path = parsed_dir / "mimi.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["source_capture_sha256"] = "0" * 64
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match="fingerprint"):
        validate_parsed_superboss_corpus(
            parsed_dir,
            manifest_path=MANIFEST_PATH,
            repository_root=ROOT,
        )

    _build(tmp_path)
    artifact_path = parsed_dir / "mimi.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["rows"][0]["canonical_id"] = "zennon-ogres-shadow"
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Duplicate parsed superboss canonical_id"):
        validate_parsed_superboss_corpus(
            parsed_dir,
            manifest_path=MANIFEST_PATH,
            repository_root=ROOT,
        )

    _build(tmp_path)
    artifact_path = parsed_dir / "mimi.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["rows"][0]["mechanics_text"] = ""
    artifact["parsed_counts"]["mechanics_text_chars"] = 0
    artifact["rows"][0]["recommendation_ready"] = False
    artifact["parsed_counts"]["recommendation_ready"] = 0
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not recommendation-ready"):
        validate_parsed_superboss_corpus(
            parsed_dir,
            manifest_path=MANIFEST_PATH,
            repository_root=ROOT,
        )


def test_full_manifest_target_selection_is_canonical_and_bounded():
    targets = _build_manifest_superboss_targets(CrawlConfig(source_mode="parsed", crawl_scope="full"))

    assert len(targets) == 30
    assert {target["id"] for target in targets} == {
        f"superboss::{target['metadata']['superboss']['canonical_id']}" for target in targets
    }
    assert all(
        Path(target["parsed_path"]).name == f"{target['metadata']['superboss']['canonical_id']}.json"
        for target in targets
    )


class _ReplayDriver:
    def __init__(self, records):
        self.records = records
        self.calls = []

    async def execute_query(self, cypher, **params):
        self.calls.append((cypher, params))
        if "OPTIONAL MATCH (s)-[r]-()" in cypher:
            return [
                {"name": name, "relationship_count": 0}
                for name in params["names"]
            ], None, None
        if "DELETE s" in cypher:
            return [{"deleted_count": len(params["names"])}], None, None
        return self.records, None, None


class _WriteSession:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, cypher, **params):
        self.calls.append((cypher, params))


class _WriteDriver:
    def __init__(self):
        self.calls = []

    def session(self):
        return _WriteSession(self.calls)


def _boss(canonical_id: str, name: str) -> SuperbossRow:
    return SuperbossRow.model_validate({
        "canonical_id": canonical_id,
        "name": name,
        "source_url": f"https://example.test/{canonical_id}",
        "section_anchor": "Mechanics",
        "section_bounded": True,
        "mechanics_text": "Mechanics are documented.",
        "support_status": "recommendation_ready",
        "recommendation_ready": True,
    })


@pytest.mark.asyncio
async def test_full_replay_marks_owned_nodes_without_demoting_other_replays():
    driver = _WriteDriver()
    await load_superbosses(driver, [_boss("mimi", "Mimi")], managed_by="g1.1.0")
    cypher, params = driver.calls[0]
    assert "s.managed_by = row.managed_by" in cypher
    assert params["rows"][0]["managed_by"] == "g1.1.0"
    assert params["rows"][0]["corpus_version"] == "g1.1.0"

    driver = _WriteDriver()
    await load_superbosses(driver, [_boss("mimi", "Mimi")])
    cypher, params = driver.calls[0]
    assert "s.managed_by = row.managed_by" not in cypher
    assert "managed_by" not in params["rows"][0]


@pytest.mark.asyncio
async def test_reconciliation_reports_unmanaged_and_deletes_only_stale_owned_nodes():
    driver = _ReplayDriver([
        {"name": "Mimi", "canonical_id": "mimi", "recommendation_ready": True},
        {"name": "Retired Boss", "canonical_id": "retired-boss", "recommendation_ready": True},
        {"name": "Unmanaged Boss", "canonical_id": None, "recommendation_ready": None},
    ])

    with pytest.raises(RuntimeError, match="stale manifest-managed"):
        await reconcile_superboss_corpus(driver, [_boss("mimi", "Mimi")])
    assert not any("DELETE s" in cypher for cypher, _ in driver.calls)

    driver = _ReplayDriver([
        {"name": "Mimi", "canonical_id": "mimi", "recommendation_ready": True},
        {"name": "Retired Boss", "canonical_id": "retired-boss", "recommendation_ready": True},
        {"name": "Unmanaged Boss", "canonical_id": None, "recommendation_ready": None},
    ])
    report = await reconcile_superboss_corpus(
        driver,
        [_boss("mimi", "Mimi")],
        allow_stale_delete=True,
    )

    assert report["stale_names"] == ["Retired Boss"]
    assert report["deleted_count"] == 1
    assert report["unmanaged_count"] == 1
    assert report["ready"] is True
    assert any("DELETE s" in cypher for cypher, _ in driver.calls)


@pytest.mark.asyncio
async def test_reconciliation_never_deletes_connected_stale_nodes():
    class ConnectedDriver(_ReplayDriver):
        async def execute_query(self, cypher, **params):
            self.calls.append((cypher, params))
            if "OPTIONAL MATCH (s)-[r]-()" in cypher:
                return [{"name": "Retired Boss", "relationship_count": 1}], None, None
            return self.records, None, None

    driver = ConnectedDriver([
        {"name": "Retired Boss", "canonical_id": "retired-boss", "recommendation_ready": True},
    ])
    with pytest.raises(RuntimeError, match="with relationships"):
        await reconcile_superboss_corpus(
            driver,
            [_boss("mimi", "Mimi")],
            allow_stale_delete=True,
        )
    assert not any("DELETE s" in cypher for cypher, _ in driver.calls)
