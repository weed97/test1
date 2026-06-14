#!/usr/bin/env python3
"""Strip comments, split CPE Pine into 2 halves + mobile HTML copy pages."""

from __future__ import annotations

import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs/tradingview/Crypto_Precision_Engine.pine"
OUT_DIR = REPO_ROOT / "docs/tradingview/mobile/chunks"
HTML_DIR = REPO_ROOT / "docs/tradingview/mobile"
BRANCH = "cursor/crypto-precision-engine-pine-94d6"
REPO = "weed97/test1"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/docs/tradingview/mobile"
NUM_PARTS = 2

# Part 2 starts here (after Walls — before S/R)
SPLIT_MARKERS = ["type SrZone"]

PART_HINTS = [
    "//@version=6 · Inputs · VWAP · POC · Walls",
    "S/R Zones · Wall Pressure · Dashboard · Signals · Alerts",
]

HTML_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 14px; background: #0d1117; color: #e6edf3; }}
  h1 {{ font-size: 1.05rem; margin: 0 0 10px; }}
  p {{ font-size: 0.86rem; color: #8b949e; line-height: 1.5; margin: 0 0 10px; }}
  a {{ color: #58a6ff; word-break: break-all; }}
  .btn {{
    display: block; width: 100%; padding: 13px; font-size: 0.95rem; font-weight: 600;
    border: none; border-radius: 8px; background: #238636; color: #fff; margin: 0 0 12px;
  }}
  .btn.done {{ background: #1f6feb; }}
  .warn {{
    background: #1c2128; border: 1px solid #388bfd; padding: 10px 12px;
    border-radius: 8px; font-size: 0.84rem; margin-bottom: 12px; line-height: 1.5;
  }}
  .step {{
    background: #161b22; border: 1px solid #30363d; padding: 12px;
    border-radius: 8px; margin-bottom: 14px; font-size: 0.85rem; line-height: 1.55;
  }}
  .code-scroll {{
    overflow: auto; -webkit-overflow-scrolling: touch;
    border: 1px solid #30363d; border-radius: 6px; background: #010409;
    max-height: 70vh;
  }}
  pre.code {{
    margin: 0; padding: 12px 14px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 11px; line-height: 1.45; tab-size: 4; -moz-tab-size: 4;
    white-space: pre;
    color: #c9d1d9;
  }}
</style>
</head>
<body>
"""

HTML_COPY_SCRIPT = """
<script>
function copyCode(id, btn) {
  var text = document.getElementById(id).value;
  function ok() {
    btn.textContent = '✓ 복사됨 — Pine Editor에 붙여넣기';
    btn.classList.add('done');
    setTimeout(function() { btn.textContent = btn.dataset.label; btn.classList.remove('done'); }, 2800);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(ok).catch(fallback);
  } else fallback();
  function fallback() {
    var ta = document.getElementById(id);
    ta.style.cssText = 'position:fixed;left:0;top:0;width:2em;height:2em;opacity:0';
    ta.focus(); ta.select();
    try { document.execCommand('copy'); ok(); } catch(e) { alert('복사 버튼 다시 눌러주세요'); }
    ta.style.cssText = 'position:fixed;left:-9999px;width:1px;height:1px;opacity:0';
  }
}
</script>
</body>
</html>
"""


def htmlpreview(file_name: str) -> str:
    return f"https://htmlpreview.github.io/?{RAW_BASE}/{file_name}"


def strip_comments(text: str) -> str:
    out: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = line.rstrip()
        if s.startswith("//@version"):
            out.append(s)
            continue
        if re.match(r"^\s*//", s):
            continue
        out.append(s)
    cleaned: list[str] = []
    prev_blank = False
    for line in out:
        blank = line.strip() == ""
        if blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = blank
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def normalize_table_indent(text: str) -> str:
    """2-space table blocks → 4-space (match rest of script)."""
    markers = ("if showOrderbook and barstate.islast", "if showDashboard and barstate.islast")
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if any(line.startswith(m) for m in markers):
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                if lines[i].strip():
                    body = lines[i].lstrip(" ")
                    n = len(lines[i]) - len(body)
                    out.append(" " * (n * 2) + body)
                else:
                    out.append("")
                i += 1
            continue
        i += 1
    return "\n".join(out) + "\n"


def code_panel(code_id: str, code: str) -> str:
    ta = (
        f'<textarea id="{code_id}" readonly aria-hidden="true" '
        f'style="position:fixed;left:-9999px;opacity:0;width:1px;height:1px">'
        f"{html.escape(code)}</textarea>"
    )
    pre = f'<div class="code-scroll"><pre class="code">{html.escape(code)}</pre></div>'
    return ta + pre


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
    code_id = f"code{part_num}"
    btn = f"Part {part_num} 복사 ({line_count}줄)"
    nav = "<p>"
    if part_num > 1:
        nav += f'<a href="{htmlpreview("part1.html")}">← Part 1</a> · '
    nav += f'<a href="{htmlpreview("index.html")}">전체</a>'
    if part_num < NUM_PARTS:
        nav += f' · <a href="{htmlpreview("part2.html")}">Part 2 →</a>'
    nav += "</p>"
    return (
        HTML_HEAD.format(title=f"CPE Part {part_num}")
        + f"<h1>Part {part_num} / {NUM_PARTS}</h1>"
        + '<div class="warn"><b>복사 버튼</b>만 사용 · Part 1 → Part 2 순서로 이어 붙이기</div>'
        + nav
        + f"<p>{html.escape(PART_HINTS[part_num - 1])}</p>"
        + f'<button class="btn" data-label="{html.escape(btn)}" onclick="copyCode(\'{code_id}\', this)">{btn}</button>'
        + code_panel(code_id, code)
        + HTML_COPY_SCRIPT
    )


def make_index_html(parts: list[tuple[int, int]], chunks: dict[int, str]) -> str:
    total = sum(c for _, c in parts)
    body = (
        HTML_HEAD.format(title="CPE Mobile")
        + "<h1>CPE Engine — 2분할 (주석 제거)</h1>"
        + '<div class="warn">Raw ❌ · 이 페이지 <b>복사 버튼</b> ✅</div>'
        + '<div class="step">1. Pine Editor 코드 삭제<br>2. <b>Part 1</b> 복사 → 맨 위<br>'
        + "3. <b>Part 2</b> 복사 → 맨 아래 이어 붙이기<br>4. Save</div>"
        + f"<p>총 {total}줄 (주석 제거 후)</p>"
    )
    for n, cnt in parts:
        btn = f"Part {n} 복사 ({cnt}줄)"
        cid = f"code{n}"
        body += f"<p><b>Part {n}</b> — {html.escape(PART_HINTS[n-1])} · "
        body += f'<a href="{htmlpreview(f"part{n}.html")}">단독 페이지</a></p>'
        body += f'<button class="btn" data-label="{html.escape(btn)}" onclick="copyCode(\'{cid}\', this)">{btn}</button>'
        body += code_panel(cid, chunks[n])
    body += HTML_COPY_SCRIPT
    return body


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    cleaned = normalize_table_indent(strip_comments(raw))
    SRC.write_text(cleaned, encoding="utf-8")
    print(f"Cleaned: {raw.count(chr(10))} → {cleaned.count(chr(10))} lines")

    line_starts = cleaned.split("\n")
    if line_starts and line_starts[-1] == "":
        line_starts = line_starts[:-1]

    indices = find_split_indices(line_starts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(OUT_DIR.glob("part*.pine")) + list(HTML_DIR.glob("part*.html")):
        old.unlink()

    parts: list[tuple[int, int]] = []
    chunks: dict[int, str] = {}
    for n in range(NUM_PARTS):
        start, end = indices[n], indices[n + 1]
        chunk = "\n".join(line_starts[start:end]) + "\n"
        part_num = n + 1
        (OUT_DIR / f"part{part_num}.pine").write_text(chunk, encoding="utf-8")
        chunks[part_num] = chunk
        parts.append((part_num, end - start))
        (HTML_DIR / f"part{part_num}.html").write_text(
            make_part_html(part_num, chunk, end - start), encoding="utf-8"
        )

    merged = "".join(chunks[i] for i in range(1, NUM_PARTS + 1))
    if merged != cleaned:
        raise SystemExit("Chunk merge mismatch")

    (HTML_DIR / "index.html").write_text(make_index_html(parts, chunks), encoding="utf-8")

    idx = htmlpreview("index.html")
    readme = HTML_DIR / "README.md"
    doc = [f"# Mobile 2-part install\n\n[{idx}]({idx})\n\n"]
    for n, cnt in parts:
        doc.append(f"- [Part {n}]({htmlpreview(f'part{n}.html')}) ({cnt}줄)\n")
    readme.write_text("".join(doc), encoding="utf-8")

    print(f"Index: {idx}")
    for n, cnt in parts:
        print(f"Part {n}: {htmlpreview(f'part{n}.html')} ({cnt} lines)")


if __name__ == "__main__":
    main()
