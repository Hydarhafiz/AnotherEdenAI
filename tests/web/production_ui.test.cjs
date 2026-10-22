const assert = require("node:assert/strict");
const test = require("node:test");
const { loadUI } = require("./ui_harness.cjs");

test("production sends selected boss and ownership without requiring preferences", async () => {
  const ui = await loadUI({ roster: ["Toova", "Yuna"], sidekicks: ["Tetra"] });
  assert.equal(ui.element("query-input").required, false);
  assert.equal(ui.element("boss-id").required, true);
  await ui.submit();
  assert.deepEqual(ui.requests[0].payload, {
    query: "", mode: "production", boss_id: "Celestial Mushroom",
    roster: ["Toova", "Yuna"], owned_sidekicks: ["Tetra"],
  });
  assert.equal(ui.streams[0].url, "/api/stream/test-job-1");
  assert.match(ui.element("progress-slot").innerHTML, /data-node="RETRIEVE"/);
  assert.doesNotMatch(ui.element("progress-slot").innerHTML, /data-node="PLAN"/);
});

test("production cannot submit without a selected boss", async () => {
  const ui = await loadUI({ boss: "" });
  await ui.submit();
  assert.equal(ui.requests.length, 0);
});

test("exploratory mode ignores production boss and requires its question", async () => {
  const ui = await loadUI();
  ui.switchMode("exploratory");
  assert.equal(ui.element("boss-selection").hidden, true);
  assert.equal(ui.element("boss-id").disabled, true);
  assert.equal(ui.element("query-input").required, true);
  await ui.submit();
  assert.equal(ui.requests.length, 0);
  ui.element("query-input").value = "  What is Fire Zone?  ";
  await ui.submit();
  assert.equal(ui.requests[0].payload.mode, "exploratory");
  assert.equal(ui.requests[0].payload.boss_id, null);
  assert.equal(ui.requests[0].payload.query, "What is Fire Zone?");
  assert.match(ui.element("progress-slot").innerHTML, /data-node="PLAN"/);
  assert.doesNotMatch(ui.element("progress-slot").innerHTML, /data-node="RETRIEVE"/);
  ui.switchMode("production");
  assert.equal(ui.element("boss-id").disabled, false);
  assert.equal(ui.element("boss-selection").hidden, false);
});

test("SSE result is inserted and the connection closes", async () => {
  const ui = await loadUI();
  await ui.submit();
  for (const node of ["RETRIEVE", "CANDIDATES", "ANALYZE", "FORMAT"]) {
    ui.streams[0].listeners.node_status({ data: JSON.stringify({ node }) });
  }
  ui.streams[0].listeners.result({ data: "<article>Lineup Recommendations</article>" });
  assert.equal(ui.element("result-container").innerHTML, "<article>Lineup Recommendations</article>");
  assert.equal(ui.streams[0].closed, true);
  assert.equal(ui.element("submit").disabled, false);
  assert.equal(ui.intervals.size, 0);
  assert.equal(ui.element("step-format").classList.values.has("done"), true);
});

test("typed production failures show safe field guidance without echoing input", async () => {
  const ui = await loadUI();
  await ui.submit();
  ui.streams[0].listeners.node_status({ data: JSON.stringify({
    node: "ERROR", failure_type: "boss.unsupported",
    issues: [{ code: "boss.unsupported", field: "boss_id", value: "Private boss", message: "raw internal details" }],
  }) });
  const feedback = ui.element("progress-slot").innerHTML;
  assert.match(feedback, /not available for recommendations/i);
  assert.doesNotMatch(feedback, /Private boss|raw internal details/);
  assert.equal(ui.element("submit").disabled, false);
  assert.equal(ui.streams[0].closed, true);
});

test("existing typed issue codes map to safe next actions", async () => {
  const cases = [
    ["boss.missing", "boss_id", /choose a supported boss/i],
    ["boss.unsupported", "boss_id", /not available for recommendations/i],
    ["boss.unready", "boss_id", /not ready for recommendations/i],
    ["boss.query_conflict", "preferences", /different boss/i],
    ["roster.unresolved", "roster", /saved characters are unavailable/i],
    ["roster.ambiguous", "roster", /exact form name/i],
    ["sidekick.unresolved", "owned_sidekicks", /saved sidekicks are unavailable/i],
    ["sidekick.ambiguous", "owned_sidekicks", /exact name from the loaded sidekick list/i],
    ["request.invalid", "query", /review the question or preferences/i],
  ];
  for (const [code, field, guidance] of cases) {
    const ui = await loadUI();
    await ui.submit();
    ui.streams[0].listeners.node_status({ data: JSON.stringify({
      node: "ERROR", failure_type: code,
      issues: [{ code, field, value: "SENSITIVE INPUT", message: "PRIVATE DIAGNOSTIC" }],
    }) });
    const feedback = ui.element("progress-slot").innerHTML;
    assert.match(feedback, guidance, code);
    assert.doesNotMatch(feedback, /SENSITIVE INPUT|PRIVATE DIAGNOSTIC/);
    assert.equal(ui.element("submit").disabled, false);
  }
});

test("POST validation and network failures give safe guidance and preserve inputs", async () => {
  const invalid = await loadUI({
    roster: ["Aldo", "Ciel"], query: "keep this question",
    postResponses: [{ ok: false, status: 422, body: { detail: [{ loc: ["body", "roster"], msg: "raw request value" }] } }],
  });
  await invalid.submit();
  assert.match(invalid.element("progress-slot").innerHTML, /saved characters are unavailable/i);
  assert.doesNotMatch(invalid.element("progress-slot").innerHTML, /raw request value/);
  assert.equal(invalid.element("query-input").value, "keep this question");
  assert.deepEqual(invalid.roster(), ["Aldo", "Ciel"]);
  assert.equal(invalid.element("submit").disabled, false);

  const offline = await loadUI({ postResponses: [{ reject: true, message: "raw network details" }] });
  await offline.submit();
  assert.match(offline.element("progress-slot").innerHTML, /check your connection/i);
  assert.doesNotMatch(offline.element("progress-slot").innerHTML, /raw network details/);
  assert.equal(offline.element("submit").disabled, false);
});

test("POST server errors and missing or unavailable stream connections settle cleanly", async () => {
  for (const status of [404, 503]) {
    const ui = await loadUI({ postResponses: [{ ok: false, status }] });
    await ui.submit();
    assert.match(ui.element("progress-slot").innerHTML, status === 404 ? /endpoint was not found/i : /server could not start/i);
    assert.equal(ui.element("submit").disabled, false);
    assert.equal(ui.intervals.size, 0);
  }

  const missingJob = await loadUI({ postResponses: [{ noStream: true }] });
  await missingJob.submit();
  assert.match(missingJob.element("progress-slot").innerHTML, /did not provide its progress connection/i);
  assert.equal(missingJob.element("submit").disabled, false);

  const unavailableStream = await loadUI({ streamConstructionFails: true });
  await unavailableStream.submit();
  assert.match(unavailableStream.element("progress-slot").innerHTML, /stream could not be opened/i);
  assert.equal(unavailableStream.element("submit").disabled, false);
});

test("a stale saved roster entry can be removed without clearing valid ownership", async () => {
  const ui = await loadUI({
    roster: [], sidekicks: [],
    storageValues: { roster: JSON.stringify(["Aldo", "Unavailable form"]), sidekicks: JSON.stringify(["Tetra"]) },
    entityResponse: { characters: ["Aldo"], sidekicks: ["Tetra"] },
  });
  assert.match(ui.element("selection-status").innerHTML, /unavailable in the loaded lists/i);
  assert.equal(ui.element("character-list").staleControls.length, 1);
  ui.element("character-list").staleControls[0].listeners.click();
  assert.deepEqual(ui.roster(), ["Aldo"]);
  assert.deepEqual(ui.sidekicks(), ["Tetra"]);
  assert.match(ui.element("selection-status").innerHTML, /other saved selections were kept/i);
});

test("malformed and unavailable browser storage leave the page usable", async () => {
  const malformed = await loadUI({ storageValues: { roster: "{broken", sidekicks: "{}" } });
  assert.match(malformed.element("selection-status").innerHTML, /could not be read/i);
  assert.equal(malformed.storage.get("anothereden_roster"), "{broken");
  await malformed.submit();
  assert.equal(malformed.requests.length, 1);
  assert.deepEqual(malformed.requests[0].payload.roster, []);

  const unavailable = await loadUI({ storageReadFails: true, storageWriteFails: true });
  assert.match(unavailable.element("selection-status").innerHTML, /could not be read/i);
  assert.doesNotMatch(unavailable.element("selection-status").innerHTML, /storage details must not be shown/);
  unavailable.saveRoster(["Aldo"]);
  assert.deepEqual(unavailable.roster(), ["Aldo"]);
  assert.match(unavailable.element("selection-status").innerHTML, /could not save character selections/i);
});

test("entity-load failure keeps saved selections and gives reload guidance", async () => {
  const ui = await loadUI({ roster: ["Aldo", "Ciel"], sidekicks: ["Tetra"], entityFailure: true });
  assert.match(ui.element("selection-status").innerHTML, /reload the page to try again/i);
  assert.match(ui.element("character-list").innerHTML, /could not be loaded/i);
  await ui.submit();
  assert.deepEqual(ui.requests[0].payload.roster, ["Aldo", "Ciel"]);
  assert.deepEqual(ui.requests[0].payload.owned_sidekicks, ["Tetra"]);

  const malformed = await loadUI({ entityResponse: { characters: "not a list", sidekicks: [] } });
  assert.match(malformed.element("selection-status").innerHTML, /lists could not be loaded/i);
  await malformed.submit();
  assert.deepEqual(malformed.requests[0].payload.roster, ["Aldo"]);
});

test("SSE no-result completion and disconnect settle progress; retry creates a fresh job", async () => {
  const ui = await loadUI({ query: "preserve preference" });
  await ui.submit();
  ui.streams[0].listeners.node_status({ data: JSON.stringify({ node: "RETRIEVE" }) });
  assert.equal(ui.intervals.size, 1);
  ui.streams[0].listeners.done({ data: "" });
  assert.match(ui.element("progress-slot").innerHTML, /ended without returning a result/i);
  assert.equal(ui.element("submit").disabled, false);
  assert.equal(ui.intervals.size, 0);
  assert.equal(ui.streams[0].closed, true);
  assert.equal(ui.element("query-input").value, "preserve preference");

  await ui.submit();
  assert.equal(ui.requests.length, 2);
  assert.equal(ui.streams.length, 2);
  assert.notEqual(ui.streams[0].url, ui.streams[1].url);
  ui.streams[1].onerror();
  assert.match(ui.element("progress-slot").innerHTML, /job may be unavailable or expired/i);
  assert.equal(ui.element("submit").disabled, false);
  assert.equal(ui.intervals.size, 0);
});

test("render failure is actionable and unknown SSE failures stay generic", async () => {
  const ui = await loadUI();
  await ui.submit();
  ui.streams[0].listeners.node_status({ data: JSON.stringify({ node: "ERROR", failure_type: "result.render" }) });
  assert.match(ui.element("progress-slot").innerHTML, /result could not be displayed/i);
  assert.equal(ui.element("submit").disabled, false);

  await ui.submit();
  ui.streams[1].listeners.node_status({ data: JSON.stringify({ node: "ERROR", failure_type: "unknown.internal.failure", message: "secret details" }) });
  assert.match(ui.element("progress-slot").innerHTML, /request could not finish/i);
  assert.doesNotMatch(ui.element("progress-slot").innerHTML, /secret details|unknown\.internal\.failure/);
});
