/**
 * AnotherEdenAI roster localStorage sync + client-side filter.
 * D-06: Checklist selections sync to localStorage.
 * D-15: Minimal hand-written JS; HTMX handles SSE and DOM swaps.
 */
const STORAGE_KEY = "anothereden_roster";
const GRASTA_STORAGE_KEY = "anothereden_grastas";

function loadRoster() {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
}
function loadGrastas() {
  return JSON.parse(localStorage.getItem(GRASTA_STORAGE_KEY) || "[]");
}
function saveRoster(roster) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(roster));
  updateRosterPayload();
}
function saveGrastas(grastas) {
  localStorage.setItem(GRASTA_STORAGE_KEY, JSON.stringify(grastas));
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
  const searchId = type === "characters" ? "character-search" : "grasta-search";
  const listId = type === "characters" ? "character-list" : "grasta-list";
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
      const isChar = checkboxClass === "char-checkbox";
      const current = isChar ? loadRoster() : loadGrastas();
      const updated = cb.checked
        ? [...new Set([...current, cb.value])]
        : current.filter(n => n !== cb.value);
      if (isChar) saveRoster(updated); else saveGrastas(updated);
    });
  });
}

// Load entities from API on page load (D-04: single GET /api/entities request)
document.addEventListener("DOMContentLoaded", () => {
  updateRosterPayload();

  fetch("/api/entities")
    .then(r => r.json())
    .then(data => {
      buildChecklistHTML(data.characters, STORAGE_KEY, "character-list", "char-checkbox");
      buildChecklistHTML(data.grastas, GRASTA_STORAGE_KEY, "grasta-list", "grasta-checkbox");
    })
    .catch(err => {
      console.error("Failed to load entities:", err);
      document.getElementById("character-list").innerHTML = "<p>Error loading characters.</p>";
      document.getElementById("grasta-list").innerHTML = "<p>Error loading Grastas.</p>";
    });

  // Wire query form to include current roster as JSON before POST
  const form = document.getElementById("query-form");
  if (form) {
    form.addEventListener("htmx:beforeRequest", () => updateRosterPayload());
    form.addEventListener("submit", () => updateRosterPayload());
  }
});
