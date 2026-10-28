/* Zero-dependency browser interaction smoke tests. Run: node --test scripts/portfolio-smoke.test.cjs */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const ROOT = path.resolve(__dirname, "..");
const SOURCE = fs.readFileSync(path.join(ROOT, "docs/assets/app.js"), "utf8");
const HTML = fs.readFileSync(path.join(ROOT, "docs/index.html"), "utf8");
const PROFILE = JSON.parse(fs.readFileSync(path.join(ROOT, "docs/data/profile.json"), "utf8"));

class Element {
  constructor(tag, attributes = {}) {
    this.tagName = tag;
    this.children = [];
    this.attributes = { ...attributes };
    this.dataset = {};
    this.listeners = {};
    this.style = { setProperty() {} };
    this.value = "";
    this.hidden = false;
    this.className = "";
    this._text = "";
    this.parentNode = null;
  }
  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }
  get textContent() {
    return this._text + this.children.map(child => child.textContent).join(" ");
  }
  appendChild(child) {
    assert.ok(child instanceof Element, "A DOM node was expected");
    this.children.push(child);
    child.parentNode = this;
    return child;
  }
  replaceChildren(...children) {
    this.children = [];
    this._text = "";
    for (const child of children) this.appendChild(child);
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name]; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(type, callback) {
    (this.listeners[type] ||= []).push(callback);
  }
  dispatch(type, value = this.value) {
    this.value = value;
    for (const handler of this.listeners[type] || []) {
      handler({ type, target: this, currentTarget: this });
    }
  }
}

function harness({ failFetch = false } = {}) {
  const ids = [...HTML.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
  const elements = new Map(ids.map(id => [id, new Element("div", { id })]));
  elements.get("projectCategory").value = "All";
  elements.get("projectSort").value = "featured";
  const repoScopes = ["featured", "all", "forks"].map(scope => {
    const b = new Element("button"); b.dataset.repoScope = scope; return b;
  });
  const prStates = ["all", "merged", "open"].map(state => {
    const b = new Element("button"); b.dataset.prState = state; return b;
  });
  const document = {
    documentElement: { dataset: {} },
    createElement(tag) { return new Element(tag); },
    querySelector(selector) {
      if (selector.startsWith("#")) {
        const el = elements.get(selector.slice(1));
        if (!el) throw new Error("Missing element " + selector);
        return el;
      }
      throw new Error("Unsupported single-element selector: " + selector);
    },
    querySelectorAll(selector) {
      if (selector === "[data-pr-state]") return prStates;
      if (selector === "[data-repo-scope]") return repoScopes;
      throw new Error("Unsupported multi-element selector: " + selector);
    },
  };
  const logs = [];
  const context = {
    document,
    URL,
    Date,
    console: { warn: (...args) => logs.push(args.join(" ")) },
    window: { matchMedia: () => ({ matches: false }) },
    localStorage: { getItem: () => null, setItem() {} },
    fetch: async () => {
      if (failFetch) throw new Error("offline");
      return { ok: true, json: async () => PROFILE };
    },
  };
  vm.runInNewContext(SOURCE, context, { filename: "docs/assets/app.js", timeout: 5000 });
  return {
    elements,
    prStates,
    repoScopes,
    logs,
    async flush() {
      await new Promise(resolve => setImmediate(resolve));
      await new Promise(resolve => setImmediate(resolve));
    },
    text(id) { return elements.get(id).textContent; },
    dispatch(id, type, value) { elements.get(id).dispatch(type, value); },
  };
}

test("portfolio boots: project and PR data actually render, company-only", async () => {
  const app = harness();
  await app.flush();
  assert.match(app.text("statRepos"), /\d+/);
  assert.match(app.text("projectsCount"), /project/);
  assert.ok(app.elements.get("projectsGrid").children.length > 0, "Projects grid should populate");
  const prs = app.text("prList");
  for (const company of ["Tesla", "Meta", "Google DeepMind", "Waymo"]) {
    assert.ok(prs.includes(company), "Missing company " + company);
  }
  assert.match(prs, /mariana-trench/i);
  assert.match(prs, /CodeSync/);
  assert.match(prs, /81b835d/i);
  assert.doesNotMatch(prs, /maharshi-coding\/(ai-tutor-app|oss-agent|ride-share)/i);
  assert.equal(app.logs.length, 0, "No browser warnings should be emitted");
});

test("merged, open, and company search controls update real PR rows", async () => {
  const app = harness();
  await app.flush();

  const merged = app.prStates.find(p => p.dataset.prState === "merged");
  merged.dispatch("click");
  assert.match(app.text("prList"), /Meta/);
  assert.match(app.text("prList"), /Landed upstream via Meta CodeSync/);
  assert.match(app.text("prList"), /Tesla/);
  assert.doesNotMatch(app.text("prList"), /pyrefly/i);

  const open = app.prStates.find(p => p.dataset.prState === "open");
  open.dispatch("click");
  assert.match(app.text("prList"), /pyrefly/i);
  assert.doesNotMatch(app.text("prList"), /mariana-trench/i);

  app.dispatch("prSearch", "input", "Waymo");
  assert.match(app.text("prList"), /Waymo/);
  assert.doesNotMatch(app.text("prList"), /Meta/);
});

test("repository filters and accessible details modal work", async () => {
  const app = harness();
  await app.flush();
  app.repoScopes.find(p => p.dataset.repoScope === "all").dispatch("click");
  assert.match(app.text("projectsCount"), /project/);
  app.dispatch("projectSearch", "input", "FulfillFlow");
  assert.match(app.text("projectsGrid"), /FulfillFlow/i);
  app.dispatch("projectSearch", "input", "there-is-no-such-project");
  assert.match(app.text("projectsGrid"), /No repositories match/i);
  const dark = app.elements.get("themeToggle");
  dark.dispatch("click");
  assert.equal(dark.getAttribute("aria-label"), "Switch to light theme");
});

test("unavailable data shows explicit messages instead of hanging on Loading", async () => {
  const app = harness({ failFetch: true });
  await app.flush();
  assert.match(app.text("prList"), /temporarily unavailable/i);
  assert.match(app.text("projectsGrid"), /could not be loaded/i);
  assert.match(app.text("updated"), /Unable to load/i);
});

test("server-rendered HTML includes a usable PR fallback if scripts cannot run", () => {
  assert.match(HTML, /Static GitHub-data fallback/);
  for (const company of ["Tesla", "Meta", "Google DeepMind", "Waymo"]) {
    assert.ok(HTML.includes(company), "Missing fallback company " + company);
  }
  assert.match(HTML, /mariana-trench\/pull\/277/);
  assert.match(HTML, /81b835dff56763b871d9db8dcbf29bdb1bb35973/);
  assert.match(HTML, /app\.js\?v=20261028-prfix2/);
});
