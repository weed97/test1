# 이세계 풀다이브 VR — 세계 설계 인덱스

에르도리아(Eldoria)를 **완전 몰입형 풀다이브 VR 이세계**로 운영하기 위한 설계 문서 모음입니다.  
구현은 `fantasy_simulator/` 엔진·콘텐츠와 1:1로 대응되도록 작성했습니다.

## 읽는 순서

| 문서 | 내용 |
|------|------|
| [00_VISION.md](00_VISION.md) | 비전, 기둥, 타깃 경험 |
| [01_FULLDIVE_PLATFORM.md](01_FULLDIVE_PLATFORM.md) | 풀다이브 기술·안전·세션·운영자 |
| [02_ISEKAI_FRAME.md](02_ISEKAI_FRAME.md) | 이전, 아바타, 신·관리자, 사망/로그아웃 |
| [03_WORLD_ATLAS.md](03_WORLD_ATLAS.md) | 대륙·지역·존·확장 로드맵 |
| [04_FACTIONS_AND_POLITICS.md](04_FACTIONS_AND_POLITICS.md) | 6+α 세력, 정치 루프, 플레이어 역할 |
| [05_NARRATIVE_ARCS.md](05_NARRATIVE_ARCS.md) | 메인·서브·시즌 아크, 결말 철학 |
| [06_SYSTEMS_MAP.md](06_SYSTEMS_MAP.md) | 엔진 모듈 ↔ VR 메타 상태 매핑 |
| [07_CONTENT_ROADMAP.md](07_CONTENT_ROADMAP.md) | 시즌·DLC·씨앗·퀘스트 계획 |
| [08_PLAYER_LOOPS.md](08_PLAYER_LOOPS.md) | 일상·소셜·경제·엔드게임 루프 |

## 현재 구현과의 관계

- **이미 플레이 가능:** 애쉬포인트 변경, `smoke_on_the_mountain` → `ashen_seal_cracking` 3단계 메인 스토리, 세력 평판, 긴장도, 150+ 이벤트 씨앗.
- **설계만 있는 레이어:** VR 로비, 현실-게임 이중 시간, 길드/파티 인스턴스, 서버 샤드 — `06_SYSTEMS_MAP.md`의 `flags.vr_meta` 확장으로 단계적 도입.

## 관련 문서

- [../ARCHITECTURE.md](../ARCHITECTURE.md) — 턴 엔진·LLM 라우팅
- [../LORE_AND_EVENTS.md](../LORE_AND_EVENTS.md) — lore/events 분리 원칙
- [../../lore/npcs.md](../../lore/npcs.md) — NPC 바이블
