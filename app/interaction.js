const DATA_PATH = "data/interaction.json";

const els = {
  metrics: document.getElementById("reportMetrics"),
  method: document.getElementById("reportMethod"),
  strengths: document.getElementById("reportStrengths"),
  gaps: document.getElementById("reportGaps"),
  quotes: document.getElementById("reportQuotes"),
  boundaries: document.getElementById("reportBoundaries"),
  clusterUp: document.getElementById("reportClusterUp"),
  clusterDown: document.getElementById("reportClusterDown"),
  backBtn: document.getElementById("backBtn"),
};

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString();
}

function renderMetrics(summary) {
  els.metrics.innerHTML = "";
  const metrics = [
    { label: "清晰度", value: formatPercent(summary.clarity_avg) },
    { label: "约束率", value: formatPercent(summary.constraint_rate) },
    { label: "背景率", value: formatPercent(summary.context_rate) },
    { label: "反馈率", value: formatPercent(summary.feedback_rate) },
    { label: "迭代率", value: formatPercent(summary.iteration_rate) },
    { label: "平均轮次", value: formatNumber(summary.avg_turns) },
    { label: "平均字数", value: formatNumber(summary.avg_user_chars) },
  ];

  metrics.forEach((item) => {
    const card = document.createElement("div");
    card.className = "report-metric-card";
    const label = document.createElement("span");
    label.textContent = item.label;
    const value = document.createElement("strong");
    value.textContent = item.value;
    card.appendChild(label);
    card.appendChild(value);
    els.metrics.appendChild(card);
  });
}

function renderList(container, items, emptyText) {
  container.innerHTML = "";
  if (!items || !items.length) {
    const empty = document.createElement("div");
    empty.className = "report-item";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "report-item";
    const title = document.createElement("strong");
    title.textContent = item.label || "—";
    card.appendChild(title);
    if (item.detail) {
      const detail = document.createElement("div");
      detail.textContent = item.detail;
      card.appendChild(detail);
    }
    container.appendChild(card);
  });
}

function renderQuotes(container, quotes, emptyText) {
  container.innerHTML = "";
  if (!quotes || !quotes.length) {
    const empty = document.createElement("div");
    empty.className = "report-item";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }
  quotes.forEach((quote) => {
    const card = document.createElement("div");
    card.className = "report-quote";
    card.textContent = quote.text || "—";
    const label = document.createElement("span");
    label.textContent = quote.label || "引用";
    card.appendChild(label);
    if (quote.file) {
      card.addEventListener("click", () => {
        window.open(quote.file, "_blank");
      });
    }
    container.appendChild(card);
  });
}

function renderClusterList(container, items, emptyText) {
  container.innerHTML = "";
  if (!items || !items.length) {
    const empty = document.createElement("div");
    empty.className = "report-item";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "report-item";
    const title = document.createElement("strong");
    const delta = Number.isFinite(item.delta)
      ? `${item.delta > 0 ? "+" : ""}${Math.round(item.delta * 100)}%`
      : "—";
    title.textContent = `${item.label || "主题"} · ${delta}`;
    const detail = document.createElement("div");
    detail.textContent = `早期 ${formatPercent(item.early)} → 最近 ${formatPercent(
      item.recent
    )}（${formatNumber(item.count)} 条）`;
    card.appendChild(title);
    card.appendChild(detail);
    container.appendChild(card);
  });
}

async function init() {
  try {
    const response = await fetch(DATA_PATH);
    if (!response.ok) throw new Error("missing");
    const data = await response.json();
    renderMetrics(data.summary || {});
    renderList(els.strengths, data.strengths, "暂无优势统计。");
    renderList(els.gaps, data.gaps, "暂无可改进项。");
    renderQuotes(els.quotes, data.quotes, "暂无引用。");
    renderQuotes(els.boundaries, data.boundaries, "暂无边界提示。");
    renderClusterList(
      els.clusterUp,
      data.cluster_trends?.improving,
      "暂无明显提升主题。"
    );
    renderClusterList(
      els.clusterDown,
      data.cluster_trends?.needs_work,
      "暂无明显下降主题。"
    );

    const generated = data.generated_utc ? `生成时间：${data.generated_utc}` : "";
    els.method.textContent = [data.method, generated].filter(Boolean).join(" · ");
  } catch (error) {
    els.metrics.innerHTML = "";
    els.method.textContent = "未找到交互分析数据。请先运行数据构建脚本。";
  }
}

els.backBtn.addEventListener("click", () => {
  window.location.href = "index.html";
});

init();
