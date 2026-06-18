# 에리어 외교 — 적대 · 중립 · 동맹

## 관계 유형

| 관계 | 의미 | 게임플레이 |
|------|------|------------|
| **적대** (`hostile`) | 서로 싸우는 관계 | 타 에리어 오브젝트 **교차 파괴** 가능 |
| **중립** (`neutral`) | 경쟁만, 직접 개입 없음 | **규모·지배**로 경쟁; **관찰자는 타 에리어에 관여 불가** |
| **동맹** (`alliance`) | 우호·협력 | **상호 동맹** 선언 시 파트너 에리어에 **협력 창조** 가능 |

기본값은 **중립**입니다.

## 해석 규칙

```
한쪽이라도 적대 선언 → 실효 관계 = 적대
양쪽 모두 동맹 선언 → 실효 관계 = 동맹
그 외 → 중립
```

동맹은 **창시자가 양쪽 모두** `alliance`를 선언해야 활성화됩니다.

## 적대 — 교차 파괴 · 공성 압력

- 공격자는 **자기 에리어 구성원**이어야 함
- **관찰자**는 교전 불가
- 작은 에리어가 큰 에리어를 공격하면 **지배 비율**만큼 파괴력 요구량 증가
- 반복 파괴는 **공성 압력**을 쌓아 방어를 마모 — [AREA_SIEGE.md](AREA_SIEGE.md)

## 중립 — 경쟁만

- `GET /v1/areas/dominance`로 규모·지배 비교
- 타 에리어에 직접 창조·파괴 불가
- **OBSERVER** 역할은 타 에리어 어떤 행동도 불가

## 동맹 — 협력 창조

```
POST /v1/areas/allied_create
{
  "home_area_id": "내 에리어",
  "target_area_id": "동맹 에리어",
  "creator_id": "builder",
  "label": "협력 불",
  "heat_intensity": 25
}
```

창조력은 **home 에리어** 멤버 게이지에서 소비됩니다.

## API

```bash
POST /v1/areas/diplomacy       # 선언 (founder만)
GET  /v1/areas/diplomacy       ?area_id=&target_area_id=
POST /v1/areas/cross_destroy   # 적대 시 교차 파괴
POST /v1/areas/allied_create   # 동맹 시 협력 창조
```

## 모듈

```
cpow_engine/areas/diplomacy.py
cpow_engine/areas/registry.py  # DiplomacyLedger 통합
```
