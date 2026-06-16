# 협동 오픈월드 — 다인 창조 + 노이즈 억제

## 한 줄 답

**됩니다.** 이미 있는 `shared_state`(병합) 위에 **변화량 감쇄(Noise Gate)** 를 얹으면, 여러 사람이 함께 창조하면서도 과도한 변화로 인한 노이즈를 줄일 수 있습니다.

## 핵심 아이디어

> 협동은 허용하되, **한 번에 세상을 뒤바꾸는 창조**는 자동으로 약해진다.

| 문제 | 해결 |
|------|------|
| 누군가 heat=9999 올림 | 월드 평균 기준 **감쇄** → 실제 반영은 일부만 |
| 동시에 100명이 창조 | **틱당 생성 상한** (`max_creations_per_tick`) |
| 같은 오브젝트 격렬 수정 | **상대 변화율 15%** 초과 시 강한 damp |
| 봇·스팸 | CPoW 창조성 낮으면 큰 변화 **추가 감쇄** |

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
  "max_creations_per_tick": 12,
  "damp_factor": 0.35,
  "noise_threshold": 0.65
}
```

- `max_relative_change` — 기존 값 대비 15% 넘는 수정은 강하게 감쇄
- `damp_factor` — 들어온 변화의 35%만 반영 (나머지는 기존 상태 유지)
- `noise_threshold` — 이 이상이면 추가 감쇄

## API

```bash
# 월드 참가
POST /v1/collab/join  {"world_id": "open_alpha", "creator_id": "alice"}

# 협동 창조 (감쇄 적용)
POST /v1/collab/create  {
  "world_id": "open_alpha",
  "creator_id": "bob",
  "type": "heat",
  "heat_intensity": 500,
  "creativity_score": 0.8
}

# 월드 상태
GET /v1/collab/world?world_id=open_alpha
```

응답에 `magnitude`, `applied_damping`, `noise_level` 포함 → 클라이언트가 "얼마나 약해져 반영됐는지" 표시 가능.

## XR / Godot 연동

동일 `world_id`를 여러 Quest 클라이언트가 공유:

1. `POST /v1/collab/join` → `world_id` 수신
2. 핀치 창조 → `POST /v1/collab/create` (XR intent 또는 heat 파라미터)
3. 주기적 `GET /v1/collab/world` → 다른 유저 창조물 동기화

## 설계 원칙

1. **거부보다 감쇄** — 신규 창조는 거부하지 않고 감쇄만 적용, 기존 오브젝트 극단 수정만 거부
2. **작은 창조 장려** — 월드 평균 근처 변화는 damp 적게
3. **고유 창조 보상** — `creativity_score` 높으면 큰 변화 허용폭 소폭 확대
4. **틱 단위 상한** — 오픈월드 서버 보호

## 모듈

```
cpow_engine/collab/
  policy.py      # CollabPolicy
  noise_gate.py  # 변화량 측정·감쇄
  world.py       # CollaborativeWorld
```

## 관련

- [CPOW_ARCHITECTURE.md](CPOW_ARCHITECTURE.md) — shared_state 병합
- [XR_INTEGRATION.md](XR_INTEGRATION.md) — XR 클라이언트
