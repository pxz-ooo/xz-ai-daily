from pathlib import Path

from aihot_client import load_aihot_digest


def build_front_matter_tags(tags: list[str]) -> str:
    return "\n".join(f'  - "{tag}"' for tag in tags)


def escape_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def get_daily_paper_markdown() -> Path:
    digest = load_aihot_digest()
    content = f"""---
title: "{escape_yaml(digest.title)}"
summary: "{escape_yaml(digest.summary)}"
date: "{digest.date_str}"
tags:
{build_front_matter_tags(digest.tags)}
category: "{escape_yaml(digest.category)}"
slug: "aihot-{digest.date_str}-{digest.slug_suffix}"
---

{digest.markdown_body}
"""

    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{digest.date_str}-aihot-{digest.slug_suffix}.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated file: {output_path}")
    return output_path


if __name__ == "__main__":
    get_daily_paper_markdown()
