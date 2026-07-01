/**
 * AnotherEdenAI roster localStorage sync + client-side filter.
 */
const STORAGE_KEY = "anothereden_roster";
const SIDEKICK_STORAGE_KEY = "anothereden_sidekicks";

function loadRoster() {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
}
function loadSidekicks() {
  return JSON.parse(localStorage.getItem(SIDEKICK_STORAGE_KEY) || "[]");
}
function saveRoster(roster) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(roster));
  updateRosterPayload();
}
function saveSidekicks(sidekicks) {
  localStorage.setItem(SIDEKICK_STORAGE_KEY, JSON.stringify(sidekicks));
}

function updateRosterPayload() {
  const payload = document.getElementById("roster-payload");
  if (payload) payload.value = JSON.stringify(loadRoster());
}

function switchTab(tab) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.getElementById("panel-" + tab).classList.add("active");
}

function filterList(type) {
  const searchId = type === "characters" ? "character-search" : "sidekick-search";
  const listId = type === "characters" ? "character-list" : "sidekick-list";
  const q = document.getElementById(searchId).value.toLowerCase();
  document.querySelectorAll(`#${listId} .roster-item`).forEach(item => {
    item.style.display = item.dataset.name.toLowerCase().includes(q) ? "" : "none";
  });
}

function buildChecklistHTML(names, storageKey, listId, checkboxClass) {
  const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
  const ul = document.getElementById(listId);
  if (!ul) return;
  ul.innerHTML = names.map(name => `
    <div class="roster-item" data-name="${name}">
      <label>
        <input type="checkbox" class="${checkboxClass}" value="${name}"
               ${saved.includes(name) ? "checked" : ""}>
        ${name}
      </label>
    </div>
  `).join("");

  ul.querySelectorAll(`.${checkboxClass}`).forEach(cb => {
    cb.addEventListener("change", () => {
      const kind = checkboxClass === "char-checkbox" ? "character" : "sidekick";
      const current = kind === "character" ? loadRoster() : loadSidekicks();
      const updated = cb.checked
        ? [...new Set([...current, cb.value])]
        : current.filter(n => n !== cb.value);
      if (kind === "character") saveRoster(updated);
      else saveSidekicks(updated);
    });
  });
}

// ---------------------------------------------------------------------------
// Pipeline step tracker
// ---------------------------------------------------------------------------

const NODE_TO_STEP = {
  "PLAN":     "step-plan",
  "CYPHER":   "step-cypher",
  "VALIDATE": "step-validate",
  "CANDIDATES": "step-candidates",
  "ANALYZE":  "step-analyze",
  "FORMAT":   "step-format",
};

const STEP_LABELS = {
  "PLAN":     "Planning strategy",
  "CYPHER":   "Building database query",
  "VALIDATE": "Validating results",
  "CANDIDATES": "Preparing legal candidates",
  "ANALYZE":  "Analyzing team composition",
  "FORMAT":   "Formatting recommendations",
};

const STEPS_HTML = `
<div id="pipeline-steps" aria-live="polite">
  <div class="pipeline-step" id="step-plan"     data-node="PLAN">
    <span class="step-icon">⬜</span>
    <span class="step-label">Planning strategy</span>
    <span class="step-time"></span>
  </div>
  <div class="pipeline-step" id="step-cypher"   data-node="CYPHER">
    <span class="step-icon">⬜</span>
    <span class="step-label">Building database query</span>
    <span class="step-time"></span>
  </div>
  <div class="pipeline-step" id="step-validate" data-node="VALIDATE">
    <span class="step-icon">⬜</span>
    <span class="step-label">Validating results</span>
    <span class="step-time"></span>
  </div>
  <div class="pipeline-step" id="step-candidates" data-node="CANDIDATES">
    <span class="step-icon">⬜</span>
    <span class="step-label">Preparing legal candidates</span>
    <span class="step-time"></span>
  </div>
  <div class="pipeline-step" id="step-analyze"  data-node="ANALYZE">
    <span class="step-icon">⬜</span>
    <span class="step-label">Analyzing team composition</span>
    <span class="step-time"></span>
  </div>
  <div class="pipeline-step" id="step-format"   data-node="FORMAT">
    <span class="step-icon">⬜</span>
    <span class="step-label">Formatting recommendations</span>
    <span class="step-time"></span>
  </div>
</div>`;

let pipelineActiveStepId = null;
let stepStartTime = null;
let stepTimerInterval = null;

function stepStartTimer() {
  stepStartTime = Date.now();
  stepTimerInterval = setInterval(() => {
    if (!pipelineActiveStepId) return;
    const el = document.getElementById(pipelineActiveStepId);
    if (!el) return;
    const t = el.querySelector(".step-time");
    if (t) t.textContent = ((Date.now() - stepStartTime) / 1000).toFixed(1) + "s";
  }, 100);
}

function stepStopTimer() {
  clearInterval(stepTimerInterval);
  stepTimerInterval = null;
}

function stepMarkDone(stepId, elapsed) {
  const el = document.getElementById(stepId);
  if (!el) return;
  el.classList.remove("active");
  el.classList.add("done");
  el.querySelector(".step-icon").textContent = "✅";
  const retry = el.querySelector(".step-retry");
  if (retry) retry.remove();
  const label = el.querySelector(".step-label");
  if (label) label.textContent = STEP_LABELS[el.dataset.node] || label.textContent;
  const t = el.querySelector(".step-time");
  if (t && elapsed != null) t.textContent = elapsed.toFixed(1) + "s";
}

function stepMarkActive(stepId, label, retryText) {
  const el = document.getElementById(stepId);
  if (!el) return;
  el.classList.add("active");
  el.querySelector(".step-icon").innerHTML = '<span class="spinner"></span>';
  const labelEl = el.querySelector(".step-label");
  if (labelEl) labelEl.textContent = label;
  const t = el.querySelector(".step-time");
  if (t) t.textContent = "0.0s";
  const oldRetry = el.querySelector(".step-retry");
  if (oldRetry) oldRetry.remove();
  if (retryText) {
    const badge = document.createElement("span");
    badge.className = "step-retry";
    badge.textContent = retryText;
    el.appendChild(badge);
  }
}

function setSubmitBusy(busy) {
  const btn = document.querySelector("#query-form button[type=submit]");
  if (!btn) return;
  if (busy) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:0.85rem;height:0.85rem;border-width:2px"></span> Running…';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText || "Find Best Team";
  }
}

function handleNodeStatus(payload) {
  const node    = payload.node    || "UNKNOWN";
  const attempt = payload.attempt || 1;
  const max     = payload.max     || 1;

  // Mark previous step done with elapsed time
  if (pipelineActiveStepId && pipelineActiveStepId !== NODE_TO_STEP[node]) {
    const elapsed = stepStartTime ? (Date.now() - stepStartTime) / 1000 : null;
    stepStopTimer();
    stepMarkDone(pipelineActiveStepId, elapsed);
  }

  if (node === "ERROR") {
    stepStopTimer();
    if (pipelineActiveStepId) {
      const el = document.getElementById(pipelineActiveStepId);
      if (el) {
        el.classList.remove("active");
        el.classList.add("error-step");
        el.querySelector(".step-icon").textContent = "❌";
        el.querySelector(".step-label").textContent = "Pipeline error — please retry";
        const t = el.querySelector(".step-time");
        if (t) t.textContent = "";
      }
    }
    setSubmitBusy(false);
    pipelineActiveStepId = null;
    return;
  }

  const stepId = NODE_TO_STEP[node];
  if (!stepId) return;

  let retryText = null;
  if (node === "VALIDATE" && attempt > 1) retryText = "Cypher retry " + attempt + "/" + max;
  if (node === "ANALYZE" && payload.correction_rounds > 0) {
    retryText = "correction " + payload.correction_rounds + "/2";
  }

  stepMarkActive(stepId, STEP_LABELS[node] || node, retryText);
  pipelineActiveStepId = stepId;
  stepStartTimer();
}

// ---------------------------------------------------------------------------
// SSE pipeline runner — uses native EventSource, no HTMX SSE extension needed
// ---------------------------------------------------------------------------

function runPipeline(streamUrl) {
  const es = new EventSource(streamUrl);

  es.addEventListener("node_status", function(e) {
    let payload;
    try { payload = JSON.parse(e.data); } catch { return; }
    handleNodeStatus(payload);
  });

  es.addEventListener("result", function(e) {
    // Mark last step done
    if (pipelineActiveStepId) {
      const elapsed = stepStartTime ? (Date.now() - stepStartTime) / 1000 : null;
      stepStopTimer();
      stepMarkDone(pipelineActiveStepId, elapsed);
      pipelineActiveStepId = null;
    }
    setSubmitBusy(false);
    // Inject result HTML into result-container
    document.getElementById("result-container").innerHTML = e.data;
    es.close();
  });

  es.addEventListener("done", function() {
    setSubmitBusy(false);
    es.close();
  });

  es.onerror = function() {
    stepStopTimer();
    setSubmitBusy(false);
    es.close();
  };
}

// ---------------------------------------------------------------------------
// Page init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  updateRosterPayload();

  fetch("/api/entities")
    .then(r => r.json())
    .then(data => {
      buildChecklistHTML(data.characters, STORAGE_KEY, "character-list", "char-checkbox");
      buildChecklistHTML(data.sidekicks, SIDEKICK_STORAGE_KEY, "sidekick-list", "sidekick-checkbox");
    })
    .catch(err => {
      console.error("Failed to load entities:", err);
      document.getElementById("character-list").innerHTML = "<p>Error loading characters.</p>";
      document.getElementById("sidekick-list").innerHTML = "<p>Error loading sidekicks.</p>";
    });

  const form = document.getElementById("query-form");
  if (form) {
    form.addEventListener("submit", async (evt) => {
      evt.preventDefault();
      updateRosterPayload();
      const query = document.getElementById("query-input").value.trim();
      if (!query) return;
      const roster = loadRoster();
      const owned_sidekicks = loadSidekicks();

      setSubmitBusy(true);
      pipelineActiveStepId = null;
      stepStopTimer();

      // Inject step tracker UI directly — no HTMX fragment needed
      const slot = document.getElementById("progress-slot");
      slot.innerHTML = STEPS_HTML;
      document.getElementById("result-container").innerHTML = "";

      try {
        const resp = await fetch("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, roster, owned_sidekicks }),
        });
        if (!resp.ok) {
          slot.innerHTML = `<p style="color:red">Error ${resp.status}: ${resp.statusText}</p>`;
          setSubmitBusy(false);
          return;
        }
        // Extract job_id from the returned fragment to get the stream URL
        const html = await resp.text();
        const match = html.match(/sse-connect="([^"]+)"/);
        if (!match) {
          slot.innerHTML = `<p style="color:red">Could not find stream URL in response.</p>`;
          setSubmitBusy(false);
          return;
        }
        runPipeline(match[1]);
      } catch (err) {
        slot.innerHTML = `<p style="color:red">Network error: ${err.message}</p>`;
        setSubmitBusy(false);
      }
    });
  }
});
