# Crypto Precision Engine — 한국어 사용 가이드

## 설치 방법

1. TradingView 차트에서 **Pine Editor** 열기
2. `Crypto_Precision_Engine.pine` 전체 코드 붙여넣기
3. **Add to chart** 클릭
4. 권장 심볼: `BINANCE:BTCUSDT`, `BINANCE:ETHUSDT`, `BYBIT:BTCUSDT.P`, `BYBIT:ETHUSDT.P`
5. 권장 타임프레임: 5분 ~ 1시간 (스캘핑·데이트레이딩)

---

## SECTION 1: VWAP + 밴드

### 세션 VWAP
- **매일 세션 시작**부터 누적 VWAP입니다.
- 종가가 VWAP **위** → 녹색 선 (매수 우위)
- 종가가 VWAP **아래** → 빨간 선 (매도 우위)

### 표준편차 밴드 (±1σ ~ ±3σ)
- 가격이 VWAP에서 얼마나 벗어났는지 보여줍니다.
- ±1σ: 일반 변동 범위 (파란색)
- ±2σ: 확장 구간 (주황)
- ±3σ: 극단 구간 (빨강/라임) — 평균 회귀·반전 관찰

### 주간·월간 VWAP
- 설정에서 활성화 시 보라(주간)·주황(월간) 점선으로 표시
- 장기 기준 가격이 고평가/저평가인지 판단

### VWAP 존 (Zone)
- 각 밴드 주변에 ATR 기반 **박스 존** 표시
- **녹색**: 2회 이상 터치 후 반등 (지지)
- **빨강**: 2회 이상 터치 후 거부 (저항)
- **회색**: 돌파된 레벨 (무효)

---

## SECTION 2: 거래량 프로파일 + POC

### POC (Point of Control)
- 최근 N봉(기본 300)에서 **가장 많은 거래량**이 발생한 가격
- 노란 점선 — 시장이 가장 많이 거래한 "공정 가격"

### VAH / VAL (Value Area)
- 전체 거래량의 70%가 집중된 상·하단
- VAH 위 = 프리미엄 구간, VAL 아래 = 디스카운트 구간

### POC 존·HVN·LVN
- **POC 존** (금색): 최고 거래 밀집 구간 — 강한 지지/저항
- **HVN** (노란 박스): POC 외 거래량 상위 3구간
- **LVN** (회색 점선): 거래 공백 — 가격이 빠르게 통과하는 구간

### POC Strength Score
- 대시보드에서 확인
- **Strong (>15%)**: 강한 POC — 되돌림 매매에 유리
- **Medium (8~15%)**: 보통
- **Weak (<8%)**: 약함 — POC 신뢰도 낮음

---

## SECTION 3: 매수벽 / 매도벽

### 매수벽 (Buy Wall, BW)
- 대량 매수 + VWAP 아래 + 양봉/긴 아래꼬리
- **라임** 수평선 + 존 박스
- 💪 STRONG / ⚡ MODERATE 로 강도 표시

### 매도벽 (Sell Wall, SW)
- 대량 매도 + VWAP 위 + 음봉/긴 위꼬리
- **빨강** 수평선 + 존 박스

### 해석법
- 가격이 벽에 **도달 후 반등** → 벽 유효, 역추세 진입 고려
- **BW BROKEN** / **SW BROKEN** → 벽 돌파, 추세 지속 신호
- 벽은 기본 100봉 후 만료

---

## SECTION 4: 지지·저항 구간 (순지지/순저항)

### 순지지력 % (Net Support %)
```
순지지력 = (구간 터치 후 3봉 내 위로 마감한 횟수 / 총 터치) × 100
```
- **70% 이상 + 3회 이상 터치** → 🟢 Major Support (대형 지지)
- **50% 이상** → Minor Support (소형 지지)

### 순저항력 % (Net Resistance %)
```
순저항력 = (구간 터치 후 3봉 내 아래로 마감한 횟수 / 총 터치) × 100
```
- **70% 이상** → 🔴 Major Resistance
- **40~60%** → Neutral Zone (중립)

### 활용법
| 순지지력 | 해석 | 매매 |
|---------|------|------|
| ≥70% | 강한 지지 | 롱 진입·손절 아래 |
| 50~70% | 약한 지지 | 확인 후 진입 |
| 40~60% | 중립 | 관망 |
| 순저항 ≥70% | 강한 저항 | 숏·익절 구간 |

### 거리 라벨
- 현재가에서 가장 가까운 지지/저항 3개까지 ↓/↑ % 거리 표시

---

## SECTION 5: 오더북 시뮬레이터

### 한계 (중요)
TradingView는 **실시간 오더북 데이터에 접근할 수 없습니다.**  
이 모듈은 다음으로 **추정**합니다:
- ATR 기반 가격 레벨 간격
- 거래량·매수/매도벽 위치
- 가격 시드 의사 난수

### 활용법
- **BID DOMINANT (1.5x 이상)**: 매수 압력 우위 → 롱 바이어스
- **ASK DOMINANT (0.67x 이하)**: 매도 압력 우위 → 숏 바이어스
- **WALL 🧱** 표시: 실제 탐지된 매수/매도벽과 겹치는 레벨
- **POC⭐, MS🟢, MR🔴, V±σ** 태그: S/R·VWAP와 오더북 레벨 일치

### 실시간 오더북이 필요할 때
1. **Binance/Bybit WebSocket API** + 외부 서버 → TradingView `request.security()` 로 커스텀 심볼 피드
2. **3rd-party 데이터** (Bookmap, TensorCharts 등) 연동
3. 거래소 **Depth Chart** 를 별도 모니터와 병행

---

## SECTION 6: 대시보드 + 복합 시그널

### Signal 해석
| 시그널 | 조건 | 의미 |
|--------|------|------|
| LONG SETUP 🟢 | VWAP 위 + Major Support 근처 + Bid Dominant + Vol > 2x MA | 롱 셋업 |
| SHORT SETUP 🔴 | VWAP 아래 + Major Resistance 근처 + Ask Dominant + Vol > 2x MA | 숏 셋업 |
| NEUTRAL ⚪ | 위 조건 미충족 | 관망 |

### 권장 매매 흐름 (롱 예시)
1. 대시보드 **LONG SETUP** 확인
2. 가격이 **Major Support** (순지지 ≥70%) 근처
3. **BW** (매수벽) 또는 **POC 존**과 겹치는지 확인
4. VWAP 위에서 지지 확인 후 진입
5. 손절: 지지 존 아래 / 익절: Major Resistance 또는 VWAP +2σ

---

## 알림 설정

차트 → 알림 → 조건에서 다음 선택:
- VWAP 상향/하향 돌파
- POC Zone 진입
- Buy/Sell Wall 탐지·돌파
- Major Support/Resistance 진입
- Bid/Ask 불균형
- LONG/SHORT SETUP

---

## Pine Script 제한 사항

| 제한 | 설명 | 대응 |
|------|------|------|
| 오더북 없음 | 실제 호가 데이터 불가 | 시뮬레이터 + 외부 API |
| drawing 한도 | line 500, box 100, label 500 | 오래된 객체 자동 삭제 |
| VP 연산 | 300봉×48빈 매 바 계산 | lookback 줄이기 |
| S/R 클러스터 | pivot 50개 상한 | pivotLeft/Right 조정 |
| repainting 방지 | 확정 봉 기준 (`barstate.isconfirmed`) | 실시간 봉에서는 1봉 지연 |

---

## 권장 설정 (BTC/ETH 15분)

| 항목 | 값 |
|------|-----|
| VP Lookback | 300 |
| VP Bins | 48 |
| Wall Expiry | 100 |
| S/R Lookback | 200 |
| Show Dashboard | ON |
| Show Order Book | ON |
