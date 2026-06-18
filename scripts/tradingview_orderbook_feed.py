#!/usr/bin/env python3
"""
Binance / Bybit 무료 실시간 오더북 (API 키 불필요 · stdlib only)

기본: WebSocket 실시간 push
폴백: --rest (방화벽/네트워크 제한 시)

  python3 scripts/tradingview_orderbook_feed.py
  python3 scripts/tradingview_orderbook_feed.py -e bybit -s ETHUSDT
  python3 scripts/tradingview_orderbook_feed.py --rest --once
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
from dataclasses import dataclass, field
from typing import Any, Callable

# ── data ─────────────────────────────────────────────────────────────────────

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
    mid: float = 0.0
    spread_pct: float = 0.0
    bid_total: float = 0.0
    ask_total: float = 0.0
    imbalance: float = 1.0

    def finalize(self) -> OrderBook:
        if not self.bids or not self.asks:
            raise ValueError("empty order book")
        bb, ba = self.bids[0].price, self.asks[0].price
        self.mid = (bb + ba) / 2.0
        self.spread_pct = (ba - bb) / self.mid * 100.0 if self.mid else 0.0
        self.bid_total = sum(b.size for b in self.bids)
        self.ask_total = sum(a.size for a in self.asks)
        self.imbalance = self.bid_total / self.ask_total if self.ask_total else 1.0
        return self

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


@dataclass
class LocalBook:
    """Bybit delta stream용 로컬 호가창."""
    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)

    def apply(self, side: str, rows: list[list[str]]) -> None:
        book = self.bids if side == "b" else self.asks
        for p, s in rows:
            price, size = float(p), float(s)
            if size == 0:
                book.pop(price, None)
            else:
                book[price] = size

    def levels(self, n: int) -> tuple[list[Level], list[Level]]:
        bids = [Level(p, s) for p, s in sorted(self.bids.items(), reverse=True)[:n]]
        asks = [Level(p, s) for p, s in sorted(self.asks.items())[:n]]
        return bids, asks

    def load_snapshot(self, bids: list[list[str]], asks: list[list[str]]) -> None:
        self.bids = {float(p): float(s) for p, s in bids if float(s) > 0}
        self.asks = {float(p): float(s) for p, s in asks if float(s) > 0}


# ── REST (무료 공개) ─────────────────────────────────────────────────────────

def _http_get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def fetch_rest(exchange: str, symbol: str, levels: int, market: str) -> OrderBook:
    sym = symbol.upper()
    if exchange == "binance":
        qs = urllib.parse.urlencode({"symbol": sym, "limit": levels})
        base = "https://fapi.binance.com/fapi/v1" if market == "futures" else "https://api.binance.com/api/v3"
        data = _http_get(f"{base}/depth?{qs}")
        bids = [Level(float(p), float(s)) for p, s in data["bids"][:levels]]
        asks = [Level(float(p), float(s)) for p, s in data["asks"][:levels]]
    else:
        cat = "linear" if market == "futures" else "spot"
        qs = urllib.parse.urlencode({"category": cat, "symbol": sym, "limit": levels})
        data = _http_get(f"https://api.bybit.com/v5/market/orderbook?{qs}")
        r = data["result"]
        bids = [Level(float(p), float(s)) for p, s in r["b"][:levels]]
        asks = [Level(float(p), float(s)) for p, s in r["a"][:levels]]
    return OrderBook(sym, exchange, market, bids, asks).finalize()


# ── WebSocket (stdlib) ───────────────────────────────────────────────────────

class Ws:
    def __init__(self, host: str, path: str) -> None:
        sock = ssl.create_default_context().wrap_socket(
            socket.create_connection((host, 443), timeout=15), server_hostname=host
        )
        key = base64.b64encode(os.urandom(16)).decode()
        sock.send(
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += sock.recv(4096)
        if b"101" not in buf.split(b"\r\n", 1)[0]:
            raise ConnectionError("handshake failed")
        self._sock = sock

    def send_json(self, obj: dict[str, Any]) -> None:
        payload = json.dumps(obj).encode()
        mask = os.urandom(4)
        hdr = bytearray([0x81])
        n = len(payload)
        hdr.append(0x80 | (126 if n >= 126 else n))
        if n >= 126:
            hdr.extend(struct.pack(">H", n))
        hdr.extend(mask)
        hdr.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        self._sock.send(hdr)

    def recv_json(self) -> dict[str, Any]:
        while True:
            h = self._recv(2)
            op, b2 = h[0] & 0x0F, h[1]
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._recv(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._recv(8))[0]
            if b2 & 0x80:
                self._recv(4)
            payload = self._recv(ln)
            if op == 8:
                raise ConnectionError("closed")
            if op == 1:
                return json.loads(payload.decode())

    def _recv(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            c = self._sock.recv(n - len(buf))
            if not c:
                raise ConnectionError("lost")
            buf += c
        return buf

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


def connect_ws(exchange: str, symbol: str, market: str, levels: int) -> tuple[Ws, LocalBook | None]:
    sym_l, sym_u = symbol.lower(), symbol.upper()
    if exchange == "binance":
        depth = min(max(levels, 5), 20)
        host = "fstream.binance.com" if market == "futures" else "stream.binance.com"
        return Ws(host, f"/ws/{sym_l}@depth{depth}@100ms"), None
    cat = "linear" if market == "futures" else "spot"
    ws = Ws("stream.bybit.com", f"/v5/public/{cat}")
    d = min(max(levels, 1), 50)
    ws.send_json({"op": "subscribe", "args": [f"orderbook.{d}.{sym_u}"]})
    return ws, LocalBook()


def parse_ws_msg(
    exchange: str, msg: dict[str, Any], levels: int, local: LocalBook | None
) -> tuple[list[Level], list[Level]] | None:
    if exchange == "binance":
        d = msg.get("data", msg)
        bids = [Level(float(p), float(s)) for p, s in d.get("b", [])[:levels]]
        asks = [Level(float(p), float(s)) for p, s in d.get("a", [])[:levels]]
        return (bids, asks) if bids and asks else None
    if not msg.get("topic", "").startswith("orderbook"):
        return None
    d = msg["data"]
    assert local is not None
    if msg["type"] == "snapshot":
        local.load_snapshot(d.get("b", []), d.get("a", []))
    else:
        local.apply("b", d.get("b", []))
        local.apply("a", d.get("a", []))
    bids, asks = local.levels(levels)
    return (bids, asks) if bids and asks else None


# ── display ───────────────────────────────────────────────────────────────────

def _bar(v: float, mx: float, w: int = 10) -> str:
    n = int(round(v / mx * w)) if mx > 0 else 0
    return "█" * n + "░" * (w - n)


def render(book: OrderBook, via: str) -> str:
    mx = max([x.size for x in book.asks + book.bids] + [1e-9])
    lines = [
        f"\n{'═' * 54}",
        f"  {book.exchange.upper()} {book.market} {book.symbol}  [{via}]  FREE",
        f"  mid {book.mid:,.2f}  spread {book.spread_pct:.3f}%",
        f"{'═' * 54}",
    ]
    for a in reversed(book.asks):
        lines.append(f"  {a.price:>11,.2f}  {a.size:>9.4f}  {_bar(a.size, mx)}  ASK")
    lines.append(f"  {'▶':^40}")
    lines.append(f"  {book.mid:>11,.2f}")
    for b in book.bids:
        lines.append(f"  {b.price:>11,.2f}  {b.size:>9.4f}  {_bar(b.size, mx)}  BID")
    imb = book.imbalance
    tag = (
        f"📈 BID {imb:.2f}x" if imb > 1.5 else f"📉 ASK {imb:.2f}x" if imb < 0.67 else f"⚖ {imb:.2f}x"
    )
    lines.append(f"  {tag}  (vol {book.bid_total:.2f} / {book.ask_total:.2f})")
    return "\n".join(lines)


class Display:
    def __init__(self, min_interval: float = 0.25) -> None:
        self._min = min_interval
        self._last = 0.0

    def show(self, book: OrderBook, via: str, json_out: str | None) -> None:
        now = time.monotonic()
        if now - self._last < self._min:
            return
        self._last = now
        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(book.to_dict(), f)
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
        print(render(book, via))


# ── runners ───────────────────────────────────────────────────────────────────

def run_rest(
    exchange: str, symbol: str, levels: int, market: str,
    interval: float, json_out: str | None, once: bool,
) -> None:
    disp = Display(0.0 if once else interval)
    while True:
        try:
            book = fetch_rest(exchange, symbol, levels, market)
            disp.show(book, "REST", json_out)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
            print(f"[error] {e}", file=sys.stderr)
        if once:
            break
        time.sleep(interval)


def run_ws(
    exchange: str, symbol: str, levels: int, market: str, json_out: str | None,
) -> None:
    disp = Display(0.25)
    sym = symbol.upper()
    while True:
        ws: Ws | None = None
        try:
            ws, local = connect_ws(exchange, symbol, market, levels)
            while True:
                parsed = parse_ws_msg(exchange, ws.recv_json(), levels, local)
                if parsed:
                    bids, asks = parsed
                    disp.show(
                        OrderBook(sym, exchange, market, bids, asks).finalize(),
                        "WS",
                        json_out,
                    )
        except (ConnectionError, OSError, json.JSONDecodeError, ValueError) as e:
            print(f"[reconnect] {e}", file=sys.stderr)
            time.sleep(2)
        finally:
            if ws:
                ws.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Binance/Bybit 무료 오더북")
    p.add_argument("-s", "--symbol", default="BTCUSDT")
    p.add_argument("-e", "--exchange", choices=["binance", "bybit"], default="binance")
    p.add_argument("-m", "--market", choices=["spot", "futures"], default="futures")
    p.add_argument("-l", "--levels", type=int, default=10)
    p.add_argument("--rest", action="store_true", help="REST 폴링 (기본=WebSocket)")
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--json-out")
    p.add_argument("--once", action="store_true")
    a = p.parse_args()

    if a.rest:
        run_rest(a.exchange, a.symbol, a.levels, a.market, a.interval, a.json_out, a.once)
    else:
        if a.once:
            run_rest(a.exchange, a.symbol, a.levels, a.market, 0, a.json_out, True)
        else:
            run_ws(a.exchange, a.symbol, a.levels, a.market, a.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
