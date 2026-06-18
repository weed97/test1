# CPoW World Client (Godot 4)

**Eldoria `fantasy_simulator`와 분리된** CPoW 전용 Godot 클라이언트입니다.

- API: `/v1/areas/*` (창조 에리어·협업·거버넌스)
- **사용하지 않음**: `/v1/turn`, Eldoria 2D `exploration.tscn`, 고정 `item_catalog`

## 실행

1. CPoW API 서버 (Eldoria 불필요):

```bash
pip install -r requirements-cpow-api.txt
uvicorn cpow_api.server:app --host 127.0.0.1 --port 8765
```

2. Godot 4.2+에서 `cpow_client/godot/project.godot` 열기 → F5

환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CPOW_API_URL` | `http://127.0.0.1:8765` | API 베이스 URL |
| `CPOW_CREATOR_ID` | `cpow_player` | `creator_id` / `user_id` |

## 프로젝트 구조

```
cpow_client/godot/
  scenes/
    main_menu.tscn      # 에리어 목록·개척·입장
    area/area_viewer.tscn  # 3D 에리어 뷰어
    avatar/player_avatar.tscn  # VRoid/glb 아바타 루트
  scripts/
    net/areas_client.gd # /v1/areas/* 전용 HTTP
    avatar/equipment_manager.gd  # glb 장착
    world/area_object_renderer.gd  # CreativeObject 3D 배치
```

## Visual 메타데이터

서버 `CreativeObject`에 `visual` 필드:

```json
{
  "visual": {
    "glb_url": "https://cdn.example/sword.glb",
    "slot": "weapon",
    "attach_bone": "RightHand",
    "offset": {"position": [0, 0.1, 0]}
  }
}
```

슬롯: `avatar`, `weapon`, `movement`, `accessory`, `world_prop`

자세한 파이프라인: [docs/CLIENT_ARCHITECTURE.md](docs/CLIENT_ARCHITECTURE.md)

## Eldoria 클라이언트와의 관계

| | `fantasy_simulator/client/godot` | `cpow_client/godot` |
|--|----------------------------------|---------------------|
| 목적 | Eldoria RPG (2D + XR 슬라이스) | 유저 창조 월드 |
| API | `/v1/turn`, `/v1/xr/*` | `/v1/areas/*` |
| 아이템 | 고정 `iron_sword` 카탈로그 | 크리에이터 glb 마켓 (예정) |
| 아바타 | 없음 (2D 스프라이트) | VRoid + 장비 glb |
