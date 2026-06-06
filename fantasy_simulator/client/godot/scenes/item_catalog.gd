extends Control

const CATEGORIES := [
	{"id": "", "label": "전체"},
	{"id": "weapon", "label": "무기"},
	{"id": "armor", "label": "방어구"},
	{"id": "accessory", "label": "장신구"},
	{"id": "potion", "label": "물약"},
	{"id": "magic", "label": "마법"},
	{"id": "material", "label": "재료"},
]

var _items: Array = []
var _load_token: int = 0


func _ready() -> void:
	ApiClient.api_error.connect(_on_api_error)
	$VBox/BackButton.pressed.connect(_on_back_pressed)
	$VBox/RefreshButton.pressed.connect(_on_refresh_pressed)
	$VBox/OpenInventoryButton.pressed.connect(_on_open_inventory_pressed)
	_populate_category_filter()
	if ApiClient.session_id.is_empty():
		$VBox/StatusLabel.text = "세션이 없습니다. 메인 메뉴에서 새 게임을 시작하세요."
		return
	await _load_catalog()


func _populate_category_filter() -> void:
	var opt: OptionButton = $VBox/FilterRow/CategoryOption
	opt.clear()
	for i in CATEGORIES.size():
		opt.add_item(CATEGORIES[i]["label"], i)
		opt.set_item_metadata(i, CATEGORIES[i]["id"])
	opt.item_selected.connect(_on_filter_changed)
	$VBox/FilterRow/SearchBox.text_submitted.connect(_on_search_submitted)


func _on_filter_changed(_index: int) -> void:
	_load_catalog()


func _on_search_submitted(_text: String) -> void:
	_load_catalog()


func _on_refresh_pressed() -> void:
	await _load_catalog()


func _load_catalog() -> void:
	_load_token += 1
	var token := _load_token
	$VBox/StatusLabel.text = "도감 불러오는 중…"
	var cat_idx: int = $VBox/FilterRow/CategoryOption.selected
	if cat_idx < 0:
		cat_idx = 0
	var category: String = str($VBox/FilterRow/CategoryOption.get_item_metadata(cat_idx))
	var search: String = $VBox/FilterRow/SearchBox.text.strip_edges()
	var payload: Dictionary = await ApiClient.fetch_item_catalog(category, "", search, 300)
	if token != _load_token:
		return
	if payload.is_empty():
		$VBox/StatusLabel.text = "도감을 불러오지 못했습니다."
		return
	var counts: Dictionary = payload.get("counts", {})
	_items = payload.get("items", [])
	$VBox/StatusLabel.text = "총 %s종 · 표시 %s개" % [
		counts.get("total", "?"),
		payload.get("filtered_count", _items.size()),
	]
	_fill_item_list()


func _fill_item_list() -> void:
	var list: ItemList = $VBox/ItemList
	list.clear()
	for it in _items:
		if not it is Dictionary:
			continue
		var icon := str(it.get("icon", "📦"))
		var label := str(it.get("label", it.get("item_id", "?")))
		var grade := str(it.get("grade_label", it.get("grade", "")))
		var cat := str(it.get("category", ""))
		var idx := list.add_item("%s %s [%s·%s]" % [icon, label, grade, cat])
		list.set_item_metadata(idx, it.get("item_id", ""))


func _on_item_selected(index: int) -> void:
	if index < 0:
		return
	var list: ItemList = $VBox/ItemList
	var item_id: String = str(list.get_item_metadata(index))
	var it: Dictionary = _find_item(item_id)
	if it.is_empty():
		var detail: Dictionary = await ApiClient.fetch_item_detail(item_id)
		it = detail
	_render_detail(it)


func _find_item(item_id: String) -> Dictionary:
	for it in _items:
		if it is Dictionary and str(it.get("item_id", "")) == item_id:
			return it
	return {}


func _render_detail(it: Dictionary) -> void:
	if it.is_empty():
		$VBox/DetailLabel.text = "항목을 선택하세요."
		return
	var lines: PackedStringArray = []
	lines.append("%s %s" % [it.get("icon", "📦"), it.get("label", "?")])
	lines.append("ID: %s" % it.get("item_id", ""))
	lines.append("분류: %s · 등급: %s (%s)" % [
		it.get("category", "?"),
		it.get("grade_label", it.get("grade", "?")),
		it.get("rarity_color", ""),
	])
	if it.get("description"):
		lines.append("")
		lines.append(str(it.get("description")))
	lines.append("")
	if it.get("attack"):
		lines.append("공격력: %s" % it.get("attack"))
	if it.get("defense"):
		lines.append("방어력: %s" % it.get("defense"))
	if it.get("hp_restore"):
		lines.append("HP 회복: %s" % it.get("hp_restore"))
	if it.get("mp_restore"):
		lines.append("MP 회복: %s" % it.get("mp_restore"))
	if it.get("value_gold"):
		lines.append("가치: %s 골드" % it.get("value_gold"))
	if it.get("equippable"):
		lines.append("착용 가능 슬롯: %s" % it.get("slot", "weapon"))
	if it.get("consumable"):
		lines.append("소비 아이템")
	lines.append("")
	lines.append("인벤토리에서 착용/사용하세요.")
	$VBox/DetailLabel.text = "\n".join(lines)


func _on_open_inventory_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/inventory.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _on_api_error(message: String) -> void:
	$VBox/StatusLabel.text += "\n[오류] %s" % message
