# 이세계 초몰입 풀다이브 — 세계 설계 인덱스

에르도리아(Eldoria)를 **VR×BCI×Mnemosyne(딥마인드급 월드 모델) 융합**, **오감+육감 현실 동형**, **구분 불가능한 완전 이세계**로 운영하기 위한 설계 문서 모음입니다.  
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
| [09_BCI_DEEPMIND_FUSION.md](09_BCI_DEEPMIND_FUSION.md) | **VR×BCI×Mnemosyne 융합**, 육감, 샤드 AI |
| [10_REALITY_PARITY.md](10_REALITY_PARITY.md) | 현실 동형성 R0–R4 규격·검증 |

## 현재 구현과의 관계

- **이미 플레이 가능:** 애쉬포인트 변경, `smoke_on_the_mountain` → `ashen_seal_cracking` 3단계 메인 스토리, 세력 평판, 긴장도, 150+ 이벤트 씨앗.
- **설계만 있는 레이어:** BCI 읽기/쓰기, Mnemosyne 샤드 AI, 육감·체화, R3 현실 동형 — `flags.bci_meta` + `09`·`10` 문서.
- **스키마:** `config/vr_meta.schema.json`, `config/bci_meta.schema.json`

## 관련 문서

- [../ARCHITECTURE.md](../ARCHITECTURE.md) — 턴 엔진·LLM 라우팅
- [../LORE_AND_EVENTS.md](../LORE_AND_EVENTS.md) — lore/events 분리 원칙
- [../../lore/npcs.md](../../lore/npcs.md) — NPC 바이블
