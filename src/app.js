const {
  createInitialState,
  getSeason,
  getBuildingList,
  getAvailableActions,
  performAction,
  advanceTurn,
  formatCost,
  resourceLabels
} = window.FantasySimulator;

const storageKey = "medieval-fantasy-simulator-state";
let state = loadState();

const elements = {
  kingdomName: document.querySelector("#kingdom-name"),
  turn: document.querySelector("#turn"),
  season: document.querySelector("#season"),
  status: document.querySelector("#status"),
  resources: document.querySelector("#resources"),
  metrics: document.querySelector("#metrics"),
  buildings: document.querySelector("#buildings"),
  adventurers: document.querySelector("#adventurers"),
  actions: document.querySelector("#actions"),
  log: document.querySelector("#log"),
  advance: document.querySelector("#advance-turn"),
  reset: document.querySelector("#reset")
};

elements.advance.addEventListener("click", () => {
  const result = advanceTurn(state);
  state = result.state;
  persistAndRender();
});

elements.reset.addEventListener("click", () => {
  state = createInitialState({ seed: Date.now() });
  persistAndRender();
});

render();

function loadState() {
  try {
    const saved = localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : createInitialState();
  } catch (error) {
    console.warn("Saved state could not be loaded.", error);
    return createInitialState();
  }
}

function persistAndRender() {
  localStorage.setItem(storageKey, JSON.stringify(state));
  render();
}

function render() {
  elements.kingdomName.textContent = state.kingdomName;
  elements.turn.textContent = `${state.turn}턴`;
  elements.season.textContent = getSeason(state);
  elements.status.textContent = state.gameOverReason || "왕국은 아직 버티고 있습니다.";
  elements.status.classList.toggle("is-ending", Boolean(state.gameOverReason));
  elements.advance.disabled = Boolean(state.gameOverReason);

  renderResources();
  renderMetrics();
  renderBuildings();
  renderAdventurers();
  renderActions();
  renderLog();
}

function renderResources() {
  const resourceOrder = ["gold", "food", "wood", "mana", "morale"];
  elements.resources.innerHTML = resourceOrder
    .map((resource) => {
      const value = Math.round(state.resources[resource]);
      const meter = resource === "morale" ? progressBar(value, 100) : "";
      return `
        <article class="card resource-card">
          <span>${resourceLabels[resource]}</span>
          <strong>${value}</strong>
          ${meter}
        </article>
      `;
    })
    .join("");
}

function renderMetrics() {
  const metrics = [
    { label: "인구", value: state.population, max: 140 },
    { label: "병력", value: state.army, max: 120 },
    { label: "위협도", value: state.threat, max: 100, danger: true },
    { label: "명성", value: state.reputation, max: 100 }
  ];

  elements.metrics.innerHTML = metrics
    .map((metric) => `
      <article class="card metric-card ${metric.danger ? "danger" : ""}">
        <div>
          <span>${metric.label}</span>
          <strong>${Math.round(metric.value)}</strong>
        </div>
        ${progressBar(metric.value, metric.max)}
      </article>
    `)
    .join("");
}

function renderBuildings() {
  elements.buildings.innerHTML = getBuildingList(state)
    .map((building) => `
      <li>
        <span class="building-icon">${building.icon}</span>
        <div>
          <strong>${building.name}</strong>
          <small>${building.description}</small>
        </div>
        <b>x${building.count}</b>
      </li>
    `)
    .join("");
}

function renderAdventurers() {
  elements.adventurers.innerHTML = state.adventurers
    .map((adventurer) => `
      <li>
        <div>
          <strong>${adventurer.name}</strong>
          <small>${adventurer.role}</small>
        </div>
        <span>Lv.${adventurer.level}</span>
        <span>충성 ${adventurer.loyalty}</span>
        <em>${adventurer.status}</em>
      </li>
    `)
    .join("");
}

function renderActions() {
  elements.actions.innerHTML = getAvailableActions(state)
    .map((action) => `
      <button class="action-card" type="button" data-action="${action.id}" ${action.disabled ? "disabled" : ""}>
        <span>${action.category}</span>
        <strong>${action.title}</strong>
        <small>${action.description}</small>
        <b>${formatCost(action.cost)}</b>
      </button>
    `)
    .join("");

  elements.actions.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const result = performAction(state, button.dataset.action);
      state = result.state;
      if (!result.ok) {
        state.log = [result.message, ...state.log].slice(0, 30);
      }
      persistAndRender();
    });
  });
}

function renderLog() {
  elements.log.innerHTML = state.log
    .map((item) => `<li>${item}</li>`)
    .join("");
}

function progressBar(value, max) {
  const percent = Math.max(0, Math.min(100, Math.round((value / max) * 100)));
  return `
    <div class="meter" aria-hidden="true">
      <span style="width: ${percent}%"></span>
    </div>
  `;
}
