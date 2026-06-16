extends Node3D
## CPoW XR 월드 — OpenXR 또는 데스크톱 시뮬레이터.

@onready var _xr_origin: XROrigin3D = $XROrigin3D
@onready var _xr_camera: XRCamera3D = $XROrigin3D/XRCamera3D
@onready var _sim_camera: Camera3D = $DesktopSimulator/Camera3D
@onready var _objects: Node3D = $CreationObjects
@onready var _creation: XRCreationController = $XRCreationController
@onready var _comfort: XRComfort = $XRComfort
@onready var _hud: Label = $CanvasLayer/HUD
@onready var _log: RichTextLabel = $CanvasLayer/Log
@onready var _beam: MeshInstance3D = $ConnectionBeam

var _xr_running: bool = false
var _object_nodes: Dictionary = {}
var _energy_total: float = 0.0
var _connect_source_id: String = ""


func _ready() -> void:
	_beam.visible = false
	ApiClient.xr_creation_completed.connect(_on_xr_creation_completed)
	ApiClient.api_error.connect(_on_api_error)
	_creation.creation_requested.connect(_on_creation_requested)
	_creation.connect_requested.connect(_on_connect_requested)

	_try_start_xr()
	_comfort.setup(_xr_origin, _active_camera())
	_update_hud()

	if ApiConfig.xr_auto_session:
		await _ensure_session()


func _try_start_xr() -> void:
	var interfaces := XRServer.get_interfaces()
	for iface in interfaces:
		if iface.get_name() == "OpenXR":
			if iface.is_initialized():
				_xr_running = true
				break
			var err := iface.initialize()
			if err == OK:
				_xr_running = true
				break

	_xr_origin.visible = _xr_running
	$DesktopSimulator.visible = not _xr_running

	if _xr_running:
		get_viewport().use_xr = true
		_xr_camera.current = true
		_sim_camera.current = false
		_creation.setup_xr(_xr_origin)
		_log_append("[XR] OpenXR 활성 — 트리거로 창조")
	else:
		_xr_camera.current = false
		_sim_camera.current = true
		_creation.setup_simulator(_sim_camera)
		_log_append("[시뮬레이터] 마우스 클릭으로 창조 (1=열, 2=재료)")


func _active_camera() -> Node3D:
	return _xr_camera if _xr_running else _sim_camera


func _ensure_session() -> void:
	if not ApiClient.session_id.is_empty():
		return
	_log_append("API 세션 생성 중…")
	await ApiClient.new_game(42, "precision")
	if ApiClient.session_id.is_empty():
		_log_append("[경고] API 없음 — 로컬 시각화만 동작")


func _on_creation_requested(intent: Dictionary) -> void:
	var pose: Dictionary = intent.get("pose", {})
	_log_append("창조: %s @ (%.1f, %.1f, %.1f)" % [
		intent.get("label", "?"),
		float(pose.get("x", 0)),
		float(pose.get("y", 0)),
		float(pose.get("z", 0)),
	])
	var result: Dictionary = await ApiClient.submit_xr_creation(intent)
	if result.is_empty():
		_spawn_local_preview(intent, {})
	else:
		_spawn_from_response(result, intent)


func _on_connect_requested(source_id: String, target_id: String, pose: Dictionary) -> void:
	_log_append("연결: %s → %s" % [source_id, target_id])
	await ApiClient.submit_xr_connect(source_id, target_id, pose)
	_draw_connection_beam(source_id, target_id)


func _on_xr_creation_completed(payload: Dictionary) -> void:
	var energy := float(payload.get("energy_minted", payload.get("energy", 0.0)))
	if energy > 0.0:
		_energy_total += energy
	_update_hud()


func _spawn_from_response(result: Dictionary, intent: Dictionary) -> void:
	var obj: Dictionary = result.get("object", {})
	var pose: Dictionary = intent.get("pose", {})
	var node := _spawn_visual(
		str(obj.get("id", "local_%d" % Time.get_ticks_msec())),
		str(intent.get("property_hint", "heat_intensity")),
		Vector3(float(pose.get("x", 0)), float(pose.get("y", 0)), float(pose.get("z", 0))),
		float(result.get("energy", 0.0)),
	)
	if result.has("energy"):
		_energy_total += float(result.get("energy", 0.0))
		_on_xr_creation_completed(result)


func _spawn_local_preview(intent: Dictionary, _extra: Dictionary) -> void:
	var pose: Dictionary = intent.get("pose", {})
	var oid := "local_%d" % Time.get_ticks_msec()
	_spawn_visual(
		oid,
		str(intent.get("property_hint", "heat_intensity")),
		Vector3(float(pose.get("x", 0)), float(pose.get("y", 0)), float(pose.get("z", 0))),
		50.0,
	)


func _spawn_visual(
	object_id: String,
	property_hint: String,
	pos: Vector3,
	energy: float,
) -> XRCreationObject:
	var vis := XRCreationObject.new()
	vis.configure({
		"object_id": object_id,
		"property_hint": property_hint,
		"energy": energy,
	})
	vis.position = pos
	_objects.add_child(vis)
	_object_nodes[object_id] = vis

	if _connect_source_id.is_empty():
		_connect_source_id = object_id
	elif _connect_source_id != object_id:
		_creation.try_connect(_connect_source_id, object_id, Transform3D(Basis.IDENTITY, pos))
		_connect_source_id = object_id
	else:
		_connect_source_id = object_id

	return vis


func _draw_connection_beam(source_id: String, target_id: String) -> void:
	if not _object_nodes.has(source_id) or not _object_nodes.has(target_id):
		return
	var a: Node3D = _object_nodes[source_id]
	var b: Node3D = _object_nodes[target_id]
	var mid := (a.global_position + b.global_position) * 0.5
	var dir := b.global_position - a.global_position
	var length := dir.length()
	if length < 0.01:
		return
	_beam.visible = true
	_beam.global_position = mid
	_beam.look_at(b.global_position, Vector3.UP)
	if _beam.mesh is CylinderMesh:
		(_beam.mesh as CylinderMesh).height = length


func _update_hud() -> void:
	var mode := "열원" if _creation.creation_mode == XRCreationController.CreationMode.HEAT else "재료"
	var xr_label := "OpenXR" if _xr_running else "시뮬레이터"
	_hud.text = "CPoW XR · %s · 모드: %s · NRG: %.1f · 오브젝트: %d" % [
		xr_label, mode, _energy_total, _object_nodes.size(),
	]
	$CanvasLayer/ApiLabel.text = "API: %s" % ApiConfig.base_url()


func _log_append(text: String) -> void:
	_log.text += text + "\n"


func _on_api_error(message: String) -> void:
	_log_append("[오류] %s" % message)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var key := event as InputEventKey
		if key.pressed and not key.echo and key.keycode == KEY_ESCAPE:
			get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
		if key.pressed and not key.echo and key.keycode == KEY_Q:
			_comfort.snap_turn(-1)
		if key.pressed and not key.echo and key.keycode == KEY_E:
			_comfort.snap_turn(1)
		if key.pressed and not key.echo and key.keycode == KEY_T:
			_comfort.teleport_forward()


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
