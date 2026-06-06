# 중세 판타지 아이템 도감 (Medieval Fantasy Item List)

중세 판타지 세계관의 아이템을 모아놓은 인터랙티브 웹 도감입니다.
무기, 방어구, 물약, 마법 도구, 장신구, 재료 등 다양한 아이템을 분류·등급·검색으로 탐색할 수 있습니다.

## 주요 기능

- **분류 필터**: 무기 / 방어구 / 물약 / 마법 도구 / 장신구 / 재료
- **등급 필터**: 일반 · 고급 · 희귀 · 영웅 · 전설 (색상으로 구분)
- **검색**: 아이템 이름과 설명으로 실시간 검색
- **상세 정보**: 각 아이템의 능력치, 무게, 가치(골드) 표시
- 반응형 레이아웃 + 중세 판타지 테마 UI (외부 의존성 없는 순수 HTML/CSS/JS)

## 실행 방법

`fetch`로 JSON을 불러오기 때문에 간단한 로컬 서버에서 실행해야 합니다.

```bash
# Python 3
python3 -m http.server 8000

# 또는 Node.js
npx serve .
```

브라우저에서 `http://localhost:8000` 으로 접속하세요.

## 파일 구조

```
.
├── index.html       # 페이지 구조
├── styles.css       # 중세 판타지 테마 스타일
├── app.js           # 렌더링·검색·필터 로직
└── data/
    └── items.json   # 아이템 데이터 (분류·등급·아이템 목록)
```

## 아이템 데이터 추가하기

`data/items.json` 의 `items` 배열에 항목을 추가하면 자동으로 화면에 반영됩니다.

```json
{
  "id": "고유-id",
  "name": "아이템 이름",
  "category": "weapon",
  "rarity": "rare",
  "icon": "🗡️",
  "value": 100,
  "weight": 2.0,
  "description": "설명 텍스트",
  "stats": { "공격력": 20, "내구도": 100 }
}
```

- `category` 는 `weapon` / `armor` / `potion` / `magic` / `accessory` / `material` 중 하나
- `rarity` 는 `common` / `uncommon` / `rare` / `epic` / `legendary` 중 하나
