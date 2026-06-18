# 남은 작업 — CPoW (2026)

## 🔴 프로덕션·클라이언트

- [ ] Godot `areas_client.gd` Bearer 토큰 + 로그인 UI
- [ ] Auth 강제 정책 (`CPOW_AUTH_REQUIRED` 또는 mutating API 필수)
- [ ] `CPOW_JWT_SECRET` / HTTPS / CORS 화이트리스트
- [ ] 계정·에리어 영속 저장 (SQLite/Redis)
- [ ] auth rate limit

## 🟠 신원·공정성 후속

- [ ] person_key OAuth / PASS / 카드 실인증
- [ ] `GET /v1/identity/status` 인증 보호
- [ ] 멀티 인스턴스 상태 공유

## 🟡 Godot UX

- [ ] 거버넌스·외교·공성 UI
- [ ] glb HTTP 캐시 · VRoid 로드
- [ ] 실시간 state 동기화 (폴링/WebSocket)

## 🟢 물리 엔진 (이번에 추가)

- [x] 전기·유체·복사·구조 역할 + 확장 상호작용
- [x] 중력·풍·압력 환경장
- [x] 상변화(용융) 피드백
- [x] 교차 물리: 전하·복사 허브 결합
- [x] `engine.py` 틱 파이프라인 연동 + API 타입 (`charge`/`fluid`/`radiant`/`structural`)
- [x] `docs/PHYSICS_EXTENDED.md` + 테스트
- [ ] 물리 법칙 에리어별 커스텀 (`AreaLawSet` 연동)
- [ ] XR 손짓 → `connect` + 속성 부여 실시간
- [ ] 3D 위치 기반 거리 감쇠 (현재는 그래프 거리)

## ⚪ 후순위 (로드맵 Phase 3~4)

- [ ] 프로덕션 온체인 브릿지
- [ ] L1 / 롤업 선택

## 테스트

```bash
python3 -m unittest discover -s cpow_engine/tests -v
cd fantasy_simulator && python3 -m unittest tests.test_cpow_api_flow -v
```
