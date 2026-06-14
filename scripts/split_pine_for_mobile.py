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
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/docs/tradingview/mobile"
NUM_PARTS = 7

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
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    margin: 0; padding: 14px; background: #0d1117; color: #e6edf3;
    -webkit-text-size-adjust: 100%;
  }}
  h1 {{ font-size: 1.05rem; margin: 0 0 10px; line-height: 1.35; }}
  h2 {{ font-size: 0.95rem; margin: 18px 0 8px; color: #c9d1d9; }}
  p, li {{ font-size: 0.88rem; color: #8b949e; line-height: 1.55; margin: 0 0 10px; }}
  .btn {{
    display: block; width: 100%; padding: 13px; font-size: 0.95rem; font-weight: 600;
    border: none; border-radius: 8px; background: #238636; color: #fff;
    cursor: pointer; margin: 0 0 10px;
  }}
  .btn:active {{ background: #2ea043; }}
  .btn.done {{ background: #1f6feb; }}
  .warn {{
    background: #3d1f00; border: 1px solid #9e6a03; padding: 10px 12px;
    border-radius: 8px; font-size: 0.84rem; margin-bottom: 12px; line-height: 1.5;
  }}
  .step {{
    background: #161b22; border: 1px solid #30363d; padding: 12px;
    border-radius: 8px; margin-bottom: 14px; font-size: 0.86rem; line-height: 1.6;
  }}
  .sizes {{ font-size: 0.82rem; color: #8b949e; margin-bottom: 12px; }}
  .links {{ list-style: none; padding: 0; margin: 0 0 16px; }}
  .links li {{ margin: 0 0 6px; }}
  .links a {{ color: #58a6ff; font-size: 0.86rem; word-break: break-all; }}
  .codebox {{
    display: block;
    margin: 0 0 16px;
    padding: 12px 10px;
    background: #010409;
    border: 1px solid #30363d;
    border-radius: 8px;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 11px;
    line-height: 1.55;
    letter-spacing: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    color: #e6edf3;
    tab-size: 4;
  }}
  .part-block {{ margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #21262d; }}
  .hint {{ font-size: 0.8rem; color: #6e7681; margin: -6px 0 8px; }}
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
    btn.textContent = '✓ 복사됨 — Pine Editor에 붙여넣기';
    btn.classList.add('done');
    setTimeout(function() {
      btn.textContent = btn.dataset.label;
      btn.classList.remove('done');
    }, 2800);
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
    catch (e) { alert('복사 실패 — 아래 코드를 길게 눌러 직접 복사하세요.'); }
    document.body.removeChild(ta);
  }
}
</script>
</body>
</html>
"""


def htmlpreview(file_name: str) -> str:
    return f"https://htmlpreview.github.io/?{RAW_BASE}/{file_name}"


def code_block(code_id: str, code: str) -> str:
    return f'<pre class="codebox" id="{code_id}">{html.escape(code)}</pre>\n'


def normalize_pine(text: str) -> str:
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
    btn_label = f"Part {part_num} 전체 복사 ({line_count}줄)"
    prev_link = htmlpreview(f"part{part_num - 1}.html") if part_num > 1 else ""
    next_link = htmlpreview(f"part{part_num + 1}.html") if part_num < NUM_PARTS else htmlpreview("index.html")
    nav = "<p>"
    if prev_link:
        nav += f'<a href="{prev_link}" style="color:#58a6ff">← Part {part_num - 1}</a> · '
    nav += f'<a href="{htmlpreview("index.html")}" style="color:#58a6ff">전체 목록</a>'
    if part_num < NUM_PARTS:
        nav += f' · <a href="{next_link}" style="color:#58a6ff">Part {part_num + 1} →</a>'
    nav += "</p>\n"
    return (
        HTML_HEAD.format(title=f"CPE Part {part_num}")
        + f"<h1>Part {part_num} / {NUM_PARTS}</h1>\n"
        + '<div class="warn">모바일 <b>Raw</b>는 한 줄 → 이 페이지에서 <b>복사 버튼</b> 또는 아래 코드 블록 사용.</div>\n'
        + nav
        + f'<p class="hint">{html.escape(hint)}</p>\n'
        + f'<button class="btn" data-label="{html.escape(btn_label)}" '
        + f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        + code_block(code_id, code)
        + HTML_COPY_SCRIPT
    )


def make_index_html(parts: list[tuple[int, int]]) -> str:
    total = sum(c for _, c in parts)
    size_txt = " · ".join(f"P{n}:{c}" for n, c in parts)
    body = (
        HTML_HEAD.format(title="CPE Mobile Install")
        + "<h1>CPE Engine — 모바일 7분할</h1>\n"
        + '<div class="warn"><b>raw.githubusercontent.com = 모바일 한 줄.</b><br>'
        + "이 페이지(HTML Preview)에서 줄간격 유지 · <b>복사 버튼</b> 사용.</div>\n"
        + f'<p class="sizes">총 {total}줄 · {size_txt}</p>\n'
        + '<div class="step"><b>순서</b><br>'
        + "1. TradingView <b>웹</b> → Pine Editor → 코드 전부 삭제<br>"
        + "2. Part 1 복사 → <b>맨 위</b> 붙여넣기<br>"
        + "3. Part 2~7 → <b>맨 아래 이어 붙이기</b> (빈 줄 X)<br>"
        + "4. Save → Add to chart</div>\n"
        + "<h2>Part별 링크 (HTML Preview)</h2>\n<ul class=\"links\">\n"
    )
    for part_num, line_count in parts:
        url = htmlpreview(f"part{part_num}.html")
        body += (
            f'<li><a href="{url}">Part {part_num}</a> '
            f'({line_count}줄) — {html.escape(PART_HINTS[part_num - 1])}</li>\n'
        )
    body += "</ul>\n<h2>한 페이지에서 전부 복사</h2>\n"
    for part_num, line_count in parts:
        hint = PART_HINTS[part_num - 1]
        code_id = f"code{part_num}"
        btn_label = f"Part {part_num} 복사 ({line_count}줄)"
        chunk = (OUT_DIR / f"part{part_num}.pine").read_text(encoding="utf-8")
        body += f'<div class="part-block"><p><b>Part {part_num}</b> — {html.escape(hint)}</p>\n'
        body += (
            f'<button class="btn" data-label="{html.escape(btn_label)}" '
            f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        )
        body += code_block(code_id, chunk)
        body += "</div>\n"
    body += f'<p class="hint">북마크: {html.escape(htmlpreview("index.html"))}</p>\n'
    body += HTML_COPY_SCRIPT
    return body


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    normalized = normalize_pine(raw)
    if normalized != raw:
        SRC.write_text(normalized, encoding="utf-8")
        print("Normalized line endings in source .pine")

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
        chunk = "\n".join(line_starts[start:end]) + "\n"
        part_num = n + 1
        (OUT_DIR / f"part{part_num}.pine").write_text(chunk, encoding="utf-8")
        count = end - start
        parts.append((part_num, count))
        (HTML_DIR / f"part{part_num}.html").write_text(
            make_part_html(part_num, chunk, count), encoding="utf-8"
        )

    merged = "".join((OUT_DIR / f"part{i}.pine").read_text(encoding="utf-8") for i in range(1, NUM_PARTS + 1))
    if merged != normalized:
        raise SystemExit("Chunk merge mismatch")

    (HTML_DIR / "index.html").write_text(make_index_html(parts), encoding="utf-8")

    readme = HTML_DIR / "README.md"
    idx_url = htmlpreview("index.html")
    lines_doc = [
        "# Mobile — HTML Preview (7 parts)\n\n",
        f"**전체:** [{idx_url}]({idx_url})\n\n",
        "모바일 Raw는 한 줄 → **htmlpreview.github.io** 링크 사용.\n\n",
        "Regenerate: `python3 scripts/split_pine_for_mobile.py`\n\n",
    ]
    for num, count in parts:
        url = htmlpreview(f"part{num}.html")
        lines_doc.append(f"- [Part {num}]({url}) ({count}줄)\n")
    readme.write_text("".join(lines_doc), encoding="utf-8")

    print(f"Index: {idx_url}")
    for num, count in parts:
        print(f"Part {num}: {htmlpreview(f'part{num}.html')} ({count} lines)")


if __name__ == "__main__":
    main()
