#!/usr/bin/env python3
"""将 TradingAgents 的 complete_report.md 导出为可正常显示中文的 PDF。

Chrome headless 默认只嵌 Menlo，中文会乱码。必须把 CJK TTF 拷到与 HTML
同目录并用 @font-face 引用，打印时才会子集嵌入 Arial Unicode MS。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CJK_FONT = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")

COVER_CSS = """
@font-face {
  font-family: "ReportCJK";
  src: url("cjk.ttf") format("truetype");
  font-weight: 100 900;
  font-style: normal;
}
:root {
  --ink: #1a2332;
  --muted: #5c6b7a;
  --navy: #0b2a4a;
  --line: #d5dde6;
  --band: #f4f7fa;
  --accent: #1f7a54;
  --gold: #b8860b;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  color: var(--ink);
  font-family: "ReportCJK", "PingFang SC", "Hiragino Sans GB", sans-serif;
  font-size: 10.5pt;
  line-height: 1.62;
  -webkit-font-smoothing: antialiased;
}
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
.cover { page-break-after: always; padding: 28px 8px 0; min-height: 240mm; }
.kicker {
  letter-spacing: 0.18em; font-size: 9pt; color: var(--gold);
  font-weight: 700; text-transform: uppercase;
}
.cover h1 {
  font-size: 26pt; line-height: 1.25; color: var(--navy);
  margin: 10px 0 6px; page-break-before: avoid;
}
.sub { color: var(--muted); font-size: 12pt; margin-bottom: 28px; }
.badge {
  display: inline-block; background: var(--accent); color: #fff;
  font-weight: 700; padding: 4px 12px; border-radius: 4px; font-size: 12pt;
}
.meta { width: 100%; border-collapse: collapse; margin: 28px 0 32px; }
.meta th, .meta td {
  text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line);
  font-size: 10.5pt; font-family: "ReportCJK", sans-serif;
}
.meta th { width: 28%; color: var(--muted); font-weight: 700; }
.cover p.lead {
  font-size: 11pt; background: var(--band); padding: 16px 18px;
  border-left: 4px solid var(--accent);
}
.disclaimer { margin-top: 48px; font-size: 8.5pt; color: var(--muted); }
.content h1 {
  font-size: 16pt; color: var(--navy); border-bottom: 2px solid var(--navy);
  padding-bottom: 6px; margin: 28px 0 12px; page-break-before: always;
}
.content h1:first-child { page-break-before: avoid; }
.content h2 { font-size: 13.5pt; color: var(--navy); margin: 22px 0 10px; page-break-after: avoid; }
.content h3 { font-size: 12pt; color: #24364d; margin: 18px 0 8px; page-break-after: avoid; }
.content h4 { font-size: 11pt; margin: 14px 0 6px; page-break-after: avoid; }
.content p { margin: 0 0 9px; }
.content ul, .content ol { margin: 0 0 10px; padding-left: 1.3em; }
.content li { margin: 2px 0; }
.content hr { border: none; border-top: 1px solid var(--line); margin: 16px 0; }
.content table {
  width: 100%; border-collapse: collapse; margin: 10px 0 16px;
  font-size: 9pt; page-break-inside: avoid;
}
.content th, .content td {
  border: 1px solid var(--line); padding: 6px 8px; text-align: left;
  vertical-align: top; font-family: "ReportCJK", sans-serif;
}
.content th { background: var(--navy); color: #fff; font-weight: 700; }
.content tr:nth-child(even) td { background: var(--band); }
.content blockquote {
  margin: 10px 0 14px; padding: 8px 14px;
  border-left: 3px solid var(--gold); background: #fbf8ef;
}
"""


def _field(md: str, label: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(label)}\*\*\s*[:：]\s*(.+)", md)
    return m.group(1).strip() if m else None


def parse_meta(md: str, report_dir: Path) -> dict[str, str]:
    """从完整报告 / 组合决策里抽出封面字段。"""
    ticker = report_dir.name.split("_")[0]
    m = re.search(r"^#\s+Trading Analysis Report:\s*(.+)$", md, re.M)
    if m:
        ticker = m.group(1).strip()
    generated = ""
    m = re.search(r"^Generated:\s*(.+)$", md, re.M)
    if m:
        generated = m.group(1).strip()

    alias = ""
    m = re.search(rf"{re.escape(ticker)}[（(]([^）)]+)[）)]", md)
    if m:
        alias = m.group(1).strip()

    return {
        "ticker": ticker,
        "alias": alias,
        "generated": generated,
        "rating": _field(md, "Rating") or "",
        "target": _field(md, "Price Target") or "",
        "horizon": _field(md, "Time Horizon") or "",
        "summary": _field(md, "Executive Summary") or "",
    }


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_cover(meta: dict[str, str]) -> str:
    title = meta["ticker"]
    if meta["alias"]:
        title = f"{meta['ticker']}　{_esc(meta['alias'])}"
    rows = [("标的", meta["ticker"] + (f"（{meta['alias']}）" if meta["alias"] else ""))]
    if meta["generated"]:
        rows.append(("生成时间", meta["generated"]))
    if meta["rating"]:
        rows.append(("投资评级", meta["rating"]))
    if meta["target"]:
        rows.append(("目标价", meta["target"]))
    if meta["horizon"]:
        rows.append(("时间周期", meta["horizon"]))
    rows.append(("研究流程", "分析师团队 → 研究辩论 → 交易计划 → 风险管理 → 组合决策"))
    table = "".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in rows if v
    )
    badge = (
        f'<p><span class="badge">{_esc(meta["rating"])}</span></p>'
        if meta["rating"]
        else ""
    )
    lead = (
        f'<p class="lead">{_esc(meta["summary"])}</p>' if meta["summary"] else ""
    )
    sub_bits = ["TradingAgents 多智能体研究报告"]
    if meta["generated"]:
        sub_bits.append(f"生成 {meta['generated']}")
    return f"""
<section class="cover">
  <div class="kicker">TradingAgents · Multi-Agent Research Note</div>
  <h1>{title}</h1>
  <div class="sub">{_esc('　|　'.join(sub_bits))}</div>
  {badge}
  <table class="meta">{table}</table>
  {lead}
  <p class="disclaimer">本文件由 TradingAgents 多智能体框架根据公开市场数据自动生成，仅供研究参考，不构成投资建议。过往表现不代表未来收益。</p>
</section>
"""


def resolve_md(src: Path) -> Path:
    if src.is_dir():
        md = src / "complete_report.md"
    else:
        md = src
    if not md.is_file():
        raise FileNotFoundError(f"找不到 complete_report.md: {src}")
    return md


def export_pdf(md_path: Path, pdf_path: Path) -> None:
    try:
        import markdown
    except ImportError as exc:
        raise SystemExit("需要 markdown 包：.venv/bin/pip install markdown") from exc
    if not CHROME.is_file():
        raise SystemExit(f"找不到 Chrome: {CHROME}")
    if not CJK_FONT.is_file():
        raise SystemExit(f"找不到 CJK 字体: {CJK_FONT}")

    md = md_path.read_text(encoding="utf-8")
    meta = parse_meta(md, md_path.parent)
    body = markdown.markdown(
        md, extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{_esc(meta["ticker"])} · TradingAgents 分析报告</title>
  <style>{COVER_CSS}</style>
</head>
<body>
{build_cover(meta)}
<article class="content">
{body}
</article>
</body>
</html>
"""
    work = Path(tempfile.mkdtemp(prefix="ta-report-pdf-"))
    try:
        shutil.copy(CJK_FONT, work / "cjk.ttf")
        html_path = work / "report.html"
        html_path.write_text(html, encoding="utf-8")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                str(CHROME),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                "--allow-file-access-from-files",
                "--virtual-time-budget=20000",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not pdf_path.is_file():
            raise SystemExit(
                f"Chrome 导出失败 rc={proc.returncode}\n{proc.stderr[:800]}"
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    data = pdf_path.read_bytes()
    # 必须嵌 CJK 字体，否则预览会乱码（上一版只嵌了 Menlo）
    if b"ArialUnicodeMS" not in data and b"Arial Unicode" not in data:
        raise SystemExit(
            f"PDF 未嵌入 CJK 字体，可能仍会乱码: {pdf_path}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export TradingAgents report to PDF")
    parser.add_argument(
        "report",
        type=Path,
        help="reports/<TICKER>_<timestamp> 目录，或 complete_report.md 路径",
    )
    parser.add_argument("-o", "--output", type=Path, help="输出 PDF 路径")
    args = parser.parse_args()
    md_path = resolve_md(args.report)
    pdf_path = args.output or (md_path.parent / "complete_report.pdf")
    export_pdf(md_path, pdf_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
