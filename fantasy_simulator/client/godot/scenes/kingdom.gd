extends Control

var _status: Dictionary = {}
var _wars: Dictionary = {}
var _selected_doctrine_id: String = "feudal_balance"
var _busy: bool = false


@onready var _status_label: Label = $VBox/StatusLabel
@onready var _summary: RichTextLabel = $VBox/Summary
@onready var _founding_panel: PanelContainer = $VBox/FoundingPanel
@onready var _founding_checks: RichTextLabel = $VBox/FoundingPanel/Margin/FoundingVBox/FoundingChecks
@onready var _kingdom_name: LineEdit = $VBox/FoundingPanel/Margin/FoundingVBox/FoundingForm/KingdomName
@onready var _decree_input: LineEdit = $VBox/DoctrinePanel/Margin/DoctrineVBox/DecreeInput
@onready var _doctrine_grid: GridContainer = $VBox/DoctrinePanel/Margin/DoctrineVBox/DoctrineGrid
@onready var _apply_doctrine_btn: Button = $VBox/DoctrinePanel/Margin/DoctrineVBox/ApplyDoctrineButton
@onready var _found_btn: Button = $VBox/FoundingPanel/Margin/FoundingVBox/FoundBtn
@onready var _manage_panel: PanelContainer = $VBox/ManagePanel
@onready var _manage_info: RichTextLabel = $VBox/ManagePanel/Margin/ManageVBox/ManageInfo
@onready var _fortify_row: HBoxContainer = $VBox/ManagePanel/Margin/ManageVBox/FortifyRow
@onready var _interior_row: HBoxContainer = $VBox/ManagePanel/Margin/ManageVBox/InteriorRow
@onready var _recruit_row: HBoxContainer = $VBox/ManagePanel/Margin/ManageVBox/RecruitRow
@onready var _wars_label: RichTextLabel = $VBox/WarsLabel
@onready var _siege_battle: PanelContainer = $VBox/SiegeBattleHost/SiegeBattle
@onready var _refresh_btn: Button = $VBox/TopRow/RefreshButton
@onready var _back_btn: Button = $VBox/TopRow/BackButton


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	_refresh_btn.pressed.connect(_on_refresh_pressed)
	_back_btn.pressed.connect(_on_back_pressed)
	_found_btn.pressed.connect(_on_found_pressed)
	_apply_doctrine_btn.pressed.connect(_on_apply_doctrine_pressed)
	if ApiClient.session_id.is_empty():
		_status_label.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	await _reload_all()


func _reload_all() -> void:
	_busy = true
	_status_label.text = "왕국 정보 불러오는 중…"
	_status = await ApiClient.fetch_kingdom_status()
	_wars = await ApiClient.fetch_kingdom_wars()
	_busy = false
	if _status.is_empty():
		_status_label.text = "왕국 API 응답 없음"
		return
	_render_all()


func _render_all() -> void:
	var is_kingdom: bool = bool(_status.get("is_kingdom", false))
	var gold: int = int(_status.get("party_gold", 0))
	_status_label.text = "보유 골드 %sG · %s" % [
		_format_num(gold),
		"왕국 운영 중" if is_kingdom else "왕국 미건설",
	]
	_render_summary(is_kingdom)
	_founding_panel.visible = not is_kingdom
	_manage_panel.visible = is_kingdom
	_apply_doctrine_btn.visible = is_kingdom
	var mon: Dictionary = _status.get("monarchy", {})
	var active_doc: Dictionary = mon.get("doctrine", {})
	if not active_doc.is_empty():
		_selected_doctrine_id = str(active_doc.get("doctrine_id", _selected_doctrine_id))
		_decree_input.text = str(active_doc.get("custom_decree", ""))
	_build_doctrine_cards(_status.get("available_doctrines", []))
	if not is_kingdom:
		_render_founding()
	else:
		_render_management()
	_render_wars()
	_sync_live_siege_panel()


func _sync_live_siege_panel() -> void:
	var live: Variant = _wars.get("siege_live")
	if not live is Dictionary or live.is_empty():
		return
	if not _siege_battle.visible:
		_siege_battle.open_live(live)
	else:
		_siege_battle.sync_live(live)


func _render_summary(is_kingdom: bool) -> void:
	var lines: PackedStringArray = []
	if is_kingdom:
		var charter: Dictionary = _status.get("charter", {})
		var barrier: Dictionary = charter.get("barrier", {})
		var defense: Dictionary = _status.get("defense_summary", {})
		var mon: Dictionary = _status.get("monarchy", {})
		var doctrine: Dictionary = mon.get("doctrine", {})
		lines.append("[b]%s[/b]" % charter.get("name", "왕국"))
		lines.append(
			"결계 %s / %s (%s%%) · 안정 %s" % [
				_format_num(int(barrier.get("hp", 0))),
				_format_num(int(barrier.get("max_hp", 0))),
				_status.get("barrier_pct", "?"),
				charter.get("stability", "?"),
			]
		)
		lines.append(
			"왕정: %s — %s" % [
				doctrine.get("label", "?"),
				mon.get("decree_text", ""),
			]
		)
		lines.append(
			"방어 등급 %s · 성벽 Lv%s · 포탑 %s기" % [
				defense.get("rating", "?"),
				_status.get("fortifications", {}).get("walls_level", 0),
				_status.get("fortifications", {}).get("tower_count", 0),
			]
		)
		var upkeep: Dictionary = _status.get("upkeep", {})
		lines.append("유지비 턴당 %sG · 식량 %s" % [upkeep.get("gold", "?"), upkeep.get("food", "?")])
	else:
		var preview: Dictionary = _status.get("founding_preview", {})
		lines.append("[b]왕국 선포 미완료[/b]")
		lines.append(
			"예상 비용 %sG (직접 %s + 부대비 %s)" % [
				_format_num(int(preview.get("gold_cost_total", 0))),
				_format_num(int(preview.get("gold_cost_direct", 0))),
				_format_num(int(preview.get("gold_cost_ancillary", 0))),
			]
		)
		lines.append(str(preview.get("ancillary_note", "")))
	_summary.text = "\n".join(lines)


func _render_founding() -> void:
	var preview: Dictionary = _status.get("founding_preview", {})
	var checks: Array = preview.get("checks", [])
	var check_lines: PackedStringArray = []
	for c in checks:
		if not c is Dictionary:
			continue
		var mark := "✓" if c.get("ok", false) else "✗"
		check_lines.append("%s %s" % [mark, _check_label(c)])
	_founding_checks.text = "\n".join(check_lines)
	_found_btn.disabled = not bool(preview.get("can_found", false)) or _busy


func _check_label(c: Dictionary) -> String:
	match str(c.get("id", "")):
		"construction_level":
			return "건축 Lv%s (필요 %s)" % [c.get("have", "?"), c.get("need", "?")]
		"buildings":
			if c.get("ok", false):
				return "필수 건물 완료"
			return "미완공: %s" % ", ".join(c.get("missing", []))
		"workers":
			return "고용 인력 %s / %s" % [c.get("have", "?"), c.get("need", "?")]
		"gold":
			return "골드 %s / %s" % [_format_num(int(c.get("have", 0))), _format_num(int(c.get("need", 0)))]
		"materials":
			return "자재" if c.get("ok", false) else "자재 부족"
		"not_kingdom":
			return "왕국 미건설" if c.get("ok", false) else str(c.get("error", "이미 왕국"))
		_:
			return str(c.get("id", "?"))


func _build_doctrine_cards(doctrines: Array) -> void:
	for child in _doctrine_grid.get_children():
		child.queue_free()
	for d in doctrines:
		if not d is Dictionary:
			continue
		var did := str(d.get("id", ""))
		var card := _make_doctrine_card(d, did)
		_doctrine_grid.add_child(card)
		if did == _selected_doctrine_id:
			card.button_pressed = true


func _make_doctrine_card(d: Dictionary, did: String) -> Button:
	var btn := Button.new()
	btn.toggle_mode = true
	btn.custom_minimum_size = Vector2(200, 90)
	btn.text = "%s\n%s" % [d.get("label", "?"), d.get("motto", "")]
	btn.tooltip_text = str(d.get("description", ""))
	btn.set_meta("doctrine_id", did)
	btn.pressed.connect(_on_doctrine_card_pressed.bind(btn))
	return btn


func _on_doctrine_card_pressed(btn: Button) -> void:
	_selected_doctrine_id = str(btn.get_meta("doctrine_id", "feudal_balance"))
	for child in _doctrine_grid.get_children():
		if child is Button and child != btn:
			(child as Button).button_pressed = false
	btn.button_pressed = true


func _render_management() -> void:
	var charter: Dictionary = _status.get("charter", {})
	var interior: Dictionary = _status.get("interior", {})
	var mil: Dictionary = charter.get("military", {})
	var lines: PackedStringArray = [
		"군사 %s / %s (정찰 %s · 경비 %s · 궁수 %s · 정예 %s)" % [
			_status.get("military_total", 0),
			_status.get("military_cap", "?"),
			mil.get("scout", 0),
			mil.get("guard", 0),
			mil.get("wall_archer", 0),
			mil.get("elite", 0),
		],
		"농경지 %s · 도시 Lv%s · 훈련소 Lv%s" % [
			interior.get("farmland_plots", 0),
			interior.get("city_level", 0),
			interior.get("training_ground_level", 0),
		],
	]
	_manage_info.text = "\n".join(lines)
	_wire_action_buttons()


func _wire_action_buttons() -> void:
	_clear_row(_fortify_row)
	_add_action(_fortify_row, "성벽 강화", _on_fortify.bind("walls"))
	_add_action(_fortify_row, "포탑 건설", _on_fortify.bind("tower"))
	_add_action(_fortify_row, "결계 의식", _on_fortify.bind("barrier_ritual"))
	_clear_row(_interior_row)
	_add_action(_interior_row, "농경지", _on_interior.bind("farmland"))
	_add_action(_interior_row, "도시 구역", _on_interior.bind("city_district"))
	_add_action(_interior_row, "훈련소", _on_interior.bind("training_ground"))
	_clear_row(_recruit_row)
	_add_action(_recruit_row, "정찰병 +1", _on_recruit.bind("scout", 1))
	_add_action(_recruit_row, "경비병 +1", _on_recruit.bind("guard", 1))
	_add_action(_recruit_row, "성벽궁수 +1", _on_recruit.bind("wall_archer", 1))
	_add_action(_recruit_row, "정예 +1", _on_recruit.bind("elite", 1))


func _clear_row(row: HBoxContainer) -> void:
	for child in row.get_children():
		child.queue_free()


func _add_action(row: HBoxContainer, label: String, cb: Callable) -> void:
	var btn := Button.new()
	btn.text = label
	btn.pressed.connect(cb)
	row.add_child(btn)


func _render_wars() -> void:
	var lines: PackedStringArray = []
	var active: Array = _wars.get("active_sieges", [])
	if active.is_empty():
		lines.append("진행 중인 공성전 없음")
	else:
		for w in active:
			if not w is Dictionary:
				continue
			var atk: Dictionary = w.get("attacker", {})
			var dfn: Dictionary = w.get("defender", {})
			lines.append(
				"⚔ %s → %s (라운드 %s) · 공격 사기 %s · 수비 사기 %s" % [
					atk.get("label", "?"),
					dfn.get("kingdom_name", "?"),
					w.get("round", 0),
					atk.get("morale", "?"),
					dfn.get("morale", "?"),
				]
			)
	_wars_label.text = "\n".join(lines)


func _barrier_max_hp() -> int:
	var charter: Dictionary = _status.get("charter", {})
	if charter.is_empty():
		var preview: Dictionary = _status.get("founding_preview", {})
		var bp: Dictionary = preview.get("barrier_preview", {})
		return int(bp.get("base_max_hp", 12000))
	return int(charter.get("barrier", {}).get("max_hp", 12000))


func _on_apply_doctrine_pressed() -> void:
	if _busy:
		return
	var result: Dictionary = await ApiClient.set_kingdom_doctrine(
		_selected_doctrine_id,
		_decree_input.text.strip_edges(),
	)
	await _run_action(result)


func _on_found_pressed() -> void:
	if _busy:
		return
	_busy = true
	_found_btn.disabled = true
	var name_text := _kingdom_name.text.strip_edges()
	if name_text.is_empty():
		name_text = "플레이어 왕국"
	var result: Dictionary = await ApiClient.start_kingdom_founding(
		name_text,
		_selected_doctrine_id,
		_decree_input.text.strip_edges(),
	)
	_busy = false
	if result.get("ok", false):
		_status_label.text = "왕국 선포 의식이 시작되었습니다. 건설 완료 시 결계가 전개됩니다."
		await _reload_all()
	else:
		_status_label.text = str(result.get("error", "선포 실패"))
		_found_btn.disabled = false


func _on_fortify(upgrade_type: String) -> void:
	await _run_action(await ApiClient.fortify_kingdom(upgrade_type))


func _on_interior(build_type: String) -> void:
	await _run_action(await ApiClient.build_kingdom_interior(build_type))


func _on_recruit(unit_type: String, count: int) -> void:
	await _run_action(await ApiClient.recruit_kingdom_military(unit_type, count))


func _run_action(result: Dictionary) -> void:
	if _busy or result.is_empty():
		return
	_busy = true
	if result.get("ok", false):
		_status_label.text = str(result.get("message", "완료"))
		await _reload_all()
	else:
		_status_label.text = str(result.get("error", "실패"))
	_busy = false


func _on_refresh_pressed() -> void:
	await _reload_all()


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	_status_label.text = "[오류] %s" % message
	_busy = false


func _format_num(n: int) -> String:
	var s := str(n)
	var out := ""
	var count := 0
	for i in range(s.length() - 1, -1, -1):
		if count > 0 and count % 3 == 0:
			out = "," + out
		out = s[i] + out
		count += 1
	return out
