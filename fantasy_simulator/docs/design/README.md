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
| [11_TEMPORAL_MODEL.md](11_TEMPORAL_MODEL.md) | **턴 vs 초몰입** — 3층 시간·RTwP·API 로드맵 |
| [12_MICRO_TIME_AND_COCREATION.md](12_MICRO_TIME_AND_COCREATION.md) | **분 단위 시계**·공동 창조 루프 |
| [13_ISEKAI_AFFORDANCES.md](13_ISEKAI_AFFORDANCES.md) | 현실 불가 행위·이세계 계약 |
| [14_CONTRIBUTION_PERMISSIONS.md](14_CONTRIBUTION_PERMISSIONS.md) | **기여도→권한**·성장 목표·디테일 게이트 |
| [15_GODOT_RELEASE_ARCHITECTURE.md](15_GODOT_RELEASE_ARCHITECTURE.md) | **Godot 클라이언트**·API·출시 구조 |
| [16_CUSTOM_ENGINE_VS_GODOT_CLIENT.md](16_CUSTOM_ENGINE_VS_GODOT_CLIENT.md) | **우리 엔진 vs Godot**·몰입·비용 (무료/유료 구분) |
| [19_SPATIAL_SIMULATION.md](19_SPATIAL_SIMULATION.md) | **Godot 타일 ↔ 시뮬 좌표**·존·맵 전환 |
| [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md) | **살아 있는 필드**·NPC/몬스터 스킬·탐험 중심 생태계 |
| [21_PLAYER_SETTLEMENT_BUILDING.md](21_PLAYER_SETTLEMENT_BUILDING.md) | **플레이어 건설**·건축 Lv·고용·대장간·왕국 |
| [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md) | **성장**·직업/스킬/장비·몬스터 진화·맵 스폰 한도 |
| [23_WORLD_SCALE_AND_TEN_CONTINENTS.md](23_WORLD_SCALE_AND_TEN_CONTINENTS.md) | **행성 에르도리아**·5종족 영역·왕국·마을 |
| [24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md](24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md) | **에르도리아=시스템·행성**·MMO 독점 억제·전력 분산 |
| [25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md](25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md) | **몬스터 문명**·라이벌 경쟁·NPC 번영 |
| [26_WORLD_WARS_AND_APEX_THREATS.md](26_WORLD_WARS_AND_APEX_THREATS.md) | **월드 전쟁**·침입 목적·최상위 위협·연합 방어 |
| [27_ECOLOGY_AGENT_OBJECTS.md](27_ECOLOGY_AGENT_OBJECTS.md) | **ecology_agent 객체**·HP/MP/스킬·지성·Godot 스프라이트 |
| [28_PARALLEL_BEAT.md](28_PARALLEL_BEAT.md) | **병렬 비트**·연출 스태거 |
| [34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md) | **준신 주권**·엑스칼리버·4년 소원·아서 승계 |
| [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md) | **무기 클래스별** 직업·레벨·경지 (들기≠착용) |
| [36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md](36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md) | **등급** 준신~일반 · **레벨 우선** |
| [37_ARTHUR_AND_MONSTER_GRAND_COALITION.md](37_ARTHUR_AND_MONSTER_GRAND_COALITION.md) | **아서** · 대몬스터 연합 · 검주 보스 |
| [38_COMBAT_POWER.md](38_COMBAT_POWER.md) | **전투력** · 직업 스탯 루트 · 장비별 능력·등급 스킬 |
| [39_PRECISION_COMBAT_MATH.md](39_PRECISION_COMBAT_MATH.md) | **0.001** 데미지·방어·회피·크리 · 밸런스 |
| [40_STAT_PRECISION_AND_SOVEREIGN_SURVIVAL.md](40_STAT_PRECISION_AND_SOVEREIGN_SURVIVAL.md) | 물리/마법·99.999% 방어·만타·아서 회복 |
| [41_ARTHUR_SIEGE_MATH.md](41_ARTHUR_SIEGE_MATH.md) | **아서 공성 수학** · 연합 병렬·즉사·160만 DPS 앵커 |
| [42_DEMIGOD_HP_AND_ARMOR_PIERCE.md](42_DEMIGOD_HP_AND_ARMOR_PIERCE.md) | **준신 HP 100만** · 방무 9999 · 필멸 99,999 |
| [43_WORLD_PIERCE_ELITES.md](43_WORLD_PIERCE_ELITES.md) | **2~11위** 방무 정예 · 신화 10% · 합산 5000 DPS |

## 현재 구현과의 관계

- **이미 플레이 가능:** 애쉬포인트 변경, `smoke_on_the_mountain` → `ashen_seal_cracking` 3단계 메인 스토리, 세력 평판, 긴장도, 150+ 이벤트 씨앗. 플레이 시간: **Classic** (테스트·라우트), **Nex** (`--nex`), **Precision** (`--precision`, 분 시계).
- **설계만 있는 레이어:** BCI 읽기/쓰기, Mnemosyne 샤드 AI, 육감·체화, R3 현실 동형 — `flags.bci_meta` + `09`·`10` 문서.
- **스키마:** `config/vr_meta.schema.json`, `config/bci_meta.schema.json`, `config/contributor_meta.schema.json`
- **월드빌딩:** `utils/contrib_permissions.py` — 기여도·티어·`can()` (T1 훅)

## 관련 문서

- [../ARCHITECTURE.md](../ARCHITECTURE.md) — 턴 엔진·LLM 라우팅
- [../LORE_AND_EVENTS.md](../LORE_AND_EVENTS.md) — lore/events 분리 원칙
- [../../lore/npcs.md](../../lore/npcs.md) — NPC 바이블
