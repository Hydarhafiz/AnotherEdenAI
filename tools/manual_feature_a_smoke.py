"""Manual smoke runner for Feature A ETL verification."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default="data/manual_feature_a/smoke1")
    parser.add_argument("--source-mode", choices=["live", "parsed"], default="live")
    parser.add_argument("--scope", choices=["small", "fallback", "full"], default="small")
    parser.add_argument("--include-character-pages", action="store_true", default=True)
    parser.add_argument("--no-character-pages", dest="include_character_pages", action="store_false")
    parser.add_argument("--include-sidekick-pages", action="store_true", default=True)
    parser.add_argument("--no-sidekick-pages", dest="include_sidekick_pages", action="store_false")
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> Path:
    run_root = Path(args.run_root)
    if args.source_mode == "live":
        for path in [run_root / "raw" / "sidekicks", run_root / "parsed" / "sidekicks"]:
            if path.exists():
                shutil.rmtree(path)
        manifest_path = run_root / "etl" / "crawl_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            targets = manifest.get("targets", {})
            manifest["targets"] = {
                target_id: entry
                for target_id, entry in targets.items()
                if not (target_id.startswith("sidekick::") or entry.get("kind") == "sidekick_detail")
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    os.environ["RAW_DATA_DIR"] = str(run_root / "raw")
    os.environ["PARSED_DATA_DIR"] = str(run_root / "parsed")
    os.environ["ETL_STATE_DIR"] = str(run_root / "etl")
    os.environ["ETL_SOURCE_MODE"] = args.source_mode
    os.environ["ETL_CRAWL_SCOPE"] = args.scope
    os.environ["ETL_INCLUDE_CHARACTER_PAGES"] = "true" if args.include_character_pages else "false"
    os.environ["ETL_INCLUDE_SIDEKICK_PAGES"] = "true" if args.include_sidekick_pages else "false"
    return run_root


def configure_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


async def main() -> None:
    args = parse_args()
    run_root = configure_environment(args)
    configure_import_path()

    from src.etl.pipeline import CrawlConfig, prepare_parsed_data

    data, manifest = await prepare_parsed_data(CrawlConfig())

    print(f"Run root: {run_root}")
    print(f"Source mode: {args.source_mode}")
    print(f"Crawl scope: {args.scope}")
    print(
        "Prepared counts: "
        f"{len(data['characters'])} characters, "
        f"{len(data['sidekicks'])} sidekicks, "
        f"{len(data['grastas'])} grastas, "
        f"{len(data['ores'])} ores"
    )

    manifest_path = run_root / "etl" / "crawl_manifest.json"
    print(f"Manifest: {manifest_path}")

    states = {}
    for entry in manifest["targets"].values():
        states[entry["state"]] = states.get(entry["state"], 0) + 1
    print(f"State summary: {json.dumps(states, sort_keys=True)}")

    active_sidekick_details = [
        entry
        for entry in manifest["targets"].values()
        if entry["kind"] == "sidekick_detail" and entry["state"] in {"parsed", "loaded"}
    ]
    print("Active sidekick detail targets:")
    for entry in sorted(active_sidekick_details, key=lambda item: item["id"]):
        sidekick = entry["metadata"]["sidekick"]["name"]
        print(
            f"- {sidekick}: state={entry['state']} "
            f"quality={entry['quality_status']} "
            f"parsed={entry['parsed_counts']}"
        )

    sample_targets = sorted(manifest["targets"].values(), key=lambda item: item["id"])[:5]
    print("Sample targets:")
    for entry in sample_targets:
        print(
            f"- {entry['id']}: state={entry['state']} "
            f"attempts={entry['attempt_count']} "
            f"bytes={entry['html_byte_size']} "
            f"quality={entry['quality_status']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
