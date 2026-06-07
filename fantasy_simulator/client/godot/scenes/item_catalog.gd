extends Control

const ItemUiTheme = preload("res://scripts/ui/item_ui_theme.gd")

@onready var _search: LineEdit = $Root/Margin/VBox/Toolbar/SearchRow/SearchEdit
@onready var _count_label: Label = $Root/Margin/VBox/Header/CountLabel
@onready var _list: ItemList = $Root/Margin/VBox/Body/ListPanel/Margin/List
@onready var _detail: RichTextLabel = $Root/Margin/VBox/Body/DetailPanel/Margin/Detail
@onready var _status: Label = $Root/Margin/VBox/StatusLabel
@onready var _chip_row: HBoxContainer = $Root/Margin/VBox/Toolbar/ChipRow

var _items: Array = []
var _filtered: Array = []
var _category_filter: String = "all"
var _chip_buttons: Dictionary = {}


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	_search.text_changed.connect(_on_search_changed)
	_list.item_selected.connect(_on_item_selected)
	_list.item_activated.connect(_on_item_selected)
	$Root/Margin/VBox/Toolbar/SearchRow/RefreshButton.pressed.connect(_load_catalog)
	$Root/Margin/VBox/Header/BackButton.pressed.connect(_on_back_pressed)
	$Root/Margin/VBox/Header/InventoryButton.pressed.connect(_on_open_inventory_pressed)
	_build_category_chips()
	_apply_list_theme()
	_style_panels()
	if ApiClient.session_id.is_empty():
		_status.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	_load_catalog()


func _style_panels() -> void:
	for panel_name in ["ListPanel", "DetailPanel"]:
		var panel: PanelContainer = $Root/Margin/VBox/Body.get_node(panel_name)
		panel.add_theme_stylebox_override("panel", ItemUiTheme.panel_style())


func _apply_list_theme() -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = ItemUiTheme.PANEL.lightened(0.05)
	sb.set_corner_radius_all(8)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	_list.add_theme_stylebox_override("panel", sb)
	_list.add_theme_font_size_override("font_size", 15)


func _build_category_chips() -> void:
	for child in _chip_row.get_children():
		child.queue_free()
	_chip_buttons.clear()

	var categories: Array[String] = [
		"all", "weapon", "armor", "accessory", "potion", "magic", "material"
	]
	var labels: Dictionary = {
		"all": "전체",
		"weapon": "무기",
		"armor": "방어구",
		"accessory": "장신구",
		"potion": "포션",
		"magic": "마법",
		"material": "재료",
	}
	for cat in categories:
		var btn := Button.new()
		btn.text = labels.get(cat, cat)
		btn.toggle_mode = true
		btn.button_pressed = cat == "all"
		btn.custom_minimum_size = Vector2(72, 34)
		btn.add_theme_font_size_override("font_size", 13)
		_style_chip(btn, cat == "all")
		btn.pressed.connect(_on_chip_pressed.bind(cat, btn))
		_chip_row.add_child(btn)
		_chip_buttons[cat] = btn


func _style_chip(btn: Button, active: bool) -> void:
	var sb := StyleBoxFlat.new()
	sb.set_corner_radius_all(16)
	if active:
		sb.bg_color = ItemUiTheme.ACCENT
		btn.add_theme_color_override("font_color", Color.WHITE)
	else:
		sb.bg_color = ItemUiTheme.PANEL_LIGHT
		btn.add_theme_color_override("font_color", ItemUiTheme.TEXT_DIM)
	btn.add_theme_stylebox_override("normal", sb)
	var sb_hover := sb.duplicate()
	sb_hover.bg_color = sb.bg_color.lightened(0.12)
	btn.add_theme_stylebox_override("hover", sb_hover)
	var sb_pressed := sb.duplicate()
	sb_pressed.bg_color = ItemUiTheme.ACCENT.darkened(0.1)
	btn.add_theme_stylebox_override("pressed", sb_pressed)


func _on_chip_pressed(category: String, btn: Button) -> void:
	_category_filter = category
	for cat in _chip_buttons:
		var chip: Button = _chip_buttons[cat]
		var active := cat == category
		chip.button_pressed = active
		_style_chip(chip, active)
	_apply_filter()


func _load_catalog() -> void:
	_status.text = "도감 불러오는 중..."
	_list.clear()
	_detail.clear()
	var result: Dictionary = await ApiClient.fetch_item_catalog("", "", "", 500)
	if result.is_empty():
		_status.text = "도감 로드 실패"
		_count_label.text = ""
		return
	_items = result.get("items", [])
	var counts: Dictionary = result.get("counts", {})
	_apply_filter()
	_status.text = "총 %s종 아이템 · 클릭하면 상세 정보" % counts.get("total", _items.size())


func _apply_filter() -> void:
	var query := _search.text.strip_edges().to_lower()
	_filtered.clear()
	for item in _items:
		if not item is Dictionary:
			continue
		var cat: String = str(item.get("category", ""))
		if _category_filter != "all" and cat != _category_filter:
			continue
		if query != "":
			var label: String = str(item.get("label", "")).to_lower()
			var item_id: String = str(item.get("item_id", "")).to_lower()
			var desc: String = str(item.get("description", "")).to_lower()
			if query not in label and query not in item_id and query not in desc:
				continue
		_filtered.append(item)
	_refresh_list()


func _refresh_list() -> void:
	_list.clear()
	for item in _filtered:
		var grade: String = str(item.get("grade", "common"))
		var icon := str(item.get("icon", "📦"))
		var label := str(item.get("label", item.get("item_id", "?")))
		var grade_txt := str(item.get("grade_label", ItemUiTheme.grade_label(grade)))
		var idx := _list.add_item("%s %s [%s]" % [icon, label, grade_txt])
		_list.set_item_metadata(idx, item.get("item_id", ""))
		_list.set_item_custom_fg_color(idx, ItemUiTheme.grade_color(grade))
	_count_label.text = "%d / %d 종" % [_filtered.size(), _items.size()]
	if _filtered.is_empty():
		_detail.text = "[center][color=#8899bb]조건에 맞는 아이템이 없습니다.[/color][/center]"
		return
	if _list.get_item_count() > 0:
		_list.select(0)
		_on_item_selected(0)


func _on_search_changed(_text: String) -> void:
	_apply_filter()


func _on_item_selected(index: int) -> void:
	if index < 0:
		return
	var item_id: String = str(_list.get_item_metadata(index))
	var item: Dictionary = _find_item(item_id)
	if item.is_empty():
		item = await ApiClient.fetch_item_detail(item_id)
	_detail.text = ItemUiTheme.detail_bbcode(item)


func _find_item(item_id: String) -> Dictionary:
	for it in _filtered:
		if it is Dictionary and str(it.get("item_id", "")) == item_id:
			return it
	return {}


func _on_open_inventory_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/inventory.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	_status.text += "\n[오류] %s" % message
