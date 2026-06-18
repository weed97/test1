# CPoW World — 별도 저장소

**전용 repo:** https://github.com/weed97/cpow_world

## 최초 push (repo를 방금 만든 경우)

`test1`의 export 브랜치에서 한 번만 push:

```bash
git clone -b cpow-world https://github.com/weed97/test1.git cpow_world
cd cpow_world
git branch -M main
git remote set-url origin https://github.com/weed97/cpow_world.git
git push -u origin main
```

또는 Actions: [publish-cpow-world.yml](https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml) — **PAT 설정:** [SYNC_CPOW_WORLD.md](SYNC_CPOW_WORLD.md)

이후 일반 clone:

```bash
git clone https://github.com/weed97/cpow_world.git
cd cpow_world
pip install -r requirements-api.txt
bash scripts/verify.sh
```

## test1 모노레포와의 관계

| 저장소 | 역할 |
|--------|------|
| **[weed97/cpow_world](https://github.com/weed97/cpow_world)** | **정식** — 엔진·API·Unity 클라이언트. 여기서 clone·작업 |
| [weed97/test1](https://github.com/weed97/test1) | 모노레포 **미러** — Agent가 `cpow_*` 수정 후 Actions로 cpow_world에 export |

`test1/main` push 시 (PAT 등록 후) **자동** cpow_world 동기화.  
수동 1회: [SYNC_CPOW_WORLD.md](SYNC_CPOW_WORLD.md)

## 실행 확인

- [ ] `python3 -m cpow_engine.demo --areas`
- [ ] `uvicorn cpow_api.server:app --port 8765`
- [ ] `curl http://127.0.0.1:8765/v1/health`
- [ ] Unity `cpow_client/unity/CPoWWorld` → 청크 스트리밍·채굴 UI
- [ ] (레거시) Godot `cpow_client/godot` → 에리어 개척·입장
- [ ] `bash scripts/verify.sh`
