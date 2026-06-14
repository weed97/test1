#!/usr/bin/env python3
"""Split Crypto_Precision_Engine.pine into mobile-friendly paste chunks."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs/tradingview/Crypto_Precision_Engine.pine"
OUT_DIR = REPO_ROOT / "docs/tradingview/mobile/chunks"

MARKERS = [
    "// ══════════ SECTION 2:",
    "// ══════════ SECTION 3:",
    "// ══════════ SECTION 4:",
    "// ══════════ SECTION 5:",
    "// ══════════ SECTION 6:",
]


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    indices = [0]
    for marker in MARKERS:
        for i, line in enumerate(lines):
            if line.startswith(marker):
                indices.append(i)
                break
        else:
            raise SystemExit(f"Marker not found: {marker}")
    indices.append(len(lines))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("part*.pine"):
        old.unlink()

    parts: list[tuple[int, str, int]] = []
    for n in range(len(indices) - 1):
        chunk = "".join(lines[indices[n] : indices[n + 1]])
        part_num = n + 1
        fname = f"part{part_num}.pine"
        (OUT_DIR / fname).write_text(chunk, encoding="utf-8")
        parts.append((part_num, fname, indices[n + 1] - indices[n]))

    readme = REPO_ROOT / "docs/tradingview/mobile/README.md"
    body = [
        "# Mobile paste chunks\n\n",
        "Auto-generated from `Crypto_Precision_Engine.pine`.\n\n",
        "Regenerate:\n\n",
        "```bash\npython3 scripts/split_pine_for_mobile.py\n```\n\n",
    ]
    for num, fname, count in parts:
        body.append(f"- Part {num}: `{fname}` ({count} lines)\n")
    readme.write_text("".join(body), encoding="utf-8")

    for num, fname, count in parts:
        print(f"Part {num}: {count} lines -> {fname}")


if __name__ == "__main__":
    main()
