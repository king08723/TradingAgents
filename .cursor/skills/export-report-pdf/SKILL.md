---
name: export-report-pdf
description: Converts a TradingAgents reports/<TICKER>_<timestamp>/ run into a Chinese-capable PDF (complete_report.pdf) with an embedded CJK font. Use when the user asks to 输出 PDF、导出报告 PDF、把 complete_report.md 或 reports/ 目录转成 PDF.
---

# 导出 TradingAgents 报告 PDF

用户点名某个 `reports/<TICKER>_<timestamp>/` 目录或 `complete_report.md` 要 PDF 时，**直接跑脚本**，不要手写 Chrome/HTML，也不要再用未嵌 CJK 字体的 headless 打印（会乱码）。

## 步骤

1. 确认目录里有 `complete_report.md`。
2. 用项目虚拟环境执行：

```bash
.venv/bin/python .cursor/skills/export-report-pdf/scripts/export_report_pdf.py reports/<TICKER>_<timestamp>
```

缺 `markdown` 时先：`.venv/bin/pip install markdown`

3. 成功则同目录写出 `complete_report.pdf`，stdout 是该路径。脚本会校验 PDF 已嵌入 `ArialUnicodeMS`；未嵌入则失败，不得把乱码文件当成功交付。
4. 回复用户 PDF 路径。若 Cursor 预览仍乱码，建议用系统「预览」打开。

## 约束

- 输入是一次完整 run 的报告树，不是任意 markdown。
- 不要把 CJK 字体拷进仓库。
- 不要把中间 HTML 留在 `reports/`。
- macOS + Google Chrome + `/System/Library/Fonts/Supplemental/Arial Unicode.ttf`。
