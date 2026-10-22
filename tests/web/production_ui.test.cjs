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
  assert.equal(ui.streams[0].url, "/api/stream/test-job");
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
  ui.streams[0].listeners.result({ data: "<article>Lineup Recommendations</article>" });
  assert.equal(ui.element("result-container").innerHTML, "<article>Lineup Recommendations</article>");
  assert.equal(ui.streams[0].closed, true);
  assert.equal(ui.element("submit").disabled, false);
});
