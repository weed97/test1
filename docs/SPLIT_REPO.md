# CPoW World — 별도 저장소

**전용 repo:** https://github.com/weed97/cpow-world

## 최초 push (repo를 방금 만든 경우)

`test1`의 export 브랜치에서 한 번만 push:

```bash
git clone -b cpow-world https://github.com/weed97/test1.git cpow-world
cd cpow-world
git branch -M main
git remote set-url origin https://github.com/weed97/cpow-world.git
git push -u origin main
```

이후 일반 clone:

```bash
git clone https://github.com/weed97/cpow-world.git
cd cpow-world
pip install -r requirements-api.txt
bash scripts/verify.sh
```

## test1 모노레포와의 관계

| 저장소 | 내용 |
|--------|------|
| [weed97/cpow-world](https://github.com/weed97/cpow-world) | CPoW 전용 (엔진·API·3D Godot) |
| [weed97/test1](https://github.com/weed97/test1) | Eldoria + 기타 시뮬 (`fantasy_simulator` 등) |

`test1/main`의 `cpow_*` 폴더는 레거시 미러입니다. 신규 작업은 **cpow-world** repo에서 진행하세요.

## 실행 확인

- [ ] `python3 -m cpow_engine.demo --areas`
- [ ] `uvicorn cpow_api.server:app --port 8765`
- [ ] `curl http://127.0.0.1:8765/v1/health`
- [ ] Godot `cpow_client/godot` → 에리어 개척·입장
- [ ] `bash scripts/verify.sh`
