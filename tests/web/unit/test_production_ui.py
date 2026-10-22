"""Browser-script contract checks using Node's built-in runner; no npm packages."""
from pathlib import Path
import subprocess


def test_production_and_exploratory_browser_script():
    repo = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        ["node", "tests/web/production_ui.test.cjs"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
