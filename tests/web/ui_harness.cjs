// Execute the shipped browser script with only its DOM/network boundaries stubbed.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

async function loadUI({ mode = "production", boss = "Celestial Mushroom", query = "", roster = ["Aldo"], sidekicks = [] } = {}) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) {
      elements.set(id, {
        value: "", innerHTML: "", textContent: "Find Recommendations", dataset: {},
        listeners: {}, querySelectorAll: () => [],
        addEventListener(event, handler) { this.listeners[event] = handler; },
      });
    }
    return elements.get(id);
  }
  element("workflow-mode").value = mode;
  element("boss-id").value = boss;
  element("query-input").value = query;
  const storage = new Map([
    ["anothereden_roster", JSON.stringify(roster)],
    ["anothereden_sidekicks", JSON.stringify(sidekicks)],
  ]);
  const requests = [];
  const streams = [];
  const document = {
    getElementById: element,
    querySelector: () => element("submit"),
    addEventListener(event, handler) { this.ready = handler; },
  };
  const sandbox = {
    document, console, setInterval: () => 1, clearInterval: () => {},
    localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
    fetch: async (url, options) => {
      if (url === "/api/entities") return { json: async () => ({ characters: [], sidekicks: [] }) };
      requests.push({ url, ...options, payload: JSON.parse(options.body) });
      return { ok: true, text: async () => '<div sse-connect="/api/stream/test-job"></div>' };
    },
    EventSource: class {
      constructor(url) { this.url = url; this.listeners = {}; streams.push(this); }
      addEventListener(event, handler) { this.listeners[event] = handler; }
      close() { this.closed = true; }
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../../src/web/static/app.js"), "utf8"), sandbox);
  document.ready();
  await Promise.resolve();
  return {
    element, requests, streams,
    submit: () => element("query-form").listeners.submit({ preventDefault() {} }),
    switchMode(value) {
      element("workflow-mode").value = value;
      element("workflow-mode").listeners.change();
    },
  };
}

module.exports = { loadUI };
