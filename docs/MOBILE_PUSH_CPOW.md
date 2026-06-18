# 모바일에서 cpow-world로 push하기

PC 터미널 없이 **GitHub 앱/브라우저**만으로 초기 push 하는 방법입니다.

---

## ⚠️ 403 `Permission denied to github-actions[bot]` 나올 때

Actions 로그에 이렇게 보이면 **토큰 권한 문제**입니다:

```text
Permission to weed97/cpow-world.git denied
```

### 해결 (weed97 계정으로 로그인한 브라우저에서)

1. **기존 시크릿 삭제**  
   https://github.com/weed97/test1/settings/secrets/actions  
   → `CPOW_WORLD_PUSH_TOKEN` 있으면 **Remove**

2. **새 토큰 — Classic 권장**  
   https://github.com/settings/tokens → **Generate new token (classic)**  
   - Note: `cpow-world-push`  
   - Expiration: 90 days (원하는 기간)  
   - ✅ **`repo`** 전체 체크 (private repo면 필수)  
   - Generate → `ghp_...` 로 시작하는 문자열 **전부 복사**

   > Fine-grained 쓸 경우:  
   > https://github.com/settings/tokens?type=beta  
   > - Repository access: **Only select** → **`cpow-world`만** 선택  
   > - Permissions → **Contents: Read and write**  
   > - Metadata는 Read (기본)

3. **시크릿 다시 등록**  
   https://github.com/weed97/test1/settings/secrets/actions  
   - Name: `CPOW_WORLD_PUSH_TOKEN` (철자 정확히)  
   - Secret: 붙여넣기 (앞뒤 공백 없이)

4. **워크플로 재실행**  
   https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml  
   → **Run workflow**

---

## 방법 A — Actions 버튼 (추천)

위 403 해결 후:

1. https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml  
2. **Run workflow** → Run workflow  
3. https://github.com/weed97/cpow-world 에 `cpow_engine/` 등 확인

---

## 방법 B — GitHub.dev (토큰 없이, 더 쉬울 수 있음)

**weed97**으로 로그인한 모바일 브라우저에서:

1. 열기: **https://github.dev/weed97/test1/tree/cpow-world**  
   (일반 github.com 말고 **github.dev** 주소)

2. 메뉴(≡) → **Terminal** (터미널)

3. 한 줄씩 입력:

```bash
git branch -M main
git remote set-url origin https://github.com/weed97/cpow-world.git
git push -u origin main
```

4. GitHub 로그인/권한 창 → **Authorize**  
   (본인 계정이면 토큰 없이 push 됨)

---

## 방법 C — PC에서 나중에

```bash
git clone -b cpow-world https://github.com/weed97/test1.git cpow-world
cd cpow-world
git branch -M main
git remote set-url origin https://github.com/weed97/cpow-world.git
git push -u origin main
```

---

## 확인

push 성공 후 https://github.com/weed97/cpow-world 에  
`cpow_engine/`, `cpow_api/`, `README.md` 가 보이면 완료입니다.
