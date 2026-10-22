// Execute the shipped browser script with only its DOM/network boundaries stubbed.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

async function loadUI({
  mode = "production", boss = "Celestial Mushroom", query = "", roster = ["Aldo"], sidekicks = [],
  entityResponse, entityFailure = false, storageValues = {}, storageReadFails = false,
  storageWriteFails = false, postResponses = [], streamConstructionFails = false,
} = {}) {
  const elements = new Map();
  const intervals = new Set();
  let nextInterval = 1;
  function element(id) {
    if (!elements.has(id)) {
      const children = new Map();
      let html = "";
      const node = {
        id, value: "", textContent: "Find Recommendations", dataset: {}, listeners: {},
        disabled: false, hidden: false, required: false, placeholder: "", staleControls: [],
        classList: {
          values: new Set(),
          add(value) { this.values.add(value); },
          remove(value) { this.values.delete(value); },
        },
        get innerHTML() { return html; },
        set innerHTML(value) {
          html = String(value);
          this.staleControls = [...html.matchAll(/class="remove-stale-selection" data-stale-index="(\d+)"/g)].map(match => ({
            dataset: { staleIndex: match[1] }, listeners: {},
            addEventListener(event, handler) { this.listeners[event] = handler; },
          }));
        },
        querySelectorAll(selector) {
          return selector === ".remove-stale-selection" ? this.staleControls : [];
        },
        querySelector(selector) {
          if (!children.has(selector)) {
            children.set(selector, {
              textContent: "", innerHTML: "", dataset: {},
              classList: {
                add() {}, remove() {},
              },
              focus() { document.activeElement = this; },
              remove() {},
            });
          }
          return children.get(selector);
        },
        addEventListener(event, handler) { this.listeners[event] = handler; },
        appendChild() {},
      };
      elements.set(id, node);
    }
    return elements.get(id);
  }
  element("workflow-mode").value = mode;
  element("boss-id").value = boss;
  element("query-input").value = query;
  const storage = new Map([
    ["anothereden_roster", storageValues.roster ?? JSON.stringify(roster)],
    ["anothereden_sidekicks", storageValues.sidekicks ?? JSON.stringify(sidekicks)],
  ]);
  const requests = [];
  const streams = [];
  const entityData = entityResponse || { characters: roster, sidekicks };
  let postIndex = 0;
  const document = {
    getElementById: element,
    querySelector: () => element("submit"),
    createElement: () => ({ className: "", textContent: "", dataset: {}, remove() {} }),
    addEventListener(event, handler) { this.ready = handler; },
  };
  const sandbox = {
    document, console, Date,
    setInterval: () => { const id = nextInterval++; intervals.add(id); return id; },
    clearInterval: id => intervals.delete(id),
    localStorage: {
      getItem(key) {
        if (storageReadFails) throw new Error("storage details must not be shown");
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (storageWriteFails) throw new Error("storage details must not be shown");
        storage.set(key, value);
      },
    },
    fetch: async (url, options) => {
      if (url === "/api/entities") {
        if (entityFailure) throw new Error("entity details must not be shown");
        return { ok: true, json: async () => entityData };
      }
      requests.push({ url, ...options, payload: JSON.parse(options.body) });
      const response = postResponses[postIndex++];
      if (response && response.reject) throw new Error(response.message || "network details must not be shown");
      if (response && response.ok === false) {
        return {
          ok: false, status: response.status, statusText: response.statusText || "unsafe status text",
          json: async () => response.body,
        };
      }
      if (response && response.noStream) return { ok: true, text: async () => "<div class=\"progress-slot\"></div>" };
      return { ok: true, text: async () => `<div sse-connect="/api/stream/test-job-${postIndex}"></div>` };
    },
    EventSource: class {
      constructor(url) {
        if (streamConstructionFails) throw new Error("stream details must not be shown");
        this.url = url;
        this.listeners = {};
        this.readyState = 0;
        streams.push(this);
      }
      addEventListener(event, handler) { this.listeners[event] = handler; }
      close() { this.closed = true; this.readyState = 2; }
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../../src/web/static/app.js"), "utf8"), sandbox);
  document.ready();
  await new Promise(resolve => setImmediate(resolve));
  return {
    element, requests, streams, storage, intervals,
    submit: () => element("query-form").listeners.submit({ preventDefault() {} }),
    switchMode(value) {
      element("workflow-mode").value = value;
      element("workflow-mode").listeners.change();
    },
    saveRoster: values => sandbox.saveRoster(values),
    roster: () => Array.from(sandbox.loadRoster()),
    sidekicks: () => Array.from(sandbox.loadSidekicks()),
  };
}

module.exports = { loadUI };
