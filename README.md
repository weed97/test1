# Medieval Fantasy Text MMORPG Mega Simulator

중세 판타지 세계를 텍스트 기반으로 플레이하는 대규모 시뮬레이터입니다.
NPC 대화, 세력 관계, 지역 경제, 퀘스트 진행, 장기 시뮬레이션을 하나의 엔진에서 다룹니다.

## 핵심 특징

- **월드 시뮬레이션**
  - 6개 지역(지형/위험도/번영도/자원/인접 경로)
  - 4개 세력(관계도, 영향력, 부, 외교 긴장)
  - 일 단위 날씨/이벤트/시장 가격 변동
- **NPC 대화 엔진**
  - 성향(`honor`, `warmth`, `greed`, `mystic`) 기반 톤
  - 플레이어 평판 + 대화 키워드 기반 호감도 변화
  - NPC별 대화 기억(memory) 누적
- **MMORPG 루프**
  - 이동, 사냥, 휴식, 거래(구매/판매/소비), 로그 조회
  - 퀘스트 수락/진행/완료
  - 경험치/레벨업/평판 보상
- **초대형 진행 감각**
  - `simulate <days>`로 대규모 장기 시뮬레이션(최대 365일)
  - 월드 상태를 압축적으로 업데이트하여 메가 단위 전개 가능

## 프로젝트 구조

```text
mmorpg_sim/
  __init__.py
  cli.py           # 실행 진입점
  commands.py      # 텍스트 명령 파서
  data.py          # 월드/NPC/퀘스트/아이템 데이터
  dialogue.py      # NPC 대화 생성 로직
  engine.py        # 메인 시뮬레이션 엔진
  models.py        # 도메인 모델(dataclass)
tests/
  test_engine.py
  test_dialogue.py
```

## 실행 방법

```bash
python -m mmorpg_sim.cli --name "Arin" --seed 1337
```

또는 설치 후:

```bash
pip install -e .
fantasy-mmorpg --name "Arin" --seed 1337
```

## 주요 커맨드

- `help`
- `status`
- `map`
- `look`
- `where`
- `travel <region_key>`
- `talk <npc_key_or_name> | <message>`
- `hunt`
- `rest`
- `inventory`
- `quests`
- `quest accept <quest_key>`
- `quest complete <quest_key>`
- `buy <item_key> [amount]`
- `sell <item_key> [amount]`
- `consume <item_key>`
- `logs [count]`
- `simulate <days>`

## 테스트

```bash
python -m pytest -q
```

## 확장 포인트

- 직업/스킬 트리/장비 강화
- 지역 점령전(세력전) 및 길드 단위 비동기 진행
- 월드 보스/레이드 시즌 이벤트
- 대사 템플릿을 규칙 기반 + 생성 모델 기반 하이브리드로 확장