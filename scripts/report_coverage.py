#!/usr/bin/env python3
"""Generate Feature A coverage reports from committed, offline artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.etl.coverage_baseline import (
    build_accepted_baseline,
    load_catalog_report,
    summarize_historical_diversity,
)


DEFAULT_OUTPUT = Path("artifacts/generated/coverage/feature_a_report.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the deterministic Feature A offline coverage report")
    parser.add_argument("--catalog", type=Path, default=Path("src/etl/kit_catalog.json"))
    parser.add_argument("--h1-report", type=Path, help="Optional sanitized historical H1 report for diversity distributions")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--accepted-baseline", type=Path, help="Optional concise durable baseline output")
    args = parser.parse_args()

    report = load_catalog_report(args.catalog)
    historical = None
    if args.h1_report:
        payload = json.loads(args.h1_report.read_text(encoding="utf-8"))
        scenarios = payload.get("scenarios") if isinstance(payload, dict) else None
        if not isinstance(scenarios, list):
            raise SystemExit("--h1-report must contain a scenarios list")
        historical = summarize_historical_diversity(scenarios)
        report["historical_request_diversity"] = historical

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.accepted_baseline:
        args.accepted_baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline = build_accepted_baseline(report, historical_diversity=historical)
        args.accepted_baseline.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {args.output}")
    print(f"Catalog identities: {report['catalog_characters']}")
    print(f"Complete legal-kit receipts: {report['legal_kit_complete']}")
    print(f"High-value extraction attempted: {report['high_value_capability_attempted']}")
    print("Thresholds: not set (planned human checkpoint)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
