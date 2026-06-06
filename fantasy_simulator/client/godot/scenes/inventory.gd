extends Control

var _heroes: Dictionary = {}
var _inventory: Dictionary = {}
var _owned_ids: Array = []
var _consumables: Dictionary = {}
var _selected_item_id: String = ""
var _item_cache: Dictionary = {}


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	$VBox/BackButton.pressed.connect(_on_back_pressed)
	$VBox/CatalogButton.pressed.connect(_on_catalog_pressed)
	$VBox/ActionRow/EquipButton.pressed.connect(_on_equip_pressed)
	$VBox/ActionRow/UseButton.pressed.connect(_on_use_pressed)
	$VBox/ActionRow/StarterPackButton.pressed.connect(_on_starter_pack_pressed)
	if ApiClient.session_id.is_empty():
		$VBox/StatusLabel.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	await _reload_all()


func _current_character_id() -> String:
	var opt: OptionButton = $VBox/CharacterOption
	if opt.item_count == 0:
		return "gareth_ironshield"
	var sel := opt.selected
	if sel < 0:
		sel = 0
	return str(opt.get_item_metadata(sel))


func _reload_all() -> void:
	$VBox/StatusLabel.text = "인벤토리 불러오는 중…"
	var status: Dictionary = await ApiClient.fetch_progression_status()
	var catalog: Dictionary = await ApiClient.fetch_item_catalog("", "", "", 500)
	_heroes = status.get("heroes", {})
	_inventory = catalog.get("inventory", {})
	_owned_ids = list(_inventory.get("equipment_owned", []))
	_consumables = _inventory.get("consumables", {})
	_item_cache.clear()
	for it in catalog.get("items", []):
		if it is Dictionary:
			_item_cache[str(it.get("item_id", ""))] = it
	await _populate_characters()
	_refresh_lists()
	_refresh_equipped()
	var total_items := int(catalog.get("counts", {}).get("total", 0))
	$VBox/StatusLabel.text = "도감 %s종 · 보유 장비 %d · 소비 %d" % [
		total_items,
		_owned_ids.size(),
		_consumables.size(),
	]


func _populate_characters() -> void:
	var opt: OptionButton = $VBox/CharacterOption
	if opt.item_selected.is_connected(_on_character_changed):
		opt.item_selected.disconnect(_on_character_changed)
	opt.clear()
	if _heroes.is_empty():
		opt.add_item("gareth_ironshield", 0)
		opt.set_item_metadata(0, "gareth_ironshield")
	else:
		var i := 0
		for cid in _heroes.keys():
			opt.add_item(str(cid), i)
			opt.set_item_metadata(i, cid)
			i += 1
	if not opt.item_selected.is_connected(_on_character_changed):
		opt.item_selected.connect(_on_character_changed)


func _on_character_changed(_index: int) -> void:
	_refresh_equipped()
	_clear_detail()


func _refresh_equipped() -> void:
	var cid := _current_character_id()
	var hero: Dictionary = _heroes.get(cid, {})
	var eq: Dictionary = hero.get("equipment", {})
	var lines: PackedStringArray = ["[%s 장착]" % cid]
	for slot in ["weapon", "armor", "accessory", "trinket"]:
		var iid: String = str(eq.get(slot, ""))
		if iid.is_empty():
			lines.append("  %s: (비어 있음)" % slot)
		else:
			lines.append("  %s: %s" % [slot, _label_for(iid)])
	$VBox/EquippedLabel.text = "\n".join(lines)


func _refresh_lists() -> void:
	var owned_list: ItemList = $VBox/OwnedList
	var cons_list: ItemList = $VBox/ConsumableList
	owned_list.clear()
	cons_list.clear()
	for iid in _owned_ids:
		var idx := owned_list.add_item(_label_for(str(iid)))
		owned_list.set_item_metadata(idx, str(iid))
	for iid in _consumables.keys():
		var cnt: int = int(_consumables[iid])
		var idx := cons_list.add_item("%s x%d" % [_label_for(str(iid)), cnt])
		cons_list.set_item_metadata(idx, str(iid))
	if owned_list.item_selected.is_connected(_on_owned_selected):
		owned_list.item_selected.disconnect(_on_owned_selected)
	if cons_list.item_selected.is_connected(_on_consumable_selected):
		cons_list.item_selected.disconnect(_on_consumable_selected)
	owned_list.item_selected.connect(_on_owned_selected)
	cons_list.item_selected.connect(_on_consumable_selected)


func _label_for(item_id: String) -> String:
	if _item_cache.has(item_id):
		var it: Dictionary = _item_cache[item_id]
		return "%s %s" % [it.get("icon", "📦"), it.get("label", item_id)]
	return item_id


func _on_owned_selected(index: int) -> void:
	if index < 0:
		return
	_selected_item_id = str($VBox/OwnedList.get_item_metadata(index))
	_show_item_actions(true, false)


func _on_consumable_selected(index: int) -> void:
	if index < 0:
		return
	_selected_item_id = str($VBox/ConsumableList.get_item_metadata(index))
	_show_item_actions(false, true)


func _show_item_actions(can_equip: bool, can_use: bool) -> void:
	$VBox/ActionRow/EquipButton.disabled = not can_equip
	$VBox/ActionRow/UseButton.disabled = not can_use
	if _selected_item_id.is_empty():
		$VBox/DetailLabel.text = ""
		return
	var it: Dictionary = _item_cache.get(_selected_item_id, {})
	if it.is_empty():
		it = await ApiClient.fetch_item_detail(_selected_item_id)
		if not it.is_empty():
			_item_cache[_selected_item_id] = it
	_render_detail(it)


func _render_detail(it: Dictionary) -> void:
	if it.is_empty():
		$VBox/DetailLabel.text = _selected_item_id
		return
	var lines: PackedStringArray = [
		"%s %s" % [it.get("icon", "📦"), it.get("label", _selected_item_id)],
		"등급: %s · %s" % [it.get("grade_label", it.get("grade", "?")), it.get("category", "")],
	]
	if it.get("description"):
		lines.append(str(it.get("description")))
	$VBox/DetailLabel.text = "\n".join(lines)


func _clear_detail() -> void:
	_selected_item_id = ""
	$VBox/DetailLabel.text = ""
	$VBox/ActionRow/EquipButton.disabled = true
	$VBox/ActionRow/UseButton.disabled = true


func _on_equip_pressed() -> void:
	if _selected_item_id.is_empty():
		return
	var cid := _current_character_id()
	var result: Dictionary = await ApiClient.equip_item(cid, _selected_item_id)
	if result.get("ok", false) or result.has("slot"):
		$VBox/StatusLabel.text = "착용: %s → %s" % [_selected_item_id, result.get("slot", "?")]
		var status: Dictionary = await ApiClient.fetch_progression_status()
		_heroes = status.get("heroes", {})
		_refresh_equipped()
	else:
		$VBox/StatusLabel.text = "착용 실패: %s" % result.get("error", "unknown")


func _on_use_pressed() -> void:
	if _selected_item_id.is_empty():
		return
	var cid := _current_character_id()
	var result: Dictionary = await ApiClient.use_item(cid, _selected_item_id)
	if result.get("ok", false):
		$VBox/StatusLabel.text = "사용: %s · 효과 %s" % [
			result.get("label", _selected_item_id),
			str(result.get("effects", {})),
		]
		await _reload_all()
	else:
		$VBox/StatusLabel.text = "사용 실패: %s" % result.get("error", "unknown")


func _on_starter_pack_pressed() -> void:
	$VBox/StatusLabel.text = "시작 패키지 지급 중…"
	var pack := [
		["iron_sword", 1],
		["leather_vest", 1],
		["minor_heal_potion", 3],
		["mana_potion", 2],
	]
	for entry in pack:
		await ApiClient.grant_item(str(entry[0]), int(entry[1]))
	await _reload_all()
	$VBox/StatusLabel.text += " 완료"


func _on_catalog_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/item_catalog.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	$VBox/StatusLabel.text += "\n[오류] %s" % message
