"use strict";

const state = {
  data: null,
  search: "",
  category: "all",
  rarity: "all",
};

const els = {
  grid: document.getElementById("itemGrid"),
  search: document.getElementById("searchInput"),
  categoryFilters: document.getElementById("categoryFilters"),
  rarityFilters: document.getElementById("rarityFilters"),
  resultCount: document.getElementById("resultCount"),
  empty: document.getElementById("emptyState"),
  footerStat: document.getElementById("footerStat"),
};

init();

async function init() {
  try {
    const res = await fetch("data/items.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.data = await res.json();
  } catch (err) {
    els.grid.innerHTML = "";
    els.empty.hidden = false;
    els.empty.textContent =
      "아이템 데이터를 불러오지 못했습니다. 로컬 서버에서 실행해 주세요. (예: python3 -m http.server)";
    console.error(err);
    return;
  }

  buildFilters();
  bindEvents();
  render();

  els.footerStat.textContent =
    `전체 ${state.data.items.length}종 · ${state.data.categories.length}개 분류 · 도감 v${state.data.meta.version}`;
}

function buildFilters() {
  const { categories, rarities } = state.data;

  els.categoryFilters.appendChild(makeChip("전체", "all", "category", true));
  categories.forEach((c) =>
    els.categoryFilters.appendChild(
      makeChip(`${c.icon} ${c.name}`, c.id, "category", false)
    )
  );

  els.rarityFilters.appendChild(makeChip("모든 등급", "all", "rarity", true));
  rarities.forEach((r) => {
    const chip = makeChip(r.name, r.id, "rarity", false);
    chip.dataset.rarity = r.id;
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = r.color;
    chip.prepend(dot);
    els.rarityFilters.appendChild(chip);
  });
}

function makeChip(label, value, group, pressed) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "chip";
  btn.textContent = label;
  btn.dataset.group = group;
  btn.dataset.value = value;
  btn.setAttribute("aria-pressed", String(pressed));
  btn.addEventListener("click", () => {
    state[group] = value;
    document
      .querySelectorAll(`.chip[data-group="${group}"]`)
      .forEach((c) => c.setAttribute("aria-pressed", String(c === btn)));
    render();
  });
  return btn;
}

function bindEvents() {
  els.search.addEventListener("input", (e) => {
    state.search = e.target.value.trim().toLowerCase();
    render();
  });
}

function getFiltered() {
  return state.data.items.filter((item) => {
    if (state.category !== "all" && item.category !== state.category) return false;
    if (state.rarity !== "all" && item.rarity !== state.rarity) return false;
    if (state.search) {
      const haystack = `${item.name} ${item.description}`.toLowerCase();
      if (!haystack.includes(state.search)) return false;
    }
    return true;
  });
}

function render() {
  const items = getFiltered();
  els.grid.innerHTML = "";

  els.empty.hidden = items.length !== 0;
  els.resultCount.textContent = `${items.length}개의 아이템을 표시 중`;

  const frag = document.createDocumentFragment();
  items.forEach((item) => frag.appendChild(makeCard(item)));
  els.grid.appendChild(frag);
}

function makeCard(item) {
  const category = state.data.categories.find((c) => c.id === item.category);
  const rarity = state.data.rarities.find((r) => r.id === item.rarity);

  const card = document.createElement("article");
  card.className = "card";
  card.style.setProperty("--rarity", rarity ? rarity.color : "var(--gold)");

  const stats = Object.entries(item.stats || {})
    .map(([k, v]) => `<span class="stat">${escapeHtml(k)} <b>${escapeHtml(String(v))}</b></span>`)
    .join("");

  card.innerHTML = `
    <div class="card__head">
      <span class="card__icon">${item.icon || category?.icon || "❔"}</span>
      <h2 class="card__title">${escapeHtml(item.name)}</h2>
    </div>
    <div class="card__tags">
      <span class="tag">${category ? category.icon + " " + escapeHtml(category.name) : "기타"}</span>
      <span class="tag tag--rarity" style="background:${rarity ? rarity.color : "var(--gold)"}">
        ${rarity ? escapeHtml(rarity.name) : ""}
      </span>
    </div>
    <p class="card__desc">${escapeHtml(item.description)}</p>
    <div class="card__stats">${stats}</div>
    <div class="card__meta">
      <span>무게 ${item.weight ?? "—"}</span>
      <span class="gold">💰 ${formatGold(item.value)}</span>
    </div>
  `;
  return card;
}

function formatGold(n) {
  if (typeof n !== "number") return "—";
  return n.toLocaleString("ko-KR") + " G";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
