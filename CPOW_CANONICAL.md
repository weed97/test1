# CPoW — 정식 저장소는 cpow_world

> **CPoW 코드는 `weed97/cpow_world` 에서 작업하세요.**  
> 이 `test1` 저장소의 `cpow_*` 폴더는 **자동 미러(export 소스)** 입니다.

## 왜 test1에 있나?

Cloud Agent / CI는 `test1`에만 push 권한이 있습니다.  
`cpow_world`는 별도 repo라 **PAT 한 번** 등록 후 Actions로 동기화합니다.

## 지금 바로 cpow_world 쓰기

```bash
git clone https://github.com/weed97/cpow_world.git
cd cpow_world
pip install -r requirements-api.txt
bash scripts/verify.sh
```

Unity: `cpow_client/unity/CPoWWorld`

## test1 → cpow_world 동기화

1. [docs/SYNC_CPOW_WORLD.md](docs/SYNC_CPOW_WORLD.md) — `CPOW_WORLD_PUSH_TOKEN` 등록  
2. Actions → **Publish CPoW World** 실행  
3. 이후 `cpow_*` 수정 시 **main push 마다 자동 동기화** (워크플로 설정됨)

## 이 폴더에서 직접 수정하면?

`test1/main`에 커밋 → Actions가 `cpow_world`로 export.  
**로컬 개발은 `cpow_world` clone 권장.**
