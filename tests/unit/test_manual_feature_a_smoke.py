import json


def test_live_smoke_cleanup_removes_stale_sidekick_detail_manifest_entries(tmp_path):
    from tools.manual_feature_a_smoke import configure_environment

    run_root = tmp_path / "smoke"
    manifest_path = run_root / "etl" / "crawl_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "targets": {
                    "sidekick": {"kind": "sidekick_index", "state": "parsed"},
                    "sidekick::ashtear": {"kind": "sidekick_detail", "state": "inactive"},
                    "characters": {"kind": "characters_index", "state": "parsed"},
                }
            }
        ),
        encoding="utf-8",
    )
    (run_root / "raw" / "sidekicks").mkdir(parents=True)
    (run_root / "raw" / "sidekicks" / "ashtear.html").write_text("stale", encoding="utf-8")
    (run_root / "parsed" / "sidekicks").mkdir(parents=True)
    (run_root / "parsed" / "sidekicks" / "ashtear.json").write_text("{}", encoding="utf-8")

    class Args:
        source_mode = "live"
        scope = "small"
        include_character_pages = True
        include_sidekick_pages = True

    args = Args()
    args.run_root = str(run_root)

    configure_environment(args)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert sorted(manifest["targets"]) == ["characters", "sidekick"]
    assert not (run_root / "raw" / "sidekicks").exists()
    assert not (run_root / "parsed" / "sidekicks").exists()
