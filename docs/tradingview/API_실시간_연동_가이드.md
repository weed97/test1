# TradingView Pine Script + API 실시간 연동 — 가능한 것과 불가능한 것

## 핵심 답변

**Pine Script는 외부 API(HTTP/WebSocket)를 직접 호출할 수 없습니다.**

TradingView가 의도적으로 막아 둔 제한입니다. Pine에는 `fetch()`, `http.get()`, WebSocket 같은 기능이 없습니다.

그래서 "API 키 넣으면 차트에 실시간 오더북 붙이기"는 **순수 Pine만으로는 불가능**합니다.

---

## 그럼 뭐가 실시간인가?

| 데이터 | Pine에서 실시간? | 출처 |
|--------|------------------|------|
| 가격·거래량·캔들 | ✅ 예 | TradingView 거래소 피드 (Binance/Bybit 심볼) |
| VWAP, POC, 벽, S/R | ✅ 예 | 위 캔들 데이터로 매 틱/봉 갱신 |
| **실제 오더북 호가** | ❌ 아니오 | API 필요 → Pine 불가 |
| 시뮬레이터 오더북 | ⚠️ 추정치 | ATR + 거래량 기반 (현재 인디케이터) |

**Crypto Precision Engine** 인디케이터의 VWAP·POC·벽·S/R은 TradingView가 주는 BTC/ETH 캔들로 **이미 실시간 추적**됩니다.  
다만 **거래소 Depth(호가창)** 만 Pine으로는 못 가져옵니다.

---

## 실시간 오더북을 쓰는 3가지 현실적 방법

### 방법 1: 병행 모니터 (가장 쉬움) ✅

1. TradingView — Pine 인디케이터 (가격·VWAP·POC·벽·S/R)
2. 터미널 — 실시간 API 오더북 스크립트

```bash
# Binance BTC 실시간 호가 (1초 갱신)
python3 scripts/tradingview_orderbook_feed.py --symbol BTCUSDT --exchange binance

# Bybit ETH
python3 scripts/tradingview_orderbook_feed.py --symbol ETHUSDT --exchange bybit --levels 10

# JSON 파일로 저장 (외부 대시보드용)
python3 scripts/tradingview_orderbook_feed.py --symbol BTCUSDT --json-out /tmp/ob.json
```

Pine 시뮬레이터 테이블과 터미널 실제 호가를 **나란히** 보면서 매매합니다.

---

### 방법 2: 알림 Webhook (자동매매·봇 연동)

Pine → `alertcondition` → TradingView 알림 → **Webhook URL** → 내 서버

```
[TradingView Alert]
     │  HTTP POST (시그널만)
     ▼
[내 서버 / 봇]
     │  Binance·Bybit API
     ▼
[실제 주문 / 텔레그램 알림]
```

- 차트에 오더북을 그리는 게 아니라 **시그널을 밖으로 보내는** 방식
- LONG SETUP, BW BROKEN 등 알림을 서버에서 받아 API로 주문 가능
- Pine은 여전히 API를 "읽지"는 못함

**Webhook 예시 (TradingView 알림 메시지):**
```json
{"signal": "{{strategy.order.action}}", "price": "{{close}}", "ticker": "{{ticker}}"}
```

---

### 방법 3: 자체 차트 (TradingView Charting Library)

TradingView **웹사이트 Pine**이 아니라, **Charting Library**를 내 사이트에 embed하면:

- Binance WebSocket → 내 백엔드 → UDF 데이터피드 → 차트

이건 Pine Script가 아니라 **JavaScript + 백엔드** 개발입니다.  
완전 커스텀 실시간 오더북 히트맵이 필요하면 이쪽입니다.

---

## `request.security()`로 API 연동되나?

**아니요.** `request.security()`는 TradingView에 **이미 등록된 다른 심볼**의 데이터만 가져옵니다.

```pine
// ❌ 불가 — API URL을 넣을 수 없음
// data = request.security("https://api.binance.com/...", ...)

// ✅ 가능 — TV에 있는 거래소 심볼
btc1h = request.security("BINANCE:BTCUSDT", "60", close)
```

내 API 서버에서 만든 가짜 심볼을 TV에 올리는 것도 **일반 사용자에게는 불가**에 가깝습니다.

---

## 권장 트레이딩 워크플로 (BTC/ETH)

```
┌─────────────────────┐     ┌──────────────────────────┐
│  TradingView        │     │  터미널 / 2번 모니터      │
│  CPE Pine 인디케이터 │     │  orderbook_feed.py       │
│  · VWAP / POC       │     │  · 실제 Bid/Ask 10단     │
│  · 매수·매도벽       │     │  · Bid/Ask imbalance     │
│  · Major S/R        │     │  · Binance / Bybit API   │
│  · 대시보드 Signal  │     └──────────────────────────┘
└─────────────────────┘
         │
         │ 알림 (선택)
         ▼
┌─────────────────────┐
│  Webhook → 봇       │
│  자동매매 / 텔레그램  │
└─────────────────────┘
```

**롱 예시:**
1. Pine 대시보드 `LONG SETUP 🟢`
2. 터미널 오더북 `BID DOMINANT` 확인
3. Major Support + 실제 매수벽(대량 bid) 겹치면 진입

---

## API 키가 필요한가?

| 용도 | API 키 |
|------|--------|
| 공개 오더북 조회 (depth) | **불필요** (Binance/Bybit public endpoint) |
| **CoinGlass API** | **필요 + 유료 플랜** ($29/월 Hobbyist~) |
| 주문·잔고 | **필요** (별도 봇·서버에서만; Pine과 무관) |

`tradingview_orderbook_feed.py`는 **공개 REST API**만 사용하므로 키 없이 동작합니다.

---

## CoinGlass — 웹 무료 vs API 유료 (헷갈리기 쉬운 부분)

| | 웹사이트 (coinglass.com) | CoinGlass API |
|--|--------------------------|---------------|
| 오더북·청산·OI 보기 | ✅ 개인용 **무료** | ❌ 무료 티어 없음 (유료) |
| 오픈소스? | ❌ 상용 서비스 | ❌ **Open API**일 뿐, 오픈소스 아님 |
| 공개 API 키? | ❌ 없음 — **본인 키** 발급 | `CG-API-KEY` 헤더 필수 |
| Pine에서 직접 호출 | — | ❌ 불가 |

**"Open API"** = 문서 공개된 REST 인터페이스 (개발용)  
**"오픈소스"** = 소스·데이터가 무료로 공개 — **CoinGlass는 해당 없음**

### CoinGlass API로 뽑을 수 있는 오더북 데이터

문서: https://docs.coinglass.com/reference/endpoint-overview

| 엔드포인트 | 내용 | 실시간 |
|-----------|------|--------|
| `/api/futures/orderbook/large-limit-order` | 대형 지정가(벽) — 웹 UI와 유사 | ✅ Real-time |
| `/api/futures/orderbook/aggregated-ask-bids-history` | 거래소 합산 Bid/Ask (±range%) | interval별 |
| `/api/futures/orderbook/history` | 오더북 히트맵 | 히스토리 |

플랜별 제한 (예: Hobbyist는 interval ≥4h 등) — https://www.coinglass.com/pricing

### CoinGlass 스크립트 (API 키 있을 때)

```bash
export COINGLASS_API_KEY="발급받은_본인_키"
python3 scripts/coinglass_orderbook_feed.py --symbol BTC --exchange Binance
python3 scripts/coinglass_orderbook_feed.py --mode imbalance --symbol BTC --interval 1m
```

**Pine Script에는 여전히 못 넣습니다.** 터미널/자체 대시보드에서 CoinGlass + TradingView 병행.

---

## 요약

| 질문 | 답 |
|------|-----|
| Pine에 API 붙여서 실시간 오더북? | ❌ 불가 |
| Pine 인디케이터 실시간 가격 추적? | ✅ TV 피드로 이미 됨 |
| 실시간 호가 보려면? | ✅ Python 스크립트 또는 거래소 Depth |
| 시그널 자동화? | ✅ Pine Alert + Webhook |

Pine = **차트 분석·알림**, API = **실제 호가·주문** — 역할을 나누는 것이 현실적인 최선입니다.
