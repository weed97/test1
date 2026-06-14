#!/usr/bin/env python3
"""Split CPE Pine script into chunks + mobile HTML copy pages."""

from __future__ import annotations

import html
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "docs/tradingview/Crypto_Precision_Engine.pine"
OUT_DIR = REPO_ROOT / "docs/tradingview/mobile/chunks"
HTML_DIR = REPO_ROOT / "docs/tradingview/mobile"
BRANCH = "cursor/crypto-precision-engine-pine-94d6"
REPO = "weed97/test1"

MARKERS = [
    "// ══════════ SECTION 2:",
    "// ══════════ SECTION 3:",
    "// ══════════ SECTION 4:",
    "// ══════════ SECTION 5:",
    "// ══════════ SECTION 6:",
]

PART_HINTS = [
    "맨 위 //@version=6 로 시작",
    "SECTION 2: VOLUME PROFILE",
    "SECTION 3: BUY WALL",
    "SECTION 4: SUPPORT",
    "SECTION 5: WALL PRESSURE",
    "SECTION 6: DASHBOARD + ALERTS",
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
    btn.textContent = '✓ 복사됨 — TradingView Pine Editor에 붙여넣기';
    btn.classList.add('done');
    setTimeout(function() {
      btn.textContent = btn.dataset.label;
      btn.classList.remove('done');
    }, 3000);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(ok).catch(fallback);
  } else {
    fallback();
  }
  function fallback() {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); ok(); } catch (e) { alert('복사 실패 — 아래 코드 영역을 길게 눌러 직접 복사하세요.'); }
    document.body.removeChild(ta);
  }
}
</script>
</body>
</html>
"""


def make_part_html(part_num: int, code: str, line_count: int) -> str:
    hint = PART_HINTS[part_num - 1]
    code_id = f"code{part_num}"
    btn_label = f"Part {part_num} 복사 ({line_count}줄)"
    return (
        HTML_HEAD.format(title=f"CPE Pine Part {part_num}")
        + f"<h1>CPE Engine — Part {part_num} / 6</h1>\n"
        + f'<div class="warn">Raw GitHub는 모바일에서 한 줄로 보일 수 있습니다. '
        + f'<b>아래 초록 버튼</b>으로 복사하면 줄바꿈이 유지됩니다.</div>\n'
        + f'<p>확인: <code>{html.escape(hint)}</code></p>\n'
        + f'<button class="btn" data-label="{html.escape(btn_label)}" '
        + f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        + f'<pre id="{code_id}">{html.escape(code)}</pre>\n'
        + HTML_COPY_SCRIPT
    )


def make_index_html(parts: list[tuple[int, str, int]]) -> str:
    total = sum(c for _, _, c in parts)
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/docs/tradingview/mobile/index.html"
    body = (
        HTML_HEAD.format(title="CPE Mobile Install")
        + "<h1>Crypto Precision Engine — 모바일 설치</h1>\n"
        + '<div class="warn"><b>Raw 페이지는 모바일에서 한 줄로 보입니다.</b> '
        + "각 Part의 <b>복사 버튼</b>을 누르세요. 줄바꿈이 살아 있습니다.</div>\n"
        + f"<p>총 {total}줄 · Part 1 → 6 순서로 Pine Editor에 <b>이어 붙이기</b></p>\n"
        + '<div class="step"><b>순서</b><br>1. TradingView 웹(브라우저) → Pine Editor<br>'
        + "2. 기존 코드 전부 삭제<br>3. Part 1 복사 → 붙여넣기<br>"
        + "4. 맨 아래로 가서 Part 2~6 반복<br>5. Save → Add to chart</div>\n"
    )
    for part_num, _, line_count in parts:
        hint = PART_HINTS[part_num - 1]
        code_id = f"code{part_num}"
        btn_label = f"Part {part_num} 복사 ({line_count}줄)"
        chunk = (OUT_DIR / f"part{part_num}.pine").read_text(encoding="utf-8")
        body += f'<p><b>Part {part_num}</b> — {html.escape(hint)}</p>\n'
        body += (
            f'<button class="btn" data-label="{html.escape(btn_label)}" '
            f'onclick="copyCode(\'{code_id}\', this)">{html.escape(btn_label)}</button>\n'
        )
        body += f'<pre id="{code_id}">{html.escape(chunk)}</pre>\n'
    body += f'<p style="margin-top:20px;font-size:0.8rem;color:#6e7681">북마크: {html.escape(jsdelivr)}</p>\n'
    body += HTML_COPY_SCRIPT
    return body


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
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("part*.pine"):
        old.unlink()
    for old in HTML_DIR.glob("part*.html"):
        old.unlink()

    parts: list[tuple[int, str, int]] = []
    for n in range(len(indices) - 1):
        chunk = "".join(lines[indices[n] : indices[n + 1]])
        part_num = n + 1
        fname = f"part{part_num}.pine"
        (OUT_DIR / fname).write_text(chunk, encoding="utf-8")
        parts.append((part_num, fname, indices[n + 1] - indices[n]))
        html_name = f"part{part_num}.html"
        (HTML_DIR / html_name).write_text(
            make_part_html(part_num, chunk, indices[n + 1] - indices[n]),
            encoding="utf-8",
        )

    (HTML_DIR / "index.html").write_text(make_index_html(parts), encoding="utf-8")

    jsdelivr_index = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/docs/tradingview/mobile/index.html"
    readme = HTML_DIR / "README.md"
    body = [
        "# Mobile paste (Pine chunks + HTML copy pages)\n\n",
        "모바일 Raw는 한 줄로 보일 수 있음 → **HTML 복사 버튼** 사용.\n\n",
        "## 모바일 설치 (권장)\n\n",
        f"**[복사 페이지 열기]({jsdelivr_index})**\n\n",
        "Part 1 → 6 순서로 **복사 버튼** → TradingView Pine Editor에 이어 붙이기.\n\n",
        "## Regenerate\n\n",
        "```bash\npython3 scripts/split_pine_for_mobile.py\n```\n\n",
        "## Files\n\n",
    ]
    for num, fname, count in parts:
        body.append(f"- Part {num}: `{fname}` ({count} lines) + `part{num}.html`\n")
    body.append(f"- All-in-one: `index.html`\n")
    readme.write_text("".join(body), encoding="utf-8")

    for num, fname, count in parts:
        print(f"Part {num}: {count} lines -> {fname} + part{num}.html")
    print(f"Index: {jsdelivr_index}")


if __name__ == "__main__":
    main()
