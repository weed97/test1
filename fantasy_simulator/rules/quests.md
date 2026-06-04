# 퀘스트 & 평판 시스템

## 평판 (`flags.reputation`)

- 범위: -100 ~ 100 (마을·NPC별)
- `talk` 행동으로 NPC 평판 +2
- 이벤트 `outcome.reputation`으로 일괄 조정

## 퀘스트 (`events/quests.json`)

- `flags.quests.active` — 진행 중 ID
- `flags.quests.stage` — 현재 단계 (1-based)
- `quest` 명령으로 목표 확인

## 메인 아크: 산의 검은 연기

1. **1단계:** `talk torren`, `talk lilian`, `talk grey` — 정보 수집
2. **2단계:** `investigate forest` — 숲 외곽
3. **3단계:** `combat silver_stalker` — 관측탑 보스

## 이벤트 씨앗

- `explore` / `investigate` / `rest` / `talk` 시 `pending_events`에서 조건 맞는 씨앗 발동
- `requires_time`, `requires_action`으로 밤/낮 차별
- 발동 후 pending에서 제거, `event_log`에 한 줄만 기록
