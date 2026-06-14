#!/usr/bin/env python3
"""
실시간 오더북 피드 (Binance / Bybit REST)
TradingView Pine Script는 API를 직접 호출할 수 없으므로,
이 스크립트를 별도 터미널에서 실행해 실제 호가를 모니터링합니다.

Pine 인디케이터의 시뮬레이터 오더북과 나란히 두고 비교하세요.

Usage:
  python3 scripts/tradingview_orderbook_feed.py --symbol BTCUSDT --exchange binance
  python3 scripts/tradingview_orderbook_feed.py --symbol ETHUSDT --exchange bybit --levels 10
  python3 scripts/tradingview_orderbook_feed.py --symbol BTCUSDT --json-out /tmp/ob.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class Level:
    price: float
    size: float


@dataclass
class OrderBook:
    symbol: str
    exchange: str
    bids: list[Level]
    asks: list[Level]
    mid: float
    spread_pct: float
    bid_total: float
    ask_total: float
    imbalance: float  # bid_total / ask_total

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "mid": self.mid,
            "spread_pct": round(self.spread_pct, 4),
            "bid_total": round(self.bid_total, 4),
            "ask_total": round(self.ask_total, 4),
            "imbalance": round(self.imbalance, 4),
            "bids": [{"price": b.price, "size": b.size} for b in self.bids],
            "asks": [{"price": a.price, "size": a.size} for a in self.asks],
            "ts": int(time.time()),
        }


def fetch_binance(symbol: str, levels: int) -> OrderBook:
    qs = urllib.parse.urlencode({"symbol": symbol.upper(), "limit": levels})
    url = f"https://api.binance.com/api/v3/depth?{qs}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    bids = [Level(float(p), float(s)) for p, s in data["bids"][:levels]]
    asks = [Level(float(p), float(s)) for p, s in data["asks"][:levels]]
    return _build_book(symbol, "binance", bids, asks)


def fetch_bybit(symbol: str, levels: int) -> OrderBook:
    # USDT perpetual: BTCUSDT on linear category
    qs = urllib.parse.urlencode(
        {"category": "linear", "symbol": symbol.upper(), "limit": levels}
    )
    url = f"https://api.bybit.com/v5/market/orderbook?{qs}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        payload = json.loads(resp.read().decode())
    result = payload["result"]
    bids = [Level(float(p), float(s)) for p, s in result["b"][:levels]]
    asks = [Level(float(p), float(s)) for p, s in result["a"][:levels]]
    return _build_book(symbol, "bybit", bids, asks)


def _build_book(
    symbol: str, exchange: str, bids: list[Level], asks: list[Level]
) -> OrderBook:
    if not bids or not asks:
        raise ValueError("empty order book")
    best_bid = bids[0].price
    best_ask = asks[0].price
    mid = (best_bid + best_ask) / 2.0
    spread_pct = (best_ask - best_bid) / mid * 100.0
    bid_total = sum(b.size for b in bids)
    ask_total = sum(a.size for a in asks)
    imbalance = bid_total / ask_total if ask_total else 1.0
    return OrderBook(
        symbol=symbol.upper(),
        exchange=exchange,
        bids=bids,
        asks=asks,
        mid=mid,
        spread_pct=spread_pct,
        bid_total=bid_total,
        ask_total=ask_total,
        imbalance=imbalance,
    )


def bar(value: float, max_value: float, width: int = 12) -> str:
    if max_value <= 0:
        return "░" * width
    filled = int(round(value / max_value * width))
    return "█" * filled + "░" * (width - filled)


def render(book: OrderBook) -> str:
    lines: list[str] = []
    lines.append(
        f"\n{'═' * 56}\n"
        f"  {book.exchange.upper()} {book.symbol}  |  mid {book.mid:,.2f}  "
        f"spread {book.spread_pct:.3f}%\n"
        f"{'═' * 56}"
    )
    max_sz = max(
        [a.size for a in book.asks] + [b.size for b in book.bids] + [1e-9]
    )
    lines.append(f"  {'PRICE':>12}  {'SIZE':>10}  BAR")
    lines.append(f"  {'─' * 40}")
    for ask in reversed(book.asks):
        lines.append(
            f"  {ask.price:>12,.2f}  {ask.size:>10.4f}  {bar(ask.size, max_sz)}  ASK"
        )
    lines.append(f"  {'▶ CURRENT':^40}")
    lines.append(f"  {book.mid:>12,.2f}")
    for bid in book.bids:
        lines.append(
            f"  {bid.price:>12,.2f}  {bid.size:>10.4f}  {bar(bid.size, max_sz)}  BID"
        )
    imb = book.imbalance
    if imb > 1.5:
        imb_txt = f"📈 BID DOMINANT ({imb:.2f}x)"
    elif imb < 0.67:
        imb_txt = f"📉 ASK DOMINANT ({imb:.2f}x)"
    else:
        imb_txt = f"⚖ BALANCED ({imb:.2f}x)"
    lines.append(f"  {'─' * 40}")
    lines.append(f"  Bid vol: {book.bid_total:.4f}  Ask vol: {book.ask_total:.4f}")
    lines.append(f"  {imb_txt}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="실시간 오더북 피드 (Binance/Bybit)")
    parser.add_argument("--symbol", default="BTCUSDT", help="e.g. BTCUSDT, ETHUSDT")
    parser.add_argument(
        "--exchange", choices=["binance", "bybit"], default="binance"
    )
    parser.add_argument("--levels", type=int, default=10, help="depth levels per side")
    parser.add_argument("--interval", type=float, default=1.0, help="poll seconds")
    parser.add_argument(
        "--json-out",
        help="write latest snapshot JSON (for external dashboards; Pine cannot read this)",
    )
    parser.add_argument("--once", action="store_true", help="fetch once and exit")
    args = parser.parse_args()

    fetcher = fetch_binance if args.exchange == "binance" else fetch_bybit

    while True:
        try:
            book = fetcher(args.symbol, args.levels)
            if args.json_out:
                with open(args.json_out, "w", encoding="utf-8") as f:
                    json.dump(book.to_dict(), f, indent=2)
            # clear screen (ANSI); skip if not a TTY
            if sys.stdout.isatty():
                sys.stdout.write("\033[2J\033[H")
            print(render(book))
            if args.json_out:
                print(f"\n  JSON → {args.json_out}")
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
            print(f"[error] {exc}", file=sys.stderr)

        if args.once:
            break
        time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
