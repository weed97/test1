# TradingView 설치 방법 (중요)

## 모바일 사용자

휴대폰에서 **한 번에 붙여넣기가 안 되거나 코드가 한 줄로 합쳐지면** →  
**[모바일_설치가이드.md](./모바일_설치가이드.md)** (6조각 나눠 붙이기 포함)

---

## 왜 에러가 나는가?

Pine Script는 **Python처럼 들여쓰기(indent)가 필수**입니다.  
채팅·문서에서 복사하면 들여쓰기가 깨져서 **전체 코드가 한 블록 안에 들어가** 컴파일이 실패합니다.

---

## 올바른 설치 (3단계)

**버전: Pine Script v6** (`//@version=6`)

Pine Editor에서 v5로 열리면: **Manage script → Convert code to v6**

### 1) Raw 파일 전체 복사

GitHub에서 파일 열기 → **Raw** 버튼 → `Ctrl+A` → `Ctrl+C`

파일: `docs/tradingview/Crypto_Precision_Engine.pine`

### 2) Pine Editor에 붙여넣기

1. TradingView 차트 → 하단 **Pine Editor**
2. 기존 코드 **전부 삭제**
3. 붙여넣기 (`Ctrl+V`)
4. **Save** → **Add to chart**

### 3) 심볼·타임프레임

- `BINANCE:BTCUSDT` 또는 `BINANCE:ETHUSDT`
- 권장: 15m ~ 1h

---

## "Script too heavy" / 타임아웃 시

설정에서 줄이기:

| 설정 | 권장 |
|------|------|
| VP Lookback | 300 → **150** |
| VP Bins | 48 → **24** |
| Show VWAP S/R Zones | OFF |
| Show Distance Labels | OFF |
| S/R Lookback | 200 → **100** |

---

## 자주 나는 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `Mismatched input` | 들여쓰기 깨짐 | Raw 파일에서 다시 복사 |
| `Undeclared identifier` | if/for 블록 밖 변수 | 들여쓰기 수정 |
| `Script requests too many` | drawing 한도 | 존·라벨 옵션 OFF |
| `Calculation takes too long` | VP lookback 큼 | VP Lookback 줄이기 |

---

## Strategy (승률 백테스트)

승률 검증은 인디케이터가 아니라:

`docs/tradingview/Crypto_Precision_Engine_Strategy.pine`
