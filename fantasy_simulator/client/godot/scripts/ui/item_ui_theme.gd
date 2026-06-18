extends RefCounted
class_name ItemUiTheme

## Shared palette for catalog / inventory (dark fantasy codex style).

const BG := Color(0.043, 0.059, 0.102, 1.0)
const PANEL := Color(0.11, 0.14, 0.2, 0.95)
const PANEL_LIGHT := Color(0.16, 0.2, 0.28, 1.0)
const PANEL_BORDER := Color(0.45, 0.36, 0.22, 1.0)
const ACCENT := Color(0.35, 0.55, 0.92, 1.0)
const GOLD := Color(0.91, 0.78, 0.42, 1.0)
const TEXT := Color(0.93, 0.9, 0.84, 1.0)
const TEXT_DIM := Color(0.55, 0.62, 0.78, 1.0)
const MUTED := Color(0.65, 0.6, 0.52, 1.0)

const GRADE_COLORS := {
	"common": Color(0.6, 0.63, 0.65),
	"high": Color(0.25, 0.72, 0.38),
	"rare": Color(0.23, 0.55, 0.96),
	"hero": Color(0.66, 0.33, 0.97),
	"legend": Color(0.96, 0.62, 0.12),
	"mythic": Color(0.94, 0.27, 0.27),
	"demigod": Color(0.99, 0.84, 0.35),
}

const GRADE_LABELS := {
	"common": "일반",
	"high": "고급",
	"rare": "희귀",
	"hero": "영웅",
	"legend": "전설",
	"mythic": "신화",
	"demigod": "준신",
}

const CATEGORY_ICONS := {
	"weapon": "⚔️",
	"armor": "🛡️",
	"accessory": "💍",
	"potion": "🧪",
	"magic": "📜",
	"material": "🪨",
}


static func grade_color(grade: String) -> Color:
	return GRADE_COLORS.get(grade, TEXT)


static func grade_label(grade: String) -> String:
	return GRADE_LABELS.get(grade, grade)


static func panel_style(border: Color = PANEL_BORDER, radius: int = 8) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = PANEL
	s.border_color = border
	s.set_border_width_all(2)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 12
	s.content_margin_right = 12
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	return s


static func list_line(item: Dictionary) -> String:
	var icon := str(item.get("icon", CATEGORY_ICONS.get(item.get("category", ""), "📦")))
	var label := str(item.get("label", item.get("item_id", "?")))
	var grade := str(item.get("grade_label", grade_label(str(item.get("grade", "")))))
	return "%s  %s   · %s" % [icon, label, grade]


static func detail_bbcode(item: Dictionary) -> String:
	if item.is_empty():
		return "[center][color=#8899bb]왼쪽 목록에서 아이템을 선택하세요[/color][/center]"
	var grade: String = str(item.get("grade", "common"))
	var col := grade_color(grade).to_html(false)
	var icon := str(item.get("icon", CATEGORY_ICONS.get(item.get("category", ""), "📦")))
	var label := str(item.get("label", item.get("name", item.get("item_id", "?"))))
	var lines: PackedStringArray = []
	lines.append("[center][font_size=26]%s[/font_size][/center]" % icon)
	lines.append("[center][font_size=20][color=%s]%s[/color][/font_size][/center]" % [col, label])
	lines.append("")
	lines.append(
		"[color=#c9a84c]등급[/color]  [color=%s]%s[/color]   ·   [color=#c9a84c]분류[/color]  %s"
		% [col, item.get("grade_label", grade_label(grade)), _category_ko(str(item.get("category", "")))]
	)
	if item.get("quantity"):
		lines.append("[color=#c9a84c]보유[/color]  x%s" % item.get("quantity"))
	if item.get("description"):
		lines.append("")
		lines.append("[color=#ddd5c8]%s[/color]" % str(item.get("description")))
	lines.append("")
	lines.append("[color=#c9a84c]── 스탯 ──[/color]")
	var stats: Array[String] = []
	if item.get("attack"):
		stats.append("⚔ 공격 %s" % item.get("attack"))
	if item.get("defense"):
		stats.append("🛡 방어 %s" % item.get("defense"))
	if item.get("hp_restore"):
		stats.append("❤ HP +%s" % item.get("hp_restore"))
	if item.get("mp_restore"):
		stats.append("💧 MP +%s" % item.get("mp_restore"))
	if item.get("scroll_damage"):
		stats.append("✨ 마법 피해 %s" % item.get("scroll_damage"))
	if item.get("value_gold"):
		stats.append("🪙 %s 골드" % item.get("value_gold"))
	if stats.is_empty():
		lines.append("[color=#888]—[/color]")
	else:
		for s in stats:
			lines.append("[color=#e8e0d4]  %s[/color]" % s)
	if item.get("equippable"):
		lines.append("")
		lines.append("[color=#7ec8ff]착용 가능 · %s[/color]" % item.get("slot", "weapon"))
	if item.get("consumable"):
		lines.append("[color=#7ec8ff]소비 아이템[/color]")
	lines.append("")
	lines.append("[center][color=#666][i]%s[/i][/color][/center]" % item.get("item_id", ""))
	return "\n".join(lines)


static func _category_ko(cat: String) -> String:
	match cat:
		"weapon":
			return "무기"
		"armor":
			return "방어구"
		"accessory":
			return "장신구"
		"potion":
			return "물약"
		"magic":
			return "마법"
		"material":
			return "재료"
	return cat
