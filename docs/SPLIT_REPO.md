# CPoW World — 별도 저장소 분리 가이드

`test1` 모노레포에서 CPoW 3D 시뮬레이터만 잘라내 새 GitHub repo로 옮기는 방법입니다.

## 복사할 경로

```text
cpow_engine/
cpow_api/
cpow_client/
docs/CPOW_*.md
docs/TODO_REMAINING.md
docs/HOST_SECURITY.md
docs/XR_INTEGRATION.md
docs/L1_PROTOCOL_ARCHITECTURE.md
docs/COLLABORATIVE_WORLD.md
docs/AREA_MODES.md
docs/CREATION_DESTRUCTION_POWERS.md
docs/PHYSICS_*.md
docs/SYSTEM_GOVERNANCE.md
docs/SPLIT_REPO.md          # 이 파일
tests/test_cpow_api_flow.py
scripts/verify_cpow.sh
requirements-cpow-api.txt
.github/workflows/cpow.yml
README_CPOW.md              # → README.md 로 이름 변경
.gitignore                  # Python/Godot 공통 항목
```

**남기는 것 (test1 / Eldoria):**

- `fantasy_simulator/` (2D RPG + Eldoria API)
- `sungjwa_hunter_sim/`, `mmorpg_sim/` 등 텍스트 시뮬

## 새 repo 초기화

```bash
# 1) 새 디렉터리
mkdir cpow-world && cd cpow-world
git init

# 2) test1에서 파일 복사 (예: cpow-world-scaffold 브랜치 체크아웃 후)
cp -r ../test1/cpow_engine ../test1/cpow_api ../test1/cpow_client .
cp -r ../test1/docs/CPOW*.md docs/
# ... (위 목록 참고)
cp ../test1/README_CPOW.md README.md
cp ../test1/requirements-cpow-api.txt .
cp ../test1/scripts/verify_cpow.sh scripts/
mkdir -p .github/workflows tests
cp ../test1/.github/workflows/cpow.yml .github/workflows/test.yml
cp ../test1/tests/test_cpow_api_flow.py tests/

# 3) 검증
pip install -r requirements-cpow-api.txt
bash scripts/verify_cpow.sh

# 4) push
git remote add origin git@github.com:weed97/cpow-world.git
git add .
git commit -m "Initial CPoW World scaffold"
git push -u origin main
```

## git subtree로 히스토리 유지 (선택)

엔진·클라이언트 커밋 히스토리만 가져오려면 test1에서:

```bash
git subtree split -P cpow_engine -b cpow-engine-history
git subtree split -P cpow_client -b cpow-client-history
# 새 repo에 각 브랜치 push 후 merge
```

`cpow_api/`는 `fantasy_simulator/api/cpow_*`에서 추출된 신규 코드라 subtree 히스토리가 없습니다.

## 실행 확인 체크리스트

- [ ] `python3 -m cpow_engine.demo --areas`
- [ ] `uvicorn cpow_api.server:app --port 8765`
- [ ] `curl http://127.0.0.1:8765/v1/health`
- [ ] Godot `cpow_client/godot` → 에리어 개척·입장
- [ ] `bash scripts/verify_cpow.sh` 통과

## test1 쪽 정리 (분리 후)

1. `main`에 CPoW 스캐폴드가 머지되어 있다면 `cpow_*` 디렉터리 제거 PR (선택)
2. `cursor/cpow-simulation-engine-9e0b` 브랜치 아카이브
3. 루트 `README.md`에서 CPoW → 새 repo 링크로 변경
