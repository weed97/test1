# Godot 4 OpenXR 설정 체크리스트 — CPoW XR 클라이언트

## 전제

- Godot **4.3+** (프로젝트는 4.6)
- Meta Quest: Android export + Meta Quest Developer 계정
- PCVR: SteamVR 또는 Oculus PC 앱 실행 중

## 1. 프로젝트 설정

1. **Project → Project Settings → XR → OpenXR**
   - Enable OpenXR: `ON`
2. **Rendering**
   - Method: `Forward Plus` (이미 설정됨)
3. **Android** (Quest 빌드 시)
   - Min SDK: 29+
   - XR Mode: `OpenXR`
   - Hand Tracking: `Optional` 또는 `Required`

## 2. 씬 구조 (권장)

```
scenes/xr/
  world_xr.tscn          # 루트
  xr_origin.tscn         # XROrigin3D
  creation_hands.tscn    # 손 추적 + 핀치 감지
scripts/xr/
  xr_creation_controller.gd
  xr_pose_serializer.gd
  xr_comfort.gd          # 비네팅·텔레포트
```

```
WorldXR (Node3D)
└── XROrigin3D
    ├── XRCamera3D
    ├── XRController3D ("left")
    ├── XRController3D ("right")
    └── HandTracking (optional)
```

## 3. 실행 모드

| 모드 | 명령 |
|------|------|
| PCVR 에디터 테스트 | Godot 실행 → OpenXR 런타임 활성 |
| Quest 디바이스 | Android APK export → `adb install` |
| XR 없이 개발 | `xr_meta.device_type = "simulator"` |

## 4. CPoW API 연동

기존 `ApiClient` (`scripts/net/api_client.gd`)에 메서드 추가:

```gdscript
func submit_xr_creation(intent: Dictionary) -> Dictionary:
    return await _post("/v1/xr/creation", intent)
```

서버: `cpow_engine/xr/intent_to_creative_object()` 호출.

## 5. 체크리스트

- [ ] OpenXR 활성화
- [ ] XROrigin3D 씬 생성
- [ ] 핀치/트리거 → XRCreationIntent JSON
- [ ] API `/v1/xr/creation` 연동
- [ ] 서버 틱 결과 → 3D 오브젝트 VFX (열 glow, 연결 빔)
- [ ] Quest APK 빌드 테스트

상세: [../../../docs/XR_INTEGRATION.md](../../../docs/XR_INTEGRATION.md)
