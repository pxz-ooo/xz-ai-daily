import os
import re
from datetime import date, datetime
from pathlib import Path

import frontmatter
from notion_client import Client


NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")


def ensure_env() -> None:
    missing = []
    if not NOTION_TOKEN:
        missing.append("NOTION_TOKEN")
    if not NOTION_DATABASE_ID:
        missing.append("NOTION_DATABASE_ID")

    if missing:
        raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")


def normalize_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value:
        return str(value)
    return datetime.now().strftime("%Y-%m-%d")


def make_slug(title: str, date_str: str) -> str:
    normalized = title.lower().strip()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or f"ai-daily-{date_str}"


def get_data_source_id(notion: Client) -> str:
    database = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
    data_sources = database.get("data_sources", [])
    if not data_sources:
        raise RuntimeError("未找到 data source，请确认这是原始数据库而不是链接视图。")
    return data_sources[0]["id"]


def build_children(markdown_content: str) -> list[dict]:
    children = []
    for raw_line in markdown_content.strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("# "):
            children.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                }
            )
            continue

        if line.startswith("- "):
            children.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                }
            )
            continue

        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                },
            }
        )

    return children[:100]


def find_existing_page(notion: Client, data_source_id: str, title: str) -> dict | None:
    result = notion.data_sources.query(
        data_source_id=data_source_id,
        filter={"property": "title", "title": {"equals": title}},
    )
    pages = result.get("results", [])
    return pages[0] if pages else None


def create_page(
    notion: Client,
    data_source_id: str,
    title: str,
    summary: str,
    date_str: str,
    tags: list,
    category: str,
    slug: str,
    children: list[dict],
) -> None:
    notion.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties={
            "type": {"select": {"name": "Post"}},
            "title": {"title": [{"text": {"content": title}}]},
            "summary": {"rich_text": [{"text": {"content": summary}}]},
            "status": {"select": {"name": "Published"}},
            "category": {"select": {"name": category}},
            "tags": {"multi_select": [{"name": str(tag)} for tag in tags]},
            "slug": {"rich_text": [{"text": {"content": slug}}]},
            "date": {"date": {"start": date_str}},
        },
        children=children,
    )


def sync_markdown_to_notion(notion: Client, file_path: Path) -> None:
    data_source_id = get_data_source_id(notion)
    post = frontmatter.loads(file_path.read_text(encoding="utf-8"))

    title = post.get("title", "无标题")
    summary = post.get("summary", "今日 AI 内容摘要")
    date_str = normalize_date(post.get("date"))
    tags = post.get("tags", [])
    category = post.get("category", "AI日报")
    slug = post.get("slug", make_slug(title, date_str))
    children = build_children(post.content)

    existing = find_existing_page(notion, data_source_id, title)
    if existing:
        print(f"跳过已存在页面: {title}")
        return

    create_page(notion, data_source_id, title, summary, date_str, tags, category, slug, children)
    print(f"创建新页面: {title}")


def main() -> None:
    ensure_env()
    notion = Client(auth=NOTION_TOKEN)

    output_dir = Path(__file__).resolve().parent / "output"
    if not output_dir.exists():
        raise RuntimeError(f"输出目录不存在: {output_dir}")

    files = sorted(output_dir.glob("*.md"))
    if not files:
        print("output 目录中没有可同步的 Markdown 文件。")
        return

    for file_path in files:
        try:
            sync_markdown_to_notion(notion, file_path)
        except Exception as exc:
            print(f"同步失败 {file_path.name}: {exc}")


if __name__ == "__main__":
    main()
