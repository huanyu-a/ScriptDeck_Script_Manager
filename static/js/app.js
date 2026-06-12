const storageKeys = {
  theme: "psm.theme",
  favorites: "psm.favorites",
  recent: "psm.recent",
  viewMode: "psm.viewMode",
};

const palette = ["#6d5dfc", "#0ea5e9", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#f97316", "#14b8a6"];

const appState = {
  items: [],
  scripts: [],
  scanRoot: "-",
  filter: "",
  activeMode: "all",
  activePath: "",
  selectedId: "",
  viewMode: localStorage.getItem(storageKeys.viewMode) || "grid",
  favorites: new Set(readJson(storageKeys.favorites, [])),
  recent: readJson(storageKeys.recent, []),
  treeOpen: new Set(),
  excludeBats: [],
  excludeScripts: [],
};

const elements = {};

document.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindEvents();
  applyInitialTheme();
  setViewMode(appState.viewMode);
  loadExcludeBats();
  loadData();
});

function bindElements() {
  elements.searchInput = document.getElementById("searchInput");
  elements.refreshBtn = document.getElementById("refreshBtn");
  elements.settingsBtn = document.getElementById("settingsBtn");
  elements.themeBtn = document.getElementById("themeBtn");
  elements.closeSettingsBtn = document.getElementById("closeSettingsBtn");
  elements.setRootBtn = document.getElementById("setRootBtn");
  elements.rootInput = document.getElementById("rootInput");
  elements.settingsModal = document.getElementById("settingsModal");

  elements.sidebarTree = document.getElementById("sidebarTree");
  elements.main = document.getElementById("main");
  elements.detailPanel = document.getElementById("detailPanel");
  elements.toast = document.getElementById("toast");
  elements.viewTitle = document.getElementById("viewTitle");
  elements.viewSubtitle = document.getElementById("viewSubtitle");
  elements.gridViewBtn = document.getElementById("gridViewBtn");
  elements.listViewBtn = document.getElementById("listViewBtn");
  elements.metricDirs = document.getElementById("metricDirs");
  elements.metricScripts = document.getElementById("metricScripts");
  elements.metricReadmes = document.getElementById("metricReadmes");
  elements.countAll = document.getElementById("countAll");
  elements.countFavorites = document.getElementById("countFavorites");
  elements.countRecent = document.getElementById("countRecent");

  // Exclude-bats UI
  elements.excludeBatsList = document.getElementById("excludeBatsList");
  elements.excludeBatInput = document.getElementById("excludeBatInput");
  elements.addExcludeBatBtn = document.getElementById("addExcludeBatBtn");

  // Create detail overlay element
  elements.detailOverlay = document.createElement("div");
  elements.detailOverlay.className = "detail-overlay";
  elements.detailOverlay.id = "detailOverlay";
  document.body.appendChild(elements.detailOverlay);
}

function bindEvents() {
  elements.searchInput.addEventListener("input", (event) => {
    appState.filter = event.target.value.trim().toLowerCase();
    render();
  });

  elements.refreshBtn.addEventListener("click", () => {
    toast("正在刷新目录…", "ok");
    loadData();
  });

  elements.settingsBtn.addEventListener("click", openSettings);
  elements.closeSettingsBtn.addEventListener("click", closeSettings);
  elements.setRootBtn.addEventListener("click", setScanRoot);
  elements.themeBtn.addEventListener("click", toggleTheme);
  elements.gridViewBtn.addEventListener("click", () => setViewMode("grid"));
  elements.listViewBtn.addEventListener("click", () => setViewMode("list"));

  elements.rootInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") setScanRoot();
  });

  elements.addExcludeBatBtn.addEventListener("click", addExcludeBatPattern);
  elements.excludeBatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") addExcludeBatPattern();
  });

  elements.excludeBatsList.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-exclude-bat-remove]");
    if (btn) removeExcludeBatPattern(btn.dataset.excludeBatRemove);
  });

  elements.settingsModal.addEventListener("click", (event) => {
    if (event.target === elements.settingsModal) closeSettings();
  });

  document.querySelector(".nav-tabs").addEventListener("click", (event) => {
    const navTab = event.target.closest(".nav-tab");
    if (!navTab) return;
    appState.activeMode = navTab.dataset.mode;
    appState.activePath = "";
    render();
  });

  elements.sidebarTree.addEventListener("click", (event) => {
    const toggleButton = event.target.closest("[data-tree-toggle]");
    const treeRow = event.target.closest("[data-tree-path]");
    if (toggleButton) {
      const treePath = toggleButton.dataset.treeToggle;
      toggleTree(treePath);
      event.stopPropagation();
      return;
    }
    if (!treeRow) return;
    appState.activeMode = "folder";
    appState.activePath = treeRow.dataset.treePath;
    render();
  });

  elements.main.addEventListener("click", (event) => {
    const favoriteButton = event.target.closest("[data-favorite-id]");
    if (favoriteButton) {
      toggleFavorite(favoriteButton.dataset.favoriteId);
      event.stopPropagation();
      return;
    }

    const runButton = event.target.closest("[data-run-id]");
    if (runButton) {
      runScriptById(runButton.dataset.runId);
      event.stopPropagation();
      return;
    }

    const scriptCard = event.target.closest("[data-script-id]");
    if (!scriptCard) return;
    selectScript(scriptCard.dataset.scriptId);
  });

  elements.main.addEventListener("dblclick", (event) => {
    const scriptCard = event.target.closest("[data-script-id]");
    if (scriptCard) runScriptById(scriptCard.dataset.scriptId);
  });

  // Right-click context menu on script cards
  elements.main.addEventListener("contextmenu", (event) => {
    const scriptCard = event.target.closest("[data-script-id]");
    if (!scriptCard) return;
    event.preventDefault();
    const scriptId = scriptCard.dataset.scriptId;
    const script = appState.scripts.find((s) => s.id === scriptId);
    if (script) showContextMenu(event.clientX, event.clientY, script);
  });

  // Close context menu on click elsewhere
  document.addEventListener("click", closeContextMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeContextMenu();
  });

  elements.detailPanel.addEventListener("click", (event) => {
    const detailRun = event.target.closest("[data-detail-run]");
    if (detailRun) {
      runScriptById(detailRun.dataset.detailRun);
      return;
    }

    const openFolderButton = event.target.closest("[data-open-folder]");
    if (openFolderButton) {
      openFolder(openFolderButton.dataset.openFolder);
      return;
    }

    const detailFavorite = event.target.closest("[data-detail-favorite]");
    if (detailFavorite) {
      toggleFavorite(detailFavorite.dataset.detailFavorite);
      return;
    }

    const expandBtn = event.target.closest("[data-expand-detail]");
    if (expandBtn) {
      openDetailOverlay();
      return;
    }

    const closeDetail = event.target.closest("[data-close-detail]");
    if (closeDetail) {
      appState.selectedId = "";
      renderDetail();
    }
  });

  // Overlay click handlers (delegated)
  elements.detailOverlay.addEventListener("click", (event) => {
    const closeBtn = event.target.closest(".detail-overlay-close");
    if (closeBtn) {
      closeDetailOverlay();
      return;
    }
    const detailRun = event.target.closest("[data-detail-run]");
    if (detailRun) {
      runScriptById(detailRun.dataset.detailRun);
      return;
    }
    const openFolderButton = event.target.closest("[data-open-folder]");
    if (openFolderButton) {
      openFolder(openFolderButton.dataset.openFolder);
      return;
    }
    const detailFavorite = event.target.closest("[data-detail-favorite]");
    if (detailFavorite) {
      toggleFavorite(detailFavorite.dataset.detailFavorite);
      renderDetailOverlayContent();
      return;
    }
    // Click backdrop to close
    if (event.target === elements.detailOverlay) {
      closeDetailOverlay();
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      elements.searchInput.focus();
    }
    if (event.key === "Escape") {
      closeSettings();
      closeDetailOverlay();
      appState.selectedId = "";
      renderDetail();
    }
    if (event.key === "Enter" && document.activeElement === elements.searchInput) {
      const firstScript = getVisibleScripts()[0];
      if (firstScript) selectScript(firstScript.id);
    }
  });
}

async function loadData() {
  renderLoading();
  try {
    const response = await fetch("/api/scan");
    const payload = await response.json();
    appState.items = payload.items || [];
    appState.scanRoot = payload.scan_root || "-";
    appState.excludeScripts = payload.exclude_scripts || [];
    appState.scripts = flattenScripts(appState.items);
    appState.recent = appState.recent.filter((scriptId) => appState.scripts.some((script) => script.id === scriptId));
    if (appState.selectedId && !appState.scripts.some((script) => script.id === appState.selectedId)) {
      appState.selectedId = "";
    }
    persistRecent();
    render();
    toast("扫描完成", "ok");
  } catch (error) {
    elements.main.innerHTML = `<div class="error-state">加载失败：${escapeHtml(error.message)}</div>`;
    toast(`加载失败：${error.message}`, "err");
  }
}

async function setScanRoot() {
  const scanRoot = elements.rootInput.value.trim();
  if (!scanRoot) {
    toast("扫描目录不能为空", "err");
    return;
  }

  elements.setRootBtn.disabled = true;
  elements.setRootBtn.textContent = "应用中…";
  try {
    const response = await fetch("/api/set-root", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scan_root: scanRoot }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      toast(payload.msg || "设置失败", "err");
      return;
    }

    appState.items = payload.items || [];
    appState.scanRoot = payload.scan_root || scanRoot;
    appState.scripts = flattenScripts(appState.items);
    appState.activeMode = "all";
    appState.activePath = "";
    appState.selectedId = "";
    appState.treeOpen = new Set();
    closeSettings();
    render();
    toast("扫描目录已更新", "ok");
  } catch (error) {
    toast(`请求失败：${error.message}`, "err");
  } finally {
    elements.setRootBtn.disabled = false;
    elements.setRootBtn.textContent = "应用";
  }
}

// ── 排除规则管理 ──

async function loadExcludeBats() {
  try {
    const res = await fetch("/api/exclude-bats");
    const data = await res.json();
    appState.excludeBats = data.exclude_bats || [];
    renderExcludeBatsList();
  } catch { appState.excludeBats = []; }
}

function renderExcludeBatsList() {
  if (!elements.excludeBatsList) return;
  elements.excludeBatsList.innerHTML = appState.excludeBats.map((pat) => `
    <span class="exclude-bat-chip">
      ${escapeHtml(pat)}
      <button type="button" data-exclude-bat-remove="${escapeAttr(pat)}" title="移除">×</button>
    </span>
  `).join("");
}

async function addExcludeBatPattern() {
  const input = elements.excludeBatInput;
  const pattern = input.value.trim();
  if (!pattern) return;
  if (appState.excludeBats.includes(pattern)) {
    toast("该规则已存在", "err");
    return;
  }
  input.value = "";
  const updated = [...appState.excludeBats, pattern];
  await saveExcludeBats(updated);
}

async function removeExcludeBatPattern(pattern) {
  const updated = appState.excludeBats.filter((p) => p !== pattern);
  await saveExcludeBats(updated);
}

async function saveExcludeBats(patterns) {
  try {
    const res = await fetch("/api/exclude-bats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exclude_bats: patterns }),
    });
    const data = await res.json();
    if (data.ok) {
      appState.excludeBats = data.exclude_bats || [];
      appState.items = data.items || [];
      appState.scripts = flattenScripts(appState.items);
      renderExcludeBatsList();
      render();
      toast("排除规则已更新", "ok");
    } else {
      toast(data.msg || "保存失败", "err");
    }
  } catch (error) {
    toast(`保存失败：${error.message}`, "err");
  }
}

// ── 右键菜单 ──

function showContextMenu(x, y, script) {
  closeContextMenu();
  const isExcluded = appState.excludeScripts.some(
    (p) => p.toLowerCase().replace(/\\/g, "/") === script.path.toLowerCase().replace(/\\/g, "/")
  );

  const menu = document.createElement("div");
  menu.className = "ctx-menu";
  menu.id = "ctxMenu";
  menu.innerHTML = `
    <button class="ctx-menu-item" data-action="run">▶ 运行脚本</button>
    <button class="ctx-menu-item" data-action="favorite">${appState.favorites.has(script.id) ? "★ 取消收藏" : "☆ 收藏"}</button>
    <button class="ctx-menu-item" data-action="open-folder">📂 打开目录</button>
    <button class="ctx-menu-item ${isExcluded ? "" : "danger"}" data-action="exclude">
      ${isExcluded ? "✓ 取消排除" : "✕ 排除此脚本"}
    </button>
  `;

  // Position the menu, ensuring it stays within viewport
  document.body.appendChild(menu);
  const rect = menu.getBoundingClientRect();
  const left = x + rect.width > window.innerWidth ? x - rect.width : x;
  const top = y + rect.height > window.innerHeight ? y - rect.height : y;
  menu.style.left = `${Math.max(4, left)}px`;
  menu.style.top = `${Math.max(4, top)}px`;

  menu.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    closeContextMenu();
    if (action === "run") runScriptById(script.id);
    else if (action === "favorite") toggleFavorite(script.id);
    else if (action === "open-folder") openFolder(script.folderPath);
    else if (action === "exclude") toggleExcludeScript(script);
  });
}

function closeContextMenu() {
  const existing = document.getElementById("ctxMenu");
  if (existing) existing.remove();
}

async function toggleExcludeScript(script) {
  const isExcluded = appState.excludeScripts.some(
    (p) => p.toLowerCase().replace(/\\/g, "/") === script.path.toLowerCase().replace(/\\/g, "/")
  );
  const action = isExcluded ? "remove" : "add";

  try {
    const res = await fetch("/api/exclude-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: script.path, action }),
    });
    const data = await res.json();
    if (data.ok) {
      appState.excludeScripts = data.exclude_scripts || [];
      appState.items = data.items || [];
      appState.scripts = flattenScripts(appState.items);
      if (!appState.scripts.some((s) => s.id === appState.selectedId)) {
        appState.selectedId = "";
      }
      render();
      toast(isExcluded ? "已取消排除" : "已排除该脚本", "ok");
    }
  } catch (error) {
    toast(`操作失败：${error.message}`, "err");
  }
}

async function runScriptById(scriptId) {
  const script = appState.scripts.find((candidate) => candidate.id === scriptId);
  if (!script) return;

  try {
    const response = await fetch("/api/run-bat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: script.path }),
    });
    const payload = await response.json();
    if (!payload.ok) {
      toast(payload.msg || "启动失败", "err");
      return;
    }

    rememberRecent(script.id);
    selectScript(script.id, false);
    render();
    toast(`已启动：${script.name}`, "ok");
  } catch (error) {
    toast(`启动失败：${error.message}`, "err");
  }
}

async function openFolder(folderPath) {
  try {
    await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folderPath }),
    });
  } catch (error) {
    toast(`打开目录失败：${error.message}`, "err");
  }
}

function flattenScripts(items) {
  return items.flatMap((item) => {
    const readmeText = item.readme?.content || "";
    const readmeSummary = summarizeReadme(readmeText);
    const readmeTitle = extractReadmeTitle(readmeText);
    return (item.bats || []).map((batFile) => ({
      id: batFile.path,
      name: batFile.name,
      title: readmeTitle || batFile.name.replace(/\.bat$/i, ""),
      path: batFile.path,
      folder: item.folder,
      folderName: item.folder_name,
      parent: item.parent,
      folderPath: getFolderPath(batFile.path),
      readmeName: item.readme?.name || "",
      readmeText,
      readmeSummary,
      color: colorFor(`${item.folder}/${batFile.name}`),
      icon: iconFor(`${item.folder} ${batFile.name} ${readmeText}`),
    }));
  });
}

function extractReadmeTitle(readmeText) {
  if (!readmeText) return "";
  const firstLine = readmeText.split(/\r?\n/)[0].trim();
  return firstLine.replace(/^#+\s*/, "").trim();
}

function summarizeReadme(readmeText) {
  if (!readmeText) return "";
  const cleanLines = readmeText
    .split(/\r?\n/)
    .map((line) => line.replace(/^#+\s*/, "").replace(/[*_`>#-]/g, "").trim())
    .filter(Boolean);
  const summary = cleanLines.slice(0, 3).join(" · ");
  return summary.length > 140 ? `${summary.slice(0, 140)}…` : summary;
}

function getVisibleScripts() {
  let scripts = [...appState.scripts];

  if (appState.activeMode === "favorites") {
    scripts = scripts.filter((script) => appState.favorites.has(script.id));
  } else if (appState.activeMode === "recent") {
    scripts = appState.recent
      .map((scriptId) => appState.scripts.find((script) => script.id === scriptId))
      .filter(Boolean);
  } else if (appState.activeMode === "folder" && appState.activePath) {
    scripts = scripts.filter((script) => script.folder === appState.activePath || script.folder.startsWith(`${appState.activePath}/`));
  }

  if (!appState.filter) return scripts;
  return scripts.filter((script) => {
    const searchable = `${script.title} ${script.name} ${script.folder} ${script.path} ${script.readmeSummary}`.toLowerCase();
    return searchable.includes(appState.filter);
  });
}

function render() {
  renderShell();
  renderSidebar();
  renderBoard();
  renderDetail();
  if (typeof lucide !== "undefined") lucide.createIcons();
}

function renderShell() {
  const readmeCount = appState.items.filter((item) => item.readme).length;
  elements.metricDirs.textContent = appState.items.length;
  elements.metricScripts.textContent = appState.scripts.length;
  elements.metricReadmes.textContent = readmeCount;
  elements.countAll.textContent = appState.scripts.length;
  elements.countFavorites.textContent = [...appState.favorites].filter((scriptId) => appState.scripts.some((script) => script.id === scriptId)).length;
  elements.countRecent.textContent = appState.recent.length;

  document.querySelectorAll(".nav-tab").forEach((navTab) => {
    navTab.classList.toggle("active", appState.activeMode === navTab.dataset.mode);
  });
}

function renderSidebar() {
  const tree = buildTree();
  elements.sidebarTree.innerHTML = renderTree(tree, "", 0);
}

function renderBoard() {
  const visibleScripts = getVisibleScripts();
  const title = getViewTitle();
  elements.viewTitle.textContent = title;
  elements.viewSubtitle.textContent = `${visibleScripts.length} 个可见脚本 · ${appState.filter ? "已应用搜索过滤" : "双击卡片可直接运行"}`;
  elements.main.classList.toggle("list-view", appState.viewMode === "list");

  if (!visibleScripts.length) {
    elements.main.innerHTML = `<div class="empty-state"><strong>没有找到脚本</strong><span>换个关键词，或调整左侧筛选试试。</span></div>`;
    return;
  }

  const groupedScripts = groupScripts(visibleScripts);
  elements.main.innerHTML = groupedScripts.map(([groupName, scripts]) => `
    <div class="script-group">
      <h3 class="group-title">${escapeHtml(groupName)} <span>${scripts.length} 个</span></h3>
      <div class="script-grid">
        ${scripts.map((script) => renderScriptCard(script)).join("")}
      </div>
    </div>
  `).join("");
}

function renderScriptCard(script) {
  const isFavorite = appState.favorites.has(script.id);
  const isActive = appState.selectedId === script.id;
  return `
    <article class="script-card ${isActive ? "active" : ""}" data-script-id="${escapeAttr(script.id)}" style="--card-color:${script.color}">
      <div class="script-card-head">
        <div class="script-icon"><i data-lucide="${script.icon}"></i></div>
        <div class="script-title">
          <h3 title="${escapeAttr(script.title)}">${escapeHtml(script.title)}</h3>
          <p title="${escapeAttr(script.folder)}">${escapeHtml(script.folder)}</p>
        </div>
      </div>
      <p class="script-desc">${escapeHtml(script.readmeSummary || "暂无 README 摘要。选中后可查看路径与快捷操作。")}</p>
      <div class="script-actions">
        <div class="badge-row">
          <span class="badge">BAT</span>
          ${script.readmeText ? `<span class="badge readme">README</span>` : ""}
        </div>
        <div class="script-actions">
          <button class="favorite-button ${isFavorite ? "active" : ""}" type="button" data-favorite-id="${escapeAttr(script.id)}" title="收藏">★</button>
          <button class="run-button" type="button" data-run-id="${escapeAttr(script.id)}">运行</button>
        </div>
      </div>
    </article>
  `;
}

function renderDetail() {
  const script = appState.scripts.find((candidate) => candidate.id === appState.selectedId);
  elements.detailPanel.classList.toggle("has-selection", Boolean(script));

  let container = elements.detailPanel.querySelector(".detail-content");
  if (!container) {
    container = document.createElement("div");
    container.className = "detail-content";
    elements.detailPanel.appendChild(container);
  }

  if (!script) {
    container.innerHTML = `
      <div class="detail-empty">
        <div class="empty-orb">✦</div>
        <h3>选择一个脚本</h3>
        <p>这里会展示路径、README 摘要和快捷操作。</p>
      </div>
    `;
    return;
  }

  const siblingScripts = appState.scripts.filter((candidate) => candidate.folder === script.folder && candidate.id !== script.id);
  const isFavorite = appState.favorites.has(script.id);
  container.innerHTML = `
    <div class="detail-card">
      <section class="detail-hero" style="--card-color:${script.color}">
        <div class="detail-top-actions">
          <button class="expand-button" type="button" data-expand-detail title="全屏查看">⛶</button>
          <button class="icon-button" type="button" data-close-detail aria-label="关闭详情">×</button>
        </div>
        <div class="script-icon"><i data-lucide="${script.icon}"></i></div>
        <div>
          <span class="eyebrow">${escapeHtml(script.folderName || "脚本")}</span>
          <h3>${escapeHtml(script.title)}</h3>
        </div>
        <div class="detail-path">${escapeHtml(script.path)}</div>
        <div class="detail-actions">
          <button class="run-button" type="button" data-detail-run="${escapeAttr(script.id)}">运行脚本</button>
          <button class="subtle-button" type="button" data-open-folder="${escapeAttr(script.folderPath)}">打开目录</button>
          <button class="subtle-button" type="button" data-detail-favorite="${escapeAttr(script.id)}">${isFavorite ? "取消收藏" : "收藏"}</button>
        </div>
      </section>

      <section class="detail-section">
        <h4>README</h4>
        ${script.readmeText ? `<div class="markdown-body">${renderMarkdown(script.readmeText)}</div>` : '<p class="detail-empty-text">当前目录没有 README 文件。</p>'}
      </section>

      <section class="detail-section">
        <h4>同目录脚本</h4>
        <div class="detail-list">
          ${siblingScripts.length ? siblingScripts.map((candidate) => `
            <button type="button" data-detail-run="${escapeAttr(candidate.id)}">${escapeHtml(candidate.name)}</button>
          `).join("") : "<span>没有其它 bat 脚本。</span>"}
        </div>
      </section>
    </div>
  `;
  if (typeof lucide !== "undefined") lucide.createIcons();
}

function renderLoading() {
  elements.main.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <span>正在扫描目录…</span>
    </div>
  `;
}

function openDetailOverlay() {
  renderDetailOverlayContent();
  elements.detailOverlay.classList.add("show");
  document.body.style.overflow = "hidden";
}

function closeDetailOverlay() {
  elements.detailOverlay.classList.remove("show");
  document.body.style.overflow = "";
}

function renderDetailOverlayContent() {
  const script = appState.scripts.find((candidate) => candidate.id === appState.selectedId);
  if (!script) return;
  const siblingScripts = appState.scripts.filter((candidate) => candidate.folder === script.folder && candidate.id !== script.id);
  const isFavorite = appState.favorites.has(script.id);
  elements.detailOverlay.innerHTML = `
    <div class="detail-overlay-content">
      <button class="detail-overlay-close" type="button" title="关闭">×</button>
      <div class="detail-card">
        <section class="detail-hero" style="--card-color:${script.color}">
          <div class="script-icon"><i data-lucide="${script.icon}"></i></div>
          <div>
            <span class="eyebrow">${escapeHtml(script.folderName || "脚本")}</span>
            <h3>${escapeHtml(script.title)}</h3>
          </div>
          <div class="detail-path">${escapeHtml(script.path)}</div>
          <div class="detail-actions">
            <button class="run-button" type="button" data-detail-run="${escapeAttr(script.id)}">运行脚本</button>
            <button class="subtle-button" type="button" data-open-folder="${escapeAttr(script.folderPath)}">打开目录</button>
            <button class="subtle-button" type="button" data-detail-favorite="${escapeAttr(script.id)}">${isFavorite ? "取消收藏" : "收藏"}</button>
          </div>
        </section>

        <section class="detail-section">
          <h4>README</h4>
          ${script.readmeText ? `<div class="markdown-body">${renderMarkdown(script.readmeText)}</div>` : '<p class="detail-empty-text">当前目录没有 README 文件。</p>'}
        </section>

        <section class="detail-section">
          <h4>同目录脚本</h4>
          <div class="detail-list">
            ${siblingScripts.length ? siblingScripts.map((candidate) => `
              <button type="button" data-detail-run="${escapeAttr(candidate.id)}">${escapeHtml(candidate.name)}</button>
            `).join("") : "<span>没有其它 bat 脚本。</span>"}
          </div>
        </section>
      </div>
    </div>
  `;
  if (typeof lucide !== "undefined") lucide.createIcons();
}

function buildTree() {
  const root = { children: {}, count: 0 };
  appState.items.forEach((item) => {
    const parts = item.folder.split("/");
    let currentNode = root;
    currentNode.count += item.bats?.length || 0;
    parts.forEach((part) => {
      if (!currentNode.children[part]) {
        currentNode.children[part] = { name: part, children: {}, count: 0 };
      }
      currentNode = currentNode.children[part];
      currentNode.count += item.bats?.length || 0;
    });
  });
  return root;
}

function renderTree(node, parentPath, depth) {
  return Object.keys(node.children)
    .sort((left, right) => left.localeCompare(right, "zh-CN"))
    .map((name) => {
      const child = node.children[name];
      const fullPath = parentPath ? `${parentPath}/${name}` : name;
      const hasChildren = Object.keys(child.children).length > 0;
      const isOpen = appState.treeOpen.has(fullPath);
      const isActive = appState.activeMode === "folder" && appState.activePath === fullPath;
      const childrenHtml = hasChildren && isOpen ? renderTree(child, fullPath, depth + 1) : "";
      return `
        <div>
          <button class="tree-row ${isActive ? "active" : ""}" type="button" data-tree-path="${escapeAttr(fullPath)}" style="--indent:${8 + depth * 16}px">
            <span class="tree-toggle ${isOpen ? "open" : ""}" ${hasChildren ? `data-tree-toggle="${escapeAttr(fullPath)}"` : ""}>${hasChildren ? "▶" : "·"}</span>
            <span class="tree-name">${escapeHtml(name)}</span>
            <span class="tree-count">${child.count}</span>
          </button>
          ${childrenHtml}
        </div>
      `;
    })
    .join("");
}

function toggleTree(treePath) {
  if (appState.treeOpen.has(treePath)) {
    appState.treeOpen.delete(treePath);
  } else {
    appState.treeOpen.add(treePath);
  }
  renderSidebar();
}

function groupScripts(scripts) {
  const groups = new Map();
  scripts.forEach((script) => {
    const groupName = appState.activeMode === "folder" && appState.activePath
      ? script.folder.replace(`${appState.activePath}/`, "") || script.folder
      : script.folder;
    if (!groups.has(groupName)) groups.set(groupName, []);
    groups.get(groupName).push(script);
  });
  return [...groups.entries()];
}

function selectScript(scriptId, rerenderBoard = true) {
  appState.selectedId = scriptId;
  if (rerenderBoard) renderBoard();
  renderDetail();
}

function toggleFavorite(scriptId) {
  if (appState.favorites.has(scriptId)) {
    appState.favorites.delete(scriptId);
  } else {
    appState.favorites.add(scriptId);
  }
  localStorage.setItem(storageKeys.favorites, JSON.stringify([...appState.favorites]));
  render();
}

function rememberRecent(scriptId) {
  appState.recent = [scriptId, ...appState.recent.filter((candidateId) => candidateId !== scriptId)].slice(0, 20);
  persistRecent();
}

function persistRecent() {
  localStorage.setItem(storageKeys.recent, JSON.stringify(appState.recent));
}

function setViewMode(viewMode) {
  appState.viewMode = viewMode;
  localStorage.setItem(storageKeys.viewMode, viewMode);
  elements.gridViewBtn.classList.toggle("active", viewMode === "grid");
  elements.listViewBtn.classList.toggle("active", viewMode === "list");
  if (elements.main) elements.main.classList.toggle("list-view", viewMode === "list");
}

function openSettings() {
  elements.rootInput.value = appState.scanRoot === "-" ? "" : appState.scanRoot;
  elements.settingsModal.hidden = false;
  requestAnimationFrame(() => elements.rootInput.focus());
}

function closeSettings() {
  elements.settingsModal.hidden = true;
}

function applyInitialTheme() {
  const storedTheme = localStorage.getItem(storageKeys.theme);
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const theme = storedTheme || (prefersDark ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
  elements.themeBtn.textContent = theme === "dark" ? "☀" : "☾";
}

function toggleTheme() {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem(storageKeys.theme, nextTheme);
  elements.themeBtn.textContent = nextTheme === "dark" ? "☀" : "☾";
}

function getViewTitle() {
  if (appState.activeMode === "favorites") return "我的收藏";
  if (appState.activeMode === "recent") return "最近运行";
  if (appState.activeMode === "folder") return appState.activePath || "目录筛选";
  return "全部脚本";
}

function colorFor(text) {
  let hash = 0;
  for (const character of text) {
    hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  }
  return palette[Math.abs(hash) % palette.length];
}

function iconFor(text) {
  const lowerText = text.toLowerCase();
  const iconRules = [
    [["ai", "gpt", "llm", "deepseek", "kimi", "chat", "智能"], "bot"],
    [["excel", "csv", "xls", "表格", "pandas"], "chart-bar"],
    [["db", "sql", "mysql", "sqlite", "数据库"], "database"],
    [["crawl", "spider", "scrape", "爬", "采集", "抓取"], "bug"],
    [["image", "img", "photo", "图", "图片", "wechat"], "image"],
    [["keyword", "rank", "seo", "关键词", "排名"], "search"],
    [["build", "exe", "pyinstaller", "打包"], "hammer"],
    [["json", "api", "extract", "转换", "解析"], "code-2"],
    [["log", "日志", "analysis", "统计"], "chart-line"],
    [["push", "submit", "提交", "推送"], "send"],
  ];
  const matchedRule = iconRules.find(([keywords]) => keywords.some((keyword) => lowerText.includes(keyword)));
  return matchedRule ? matchedRule[1] : "zap";
}

function getFolderPath(filePath) {
  return filePath.replace(/[\\/][^\\/]+$/, "");
}

function toast(message, type = "ok") {
  elements.toast.textContent = message;
  elements.toast.className = `toast ${type} show`;
  clearTimeout(elements.toast.hideTimer);
  elements.toast.hideTimer = setTimeout(() => {
    elements.toast.classList.remove("show");
  }, 2400);
}

/* —— 回到顶部小火箭 —— */
const rocketBtn = document.getElementById("rocketBtn");
const contentEl = document.querySelector(".content");

contentEl.addEventListener("scroll", () => {
  rocketBtn.classList.toggle("visible", contentEl.scrollTop > 10);
});
rocketBtn.addEventListener("click", () => {
  rocketBtn.classList.add("launching");
  rocketBtn.classList.remove("visible");
  /* 等升空动画结束后再滚回顶部 */
  setTimeout(() => {
    contentEl.scrollTo({ top: 0, behavior: "smooth" });
  }, 350);
  /* 动画完成后清理 */
  setTimeout(() => {
    rocketBtn.classList.remove("launching");
    /* 滚回顶部后重新检查是否需要显示 */
    rocketBtn.classList.toggle("visible", contentEl.scrollTop > 10);
  }, 700);
});

function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}

function renderMarkdown(text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text);
  }
  // fallback: 简单处理基本 markdown 语法
  return escapeHtml(text)
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}
