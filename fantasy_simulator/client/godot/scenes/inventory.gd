extends Control

const ItemUiTheme = preload("res://scripts/ui/item_ui_theme.gd")

@onready var _owned_list: ItemList = $Root/Margin/VBox/Body/OwnedPanel/Margin/VBox/List
@onready var _cons_list: ItemList = $Root/Margin/VBox/Body/ConsumablePanel/Margin/VBox/List
@onready var _detail: RichTextLabel = $Root/Margin/VBox/DetailPanel/Margin/Detail
@onready var _status: Label = $Root/Margin/VBox/StatusLabel
@onready var _count_label: Label = $Root/Margin/VBox/Header/CountLabel
@onready var _equipped: RichTextLabel = $Root/Margin/VBox/EquippedPanel/Margin/Equipped
@onready var _char_opt: OptionButton = $Root/Margin/VBox/CharRow/CharacterOption

var _heroes: Dictionary = {}
var _inventory: Dictionary = {}
var _owned_ids: Array = []
var _consumables: Dictionary = {}
var _selected_item_id: String = ""
var _item_cache: Dictionary = {}
var _can_equip: bool = false
var _can_use: bool = false


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	_owned_list.item_selected.connect(_on_owned_selected)
	_owned_list.item_activated.connect(_on_owned_selected)
	_cons_list.item_selected.connect(_on_consumable_selected)
	_cons_list.item_activated.connect(_on_consumable_selected)
	$Root/Margin/VBox/Header/BackButton.pressed.connect(_on_back_pressed)
	$Root/Margin/VBox/Header/CatalogButton.pressed.connect(_on_catalog_pressed)
	$Root/Margin/VBox/Header/RefreshButton.pressed.connect(func(): await _reload_all())
	$Root/Margin/VBox/Actions/EquipButton.pressed.connect(_on_equip_pressed)
	$Root/Margin/VBox/Actions/UseButton.pressed.connect(_on_use_pressed)
	$Root/Margin/VBox/Actions/StarterPackButton.pressed.connect(_on_starter_pack_pressed)
	_apply_list_theme(_owned_list)
	_apply_list_theme(_cons_list)
	_style_panels()
	if ApiClient.session_id.is_empty():
		_status.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	await _reload_all()


func _style_panels() -> void:
	for node_name in ["OwnedPanel", "ConsumablePanel", "DetailPanel", "EquippedPanel"]:
		var panel: PanelContainer = get_node_or_null("Root/Margin/VBox/Body/" + node_name)
		if panel == null:
			panel = get_node_or_null("Root/Margin/VBox/" + node_name)
		if panel:
			panel.add_theme_stylebox_override("panel", ItemUiTheme.panel_style())


func _apply_list_theme(list: ItemList) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = ItemUiTheme.PANEL.lightened(0.05)
	sb.set_corner_radius_all(8)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	list.add_theme_stylebox_override("panel", sb)
	list.add_theme_font_size_override("font_size", 14)


func _current_character_id() -> String:
	if _char_opt.item_count == 0:
		return "gareth_ironshield"
	var sel := _char_opt.selected
	if sel < 0:
		sel = 0
	return str(_char_opt.get_item_metadata(sel))


func _reload_all() -> void:
	_status.text = "인벤토리 불러오는 중..."
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
	_count_label.text = "도감 %d종" % total_items
	_status.text = "보유 장비 %d · 소비 %d종" % [_owned_ids.size(), _consumables.size()]


func _populate_characters() -> void:
	if _char_opt.item_selected.is_connected(_on_character_changed):
		_char_opt.item_selected.disconnect(_on_character_changed)
	_char_opt.clear()
	if _heroes.is_empty():
		_char_opt.add_item("gareth_ironshield", 0)
		_char_opt.set_item_metadata(0, "gareth_ironshield")
	else:
		var i := 0
		for cid in _heroes.keys():
			_char_opt.add_item(str(cid), i)
			_char_opt.set_item_metadata(i, cid)
			i += 1
	if not _char_opt.item_selected.is_connected(_on_character_changed):
		_char_opt.item_selected.connect(_on_character_changed)


func _on_character_changed(_index: int) -> void:
	_refresh_equipped()
	_clear_detail()


func _refresh_equipped() -> void:
	var cid := _current_character_id()
	var hero: Dictionary = _heroes.get(cid, {})
	var eq: Dictionary = hero.get("equipment", {})
	var lines: PackedStringArray = []
	lines.append("[color=#c9a84c][b]%s 장착[/b][/color]" % cid)
	for slot in ["weapon", "armor", "accessory", "trinket"]:
		var iid: String = str(eq.get(slot, ""))
		if iid.is_empty():
			lines.append("  [color=#666]%s[/color]: (비어 있음)" % slot)
		else:
			var it: Dictionary = _item_cache.get(iid, {})
			var col := ItemUiTheme.grade_color(str(it.get("grade", "common"))).to_html(false)
			lines.append(
				"  %s: [color=%s]%s %s[/color]"
				% [slot, col, it.get("icon", "📦"), it.get("label", iid)]
			)
	_equipped.text = "\n".join(lines)


func _refresh_lists() -> void:
	_owned_list.clear()
	_cons_list.clear()
	for iid in _owned_ids:
		var it: Dictionary = _item_cache.get(str(iid), {})
		var grade: String = str(it.get("grade", "common"))
		var idx := _owned_list.add_item(_label_for(str(iid)))
		_owned_list.set_item_metadata(idx, str(iid))
		_owned_list.set_item_custom_fg_color(idx, ItemUiTheme.grade_color(grade))
	for iid in _consumables.keys():
		var it: Dictionary = _item_cache.get(str(iid), {})
		var grade: String = str(it.get("grade", "common"))
		var cnt: int = int(_consumables[iid])
		var idx := _cons_list.add_item("%s x%d" % [_label_for(str(iid)), cnt])
		_cons_list.set_item_metadata(idx, str(iid))
		_cons_list.set_item_custom_fg_color(idx, ItemUiTheme.grade_color(grade))


func _label_for(item_id: String) -> String:
	if _item_cache.has(item_id):
		var it: Dictionary = _item_cache[item_id]
		var grade_txt := str(it.get("grade_label", ItemUiTheme.grade_label(str(it.get("grade", "")))))
		return "%s %s [%s]" % [it.get("icon", "📦"), it.get("label", item_id), grade_txt]
	return item_id


func _on_owned_selected(index: int) -> void:
	if index < 0:
		return
	_selected_item_id = str(_owned_list.get_item_metadata(index))
	_show_item_actions(true, false)


func _on_consumable_selected(index: int) -> void:
	if index < 0:
		return
	_selected_item_id = str(_cons_list.get_item_metadata(index))
	_show_item_actions(false, true)


func _show_item_actions(can_equip: bool, can_use: bool) -> void:
	_can_equip = can_equip
	_can_use = can_use
	$Root/Margin/VBox/Actions/EquipButton.disabled = not can_equip
	$Root/Margin/VBox/Actions/UseButton.disabled = not can_use
	if _selected_item_id.is_empty():
		_detail.text = ""
		return
	var it: Dictionary = _item_cache.get(_selected_item_id, {})
	if it.is_empty():
		it = await ApiClient.fetch_item_detail(_selected_item_id)
		if not it.is_empty():
			_item_cache[_selected_item_id] = it
	if can_use and _consumables.has(_selected_item_id):
		it = it.duplicate(true)
		it["quantity"] = _consumables[_selected_item_id]
	_detail.text = ItemUiTheme.detail_bbcode(it)


func _clear_detail() -> void:
	_selected_item_id = ""
	_detail.text = ""
	_can_equip = false
	_can_use = false
	$Root/Margin/VBox/Actions/EquipButton.disabled = true
	$Root/Margin/VBox/Actions/UseButton.disabled = true


func _on_equip_pressed() -> void:
	if _selected_item_id.is_empty():
		return
	var cid := _current_character_id()
	_status.text = "장착 중..."
	var result: Dictionary = await ApiClient.equip_item(cid, _selected_item_id)
	if result.get("ok", false) or result.has("slot"):
		_status.text = "착용 완료: %s → %s" % [_selected_item_id, result.get("slot", "?")]
		var status: Dictionary = await ApiClient.fetch_progression_status()
		_heroes = status.get("heroes", {})
		_refresh_equipped()
	else:
		_status.text = "착용 실패: %s" % result.get("error", "unknown")


func _on_use_pressed() -> void:
	if _selected_item_id.is_empty():
		return
	var cid := _current_character_id()
	_status.text = "사용 중..."
	var result: Dictionary = await ApiClient.use_item(cid, _selected_item_id)
	if result.get("ok", false):
		_status.text = "사용 완료: %s" % result.get("label", _selected_item_id)
		await _reload_all()
	else:
		_status.text = "사용 실패: %s" % result.get("error", "unknown")


func _on_starter_pack_pressed() -> void:
	_status.text = "시작 패키지 지급 중..."
	var pack := [
		["iron_sword", 1],
		["leather_vest", 1],
		["minor_heal_potion", 3],
		["mana_potion", 2],
	]
	for entry in pack:
		await ApiClient.grant_item(str(entry[0]), int(entry[1]))
	await _reload_all()
	_status.text += " 완료"


func _on_catalog_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/item_catalog.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	_status.text += "\n[오류] %s" % message
