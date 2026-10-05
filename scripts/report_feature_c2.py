"""Generate deterministic Milestone 6 Feature C2 comparison evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.etl.c2_scoped_classification import build_c2_report

DEVELOPMENT_FIDELITY_ORACLE = Path("tests/fixtures/source_fidelity/c2_development_oracle.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Report C2 scoped classification and review-reduction evidence")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fidelity_oracle = json.loads(DEVELOPMENT_FIDELITY_ORACLE.read_text(encoding="utf-8"))
    report = build_c2_report(fidelity_oracle=fidelity_oracle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"C2 artifact: {report['artifact_version']}")
    for cohort, comparison in report["comparisons"].items():
        arm = comparison["arms"]["fidelity_checked"]
        print(
            f"{cohort}: witnesses={comparison['witness_count']} "
            f"effects={arm['effect_occurrence_count']} "
            f"dependencies={arm['dependency_occurrence_count']}"
        )
    print(f"comparison digest: {report['deterministic_replay']['comparison_digest']}")


if __name__ == "__main__":
    main()
