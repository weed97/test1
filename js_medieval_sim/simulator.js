(function exposeSimulator(root, factory) {
  const api = factory();

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }

  root.FantasySimulator = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function buildSimulator() {
  const seasons = ["봄", "여름", "가을", "겨울"];

  const buildings = {
    farm: {
      name: "영주의 농장",
      icon: "🌾",
      cost: { gold: 35, wood: 25 },
      description: "식량 생산을 늘려 긴 겨울을 버틸 기반을 만듭니다."
    },
    lumberMill: {
      name: "벌목소",
      icon: "🪓",
      cost: { gold: 25, wood: 30 },
      description: "숲의 목재 수급을 안정화해 건설 속도를 높입니다."
    },
    mageTower: {
      name: "마법사의 탑",
      icon: "🔮",
      cost: { gold: 70, wood: 45, mana: 20 },
      description: "마나 생산량을 높이고 불길한 징조를 해석합니다."
    },
    barracks: {
      name: "기사단 병영",
      icon: "⚔️",
      cost: { gold: 55, wood: 40 },
      description: "병력 훈련 효율을 높이고 위협 억제에 도움을 줍니다."
    },
    tavern: {
      name: "모험가의 주점",
      icon: "🍺",
      cost: { gold: 45, wood: 25, food: 10 },
      description: "사기를 높이고 소문을 모아 명성을 키웁니다."
    },
    walls: {
      name: "룬 각인 성벽",
      icon: "🛡️",
      cost: { gold: 80, wood: 60 },
      description: "몬스터 습격과 국경 분쟁으로부터 왕국을 보호합니다."
    }
  };

  const resourceLabels = {
    gold: "금화",
    food: "식량",
    wood: "목재",
    mana: "마나",
    morale: "사기"
  };

  const actionCatalog = [
    {
      id: "train-army",
      title: "징집과 훈련",
      category: "군사",
      cost: { gold: 25, food: 15 },
      description: "민병대와 종자들을 훈련해 병력을 늘립니다.",
      run(state) {
        const barracksBonus = state.buildings.barracks * 3;
        state.army += 8 + barracksBonus;
        state.resources.morale = clamp(state.resources.morale - 1, 0, 100);
        addLog(state, `병영에서 ${8 + barracksBonus}명의 병력이 새로 훈련되었습니다.`);
      }
    },
    {
      id: "host-festival",
      title: "수확제 개최",
      category: "민심",
      cost: { gold: 22, food: 18 },
      description: "광장에 음유시인과 장인들을 불러 백성의 마음을 달랩니다.",
      run(state) {
        state.resources.morale = clamp(state.resources.morale + 12, 0, 100);
        state.reputation = clamp(state.reputation + 4, 0, 100);
        state.threat = clamp(state.threat - 2, 0, 100);
        addLog(state, "수확제가 성황리에 끝나 사기와 명성이 올랐습니다.");
      }
    },
    {
      id: "arcane-ritual",
      title: "결계 의식",
      category: "마법",
      cost: { mana: 20, wood: 8 },
      description: "궁정 마법사들이 고대 룬으로 국경의 괴물들을 밀어냅니다.",
      run(state) {
        const towerBonus = state.buildings.mageTower * 3;
        state.threat = clamp(state.threat - 10 - towerBonus, 0, 100);
        state.resources.morale = clamp(state.resources.morale + 2, 0, 100);
        addLog(state, `결계가 빛나며 위협도가 ${10 + towerBonus}만큼 낮아졌습니다.`);
      }
    },
    {
      id: "send-quest",
      title: "모험 의뢰 파견",
      category: "모험",
      cost: { food: 10, gold: 10 },
      description: "모험가를 폐허와 숲길로 보내 보물과 정보를 찾습니다.",
      run(state) {
        const adventurer = pickAdventurer(state);
        const roll = random(state);
        const chance = clamp(
          0.56 + adventurer.level * 0.06 + state.resources.morale * 0.002 - state.threat * 0.003,
          0.25,
          0.9
        );

        if (roll <= chance) {
          const gold = 24 + adventurer.level * 8;
          state.resources.gold += gold;
          state.resources.mana += 6;
          state.reputation = clamp(state.reputation + 8, 0, 100);
          state.threat = clamp(state.threat - 4, 0, 100);
          adventurer.level += 1;
          adventurer.loyalty = clamp(adventurer.loyalty + 5, 0, 100);
          adventurer.status = "귀환";
          addLog(state, `${adventurer.name}이(가) 의뢰를 완수하고 금화 ${gold}개와 고대 룬 조각을 가져왔습니다.`);
        } else {
          state.resources.morale = clamp(state.resources.morale - 6, 0, 100);
          state.threat = clamp(state.threat + 5, 0, 100);
          adventurer.loyalty = clamp(adventurer.loyalty - 8, 0, 100);
          adventurer.status = "부상";
          addLog(state, `${adventurer.name}이(가) 폐허에서 후퇴했습니다. 위협이 커지고 사기가 떨어졌습니다.`);
        }
      }
    },
    {
      id: "recruit-settlers",
      title: "개척민 초청",
      category: "내정",
      cost: { gold: 30, food: 20 },
      description: "안전한 토지와 세금 감면을 약속해 새 주민을 받아들입니다.",
      run(state) {
        const tavernBonus = state.buildings.tavern * 2;
        state.population += 12 + tavernBonus;
        state.resources.morale = clamp(state.resources.morale + 3, 0, 100);
        addLog(state, `${12 + tavernBonus}명의 개척민이 왕국에 정착했습니다.`);
      }
    }
  ];

  const events = [
    {
      title: "방랑 상단 도착",
      run(state) {
        state.resources.gold += 22;
        state.resources.food += 8;
        state.reputation = clamp(state.reputation + 3, 0, 100);
        return "방랑 상단이 도착해 금화와 식량을 남기고 떠났습니다.";
      }
    },
    {
      title: "고블린 습격",
      condition: (state) => state.threat >= 18,
      run(state) {
        const wallReduction = state.buildings.walls * 4;
        const loss = Math.max(4, 16 - wallReduction);
        state.resources.food = Math.max(0, state.resources.food - loss);
        state.army = Math.max(0, state.army - 2);
        state.resources.morale = clamp(state.resources.morale - 5, 0, 100);
        state.threat = clamp(state.threat + 6, 0, 100);
        return `고블린 습격으로 식량 ${loss}개와 병력 일부를 잃었습니다.`;
      }
    },
    {
      title: "성소의 축복",
      run(state) {
        state.resources.food += 20;
        state.resources.morale = clamp(state.resources.morale + 5, 0, 100);
        state.threat = clamp(state.threat - 3, 0, 100);
        return "숲속 성소의 축복으로 곡식 창고가 채워졌습니다.";
      }
    },
    {
      title: "드래곤의 그림자",
      condition: (state) => state.turn >= 3,
      run(state) {
        state.threat = clamp(state.threat + 12, 0, 100);
        state.resources.mana += 8;
        state.resources.morale = clamp(state.resources.morale - 4, 0, 100);
        return "북쪽 하늘에 드래곤의 그림자가 지나가며 불길한 마나가 응집되었습니다.";
      }
    },
    {
      title: "음유시인의 영웅담",
      condition: (state) => state.resources.morale >= 35,
      run(state) {
        state.reputation = clamp(state.reputation + 9, 0, 100);
        state.resources.morale = clamp(state.resources.morale + 4, 0, 100);
        return "음유시인이 영웅담을 퍼뜨려 왕국의 명성이 높아졌습니다.";
      }
    },
    {
      title: "검은 열병",
      condition: (state) => state.resources.food < state.population * 0.7,
      run(state) {
        state.population = Math.max(10, state.population - 5);
        state.resources.morale = clamp(state.resources.morale - 7, 0, 100);
        return "식량 부족으로 검은 열병이 번져 인구와 사기가 줄었습니다.";
      }
    }
  ];

  function createInitialState(options = {}) {
    return {
      kingdomName: options.kingdomName || "은빛가시 왕국",
      turn: 1,
      seasonIndex: 0,
      rngSeed: normalizeSeed(options.seed || 73421),
      resources: {
        gold: 120,
        food: 100,
        wood: 70,
        mana: 35,
        morale: 62
      },
      population: 80,
      army: 18,
      threat: 22,
      reputation: 25,
      buildings: {
        farm: 1,
        lumberMill: 1,
        mageTower: 0,
        barracks: 0,
        tavern: 0,
        walls: 0
      },
      adventurers: [
        { name: "아리엔", role: "엘프 정찰자", level: 1, loyalty: 62, status: "대기" },
        { name: "브란", role: "북부 기사", level: 1, loyalty: 58, status: "대기" },
        { name: "미라", role: "룬 마법사", level: 1, loyalty: 65, status: "대기" }
      ],
      log: [
        "왕관이 당신에게 넘어왔습니다. 농장, 병영, 마법, 모험가를 조율해 왕국을 지키세요."
      ],
      gameOverReason: ""
    };
  }

  function getSeason(state) {
    return seasons[state.seasonIndex % seasons.length];
  }

  function getBuildingList(state) {
    return Object.entries(buildings).map(([id, building]) => ({
      id,
      ...building,
      count: state.buildings[id] || 0,
      canAfford: canPay(state, building.cost)
    }));
  }

  function getAvailableActions(state) {
    const buildingActions = Object.entries(buildings).map(([id, building]) => ({
      id: `build:${id}`,
      title: `${building.name} 건설`,
      category: "건설",
      cost: building.cost,
      description: building.description,
      disabled: Boolean(state.gameOverReason) || !canPay(state, building.cost)
    }));

    const actions = actionCatalog.map((action) => ({
      id: action.id,
      title: action.title,
      category: action.category,
      cost: action.cost,
      description: action.description,
      disabled: Boolean(state.gameOverReason) || !canPay(state, action.cost)
    }));

    return [...buildingActions, ...actions];
  }

  function performAction(inputState, actionId) {
    const state = cloneState(inputState);

    if (state.gameOverReason) {
      return { state, ok: false, message: "이미 왕국의 운명이 결정되었습니다." };
    }

    if (actionId.startsWith("build:")) {
      return buildStructure(state, actionId.replace("build:", ""));
    }

    const action = actionCatalog.find((item) => item.id === actionId);
    if (!action) {
      return { state, ok: false, message: "알 수 없는 명령입니다." };
    }

    if (!canPay(state, action.cost)) {
      return { state, ok: false, message: "자원이 부족합니다." };
    }

    spend(state, action.cost);
    action.run(state);
    evaluateGameOver(state);
    return { state, ok: true, message: `${action.title} 완료` };
  }

  function advanceTurn(inputState) {
    const state = cloneState(inputState);

    if (state.gameOverReason) {
      return { state, summary: state.gameOverReason };
    }

    const season = getSeason(state);
    const production = calculateProduction(state, season);

    Object.entries(production.resources).forEach(([resource, amount]) => {
      state.resources[resource] = Math.max(0, Math.round(state.resources[resource] + amount));
    });

    state.resources.morale = clamp(Math.round(state.resources.morale + production.morale), 0, 100);
    state.threat = clamp(Math.round(state.threat + production.threat), 0, 100);
    state.population = Math.max(0, Math.round(state.population + production.population));

    const eventMessage = applyRandomEvent(state);
    const productionMessage = [
      `${season}이(가) 지나며 금화 ${formatSigned(production.resources.gold)}, 식량 ${formatSigned(production.resources.food)}, 목재 ${formatSigned(production.resources.wood)}, 마나 ${formatSigned(production.resources.mana)} 변화가 있었습니다.`,
      `사기 ${formatSigned(production.morale)}, 위협 ${formatSigned(production.threat)}.`
    ].join(" ");

    addLog(state, productionMessage);
    addLog(state, eventMessage);

    state.turn += 1;
    state.seasonIndex = (state.seasonIndex + 1) % seasons.length;

    state.adventurers.forEach((adventurer) => {
      if (adventurer.status !== "대기") {
        adventurer.status = "대기";
      }
    });

    evaluateGameOver(state);
    return { state, summary: `${productionMessage} ${eventMessage}` };
  }

  function calculateProduction(state, season) {
    const winterPenalty = season === "겨울" ? -14 : 0;
    const autumnBonus = season === "가을" ? 12 : 0;
    const summerBonus = season === "여름" ? 5 : 0;
    const armyUpkeepFood = state.army * 0.08;
    const armyUpkeepGold = state.army * 0.18;
    const populationFood = state.population * 0.35;

    return {
      resources: {
        gold: 8 + state.population * 0.16 + state.buildings.tavern * 5 + state.reputation * 0.05 - armyUpkeepGold,
        food: state.buildings.farm * 26 + autumnBonus + summerBonus + winterPenalty - populationFood - armyUpkeepFood,
        wood: 8 + state.buildings.lumberMill * 20,
        mana: 5 + state.buildings.mageTower * 16
      },
      morale: state.buildings.tavern * 2 + state.reputation * 0.03 - state.threat * 0.03 + (season === "겨울" ? -2 : 1),
      threat: 4 + state.turn * 0.1 - state.buildings.walls * 2 - state.army * 0.05,
      population: state.resources.food <= 0 ? -3 : state.resources.morale >= 75 ? 2 : 0
    };
  }

  function buildStructure(state, buildingId) {
    const building = buildings[buildingId];

    if (!building) {
      return { state, ok: false, message: "알 수 없는 건물입니다." };
    }

    if (!canPay(state, building.cost)) {
      return { state, ok: false, message: "건설 자원이 부족합니다." };
    }

    spend(state, building.cost);
    state.buildings[buildingId] = (state.buildings[buildingId] || 0) + 1;
    addLog(state, `${building.icon} ${building.name}이(가) 완공되었습니다.`);
    evaluateGameOver(state);
    return { state, ok: true, message: `${building.name} 건설 완료` };
  }

  function applyRandomEvent(state) {
    const candidates = events.filter((event) => !event.condition || event.condition(state));
    const index = Math.floor(random(state) * candidates.length);
    const event = candidates[index] || candidates[0];
    return `[사건: ${event.title}] ${event.run(state)}`;
  }

  function pickAdventurer(state) {
    const sorted = [...state.adventurers].sort((a, b) => {
      if (b.loyalty !== a.loyalty) {
        return b.loyalty - a.loyalty;
      }
      return b.level - a.level;
    });
    return state.adventurers.find((adventurer) => adventurer.name === sorted[0].name);
  }

  function canPay(state, cost) {
    return Object.entries(cost).every(([resource, amount]) => state.resources[resource] >= amount);
  }

  function spend(state, cost) {
    Object.entries(cost).forEach(([resource, amount]) => {
      state.resources[resource] -= amount;
    });
  }

  function evaluateGameOver(state) {
    if (state.population <= 0) {
      state.gameOverReason = "왕국의 인구가 사라졌습니다. 폐허만이 남았습니다.";
    } else if (state.resources.morale <= 0) {
      state.gameOverReason = "민심이 무너져 귀족 의회가 왕관을 빼앗았습니다.";
    } else if (state.threat >= 100) {
      state.gameOverReason = "마왕의 군세가 국경을 넘어 왕국을 삼켰습니다.";
    } else if (state.reputation >= 100 && state.threat <= 10) {
      state.gameOverReason = "당신의 왕국은 대륙의 수호국으로 칭송받는 황금기를 열었습니다.";
    }

    if (state.gameOverReason) {
      addLog(state, state.gameOverReason);
    }
  }

  function addLog(state, message) {
    state.log = [message, ...state.log].slice(0, 30);
  }

  function random(state) {
    const next = (state.rngSeed * 1664525 + 1013904223) >>> 0;
    state.rngSeed = next;
    return next / 4294967296;
  }

  function normalizeSeed(seed) {
    const normalized = Number(seed) >>> 0;
    return normalized === 0 ? 1 : normalized;
  }

  function cloneState(state) {
    return JSON.parse(JSON.stringify(state));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function formatSigned(value) {
    const rounded = Math.round(value);
    return `${rounded >= 0 ? "+" : ""}${rounded}`;
  }

  function formatCost(cost) {
    return Object.entries(cost)
      .map(([resource, amount]) => `${resourceLabels[resource]} ${amount}`)
      .join(", ");
  }

  return {
    seasons,
    buildings,
    resourceLabels,
    createInitialState,
    getSeason,
    getBuildingList,
    getAvailableActions,
    performAction,
    advanceTurn,
    calculateProduction,
    formatCost
  };
});
