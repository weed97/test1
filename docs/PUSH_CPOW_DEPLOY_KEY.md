# cpow_world 최초 push — Deploy Key (1회)

Cursor bot은 `weed97/cpow_world`에 쓰기 권한이 없습니다.  
**아래 공개키를 repo에 등록**하면 에이전트가 SSH로 push 합니다.

## 모바일에서 30초

1. https://github.com/weed97/cpow_world/settings/keys  
2. **Add deploy key**  
3. Title: `cloud-agent-push`  
4. Key (아래 전체 복사):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICXxx15zC/KHCT2pMK8MjHWwXyds+l1bWgRrZ+dR1Ptn cpow-world-push
```

5. ✅ **Allow write access** 체크  
6. **Add key**

등록 후 채팅에 **「키 추가함」** 이라고 보내 주세요.

## 또는 Actions (토큰 이미 있으면)

**PAT 만들기·Secret 등록:** [docs/SYNC_CPOW_WORLD.md](SYNC_CPOW_WORLD.md)

https://github.com/weed97/test1/actions/workflows/publish-cpow-world.yml  
→ Run workflow → (workflow 파일은 main 에서 checkout)
