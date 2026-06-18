# CPoW Unity Client Architecture

## 목표

협업 에리어 + 오픈월드(바이옴·채굴·모듈 건축)를 **메모리 상한이 있는 청크 스트림**으로 표현합니다.

```
┌─────────────────────────┐     REST      ┌──────────────────────┐
│  Unity CPoWWorld        │ ◄───────────► │  cpow_api            │
│  ChunkStreamer (AOI)    │  /v1/world/*  │  cpow_engine/world   │
│  AreaObjectRenderer     │  /v1/areas/*  │  cpow_engine/areas   │
└───────────┬─────────────┘               └──────────────────────┘
            │
   ┌────────┴────────┬──────────────┐
   │ ChunkPool (LRU) │ Areas sync   │
   │ BiomeChunkView  │ glb props    │
   └─────────────────┴──────────────┘
```

## 메모리 모델 (ChunkStore 분리)

서버 `cpow_engine/world/grid.py` 는 **결정론적 셀 데이터**만 제공합니다.  
클라이언트는 **ChunkStore(데이터)** 와 **ChunkView(메시)** 를 분리합니다.

| 레이어 | 책임 | Unity 타입 |
|--------|------|------------|
| Data | API JSON 캐시, biome/hazard/ore | `ChunkCellSnapshot` |
| Pool | 상한·LRU·GameObject 재사용 | `ChunkPool` |
| Stream | 플레이어 셀 좌표, 로드 링 | `ChunkStreamer` |
| View | 바이옴 색 plane, 위험 VFX | `BiomeChunkView` |

### AOI 규칙

- `loadRadius = 3` → 7×7 = **49 청크** 상한 (기본)
- `unloadRadius = 4` → 히스테리시스로 경계 플리커 방지
- `maxConcurrentLoads = 4` → 프레임 스파이크 완화
- 풀 초과 시 **가장 오래 본 청크**부터 `ChunkPool` 이 회수

### 좌표

- 월드 (x, z) → 셀 `(cx, cz) = floor(x / cellSize), floor(z / cellSize)`
- `cellSize` 는 서버 `WorldCellRequest.cell_size` 와 동일 (기본 64)

## API 계약

### Areas (`AreasApiClient`)

| 메서드 | HTTP | 용도 |
|--------|------|------|
| `ListAreasAsync` | GET `/v1/areas/list` | 목록 |
| `FoundAreaAsync` | POST `/v1/areas/found` | 개척 |
| `JoinAreaAsync` | POST `/v1/areas/join` | 입장 |
| `FetchStateAsync` | GET `/v1/areas/state` | 오브젝트 동기화 |
| `CreateObjectAsync` | POST `/v1/areas/create` | 창조 |
| `AdventureMineAsync` | POST `/v1/areas/adventure` | action=mine |

### World (`WorldApiClient`)

| 메서드 | HTTP | 용도 |
|--------|------|------|
| `GetCatalogAsync` | GET `/v1/world/catalog` | 바이옴·광물·도구 |
| `InspectCellAsync` | POST `/v1/world/cell` | 셀 + hazard audio |
| `MineAsync` | POST `/v1/world/mine` | 채굴 |
| `ValidateBuildAsync` | POST `/v1/world/build/validate` | 모듈 건축 검증 |

## 씬 흐름

```
Boot.unity
  └─ GameBootstrap
        ├─ CpowSession (area_id, user_id)
        ├─ AreasApiClient + WorldApiClient
        ├─ ChunkStreamer → ChunkPool → BiomeChunkView
        └─ AreaObjectRenderer (state poll)
```

## 다음 단계 (로드맵)

- [x] 채굴 HUD — 도구·깊이·POST `/v1/world/mine` (`MiningHud`, `MiningController`)
- [x] 채굴 결과 → `submit_creation` (`attach_mined_resource_to_area`, `creation` in mine response)
- [ ] Addressables / GLTFast 로 glb 스트리밍
- [ ] WebSocket delta (`/v1/stream`) — 멀티플레이어 AOI 동기화
- [ ] VRM / Universal RP 아바타
- [ ] 모듈 건축 고스트 메시 프리뷰
- [ ] 채굴 결과 → `submit_creation` 자동 연동

## Godot 클라이언트

`cpow_client/godot/` 는 **레거시 프로토타입**입니다. 신규 3D 작업은 Unity만 유지합니다.
