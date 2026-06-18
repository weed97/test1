extends Camera3D
## 데스크톱 XR 시뮬레이터 — WASD + 마우스 룩.

const MOVE_SPEED := 4.0
const MOUSE_SENS := 0.002

var _yaw: float = 0.0
var _pitch: float = -0.2


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var mm := event as InputEventMouseMotion
		_yaw -= mm.relative.x * MOUSE_SENS
		_pitch = clampf(_pitch - mm.relative.y * MOUSE_SENS, -1.4, 1.2)
		rotation = Vector3(_pitch, __yaw, 0.0)
	if event is InputEventKey:
		var key := event as InputEventKey
		if key.pressed and key.keycode == KEY_TAB:
			Input.mouse_mode = (
				Input.MOUSE_MODE_VISIBLE
				if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
				else Input.MOUSE_MODE_CAPTURED
			)


func _physics_process(delta: float) -> void:
	var input_dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var direction := (
		(transform.basis * Vector3(input_dir.x, 0.0, input_dir.y)).normalized()
	)
	if direction.length_squared() > 0.0:
		global_position += direction * MOVE_SPEED * delta
