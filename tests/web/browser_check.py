"""Offline real-browser check of form validation, submission, SSE insertion and modes.

Run with .venv/bin/python -B tests/web/browser_check.py. No server, graph or
provider is contacted; external assets are removed from the temporary page.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

from jinja2 import Environment, FileSystemLoader, select_autoescape


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--production-smoke", action="store_true")
    parser.add_argument(
        "--browser", default="/snap/chromium/current/usr/lib/chromium-browser/chrome"
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo))
    if args.production_smoke:
        result = asyncio.run(production_result(repo))
    elif args.result_json:
        result = json.loads(args.result_json.read_text())
    else:
        from tests.web.unit.test_feature_e_result_ui import _recommendation
        result = {"recommendations": [_recommendation("burst")], "warnings": []}

    templates = Environment(
        loader=FileSystemLoader(repo / "src/web/templates"),
        autoescape=select_autoescape(["html"]),
    )
    rendered = templates.get_template("partials/result.html").render(result=result)
    fixture = json.dumps({
        "html": rendered,
        "degraded": result.get("degraded", False),
        "detailed_evidence": "Boss facts and search limits" in rendered,
    }).replace("<", "\\u003c")
    page = templates.get_template("index.html").render()
    page = re.sub(r'<script\b[^>]*src="[^"]+"[^>]*></script>', "", page)
    page = re.sub(r'<link\b[^>]*>', "", page)
    setup = """
const fixture = FIXTURE;
const sent = [];
const streamUrls = [];
let postAttempt = 0;
let streamAttempt = 0;
localStorage.setItem('anothereden_roster', JSON.stringify(['Toova', 'Yuna', 'Unavailable Form']));
localStorage.setItem('anothereden_sidekicks', '[]');
window.fetch = async (url, options) => {
  if (url === '/api/entities') return {ok:true,json: async () => ({characters:['Toova','Yuna'],sidekicks:[]})};
  sent.push(JSON.parse(options.body));
  postAttempt += 1;
  if (postAttempt === 3) return {ok:false,status:422,json:async () => ({detail:[{loc:['body','roster',0]}]})};
  return {ok:true,text:async () => `<div sse-connect="/api/stream/local-job-${postAttempt}"></div>`};
};
window.EventSource = class {
  constructor(url) { this.url = url; streamUrls.push(url); this.scenario = ['success','success','done','disconnect','success'][streamAttempt++]; }
  addEventListener(name, handler) {
    if (this.scenario === 'success' && name === 'node_status') {
      const nodes = document.getElementById('workflow-mode').value === 'production'
        ? ['RETRIEVE','CANDIDATES','ANALYZE','FORMAT']
        : ['PLAN','CYPHER','VALIDATE','CANDIDATES','ANALYZE','FORMAT'];
      setTimeout(() => nodes.forEach(node => handler({data:JSON.stringify({node,attempt:1,max:1})})), 0);
    }
    if (this.scenario === 'success' && name === 'result') setTimeout(() => handler({data:fixture.html}), 0);
    if (this.scenario === 'done' && name === 'done') setTimeout(() => handler({data:''}), 0);
  }
  close() { this.closed = true; }
  set onerror(handler) { this._onerror = handler; if (this.scenario === 'disconnect') setTimeout(() => handler(), 0); }
  get onerror() { return this._onerror; }
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
    const staleRemoval = document.querySelector('.remove-stale-selection');
    check(staleRemoval && staleRemoval.tabIndex === 0, 'stale selection has a keyboard-reachable remove button');
    staleRemoval.focus();
    check(document.activeElement === staleRemoval, 'stale selection remove button receives keyboard focus');
    staleRemoval.click();
    check(!document.querySelector('.remove-stale-selection'), 'stale selection removed');
    check(document.querySelectorAll('.char-checkbox:checked').length === 2, 'valid saved roster preserved');
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
    check(document.querySelectorAll('.pipeline-step.done').length === 4, 'production progress completes');
    const firstCard = document.querySelector('#result-container .recommendation-card');
    firstCard.open = true;
    const resultText = document.getElementById('result-container').textContent;
    if (fixture.detailed_evidence) {
      check(resultText.includes('Boss facts and search limits'), 'boss affinity evidence panel');
      check(resultText.includes('Celestial Mushroom'), 'selected production boss');
      check(resultText.includes('Selected skill evidence'), 'final selected-skill evidence panel');
      check(resultText.includes('Source-effect coverage is not established'), 'review limitation');
      check(resultText.includes('Modeled fit'), 'heuristic fit label scope');
      check(document.querySelectorAll('#result-container a[href]').length > 0, 'source citations');
      check(resultText.includes('Reserve skills require switching'), 'reserve switch limitation');
    }
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

    query.value = 'retain this preference';
    form.requestSubmit();
    await tick();
    const invalidAlert = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(sent.length === 3 && invalidAlert && invalidAlert.textContent.includes('saved characters are unavailable'), 'POST validation gets safe field guidance');
    check(invalidAlert.tabIndex === -1 && document.activeElement === invalidAlert, 'POST error guidance is announced and focusable');
    check(!document.querySelector('#query-form button[type=submit]').disabled, 'invalid POST restores submit');
    check(sent[2].query === 'retain this preference' && sent[2].roster.join(',') === 'Toova,Yuna', 'POST error preserves current inputs');

    form.requestSubmit();
    await tick();
    check(sent.length === 4 && streamUrls.length === 3, 'explicit retry opens a new job after validation error');
    let terminal = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(terminal && terminal.textContent.includes('ended without returning a result'), 'done without result is explained');
    check(!document.querySelector('#query-form button[type=submit]').disabled, 'no-result completion restores submit');

    form.requestSubmit();
    await tick();
    terminal = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(sent.length === 5 && terminal && terminal.textContent.includes('job may be unavailable or expired'), 'reused or disconnected job gets recovery guidance');
    check(!document.querySelector('#query-form button[type=submit]').disabled, 'disconnect restores submit');

    form.requestSubmit();
    await tick();
    check(sent.length === 6 && streamUrls.length === 5, 'explicit recovery retry starts one fresh stream');
    check(new Set(streamUrls).size === streamUrls.length, 'every explicit retry uses a fresh job URL');
    check(document.querySelectorAll('#result-container .recommendation-card').length > 0, 'explicit retry returns to successful result');
    check(!document.querySelector('#query-form button[type=submit]').disabled, 'successful retry restores submit');
    status.textContent = 'PASS: both mode success paths, stale roster keyboard recovery, invalid POST, no-result, disconnect, focused guidance and explicit fresh-job retry' + (fixture.degraded ? ', degraded banner' : '');
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
        raise SystemExit(
            (match[1] if match else "Browser check did not finish")
            + "\nBROWSER STDOUT:\n" + completed.stdout[-4000:]
            + "\nBROWSER STDERR:\n" + completed.stderr[-2000:]
        )
    print(match[1])


async def production_result(repo: Path) -> dict:
    """Render the real isolated HTTP/production smoke output in the DOM check."""
    import httpx
    with patch("dotenv.load_dotenv", return_value=False):
        from src.web.app import app
        from tests.web.production_fixture import PilotGraphRecords
        from tests.web.unit.test_production_integration import production_smoke

    with tempfile.TemporaryDirectory(prefix="anothereden-pilot-") as folder:
        records = PilotGraphRecords(Path(folder))
        capture = subprocess.run(
            ["node", "-e",
             "const {loadUI}=require('./tests/web/ui_harness.cjs');"
             "(async()=>{const ui=await loadUI({roster:JSON.parse(process.argv[1])});"
             "await ui.submit();process.stdout.write(JSON.stringify(ui.requests[0].payload));})()"
             ".catch(error=>{console.error(error);process.exitCode=1;});",
             json.dumps(records.roster)],
            cwd=repo, capture_output=True, text=True, timeout=15,
        )
        if capture.returncode:
            raise SystemExit(capture.stderr)
        app.state.jobs = {}
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                observed = await production_smoke(client, records, json.loads(capture.stdout))
        finally:
            app.dependency_overrides.clear()
            app.state.jobs = {}
    final = observed["final_output"]
    print(f"PASS: isolated real production smoke, {len(final['recommendations'])} degraded recommendations, final legality and SSE wire contract")
    return final


if __name__ == "__main__":
    main()
