#!/usr/bin/env python3
"""Mobile HTML copy page — full CPE Pine script in one piece."""

from __future__ import annotations

import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs/tradingview/Crypto_Precision_Engine.pine"
HTML_DIR = REPO_ROOT / "docs/tradingview/mobile"
BRANCH = "cursor/crypto-precision-engine-pine-94d6"
REPO = "weed97/test1"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/docs/tradingview/mobile"

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
  .btn {{
    display: block; width: 100%; padding: 14px; font-size: 1rem; font-weight: 700;
    border: none; border-radius: 8px; background: #238636; color: #fff; margin: 0 0 14px;
  }}
  .btn.done {{ background: #1f6feb; }}
  .warn {{
    background: #1c2128; border: 1px solid #388bfd; padding: 10px 12px;
    border-radius: 8px; font-size: 0.84rem; margin-bottom: 12px; line-height: 1.5;
  }}
  .code-scroll {{
    overflow: auto; -webkit-overflow-scrolling: touch;
    border: 1px solid #30363d; border-radius: 6px; background: #010409;
    max-height: 75vh;
  }}
  pre.code {{
    margin: 0; padding: 12px 14px;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 11px; line-height: 1.45; tab-size: 4;
    white-space: pre; color: #c9d1d9;
  }}
</style>
</head>
<body>
"""

HTML_COPY_SCRIPT = """
<script>
function copyAll(btn) {
  var text = document.getElementById('src').value;
  function ok() {
    btn.textContent = '✓ 전체 복사됨 — Pine Editor에 붙여넣기';
    btn.classList.add('done');
    setTimeout(function() { btn.textContent = btn.dataset.label; btn.classList.remove('done'); }, 3000);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(ok).catch(fallback);
  } else fallback();
  function fallback() {
    var ta = document.getElementById('src');
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


def make_full_html(code: str, line_count: int) -> str:
    btn = f"전체 코드 복사 ({line_count}줄)"
    return (
        HTML_HEAD.format(title="CPE Engine — Full")
        + "<h1>Crypto Precision Engine — 전체</h1>"
        + '<div class="warn"><b>복사 버튼</b> 한 번 → Pine Editor에 붙여넣기 → Save</div>'
        + f"<p>주석 제거 · 들여쓰기 정리 · {line_count}줄</p>"
        + f'<button class="btn" data-label="{html.escape(btn)}" onclick="copyAll(this)">{btn}</button>'
        + f'<textarea id="src" readonly aria-hidden="true" '
        + f'style="position:fixed;left:-9999px;opacity:0;width:1px;height:1px">'
        + f"{html.escape(code)}</textarea>"
        + f'<div class="code-scroll"><pre class="code">{html.escape(code)}</pre></div>'
        + HTML_COPY_SCRIPT
    )


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    cleaned = normalize_table_indent(strip_comments(raw))
    SRC.write_text(cleaned, encoding="utf-8")

    line_count = cleaned.count("\n")
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    html_body = make_full_html(cleaned, line_count)
    (HTML_DIR / "index.html").write_text(html_body, encoding="utf-8")
    (HTML_DIR / "full.html").write_text(html_body, encoding="utf-8")

    # optional backup chunks for PC raw-style users
    chunks_dir = HTML_DIR / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    (chunks_dir / "full.pine").write_text(cleaned, encoding="utf-8")

    url = htmlpreview("index.html")
    (HTML_DIR / "README.md").write_text(
        f"# CPE Mobile — 전체 한 번에\n\n**[{url}]({url})**\n\n"
        f"`python3 scripts/split_pine_for_mobile.py` 로 재생성\n",
        encoding="utf-8",
    )
    print(f"{line_count} lines")
    print(url)


if __name__ == "__main__":
    main()
