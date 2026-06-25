"""Report or remove Sidekick nodes that were incorrectly loaded as Character nodes."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from neo4j import AsyncGraphDatabase


def configure_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="delete confirmed duplicate Character nodes; omit for dry-run reporting",
    )
    return parser.parse_args()


def print_report(rows: list[dict], *, applied: bool) -> None:
    mode = "cleanup" if applied else "dry run"
    print(f"Sidekick/Character overlap {mode}: {len(rows)} matched name(s)")
    if not rows:
        return

    for row in rows:
        decision = "cleanup-candidate" if row["cleanup_candidate"] else "kept"
        print(
            f"- {row['name']}: {decision}; "
            f"skills={row['skill_count']} "
            f"passives={row['passive_skill_count']} "
            f"unlocks={row['unlock_relationship_count']} "
            f"lacks_character_detail={row['lacks_character_detail']} "
            f"sidekick_like_origin={row['sidekick_like_origin']} "
            f"character_detail_url={row['character_detail_url'] or '-'} "
            f"sidekick_source_url={row['sidekick_source_url'] or '-'}"
        )


async def main() -> None:
    args = parse_args()
    configure_import_path()

    from src.etl.constants import NEO4J_AUTH, NEO4J_URI
    from src.etl.loader import (
        cleanup_duplicate_sidekick_characters,
        find_sidekick_character_overlaps,
    )

    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        await driver.verify_connectivity()
        if args.apply:
            rows = await cleanup_duplicate_sidekick_characters(driver)
        else:
            rows = await find_sidekick_character_overlaps(driver)
        print_report(rows, applied=args.apply)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
