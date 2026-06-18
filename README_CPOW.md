# CPoW World — 3D 창조 시뮬레이터

> **게임이 아닙니다.** 유저 창조 데이터가 물리 법칙이 되는 **CPoW (Creativity-Proof of Work) 자율 시뮬레이션**입니다.

Eldoria (`fantasy_simulator`)와 **완전 분리**된 독립 프로젝트 스캐폴드입니다.  
이 디렉터리들만 복사하면 별도 GitHub 저장소로 즉시 분리할 수 있습니다.

## 구조

```
cpow_engine/          # Python 시뮬 엔진 (물리·CPoW·에리어·거버넌스)
cpow_api/             # FastAPI 서버 (/v1/areas/*, /v1/auth/*, /v1/xr/*)
cpow_client/godot/    # Godot 4 3D 클라이언트
docs/                 # CPOW 설계 문서
tests/                # API 통합 스모크 테스트
```

## 빠른 실행

```bash
# API 의존성
pip install -r requirements-cpow-api.txt

# 엔진 데모
python3 -m cpow_engine.demo --areas

# API 서버 (Eldoria 불필요)
uvicorn cpow_api.server:app --host 127.0.0.1 --port 8765

# 테스트
bash scripts/verify_cpow.sh
```

## Godot 3D 클라이언트

1. 위 API 서버 실행
2. Godot 4.2+에서 `cpow_client/godot/project.godot` 열기 → F5

환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CPOW_API_URL` | `http://127.0.0.1:8765` | API 베이스 URL |
| `CPOW_CREATOR_ID` | `cpow_player` | creator_id |

## Eldoria와의 차이

| | Eldoria (`fantasy_simulator`) | CPoW World |
|--|-------------------------------|------------|
| 클라이언트 | 2D Godot + XR 슬라이스 | **3D** `cpow_client/godot` |
| API | `/v1/turn`, `/v1/session` | `/v1/areas/*` 전용 `cpow_api` |
| 엔진 | 고정 RPG 규칙 | 속성 기반 창조 물리 |

## 별도 저장소로 분리

→ [docs/SPLIT_REPO.md](docs/SPLIT_REPO.md)

## 문서

- [CPOW_ARCHITECTURE.md](docs/CPOW_ARCHITECTURE.md)
- [CPOW_ROADMAP.md](docs/CPOW_ROADMAP.md)
- [TODO_REMAINING.md](docs/TODO_REMAINING.md)
- [cpow_client/godot/docs/CLIENT_ARCHITECTURE.md](cpow_client/godot/docs/CLIENT_ARCHITECTURE.md)

## 개발

```bash
python3 -m unittest discover -s cpow_engine/tests -v
python3 -m unittest tests.test_cpow_api_flow -v
python3 -m compileall -q cpow_engine cpow_api
```
