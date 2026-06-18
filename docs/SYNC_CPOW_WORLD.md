# cpow_world 동기화 — PAT 설정 (5분)

`test1/main` 에 머지된 CPoW 코드(Unity·월드 모듈 포함)를  
**https://github.com/weed97/cpow_world** 에 올리는 방법입니다.

---

## 1단계 — Personal Access Token 만들기

1. GitHub 로그인 (**weed97** 계정)
2. **Settings** → **Developer settings** → **Personal access tokens**
3. 아래 둘 중 하나 선택:

### A) Fine-grained (권장)

| 항목 | 값 |
|------|-----|
| Repository access | **Only select** → `cpow_world` + `test1` |
| Permissions → Contents | **Read and write** |
| Permissions → Actions | **Read** (workflow 실행용, 선택) |

### B) Classic

- Scope: **`repo`** 전체 체크
- 만료: 90일 또는 No expiration (본인 정책에 맞게)

4. **Generate token** → 토큰 문자열 **복사** (다시 안 보임)

---

## 2단계 — test1에 Secret 등록

1. https://github.com/weed97/test1/settings/secrets/actions  
2. **New repository secret**
3. Name: `CPOW_WORLD_PUSH_TOKEN`  
4. Value: 위에서 복사한 PAT  
5. **Add secret**

---

## 3단계 — Actions로 push (모바일 가능)

1. https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml  
2. **Run workflow** → Branch **`main`** → **Run workflow**  
3. 1~2분 후 https://github.com/weed97/cpow_world 확인

포함되는 것:

- `cpow_engine/` (world 바이옴·채굴 포함)
- `cpow_api/`
- `cpow_client/unity/` + `godot/`(레거시)
- `docs/`, `tests/`, `scripts/verify.sh`

`fantasy_simulator` 등은 **제외**됩니다 (`scripts/export_cpow_world.sh`).

---

## 4단계 — 확인

https://github.com/weed97/cpow_world 에서:

- [ ] `cpow_client/unity/CPoWWorld/` 존재
- [ ] `cpow_engine/world/` 존재
- [ ] README에 Unity 안내
- [ ] Actions → Tests 워크플로 green

로컬:

```bash
git clone https://github.com/weed97/cpow_world.git
cd cpow_world
pip install -r requirements-api.txt
bash scripts/verify.sh
```

---

## PC에서 직접 push (PAT)

```bash
git clone https://github.com/weed97/test1.git
cd test1
bash scripts/export_cpow_world.sh /tmp/cpow_export
cd /tmp/cpow_export
git init && git add -A && git commit -m "Sync from test1/main"
git branch -M main
git remote add origin https://github.com/weed97/cpow_world.git
# 사용자명: weed97 / 비밀번호: PAT 붙여넣기
git push -u origin main --force
```

---

## 자주 나는 오류

| 오류 | 해결 |
|------|------|
| `CPOW_WORLD_PUSH_TOKEN secret is not set` | 2단계 Secret 등록 |
| `403 github-actions[bot]` | workflow 최신본 사용 (`persist-credentials: false`) |
| `Token cannot push` | Fine-grained → cpow_world **Contents: Write** |
| cpow_world에 Unity 없음 | workflow가 **main** 기준 export 인지 확인 (구버전은 `cpow-world` 브랜치만 push) |

---

## 이후 개발 흐름

1. **cpow_world** 에서 직접 작업 (권장)  
2. 또는 test1 `cpow_*` 수정 → Actions **Publish CPoW World** 재실행

관련: [MOBILE_PUSH_CPOW.md](MOBILE_PUSH_CPOW.md), [SPLIT_REPO.md](SPLIT_REPO.md)
