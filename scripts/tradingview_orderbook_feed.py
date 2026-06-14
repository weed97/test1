#!/usr/bin/env python3
"""
Binance / Bybit 무료 공개 오더북 피드 (API 키 불필요)

거래소 공개 Market Data = Security Type: NONE → 키 없이 무료
  - Binance Spot REST:    GET /api/v3/depth
  - Binance Futures REST: GET /fapi/v1/depth
  - Bybit Linear REST:    GET /v5/market/orderbook
  - WebSocket (--ws):     실시간 push (키 불필요)

Pine Script는 여전히 직접 호출 불가 → 이 스크립트를 터미널에서 실행.

Usage:
  python3 scripts/tradingview_orderbook_feed.py --exchange binance --market futures
  python3 scripts/tradingview_orderbook_feed.py --exchange bybit --symbol ETHUSDT --ws
  python3 scripts/tradingview_orderbook_feed.py --exchange binance --ws --levels 20
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Level:
    price: float
    size: float


@dataclass
class OrderBook:
    symbol: str
    exchange: str
    market: str
    bids: list[Level]
    asks: list[Level]
    mid: float
    spread_pct: float
    bid_total: float
    ask_total: float
    imbalance: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "market": self.market,
            "mid": self.mid,
            "spread_pct": round(self.spread_pct, 4),
            "bid_total": round(self.bid_total, 4),
            "ask_total": round(self.ask_total, 4),
            "imbalance": round(self.imbalance, 4),
            "bids": [{"price": b.price, "size": b.size} for b in self.bids],
            "asks": [{"price": a.price, "size": a.size} for a in self.asks],
            "ts": int(time.time()),
        }


def _build_book(
    symbol: str, exchange: str, market: str, bids: list[Level], asks: list[Level]
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
        market=market,
        bids=bids,
        asks=asks,
        mid=mid,
        spread_pct=spread_pct,
        bid_total=bid_total,
        ask_total=ask_total,
        imbalance=imbalance,
    )


def _http_get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def fetch_binance(symbol: str, levels: int, market: str) -> OrderBook:
    sym = symbol.upper()
    qs = urllib.parse.urlencode({"symbol": sym, "limit": levels})
    if market == "futures":
        url = f"https://fapi.binance.com/fapi/v1/depth?{qs}"
    else:
        url = f"https://api.binance.com/api/v3/depth?{qs}"
    data = _http_get(url)
    bids = [Level(float(p), float(s)) for p, s in data["bids"][:levels]]
    asks = [Level(float(p), float(s)) for p, s in data["asks"][:levels]]
    return _build_book(sym, "binance", market, bids, asks)


def fetch_bybit(symbol: str, levels: int, market: str) -> OrderBook:
    sym = symbol.upper()
    category = "linear" if market == "futures" else "spot"
    qs = urllib.parse.urlencode({"category": category, "symbol": sym, "limit": levels})
    url = f"https://api.bybit.com/v5/market/orderbook?{qs}"
    payload = _http_get(url)
    result = payload["result"]
    bids = [Level(float(p), float(s)) for p, s in result["b"][:levels]]
    asks = [Level(float(p), float(s)) for p, s in result["a"][:levels]]
    return _build_book(sym, "bybit", market, bids, asks)


# ── stdlib WebSocket (receive-only, no pip) ──────────────────────────────────

class SimpleWebSocket:
    """Minimal WebSocket client for public exchange depth streams."""

    def __init__(self, host: str, path: str) -> None:
        self._host = host
        self._sock: ssl.SSLSocket | None = None
        self._connect(host, path)

    def _connect(self, host: str, path: str) -> None:
        raw = socket.create_connection((host, 443), timeout=15)
        ctx = ssl.create_default_context()
        self._sock = ctx.wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        assert self._sock is not None
        self._sock.send(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket handshake failed")
            resp += chunk
        if b"101" not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(resp.decode(errors="replace")[:200])

    def recv_json(self) -> dict[str, Any]:
        assert self._sock is not None
        while True:
            hdr = self._recv_exact(2)
            b1, b2 = hdr[0], hdr[1]
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if b1 & 0x0F == 0x8:  # close
                raise ConnectionError("WebSocket closed by server")
            if b1 & 0x0F != 0x1:  # text only
                continue
            return json.loads(payload.decode())

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection lost")
            buf += chunk
        return buf

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None


def _parse_binance_ws(msg: dict[str, Any], levels: int) -> tuple[list[Level], list[Level]]:
    data = msg.get("data", msg)
    bids = [Level(float(p), float(s)) for p, s in data.get("b", data.get("bids", []))[:levels]]
    asks = [Level(float(p), float(s)) for p, s in data.get("a", data.get("asks", []))[:levels]]
    return bids, asks


def _parse_bybit_ws(msg: dict[str, Any], levels: int) -> tuple[list[Level], list[Level]]:
    data = msg.get("data", msg)
    bids = [Level(float(p), float(s)) for p, s in data.get("b", [])[:levels]]
    asks = [Level(float(p), float(s)) for p, s in data.get("a", [])[:levels]]
    return bids, asks


def ws_stream_binance(symbol: str, market: str, levels: int) -> SimpleWebSocket:
    sym = symbol.lower()
    depth = min(max(levels, 5), 20)  # partial depth supports 5/10/20
    if market == "futures":
        host = "fstream.binance.com"
        path = f"/ws/{sym}@depth{depth}@100ms"
    else:
        host = "stream.binance.com"
        path = f"/ws/{sym}@depth{depth}@100ms"
    return SimpleWebSocket(host, path)


def ws_stream_bybit(symbol: str, market: str, levels: int) -> tuple[SimpleWebSocket, str]:
    sym = symbol.upper()
    category = "linear" if market == "futures" else "spot"
    host = "stream.bybit.com"
    ws = SimpleWebSocket(host, "/v5/public/" + category)
    depth = min(max(levels, 1), 200)
    sub = {"op": "subscribe", "args": [f"orderbook.{depth}.{sym}"]}
    ws.send_json(sub)
    return ws, sym


# Add send to SimpleWebSocket
def _ws_send_json(self: SimpleWebSocket, obj: dict[str, Any]) -> None:
    payload = json.dumps(obj).encode()
    frame = bytearray([0x81])
    n = len(payload)
    mask = os.urandom(4)
    if n < 126:
        frame.append(0x80 | n)
    elif n < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack(">H", n))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack(">Q", n))
    frame.extend(mask)
    frame.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
    assert self._sock is not None
    self._sock.send(frame)


SimpleWebSocket.send_json = _ws_send_json  # type: ignore[method-assign]


def bar(value: float, max_value: float, width: int = 12) -> str:
    if max_value <= 0:
        return "░" * width
    filled = int(round(value / max_value * width))
    return "█" * filled + "░" * (width - filled)


def render(book: OrderBook, via: str = "REST") -> str:
    lines = [
        f"\n{'═' * 58}",
        f"  {book.exchange.upper()} {book.market.upper()} {book.symbol}  [{via}]  FREE · no API key",
        f"  mid {book.mid:,.2f}  spread {book.spread_pct:.3f}%",
        f"{'═' * 58}",
        f"  {'PRICE':>12}  {'SIZE':>10}  BAR",
        f"  {'─' * 42}",
    ]
    max_sz = max([a.size for a in book.asks] + [b.size for b in book.bids] + [1e-9])
    for ask in reversed(book.asks):
        lines.append(
            f"  {ask.price:>12,.2f}  {ask.size:>10.4f}  {bar(ask.size, max_sz)}  ASK"
        )
    lines.append(f"  {'▶ CURRENT':^42}")
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
    lines += [
        f"  {'─' * 42}",
        f"  Bid vol: {book.bid_total:.4f}  Ask vol: {book.ask_total:.4f}",
        f"  {imb_txt}",
    ]
    return "\n".join(lines)


def run_rest(
    fetcher: Callable[[str, int, str], OrderBook],
    symbol: str,
    levels: int,
    market: str,
    interval: float,
    json_out: str | None,
    once: bool,
) -> None:
    while True:
        try:
            book = fetcher(symbol, levels, market)
            if json_out:
                with open(json_out, "w", encoding="utf-8") as f:
                    json.dump(book.to_dict(), f, indent=2)
            if sys.stdout.isatty():
                sys.stdout.write("\033[2J\033[H")
            print(render(book, "REST"))
            if json_out:
                print(f"\n  JSON → {json_out}")
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
        if once:
            break
        time.sleep(interval)


def run_ws_binance(symbol: str, levels: int, market: str, json_out: str | None) -> None:
    sym = symbol.upper()
    while True:
        try:
            ws = ws_stream_binance(sym, market, levels)
            while True:
                msg = ws.recv_json()
                bids, asks = _parse_binance_ws(msg, levels)
                if bids and asks:
                    book = _build_book(sym, "binance", market, bids, asks)
                    if json_out:
                        with open(json_out, "w", encoding="utf-8") as f:
                            json.dump(book.to_dict(), f, indent=2)
                    if sys.stdout.isatty():
                        sys.stdout.write("\033[2J\033[H")
                    print(render(book, "WebSocket"))
        except (ConnectionError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[ws reconnect] {exc}", file=sys.stderr)
            time.sleep(2)


def run_ws_bybit(symbol: str, levels: int, market: str, json_out: str | None) -> None:
    sym = symbol.upper()
    depth = min(max(levels, 1), 200)
    while True:
        try:
            ws, _ = ws_stream_bybit(sym, market, depth)
            while True:
                msg = ws.recv_json()
                if msg.get("topic", "").startswith("orderbook") and msg.get("type") in (
                    "snapshot",
                    "delta",
                ):
                    bids, asks = _parse_bybit_ws(msg, levels)
                    if bids and asks:
                        book = _build_book(sym, "bybit", market, bids, asks)
                        if json_out:
                            with open(json_out, "w", encoding="utf-8") as f:
                                json.dump(book.to_dict(), f, indent=2)
                        if sys.stdout.isatty():
                            sys.stdout.write("\033[2J\033[H")
                        print(render(book, "WebSocket"))
        except (ConnectionError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[ws reconnect] {exc}", file=sys.stderr)
            time.sleep(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="무료 공개 오더북 (Binance/Bybit, API 키 불필요)"
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--exchange", choices=["binance", "bybit"], default="binance")
    parser.add_argument(
        "--market",
        choices=["spot", "futures"],
        default="futures",
        help="futures=USDT perpetual (TradingView BYBIT:BTCUSDT.P 등)",
    )
    parser.add_argument("--levels", type=int, default=10)
    parser.add_argument("--interval", type=float, default=1.0, help="REST poll seconds")
    parser.add_argument("--ws", action="store_true", help="WebSocket 실시간 (권장)")
    parser.add_argument("--json-out", help="JSON snapshot path")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.ws:
        if args.exchange == "binance":
            run_ws_binance(args.symbol, args.levels, args.market, args.json_out)
        else:
            run_ws_bybit(args.symbol, args.levels, args.market, args.json_out)
        return 0

    fetcher = fetch_binance if args.exchange == "binance" else fetch_bybit
    run_rest(fetcher, args.symbol, args.levels, args.market, args.interval, args.json_out, args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
