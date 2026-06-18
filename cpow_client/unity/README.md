# CPoW World — Unity 클라이언트

Godot 대신 **Unity 2022.3 LTS+** 로 오픈월드를 띄웁니다.  
대용량 월드는 **청크 스트리밍 + 메모리 풀** 로 AOI(관심 영역)만 유지합니다.

## 왜 Unity?

| 항목 | Godot | Unity (이 클라이언트) |
|------|-------|----------------------|
| 청크 스트리밍 | 직접 구현 부담 큼 | `ChunkStreamer` + `ChunkPool` 내장 |
| 메모리 상한 | 수동 관리 | `maxLoadedChunks`, LRU 언로드 |
| glb/VRM | 플러그인 의존 | GLTFast / Addressables 연동 예정 |
| MMO 스케일 | 프로토타입 적합 | 프로덕션 파이프라인 |

## 사전 요구

1. [cpow_world](https://github.com/weed97/cpow_world) 저장소 (또는 이 모노레포의 `cpow_*`)
2. API 서버 실행:

```bash
pip install -r requirements-cpow-api.txt
uvicorn cpow_api.server:app --host 127.0.0.1 --port 8765
```

3. Unity Hub → **2022.3 LTS** 이상 → `cpow_client/unity/CPoWWorld` 열기

## 첫 실행

1. `Assets/CPoW/Scenes/Boot.unity` 열기
2. Inspector에서 `GameBootstrap` 의 `Api Base Url` 확인 (`http://127.0.0.1:8765`)
3. Play — 자동으로 에리어 개척 후 청크 링 로드

환경 변수 (에디터/OS):

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CPOW_API_URL` | `http://127.0.0.1:8765` | API 베이스 |
| `CPOW_CREATOR_ID` | `cpow_player` | actor / creator id |

## 아키텍처

→ [docs/CLIENT_ARCHITECTURE.md](docs/CLIENT_ARCHITECTURE.md)

핵심 스크립트:

- `Net/AreasApiClient.cs` — `/v1/areas/*`
- `Net/WorldApiClient.cs` — `/v1/world/*` (바이옴·채굴·건축)
- `World/ChunkStreamer.cs` — 플레이어 주변 N×N 셀만 로드
- `World/ChunkPool.cs` — GameObject 재사용 + LRU 언로드
- `Areas/AreaObjectRenderer.cs` — CPoW 창조 오브젝트 3D 배치

## cpow_world 저장소

신규 작업은 **weed97/cpow_world** 에서 진행하세요.  
test1 모노레포에서 push 후 Actions로 동기화:

```bash
# test1 → cpow_world (한 번 설정 후)
# GitHub Actions: Publish CPoW World workflow
```

또는 직접:

```bash
git remote add cpow_world https://github.com/weed97/cpow_world.git
git push cpow_world cursor/unity-client-156a:main
```
