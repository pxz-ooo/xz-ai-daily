import datetime
from pathlib import Path


def get_daily_paper_markdown() -> Path:
    today = datetime.date.today().strftime("%Y-%m-%d")
    content = f"""---
title: "AI Daily Paper {today}"
summary: "今日 AI 论文与热点摘要"
date: "{today}"
tags:
  - "AI Daily Paper"
  - "AI"
category: "AI日报"
slug: "ai-daily-paper-{today}"
---

# AI 论文日报 - {today}

这里是今日的 AI 论文摘要。

这份内容目前是最小可运行示例，后面可以替换为真实抓取结果。

- 论文 1：Attention Is All You Need
- 论文 2：An Image is Worth 16x16 Words
"""

    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{today}-daily-paper.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"生成文件: {output_path}")
    return output_path


if __name__ == "__main__":
    get_daily_paper_markdown()
