const DATA_PATH = "data/index.json";
const SEARCH_MANIFEST_PATH = "data/search/manifest.json";
const SEARCH_FALLBACK_PATH = "data/search.json";
const STAR_KEY = "chat-insights-stars";
const NOTE_KEY = "chat-insights-notes";
const CITE_RE = /.*?/g;
const TOOL_JSON_KEYS = new Set([
  "search_query",
  "response_length",
  "path",
  "args",
  "tool_calls",
  "tool",
  "function",
  "call",
]);

const state = {
  items: [],
  filtered: [],
  selected: null,
  activeKeyword: null,
  activeCluster: null,
  availableKeywords: [],
  availableClusters: [],
  sortBy: "updated",
  search: "",
  startDate: "",
  endDate: "",
  minMessages: 0,
  onlyStarred: false,
  searchIndexMap: null,
  searchIndexLoaded: false,
  searchIndexLoading: false,
  searchIndexPromise: null,
};

const stars = new Set(JSON.parse(localStorage.getItem(STAR_KEY) || "[]"));
const notes = JSON.parse(localStorage.getItem(NOTE_KEY) || "{}");

const els = {
  searchInput: document.getElementById("searchInput"),
  startDate: document.getElementById("startDate"),
  endDate: document.getElementById("endDate"),
  minMessages: document.getElementById("minMessages"),
  minMessagesValue: document.getElementById("minMessagesValue"),
  onlyStarred: document.getElementById("onlyStarred"),
  keywordChips: document.getElementById("keywordChips"),
  clusterChips: document.getElementById("clusterChips"),
  conversationList: document.getElementById("conversationList"),
  listMeta: document.getElementById("listMeta"),
  detailTitle: document.getElementById("detailTitle"),
  detailMeta: document.getElementById("detailMeta"),
  conversationDetail: document.getElementById("conversationDetail"),
  openFileBtn: document.getElementById("openFileBtn"),
  starToggleBtn: document.getElementById("starToggleBtn"),
  noteInput: document.getElementById("noteInput"),
  detailHighlights: document.getElementById("detailHighlights"),
  detailSimilar: document.getElementById("detailSimilar"),
  metricTotal: document.getElementById("metricTotal"),
  metricRange: document.getElementById("metricRange"),
  metricStarred: document.getElementById("metricStarred"),
  randomBtn: document.getElementById("randomBtn"),
  clearFiltersBtn: document.getElementById("clearFiltersBtn"),
  exportGuideBtn: document.getElementById("exportGuideBtn"),
  sortControl: document.getElementById("sortControl"),
  insightKeywords: document.getElementById("insightKeywords"),
  insightTimeline: document.getElementById("insightTimeline"),
  insightClusters: document.getElementById("insightClusters"),
};

function parseDate(value) {
  if (!value || value === "unknown") return null;
  const parsed = new Date(value.replace(" ", "T").replace("Z", "Z"));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(date) {
  if (!date) return "unknown";
  return date.toISOString().slice(0, 10);
}

function updateMetrics() {
  els.metricTotal.textContent = state.items.length.toLocaleString();
  const dates = state.items
    .map((item) => parseDate(item.created_utc))
    .filter(Boolean)
    .sort((a, b) => a - b);
  if (dates.length) {
    const start = formatDate(dates[0]);
    const end = formatDate(dates[dates.length - 1]);
    els.metricRange.textContent = `${start} → ${end}`;
  } else {
    els.metricRange.textContent = "unknown";
  }
  els.metricStarred.textContent = stars.size.toLocaleString();
}

function saveStars() {
  localStorage.setItem(STAR_KEY, JSON.stringify(Array.from(stars)));
  updateMetrics();
}

function saveNotes() {
  localStorage.setItem(NOTE_KEY, JSON.stringify(notes));
}

function applyFilters() {
  const query = state.search.trim().toLowerCase();
  const terms = query.split(/\s+/).filter(Boolean);
  const start = state.startDate ? new Date(state.startDate) : null;
  const end = state.endDate ? new Date(state.endDate) : null;

  if (terms.length && !state.searchIndexLoaded && !state.searchIndexLoading) {
    ensureSearchIndex();
  }

  state.filtered = state.items.filter((item) => {
    if (state.minMessages && item.messages < state.minMessages) return false;
    if (state.onlyStarred && !stars.has(item.file)) return false;
    if (state.activeKeyword && !item.keywords.includes(state.activeKeyword))
      return false;
    if (state.activeCluster && item.cluster_label !== state.activeCluster)
      return false;
    if (start || end) {
      const created = parseDate(item.created_utc);
      if (!created) return false;
      if (start && created < start) return false;
      if (end && created > end) return false;
    }
    if (terms.length) {
      const title = item.title_lc || "";
      const keywords = item.keyword_text || "";
      const snippet = item.snippet_lc || "";
      const searchText = state.searchIndexMap?.get(item.file) || "";
      const matched = terms.every(
        (term) =>
          title.includes(term) ||
          keywords.includes(term) ||
          snippet.includes(term) ||
          searchText.includes(term)
      );
      if (!matched) return false;
    }
    return true;
  });

  sortItems();
  renderList();
}

function sortItems() {
  const sort = state.sortBy;
  state.filtered.sort((a, b) => {
    if (sort === "messages") return b.messages - a.messages;
    const dateA = parseDate(sort === "created" ? a.created_utc : a.updated_utc);
    const dateB = parseDate(sort === "created" ? b.created_utc : b.updated_utc);
    if (!dateA && !dateB) return 0;
    if (!dateA) return 1;
    if (!dateB) return -1;
    return sort === "created" ? dateA - dateB : dateB - dateA;
  });
}

function renderKeywordChips(keywords) {
  els.keywordChips.innerHTML = "";
  const fragment = document.createDocumentFragment();
  const allChip = document.createElement("span");
  allChip.className = `chip ${state.activeKeyword ? "" : "active"}`;
  allChip.textContent = "全部";
  allChip.addEventListener("click", () => {
    state.activeKeyword = null;
    applyFilters();
    renderKeywordChips(keywords);
  });
  fragment.appendChild(allChip);

  keywords.forEach((term) => {
    const chip = document.createElement("span");
    chip.className = `chip ${state.activeKeyword === term ? "active" : ""}`;
    chip.textContent = term;
    chip.addEventListener("click", () => {
      state.activeKeyword = term;
      applyFilters();
      renderKeywordChips(keywords);
    });
    fragment.appendChild(chip);
  });
  els.keywordChips.appendChild(fragment);
}

function renderClusterChips(clusters) {
  els.clusterChips.innerHTML = "";
  const fragment = document.createDocumentFragment();
  const allChip = document.createElement("span");
  allChip.className = `chip ${state.activeCluster ? "" : "active"}`;
  allChip.textContent = "全部";
  allChip.addEventListener("click", () => {
    state.activeCluster = null;
    applyFilters();
    renderClusterChips(clusters);
  });
  fragment.appendChild(allChip);

  clusters.slice(0, 18).forEach((cluster) => {
    const chip = document.createElement("span");
    chip.className = `chip ${
      state.activeCluster === cluster.label ? "active" : ""
    }`;
    chip.textContent = `${cluster.label} (${cluster.count})`;
    chip.addEventListener("click", () => {
      state.activeCluster = cluster.label;
      applyFilters();
      renderClusterChips(clusters);
    });
    fragment.appendChild(chip);
  });
  els.clusterChips.appendChild(fragment);
}

function renderInsights(insights) {
  const topKeywords = (insights.top_keywords || []).slice(0, 12);
  els.insightKeywords.innerHTML = "";
  topKeywords.forEach((entry) => {
    const tag = document.createElement("span");
    tag.textContent = `${entry.term} · ${entry.count}`;
    els.insightKeywords.appendChild(tag);
  });

  const monthCounts = insights.month_counts || {};
  const values = Object.values(monthCounts);
  const max = Math.max(1, ...values);
  els.insightTimeline.innerHTML = "";
  Object.entries(monthCounts).forEach(([month, count]) => {
    const bar = document.createElement("span");
    bar.style.height = `${Math.max(8, (count / max) * 80)}px`;
    bar.title = `${month}: ${count}`;
    els.insightTimeline.appendChild(bar);
  });

  const clusters = (insights.clusters || []).slice(0, 10);
  els.insightClusters.innerHTML = "";
  clusters.forEach((cluster) => {
    const tag = document.createElement("span");
    tag.textContent = `${cluster.label} · ${cluster.count}`;
    els.insightClusters.appendChild(tag);
  });
}

async function loadSearchIndex() {
  try {
    let entries = [];
    const manifestResp = await fetch(SEARCH_MANIFEST_PATH);
    if (manifestResp.ok) {
      const manifest = await manifestResp.json();
      const shardPromises = (manifest.shards || []).map((shard) =>
        fetch(`data/search/${shard.file}`).then((resp) => resp.json())
      );
      const shards = await Promise.all(shardPromises);
      entries = shards.flatMap((shard) => shard.items || []);
    } else {
      const fallbackResp = await fetch(SEARCH_FALLBACK_PATH);
      if (!fallbackResp.ok) throw new Error("search index missing");
      const data = await fallbackResp.json();
      entries = data.items || data || [];
    }
    state.searchIndexMap = new Map(
      entries.map((entry) => [entry.file, entry.search_text || ""])
    );
    state.searchIndexLoaded = true;
  } catch (error) {
    state.searchIndexMap = new Map();
    state.searchIndexLoaded = true;
  } finally {
    state.searchIndexLoading = false;
    state.searchIndexPromise = null;
    applyFilters();
  }
}

function ensureSearchIndex() {
  if (state.searchIndexLoaded || state.searchIndexLoading) return;
  state.searchIndexLoading = true;
  state.searchIndexPromise = loadSearchIndex();
}

function renderList() {
  const loading = state.searchIndexLoading ? " · 搜索索引加载中" : "";
  els.listMeta.textContent = `显示 ${state.filtered.length} / ${state.items.length}${loading}`;
  els.conversationList.innerHTML = "";
  const fragment = document.createDocumentFragment();
  state.filtered.forEach((item) => {
    const card = document.createElement("div");
    card.className = "card";
    if (state.selected && state.selected.file === item.file) {
      card.classList.add("active");
    }
    card.setAttribute("role", "button");
    card.tabIndex = 0;

    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = item.title;

    const meta = document.createElement("div");
    meta.className = "card-meta";
    const date = document.createElement("span");
    date.textContent = item.created_utc || "unknown";
    const messages = document.createElement("span");
    const star = stars.has(item.file) ? " ★" : "";
    messages.textContent = `${item.messages} 条${star}`;
    meta.appendChild(date);
    meta.appendChild(messages);

    const tags = document.createElement("div");
    tags.className = "card-tags";
    if (item.cluster_label) {
      const cluster = document.createElement("span");
      cluster.className = "tag cluster";
      cluster.textContent = item.cluster_label;
      tags.appendChild(cluster);
    }
    item.keywords.slice(0, 4).forEach((term) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = term;
      tags.appendChild(tag);
    });

    const snippet = document.createElement("div");
    snippet.className = "card-snippet";
    snippet.textContent = item.snippet ? `${item.snippet}…` : "（无摘要）";

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(tags);
    card.appendChild(snippet);

    card.addEventListener("click", () => selectConversation(item));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") selectConversation(item);
    });

    fragment.appendChild(card);
  });
  els.conversationList.appendChild(fragment);
}

function renderHighlights(highlights) {
  els.detailHighlights.innerHTML = "";
  if (!highlights || !highlights.length) {
    const empty = document.createElement("li");
    empty.textContent = "未发现可自动提取的重点。";
    els.detailHighlights.appendChild(empty);
    return;
  }
  highlights.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    els.detailHighlights.appendChild(item);
  });
}

function renderSimilar(selectedItem) {
  const baseSet = selectedItem.keyword_set || new Set(selectedItem.keywords || []);
  const scored = state.items
    .filter((item) => item.file !== selectedItem.file)
    .map((item) => {
      const set = item.keyword_set || new Set(item.keywords || []);
      if (!baseSet.size || !set.size) return { item, score: 0 };
      let overlap = 0;
      baseSet.forEach((term) => {
        if (set.has(term)) overlap += 1;
      });
      const union = new Set([...baseSet, ...set]).size || 1;
      return { item, score: overlap / union };
    })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  els.detailSimilar.innerHTML = "";
  if (!scored.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "暂无相似对话。";
    els.detailSimilar.appendChild(empty);
    return;
  }
  scored.forEach((entry) => {
    const card = document.createElement("div");
    card.className = "similar-card";
    card.innerHTML = `<strong>${entry.item.title}</strong>
      <span>${entry.item.created_utc || "unknown"} · 相似度 ${Math.round(
      entry.score * 100
    )}%</span>`;
    card.addEventListener("click", () => selectConversation(entry.item));
    els.detailSimilar.appendChild(card);
  });
}

function renderMessages(messages) {
  els.conversationDetail.innerHTML = "";
  if (!messages.length) {
    els.conversationDetail.innerHTML =
      '<div class="empty-state">这条对话没有可展示的内容。</div>';
    return;
  }
  messages.forEach((msg) => {
    const segments = parseSegments(msg.body);
    if (!segments.length) return;
    const visibleSegments = segments.filter(
      (segment) => segment.type !== "code" || !isToolCallBlock(segment)
    );
    if (!visibleSegments.length) return;

    const message = document.createElement("div");
    const roleType = msg.role.split(" ")[0].split(":")[0];
    message.className = `message role-${roleType}`;

    const role = document.createElement("div");
    role.className = "message-role";
    role.textContent = msg.role;
    message.appendChild(role);

    visibleSegments.forEach((segment) => {
      if (segment.type === "code") {
        const pre = document.createElement("pre");
        const codeEl = document.createElement("code");
        codeEl.textContent = segment.code || "";
        if (segment.lang) {
          const badge = document.createElement("div");
          badge.className = "code-lang";
          badge.textContent = segment.lang;
          pre.appendChild(badge);
        }
        pre.appendChild(codeEl);
        message.appendChild(pre);
      } else {
        const body = document.createElement("div");
        body.className = "message-body";
        body.textContent = segment.text;
        message.appendChild(body);
      }
    });

    els.conversationDetail.appendChild(message);
  });
}

function parseConversation(raw) {
  const normalized = raw.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  let start = 0;
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].trim() === "---") {
      start = i + 1;
      break;
    }
  }
  const body = lines.slice(start).join("\n");
  if (body.includes("<!-- MSG role:")) {
    const matches = [
      ...body.matchAll(
        /<!-- MSG role: (.+?) -->\n(?:### .+?\n\n)?([\s\S]*?)\n<!-- \/MSG -->/g
      ),
    ];
    return matches.map((match) => ({
      role: match[1].trim(),
      body: match[2].trim(),
    }));
  }
  const matches = [...body.matchAll(/^### (.+?)\n\n([\s\S]*?)(?=\n### |\n?$)/gm)];
  return matches.map((match) => ({
    role: match[1].trim(),
    body: match[2].trim(),
  }));
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return null;
  }
}

function cleanTextSegment(text) {
  const lines = text.split("\n");
  const cleaned = [];
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      const obj = safeJsonParse(trimmed);
      if (obj) {
        const ctype = obj.content_type || "";
        if (ctype.includes("transcription") && obj.text) {
          cleaned.push(String(obj.text).trim());
        }
        return;
      }
    }
    if (trimmed.includes("sediment://")) return;
    const withoutCite = trimmed.replace(CITE_RE, "").trim();
    if (withoutCite) cleaned.push(withoutCite);
  });
  return cleaned.join("\n");
}

function isToolCallBlock(segment) {
  if (!segment || segment.type !== "code") return false;
  if (!segment.lang || segment.lang.toLowerCase() !== "unknown") return false;
  const obj = safeJsonParse(segment.code.trim());
  if (!obj || typeof obj !== "object") return false;
  return Object.keys(obj).some((key) => TOOL_JSON_KEYS.has(key));
}

function parseSegments(body) {
  const segments = [];
  const parts = body.split("```");
  parts.forEach((part, idx) => {
    if (idx % 2 === 1) {
      const lines = part.split("\n");
      const lang = (lines.shift() || "").trim();
      const code = lines.join("\n").trim();
      if (!code) return;
      segments.push({ type: "code", lang, code });
    } else {
      const cleaned = cleanTextSegment(part);
      if (cleaned) {
        segments.push({ type: "text", text: cleaned });
      }
    }
  });
  return segments;
}

async function selectConversation(item) {
  state.selected = item;
  els.detailTitle.textContent = item.title;
  const cluster = item.cluster_label ? ` · 主题：${item.cluster_label}` : "";
  els.detailMeta.textContent = `${item.created_utc} · ${item.messages} 条消息${cluster}`;
  els.openFileBtn.disabled = false;
  els.starToggleBtn.disabled = false;
  els.noteInput.disabled = false;
  els.noteInput.value = notes[item.file] || "";
  els.starToggleBtn.textContent = stars.has(item.file) ? "取消标星" : "标星";
  els.openFileBtn.onclick = () => window.open(item.file, "_blank");
  els.starToggleBtn.onclick = () => {
    if (stars.has(item.file)) {
      stars.delete(item.file);
    } else {
      stars.add(item.file);
    }
    saveStars();
    els.starToggleBtn.textContent = stars.has(item.file) ? "取消标星" : "标星";
    renderList();
  };
  els.noteInput.oninput = (event) => {
    notes[item.file] = event.target.value;
    saveNotes();
  };

  try {
    els.conversationDetail.innerHTML =
      '<div class="empty-state">正在载入对话…</div>';
    const response = await fetch(item.file);
    if (!response.ok) throw new Error("load failed");
    const text = await response.text();
    const messages = parseConversation(text);
    renderMessages(messages);
  } catch (error) {
    els.conversationDetail.innerHTML =
      '<div class="empty-state">无法读取对话内容，请确认本地服务器正在运行。</div>';
  }
  renderHighlights(item.highlights || []);
  renderSimilar(item);
  renderList();
}

function bindEvents() {
  let searchTimer;
  els.searchInput.addEventListener("input", (event) => {
    state.search = event.target.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applyFilters, 120);
  });
  els.startDate.addEventListener("change", (event) => {
    state.startDate = event.target.value;
    applyFilters();
  });
  els.endDate.addEventListener("change", (event) => {
    state.endDate = event.target.value;
    applyFilters();
  });
  els.minMessages.addEventListener("input", (event) => {
    state.minMessages = Number(event.target.value || 0);
    els.minMessagesValue.textContent = `${state.minMessages}+`;
    applyFilters();
  });
  els.onlyStarred.addEventListener("change", (event) => {
    state.onlyStarred = event.target.checked;
    applyFilters();
  });
  els.sortControl.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-sort]");
    if (!button) return;
    state.sortBy = button.dataset.sort;
    Array.from(els.sortControl.querySelectorAll("button")).forEach((btn) => {
      btn.classList.toggle("active", btn === button);
    });
    applyFilters();
  });
  els.randomBtn.addEventListener("click", () => {
    if (!state.filtered.length) return;
    const item =
      state.filtered[Math.floor(Math.random() * state.filtered.length)];
    selectConversation(item);
  });
  els.exportGuideBtn.addEventListener("click", () => {
    window.open("../docs/EXPORTS.md", "_blank");
  });
  els.clearFiltersBtn.addEventListener("click", () => {
    state.search = "";
    state.startDate = "";
    state.endDate = "";
    state.minMessages = 0;
    state.onlyStarred = false;
    state.activeKeyword = null;
    state.activeCluster = null;
    els.searchInput.value = "";
    els.startDate.value = "";
    els.endDate.value = "";
    els.minMessages.value = 0;
    els.minMessagesValue.textContent = "0+";
    els.onlyStarred.checked = false;
    renderKeywordChips(state.availableKeywords);
    renderClusterChips(state.availableClusters);
    applyFilters();
  });
}

async function init() {
  try {
    const response = await fetch(DATA_PATH);
    if (!response.ok) throw new Error("data load failed");
    const data = await response.json();
    state.items = (data.items || []).map((item) => ({
      ...item,
      title_lc: (item.title || "").toLowerCase(),
      keyword_text: (item.keywords || []).join(" ").toLowerCase(),
      snippet_lc: (item.snippet || "").toLowerCase(),
      keyword_set: new Set(item.keywords || []),
    }));
    updateMetrics();
    renderInsights(data.insights || {});
    const keywords = (data.insights?.top_keywords || [])
      .slice(0, 18)
      .map((entry) => entry.term);
    state.availableKeywords = keywords;
    state.availableClusters = data.insights?.clusters || [];
    renderKeywordChips(state.availableKeywords);
    renderClusterChips(state.availableClusters);
    applyFilters();
  } catch (error) {
    els.conversationList.innerHTML =
      '<div class="empty-state">未找到索引数据。请先运行 <code>python tools/build_data.py --source chatgpt --input &lt;export&gt;</code> 生成 data/index.json。</div>';
  }
}

bindEvents();
init();

window.addEventListener("load", () => {
  document.body.classList.add("ready");
});
