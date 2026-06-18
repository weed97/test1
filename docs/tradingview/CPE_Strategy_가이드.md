# CPE Honest Strategy — 정직한 70% 승률에 대해

## 짧은 답

**70% 승률은 "특정 기간·타임프레임·엄격한 필터"에서는 백테스트에 나올 수 있습니다.**  
하지만 **영원히·모든 시장에서 70%를 보장하는 지표는 없습니다.**

`Crypto_Precision_Engine_Strategy.pine`은 승률 숫자를 **꾸며 넣지 않고**, TradingView `strategy()` 통계로 **실측**만 보여줍니다.

---

## 정직한 조건 (이 전략이 지키는 것)

| 원칙 | 구현 |
|------|------|
| 리페인팅 없음 | `barstate.isconfirmed` + `process_orders_on_close=true` |
| 미래 데이터 없음 | pivot은 `pivotleft/pivotright` 확정 후만 |
| 수수료 반영 | 0.04% (Binance taker 근사) |
| 슬리피지 | 2틱 |
| 승률 표시 | `strategy.wintrades / strategy.closedtrades` 실측만 |

---

## 70%에 가깝게 만들려면 (과최적화 주의)

설정에서 조절:

1. **Min Confluence Score** → `5` (신호 매우 적음, 품질↑)
2. **Take Profit × ATR** → `0.5~0.65` (작은 익절 = 승률↑, R:R↓)
3. **Stop Loss × ATR** → `1.2~1.5` (손절은 넓게)
4. 타임프레임 **15m~1h**, 심볼 **BINANCE:BTCUSDT** 등 유동성 높은 것

⚠️ 과거 6개월만 맞추면 70% 나와도, 다음 6개월은 45%일 수 있음 → **기간 바꿔서 여러 번 테스트**하세요.

---

## 설치

1. Pine Editor에 `Crypto_Precision_Engine_Strategy.pine` 붙여넣기
2. **Add to chart** (indicator가 아니라 **strategy**)
3. Strategy Tester 탭에서 Win rate / Profit factor 확인
4. 차트 왼쪽 하단 **Honest Stats** 테이블 = 동일 숫자

---

## 해석 가이드

| Win Rate | Profit Factor | 의미 |
|----------|---------------|------|
| 70%+ | > 1.3 | 좋은 구간 (기간 한정) |
| 55~65% | > 1.5 | 손익비로 충분히 수익 가능 |
| 70%+ | < 1.0 | 익절 작아 승률만 높고 **총손실** |
| < 50% | > 2.0 | 낮은 승률·큰 R:R 전략 |

**승률만 보면 안 됩니다.** Net Profit + Max Drawdown을 같이 보세요.

---

## 인디케이터 vs 전략

| 파일 | 용도 |
|------|------|
| `Crypto_Precision_Engine.pine` | 차트 분석·존·대시보드 |
| `Crypto_Precision_Engine_Strategy.pine` | **백테스트·승률 검증** |

분석은 인디케이터, 승률 검증은 전략 — 역할 분리가 정직합니다.
