"""Offline real-browser check of roster selection, submission, SSE insertion and modes.

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

SAMPLE_ROSTER_NAMES = [
    "Aldo", "Feinne", "Cyrus", "Deirdre", "Azami", "Gariyu", "Cerrine", "Levia",
    "Shion", "Toova", "Suzette", "Anabel", "Radias", "Prai", "Aisha", "Rosetta",
    "Mariel", "Yuna", "Mana", "Dunarith",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--production-smoke", action="store_true")
    parser.add_argument(
        "--browser", default="/snap/chromium/current/usr/lib/chromium-browser/chrome"
    )
    parser.add_argument("--screenshot-dir", type=Path)
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
        "detailed_evidence": "What this result establishes" in rendered,
    }).replace("<", "\\u003c")
    page = templates.get_template("index.html").render()
    page = re.sub(r'<script\b[^>]*src="[^"]+"[^>]*></script>', "", page)
    page = re.sub(r'<link\b[^>]*>', "", page)
    # Pico gives form buttons width:100%; keep that cascade in this offline
    # check so the dedicated action row is tested with the same sizing interaction.
    page = page.replace(
        "</head>",
        "<style id=\"pico-button-width-regression\">button{width:100%}</style></head>",
    )
    screenshot_page = static_fixture_page(page, rendered)
    setup = """
const fixture = FIXTURE;
const sent = [];
const streamUrls = [];
const sampleRoster = ['Aldo','Feinne','Cyrus','Deirdre','Azami','Gariyu','Cerrine','Levia','Shion','Toova','Suzette','Anabel','Radias','Prai','Aisha','Rosetta','Mariel','Yuna','Mana','Dunarith'];
let postAttempt = 0;
let streamAttempt = 0;
localStorage.setItem('anothereden_roster', JSON.stringify(['Toova', 'Yuna', 'Unavailable Form']));
localStorage.setItem('anothereden_sidekicks', JSON.stringify(['Tetra']));
window.fetch = async (url, options) => {
  if (url === '/api/entities') return {ok:true,json: async () => ({characters:sampleRoster,sidekicks:['Tetra']})};
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
  const firstViewport = selector => {
    const element = document.querySelector(selector);
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.bottom <= window.innerHeight;
  };
  try {
    await tick();
    const form = document.getElementById('query-form');
    const boss = document.getElementById('boss-id');
    const mode = document.getElementById('workflow-mode');
    const query = document.getElementById('query-input');
    check(document.querySelectorAll('.char-checkbox:checked').length === 2, 'roster selection');
    check(document.getElementById('roster-summary').textContent.includes('2 character forms selected'), 'selected roster count');
    check(document.querySelector('label[for="character-search"]') && document.querySelector('label[for="sidekick-search"]'), 'search controls have labels');
    if (window.innerWidth === 1440 || window.innerWidth === 390) {
      check(firstViewport('#boss-id'), 'boss selector is visible in the initial viewport');
      check(firstViewport('#character-search'), 'roster search is visible in the initial viewport');
      check(firstViewport('#roster-count-badge'), 'selected roster count is visible in the initial viewport');
      check(firstViewport('.quick-start'), 'three-step quick start is visible in the initial viewport');
    }
    check(firstViewport('#query-submit'), 'primary action is reachable in the initial viewport');
    const dock = document.querySelector('.action-dock').getBoundingClientRect();
    const pageShell = document.querySelector('.page-shell').getBoundingClientRect();
    const action = document.getElementById('query-submit').getBoundingClientRect();
    const context = document.querySelector('.action-context').getBoundingClientRect();
    window.__initialLayoutMetrics = {
      viewport: window.innerWidth + 'x' + window.innerHeight,
      documentWidth: document.documentElement.scrollWidth,
      pageShellWidth: document.querySelector('.page-shell').getBoundingClientRect().width,
      pageShellScrollWidth: document.querySelector('.page-shell').scrollWidth,
      pageShellBottom: Math.round(pageShell.bottom),
      actionBarTop: Math.round(dock.top),
      actionBarBottom: Math.round(dock.bottom),
      bossBottom: Math.round(document.getElementById('boss-id').getBoundingClientRect().bottom),
      rosterSearchBottom: Math.round(document.getElementById('character-search').getBoundingClientRect().bottom),
      selectedCountBottom: Math.round(document.getElementById('roster-count-badge').getBoundingClientRect().bottom),
      primaryActionTop: Math.round(action.top),
    };
    check(dock.height < 160 && dock.top >= 0 && dock.bottom <= window.innerHeight, 'dedicated action bar stays compact and inside the viewport');
    check(pageShell.bottom <= dock.top + 1, 'action bar does not overlay the scrollable page content');
    check(context.width > 100, 'action guidance retains readable width next to the button');
    check(action.width < window.innerWidth * 0.6, 'full-width framework button defaults do not consume the action dock');
    check(document.querySelector('.instructions').open === false, 'instructions are collapsed by default');
    check(document.getElementById('mode-boss').getAttribute('aria-pressed') === 'true', 'recommendation mode state is exposed');
    check(document.documentElement.scrollWidth <= window.innerWidth, 'initial page fits the viewport without horizontal overflow');
    const staleRemoval = document.querySelector('.remove-stale-selection');
    check(staleRemoval && staleRemoval.tabIndex === 0, 'stale selection has a keyboard-reachable remove button');
    staleRemoval.focus();
    check(document.activeElement === staleRemoval, 'stale selection remove button receives keyboard focus');
    staleRemoval.click();
    check(!document.querySelector('.remove-stale-selection'), 'stale selection removed');
    check(document.querySelectorAll('.char-checkbox:checked').length === 2, 'valid saved roster preserved');
    document.getElementById('use-sample-roster').click();
    check(sent.length === 0, 'sample selection does not submit a request');
    check(document.querySelectorAll('.char-checkbox:checked').length === 20, 'sample selects the twenty normal forms');
    check(Array.from(document.querySelectorAll('.char-checkbox:checked'), input => input.value).join('|') === sampleRoster.join('|'), 'sample uses the supported canonical forms in order');
    check(document.querySelectorAll('.sidekick-checkbox:checked').length === 0, 'sample declares no owned sidekicks');
    check(JSON.parse(localStorage.getItem('anothereden_roster')).join('|') === sampleRoster.join('|'), 'sample selection is saved for reload');
    check(document.getElementById('selection-status').textContent.includes('No request was submitted'), 'sample selection explains that it did not submit');
    form.requestSubmit();
    await tick();
    check(sent.length === 0, 'missing boss must prevent submission');
    check(!document.getElementById('boss-validation').hidden, 'missing boss shows inline guidance instead of a browser popup');
    check(document.activeElement === boss && boss.getAttribute('aria-invalid') === 'true', 'missing boss guidance is tied to and focuses the field');
    boss.value = 'Celestial Mushroom';
    boss.dispatchEvent(new Event('change', {bubbles:true}));
    check(document.getElementById('boss-validation').hidden && !boss.hasAttribute('aria-invalid'), 'choosing a boss clears its validation message');
    form.requestSubmit();
    await tick();
    check(sent.length === 1 && sent[0].mode === 'production', 'production request');
    check(sent[0].boss_id === boss.value && sent[0].query === '', 'boss and optional preferences');
    check(sent[0].roster.join('|') === sampleRoster.join('|') && sent[0].owned_sidekicks.length === 0, 'sample ownership payload');
    check(document.getElementById('action-context-title').textContent === 'Your candidates are ready.', 'action guidance describes the completed result');
    check(document.getElementById('query-submit').textContent === 'Run another search', 'action offers a useful follow-up after results');
    check(dock.bottom <= window.innerHeight && document.querySelector('.page-shell').getBoundingClientRect().bottom <= dock.top + 1, 'action bar stays separate after candidate generation');
    check(document.querySelectorAll('#result-container .recommendation-card').length > 0, 'SSE result cards');
    check(document.querySelectorAll('.pipeline-step.done').length === 4, 'production progress completes');
    const firstCard = document.querySelector('#result-container .recommendation-card');
    check(firstCard.open, 'first candidate is open by default');
    check(firstCard.querySelectorAll('.formation-slots--frontline .formation-slot').length === 4, 'four distinct frontline positions render');
    check(firstCard.querySelectorAll('.formation-slots--reserve .formation-slot').length === 2, 'two distinct reserve positions render');
    check(firstCard.querySelectorAll('.member-grid--frontline .member-detail').length === 4, 'frontline member skills render');
    check(firstCard.querySelectorAll('.member-grid--reserve .member-detail').length === 2, 'reserve member skills render');
    check(Array.from(document.querySelectorAll('.technical-diagnostics')).every(details => !details.open), 'technical details start collapsed');
    const skillEvidenceDetails = firstCard.querySelector('.reviewed-source-details');
    if (skillEvidenceDetails) check(!skillEvidenceDetails.open, 'individual skill evidence starts collapsed');
    check(firstCard.querySelector('.recommendation-card__summary h3'), 'candidate summary has a heading');
    check(firstCard.querySelector('.recommendation-card__summary').tabIndex === 0, 'candidate disclosure is keyboard focusable');
    const cardMarkup = firstCard.innerHTML;
    check(cardMarkup.indexOf('formation-preview') < cardMarkup.indexOf('equipped-team'), 'formation is presented before equipped skills');
    check(cardMarkup.indexOf('equipped-team') < cardMarkup.indexOf('candidate-explanation'), 'equipped skills precede the explanation');
    check(cardMarkup.indexOf('candidate-explanation') < cardMarkup.indexOf('selected-skill-evidence'), 'candidate explanation precedes detailed skill evidence');
    const recommendationMarkup = document.querySelector('.recommendation-list').innerHTML;
    if (document.querySelector('.candidate-warning-band')) {
      check(recommendationMarkup.indexOf('candidate-warning-band') < recommendationMarkup.indexOf('team-assumptions'), 'contextual warnings precede equipment assumptions');
    }
    check(recommendationMarkup.indexOf('team-assumptions') < recommendationMarkup.indexOf('technical-diagnostics'), 'equipment assumptions precede technical diagnostics');
    check(document.activeElement.textContent.includes('Candidate recommendations'), 'success moves focus to the result heading');
    const resultText = document.getElementById('result-container').textContent;
    if (fixture.detailed_evidence) {
      check(resultText.includes('What this result establishes'), 'legal result boundary');
      check(resultText.includes('Celestial Mushroom'), 'selected production boss');
      check(resultText.includes('Evidence for selected skills'), 'final selected-skill evidence panel');
      check(resultText.includes('This does not cover every effect a skill may have'), 'review limitation');
      check(skillEvidenceDetails, 'reviewed source records have an expandable detail');
      check(document.querySelectorAll('#result-container a[href]').length > 0, 'source citations');
      check(resultText.includes('Reserve; requires switching'), 'reserve switch limitation');
      check(Array.from(document.querySelectorAll('.technical-diagnostics')).every(details => !details.open), 'scorer and technical diagnostics remain collapsed');
    }
    check(Array.from(document.querySelectorAll('.candidate-warning-band')).every(band => !band.closest('details')), 'candidate cautions remain visible outside collapsed disclosures');
    if (fixture.degraded) check(document.getElementById('result-container').textContent.includes('Deterministic-only result'), 'degraded banner preserves the no-AI-analysis claim');
    check(document.documentElement.scrollWidth <= window.innerWidth, 'result fits the viewport without horizontal page overflow');
    document.getElementById('mode-graph').click();
    check(document.getElementById('recommendation-panel').hidden && !document.getElementById('graph-panel').hidden, 'graph mode has its separate workspace');
    check(boss.disabled && query.disabled && document.getElementById('graph-query-input').required, 'graph mode question controls');
    check(document.getElementById('mode-graph').getAttribute('aria-pressed') === 'true', 'graph mode state is exposed');
    check(document.getElementById('query-submit').textContent.includes('Ask the graph'), 'graph mode has a distinct action');
    form.requestSubmit();
    check(sent.length === 1, 'exploratory requires question');
    document.getElementById('graph-query-input').value = 'What is Fire Zone?';
    form.requestSubmit();
    check(document.getElementById('mode-boss').disabled, 'mode controls are locked while a job is active');
    await tick();
    check(sent.length === 2 && sent[1].mode === 'exploratory' && sent[1].boss_id === null, 'exploratory request');
    check(sent[1].query === 'What is Fire Zone?', 'Graph Q&A uses its own question field');
    document.getElementById('mode-boss').click();
    check(!boss.disabled && !query.disabled && document.getElementById('graph-query-input').disabled, 'return to production');

    query.value = 'retain this preference';
    form.requestSubmit();
    await tick();
    const invalidAlert = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(sent.length === 3 && invalidAlert && invalidAlert.textContent.includes('saved characters are unavailable'), 'POST validation gets safe field guidance');
    check(invalidAlert.tabIndex === -1 && document.activeElement === invalidAlert, 'POST error guidance is announced and focusable');
    check(!document.getElementById('query-submit').disabled, 'invalid POST restores submit');
    check(sent[2].query === 'retain this preference' && sent[2].roster.join('|') === sampleRoster.join('|') && sent[2].owned_sidekicks.length === 0, 'POST error preserves current inputs');

    form.requestSubmit();
    await tick();
    check(sent.length === 4 && streamUrls.length === 3, 'explicit retry opens a new job after validation error');
    let terminal = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(terminal && terminal.textContent.includes('ended without returning a result'), 'done without result is explained');
    check(!document.getElementById('query-submit').disabled, 'no-result completion restores submit');

    form.requestSubmit();
    await tick();
    terminal = document.querySelector('#progress-slot .user-feedback[role="alert"]');
    check(sent.length === 5 && terminal && terminal.textContent.includes('job may be unavailable or expired'), 'reused or disconnected job gets recovery guidance');
    check(!document.getElementById('query-submit').disabled, 'disconnect restores submit');

    form.requestSubmit();
    await tick();
    check(sent.length === 6 && streamUrls.length === 5, 'explicit recovery retry starts one fresh stream');
    check(new Set(streamUrls).size === streamUrls.length, 'every explicit retry uses a fresh job URL');
    check(document.querySelectorAll('#result-container .recommendation-card').length > 0, 'explicit retry returns to successful result');
    check(!document.getElementById('query-submit').disabled, 'successful retry restores submit');
    check(document.documentElement.scrollWidth <= window.innerWidth, 'result fits the viewport without horizontal page overflow');
    status.textContent = 'PASS: first-viewport controls, no overflow, sample and saved roster, separate mode fields, candidate formation and skills, visible warnings, collapsed diagnostics, focused result and recovery lifecycle' + (fixture.degraded ? ', degraded banner' : '') + ' | layout=' + JSON.stringify(window.__initialLayoutMetrics);
  } catch (error) { status.textContent = 'FAIL: ' + error.message; }
});
"""
    app_js = (repo / "src/web/static/app.js").read_text()
    keyboard_page = keyboard_fixture_page(page, app_js, fixture)
    page = page.replace("</body>", f"<script>{setup}</script><script>{app_js}</script><script>{checks}</script></body>")
    with tempfile.TemporaryDirectory(prefix="anothereden-browser-") as folder:
        path = Path(folder)
        document = path / "check.html"
        document.write_text(page)
        if args.screenshot_dir:
            args.screenshot_dir.mkdir(parents=True, exist_ok=True)
        for view, width, height in [("desktop", 1440, 900), ("mobile", 390, 844), ("reported", 886, 918)]:
            completed = subprocess.run(
                [args.browser, "--headless", "--no-sandbox", "--disable-gpu",
                 "--disable-dev-shm-usage", "--no-first-run", "--disable-background-networking",
                 f"--window-size={width},{height}", f"--user-data-dir={path / ('profile-' + view)}",
                 "--virtual-time-budget=3000", "--dump-dom", document.as_uri()],
                capture_output=True, text=True, timeout=20,
            )
            match = re.search(r'<pre id="browser-check">([^<]*)</pre>', completed.stdout)
            if completed.returncode or not match or not match[1].startswith("PASS:"):
                raise SystemExit(
                    f"{view} {width}x{height}: " + (match[1] if match else "Browser check did not finish")
                    + "\nBROWSER STDOUT:\n" + completed.stdout[-4000:]
                    + "\nBROWSER STDERR:\n" + completed.stderr[-2000:]
                )
            print(f"PASS: {view} {width}x{height}: {match[1]}")
            if args.screenshot_dir and view != "reported":
                for state, html in (
                    ("start", screenshot_page[0]),
                    ("result", screenshot_page[1]),
                    ("cautions", screenshot_page[2]),
                ):
                    preview = path / f"preview-{view}-{state}.html"
                    preview.write_text(html)
                    screenshot_path = args.screenshot_dir / f"m7-3-{view}-{state}.png"
                    captured = subprocess.run(
                        [args.browser, "--headless", "--no-sandbox", "--disable-gpu",
                         "--disable-dev-shm-usage", "--no-first-run", "--disable-background-networking",
                         "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3000",
                         f"--window-size={width},{height}", f"--user-data-dir={path / ('screenshot-profile-' + view + '-' + state)}",
                         f"--screenshot={screenshot_path}", preview.as_uri()],
                        capture_output=True, text=True, timeout=20,
                    )
                    if captured.returncode or not screenshot_path.exists() or screenshot_path.stat().st_size < 10_000:
                        raise SystemExit(f"{view} {state} screenshot failed: {captured.stderr[-2000:]}")
                    print(f"SCREENSHOT: {screenshot_path}")
        keyboard_document = path / "keyboard-check.html"
        keyboard_document.write_text(keyboard_page)
        for viewport in ["1440x900", "390x844"]:
            keyboard = subprocess.run(
                ["node", str(repo / "tests/web/accessibility_check.cjs"),
                 "--browser", args.browser, "--html", str(keyboard_document),
                 "--viewport", viewport],
                cwd=repo, capture_output=True, text=True, timeout=60,
            )
            if keyboard.returncode:
                raise SystemExit(
                    f"Chromium keyboard/accessibility check failed at {viewport}:\n"
                    + keyboard.stdout + keyboard.stderr
                )
            print(keyboard.stdout.strip())


def static_fixture_page(page: str, result_html: str) -> tuple[str, str, str]:
    """Build styled static screenshots from the same template and rendered fixture result."""
    import html

    names = SAMPLE_ROSTER_NAMES
    character_cards = "".join(
        '<div class="roster-item" data-name="{name}"><label class="roster-choice is-selected">'
        '<input type="checkbox" class="char-checkbox" value="{name}" checked>'
        '<span class="roster-avatar" aria-hidden="true">{initial}</span>'
        '<span class="roster-choice-name">{name}</span></label></div>'.format(
            name=html.escape(name), initial=html.escape(name[:1].upper())
        )
        for name in names
    )
    sidekick_cards = (
        '<div class="roster-item" data-name="Tetra"><label class="roster-choice">'
        '<input type="checkbox" class="sidekick-checkbox" value="Tetra">'
        '<span class="roster-avatar" aria-hidden="true">T</span>'
        '<span class="roster-choice-name">Tetra</span></label></div>'
    )
    start = page.replace(
        '<p id="roster-summary" role="status" aria-live="polite">Loading saved selections.</p>',
        '<p id="roster-summary" role="status" aria-live="polite">20 character forms selected; fewer than six is okay.</p>',
    ).replace(
        '<span class="count-badge" id="roster-count-badge">0 selected</span>',
        '<span class="count-badge" id="roster-count-badge">20 selected</span>',
    ).replace(
        'id="use-sample-roster" aria-describedby="sample-roster-note" disabled',
        'id="use-sample-roster" aria-describedby="sample-roster-note"',
    )
    start = re.sub(
        r'(<div class="roster-list" id="character-list"[^>]*>).*?</div>',
        lambda match: match.group(1) + character_cards + "</div>", start, count=1, flags=re.S,
    )
    start = re.sub(
        r'(<div class="roster-list" id="sidekick-list"[^>]*>).*?</div>',
        lambda match: match.group(1) + sidekick_cards + "</div>", start, count=1, flags=re.S,
    )
    result = start.replace(
        '<div id="result-container" aria-live="off"></div>',
        '<div id="result-container" aria-live="off">' + result_html + "</div>",
    )
    result = result.replace(
        "</head>",
        '<style>.page-header,.mode-switcher,.quick-start,.instructions,.workspace-card{display:none!important}'
        '.results-stage{margin:0!important;padding:0!important}.results-stage>header{display:none!important}'
        '.result-collection{margin-top:0}</style></head>',
    )
    result = result.replace(
        '<h2 id="results-region-title">Your results will appear here</h2>',
        '<h2 id="results-region-title">Candidate results ready</h2>',
    )
    result = result.replace(
        '<strong id="action-context-title">Ready to find candidates?</strong>',
        '<strong id="action-context-title">Your candidates are ready.</strong>',
    ).replace(
        '<span id="action-context-note">Choose a boss and at least one available form.</span>',
        '<span id="action-context-note">Change your boss, roster or preferences to run another search.</span>',
    ).replace(
        '>Find recommendations</button>',
        '>Run another search</button>',
    )
    candidate = result
    cautions = result.replace(
        "</head>",
        '<style>.results-stage>header,.result-collection__header,.evidence-boundary,'
        '.recommendation-card,.recommendation-list>.technical-diagnostics{display:none!important}'
        '.recommendation-list{display:grid;gap:.8rem}.candidate-warning-band{margin:0}</style></head>',
    )
    return start, candidate, cautions


def keyboard_fixture_page(page: str, app_js: str, fixture_json: str) -> str:
    """Build a fully local page for true Chromium keyboard and AX-tree checks."""
    setup = r"""
window.__requests = [];
window.__fixtureReady = false;
window.__fixture = FIXTURE;
window.fetch = async (url, options = {}) => {
  if (url === "/api/entities") {
    setTimeout(() => { window.__fixtureReady = true; }, 0);
    return {ok:true, json:async () => ({characters:ROSTER, sidekicks:["Tetra"]})};
  }
  const request = JSON.parse(options.body);
  window.__requests.push(request);
  if (request.query === "preview-error") {
    return {ok:false, status:422, json:async () => ({detail:[{loc:["body","query"]}]})};
  }
  return {ok:true, text:async () => '<div sse-connect="/api/stream/keyboard-job"></div>'};
};
window.EventSource = class {
  constructor() { this.listeners = {}; this.closed = false; }
  addEventListener(name, handler) {
    this.listeners[name] = handler;
    if (name === "node_status") setTimeout(() => handler({data:JSON.stringify({node:"RETRIEVE"})}), 0);
    if (name === "result") setTimeout(() => handler({data:window.__fixture.html}), 20);
    if (name === "done") setTimeout(() => handler({data:"{}"}), 40);
  }
  close() { this.closed = true; }
};
""".replace("ROSTER", json.dumps(SAMPLE_ROSTER_NAMES)).replace("FIXTURE", fixture_json)
    cleaned = page.replace("</body>", f"<script>{setup}</script><script>{app_js}</script></body>")
    return cleaned


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
