"""Copper / silver / gold wallet — spendable tiers for the game economy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.config_loader import load_config

Wallet = dict[str, int]


def load_currency_config(base_dir: str | Path) -> dict[str, Any]:
    return load_config(base_dir, "currency.json")


def _rates(cfg: dict[str, Any]) -> tuple[int, int]:
    cps = int(cfg.get("copper_per_silver", 100))
    spg = int(cfg.get("silver_per_gold", 100))
    return cps, spg


def empty_wallet() -> Wallet:
    return {"copper": 0, "silver": 0, "gold": 0}


def ensure_wallet(state: dict[str, Any], *, base_dir: str | Path) -> Wallet:
    """Migrate legacy party_gold → copper-only wallet (gold is not handed out freely)."""
    inv = state.setdefault("inventory", {})
    wallet = inv.get("wallet")
    if isinstance(wallet, dict) and all(k in wallet for k in ("copper", "silver", "gold")):
        return wallet

    cfg = load_currency_config(base_dir)
    start = dict(cfg.get("starting_wallet", empty_wallet()))
    legacy = int(inv.pop("party_gold", 0))
    if legacy > 0:
        mult = int(cfg.get("legacy_party_gold_to_copper", 1))
        cap = int(cfg.get("legacy_party_gold_cap_copper", 120))
        start["copper"] = min(cap, int(start.get("copper", 0)) + legacy * mult)
    inv["wallet"] = start
    return start


def get_wallet(state: dict[str, Any], *, base_dir: str | Path | None = None) -> Wallet:
    inv = state.setdefault("inventory", {})
    w = inv.get("wallet")
    if isinstance(w, dict) and "copper" in w:
        return w
    if base_dir is None:
        return ensure_wallet(state, base_dir=Path(__file__).resolve().parent.parent)
    return ensure_wallet(state, base_dir=base_dir)


def wallet_to_copper(wallet: Wallet, *, base_dir: str | Path) -> int:
    cfg = load_currency_config(base_dir)
    cps, spg = _rates(cfg)
    return (
        int(wallet.get("copper", 0))
        + int(wallet.get("silver", 0)) * cps
        + int(wallet.get("gold", 0)) * cps * spg
    )


def copper_to_wallet(total: int, *, base_dir: str | Path) -> Wallet:
    cfg = load_currency_config(base_dir)
    cps, spg = _rates(cfg)
    unit_gold = cps * spg
    gold = total // unit_gold
    rem = total % unit_gold
    silver = rem // cps
    copper = rem % cps
    return {"copper": int(copper), "silver": int(silver), "gold": int(gold)}


def normalize_cost(
    spec: int | dict[str, Any] | None,
    *,
    base_dir: str | Path,
    tier: str = "copper",
) -> Wallet:
    """Parse building cost — legacy int gold_cost maps to copper or silver by magnitude."""
    if spec is None:
        return empty_wallet()
    if isinstance(spec, dict):
        return {
            "copper": int(spec.get("copper", 0)),
            "silver": int(spec.get("silver", 0)),
            "gold": int(spec.get("gold", 0)),
        }
    amount = int(spec)
    cfg = load_currency_config(base_dir)
    if tier == "gold" or amount >= 10_000:
        return {"copper": 0, "silver": 0, "gold": amount}
    if tier == "silver" or amount >= int(cfg.get("settlement_cost_tiers", {}).get("silver_threshold", 100)):
        silver = amount // int(cfg.get("copper_per_silver", 100))
        copper = amount % int(cfg.get("copper_per_silver", 100))
        return {"copper": copper, "silver": silver, "gold": 0}
    return {"copper": amount, "silver": 0, "gold": 0}


def can_afford(state: dict[str, Any], cost: Wallet, *, base_dir: str | Path) -> bool:
    wallet = get_wallet(state, base_dir=base_dir)
    return wallet_to_copper(wallet, base_dir=base_dir) >= wallet_to_copper(cost, base_dir=base_dir)


def can_afford_gold_coins(state: dict[str, Any], gold: int, *, base_dir: str | Path) -> bool:
    wallet = get_wallet(state, base_dir=base_dir)
    return int(wallet.get("gold", 0)) >= int(gold)


def spend(
    state: dict[str, Any],
    cost: Wallet,
    *,
    base_dir: str | Path,
) -> bool:
    wallet = get_wallet(state, base_dir=base_dir)
    total = wallet_to_copper(wallet, base_dir=base_dir)
    need = wallet_to_copper(cost, base_dir=base_dir)
    if total < need:
        return False
    remain = copper_to_wallet(total - need, base_dir=base_dir)
    wallet.update(remain)
    return True


def spend_gold_coins(
    state: dict[str, Any],
    gold: int,
    *,
    base_dir: str | Path,
) -> bool:
    wallet = get_wallet(state, base_dir=base_dir)
    g = int(gold)
    if int(wallet.get("gold", 0)) < g:
        return False
    wallet["gold"] = int(wallet.get("gold", 0)) - g
    return True


def grant(
    state: dict[str, Any],
    *,
    copper: int = 0,
    silver: int = 0,
    gold: int = 0,
    base_dir: str | Path,
) -> Wallet:
    wallet = get_wallet(state, base_dir=base_dir)
    total = wallet_to_copper(wallet, base_dir=base_dir)
    total += int(copper)
    total += int(silver) * _rates(load_currency_config(base_dir))[0]
    cps, spg = _rates(load_currency_config(base_dir))
    total += int(gold) * cps * spg
    merged = copper_to_wallet(total, base_dir=base_dir)
    wallet.update(merged)
    return wallet


def format_wallet(wallet: Wallet, *, base_dir: str | Path) -> str:
    cfg = load_currency_config(base_dir)
    names = cfg.get("display", {})
    parts: list[str] = []
    g = int(wallet.get("gold", 0))
    s = int(wallet.get("silver", 0))
    c = int(wallet.get("copper", 0))
    if g:
        parts.append(f"{g}{names.get('gold', '골드')}")
    if s:
        parts.append(f"{s}{names.get('silver', '실버')}")
    if c or not parts:
        parts.append(f"{c}{names.get('copper', '쿠퍼')}")
    return " ".join(parts)


def wallet_summary(state: dict[str, Any], *, base_dir: str | Path) -> dict[str, Any]:
    wallet = get_wallet(state, base_dir=base_dir)
    return {
        "wallet": dict(wallet),
        "formatted": format_wallet(wallet, base_dir=base_dir),
        "party_gold": int(wallet.get("gold", 0)),
        "total_copper": wallet_to_copper(wallet, base_dir=base_dir),
    }


# Backward-compatible helpers used across settlement / kingdom code
def party_gold(state: dict[str, Any], *, base_dir: str | Path) -> int:
    """Gold coin count only (kingdom-scale purchases)."""
    return int(get_wallet(state, base_dir=base_dir).get("gold", 0))


def set_party_gold(state: dict[str, Any], amount: int, *, base_dir: str | Path) -> None:
    wallet = get_wallet(state, base_dir=base_dir)
    wallet["gold"] = max(0, int(amount))


def add_party_gold(state: dict[str, Any], delta: int, *, base_dir: str | Path) -> None:
    grant(state, gold=int(delta), base_dir=base_dir)
