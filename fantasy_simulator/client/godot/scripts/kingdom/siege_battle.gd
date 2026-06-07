extends PanelContainer
## Live 2D siege battlefield — syncs with sim clock, not t_ms replay.

signal battle_ended(war_id: String)

const CLASS_COLOR := {
	"sword": Color(0.95, 0.55, 0.35),
	"bow": Color(0.55, 0.85, 0.45),
	"magic": Color(0.65, 0.55, 0.95),
	"beast": Color(0.85, 0.7, 0.35),
}
const LANES := {"sword": 0, "bow": 1, "magic": 2, "beast": 3}
const BATTLE_W := 600.0
const BATTLE_H := 200.0
const WALL_X := 500.0
const SiegeUnitScript := preload("res://scripts/kingdom/siege_unit.gd")

var _war_id: String = ""
var _live: bool = false
var _barrier_max: int = 12000
var _barrier_hp: int = 12000
var _atk_morale: int = 75
var _def_morale: int = 80
var _phase_id: String = "ranged_duel"
var _phase_label: String = ""
var _assault_pressure: float = 0.0
var _title: String = ""
var _round: int = 0
var _volley_cooldown: float = 0.0
var _units: Array[Node2D] = []
var _projectiles: Array[Dictionary] = []

@onready var _title_label: Label = $Margin/VBox/TitleLabel
@onready var _phase_label_node: Label = $Margin/VBox/PhaseLabel
@onready var _battlefield: Node2D = $Margin/VBox/BattleArea/Battlefield
@onready var _barrier_bar: ProgressBar = $Margin/VBox/BarrierRow/BarrierBar
@onready var _barrier_label: Label = $Margin/VBox/BarrierRow/BarrierLabel
@onready var _atk_morale_bar: ProgressBar = $Margin/VBox/MoraleRow/AtkMoraleBar
@onready var _def_morale_bar: ProgressBar = $Margin/VBox/MoraleRow/DefMoraleBar
@onready var _atk_morale_label: Label = $Margin/VBox/MoraleRow/AtkMoraleLabel
@onready var _def_morale_label: Label = $Margin/VBox/MoraleRow/DefMoraleLabel
@onready var _status_label: Label = $Margin/VBox/StatusLabel
@onready var _close_btn: Button = $Margin/VBox/ButtonRow/CloseButton
@onready var _battle_area: Control = $Margin/VBox/BattleArea


func _ready() -> void:
	_close_btn.pressed.connect(_on_close_pressed)
	visible = false
	_battlefield.battle_host = self


func open_live(live: Dictionary) -> void:
	if live.is_empty():
		return
	_war_id = str(live.get("war_id", ""))
	_title = "%s → %s" % [
		live.get("attacker", {}).get("label", "공격군"),
		live.get("defender", {}).get("kingdom_name", "왕국"),
	]
	_title_label.text = _title
	_live = str(live.get("status", "active")) == "active"
	sync_live(live)
	if _units.is_empty():
		_spawn_armies(live)
	visible = true
	_status_label.text = "실시간 공성전 — 시뮬 시계와 연동"


func sync_live(live: Dictionary) -> void:
	if live.is_empty():
		return
	_round = int(live.get("round", 0))
	_barrier_max = maxi(1, int(live.get("barrier_max", _barrier_max)))
	_barrier_hp = int(live.get("barrier_hp", _barrier_hp))
	var atk: Dictionary = live.get("attacker", {})
	var dfn: Dictionary = live.get("defender", {})
	_atk_morale = int(atk.get("morale", _atk_morale))
	_def_morale = int(dfn.get("morale", _def_morale))
	var phase: Dictionary = live.get("phase", {})
	_phase_id = str(phase.get("id", _phase_id))
	_phase_label = str(phase.get("label", ""))
	_phase_label_node.text = "라운드 %d · %s" % [_round, _phase_label]
	var net := int(live.get("last_net", 0))
	_assault_pressure = clampf(float(net) / 400.0, 0.0, 1.0)
	_update_march_targets()
	_update_bars()
	_battlefield.queue_redraw()
	if str(live.get("status", "")) != "active":
		_on_siege_ended(str(live.get("outcome", "")))


func pulse_events(events: Array) -> void:
	for raw in events:
		if not raw is Dictionary:
			continue
		_pulse_one(raw)


func _pulse_one(ev: Dictionary) -> void:
	var kind: String = str(ev.get("kind", ""))
	if kind == "barrier_break":
		_barrier_hp = 0
		_spawn_barrier_burst()
		_status_label.text = "결계 붕괴!"
		_battlefield.queue_redraw()
		return
	var cls: String = str(ev.get("class", ""))
	var side: String = str(ev.get("side", ""))
	if cls.is_empty():
		return
	_flash_class_units(side, cls)
	if side == "attacker":
		if cls == "bow" or cls == "magic":
			_fire_projectile(cls, side)
		elif cls == "sword" or cls == "beast":
			_assault_pressure = minf(1.0, _assault_pressure + 0.15)
			_update_march_targets()
	var text: String = str(ev.get("text", ""))
	if not text.is_empty():
		_status_label.text = text


func _spawn_armies(live: Dictionary) -> void:
	_clear_units()
	var atk: Dictionary = live.get("attacker", {})
	var dfn: Dictionary = live.get("defender", {})
	_spawn_side_forces("attacker", atk.get("forces", {}), 70.0)
	_spawn_side_forces("defender", dfn.get("forces", {}), WALL_X - 40.0)


func _spawn_side_forces(side: String, forces: Variant, base_x: float) -> void:
	if not forces is Dictionary:
		return
	for cls in forces.keys():
		var count: int = int(forces[cls])
		var visual := _visual_count(count)
		var lane: int = int(LANES.get(str(cls), 0))
		for i in range(visual):
			var u: Node2D = SiegeUnitScript.new()
			var y := 36.0 + float(lane) * 42.0 + float(i % 3) * 5.0
			var x := base_x + float(i / 3) * 14.0
			if side == "attacker":
				x += randf_range(-8.0, 8.0)
			u.setup(str(cls), side, Vector2(x, y), CLASS_COLOR.get(str(cls), Color.WHITE))
			_battlefield.add_child(u)
			_units.append(u)


func _visual_count(force: int) -> int:
	return clampi(int(sqrt(float(maxi(force, 1)))) + force / 25, 2, 20)


func _update_march_targets() -> void:
	var advance := 0.0
	match _phase_id:
		"melee_assault":
			advance = 80.0 * _assault_pressure
		"magic_bombardment":
			advance = 35.0 * _assault_pressure
		_:
			advance = 20.0 * _assault_pressure
	for u in _units:
		if not is_instance_valid(u):
			continue
		if u.side != "attacker":
			continue
		u.set_march_target(Vector2(u.home_pos.x + advance, u.home_pos.y))


func _flash_class_units(side: String, cls: String) -> void:
	for u in _units:
		if not is_instance_valid(u):
			continue
		if u.side == side and u.unit_class == cls:
			u.flash_hit()
			if randf() < 0.35:
				break


func _fire_projectile(cls: String, side: String) -> void:
	var from := Vector2(120.0, 80.0)
	for u in _units:
		if is_instance_valid(u) and u.side == side and u.unit_class == cls:
			from = u.position
			break
	var to := Vector2(WALL_X - 20.0, from.y + randf_range(-20.0, 20.0))
	var col: Color = CLASS_COLOR.get(cls, Color.WHITE)
	_projectiles.append({
		"from": from,
		"to": to,
		"t": 0.0,
		"speed": 2.8 if cls == "bow" else 2.2,
		"color": col,
		"kind": cls,
	})


func _spawn_barrier_burst() -> void:
	for _i in range(8):
		var ang := randf() * TAU
		var spd := randf_range(40.0, 120.0)
		_projectiles.append({
			"from": Vector2(WALL_X - 10.0, 90.0),
			"to": Vector2(WALL_X - 10.0 + cos(ang) * spd, 90.0 + sin(ang) * spd),
			"t": 0.0,
			"speed": 3.5,
			"color": Color(0.5, 0.7, 1.0, 0.9),
			"kind": "shard",
		})


func _process(delta: float) -> void:
	if not _live or not visible:
		return
	_volley_cooldown -= delta
	if _volley_cooldown <= 0.0:
		_volley_cooldown = 0.55
		if _phase_id == "ranged_duel" or _phase_id == "magic_bombardment":
			_fire_projectile("bow" if _phase_id == "ranged_duel" else "magic", "attacker")
	_tick_projectiles(delta)
	_battlefield.queue_redraw()


func _tick_projectiles(delta: float) -> void:
	var remaining: Array[Dictionary] = []
	for p in _projectiles:
		p["t"] = float(p["t"]) + delta * float(p["speed"])
		if float(p["t"]) < 1.0:
			remaining.append(p)
		elif p.get("kind") != "shard":
			_barrier_hp = maxi(0, _barrier_hp - randi_range(2, 12))
			_update_bars()
	_projectiles = remaining


func paint_terrain(canvas: Node2D) -> void:
	canvas.draw_rect(Rect2(0, 0, BATTLE_W, BATTLE_H), Color(0.14, 0.18, 0.12))
	canvas.draw_rect(Rect2(0, BATTLE_H - 28, BATTLE_W, 28), Color(0.22, 0.19, 0.14))
	var wall_h := 70.0 + float(_round) * 0.5
	canvas.draw_rect(Rect2(WALL_X, BATTLE_H - wall_h - 28, 90, wall_h), Color(0.45, 0.42, 0.38))
	canvas.draw_rect(Rect2(WALL_X + 20, BATTLE_H - wall_h - 58, 28, 30), Color(0.38, 0.36, 0.34))
	if _barrier_hp > 0:
		var alpha := clampf(float(_barrier_hp) / float(_barrier_max), 0.25, 0.85)
		var col := Color(0.45, 0.75, 1.0, alpha)
		canvas.draw_arc(
			Vector2(WALL_X - 8, BATTLE_H - 50),
			55.0,
			-PI * 0.55,
			-PI * 0.45,
			24,
			col,
			3.0,
		)
	for p in _projectiles:
		var t := float(p["t"])
		var a: Vector2 = p["from"]
		var b: Vector2 = p["to"]
		var pos := a.lerp(b, t)
		var col: Color = p["color"]
		if p.get("kind") == "magic":
			canvas.draw_circle(pos, 4.0, col)
		elif p.get("kind") == "shard":
			canvas.draw_circle(pos, 2.0, col)
		else:
			canvas.draw_line(pos, pos + Vector2(8, 0), col, 2.0)


func _update_bars() -> void:
	_barrier_bar.max_value = _barrier_max
	_barrier_bar.value = _barrier_hp
	_barrier_label.text = "결계 %d / %d" % [_barrier_hp, _barrier_max]
	_atk_morale_bar.value = _atk_morale
	_atk_morale_label.text = "공격 %d" % _atk_morale
	_def_morale_bar.value = _def_morale
	_def_morale_label.text = "수비 %d" % _def_morale


func _clear_units() -> void:
	for u in _units:
		if is_instance_valid(u):
			u.queue_free()
	_units.clear()
	_projectiles.clear()


func _on_siege_ended(outcome: String) -> void:
	_live = false
	var msg := "공성전 종료"
	match outcome:
		"siege_repelled":
			msg = "공성 격퇴 — 왕국 방어 성공"
		"barrier_broken":
			msg = "결계 붕괴 — 함락 위기"
		"kingdom_endured":
			msg = "장기 공성 끝 — 왕국이 버텼다"
	_status_label.text = msg
	battle_ended.emit(_war_id)


func _on_close_pressed() -> void:
	visible = false
	_live = false
