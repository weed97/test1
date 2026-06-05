# 21 — 플레이어 건설·건축 레벨·NPC 고용

## 목표

> 「이세계에서 **내가** 무언가를 만든다」 — 대장간·여관·왕국까지 **디테일한 비용·인력·성장**.

| 축 | 내용 |
|----|------|
| **건축 레벨** | 1~5 — 해금 건물·동시 공사·자가 노동력 |
| **자가 건설** | 골드 + 자재 + **노동 포인트** (비트마다 진행) |
| **고용 건설** | NPC 일꾼 고용 (골드) + **매 비트 임금** + 고용 노동력 |
| **건물 역할** | `roles`: smith, inn, militia… → 효과·Godot 타일 |
| **왕국** | Lv5 + 필수 4건물 + 대규모 비용 → `is_kingdom` |

---

## 데이터

| 파일 | 역할 |
|------|------|
| `config/settlement_buildings.json` | 건물표·레벨·고용·왕국 |
| `flags.ecology.player_settlement` | 진행·거점·완공 목록 |

### player_settlement (요약)

```json
{
  "construction_level": 2,
  "construction_xp": 95,
  "hired_workers": 3,
  "stockpile": { "wood": 20, "stone": 10, "iron": 5 },
  "sites": [{
    "site_id": "site_abc",
    "map_id": "ashpoint_01",
    "x": 52, "y": 38,
    "name": "플레이어 거점",
    "active_project": {
      "building_id": "blacksmith",
      "progress": 40,
      "required": 70,
      "mode": "hire"
    },
    "buildings": []
  }],
  "completed_buildings": [],
  "is_kingdom": false
}
```

---

## 건축 레벨

| Lv | 칭호 | XP | 동시 공사 | 자가 노동/비트 |
|----|------|-----|-----------|----------------|
| 1 | 견습 | 0 | 1 | 2 |
| 2 | 마을 터 | 80 | 1 | 3 |
| 3 | 장인 | 200 | 2 | 4 |
| 4 | 영주 | 450 | 2 | 5 |
| 5 | 왕국 설계자 | 900 | 3 | 6 |

완공 시 **건축 XP** → 레벨업 → **새 건물 해금** (대장간 Lv2+ 등).

---

## 건물 예 (일부)

| id | Lv | 골드 | 노동 | 자재 | 역할 |
|----|-----|------|------|------|------|
| camp_fire | 1 | 30 | 8 | wood | 휴식 |
| storage_shack | 1 | 50 | 12 | wood | 창고 |
| blacksmith | 2 | 220 | 55 | wood+stone+iron | **대장장이** |
| inn | 2 | 180 | 45 | wood+stone | 여관·소문 |
| barracks | 3 | 320 | 80 | … | 병영 |
| market | 3 | 280 | 70 | … | 시장 |
| hall | 4 | 500 | 120 | … | 영주 회관 |

**건축 레벨 미달** → API 400 `건축 레벨 N 필요`.

---

## 고용 vs 자가

| | self | hire |
|--|------|------|
| 해금 | Lv1+ | Lv2+ |
| 노동/비트 | `self_labor_per_beat` | `workers × labor_per_worker` |
| 비용 | 건설비만 | 건설비 + **고용비 120G/인** + **임금 8G/인/비트** |
| 느낌 | 직접 망치 | 마을 키우는 **영주** |

---

## API (`ecology` / `hybrid` 모드)

| Method | Path |
|--------|------|
| GET | `/v1/settlement/status` |
| POST | `/v1/settlement/build` |
| POST | `/v1/settlement/hire` |
| POST | `/v1/settlement/kingdom` |

### build

```json
{
  "session_id": "...",
  "building_id": "blacksmith",
  "map_id": "ashpoint_01",
  "x": 52,
  "y": 38,
  "mode": "hire"
}
```

### hire

```json
{ "session_id": "...", "count": 2 }
```

진행은 **`explore` 등 턴 끝** `tick_player_build_projects` — `[건설] 대장장이 57%` 로그.

---

## Godot (다음)

- 건설 UI: 해금 목록·비용·자재 색 (가능/불가)
- 타일 클릭 → `build` API
- 완공 시 **타일 스왑** (대장장이 스프라이트)
- NPC 고용 패널: 인력·임금 예고

---

## 관련

- [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md)  
- [19_SPATIAL_SIMULATION.md](19_SPATIAL_SIMULATION.md)
