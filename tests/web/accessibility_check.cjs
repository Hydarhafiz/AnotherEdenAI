#!/usr/bin/env node
"use strict";

// Dependency-free Chromium CDP check. Keyboard interaction is sent through
// Input.dispatchKeyEvent; page scripts are limited to fixture API/SSE mocks.
const assert = require("node:assert/strict");
const {spawn} = require("node:child_process");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const {pathToFileURL} = require("node:url");

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const browser = option("--browser", "/snap/chromium/current/usr/lib/chromium-browser/chrome");
const html = option("--html");
const viewport = option("--viewport", "1440x900").split("x").map(Number);
if (viewport.length !== 2 || viewport.some(value => !Number.isInteger(value) || value < 1)) {
  throw new Error("--viewport must be WIDTHxHEIGHT");
}
if (!html) throw new Error("--html is required");

class DevTools {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 0;
    this.pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (!message.id) return;
      const item = this.pending.get(message.id);
      if (!item) return;
      this.pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message));
      else item.resolve(message.result);
    });
  }

  send(method, params = {}) {
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.socket.send(JSON.stringify({id, method, params}));
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true,
    });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    }
    return result.result.value;
  }
}

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  const profile = await fs.mkdtemp(path.join(os.tmpdir(), "anothereden-cdp-"));
  let chrome;
  let devtools;
  try {
    chrome = spawn(browser, [
      "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
      "--no-first-run", "--disable-background-networking", "--remote-allow-origins=*",
      "--remote-debugging-port=0", `--user-data-dir=${profile}`,
      "--window-size=1440,900", "about:blank",
    ], {stdio: "ignore"});
    const activePort = path.join(profile, "DevToolsActivePort");
    let port;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        port = Number((await fs.readFile(activePort, "utf8")).split("\n")[0]);
        break;
      } catch {
        if (chrome.exitCode != null) throw new Error(`Chromium exited with ${chrome.exitCode}`);
        await delay(50);
      }
    }
    assert.ok(port, "Chromium remote debugging endpoint starts");

    const targetResponse = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(pathToFileURL(path.resolve(html)).href)}`, {method: "PUT"});
    assert.equal(targetResponse.status, 200, "Chromium opens the local fixture page");
    const target = await targetResponse.json();
    devtools = new DevTools(new WebSocket(target.webSocketDebuggerUrl));
    await new Promise((resolve, reject) => {
      devtools.socket.addEventListener("open", resolve, {once: true});
      devtools.socket.addEventListener("error", reject, {once: true});
    });
    await devtools.send("Page.enable");
    await devtools.send("Runtime.enable");
    await devtools.send("Accessibility.enable");
    await devtools.send("Emulation.setDeviceMetricsOverride", {
      width: viewport[0],
      height: viewport[1],
      deviceScaleFactor: 1,
      mobile: viewport[0] <= 560,
    });
    await devtools.send("Page.navigate", {url: target.url});

    await waitFor(async () => devtools.evaluate(
      "window.__fixtureReady && document.querySelectorAll('.char-checkbox').length === 20"
    ), "roster and app initialize");
    const layoutExpression = [
      "(() => {",
      "  const rect = selector => {",
      "    const bounds = document.querySelector(selector).getBoundingClientRect();",
      "    return {top: Math.round(bounds.top), bottom: Math.round(bounds.bottom), width: Math.round(bounds.width)};",
      "  };",
      "  const page = document.querySelector('.page-shell').getBoundingClientRect();",
      "  const dock = document.querySelector('.action-dock').getBoundingClientRect();",
      "  return {",
      "    viewport: window.innerWidth + 'x' + window.innerHeight,",
      "    documentWidth: document.documentElement.scrollWidth,",
      "    pageShellWidth: Math.round(page.width),",
      "    pageShellScrollWidth: document.querySelector('.page-shell').scrollWidth,",
      "    pageShellBottom: Math.round(page.bottom),",
      "    actionBarTop: Math.round(dock.top),",
      "    actionBarBottom: Math.round(dock.bottom),",
      "    boss: rect('#boss-id'),",
      "    quickStart: rect('.quick-start'),",
      "    rosterSearch: rect('#character-search'),",
      "    selectedCount: rect('#roster-count-badge'),",
      "    primaryAction: rect('#query-submit'),",
      "  };",
      "})()",
    ].join("\n");
    const initialLayout = await devtools.evaluate(layoutExpression);
    assert.equal(initialLayout.viewport, viewport[0] + "x" + viewport[1], "Chromium uses the exact requested CSS viewport");
    assert.ok(initialLayout.documentWidth <= viewport[0], "the document has no horizontal page overflow");
    assert.ok(initialLayout.pageShellBottom <= initialLayout.actionBarTop + 1, "the action bar has a separate row after page content");
    for (const name of ["boss", "quickStart", "rosterSearch", "selectedCount", "primaryAction"]) {
      assert.ok(initialLayout[name].width > 0, name + " is visible");
      assert.ok(initialLayout[name].top >= 0 && initialLayout[name].bottom <= viewport[1], name + " is visible in the initial viewport");
    }
    assert.equal(await devtools.evaluate("document.querySelector('.instructions').open"), false, "full instructions are collapsed by default");
    console.log("PASS: exact " + initialLayout.viewport + " CSS viewport; document width "
      + initialLayout.documentWidth + "/" + viewport[0] + ", page/action boundary "
      + initialLayout.pageShellBottom + "/" + initialLayout.actionBarTop + "px; initial controls "
      + "boss=" + initialLayout.boss.bottom + "px quick-start=" + initialLayout.quickStart.bottom
      + "px roster-search=" + initialLayout.rosterSearch.bottom
      + "px selected-count=" + initialLayout.selectedCount.bottom + "px action-top="
      + initialLayout.primaryAction.top + "px");

    const tree = await devtools.send("Accessibility.getFullAXTree");
    const namedRoles = tree.nodes.map(node => ({
      role: node.role?.value || "",
      name: node.name?.value || "",
    }));
    const has = (role, name) => namedRoles.some(item => item.role === role && item.name.includes(name));
    assert.ok(has("button", "Boss recommendations"), "accessibility tree names the recommendation mode");
    assert.ok(has("button", "Graph Q&A"), "accessibility tree names Graph Q&A mode");
    assert.ok(has("combobox", "Choose a supported boss"), "accessibility tree names the boss selector");
    assert.ok(has("searchbox", "Search character forms"), "accessibility tree names roster search");
    assert.ok(has("button", "Use sample roster"), "accessibility tree names the sample action");
    assert.ok(has("button", "Find recommendations"), "accessibility tree names the primary action");
    console.log("PASS: Chromium accessibility tree exposes named mode, boss, roster search, sample and submit controls");

    async function js(expression) { return devtools.evaluate(expression); }
    async function auditTextContrast() {
      return js(`(() => {
        function color(value) {
          const text = String(value).trim();
          const hex = text.match(/^#([0-9a-f]{3,8})$/i);
          if (hex) {
            let digits = hex[1];
            if (digits.length === 3 || digits.length === 4) digits = [...digits].map(part => part + part).join("");
            if (digits.length === 6 || digits.length === 8) {
              return [0, 2, 4].map(index => parseInt(digits.slice(index, index + 2), 16) / 255)
                .concat(digits.length === 8 ? parseInt(digits.slice(6, 8), 16) / 255 : 1);
            }
          }
          const match = text.match(/^rgba?\\(([^)]+)\\)$/i);
          if (!match) return null;
          const parts = match[1].split(/\\s*[,/]\\s*|\\s+/).filter(Boolean);
          const channel = part => part.endsWith("%") ? Number.parseFloat(part) / 100 : Number.parseFloat(part) / 255;
          return [channel(parts[0]), channel(parts[1]), channel(parts[2]), parts[3] == null ? 1 : (parts[3].endsWith("%") ? Number.parseFloat(parts[3]) / 100 : Number.parseFloat(parts[3]))];
        }
        function composite(foreground, background) {
          const alpha = foreground[3];
          return [0, 1, 2].map(index => foreground[index] * alpha + background[index] * (1 - alpha)).concat(1);
        }
        function luminance(value) {
          return value.slice(0, 3).map(channel => channel <= 0.04045
            ? channel / 12.92
            : ((channel + 0.055) / 1.055) ** 2.4
          ).reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
        }
        function ratio(left, right) {
          const a = luminance(left), b = luminance(right);
          return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        }
        const paper = color(getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()) || [1, 1, 1, 1];
        const cases = [
          ['Dark workflow label', '.mode-button[aria-pressed="false"] strong', '.mode-switcher'],
          ['Dark workflow hint', '.mode-button[aria-pressed="false"] small', '.mode-switcher'],
          ['Selected workflow label', '.mode-button[aria-pressed="true"] strong', '.mode-button[aria-pressed="true"]'],
          ['Quick start', '.quick-start li strong', '.quick-start li'],
          ['Header supporting text', '.page-header > div > p:not(.eyebrow)', 'body'],
          ['Boss name', '#boss-card-title', '.boss-card'],
          ['Boss placeholder', '.boss-placeholder', '.boss-placeholder'],
          ['Roster selected count', '#roster-count-badge', '#roster-count-badge'],
          ['Selected character name', '.roster-choice.is-selected .roster-choice-name', '.roster-choice.is-selected'],
          ['Roster avatar', '.roster-choice.is-selected .roster-avatar', '.roster-choice.is-selected .roster-avatar'],
          ['Sample roster action', '#use-sample-roster', '#use-sample-roster'],
          ['Sample roster helper', '#sample-roster-note', '.roster-card'],
          ['Action bar helper', '#action-context-note', '.action-dock'],
          ['Primary action', '#query-submit', '#query-submit'],
          ['Field validation notice', '#boss-validation', '#boss-validation'],
          ['Result status notice', '.result-status', '.result-status'],
          ['Evidence boundary', '.evidence-boundary p', '.evidence-boundary'],
          ['Evidence boundary heading', '.evidence-boundary strong', '.evidence-boundary'],
          ['Candidate heading', '.candidate-heading h3', '.recommendation-card'],
          ['Candidate eyebrow', '.candidate-heading .section-kicker', '.recommendation-card'],
          ['Candidate number', '.candidate-number', '.candidate-number'],
          ['Candidate status badge', '.candidate-badge', '.candidate-badge'],
          ['Warning count badge', '.warning-count', '.warning-count'],
          ['Frontline lane heading', '.formation-lane--frontline h4', '.formation-lane--frontline'],
          ['Reserve lane heading', '.formation-lane--reserve h4', '.formation-lane--reserve'],
          ['Formation name', '.formation-slot__copy strong', '.formation-slot'],
          ['Formation position', '.formation-slot__copy small', '.formation-slot'],
          ['Character name', '.member-detail__header h5', '.member-detail'],
          ['Character placement', '.member-detail__header p', '.member-detail'],
          ['Skill section label', '.equip-list h6', '.member-detail'],
          ['Equipped skill', '.equip-list li', '.member-detail'],
          ['Candidate explanation', '.candidate-explanation p', '.candidate-explanation'],
          ['Explanation limitation', '.candidate-explanation .boundary-inline', '.candidate-explanation'],
          ['Warning text', '.candidate-warning p', '.candidate-warning-band'],
          ['Warning heading', '.candidate-warning strong', '.candidate-warning-band'],
          ['Warning source link', '.candidate-warning a', '.candidate-warning-band'],
          ['Context disclosure', '.context-details > summary', '.context-details'],
          ['Source disclosure', '.reviewed-source-details > summary', '.selected-skill-evidence'],
          ['Source citation link', '.reviewed-skill-list a', '.reviewed-skill-list > li'],
          ['Equipment disclosure', '.team-assumptions > summary', '.team-assumptions'],
          ['Equipment assumption detail', '.team-assumptions__list li li', '.team-assumptions'],
          ['Technical disclosure', '.technical-diagnostics > summary', '.technical-diagnostics'],
          ['Technical detail text', '.technical-diagnostics li', '.technical-diagnostics'],
          ['Instructions disclosure', '.instructions > summary', '.instructions'],
          ['Request recovery notice', '.user-feedback p', '.user-feedback'],
        ];
        function samples(surface) {
          const style = getComputedStyle(surface);
          const baseColor = color(style.backgroundColor);
          let underlay = baseColor && baseColor[3] > 0 ? composite(baseColor, paper) : paper;
          const imageColors = [...style.backgroundImage.matchAll(/rgba?\\([^)]+\\)|#[0-9a-f]{3,8}/gi)]
            .map(match => color(match[0])).filter(Boolean);
          if (!imageColors.length) return [underlay];
          return imageColors.map(value => composite(value, underlay));
        }
        return cases.map(([label, textSelector, backgroundSelector]) => {
          const text = document.querySelector(textSelector);
          const surface = document.querySelector(backgroundSelector);
          if (!text || !surface) return {label, missing: true, textSelector, backgroundSelector};
          const textStyle = getComputedStyle(text);
          const foreground = color(textStyle.color);
          if (!foreground) return {label, missing: true, reason: "unparsed foreground " + textStyle.color};
          let opacity = 1;
          for (let element = text; element; element = element.parentElement) {
            opacity *= Number.parseFloat(getComputedStyle(element).opacity || '1');
            if (element === surface) break;
          }
          const effectiveForeground = foreground.map((value, index) => index === 3 ? value * opacity : value);
          const backgrounds = samples(surface);
          const measurements = backgrounds.map(background => ({
            ratio: ratio(composite(effectiveForeground, background), background),
            background: background.slice(0, 3).map(channel => Math.round(channel * 255)),
          }));
          const worst = measurements.reduce((left, right) => left.ratio < right.ratio ? left : right);
          return {label, ratio: Number(worst.ratio.toFixed(2)), foreground: textStyle.color, background: "rgb(" + worst.background.join(", ") + ")"};
        });
      })()`);
    }
    async function assertContrast(label, requiredLabels = null) {
      const readings = await auditTextContrast();
      const required = requiredLabels || new Set([
        'Dark workflow label', 'Dark workflow hint', 'Selected workflow label', 'Quick start',
        'Header supporting text', 'Boss name', 'Boss placeholder', 'Roster selected count',
        'Selected character name', 'Sample roster action', 'Sample roster helper',
        'Action bar helper', 'Primary action', 'Evidence boundary', 'Candidate heading',
        'Candidate number', 'Candidate status badge', 'Formation name', 'Formation position',
        'Character name', 'Character placement', 'Equipped skill', 'Candidate explanation',
        'Equipment disclosure', 'Technical disclosure',
      ]);
      const missingRequired = readings.filter(item => item.missing && required.has(item.label));
      assert.deepEqual(missingRequired, [], `${label}: required contrast samples are present; missing: ${JSON.stringify(missingRequired)}`);
      const measured = readings.filter(item => !item.missing);
      assert.ok(measured.length >= required.size, `${label}: measured ${measured.length} text pairs`);
      const failures = measured.filter(item => item.ratio < 4.5);
      assert.deepEqual(failures, [], `${label}: normal text meets WCAG 2.2 AA 4.5:1; failing: ${JSON.stringify(failures)}`);
      const submit = await js(`(() => {
        const button = document.getElementById('query-submit');
        const prior = button.disabled;
        button.disabled = true;
        const style = getComputedStyle(button);
        const color = value => {
          const parts = value.match(/[\\d.]+/g).map(Number);
          return parts.slice(0, 3).map(channel => channel / 255);
        };
        const luminance = rgb => rgb.map(channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
          .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
        const foreground = color(style.color), background = color(style.backgroundColor);
        const a = luminance(foreground), b = luminance(background);
        button.disabled = prior;
        return Number(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)).toFixed(2));
      })()`);
      assert.ok(submit >= 4.5, `${label}: disabled action contrast is ${submit}:1`);
      const lowest = [...measured].sort((left, right) => left.ratio - right.ratio).slice(0, 5);
      const omitted = readings.filter(item => item.missing).map(item => item.label);
      console.log(`PASS: ${label} text contrast >= 4.5:1 across ${measured.length} pairs; disabled action ${submit}:1; lowest: ${lowest.map(item => `${item.label} ${item.ratio}:1`).join(', ')}`);
      const spotlight = new Set([
        'Dark workflow label', 'Dark workflow hint', 'Selected workflow label',
        'Boss name', 'Roster selected count', 'Field validation notice',
        'Result status notice', 'Evidence boundary', 'Candidate heading',
        'Candidate number', 'Formation name', 'Formation position',
        'Character name', 'Character placement', 'Equipped skill',
        'Candidate explanation', 'Warning text', 'Warning heading',
        'Source disclosure', 'Equipment disclosure', 'Technical disclosure',
        'Request recovery notice',
      ]);
      const details = measured.filter(item => spotlight.has(item.label));
      console.log(`Contrast detail: ${details.map(item => `${item.label} ${item.ratio}:1`).join('; ')}`);
      if (omitted.length) console.log(`INFO: optional contrast states absent in this fixture: ${omitted.join(', ')}`);
      return measured;
    }

    async function assertDockDoesNotCoverFocus(label) {
      const covered = await js(`(() => {
        const focus = document.activeElement;
        const dockElement = document.querySelector('.action-dock');
        const dock = dockElement.getBoundingClientRect();
        const rect = focus.getBoundingClientRect();
        return !dockElement.contains(focus) && rect.width > 0 && rect.height > 0 && rect.bottom > dock.top && rect.top < dock.bottom;
      })()`);
      assert.equal(covered, false, `${label}: bottom action bar does not cover keyboard focus`);
    }
    async function key(key, code, virtualKeyCode, modifiers = 0, text = "") {
      await devtools.send("Input.dispatchKeyEvent", {type: "keyDown", key, code, windowsVirtualKeyCode: virtualKeyCode, nativeVirtualKeyCode: virtualKeyCode, modifiers, text});
      await devtools.send("Input.dispatchKeyEvent", {type: "keyUp", key, code, windowsVirtualKeyCode: virtualKeyCode, nativeVirtualKeyCode: virtualKeyCode, modifiers});
    }
    async function tab(shift = false) { await key("Tab", "Tab", 9, shift ? 8 : 0); }
    async function space() { await key(" ", "Space", 32, 0, " "); }
    async function enter() { await key("Enter", "Enter", 13, 0, "\r"); }
    async function tabTo(selector, description = selector) {
      for (let i = 0; i < 250; i += 1) {
        if (await js(`Boolean(document.activeElement && document.activeElement.matches(${JSON.stringify(selector)}))`)) return;
        await tab();
      }
      const diagnostic = await js(`({matches:document.querySelectorAll(${JSON.stringify(selector)}).length,active:document.activeElement?.outerHTML?.slice(0,180),targets:Array.from(document.querySelectorAll(${JSON.stringify(selector)}),el=>({tabIndex:el.tabIndex,visible:el.getClientRects().length>0,disabled:el.disabled,outer:el.outerHTML.slice(0,180)}))})`);
      throw new Error(`Tab sequence could not reach ${description}: ${JSON.stringify(diagnostic)}`);
    }
    async function waitFor(predicate, description) {
      for (let i = 0; i < 150; i += 1) {
        if (await predicate()) return;
        await delay(40);
      }
      throw new Error(`Timed out waiting for ${description}`);
    }
    async function type(value) { await devtools.send("Input.insertText", {text: value}); }

    await tabTo("#mode-graph", "Graph Q&A mode");
    await space();
    assert.equal(await js("document.getElementById('graph-panel').hidden"), false, "Space opens the separate Graph Q&A workspace");
    assert.equal(await js("document.getElementById('mode-graph').getAttribute('aria-pressed')"), "true", "Graph Q&A pressed state updates");
    await tabTo("#mode-boss", "boss recommendation mode");
    await space();
    assert.equal(await js("document.getElementById('recommendation-panel').hidden"), false, "Space returns to boss recommendations");

    await tabTo(".instructions > summary", "demo instructions disclosure");
    await space();
    assert.equal(await js("document.querySelector('.instructions').open"), true, "Space expands instructions");
    await space();
    assert.equal(await js("document.querySelector('.instructions').open"), false, "Space collapses instructions");

    await tabTo("#boss-id", "supported boss selector");
    await key("ArrowDown", "ArrowDown", 40);
    await enter();
    assert.equal(await js("document.getElementById('boss-id').value"), "Celestial Mushroom", "keyboard chooses the supported boss");
    await tabTo("#character-search", "character form search");
    await type("Toova");
    await waitFor(() => js("document.querySelector('#character-list .roster-item[data-name=\"Toova\"]')?.style.display === ''"), "search filters the roster");
    await tabTo("#use-sample-roster", "sample roster button");
    await space();
    assert.equal(await js("document.querySelectorAll('.char-checkbox:checked').length"), 20, "Space applies the sample roster");
    assert.equal(await js("document.getElementById('selection-status').textContent.includes('No request was submitted')"), true, "sample selection does not submit");

    await tab(true);
    assert.equal(await js("document.activeElement.id"), "character-search", "Shift+Tab returns to roster search");
    await key("a", "KeyA", 65, 2);
    await key("Backspace", "Backspace", 8);
    await type("Toova");
    await tabTo("#character-list .char-checkbox", "filtered character checkbox");
    assert.equal(await js("document.activeElement.value"), "Toova", "keyboard reaches the filtered form");
    await assertDockDoesNotCoverFocus("focused roster checkbox");
    await space();
    assert.equal(await js("document.activeElement.checked"), false, "Space changes roster ownership");
    await space();
    assert.equal(await js("document.activeElement.checked"), true, "Space restores roster ownership");
    assert.ok(await js("getComputedStyle(document.activeElement).outlineStyle !== 'none'"), "keyboard focus has a visible outline");

    await tabTo("#query-submit", "recommendation action");
    await enter();
    await waitFor(() => js("document.getElementById('results-region-title').textContent === 'Candidate results ready' && document.querySelector('#result-container .recommendation-card')"), "candidate result arrives");
    assert.equal(await js("document.activeElement.matches('#result-container h2, #result-container h3')"), true, "result completion moves focus into the result");
    assert.equal(await js("document.activeElement.textContent.trim()"), "Candidate recommendations", "result focus lands on its heading");
    await assertDockDoesNotCoverFocus("candidate result heading");
    assert.equal(await js("window.__requests.length"), 1, "keyboard submits once");
    assert.equal(await js("window.__requests[0].mode"), "production", "submission preserves recommendation mode");
    assert.equal(await js("window.__requests[0].boss_id"), "Celestial Mushroom", "submission preserves boss selection");
    assert.equal(await js("window.__requests[0].roster.includes('Toova')"), true, "submission preserves selected form identity");
    assert.ok(await js("document.documentElement.scrollWidth <= window.innerWidth"), "candidate results do not introduce horizontal page overflow");
    assert.equal(await js("document.querySelector('.recommendation-card .formation-slots--frontline').querySelectorAll('.formation-slot').length"), 4, "result shows four frontline positions");
    assert.equal(await js("document.querySelector('.recommendation-card .formation-slots--reserve').querySelectorAll('.formation-slot').length"), 2, "result shows two reserve positions");
    assert.ok(await js("document.querySelector('.recommendation-card .member-grid--frontline .member-detail')"), "result includes equipped skill details");
    assert.ok(await js("document.querySelector('.recommendation-card .reviewed-source-details > summary')"), "result includes source-backed evidence details");
    await assertContrast("candidate result");
    assert.equal(await js("document.getElementById('action-context-title').textContent"), "Your candidates are ready.", "action context reflects the completed recommendation");
    assert.equal(await js("document.getElementById('query-submit').textContent"), "Run another search", "action button offers a meaningful follow-up");
    const warningCount = await js("document.querySelectorAll('.candidate-warning-band').length");
    assert.equal(await js("Array.from(document.querySelectorAll('.candidate-warning-band')).every(band => !band.closest('details'))"), true, "any candidate cautions remain visible outside technical details");
    if (warningCount) console.log(`PASS: ${warningCount} candidate caution groups remain visible outside technical details`);
    else console.log("INFO: production smoke result contains no candidate-scoped warning records to display");

    await tabTo(".recommendation-card__summary", "candidate disclosure");
    await space();
    assert.equal(await js("document.querySelector('.recommendation-card').open"), false, "Space collapses candidate details");
    await space();
    assert.equal(await js("document.querySelector('.recommendation-card').open"), true, "Space opens candidate details");
    const hasEvidence = await js("Boolean(document.querySelector('.reviewed-source-details > summary'))");
    if (hasEvidence) {
      await tabTo(".reviewed-source-details > summary", "reviewed evidence detail");
      await space();
      assert.equal(await js("document.querySelector('.reviewed-source-details').open"), true, "Space opens source-backed evidence detail");
      await space();
      assert.equal(await js("document.querySelector('.reviewed-source-details').open"), false, "Space returns source-backed evidence to its collapsed summary");
    }
    await tabTo(".recommendation-list > details.technical-diagnostics > summary", "candidate technical diagnostics disclosure");
    await space();
    assert.equal(await js("document.querySelector('.recommendation-list > details.technical-diagnostics').open"), true, "Space opens technical diagnostics");
    await space();
    assert.equal(await js("document.querySelector('.recommendation-list > details.technical-diagnostics').open"), false, "Space collapses technical diagnostics");

    await tabTo(".preferences > summary", "optional preferences disclosure");
    await space();
    await tabTo("#query-input", "optional preferences field");
    await type("preview-error");
    await enter();
    await waitFor(() => js("document.activeElement.matches('.user-feedback[role=\"alert\"]')"), "validation error receives focus");
    assert.ok(await js("document.activeElement.textContent.includes('Review the question or preferences')"), "validation error gives field-specific guidance");
    await assertDockDoesNotCoverFocus("request recovery notice");
    await assertContrast("request recovery", new Set(["Request recovery notice", "Action bar helper", "Primary action"]));
    await tabTo("#query-input", "optional preferences field for retry");
    await key("a", "KeyA", 65, 2);
    await key("Backspace", "Backspace", 8);
    await enter();
    await waitFor(() => js("document.getElementById('results-region-title').textContent === 'Candidate results ready' && document.querySelector('#result-container .recommendation-card')"), "keyboard retry succeeds");
    assert.equal(await js("window.__requests.length"), 3, "keyboard recovery starts one successful retry");
    assert.equal(await js("window.__requests[1].query"), "preview-error", "invalid preference reaches validation feedback");
    assert.equal(await js("window.__requests[2].query"), "", "keyboard retry clears the invalid preference");
    assert.equal(await js("document.activeElement.matches('#result-container h2, #result-container h3')"), true, "successful recovery returns focus to the result");
    assert.ok(await js("document.documentElement.scrollWidth <= window.innerWidth"), "recovered candidate results do not introduce horizontal page overflow");

    const finalTree = await devtools.send("Accessibility.getFullAXTree");
    assert.ok(finalTree.nodes.some(node => node.name?.value?.includes("Candidate results ready")), "final accessibility tree exposes the result heading");
    console.log("PASS: real Chromium keyboard journey covers mode, disclosures, boss, search, sample, roster, submit, result details and error recovery");
  } finally {
    if (devtools?.socket.readyState === WebSocket.OPEN) devtools.socket.close();
    if (chrome && chrome.exitCode == null) {
      await new Promise(resolve => {
        const timeout = setTimeout(() => {
          chrome.kill("SIGKILL");
          resolve();
        }, 2500);
        chrome.once("close", () => {
          clearTimeout(timeout);
          resolve();
        });
        chrome.kill("SIGTERM");
      });
    }
    for (let attempt = 0; attempt < 10; attempt += 1) {
      try {
        await fs.rm(profile, {recursive: true, force: true});
        break;
      } catch (error) {
        if (attempt === 9) throw error;
        await delay(100);
      }
    }
  }
}

main().catch(error => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
