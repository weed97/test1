# 무료 실시간 연동 가이드 (Binance / Bybit)

## 구성

| 구분 | 도구 | 비용 |
|------|------|------|
| 차트 분석 | `Crypto_Precision_Engine.pine` | 무료 (TradingView) |
| **실제 오더북** | `scripts/tradingview_orderbook_feed.py` | **무료** (API 키 불필요) |
| Pine Wall Pressure | 캔들·매수/매도벽 기반 추정 | 무료 (기본 OFF) |

---

## Pine Script 제한

Pine은 HTTP/WebSocket 호출 불가 → **실제 호가는 터미널 스크립트**로 봅니다.

| 데이터 | Pine | 무료 터미널 |
|--------|------|-------------|
| VWAP·POC·벽·S/R | ✅ 실시간 | — |
| 실제 Bid/Ask depth | ❌ | ✅ WebSocket |

---

## 오더북 스크립트 (기본 WebSocket)

```bash
# Binance BTC 선물 (기본값)
python3 scripts/tradingview_orderbook_feed.py

# Bybit ETH 선물
python3 scripts/tradingview_orderbook_feed.py -e bybit -s ETHUSDT

# REST 폴백 (WS 막힐 때)
python3 scripts/tradingview_orderbook_feed.py --rest --interval 1

# 1회만 조회
python3 scripts/tradingview_orderbook_feed.py --once
```

**의존성:** Python 3.10+ stdlib만 (pip·API 키 불필요)

---

## 무료 API 엔드포인트

**Binance USDT-M**
- REST: `https://fapi.binance.com/fapi/v1/depth`
- WS: `wss://fstream.binance.com/ws/btcusdt@depth10@100ms`

**Bybit Linear**
- REST: `https://api.bybit.com/v5/market/orderbook?category=linear`
- WS: `wss://stream.bybit.com/v5/public/linear`

---

## 권장 워크플로

```
TradingView (Pine)          터미널 (무료 WS)
  VWAP / POC / 벽     +     실제 10단 호가
  Major S/R                 Bid/Ask imbalance
  LONG/SHORT 시그널           스프레드
```

**롱 예시:** Pine `LONG SETUP` + 터미널 `BID 1.5x+` + Major Support 근처

---

## Pine Wall Pressure (선택)

설정 `Show Wall Pressure Table` — 기본 **OFF** (성능 최적화)  
켜면 매수/매도벽·S/R 태그만 표시 (랜덤·유료 데이터 없음)

실제 호가는 반드시 `tradingview_orderbook_feed.py` 사용.

---

## 알림 Webhook (선택·무료)

Pine Alert → Webhook → 본인 서버/텔레그램 봇  
주문 API 키는 자동매매할 때만 필요 (오더북 조회와 무관).
