# XR Integration — CPoW 시뮬레이션 XR 활용 가이드

## 한 줄 답

**가능합니다.** CPoW 엔진(물리·가치 산정)은 서버에 두고, **XR 클라이언트는 공간 입력·표현**만 담당하는 하이브리드 구조가 맞습니다.  
이미 Godot 4.6 클라이언트가 있으므로 **Godot OpenXR**이 가장 현실적인 경로입니다.

---

## 아키텍처: XR는 "손", 엔진은 "뇌"

```
┌─────────────────────────────────────────────────────────────┐
│  XR Client (Godot OpenXR)                                    │
│  · 헤드셋 6DoF · 손 추적 · 공간 UI                            │
│  · pinch_spawn / draw_connection 제스처                       │
│  · 열원·재료 오브젝트 3D 배치·연결 시각화                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket
                           │ XRCreationIntent JSON
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CPoW Simulation Server (Python)                             │
│  cpow_engine/xr/ → CreativeObject → physics → cpow → chain   │
└─────────────────────────────────────────────────────────────┘
```

**원칙**: XR에서 물리 연산을 하지 않습니다. 손짓 → **창조 의도(Intent)** → 서버가 검증·계산 → 결과를 XR에 다시 표시.

---

## 지원 가능한 XR 기기

| 기기 | 경로 | 비고 |
|------|------|------|
| **Meta Quest 2/3** | Godot OpenXR → Android APK | 가장 현실적 1차 타깃 |
| **PCVR** (SteamVR) | Godot OpenXR → Windows | 개발·디버깅 용이 |
| **Apple Vision Pro** | Godot visionOS (실험) 또는 WebXR | 아직 생태계 초기 |
| **HoloLens / AR 글래스** | Godot XR + AR 모드 | 창조물을 실공간에 오버레이 |
| **데스크톱 시뮬레이터** | Godot XR without HMD | 개발용 (`device_type: simulator`) |

---

## 구현 경로 (3단계)

### Step 1: Godot OpenXR 활성화 (클라이언트)

`fantasy_simulator/client/godot/` 에서:

1. **Project → Project Settings → XR**
   - `XR → OpenXR` 활성화
   - `Rendering Method`: Forward Plus (이미 설정됨)

2. **메인 씬을 3D로 전환**
   - 현재 `exploration.tscn`은 2D — XR용 `scenes/xr/world_xr.tscn` 신규 권장
   - `XROrigin3D` + `XRController3D` (좌/우) + `XRCamera3D`

3. **OpenXR 액션 맵**
   - `trigger_click` → 창조 스폰
   - `grip_click` → 오브젝트 잡기/연결
   - 핀치(손 추적) → `pinch_spawn` 제스처

```gdscript
# scripts/xr/xr_creation_controller.gd (개념 예시)
func _on_pinch_confirmed(hand_pose: Transform3D) -> void:
    var intent := {
        "creator_id": ApiConfig.creator_id,
        "gesture": "pinch_spawn",
        "property_hint": "heat_intensity",
        "intensity": _pinch_strength,
        "pose": _pose_to_dict(hand_pose),
        "device": {"device_type": "quest3", "hand_tracking": true}
    }
    await ApiClient.submit_xr_creation(intent)
```

### Step 2: CPoW XR 브릿지 (서버)

이미 구현됨: `cpow_engine/xr/`

```python
from cpow_engine.xr import XRCreationIntent, intent_to_creative_object
from cpow_engine.engine import SimulationEngine

intent = XRCreationIntent.from_dict(payload)
obj = intent_to_creative_object(intent)
engine.create_object(obj)
delta, score = engine.tick()
```

**제스처 → 속성 매핑**

| XR 제스처 | CPoW 속성 | 결과 |
|-----------|-----------|------|
| `pinch_spawn` + heat | `heat_intensity` | 열원 오브젝트 |
| `material_sculpt` | `material_type` | 재료 오브젝트 |
| `draw_connection` | `connections[]` | 두 오브젝트 연결 |
| 손 움직임 거리·각도 | `spatial_entropy` | CPoW 창조성 보너스 |

### Step 3: API 엔드포인트 추가

`fantasy_simulator/api/server.py` 또는 별도 `cpow_api`에:

```
POST /v1/xr/creation     — XRCreationIntent → CreativeObject 등록
POST /v1/xr/connect    — 두 오브젝트 공간 연결
GET  /v1/xr/world      — 현재 SimulationState (오브젝트 위치·속성)
```

XR 클라이언트는 **60–90fps 렌더**, 서버는 **틱 단위(5–10Hz)** 로 충분합니다.

---

## XR에서 CPoW가 빛나는 이유

1. **공간 창조** — 키보드가 아닌 손으로 열원·재료를 배치 → `heat_intensity` 속성 부여
2. **연결의 물리성** — 두 오브젝트를 손으로 이으면 `connections[]` 생성 → `heat_transfer` 발생
3. **봇 억제 강화** — 손 추적 패턴·공간 엔트로피가 CPoW `bot_risk`에 추가 신호
4. **몰입 = 창조** — "파이어볼 스킬" 대신 손 사이에 열을 **창조**하는 경험

---

## 성능·안전 가이드

| 항목 | 권장 |
|------|------|
| 렌더 FPS | Quest: 72fps, PCVR: 90fps |
| 시뮬레이션 틱 | 5–10 Hz (서버) |
| 네트워크 | Wi-Fi 5GHz, intent 배치 전송 |
| 멀미 방지 | 텔레포트 이동 기본, 비네팅 옵션 |
| 세션 길이 | 20분 단위 휴식 권장 (`xr_meta`) |

스키마: `cpow_engine/config/xr_meta.schema.json`

---

## 개발 순서 (CPoW 로드맵과 정합)

| Phase | XR 작업 |
|-------|---------|
| **1 (지금)** | `cpow_engine/xr/` 브릿지 ✅, `world_xr.tscn` Godot 씬 ✅ |
| **2** | Quest APK — [QUEST_APK_BUILD.md](../fantasy_simulator/client/godot/docs/QUEST_APK_BUILD.md) |
| **3** | Quest APK 빌드, 로컬 Wi-Fi 서버 테스트 |
| **4** | 멀티유저 공간 동기화 (`shared_state` + XR pose) |

**L1 블록체인보다 XR 클라이언트가 먼저입니다.** 창조의 재미가 XR에서 검증된 후, 브릿지로 온체인 등록.

---

## Cursor 프롬프트 예시

> Godot 4 OpenXR로 CPoW 창조 인터페이스를 만든다.  
> 핀치 제스처로 heat_intensity 오브젝트를 공간에 배치하고,  
> POST /v1/xr/creation으로 Python CPoW 엔진에 전송한다.  
> 물리 연산은 서버에서, XR은 표현·입력만.

---

## 관련 파일

- `cpow_engine/xr/__init__.py` — XR Intent → CreativeObject
- `cpow_engine/config/xr_meta.schema.json` — 세션 메타
- `fantasy_simulator/client/godot/` — Godot 클라이언트
- `fantasy_simulator/client/godot/docs/XR_SETUP.md` — OpenXR 설정 체크리스트
