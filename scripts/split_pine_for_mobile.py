#!/usr/bin/env python3
"""Split CPE Pine into 7 parts + mobile HTML (htmlpreview, line-numbered view)."""

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
    "Support & Resistance Zones",
    "Wall Pressure table",
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
  }}
  h1 {{ font-size: 1.05rem; margin: 0 0 10px; }}
  h2 {{ font-size: 0.92rem; margin: 16px 0 8px; color: #c9d1d9; }}
  p {{ font-size: 0.86rem; color: #8b949e; line-height: 1.5; margin: 0 0 10px; }}
  a {{ color: #58a6ff; }}
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
  .hint {{ font-size: 0.8rem; color: #6e7681; margin: -4px 0 10px; }}
  .links {{ list-style: none; padding: 0; margin: 0 0 14px; }}
  .links li {{ margin: 0 0 5px; font-size: 0.86rem; }}
  details {{
    margin: 0 0 10px; border: 1px solid #30363d; border-radius: 8px;
    background: #0d1117; overflow: hidden;
  }}
  summary {{
    padding: 10px 12px; cursor: pointer; font-size: 0.9rem; font-weight: 600;
    background: #161b22; list-style: none;
  }}
  summary::-webkit-details-marker {{ display: none; }}
  .part-inner {{ padding: 0 10px 10px; }}
  /* 코드: 줄 잘림 없음(pre), 가로 스크롤, 줄번호 정렬 */
  .code-scroll {{
    overflow-x: auto; -webkit-overflow-scrolling: touch;
    border: 1px solid #30363d; border-radius: 6px; background: #010409;
  }}
  .code-table {{
    border-collapse: collapse; width: max-content; min-width: 100%;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px; line-height: 1.42; tab-size: 4;
  }}
  .code-table tr:hover td.txt {{ background: #161b22; }}
  .code-table td.num {{
    color: #6e7681; text-align: right; vertical-align: top;
    padding: 0 10px 0 6px; user-select: none; white-space: nowrap;
    border-right: 1px solid #21262d; width: 1%;
  }}
  .code-table td.txt {{
    vertical-align: top; padding: 0 14px 0 10px;
    white-space: pre; color: #e6edf3;
  }}
  .code-table td.txt.empty {{ min-height: 1.42em; }}
</style>
</head>
<body>
"""

HTML_COPY_SCRIPT = """
<script>
function copyCode(id, btn) {
  var ta = document.getElementById(id);
  var text = ta.value;
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
    ta.style.position = 'fixed';
    ta.style.left = '0';
    ta.style.top = '0';
    ta.style.width = '2em';
    ta.style.height = '2em';
    ta.style.opacity = '0';
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); ok(); }
    catch (e) { alert('복사 버튼을 다시 눌러주세요.'); }
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
  }
}
</script>
</body>
</html>
"""


def htmlpreview(file_name: str) -> str:
    return f"https://htmlpreview.github.io/?{RAW_BASE}/{file_name}"


def normalize_pine(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    text = "\n".join(lines) + "\n"
    # 연속 빈 줄 2개 이상 → 1개 (가독성, 문법 동일)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def code_panel(code_id: str, code: str) -> str:
    """Hidden textarea = exact copy source. Table = aligned display, no mid-line wrap."""
    lines = code.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    rows = []
    for i, line in enumerate(lines, 1):
        cls = "txt empty" if line == "" else "txt"
        cell = html.escape(line) if line else " "
        rows.append(f"<tr><td class=\"num\">{i}</td><td class=\"{cls}\">{cell}</td></tr>")
    table = (
        '<div class="code-scroll"><table class="code-table"><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )
    ta = (
        f'<textarea id="{code_id}" readonly aria-hidden="true" '
        f'style="position:fixed;left:-9999px;top:0;width:1px;height:1px;opacity:0">'
        f"{html.escape(code)}</textarea>"
    )
    return ta + table


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


def part_block(part_num: int, line_count: int, code: str, open_default: bool = False) -> str:
    code_id = f"code{part_num}"
    btn_label = f"Part {part_num} 복사 ({line_count}줄)"
    hint = PART_HINTS[part_num - 1]
    open_attr = " open" if open_default else ""
    link = htmlpreview(f"part{part_num}.html")
    return (
        f"<details{open_attr}>"
        f"<summary>Part {part_num} · {line_count}줄 · "
        f'<a href="{link}" onclick="event.stopPropagation()">단독 페이지</a></summary>'
        f'<div class="part-inner">'
        f'<p class="hint">{html.escape(hint)}</p>'
        f'<button class="btn" data-label="{html.escape(btn_label)}" '
        f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>'
        f"{code_panel(code_id, code)}"
        f"</div></details>\n"
    )


def make_part_html(part_num: int, code: str, line_count: int) -> str:
    code_id = f"code{part_num}"
    btn_label = f"Part {part_num} 복사 ({line_count}줄)"
    nav = "<p>"
    if part_num > 1:
        nav += f'<a href="{htmlpreview(f"part{part_num - 1}.html")}">← Part {part_num - 1}</a> · '
    nav += f'<a href="{htmlpreview("index.html")}">전체</a>'
    if part_num < NUM_PARTS:
        nav += f' · <a href="{htmlpreview(f"part{part_num + 1}.html")}">Part {part_num + 1} →</a>'
    nav += "</p>"
    return (
        HTML_HEAD.format(title=f"CPE Part {part_num}")
        + f"<h1>Part {part_num} / {NUM_PARTS}</h1>"
        + '<div class="warn"><b>복사 버튼</b>만 사용하세요. '
        + "코드는 줄번호·정렬용 표시 — 가로로 스크롤 가능.</div>"
        + nav
        + f'<p class="hint">{html.escape(PART_HINTS[part_num - 1])}</p>'
        + f'<button class="btn" data-label="{html.escape(btn_label)}" '
        + f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>'
        + code_panel(code_id, code)
        + HTML_COPY_SCRIPT
    )


def make_index_html(parts: list[tuple[int, int]], chunks: dict[int, str]) -> str:
    total = sum(c for _, c in parts)
    body = (
        HTML_HEAD.format(title="CPE Mobile")
        + "<h1>CPE Engine — 모바일 7분할</h1>"
        + '<div class="warn">Raw = 한 줄 · 이 페이지 = <b>정렬된 코드</b> + <b>복사 버튼</b></div>'
        + '<div class="step">1. Pine Editor 코드 삭제<br>'
        + "2. Part 1 복사 → 맨 위<br>"
        + "3. Part 2~7 → 맨 아래 이어 붙이기<br>"
        + "4. Save</div>"
        + f"<p>총 {total}줄</p>"
        + "<h2>Part 링크</h2><ul class=\"links\">"
    )
    for n, cnt in parts:
        body += (
            f'<li><a href="{htmlpreview(f"part{n}.html")}">Part {n}</a> '
            f"({cnt}줄)</li>"
        )
    body += "</ul><h2>복사</h2>"
    for n, cnt in parts:
        body += part_block(n, cnt, chunks[n], open_default=(n == 1))
    body += HTML_COPY_SCRIPT
    return body


def main() -> None:
    raw = SRC.read_text(encoding="utf-8")
    normalized = normalize_pine(raw)
    if normalized != raw:
        SRC.write_text(normalized, encoding="utf-8")
        print("Normalized source .pine")

    line_starts = normalized.split("\n")
    if line_starts and line_starts[-1] == "":
        line_starts = line_starts[:-1]

    indices = find_split_indices(line_starts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("part*.pine"):
        old.unlink()
    for old in HTML_DIR.glob("part*.html"):
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
    if merged != normalized:
        raise SystemExit("Chunk merge mismatch")

    (HTML_DIR / "index.html").write_text(make_index_html(parts, chunks), encoding="utf-8")

    idx = htmlpreview("index.html")
    readme = HTML_DIR / "README.md"
    doc = [f"# Mobile HTML Preview\n\n[{idx}]({idx})\n\n"]
    for n, cnt in parts:
        doc.append(f"- [Part {n}]({htmlpreview(f'part{n}.html')}) ({cnt}줄)\n")
    readme.write_text("".join(doc), encoding="utf-8")

    print(f"Index: {idx}")
    for n, cnt in parts:
        print(f"Part {n}: {cnt} lines")


if __name__ == "__main__":
    main()
