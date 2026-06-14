#!/usr/bin/env python3
"""Split CPE Pine script into 7 balanced chunks + mobile HTML copy pages."""

from __future__ import annotations

import html
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs/tradingview/Crypto_Precision_Engine.pine"
OUT_DIR = REPO_ROOT / "docs/tradingview/mobile/chunks"
HTML_DIR = REPO_ROOT / "docs/tradingview/mobile"
BRANCH = "cursor/crypto-precision-engine-pine-94d6"
REPO = "weed97/test1"
NUM_PARTS = 7

# 7-way split at natural section boundaries (~130–160 lines each; S/R kept whole)
SPLIT_MARKERS = [
    "// 1-3 Weekly + Monthly VWAP",
    "// ══════════ SECTION 2:",
    "// ══════════ SECTION 3:",
    "// ══════════ SECTION 4:",
    "// ══════════ SECTION 5:",
    "// ══════════ SECTION 6:",
]

PART_HINTS = [
    "//@version=6 · Inputs · Session VWAP · σ Bands",
    "Weekly/Monthly VWAP · VWAP S/R Zones",
    "Volume Profile · POC · VAH/VAL",
    "Buy Wall · Sell Wall detection",
    "Support & Resistance Zones (전체)",
    "Wall Pressure table (free)",
    "Dashboard · Signals · Alerts",
]

HTML_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 16px; background: #0d1117; color: #e6edf3; }}
  h1 {{ font-size: 1.1rem; margin: 0 0 8px; }}
  p {{ font-size: 0.9rem; color: #8b949e; margin: 0 0 12px; line-height: 1.5; }}
  .btn {{ display: block; width: 100%; padding: 14px; font-size: 1rem; font-weight: 600;
    border: none; border-radius: 8px; background: #238636; color: #fff; cursor: pointer; margin-bottom: 12px; }}
  .btn:active {{ background: #2ea043; }}
  .btn.done {{ background: #1f6feb; }}
  pre {{ display: none; }}
  .warn {{ background: #3d1f00; border: 1px solid #9e6a03; padding: 10px; border-radius: 8px;
    font-size: 0.85rem; margin-bottom: 12px; }}
  .step {{ background: #161b22; padding: 12px; border-radius: 8px; margin-bottom: 16px; }}
  .sizes {{ font-size: 0.85rem; color: #8b949e; margin-bottom: 16px; }}
</style>
</head>
<body>
"""

HTML_COPY_SCRIPT = """
<script>
function copyCode(id, btn) {
  var el = document.getElementById(id);
  var text = el.textContent;
  function ok() {
    btn.textContent = '✓ 복사됨 — Pine Editor 맨 아래에 이어 붙이기';
    btn.classList.add('done');
    setTimeout(function() {
      btn.textContent = btn.dataset.label;
      btn.classList.remove('done');
    }, 3000);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(ok).catch(fallback);
  } else { fallback(); }
  function fallback() {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); ok(); }
    catch (e) { alert('복사 실패 — 코드 영역을 길게 눌러 직접 복사하세요.'); }
    document.body.removeChild(ta);
  }
}
</script>
</body>
</html>
"""


def normalize_pine(text: str) -> str:
    """LF only, no trailing spaces, single trailing newline — clean Zeiierman-style joins."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def find_split_indices(lines: list[str]) -> list[int]:
    indices = [0]
    for marker in SPLIT_MARKERS:
        for i, line in enumerate(lines):
            if line.startswith(marker):
                indices.append(i)
                break
        else:
            raise SystemExit(f"Split marker not found: {marker}")
    indices.append(len(lines))
    return indices


def make_part_html(part_num: int, code: str, line_count: int) -> str:
    hint = PART_HINTS[part_num - 1]
    code_id = f"code{part_num}"
    btn_label = f"Part {part_num} 복사 ({line_count}줄)"
    return (
        HTML_HEAD.format(title=f"CPE Pine Part {part_num}")
        + f"<h1>CPE Engine — Part {part_num} / {NUM_PARTS}</h1>\n"
        + '<div class="warn"><b>복사 버튼</b>으로 줄바꿈 유지. Part 1→7 순서로 <b>이어 붙이기</b>.</div>\n'
        + f"<p>{html.escape(hint)}</p>\n"
        + f'<button class="btn" data-label="{html.escape(btn_label)}" '
        + f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        + f'<pre id="{code_id}">{html.escape(code)}</pre>\n'
        + HTML_COPY_SCRIPT
    )


def make_index_html(parts: list[tuple[int, int]]) -> str:
    total = sum(c for _, c in parts)
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/docs/tradingview/mobile/index.html"
    size_txt = " · ".join(f"P{n}:{c}" for n, c in parts)
    body = (
        HTML_HEAD.format(title="CPE Mobile Install")
        + "<h1>Crypto Precision Engine — 모바일 7분할 설치</h1>\n"
        + '<div class="warn"><b>Raw GitHub = 모바일에서 한 줄.</b> '
        + "아래 <b>복사 버튼</b>만 사용하세요.</div>\n"
        + f'<p class="sizes">총 {total}줄 · {size_txt}</p>\n'
        + '<div class="step"><b>순서</b><br>'
        + "1. TradingView <b>웹 브라우저</b> → Pine Editor<br>"
        + "2. 기존 코드 전부 삭제<br>"
        + "3. Part 1 복사 → <b>맨 위</b>에 붙여넣기<br>"
        + "4. Part 2~7 복사 → <b>맨 아래에 이어 붙이기</b> (빈 줄 추가 X)<br>"
        + "5. Save → Add to chart</div>\n"
    )
    for part_num, line_count in parts:
        hint = PART_HINTS[part_num - 1]
        code_id = f"code{part_num}"
        btn_label = f"Part {part_num} 복사 ({line_count}줄)"
        chunk = (OUT_DIR / f"part{part_num}.pine").read_text(encoding="utf-8")
        body += f"<p><b>Part {part_num}</b> — {html.escape(hint)}</p>\n"
        body += (
            f'<button class="btn" data-label="{html.escape(btn_label)}" '
            f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        )
        body += f'<pre id="{code_id}">{html.escape(chunk)}</pre>\n'
    body += f'<p style="margin-top:20px;font-size:0.8rem;color:#6e7681">북마크: {html.escape(jsdelivr)}</p>\n'
    body += HTML_COPY_SCRIPT
    return body


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    normalized = normalize_pine(raw)
    if normalized != raw:
        SRC.write_text(normalized, encoding="utf-8")
        print("Normalized line endings in source .pine")

    lines = normalized.splitlines(keepends=True)
    # Re-split without keepends for index finding
    line_starts = normalized.split("\n")
    if line_starts and line_starts[-1] == "":
        line_starts = line_starts[:-1]

    indices = find_split_indices(line_starts)
    if len(indices) != NUM_PARTS + 1:
        raise SystemExit(f"Expected {NUM_PARTS} parts, got {len(indices) - 1}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("part*.pine"):
        old.unlink()
    for old in HTML_DIR.glob("part*.html"):
        old.unlink()

    parts: list[tuple[int, int]] = []
    for n in range(NUM_PARTS):
        start, end = indices[n], indices[n + 1]
        chunk_lines = line_starts[start:end]
        chunk = "\n".join(chunk_lines) + "\n"
        part_num = n + 1
        fname = f"part{part_num}.pine"
        (OUT_DIR / fname).write_text(chunk, encoding="utf-8")
        count = end - start
        parts.append((part_num, count))
        (HTML_DIR / f"part{part_num}.html").write_text(
            make_part_html(part_num, chunk, count), encoding="utf-8"
        )

    merged = "".join((OUT_DIR / f"part{i}.pine").read_text(encoding="utf-8") for i in range(1, NUM_PARTS + 1))
    if merged != normalized:
        raise SystemExit("Chunk merge mismatch — check split boundaries")

    (HTML_DIR / "index.html").write_text(make_index_html(parts), encoding="utf-8")

    jsdelivr = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/docs/tradingview/mobile/index.html"
    readme = HTML_DIR / "README.md"
    lines_doc = [
        "# Mobile paste — 7 parts + HTML copy\n\n",
        f"**[복사 페이지]({jsdelivr})**\n\n",
        "Regenerate: `python3 scripts/split_pine_for_mobile.py`\n\n",
    ]
    for num, count in parts:
        lines_doc.append(f"- Part {num}: `part{num}.pine` ({count} lines) — {PART_HINTS[num-1]}\n")
    readme.write_text("".join(lines_doc), encoding="utf-8")

    for num, count in parts:
        print(f"Part {num}: {count} lines")
    print(f"Total: {sum(c for _, c in parts)} lines")
    print(f"Index: {jsdelivr}")


if __name__ == "__main__":
    main()
