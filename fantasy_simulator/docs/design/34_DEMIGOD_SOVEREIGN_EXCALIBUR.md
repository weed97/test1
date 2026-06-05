# 34 — 준신 주권자 · 엑스칼리버 · 4년 주권 소원

## 위치 (티어)

```text
T1~T3 일반 → 전설 L1~L6 → 신화 M1~M3 (active ~30)
  → 준신(Demigod) · 【엑스칼리버】= 아서 홀더의 권능 무기
```

- **준신 세트**는 5종족 신화 T3 15개 + 월드 보스 극한 재료 + 세계 유일 대장장이로 **재련 가능** (극희귀).
- **초기 세계**: NPC **아서왕**이 이미 엑스칼리버(준신 성검)를 착용·`world_sovereign` 홀더.
- 유저·몬스터·다른 NPC가 **승계**하면 동일 권능은 **검을 쥔 홀더**에게 이전.

관련: [24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md](24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md) (준신만 의도적 불균형 예외)

---

## 엑스칼리버 권능 — 「4년에 한 번, 세계에 소원」

| 항목 | 규칙 |
|------|------|
| **이름** | `sovereign_wish` (주권 소원) |
| **주기** | **게임 내 4년**마다 1회 (`days_per_year` × 4 경과) |
| **행위자** | `world_sovereign.holder` (초기: `npc_arthur_pendragon`) |
| **효과** | 홀더가 세계에 **소원을 전달** → 시뮬이 **반드시 이행** (단, 아래 한도 내) |
| **UI** | 고담 의식 + 구조화 `edict_payload` (자연어는 파서가 edict로 변환) |

### 시간

- `world.day` + `config/demigod_sovereign.json` 의 `days_per_year` (기본 360) → `world_year = day // days_per_year`
- `last_sovereign_wish_year` 와 비교, **4년 미만**이면 거부.
- 소원 발동 시 **전역 이벤트** (하늘·종소리·모든 왕국 소문) — 마법·준신으로 세계가 듣는 **관측 가능 현상**.

---

## 소원이 “이뤄진다”는 것 (시뮬)

소원은 **무제한 치트가 아니라** `edict` 한 장으로 세계 샤드를 바꾼다.

### 허용 범주 (예)

| edict_type | 효과 |
|------------|------|
| `empower_self` | 홀더·파티·몬스터 홀더 스탯·스킬 상한 |
| `empower_kingdom` | 지정 왕국 건설·병력·자원 |
| `weaken_realm` | 특정 종족 영역 spawn·번영↓ |
| `empower_monsters` | 권역/전역 몬스터 진화·습격↑ |
| `found_civilization` | 새 문명·규칙 플래그 (`civilization_coupling`) |
| `reshape_rule` | `flags.world_rules` 커스텀 (기존 룰 덮어쓰기) |

### 이행 파이프라인

1. 홀더가 소원 제출 (`POST /v1/sovereign/wish` 또는 턴 의식)
2. `resolve_sovereign_wish(state, payload)` — **성공 이행** 플래그·로그·`world_conflicts` 후폭풍
3. `last_sovereign_wish_world_day` 갱신
4. **반작용** 자동: 다른 종족 연합·봉인 가속·신화 각성 힌트 (독점 완화)

### 금지·완화 (전설이 쉽지 않듯 준신도)

- 하드 락: `power_ecology.forbidden_edicts` (예: 월드 삭제, 전 종족 멸절)
- **부분 이행**: 과도한 소원은 `fulfillment_ratio` &lt; 1 + “세계가 저항했다” 서사
- 홀더가 **검을 잃으면** 미사용 소원 차례는 **검 보유자**만 사용

---

## 아서왕 · 승계

```json
{
  "world_sovereign": {
    "holder_id": "npc_arthur_pendragon",
    "holder_kind": "npc",
    "title": "반신 왕",
    "since_world_day": 1
  },
  "demigod_regalia": {
    "weapon": {
      "artifact_id": "excalibur_sovereign_blade",
      "tier": "demigod",
      "power_id": "sovereign_wish_every_4_years"
    }
  },
  "sovereign_wish": {
    "interval_years": 4,
    "last_wish_world_day": null,
    "next_eligible_world_day": 1441
  }
}
```

| 이벤트 | 결과 |
|--------|------|
| 유저/몬스터가 아서를 넘음 | `holder_id` 교체, **엑스칼리버 소지자**가 소원 권한 |
| 엑스칼리버만 탈취 | 소원은 **검 홀더** (왕관 없어도 검만으로 권능) |
| 4년 주기 | 이전 홀더가 쓴 소원도 **세계 상태에 영구 흔적** (되돌리기 어려움) |

---

## 다른 준신 장비와의 관계

- **엑스칼리버** = 유일 무기 슬롯 권능: **주기적 세계 소원**.
- 준신 방어구·악세서리(재련 세트)는 **별도 패시브** (예: 종족 저항, 에딕트 쿨 감소) — 추후 `config/demigod_regalia.json`.
- **15신화 T3 합성**으로 만든 **새 준신 세트**는 아서 **이전** 시대의 엑스칼리버와 **공존 불가** 또는 **승계 시 하나만 active** (설정 선택).

---

## API · Godot (후속)

| Method | Path | 용도 |
|--------|------|------|
| GET | `/v1/sovereign/status` | 홀더, 다음 소원 가능일, 엑스칼리버 소지 |
| POST | `/v1/sovereign/wish` | edict 제출 (4년 주기 검사) |
| GET | `/v1/world/rumors` | 소원 이행 후 전역 소문 |

Godot: 4년 주기 임박 시 하늘 이펙트·대사 “왕이 세계에 말을 걸 준비가 되었다.”

---

## 한 줄

**엑스칼리버 = 준신 성검 = 4년마다 세계에 소원 1회, 시뮬이 반드시 이행(한도·반작용 내) · 아서가 초기 홀더 · 검을 가진 자가 주권.**
