#!/usr/bin/env python3
"""Replay checksum-pinned source witnesses and the complete C1.1 catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.etl.source_fidelity import build_source_fidelity_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_source_fidelity_report()
    replay = build_source_fidelity_report()
    report["deterministic_replay"]["repeat_replay_digest"] = replay["deterministic_replay"]["replay_digest"]
    report["deterministic_replay"]["same_input_same_digest"] = (
        report["deterministic_replay"]["replay_digest"]
        == report["deterministic_replay"]["repeat_replay_digest"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact_version": report["artifact_version"],
                "legal_kit": report["legal_kit"],
                "development_witness_count": report["manifest"]["development_witness_count"],
                "held_out_witness_count": report["manifest"]["held_out_witness_count"],
                "character_identity_denominator": report["full_catalog_replay"]["character_identity_denominator"],
                "sidekick_identity_denominator": report["sidekick_replay"]["sidekick_identity_denominator"],
                "sidekick_record_kind_coverage": report["sidekick_replay"]["record_kind_coverage"],
                "replay_digest": report["deterministic_replay"]["replay_digest"],
                "oracle_evaluated": "oracle_evaluation" in report,
                "output": args.output.as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
