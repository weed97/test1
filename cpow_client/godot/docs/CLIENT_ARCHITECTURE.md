# CPoW Godot Client Architecture

## 목표

유저가 **협업으로 만든 에리어**를 3D로 보고, VRoid 아바타에 크리에이터 판매 glb를 장착하는 클라이언트.  
Eldoria 2D RPG(`fantasy_simulator`)와 코드·씬·API 경로를 **완전히 분리**합니다.

```
┌─────────────────────┐     /v1/areas/*      ┌──────────────────────┐
│  cpow_client/godot  │ ◄──────────────────► │ fantasy_simulator/api │
│  (표현·입력)         │                      │ + cpow_engine/areas   │
└──────────┬──────────┘                      └──────────────────────┘
           │
    ┌──────┴──────┬──────────────┐
    │ AreaViewer  │ PlayerAvatar │ EquipmentManager
    │ (월드 배치)  │ (VRoid 루트)  │ (glb bone attach)
    └─────────────┴──────────────┘
```

## 씬 흐름

```
boot.tscn → main_menu.tscn → area_viewer.tscn
                │                    │
                │ list/found/join    │ fetch_state, create
                └──── AreasClient ───┘
```

## API 계약

| 클라이언트 메서드 | HTTP | 용도 |
|------------------|------|------|
| `list_areas()` | `GET /v1/areas/list` | 에리어 목록 |
| `found_area()` | `POST /v1/areas/found` | 개척 |
| `join_area()` | `POST /v1/areas/join` | 입장 |
| `fetch_state()` | `GET /v1/areas/state` | 오브젝트 동기화 |
| `create_object()` | `POST /v1/areas/create` | 창조 제출 |
| `register_identity()` | `POST /v1/identity/register` | 1인1계정 (거버넌스) |

**호출하지 않음**: `/v1/session/new`, `/v1/turn`, `/v1/catalog/*`

## Visual 파이프라인 (VRoid + glb)

### 1. 아바타 (slot: `avatar`)

- VRoid Studio → VRM export → Godot `GLTFDocument` 또는 VRM 플러그인
- `PlayerAvatar.set_avatar_glb(path)` 로 스왑
- 기본: 캡슐 placeholder (`player_avatar.tscn`)

### 2. 장비 (slot: `weapon` | `movement` | `accessory`)

크리에이터가 에리어 내에서 판매하는 glb:

```json
{
  "label": "creator_katana",
  "visual": {
    "glb_url": "user://market/katana.glb",
    "slot": "weapon",
    "attach_bone": "RightHand"
  },
  "properties": [
    {"name": "heat_intensity", "value": 0},
    {"name": "creator_item", "value": 1, "unit": "listed"}
  ]
}
```

`EquipmentManager`:

1. `VisualObject.from_object_dict()` 파싱
2. glb 로드 (로컬 `res://` / `user://`; HTTP는 캐시 레이어 예정)
3. `BoneAttachment3D` 또는 이름 매칭 bone에 parent

### 3. 월드 프롭 (slot: `world_prop`)

`AreaObjectRenderer`가 `state.objects`를 그리드에 배치.  
glb URL이 있으면 색상 구분 placeholder(현재) → 이후 `GLTFDocument` 인스턴스.

## 엔진 측 스키마

Python `cpow_engine/models.py`:

- `ObjectVisual` — `glb_url`, `slot`, `attach_bone`, `offset`
- `CreativeObject.visual` — 선택 필드
- 레거시: `visual_glb_url` 등 property `unit` 문자열

헬퍼: `cpow_engine/visual/extract_visual(obj)`

## 마켓플레이스 (다음 단계)

아직 클라이언트에 없음. 서버 설계 방향:

- 에리어 스코프 상품 목록 API
- 20% 플랫폼 / 80% 크리에이터 정산
- 구매 시 `visual` 메타가 붙은 `CreativeObject` 인벤토리 반영

## XR

Eldoria `world_xr.tscn`의 핀치 창조는 **레거시 XR 슬라이스**입니다.  
CPoW 클라이언트 XR은 별도 마일스톤 — 동일 `AreasClient.create_object({intent: ...})`로 통합 가능.

## 개발 체크리스트

- [x] 독립 Godot 프로젝트 `cpow_client/godot`
- [x] `/v1/areas/*` 전용 `AreasClient`
- [x] `ObjectVisual` 엔진 스키마
- [x] `equipment_manager.gd` + `player_avatar.tscn` 골격
- [ ] HTTP glb 캐시 (`user://cache/`)
- [ ] VRM import 플러그인 연동
- [ ] 크리에이터 마켓 UI
- [ ] 실제 JWT 세션 (self-reported `user_id` 제거)
