# 모바일에서 cpow_world로 push하기

PC 터미널 없이 **GitHub 앱/브라우저**만으로 초기 push 하는 방법입니다.

**전용 repo:** https://github.com/weed97/cpow_world

---

## ⚠️ 403 `Permission denied to github-actions[bot]` 나올 때

```text
Permission to weed97/cpow_world.git denied to github-actions[bot]
```

→ 토큰은 맞는데 **checkout 이 bot 토큰을 git 에 남겨서** push 가 실패한 경우입니다.  
`main` 최신 워크플로(`persist-credentials: false`)로 다시 Run workflow 하세요.

### 토큰 재등록 (필요 시)

1. https://github.com/weed97/test1/settings/secrets/actions → `CPOW_WORLD_PUSH_TOKEN` 삭제 후 재등록  
2. Classic PAT: **`repo`** 전체 체크  
3. Fine-grained: 저장소 **`cpow_world`** 선택, **Contents: Read and write**

---

## 방법 A — Actions 버튼 (추천)

1. **먼저** [SYNC_CPOW_WORLD.md](SYNC_CPOW_WORLD.md) 에서 `CPOW_WORLD_PUSH_TOKEN` Secret 등록  
2. https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml  
3. **Run workflow** → Branch **`main`** → Run workflow  
4. https://github.com/weed97/cpow_world 에 `cpow_client/unity/`, `cpow_engine/world/` 확인

> 구버전 workflow는 `cpow-world` 브랜치만 push 했습니다. **main 최신**이면 Unity·월드 모듈이 포함됩니다.

---

## 방법 B — GitHub.dev (토큰 없이)

1. **https://github.dev/weed97/test1/tree/cpow-world**  
2. **Terminal** →  

```bash
git branch -M main
git remote set-url origin https://github.com/weed97/cpow_world.git
git push -u origin main
```

---

## 방법 C — PC

```bash
git clone -b cpow-world https://github.com/weed97/test1.git cpow_world
cd cpow_world
git branch -M main
git remote set-url origin https://github.com/weed97/cpow_world.git
git push -u origin main
```

---

## 확인

https://github.com/weed97/cpow_world 에 `cpow_engine/`, `cpow_api/`, `README.md` 가 보이면 완료입니다.
