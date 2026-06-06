extends Control

var _load_token: int = 0


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	$VBox/BackButton.pressed.connect(_on_back_pressed)
	if ApiClient.session_id.is_empty():
		$VBox/TreeLabel.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	await _populate_characters()
	await _load_tree()


func _populate_characters() -> void:
	var opt: OptionButton = $VBox/CharacterOption
	if opt.item_selected.is_connected(_on_character_changed):
		opt.item_selected.disconnect(_on_character_changed)
	opt.clear()
	var status: Dictionary = await ApiClient.fetch_progression_status()
	var heroes: Dictionary = status.get("heroes", {})
	if heroes.is_empty():
		opt.add_item("gareth_ironshield", 0)
		opt.set_item_metadata(0, "gareth_ironshield")
	else:
		var i := 0
		for cid in heroes.keys():
			opt.add_item(str(cid), i)
			opt.set_item_metadata(i, cid)
			i += 1
	if not opt.item_selected.is_connected(_on_character_changed):
		opt.item_selected.connect(_on_character_changed)


func _load_tree() -> void:
	_load_token += 1
	var token := _load_token
	$VBox/TreeLabel.text = "스킬 트리 불러오는 중…"
	var opt: OptionButton = $VBox/CharacterOption
	if opt.item_count == 0:
		$VBox/TreeLabel.text = "캐릭터 목록이 비어 있습니다."
		return
	var sel := opt.selected
	if sel < 0:
		sel = 0
	var cid: String = str(opt.get_item_metadata(sel))
	if cid.is_empty():
		cid = opt.get_item_text(sel)
	var tree: Dictionary = await ApiClient.fetch_skill_tree(cid)
	if token != _load_token:
		return
	if tree.has("error"):
		$VBox/TreeLabel.text = "스킬 트리 오류: %s" % tree.get("error", "unknown")
		return
	if tree.is_empty():
		$VBox/TreeLabel.text = (
			"스킬 트리가 비어 있습니다.\n"
			+ "API 서버(uvicorn)가 실행 중인지, 메인 메뉴에서 새 게임(hybrid)을 시작했는지 확인하세요."
		)
		return
	_render_tree(tree)


func _render_tree(payload: Dictionary) -> void:
	var lines: PackedStringArray = []
	var levels: Dictionary = payload.get("levels", {})
	lines.append(
		"캐릭터 Lv%s · 직업 %s Lv%s · 강화 티어 %s" % [
			levels.get("character_level", "?"),
			levels.get("job_id", "?"),
			levels.get("job_level", "?"),
			payload.get("job_skill_enhance_tier", 1),
		]
	)
	lines.append(
		"해금 %s / %s" % [
			payload.get("counts", {}).get("job_unlocked", 0),
			payload.get("counts", {}).get("job_total", 300),
		]
	)
	lines.append("")
	var cats: Dictionary = payload.get("categories", {})
	for cat in cats.keys():
		lines.append("=== %s ===" % cat)
		var entries: Array = cats[cat]
		var shown := 0
		for e in entries:
			if shown >= 12:
				lines.append("  … (%d more)" % (entries.size() - shown))
				break
			var mark := "[✓]" if e.get("unlocked") else "[ ]"
			if e.get("signature"):
				mark = "[★]" + mark
			lines.append(
				"  %s %s (tier %s, power %s)" % [
					mark,
					e.get("label", e.get("skill_id")),
					e.get("tier"),
					e.get("power"),
				]
			)
			shown += 1
		lines.append("")
	var weapon_trees: Dictionary = payload.get("weapon_skills", {})
	if not weapon_trees.is_empty():
		lines.append("=== 무기 숙련 스킬 ===")
		for wclass in weapon_trees.keys():
			lines.append("— %s —" % wclass)
			var entries: Array = weapon_trees[wclass]
			var shown_w := 0
			for e in entries:
				if shown_w >= 8:
					lines.append("  … (%d more)" % (entries.size() - shown_w))
					break
				var mark := "[✓]" if e.get("unlocked") else "[ ]"
				lines.append(
					"  %s %s (tier %s)" % [mark, e.get("label", e.get("skill_id")), e.get("tier")]
				)
				shown_w += 1
			lines.append("")
	var nxt: Array = payload.get("next_unlocks", [])
	if not nxt.is_empty():
		lines.append("--- 다음 해금 ---")
		for n in nxt.slice(0, 5):
			lines.append(
				"  %s ← %s" % [n.get("label", n.get("skill_id")), n.get("unlock_requirements")]
			)
	$VBox/TreeLabel.text = "\n".join(lines)


func _on_character_changed(_index: int) -> void:
	await _load_tree()


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	$VBox/TreeLabel.text += "\n[오류] %s" % message
