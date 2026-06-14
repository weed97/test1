#!/usr/bin/env python3
"""
CoinGlass API 실시간 오더북 / 대형 지정가 주문 피드

⚠️ CoinGlass API는 오픈소스가 아닙니다.
   - 웹사이트(coinglass.com) 오더북 UI → 개인 트레이더 무료 열람
   - API → 유료 플랜 + 본인 API 키 필요 (Hobbyist $29/월~)
   - 문서: https://docs.coinglass.com/reference/authentication

Pine Script는 이 API를 직접 호출할 수 없습니다.
터미널/대시보드에서 CoinGlass 데이터를 보고 TradingView 차트와 병행하세요.

Usage:
  export COINGLASS_API_KEY="your_key_here"
  python3 scripts/coinglass_orderbook_feed.py --symbol BTC --exchange Binance
  python3 scripts/coinglass_orderbook_feed.py --mode imbalance --symbol BTC --interval 1m
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE = "https://open-api-v4.coinglass.com"


def cg_get(path: str, params: dict[str, str], api_key: str) -> dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}{path}?{qs}"
    req = urllib.request.Request(
        url,
        headers={"accept": "application/json", "CG-API-KEY": api_key},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    if str(payload.get("code")) != "0":
        raise RuntimeError(payload.get("msg") or payload)
    return payload


def fetch_large_orders(
    api_key: str, exchange: str, symbol: str, market: str
) -> list[dict[str, Any]]:
    pair = f"{symbol}USDT" if not symbol.endswith("USDT") else symbol
    path = (
        "/api/futures/orderbook/large-limit-order"
        if market == "futures"
        else "/api/spot/orderbook/large-limit-order"
    )
    data = cg_get(path, {"exchange": exchange, "symbol": pair}, api_key)
    rows = data.get("data") or []
    return rows if isinstance(rows, list) else []


def fetch_imbalance(
    api_key: str, symbol: str, interval: str, market: str
) -> dict[str, Any]:
    coin = symbol.replace("USDT", "")
    if market == "futures":
        path = "/api/futures/orderbook/aggregated-ask-bids-history"
    else:
        path = "/api/spot/orderbook/aggregated-ask-bids-history"
    data = cg_get(
        path,
        {
            "exchange_list": "Binance,OKX,Bybit",
            "symbol": coin,
            "interval": interval,
            "limit": "1",
            "range": "1",
        },
        api_key,
    )
    rows = data.get("data") or []
    if not rows:
        raise RuntimeError("no imbalance data returned")
    return rows[-1]


def render_large(orders: list[dict[str, Any]], exchange: str, symbol: str) -> str:
    lines = [
        f"\n{'═' * 60}",
        f"  CoinGlass Large Limit Orders  |  {exchange} {symbol}",
        f"  (웹 UI와 동일 계열 — API 키 + 유료 플랜 필요)",
        f"{'═' * 60}",
        f"  {'SIDE':<6} {'PRICE':>12} {'USD VALUE':>14} {'QTY':>12}",
        f"  {'─' * 50}",
    ]
    if not orders:
        lines.append("  (현재 대형 지정가 없음)")
    for o in orders[:20]:
        price = float(o.get("price", 0))
        usd = float(o.get("current_usd_value", o.get("start_usd_value", 0)))
        qty = float(o.get("current_quantity", o.get("start_quantity", 0)))
        side = str(o.get("order_side", o.get("side", "?"))).upper()
        lines.append(f"  {side:<6} {price:>12,.2f} {usd:>14,.0f} {qty:>12.4f}")
    return "\n".join(lines)


def render_imbalance(row: dict[str, Any], symbol: str, interval: str) -> str:
    bids = float(row.get("aggregated_bids_usd", 0))
    asks = float(row.get("aggregated_asks_usd", 0))
    ratio = bids / asks if asks else 0
    if ratio > 1.5:
        tag = f"📈 BID DOMINANT ({ratio:.2f}x)"
    elif ratio < 0.67:
        tag = f"📉 ASK DOMINANT ({ratio:.2f}x)"
    else:
        tag = f"⚖ BALANCED ({ratio:.2f}x)"
    ts = int(row.get("time", 0))
    return (
        f"\n{'═' * 60}\n"
        f"  CoinGlass Aggregated Orderbook  |  {symbol}  interval={interval}\n"
        f"{'═' * 60}\n"
        f"  Bid USD (±1%):  {bids:,.0f}\n"
        f"  Ask USD (±1%):  {asks:,.0f}\n"
        f"  {tag}\n"
        f"  ts: {ts}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="CoinGlass orderbook feed (paid API key)")
    parser.add_argument("--api-key", default=os.environ.get("COINGLASS_API_KEY", ""))
    parser.add_argument("--symbol", default="BTC", help="BTC, ETH, BTCUSDT")
    parser.add_argument("--exchange", default="Binance")
    parser.add_argument(
        "--market", choices=["futures", "spot"], default="futures"
    )
    parser.add_argument(
        "--mode",
        choices=["large", "imbalance"],
        default="large",
        help="large=대형 지정가(웹 오더북 벽), imbalance=Bid/Ask 집계",
    )
    parser.add_argument("--interval", default="1m", help="imbalance mode only")
    parser.add_argument("--interval-sec", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if not args.api_key:
        print(
            "CoinGlass API 키가 필요합니다.\n"
            "  1) https://www.coinglass.com/pricing 에서 API 플랜 구독\n"
            "  2) 대시보드에서 API Key 발급\n"
            "  3) export COINGLASS_API_KEY='...' 또는 --api-key 전달\n\n"
            "※ 웹사이트 무료 열람 ≠ API 무료. 오픈소스 공개 키는 없습니다.\n"
            "※ 무료 대안: scripts/tradingview_orderbook_feed.py (Binance/Bybit 직접)",
            file=sys.stderr,
        )
        return 1

    while True:
        try:
            if args.mode == "large":
                orders = fetch_large_orders(
                    args.api_key, args.exchange, args.symbol, args.market
                )
                if sys.stdout.isatty():
                    sys.stdout.write("\033[2J\033[H")
                print(render_large(orders, args.exchange, args.symbol))
            else:
                row = fetch_imbalance(
                    args.api_key, args.symbol, args.interval, args.market
                )
                if sys.stdout.isatty():
                    sys.stdout.write("\033[2J\033[H")
                print(render_imbalance(row, args.symbol, args.interval))
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 401:
                print("  → API 키가 잘못되었거나 만료됨", file=sys.stderr)
            elif isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
                print("  → 플랜 권한 부족 (large-order는 Standard+ 필요할 수 있음)", file=sys.stderr)

        if args.once:
            break
        time.sleep(args.interval_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
