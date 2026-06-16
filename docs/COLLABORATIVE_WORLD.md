# 협동 오픈월드 — 다인 창조 + 노이즈 억제

## 한 줄 답

**됩니다.** 이미 있는 `shared_state`(병합) 위에 **변화량 감쇄(Noise Gate)** 를 얹으면, 여러 사람이 함께 창조하면서도 과도한 변화로 인한 노이즈를 줄일 수 있습니다.

## 핵심 아이디어

> 협동은 허용하되, **한 번에 세상을 뒤바꾸는 창조**는 자동으로 약해진다.  
> 그리고 창조는 **빌드 펄스**마다 모아서 함께 반영되어, 같이 만드는 리듬이 느껴진다.

| 문제 | 해결 |
|------|------|
| 누군가 heat=9999 올림 | 월드 평균 기준 **감쇄** → 실제 반영은 일부만 |
| 한 사람이 너무 빨리 여러 개 창조 | **쿨다운** + 펄스당 1개 상한 |
| 혼자만 세상이 바뀜 | **8초 펄스**에 모인 창조를 한꺼번에 반영 |
| 동시에 100명이 창조 | **펄스당 생성 상한** (`max_creations_per_tick`) |
| 같은 오브젝트 격렬 수정 | **상대 변화율 15%** 초과 시 강한 damp |
| 봇·스팸 | CPoW 창조성 낮으면 큰 변화 **추가 감쇄** |

## 빌드 펄스 (Build Pulse)

```
alice 창조 ──┐
bob 창조   ──┼──→ 대기 큐 ──→ (8초 후) 펄스 ──→ NoiseGate ──→ 월드 반영
carol 창조 ──┘
```

1. `submit_creation` → **큐에 적재** (`queued_for_pulse`)
2. `pulse_interval_sec` 경과 → **한꺼번에 반영** + 시뮬레이션 1틱
3. 클라이언트는 `seconds_until_pulse`, `pending`, `contributors_in_pulse`로 “곧 같이 반영된다” 표시

## 아키텍처

```
유저 A ──┐
유저 B ──┼──→ StatePatch ──→ NoiseGate (감쇄) ──→ SharedStateSync (병합)
유저 C ──┘                           │
                                     ▼
                            CollaborativeWorld
                            (공유 SimulationState)
```

## 정책 (`cpow_engine/config/collab_world.json`)

```json
{
  "max_relative_change": 0.15,
  "max_absolute_heat_delta": 30.0,
  "max_creations_per_tick": 6,
  "damp_factor": 0.35,
  "noise_threshold": 0.65,
  "pulse_interval_sec": 8.0,
  "min_creator_cooldown_sec": 4.0,
  "max_creations_per_creator_per_pulse": 1
}
```

- `pulse_interval_sec` — 펄스 간격(초). 이 시간 동안 모인 창조를 함께 반영
- `min_creator_cooldown_sec` — 같은 사람의 연속 창조 최소 간격
- `max_creations_per_creator_per_pulse` — 펄스당 1인 1창조 (협동감)

- `max_relative_change` — 기존 값 대비 15% 넘는 수정은 강하게 감쇄
- `damp_factor` — 들어온 변화의 35%만 반영 (나머지는 기존 상태 유지)
- `noise_threshold` — 이 이상이면 추가 감쇄

## API

```bash
# 월드 참가
POST /v1/collab/join  {"world_id": "open_alpha", "creator_id": "alice"}

# 협동 창조 (큐에 적재 — 펄스 때 반영)
POST /v1/collab/create  {
  "world_id": "open_alpha",
  "creator_id": "bob",
  "type": "heat",
  "heat_intensity": 500,
  "creativity_score": 0.8
}

# 펄스 강제 실행 (선택)
POST /v1/collab/pulse  {"world_id": "open_alpha", "force": true}

# 월드 상태 (자동 펄스 체크 포함)
GET /v1/collab/world?world_id=open_alpha
```

응답에 `queued`, `seconds_until_pulse`, `pending_count`, `contributors_in_pulse` 포함 →  
클라이언트가 “3명이 모이는 중… 5초 후 함께 반영” UI 표시 가능.

펄스 반영 후 `magnitude`, `applied_damping`, `noise_level` 포함.

## XR / Godot 연동

동일 `world_id`를 여러 Quest 클라이언트가 공유:

1. `POST /v1/collab/join` → `world_id` 수신
2. 핀치 창조 → `POST /v1/collab/create` (XR intent 또는 heat 파라미터)
3. 주기적 `GET /v1/collab/world` → 다른 유저 창조물 동기화

## 설계 원칙

1. **거부보다 감쇄** — 신규 창조는 거부하지 않고 감쇄만 적용
2. **펄스로 함께 반영** — 혼자 빠르게 진행하지 못하게, 모였다가 한 번에 적용
3. **작은 창조 장려** — 월드 평균 근처 변화는 damp 적게
4. **고유 창조 보상** — `creativity_score` 높으면 큰 변화 허용폭 소폭 확대
5. **펄스 단위 상한** — 오픈월드 서버 보호

## 모듈

```
cpow_engine/collab/
  policy.py      # CollabPolicy
  noise_gate.py  # 변화량 측정·감쇄
  pulse.py       # 빌드 펄스 큐·반영
  world.py       # CollaborativeWorld
```

## 관련

- [CPOW_ARCHITECTURE.md](CPOW_ARCHITECTURE.md) — shared_state 병합
- [XR_INTEGRATION.md](XR_INTEGRATION.md) — XR 클라이언트
