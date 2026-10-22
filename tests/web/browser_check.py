"""Offline real-browser check of form validation, submission, SSE insertion and modes.

Run with .venv/bin/python -B tests/web/browser_check.py. No server, graph or
provider is contacted; external assets are removed from the temporary page.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader, select_autoescape


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument(
        "--browser", default="/snap/chromium/current/usr/lib/chromium-browser/chrome"
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo))
    if args.result_json:
        result = json.loads(args.result_json.read_text())
    else:
        from tests.web.unit.test_feature_e_result_ui import _recommendation
        result = {"recommendations": [_recommendation("burst")], "warnings": []}

    templates = Environment(
        loader=FileSystemLoader(repo / "src/web/templates"),
        autoescape=select_autoescape(["html"]),
    )
    rendered = templates.get_template("partials/result.html").render(result=result)
    fixture = json.dumps({"html": rendered, "degraded": result.get("degraded", False)}).replace("<", "\\u003c")
    page = templates.get_template("index.html").render()
    page = re.sub(r'<script\b[^>]*src="[^"]+"[^>]*></script>', "", page)
    page = re.sub(r'<link\b[^>]*>', "", page)
    setup = """
const fixture = FIXTURE;
const sent = [];
localStorage.setItem('anothereden_roster', JSON.stringify(['Toova', 'Yuna']));
localStorage.setItem('anothereden_sidekicks', '[]');
window.fetch = async (url, options) => {
  if (url === '/api/entities') return {json: async () => ({characters:['Toova','Yuna'],sidekicks:[]})};
  sent.push(JSON.parse(options.body));
  return {ok:true,text:async () => '<div sse-connect="/api/stream/local-job"></div>'};
};
window.EventSource = class {
  addEventListener(name, handler) {
    if (name === 'result') setTimeout(() => handler({data:fixture.html}), 0);
  }
  close() {}
};
""".replace("FIXTURE", fixture)
    checks = """
document.addEventListener('DOMContentLoaded', async () => {
  const status = document.createElement('pre');
  status.id = 'browser-check';
  document.body.append(status);
  const check = (value, message) => { if (!value) throw Error(message); };
  const tick = () => new Promise(resolve => setTimeout(resolve, 20));
  try {
    await tick();
    const form = document.getElementById('query-form');
    const boss = document.getElementById('boss-id');
    const mode = document.getElementById('workflow-mode');
    const query = document.getElementById('query-input');
    check(document.querySelectorAll('.char-checkbox:checked').length === 2, 'roster selection');
    form.requestSubmit();
    await tick();
    check(sent.length === 0, 'missing boss must prevent submission');
    boss.value = 'Celestial Mushroom';
    form.requestSubmit();
    await tick();
    check(sent.length === 1 && sent[0].mode === 'production', 'production request');
    check(sent[0].boss_id === boss.value && sent[0].query === '', 'boss and optional preferences');
    check(sent[0].roster.join(',') === 'Toova,Yuna', 'owned roster payload');
    check(document.querySelectorAll('#result-container .recommendation-card').length > 0, 'SSE result cards');
    if (fixture.degraded) check(document.getElementById('result-container').textContent.includes('Deterministic-only result'), 'degraded banner');
    mode.value = 'exploratory';
    mode.dispatchEvent(new Event('change'));
    check(boss.disabled && document.getElementById('boss-selection').hidden && query.required, 'exploratory controls');
    form.requestSubmit();
    await tick();
    check(sent.length === 1, 'exploratory requires question');
    query.value = 'What is Fire Zone?';
    form.requestSubmit();
    await tick();
    check(sent.length === 2 && sent[1].mode === 'exploratory' && sent[1].boss_id === null, 'exploratory request');
    mode.value = 'production';
    mode.dispatchEvent(new Event('change'));
    check(!boss.disabled && !query.required, 'return to production');
    status.textContent = 'PASS: roster, boss validation, production request, SSE rendering, exploratory switching' + (fixture.degraded ? ', degraded banner' : '');
  } catch (error) { status.textContent = 'FAIL: ' + error.message; }
});
"""
    app_js = (repo / "src/web/static/app.js").read_text()
    page = page.replace("</body>", f"<script>{setup}</script><script>{app_js}</script><script>{checks}</script></body>")
    with tempfile.TemporaryDirectory(prefix="anothereden-browser-") as folder:
        path = Path(folder)
        document = path / "check.html"
        document.write_text(page)
        completed = subprocess.run(
            [args.browser, "--headless", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", "--no-first-run", "--disable-background-networking",
             f"--user-data-dir={path / 'profile'}", "--virtual-time-budget=3000",
             "--dump-dom", document.as_uri()],
            capture_output=True, text=True, timeout=20,
        )
    match = re.search(r'<pre id="browser-check">([^<]*)</pre>', completed.stdout)
    if completed.returncode or not match or not match[1].startswith("PASS:"):
        raise SystemExit((match[1] if match else "Browser check did not finish") + "\n" + completed.stderr[-2000:])
    print(match[1])


if __name__ == "__main__":
    main()
