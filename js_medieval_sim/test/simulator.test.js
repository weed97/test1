const assert = require("node:assert/strict");
const test = require("node:test");

const simulator = require("../simulator");

test("creates a playable initial kingdom", () => {
  const state = simulator.createInitialState({ seed: 100 });

  assert.equal(state.kingdomName, "은빛가시 왕국");
  assert.equal(simulator.getSeason(state), "봄");
  assert.equal(state.resources.gold, 120);
  assert.equal(state.buildings.farm, 1);
  assert.equal(state.adventurers.length, 3);
});

test("building construction spends resources and increments building count", () => {
  const state = simulator.createInitialState({ seed: 100 });
  const result = simulator.performAction(state, "build:farm");

  assert.equal(result.ok, true);
  assert.equal(result.state.buildings.farm, 2);
  assert.equal(result.state.resources.gold, 85);
  assert.equal(result.state.resources.wood, 45);
  assert.equal(state.buildings.farm, 1, "original state remains unchanged");
});

test("unaffordable actions are rejected without changing resources", () => {
  const state = simulator.createInitialState({ seed: 100 });
  state.resources.gold = 0;
  const result = simulator.performAction(state, "build:walls");

  assert.equal(result.ok, false);
  assert.equal(result.state.resources.gold, 0);
  assert.equal(result.state.buildings.walls, 0);
});

test("advancing a turn updates season, resources, and chronicle", () => {
  const state = simulator.createInitialState({ seed: 100 });
  const result = simulator.advanceTurn(state);

  assert.equal(result.state.turn, 2);
  assert.equal(simulator.getSeason(result.state), "여름");
  assert.notEqual(result.state.resources.gold, state.resources.gold);
  assert.ok(result.state.log[0].startsWith("[사건:"));
  assert.ok(result.state.log[1].includes("봄"));
});

test("quest action deterministically improves an adventurer when successful", () => {
  const state = simulator.createInitialState({ seed: 1 });
  state.resources.morale = 100;
  state.threat = 0;

  const result = simulator.performAction(state, "send-quest");

  assert.equal(result.ok, true);
  assert.ok(result.state.resources.gold > state.resources.gold - 10);
  assert.equal(result.state.reputation, 33);
  assert.equal(result.state.adventurers.find((item) => item.name === "미라").level, 2);
});
