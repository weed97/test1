# 모바일에서 cpow-world로 push하기

PC 터미널 없이 **GitHub 앱/브라우저**만으로 초기 push 하는 방법입니다.

## 방법 A — Actions 버튼 (추천, 1회 설정)

### 1) 토큰 만들기 (브라우저, 2분)

1. https://github.com/settings/tokens → **Generate new token (classic)**
2. Note: `cpow-world-push`
3. Scope: **`repo`** 체크
4. 생성 후 토큰 문자열 **복사** (한 번만 보임)

### 2) test1에 시크릿 등록

1. https://github.com/weed97/test1/settings/secrets/actions
2. **New repository secret**
3. Name: `CPOW_WORLD_PUSH_TOKEN`
4. Value: 위에서 복사한 토큰 → Save

### 3) 워크플로 실행 (모바일 OK)

1. https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml
2. **Run workflow** → Run workflow
3. 완료 후 https://github.com/weed97/cpow-world 에 코드 확인

---

## 방법 B — GitHub.dev 터미널 (토큰 없이, 로그인만)

1. 모바일 Chrome/Safari에서 열기:  
   **https://github.dev/weed97/test1/tree/cpow-world**
2. 하단 **Terminal** 탭 (또는 메뉴 → Terminal)
3. 아래 입력:

```bash
git branch -M main
git remote set-url origin https://github.com/weed97/cpow-world.git
git push -u origin main
```

4. GitHub 로그인 창이 뜨면 승인

---

## 방법 C — 나중에 PC에서

```bash
git clone -b cpow-world https://github.com/weed97/test1.git cpow-world
cd cpow-world
git branch -M main
git remote set-url origin https://github.com/weed97/cpow-world.git
git push -u origin main
```

---

## 확인

push 성공 후 repo에 `cpow_engine/`, `README.md` 등이 보이면 완료입니다.
