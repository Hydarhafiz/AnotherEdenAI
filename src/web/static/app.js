/**
 * AnotherEdenAI roster localStorage sync + client-side filter.
 */
const STORAGE_KEY = "anothereden_roster";
const SIDEKICK_STORAGE_KEY = "anothereden_sidekicks";
let rosterSelection = [];
let sidekickSelection = [];
let selectionMessages = [];
let activeEventSource = null;

function normalizeSelection(value) {
  if (!Array.isArray(value) || value.some(item => typeof item !== "string")) return null;
  return [...new Set(value.map(item => item.trim()).filter(Boolean))];
}

function readStoredSelection(key, label) {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return [];
    const parsed = normalizeSelection(JSON.parse(raw));
    if (parsed !== null) return parsed;
  } catch {
    // Browser storage can be disabled or contain malformed saved JSON.
  }
  selectionMessages.push(`Saved ${label} selections could not be read. Select them again; current-page changes will remain available.`);
  return [];
}

function readSelections() {
  selectionMessages = [];
  rosterSelection = readStoredSelection(STORAGE_KEY, "character");
  sidekickSelection = readStoredSelection(SIDEKICK_STORAGE_KEY, "sidekick");
}

function selectionForKey(key) {
  return key === STORAGE_KEY ? rosterSelection : sidekickSelection;
}

function loadRoster() {
  return [...rosterSelection];
}

function loadSidekicks() {
  return [...sidekickSelection];
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
  })[character]);
}

function renderSelectionMessages(role = "alert") {
  const target = document.getElementById("selection-status");
  if (!target) return;
  target.innerHTML = selectionMessages.length
    ? `<div class="user-feedback" role="${role}" aria-live="${role === "alert" ? "assertive" : "polite"}">${selectionMessages.map(message => `<p>${escapeHTML(message)}</p>`).join("")}</div>`
    : "";
}

function saveSelection(key, values, label) {
  const normalized = normalizeSelection(values) || [];
  if (key === STORAGE_KEY) rosterSelection = normalized;
  else sidekickSelection = normalized;
  try {
    localStorage.setItem(key, JSON.stringify(normalized));
  } catch {
    selectionMessages = selectionMessages.filter(message => !message.includes(`Browser storage could not save ${label} selections`));
    selectionMessages.push(`Browser storage could not save ${label} selections. Your current choices remain available until this page closes.`);
    renderSelectionMessages();
  }
}

function saveRoster(roster) {
  saveSelection(STORAGE_KEY, roster, "character");
  updateRosterPayload();
}

function saveSidekicks(sidekicks) {
  saveSelection(SIDEKICK_STORAGE_KEY, sidekicks, "sidekick");
}

function updateRosterPayload() {
  const payload = document.getElementById("roster-payload");
  if (payload) payload.value = JSON.stringify(rosterSelection);
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
  const saved = selectionForKey(storageKey);
  const ul = document.getElementById(listId);
  if (!ul) return;
  const known = new Set(names.map(name => name.toLocaleLowerCase()));
  const stale = saved.filter(name => !known.has(name.toLocaleLowerCase()));
  const listHTML = names.map(name => `
    <div class="roster-item" data-name="${escapeHTML(name)}">
      <label>
        <input type="checkbox" class="${checkboxClass}" value="${escapeHTML(name)}"
               ${saved.some(item => item.toLocaleLowerCase() === name.toLocaleLowerCase()) ? "checked" : ""}>
        ${escapeHTML(name)}
      </label>
    </div>
  `).join("");
  const staleHTML = stale.map((name, index) => `
    <div class="stale-selection">
      <span>Saved selection is unavailable: <strong>${escapeHTML(name)}</strong>.</span>
      <button type="button" class="remove-stale-selection" data-stale-index="${index}">Remove saved selection</button>
    </div>
  `).join("");
  ul.innerHTML = listHTML + staleHTML;

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

  ul.querySelectorAll(".remove-stale-selection").forEach(button => {
    button.addEventListener("click", () => {
      const staleName = stale[Number(button.dataset.staleIndex)];
      if (!staleName) return;
      const updated = selectionForKey(storageKey).filter(name => name !== staleName);
      const label = storageKey === STORAGE_KEY ? "character" : "sidekick";
      saveSelection(storageKey, updated, label);
      buildChecklistHTML(names, storageKey, listId, checkboxClass);
      selectionMessages = selectionMessages.filter(message => !message.startsWith("Some saved selections are unavailable"));
      selectionMessages.push(`Removed unavailable saved ${label} “${staleName}”. Other saved selections were kept.`);
      renderSelectionMessages("status");
      updateRosterPayload();
    });
  });
}

// ---------------------------------------------------------------------------
// Pipeline step tracker
// ---------------------------------------------------------------------------

const NODE_TO_STEP = {
  "RETRIEVE": "step-retrieve",
  "PLAN":     "step-plan",
  "CYPHER":   "step-cypher",
  "VALIDATE": "step-validate",
  "CANDIDATES": "step-candidates",
  "ANALYZE":  "step-analyze",
  "FORMAT":   "step-format",
};

const STEP_LABELS = {
  "RETRIEVE": "Retrieving boss and roster",
  "PLAN":     "Planning strategy",
  "CYPHER":   "Building database query",
  "VALIDATE": "Validating results",
  "CANDIDATES": "Preparing legal candidates",
  "ANALYZE":  "Analyzing team composition",
  "FORMAT":   "Formatting recommendations",
};

function pipelineStepsHTML(mode) {
  const nodes = mode === "production"
    ? ["RETRIEVE", "CANDIDATES", "ANALYZE", "FORMAT"]
    : ["PLAN", "CYPHER", "VALIDATE", "CANDIDATES", "ANALYZE", "FORMAT"];
  return `<div id="pipeline-steps" aria-live="polite">${nodes.map(node => `
    <div class="pipeline-step" id="${NODE_TO_STEP[node]}" data-node="${node}">
      <span class="step-icon">⬜</span>
      <span class="step-label">${STEP_LABELS[node]}</span>
      <span class="step-time"></span>
    </div>`).join("")}</div>`;
}

function updateQueryMode() {
  const production = document.getElementById("workflow-mode").value === "production";
  const boss = document.getElementById("boss-id");
  boss.disabled = !production;
  boss.required = production;
  document.getElementById("boss-selection").hidden = !production;
  const query = document.getElementById("query-input");
  query.required = !production;
  query.placeholder = production
    ? "Optional preferences for the selected boss"
    : "Ask a question about the graph";
  document.getElementById("query-label").textContent = production
    ? "Preferences (optional)"
    : "Graph question";
}

let pipelineActiveStepId = null;
let stepStartTime = null;
let stepTimerInterval = null;

function stepStartTimer() {
  stepStopTimer();
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

function completeActivePipelineStep() {
  if (!pipelineActiveStepId) return;
  const elapsed = stepStartTime ? (Date.now() - stepStartTime) / 1000 : null;
  stepStopTimer();
  stepMarkDone(pipelineActiveStepId, elapsed);
  pipelineActiveStepId = null;
}

function setSubmitBusy(busy) {
  const btn = document.querySelector("#query-form button[type=submit]");
  if (!btn) return;
  if (busy) {
    btn.disabled = true;
    if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:0.85rem;height:0.85rem;border-width:2px"></span> Running…';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText || "Find Recommendations";
  }
}

function handleNodeStatus(payload) {
  const node    = payload.node    || "UNKNOWN";
  const attempt = payload.attempt || 1;
  const max     = payload.max     || 1;

  // Mark previous step done with elapsed time
  if (pipelineActiveStepId && pipelineActiveStepId !== NODE_TO_STEP[node]) {
    completeActivePipelineStep();
  }

  const stepId = NODE_TO_STEP[node];
  if (!stepId) return;

  let retryText = null;
  if (node === "VALIDATE" && attempt > 1) retryText = "Cypher retry " + attempt + "/" + max;
  if (node === "ANALYZE" && payload.correction_rounds > 0) {
    retryText = "correction " + payload.correction_rounds + "/" + Math.max(0, max - 1);
  }

  stepMarkActive(stepId, STEP_LABELS[node] || node, retryText);
  pipelineActiveStepId = stepId;
  stepStartTimer();
}

// ---------------------------------------------------------------------------
// Safe request guidance and SSE lifecycle
// ---------------------------------------------------------------------------

const FAILURE_COPY = {
  "boss.missing": "Choose a supported boss, then submit again.",
  "boss.unsupported": "That boss is not available for recommendations. Choose a supported boss from the list.",
  "boss.unready": "That boss is not ready for recommendations. Choose a supported boss from the list.",
  "boss.query_conflict": "Your preferences mention a different boss. Change the boss selection or remove the conflicting boss from preferences.",
  "roster.unresolved": "One or more saved characters are unavailable. Remove the unavailable name below; your other selections will be kept.",
  "roster.ambiguous": "A character selection is ambiguous. Choose the exact form name from the loaded character list.",
  "sidekick.unresolved": "One or more saved sidekicks are unavailable. Remove the unavailable name below or update the selection.",
  "sidekick.ambiguous": "A sidekick selection is ambiguous. Choose the exact name from the loaded sidekick list.",
  "result.render": "The request finished, but its result could not be displayed. Your selections are unchanged; submit again to start a new request.",
};

function messageForInvalidField(field) {
  const name = String(field || "").split(".")[0];
  if (name === "boss_id") return FAILURE_COPY["boss.missing"];
  if (name === "roster") return FAILURE_COPY["roster.unresolved"];
  if (name === "owned_sidekicks") return FAILURE_COPY["sidekick.unresolved"];
  if (name === "query") return "Review the question or preferences, then submit again.";
  return "Some request fields are invalid. Review the boss and saved selections, then submit again.";
}

function failureMessages(payload) {
  const issues = Array.isArray(payload && payload.issues) ? payload.issues : [];
  const messages = issues.map(issue => {
    const code = issue && typeof issue.code === "string" ? issue.code : "";
    if (code === "request.invalid") return messageForInvalidField(issue.field);
    return FAILURE_COPY[code];
  }).filter(Boolean);
  if (messages.length) return [...new Set(messages)];
  const code = payload && typeof payload.failure_type === "string" ? payload.failure_type : "";
  if (FAILURE_COPY[code]) return [FAILURE_COPY[code]];
  if (code === "request.invalid") return ["Some request fields are invalid. Review the boss and saved selections, then submit again."];
  return ["The request could not finish. Your selections are unchanged; review them and submit again to start a new request."];
}

function renderFeedback(containerId, messages, role = "alert") {
  const target = document.getElementById(containerId);
  if (!target) return;
  const live = role === "alert" ? "assertive" : "polite";
  target.innerHTML = `<div class="user-feedback" role="${role}" aria-live="${live}"${role === "alert" ? ' tabindex="-1"' : ""}>${messages.map(message => `<p>${escapeHTML(message)}</p>`).join("")}</div>`;
  if (role === "alert") target.querySelector(".user-feedback")?.focus();
}

function settlePipeline(eventSource = activeEventSource) {
  stepStopTimer();
  pipelineActiveStepId = null;
  setSubmitBusy(false);
  if (eventSource) eventSource.close();
  if (activeEventSource === eventSource) activeEventSource = null;
}

function failPipeline(messages, eventSource = activeEventSource) {
  settlePipeline(eventSource);
  renderFeedback("progress-slot", messages, "alert");
}

function postFailureMessages(response) {
  if (response.status === 422) {
    return response.json().then(body => {
      const detail = Array.isArray(body && body.detail) ? body.detail : [];
      const messages = detail.map(issue => {
        const location = Array.isArray(issue && issue.loc) ? issue.loc.filter(part => part !== "body").join(".") : "";
        return messageForInvalidField(location);
      });
      return messages.length ? [...new Set(messages)] : ["Some request fields are invalid. Review the form and submit again."];
    }).catch(() => ["Some request fields are invalid. Review the form and submit again."]);
  }
  if (response.status === 404) return Promise.resolve(["The request endpoint was not found. Reload the page, then submit again."]);
  if (response.status >= 500) return Promise.resolve(["The server could not start this request. Your selections are unchanged; wait briefly and submit again."]);
  return Promise.resolve(["The server did not accept this request. Review the form and submit again."]);
}

function validateEntityNames(value) {
  if (!Array.isArray(value) || value.some(name => typeof name !== "string")) {
    throw new Error("Invalid entity list");
  }
  return [...new Set(value.map(name => name.trim()).filter(Boolean))];
}

async function loadEntityLists() {
  try {
    const response = await fetch("/api/entities");
    if (!response.ok) throw new Error("Entity request failed");
    const data = await response.json();
    const characters = validateEntityNames(data && data.characters);
    const sidekicks = validateEntityNames(data && data.sidekicks);
    buildChecklistHTML(characters, STORAGE_KEY, "character-list", "char-checkbox");
    buildChecklistHTML(sidekicks, SIDEKICK_STORAGE_KEY, "sidekick-list", "sidekick-checkbox");

    const staleCharacters = rosterSelection.filter(name => !characters.some(item => item.toLocaleLowerCase() === name.toLocaleLowerCase()));
    const staleSidekicks = sidekickSelection.filter(name => !sidekicks.some(item => item.toLocaleLowerCase() === name.toLocaleLowerCase()));
    if (staleCharacters.length || staleSidekicks.length) {
      selectionMessages.push("Some saved selections are unavailable in the loaded lists. Remove only those entries below; other saved selections will be kept.");
    }
    renderSelectionMessages(selectionMessages.length ? "alert" : "status");
  } catch {
    const characterList = document.getElementById("character-list");
    const sidekickList = document.getElementById("sidekick-list");
    if (characterList) characterList.innerHTML = "<p role=\"alert\">Character choices could not be loaded. Reload the page and try again.</p>";
    if (sidekickList) sidekickList.innerHTML = "<p role=\"alert\">Sidekick choices could not be loaded. Reload the page and try again.</p>";
    selectionMessages.push("Character and sidekick lists could not be loaded. Reload the page to try again; saved selections have been kept.");
    renderSelectionMessages("alert");
  }
}

function runPipeline(streamUrl) {
  let es;
  try {
    es = new EventSource(streamUrl);
  } catch {
    failPipeline(["The request stream could not be opened. Check your connection, then submit again to start a new request."]);
    return;
  }
  activeEventSource = es;
  let receivedResult = false;

  es.addEventListener("node_status", function(e) {
    if (activeEventSource !== es) return;
    let payload;
    try { payload = JSON.parse(e.data); } catch { return; }
    if (payload.node === "ERROR") {
      failPipeline(failureMessages(payload), es);
      return;
    }
    handleNodeStatus(payload);
  });

  es.addEventListener("result", function(e) {
    if (activeEventSource !== es) return;
    try {
      const result = document.getElementById("result-container");
      if (!result) throw new Error("Missing result target");
      result.innerHTML = e.data;
      receivedResult = true;
      completeActivePipelineStep();
      settlePipeline(es);
    } catch {
      failPipeline(["The request finished, but its result could not be displayed. Your selections are unchanged; submit again to start a new request."], es);
    }
  });

  es.addEventListener("done", function() {
    if (activeEventSource !== es) return;
    if (!receivedResult) {
      failPipeline(["The request ended without returning a result. No recommendation or answer was added. Review the form and submit again to start a new request."], es);
      return;
    }
    settlePipeline(es);
  });

  es.onerror = function() {
    if (activeEventSource !== es) return;
    failPipeline(["The connection ended before a result arrived. The job may be unavailable or expired. Your selections are unchanged; submit again to start a fresh request."], es);
  };
}

// ---------------------------------------------------------------------------
// Page init
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  readSelections();
  renderSelectionMessages("alert");
  updateRosterPayload();
  updateQueryMode();
  document.getElementById("workflow-mode").addEventListener("change", updateQueryMode);
  loadEntityLists();

  const form = document.getElementById("query-form");
  if (form) {
    form.addEventListener("submit", async (evt) => {
      evt.preventDefault();
      updateRosterPayload();
      const query = document.getElementById("query-input").value.trim();
      const mode = document.getElementById("workflow-mode").value;
      const boss_id = document.getElementById("boss-id").value;
      if (mode === "production" ? !boss_id : !query) return;
      const roster = loadRoster();
      const owned_sidekicks = loadSidekicks();

      if (activeEventSource) activeEventSource.close();
      activeEventSource = null;
      setSubmitBusy(true);
      pipelineActiveStepId = null;
      stepStopTimer();

      const slot = document.getElementById("progress-slot");
      slot.innerHTML = pipelineStepsHTML(mode);
      document.getElementById("result-container").innerHTML = "";

      try {
        const response = await fetch("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, roster, owned_sidekicks, mode, boss_id: mode === "production" ? boss_id : null }),
        });
        if (!response.ok) {
          failPipeline(await postFailureMessages(response), null);
          return;
        }
        const html = await response.text();
        const match = html.match(/sse-connect="([^"]+)"/);
        if (!match) {
          failPipeline(["The server accepted the request but did not provide its progress connection. Your selections are unchanged; submit again to start a new request."], null);
          return;
        }
        runPipeline(match[1]);
      } catch {
        failPipeline(["The request could not be sent or its response could not be read. Check your connection, then submit again to start a new request."], null);
      }
    });
  }
});
