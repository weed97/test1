# Host Security Checklist — CPoW API

점검 기준일: P0 이후 (`fantasy_simulator/api/server.py` + `cpow_engine/auth`)

## 자동 검증

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
python3 -m unittest tests.test_cpow_api_flow tests.test_api_server -v
cd .. && python3 -m unittest discover -s cpow_engine/tests -v
```

## 호스트 배포 전 필수 (P0)

| 항목 | 현재 | 권장 |
|------|------|------|
| `CPOW_JWT_SECRET` | dev 기본값 | **32+ byte 랜덤**, 시크릿 매니저/환경변수 |
| HTTPS | 앱 레벨 미강제 | nginx/Caddy TLS 종단 |
| CORS | `allow_origins=["*"]` | 프로덕션 origin 화이트리스트 |
| CORS credentials | ~~`allow_credentials=True`~~ → **`False`** | Bearer만 쓸 때 쿠키 불필요 |
| 계정 저장 | in-memory | Redis/DB 영속화 |
| Godot 클라이언트 | Bearer 미전송 | `areas_client.gd`에 토큰 헤더 추가 |

## API 보안 동작 (검증됨)

| 동작 | 결과 |
|------|------|
| `POST /v1/identity/register` 무토큰 | **401** |
| Bearer + 다른 `founder_id` | **403** actor_identity_mismatch |
| Bearer + actor 생략 | 세션 user로 바인딩 |
| 무Bearer `founder_id` 자기신고 | **허용** (optional auth) |

## 잔여 리스크 (알려진 한계)

1. **Optional auth** — 토큰 없이 `anonymous`/`임의 user_id`로 대부분 mutating API 호출 가능. 프로덕션에서는 리버스 프록시 또는 `CPOW_AUTH_REQUIRED` 재도입 검토.
2. **`GET /v1/identity/status?user_id=`** — 인증 없이 검증 여부 조회 가능 (정보 노출).
3. **Rate limit 없음** — `/v1/auth/register`, `/login` 브루트포스 가능.
4. **person_key** — 구조적 바인딩만; OAuth/PASS 미구현.
5. **단일 프로세스 in-memory** — 수평 확장 시 세션/계정/에리어 상태 공유 안 됨.
6. **Eldoria `/v1/session`** — CPoW auth와 별도; 기존 RPG API는 여전히 session_id 기반.

## Godot 클라이언트 갭

`cpow_client/godot/scripts/net/areas_client.gd`:

- `_request_impl`에 `Authorization: Bearer` 없음
- `register_identity`가 구 API처럼 `user_id`를 body에 넣음 → 서버는 세션만 신뢰

**권장 패치 순서**

1. `AreasConfig`에 `auth_token` / login UI
2. `_request_impl` headers에 Bearer 추가
3. identity register body에서 `user_id` 제거

## 네트워크 바인딩

```bash
# 개발
uvicorn api.server:app --host 127.0.0.1 --port 8765

# 프로덕션 — 0.0.0.0 금지 또는 방화벽 + TLS 필수
```

## 점검 체크리스트

- [ ] `CPOW_JWT_SECRET` 프로덕션 값 설정
- [ ] TLS 종단 (443)
- [ ] CORS origin 제한
- [ ] `allow_credentials=False` (쿠키 미사용 시)
- [ ] Godot Bearer 연동
- [ ] optional auth 정책 결정 (강제 vs 점진)
- [ ] auth rate limit (nginx `limit_req` 또는 앱 미들웨어)
- [ ] 계정 영속 저장소
- [ ] 로그에 password/token 미기록
