#!/usr/bin/env python3
"""Generate an offline Feature H2 Markdown review from an H1 report."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.workflow.h2_review import H2_DEFAULT_OUTPUT, generate_h2_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a bounded human-readable Feature H2 review without paid calls"
    )
    parser.add_argument("--h1-report", required=True, help="Path to an existing sanitized H1 JSON report")
    parser.add_argument(
        "--output",
        default=H2_DEFAULT_OUTPUT,
        help=f"Markdown output path (default: {H2_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--context",
        help="Optional sanitized JSON context with character, skill, boss, threat, and dependency evidence",
    )
    parser.add_argument(
        "--variant",
        choices=("baseline_a", "variant_b"),
        default="baseline_a",
        help="H1 arm to render as the primary recommendation (default: baseline_a)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    review = generate_h2_review(
        args.h1_report,
        args.output,
        context_path=args.context,
        variant_id=args.variant,
    )
    print(f"Generated {Path(args.output)}")
    print(f"Scenarios: {review['scenario_count']}")
    print("Paid provider calls: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
