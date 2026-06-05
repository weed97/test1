# 19 — 공간 시뮬레이션 (Godot 좌표 ↔ 판타지 세계)

## 원칙

| 층 | 권위 | 필드 |
|----|------|------|
| Godot | 연속 픽셀 · 충돌 · 애니 | `CharacterBody2D.position` |
| **Python 시뮬** | 타일 · 존 · POI · 이벤트 | `world.map_id`, `x`, `y`, `zone_id` |
| 콘텐츠 | 메인/씨앗 | `location_zones` = `zone_id` |

**걷기 자체는 Godot.** 타일/존이 바뀔 때 `POST /v1/world/position`.  
탐험·대화는 `POST /v1/turn` (+ 선택 `position`).

## 설정

`config/world_maps.json`

- `maps`: ashpoint_01, forest_01, tower_01  
- `exits`: 타일 rect → 맵 전환  
- `pois`: 반경 내 POI (우물, 연기 자국…)  
- `godot_scene`: Godot 씬 경로  

## API

| Method | Path | 용도 |
|--------|------|------|
| GET | `/v1/world/maps` | Godot 맵 메타 로드 |
| POST | `/v1/world/position` | 좌표 동기화 (시간 안 감) |
| POST | `/v1/turn` | `position` optional — 턴 전 동기화 |

### Position body

```json
{
  "session_id": "…",
  "position": {
    "map_id": "ashpoint_01",
    "x": 40,
    "y": 48,
    "facing": "south",
    "allow_map_transition": true
  }
}
```

응답: `zone_changed`, `map_changed`, `pois[]`, `transition`, `position`.

## Godot 연동

- `godot_pixel_per_tile` = 16 → 타일 `(floor(px/16), floor(py/16))`  
- 플레이어 이동 후 **타일 변경 시**만 `ApiClient.sync_position()`  
- 출구 타일 → 서버가 `forest_01` 등으로 **맵 전환** 확정 → Godot `change_scene`  

코드: `client/godot/scenes/exploration.tscn`, `scripts/player/player_controller.gd`

## `world` 샤드

```json
{
  "map_id": "ashpoint_01",
  "zone_id": "ashpoint",
  "x": 40,
  "y": 48,
  "facing": "south",
  "location": "실버우드 변경 마을 '애쉬포인트'"
}
```

`event_engine._location_zone` → `zone_id` 우선.

## 모듈

- `utils/spatial.py` — `sync_position`, `maps_manifest`  
- `utils/game_session.apply_position`  
- `api/server.py` — 엔드포인트  

## 관련

- [15_GODOT_RELEASE_ARCHITECTURE.md](15_GODOT_RELEASE_ARCHITECTURE.md)  
- [12_MICRO_TIME_AND_COCREATION.md](12_MICRO_TIME_AND_COCREATION.md)
