/* Read-only portfolio explorer powered by docs/data/profile.json. */
(() => {
  "use strict";

  const USER = "maharshi-coding";
  const FEATURED_ORDER = [
    "ai-tutor-app", "FulfillFlow", "oss-agent", "seller-shield",
    "outfallwatch", "overturn", "agent-pixel-visualizer", "datahub-steward-squad"
  ];
  const CATEGORIES = {
    "ai-tutor-app": "AI & agents",
    "oss-agent": "AI & agents",
    "seller-shield": "AI & agents",
    "overturn": "AI & agents",
    "datahub-steward-squad": "AI & agents",
    "FulfillFlow": "Robotics",
    "outfallwatch": "Systems & IoT",
    "agent-pixel-visualizer": "Developer tools",
    "face-attendance-app": "AI & agents",
    "maharshi-os": "Web & mobile",
    "launchpad": "Web & mobile",
    "orlog-game": "Web & mobile",
    "insta-go-sdk": "Developer tools",
    "ai-tutoring": "AI & agents",
    "reinforcement-learning": "AI & agents",
    "kinetic-darkroom": "Web & mobile"
  };
  const CATEGORY_COLORS = {
    "AI & agents": "#6366f1", "Robotics": "#2563eb",
    "Systems & IoT": "#0891b2", "Developer tools": "#8b5cf6",
    "Web & mobile": "#d97706", "Research": "#64748b", "Other": "#475569"
  };

  const state = {
    data: null, scope: "featured", category: "All",
    projectSearch: "", projectSort: "featured",
    prState: "merged", prScope: "upstream", prSearch: "", prLimit: 8
  };
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const create = (tag, cls, value) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  };
  const urlSafe = value => {
    try {
      const u = new URL(value);
      return ["http:", "https:"].includes(u.protocol) ? u.href : null;
    } catch (_) { return null; }
  };
  const link = (label, uri, cls) => {
    const a = create("a", cls, label);
    const good = urlSafe(uri);
    if (good) {
      a.href = good;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    } else a.removeAttribute("href");
    return a;
  };
  const fmt = value => Number(value || 0).toLocaleString("en-US");
  const languages = repos => {
    const counts = new Map();
    repos.filter(r => !r.fork && r.language && r.language !== "Unspecified")
      .forEach(r => counts.set(r.language, (counts.get(r.language) || 0) + 1));
    return [...counts].sort((a, b) => b[1] - a[1]);
  };
  const categoryOf = repo => {
    if (CATEGORIES[repo.name]) return CATEGORIES[repo.name];
    const text = [repo.name, repo.description || "", ...(repo.topics || [])].join(" ").toLowerCase();
    if (/robot|gazebo|ros 2|navigation/.test(text)) return "Robotics";
    if (/agent|ai |llm|tutor|machine learning|neural|recognition/.test(text)) return "AI & agents";
    if (/developer|tool|sdk|cli|visualiz|terminal/.test(text)) return "Developer tools";
    if (/iot|sensor|edge|telemetry/.test(text)) return "Systems & IoT";
    if (/app|web|frontend|game|portfolio/.test(text)) return "Web & mobile";
    return "Other";
  };
  const descOf = repo => repo.tagline || repo.description || "Explore the source code and development history.";
  const accentOf = repo => CATEGORY_COLORS[categoryOf(repo)] || CATEGORY_COLORS.Other;
  const iconOf = repo => {
    const c = categoryOf(repo);
    return { "AI & agents": "AI", "Robotics": "R", "Systems & IoT": "IoT",
      "Developer tools": "DX", "Web & mobile": "UI", "Research": "ML", "Other": "</>" }[c] || "</>";
  };

  function configureTheme() {
    let preferred = null;
    try { preferred = localStorage.getItem("portfolio-theme"); } catch (_) {}
    const systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const start = preferred === "light" || preferred === "dark" ? preferred : (systemDark ? "dark" : "light");
    document.documentElement.dataset.theme = start;
    const button = $("#themeToggle");
    const updateLabel = () => {
      const dark = document.documentElement.dataset.theme === "dark";
      button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      button.title = dark ? "Light theme" : "Dark theme";
      button.textContent = dark ? "☀" : "☾";
    };
    button.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("portfolio-theme", next); } catch (_) {}
      updateLabel();
    });
    updateLabel();
  }

  function updateCounts() {
    const data = state.data;
    if (!data) return;
    const upstream = mode => data.prs[mode].filter(p => p.upstream).length;
    $("#statRepos").textContent = fmt(data.stats.public_repos);
    $("#statMerged").textContent = fmt(upstream("merged"));
    $("#statOpen").textContent = fmt(upstream("open"));
    $("#statContributions").textContent = data.stats.annual_contributions === null
      ? "—" : fmt(data.stats.annual_contributions);
    const updated = new Date(data.generated_at);
    $("#updated").textContent = isNaN(updated.getTime())
      ? "Latest available GitHub snapshot"
      : "GitHub data refreshed " + updated.toLocaleDateString("en-US", {
          year: "numeric", month: "short", day: "numeric", timeZone: "UTC"
        }) + " (UTC)";
  }

  function projectList() {
    let repos = state.data.repos.filter(r => {
      if (state.scope === "forks") return r.fork;
      if (r.fork || r.archived || r.name === USER) return false;
      if (state.scope === "featured") return FEATURED_ORDER.includes(r.name);
      return true;
    });
    if (state.category !== "All") repos = repos.filter(r => categoryOf(r) === state.category);
    if (state.projectSearch) {
      const q = state.projectSearch.toLowerCase();
      repos = repos.filter(r => [r.name, descOf(r), r.language, ...(r.topics || [])]
        .join(" ").toLowerCase().includes(q));
    }
    if (state.projectSort === "stars") {
      repos.sort((a, b) => b.stars - a.stars || a.name.localeCompare(b.name));
    } else if (state.projectSort === "name") {
      repos.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      repos.sort((a, b) => {
        const ai = FEATURED_ORDER.indexOf(a.name), bi = FEATURED_ORDER.indexOf(b.name);
        if (ai !== -1 && bi !== -1) return ai - bi;
        if (ai !== -1) return -1;
        if (bi !== -1) return 1;
        return a.name.localeCompare(b.name);
      });
    }
    return repos;
  }

  function openProject(repo) {
    const dialog = $("#projectDialog");
    $("#modalTitle").textContent = repo.name;
    $("#modalCategory").textContent = categoryOf(repo);
    $("#modalDescription").textContent = repo.description || descOf(repo);
    $("#modalLanguage").textContent = repo.language || "Not specified";
    $("#modalStars").textContent = fmt(repo.stars);
    $("#modalTopics").replaceChildren();
    const tags = (repo.topics || []).slice(0, 12);
    if (!tags.length) tags.push(repo.language || "Software");
    tags.forEach(t => $("#modalTopics").appendChild(create("span", "tag", t)));
    const actions = $("#modalLinks");
    actions.replaceChildren();
    actions.appendChild(link("View source ↗", repo.url, "primary"));
    if (repo.live) actions.appendChild(link("Open live demo ↗", repo.live, "secondary"));
    if (typeof dialog.showModal === "function") dialog.showModal();
  }

  function projectCard(repo) {
    const card = create("article", "project-card");
    const graphic = create("div", "project-graphic");
    graphic.style.setProperty("--graphic-color", accentOf(repo));
    graphic.appendChild(create("div", "graphic-icon", iconOf(repo)));
    graphic.appendChild(create("div", "category-label", categoryOf(repo)));
    card.appendChild(graphic);

    const body = create("div", "project-body");
    body.appendChild(create("h3", "", repo.name));
    body.appendChild(create("p", "", descOf(repo)));
    const tags = create("div", "tag-row");
    [repo.language, ...(repo.topics || []).slice(0, 2)].filter(Boolean)
      .forEach(t => tags.appendChild(create("span", "tag", t)));
    body.appendChild(tags);
    const footer = create("div", "card-footer");
    footer.appendChild(create("span", "", "★ " + fmt(repo.stars) + " stars"));
    const buttons = create("div", "card-links");
    const details = create("button", "text-button", "Details");
    details.type = "button";
    details.setAttribute("aria-label", "View details for " + repo.name);
    details.addEventListener("click", () => openProject(repo));
    buttons.appendChild(details);
    buttons.appendChild(link("Code ↗", repo.url));
    if (repo.live) buttons.appendChild(link("Demo ↗", repo.live));
    footer.appendChild(buttons);
    body.appendChild(footer);
    card.appendChild(body);
    return card;
  }

  function renderProjects() {
    if (!state.data) return;
    const list = projectList();
    const root = $("#projectsGrid");
    root.replaceChildren();
    $("#projectsCount").textContent = list.length + " project" + (list.length === 1 ? "" : "s") + " shown";
    if (!list.length) {
      root.appendChild(create("p", "empty-state", "No repositories match those filters. Try a different search or category."));
    } else list.forEach(repo => root.appendChild(projectCard(repo)));
    $$("[data-repo-scope]").forEach(button =>
      button.setAttribute("aria-pressed", String(button.dataset.repoScope === state.scope)));
  }

  function filteredPRs() {
    let prs = state.data.prs[state.prState].filter(p =>
      state.prScope === "all" || (state.prScope === "upstream" ? p.upstream : !p.upstream));
    if (state.prSearch) {
      const q = state.prSearch.toLowerCase();
      prs = prs.filter(p => [p.repo, p.title, String(p.number)].join(" ").toLowerCase().includes(q));
    }
    return prs;
  }

  function renderPRs() {
    if (!state.data) return;
    const rows = filteredPRs();
    const root = $("#prList");
    root.replaceChildren();
    const visible = rows.slice(0, state.prLimit);
    if (!rows.length) root.appendChild(create("div", "empty-state", "No pull requests match these filters."));
    visible.forEach(pr => {
      const row = create("article", "pr-row");
      const left = create("div", "");
      left.appendChild(create("span", "pr-repo", pr.repo + " · #" + pr.number));
      const name = create("strong", "");
      name.appendChild(link(pr.title, pr.url));
      left.appendChild(name);
      row.appendChild(left);
      row.appendChild(create("span", "pr-status", state.prState === "merged" ? "Merged" : "Open"));
      root.appendChild(row);
    });
    $("#prCount").textContent = rows.length + " pull request" + (rows.length === 1 ? "" : "s");
    const more = $("#loadMore");
    more.hidden = state.prLimit >= rows.length;
    $$("[data-pr-state]").forEach(btn => btn.setAttribute(
      "aria-pressed", String(btn.dataset.prState === state.prState)));
  }

  function renderLanguages() {
    if (!state.data) return;
    const bars = $("#languageBars");
    bars.replaceChildren();
    const data = languages(state.data.repos).slice(0, 7);
    const max = Math.max(1, ...data.map(x => x[1]));
    for (const [language, count] of data) {
      const line = create("div", "bar");
      line.appendChild(create("label", "", language));
      const track = create("div", "bar-track");
      const fill = create("span", "");
      fill.style.width = (100 * count / max) + "%";
      track.appendChild(fill);
      line.appendChild(track);
      line.appendChild(create("output", "", count));
      bars.appendChild(line);
    }
    if (!data.length) bars.appendChild(create("p", "", "Language breakdown unavailable."));
  }

  function bindFilters() {
    $$("[data-repo-scope]").forEach(button =>
      button.addEventListener("click", () => {
        state.scope = button.dataset.repoScope;
        state.category = "All";
        $("#projectCategory").value = "All";
        renderProjects();
      }));
    $("#projectSearch").addEventListener("input", e => {
      state.projectSearch = e.target.value.trim();
      renderProjects();
    });
    $("#projectCategory").addEventListener("change", e => {
      state.category = e.target.value;
      renderProjects();
    });
    $("#projectSort").addEventListener("change", e => {
      state.projectSort = e.target.value;
      renderProjects();
    });
    $$("[data-pr-state]").forEach(button => button.addEventListener("click", () => {
      state.prState = button.dataset.prState;
      state.prLimit = 8;
      renderPRs();
    }));
    $("#prScope").addEventListener("change", e => {
      state.prScope = e.target.value;
      state.prLimit = 8;
      renderPRs();
    });
    $("#prSearch").addEventListener("input", e => {
      state.prSearch = e.target.value.trim();
      state.prLimit = 8;
      renderPRs();
    });
    $("#loadMore").addEventListener("click", () => {
      state.prLimit += 8;
      renderPRs();
    });
    $("#closeModal").addEventListener("click", () => $("#projectDialog").close());
    $("#projectDialog").addEventListener("click", e => {
      if (e.target === $("#projectDialog")) e.target.close();
    });
  }

  async function loadData() {
    try {
      const response = await fetch("./data/profile.json", { cache: "no-store" });
      if (!response.ok) throw new Error("GitHub data HTTP " + response.status);
      const data = await response.json();
      if (!Array.isArray(data.repos) || !data.prs || !Array.isArray(data.prs.merged) ||
          !Array.isArray(data.prs.open) || !data.stats)
        throw new Error("Unrecognized GitHub data snapshot");
      state.data = data;
      updateCounts();
      renderProjects();
      renderPRs();
      renderLanguages();
    } catch (error) {
      $("#projectsGrid").replaceChildren(create("div", "empty-state",
        "Project data could not be loaded. Please view the repositories directly on GitHub."));
      $("#prList").replaceChildren(create("div", "empty-state",
        "Pull request data is temporarily unavailable. See GitHub for the latest status."));
      $("#updated").textContent = "Unable to load GitHub data snapshot";
      console.warn("Portfolio data unavailable", error);
    }
  }

  configureTheme();
  bindFilters();
  loadData();
})();
