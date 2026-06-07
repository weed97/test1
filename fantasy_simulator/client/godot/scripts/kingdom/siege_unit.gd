extends Node2D
## Single siege lane unit — drawn in 2D, marches or holds wall position.

var unit_class: String = "sword"
var side: String = "attacker"
var home_pos: Vector2 = Vector2.ZERO
var march_target: Vector2 = Vector2.ZERO
var alive: bool = true
var unit_color: Color = Color.WHITE
var _bob_phase: float = 0.0


func setup(cls: String, side_name: String, pos: Vector2, col: Color) -> void:
	unit_class = cls
	side = side_name
	position = pos
	home_pos = pos
	march_target = pos
	unit_color = col
	_bob_phase = randf() * TAU
	queue_redraw()


func set_march_target(target: Vector2) -> void:
	march_target = target


func flash_hit() -> void:
	var tw := create_tween()
	tw.tween_property(self, "modulate", Color(2.0, 2.0, 2.0), 0.05)
	tw.tween_property(self, "modulate", Color.WHITE, 0.12)


func _process(delta: float) -> void:
	if not alive:
		return
	if side == "attacker":
		position = position.lerp(march_target, clampf(delta * 2.5, 0.0, 1.0))
	else:
		var bob := sin(Time.get_ticks_msec() * 0.005 + _bob_phase) * 2.0
		position.y = home_pos.y + bob


func _draw() -> void:
	if not alive:
		return
	match unit_class:
		"bow":
			draw_rect(Rect2(-4, -4, 8, 8), unit_color)
			draw_line(Vector2(0, 0), Vector2(6, -6), unit_color.lightened(0.3), 1.5)
		"magic":
			draw_colored_polygon(
				PackedVector2Array([Vector2(0, -6), Vector2(5, 0), Vector2(0, 6), Vector2(-5, 0)]),
				unit_color,
			)
		"beast":
			draw_circle(Vector2.ZERO, 7.0, unit_color)
			draw_circle(Vector2(4, -3), 2.0, Color(0.1, 0.1, 0.1))
		_:
			draw_colored_polygon(
				PackedVector2Array([Vector2(0, -7), Vector2(6, 5), Vector2(-6, 5)]),
				unit_color,
			)
