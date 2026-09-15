#!/usr/bin/env python3
"""Generate the ignored full-catalog Feature C1 structural sidecar."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.etl.structural_evidence import write_generated_sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/generated/feature_c1_structural_sidecar.json"),
    )
    args = parser.parse_args()
    payload = write_generated_sidecar(args.output)
    coverage = payload["coverage"]
    summary = {
        "artifact_version": payload["artifact_version"],
        "coverage": {
            key: value
            for key, value in coverage.items()
            if key not in {"unresolved_mappings", "parser_diagnostics"}
        },
        "topology_audit": payload["topology_audit"],
        "traversal_limits": payload["traversal_limits"],
        "reference_status_distribution": payload["reference_resolution"]["status_distribution"],
        "sidecar_digest": payload["sidecar_digest"],
        "output": args.output.as_posix(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
