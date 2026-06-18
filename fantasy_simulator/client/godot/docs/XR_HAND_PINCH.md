# 손 추적 핀치 — CPoW XR

## 제스처

| 제스처 | 동작 | CPoW 결과 |
|--------|------|-----------|
| **한 손 핀치 → 놓기** | 엄지·검지 붙였다 떼기 | `heat_pinch` / `material_sculpt` 창조 |
| **핀치 강도** | 손가락 거리 | `pinch_strength` → `heat_intensity` 스케일 |
| **양손 핀치** | 양손 동시에 놓기 (0.35s 윈도우) | 마지막 2 오브젝트 **연결** 또는 `dual_hand_pinch` |
| **컨트롤러 트리거** | 폴백 | `controller_trigger` |

## 시뮬레이터 (PC)

- **클릭 홀드** → 핀치 강도 증가 (놓을 때 창조)
- **드래그** → 창조 위치 이동
- **1 / 2** → 열원 / 재료 모드

## OpenXR (Quest)

- Meta Hand Tracking 활성화 필요 (Export: `xr_features/hand_tracking=1`)
- `XRHandTracker` — `HAND_JOINT_THUMB_TIP` ↔ `HAND_JOINT_INDEX_TIP` 거리
- 핀치 중 **발광 구체** 피드백 (`XRHandPinchVisual`)

## 모듈

```
scripts/xr/
  xr_hand_pinch.gd          # 손별 핀치 감지
  xr_hand_pinch_visual.gd   # 핀치 위치 VFX
  xr_creation_controller.gd # 제스처 → Intent
```

## API 페이로드

```json
{
  "gesture": "heat_pinch",
  "pinch_strength": 0.85,
  "intensity": 0.85,
  "pose": {"x": 1.2, "y": 0.5, "z": -0.3},
  "device": {"hand_tracking": true, "device_type": "quest3"}
}
```

Python: `cpow_engine/xr/intent_to_creative_object()` — `pinch_strength`로 열 강도 스케일.
