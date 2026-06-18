extends PanelContainer
## Replays siege_simulation.wars[].events sorted by t_ms with barrier/morale HUD.

signal replay_finished(war_id: String)

const CLASS_ICON := {
	"sword": "⚔",
	"bow": "🏹",
	"magic": "✦",
	"beast": "🐾",
}
const CLASS_COLOR := {
	"sword": Color(0.95, 0.55, 0.35),
	"bow": Color(0.55, 0.85, 0.45),
	"magic": Color(0.65, 0.55, 0.95),
	"beast": Color(0.85, 0.7, 0.35),
}

var _playing: bool = false
var _events: Array = []
var _rounds: Array = []
var _event_idx: int = 0
var _barrier_max: int = 12000
var _barrier_hp: int = 12000
var _atk_morale: int = 75
var _def_morale: int = 80
var _round_idx: int = 0
var _war_id: String = ""
var _title: String = ""
var _speed: float = 1.0


@onready var _title_label: Label = $Margin/VBox/TitleLabel
@onready var _barrier_bar: ProgressBar = $Margin/VBox/BarrierRow/BarrierBar
@onready var _barrier_label: Label = $Margin/VBox/BarrierRow/BarrierLabel
@onready var _atk_morale_bar: ProgressBar = $Margin/VBox/MoraleRow/AtkMoraleBar
@onready var _def_morale_bar: ProgressBar = $Margin/VBox/MoraleRow/DefMoraleBar
@onready var _atk_morale_label: Label = $Margin/VBox/MoraleRow/AtkMoraleLabel
@onready var _def_morale_label: Label = $Margin/VBox/MoraleRow/DefMoraleLabel
@onready var _icon_strip: HBoxContainer = $Margin/VBox/IconStrip
@onready var _event_label: Label = $Margin/VBox/EventLabel
@onready var _log: RichTextLabel = $Margin/VBox/EventLog
@onready var _close_btn: Button = $Margin/VBox/ButtonRow/CloseButton
@onready var _skip_btn: Button = $Margin/VBox/ButtonRow/SkipButton


func _ready() -> void:
	_close_btn.pressed.connect(_on_close_pressed)
	_skip_btn.pressed.connect(_on_skip_pressed)
	visible = false


func play_war(war_sim: Dictionary, barrier_max_hp: int = 12000, playback_speed: float = 1.0) -> void:
	if _playing:
		return
	_war_id = str(war_sim.get("war_id", ""))
	_title = "%s → %s" % [
		war_sim.get("attacker_label", "공격군"),
		war_sim.get("defender_name", "왕국"),
	]
	_events = _sorted_events(war_sim.get("events", []))
	_rounds = war_sim.get("rounds", [])
	_barrier_max = max(1, barrier_max_hp)
	_barrier_hp = _barrier_max
	if not _rounds.is_empty():
		var last: Dictionary = _rounds[_rounds.size() - 1]
		_barrier_hp = int(last.get("barrier_hp", war_sim.get("barrier_hp", _barrier_hp)))
	_atk_morale = 75
	_def_morale = 80
	_round_idx = 0
	_event_idx = 0
	_speed = max(0.25, playback_speed)
	_title_label.text = _title
	_log.clear()
	_log.text = ""
	_event_label.text = "공성전 재생 준비…"
	_clear_icons()
	_update_bars()
	visible = true
	_playing = true
	_schedule_next_event(0.0)


func play_simulation(sim: Dictionary, barrier_max_hp: int = 12000) -> void:
	var wars: Array = sim.get("wars", [])
	if wars.is_empty():
		return
	play_war(wars[0], barrier_max_hp)


func _sorted_events(raw: Array) -> Array:
	var out: Array = []
	for ev in raw:
		if ev is Dictionary:
			out.append(ev)
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return int(a.get("t_ms", 0)) < int(b.get("t_ms", 0))
	)
	return out


func _schedule_next_event(delay_sec: float) -> void:
	if not _playing:
		return
	var wait_ms := int(max(0.0, delay_sec) * 1000.0)
	await get_tree().create_timer(wait_ms / _speed).timeout
	if not _playing:
		return
	_advance_one_event()


func _advance_one_event() -> void:
	if _event_idx >= _events.size():
		_finish_replay()
		return

	var ev: Dictionary = _events[_event_idx]
	_event_idx += 1
	_apply_event(ev)
	_sync_round_progress()

	var delay := 0.12
	if _event_idx < _events.size():
		var next_ev: Dictionary = _events[_event_idx]
		var gap_ms := int(next_ev.get("t_ms", 0)) - int(ev.get("t_ms", 0))
		delay = clampf(float(gap_ms) / 1000.0, 0.08, 0.45)
	_schedule_next_event(delay)


func _apply_event(ev: Dictionary) -> void:
	var kind: String = str(ev.get("kind", ""))
	var text: String = str(ev.get("text", ""))
	_event_label.text = text

	if kind == "barrier_break":
		_barrier_hp = 0
		_def_morale = max(0, _def_morale - 12)
		_flash_icon("magic", Color(1.0, 0.25, 0.25))
	elif ev.has("class"):
		var cls: String = str(ev.get("class", ""))
		var side: String = str(ev.get("side", ""))
		_flash_icon(cls, CLASS_COLOR.get(cls, Color.WHITE))
		if side == "attacker":
			_atk_morale = min(100, _atk_morale + 1)
			_def_morale = max(0, _def_morale - 1)
		elif side == "defender":
			_def_morale = min(100, _def_morale + 1)
			_atk_morale = max(0, _atk_morale - 1)

	_update_bars()
	if not text.is_empty():
		_log.append_text(text + "\n")


func _sync_round_progress() -> void:
	if _rounds.is_empty():
		return
	var progress := float(_event_idx) / float(maxi(_events.size(), 1))
	var target_idx := mini(int(progress * float(_rounds.size())), _rounds.size() - 1)
	if target_idx <= _round_idx:
		return
	for i in range(_round_idx, target_idx + 1):
		var rd: Dictionary = _rounds[i]
		var net := int(rd.get("net", 0))
		if net > 0:
			_atk_morale = min(100, _atk_morale + 2)
			_def_morale = max(0, _def_morale - 5)
		else:
			_atk_morale = max(0, _atk_morale - 6)
			_def_morale = min(100, _def_morale + 3)
		_barrier_hp = int(rd.get("barrier_hp", _barrier_hp))
	_round_idx = target_idx
	_update_bars()


func _flash_icon(cls: String, color: Color) -> void:
	_clear_icons()
	var lbl := Label.new()
	lbl.text = CLASS_ICON.get(cls, "•")
	lbl.add_theme_font_size_override("font_size", 28)
	lbl.modulate = color
	_icon_strip.add_child(lbl)


func _clear_icons() -> void:
	for child in _icon_strip.get_children():
		child.queue_free()


func _update_bars() -> void:
	_barrier_bar.max_value = _barrier_max
	_barrier_bar.value = _barrier_hp
	_barrier_label.text = "결계 %d / %d" % [_barrier_hp, _barrier_max]
	_atk_morale_bar.max_value = 100
	_atk_morale_bar.value = _atk_morale
	_atk_morale_label.text = "공격 사기 %d" % _atk_morale
	_def_morale_bar.max_value = 100
	_def_morale_bar.value = _def_morale
	_def_morale_label.text = "수비 사기 %d" % _def_morale


func _finish_replay() -> void:
	_playing = false
	_event_label.text = "공성전 재생 완료"
	replay_finished.emit(_war_id)


func _on_skip_pressed() -> void:
	if not _playing:
		return
	while _event_idx < _events.size():
		_apply_event(_events[_event_idx])
		_event_idx += 1
	for rd in _rounds.slice(_round_idx):
		if rd is Dictionary:
			_barrier_hp = int(rd.get("barrier_hp", _barrier_hp))
	_round_idx = _rounds.size()
	_update_bars()
	_finish_replay()


func _on_close_pressed() -> void:
	_playing = false
	visible = false
