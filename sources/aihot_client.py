import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_BASE_URL = "https://aihot.virxact.com"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_USER_AGENT = "xz-ai-daily/1.0 (+https://github.com/pxz-ooo/xz-ai-daily)"


@dataclass
class DailyDigest:
    title: str
    summary: str
    date_str: str
    markdown_body: str
    tags: list[str]
    category: str = "AI日报"
    slug_suffix: str = "daily"


def get_timezone_name() -> str:
    return os.environ.get("AIHOT_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE


def get_today_str() -> str:
    return datetime.now(ZoneInfo(get_timezone_name())).date().isoformat()


def get_mode() -> str:
    return os.environ.get("AIHOT_SOURCE_MODE", "daily").strip().lower() or "daily"


def get_base_url() -> str:
    return os.environ.get("AIHOT_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_user_agent() -> str:
    return os.environ.get("AIHOT_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT


def use_offline_sample() -> bool:
    return os.environ.get("AIHOT_OFFLINE_MODE", "").strip() == "1"


def get_max_items() -> int:
    raw_value = os.environ.get("AIHOT_MAX_ITEMS", "12").strip() or "12"
    return max(1, min(int(raw_value), 30))


def get_lookback_days() -> int:
    raw_value = os.environ.get("AIHOT_LOOKBACK_DAYS", "3").strip() or "3"
    return max(1, min(int(raw_value), 30))


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and payload.get("data") is not None:
        return payload["data"]
    return payload


def fetch_json(path: str, params: dict[str, str] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{get_base_url()}{path}{query}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": get_user_agent(),
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AI HOT API request failed {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"AI HOT API network error: {exc.reason}") from exc


def normalize_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        text = value.strip()
        return text or fallback
    return str(value).strip() or fallback


def normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_daily_payload(payload: Any) -> DailyDigest:
    data = unwrap_data(payload)
    if isinstance(data, list):
        if not data:
            raise RuntimeError("AI HOT daily endpoint returned an empty list.")
        data = data[0]
    if not isinstance(data, dict):
        raise RuntimeError("AI HOT daily endpoint returned an unexpected payload.")

    date_str = normalize_text(data.get("date"), get_today_str())
    title = normalize_text(data.get("title") or data.get("headline"), f"AI HOT 日报 {date_str}")
    summary = normalize_text(
        data.get("summary") or data.get("description"),
        "来自 AI HOT 的每日精编日报。",
    )

    markdown_body = normalize_text(data.get("markdown") or data.get("content") or data.get("body"))
    if markdown_body:
        return DailyDigest(
            title=title,
            summary=summary,
            date_str=date_str,
            markdown_body=markdown_body,
            tags=["AI HOT", "日报", "精选"],
            category="AI日报",
            slug_suffix="daily",
        )

    sections = normalize_list(data.get("sections") or data.get("highlights") or data.get("items"))
    if not sections:
        raise RuntimeError("AI HOT daily endpoint did not return any usable content.")

    lines = [f"# {title}", "", summary, ""]
    for section in sections[: get_max_items()]:
        if isinstance(section, str):
            lines.append(f"- {section.strip()}")
            continue

        if not isinstance(section, dict):
            continue

        item_title = normalize_text(section.get("title"), "未命名条目")
        item_summary = normalize_text(section.get("summary") or section.get("description"))
        item_url = normalize_text(section.get("url") or section.get("link"))

        lines.append(f"## {item_title}")
        if item_summary:
            lines.append(item_summary)
        if item_url:
            lines.append(f"原文链接：{item_url}")
        lines.append("")

    return DailyDigest(
        title=title,
        summary=summary,
        date_str=date_str,
        markdown_body="\n".join(lines).strip(),
        tags=["AI HOT", "日报", "精选"],
        category="AI日报",
        slug_suffix="daily",
    )


def extract_items(payload: Any) -> list[dict[str, Any]]:
    data = unwrap_data(payload)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = (
            normalize_list(data.get("items"))
            or normalize_list(data.get("results"))
            or normalize_list(data.get("list"))
        )
    else:
        items = []

    normalized_items = [item for item in items if isinstance(item, dict)]
    if not normalized_items:
        raise RuntimeError("AI HOT items endpoint did not return any usable items.")
    return normalized_items


def parse_items_payload(payload: Any, mode: str) -> DailyDigest:
    items = extract_items(payload)
    date_str = get_today_str()
    mode_label = "全量动态" if mode == "all" else "精选动态"
    summary = f"来自 AI HOT 的{mode_label}，按最近时间窗口聚合。"

    lines = [f"# AI HOT {mode_label} - {date_str}", "", summary, ""]
    for item in items[: get_max_items()]:
        title = normalize_text(item.get("title"), "未命名条目")
        item_summary = normalize_text(item.get("summary") or item.get("description"))
        category = normalize_text(item.get("category") or item.get("type"))
        source = normalize_text(item.get("source") or item.get("site_name"))
        item_url = normalize_text(item.get("url") or item.get("link"))
        published_at = normalize_text(item.get("published_at") or item.get("date"))

        meta_parts = [part for part in [category, source, published_at] if part]
        lines.append(f"## {title}")
        if meta_parts:
            lines.append(f"信息：{' | '.join(meta_parts)}")
        if item_summary:
            lines.append(item_summary)
        if item_url:
            lines.append(f"原文链接：{item_url}")
        lines.append("")

    return DailyDigest(
        title=f"AI HOT {mode_label} {date_str}",
        summary=summary,
        date_str=date_str,
        markdown_body="\n".join(lines).strip(),
        tags=["AI HOT", "动态", "全量" if mode == "all" else "精选"],
        category="AI动态",
        slug_suffix=mode,
    )


def build_since_iso() -> str:
    now = datetime.now(ZoneInfo(get_timezone_name()))
    since = now - timedelta(days=get_lookback_days())
    return since.isoformat(timespec="seconds")


def build_offline_sample() -> DailyDigest:
    mode = get_mode()
    date_str = get_today_str()
    if mode == "all":
        title = f"AI HOT 全量动态 {date_str}"
        summary = "AI HOT 离线全量动态示例数据，用于本地或 CI 校验。"
        body_lines = [
            f"# {title}",
            "",
            summary,
            "",
            "## 动态流示例",
            "",
            "- OpenAI 发布新模型与 API 能力更新",
            "- Anthropic 分享企业级 Agent 实践",
            "- 多模态与视频生成赛道持续升温",
        ]
        return DailyDigest(
            title=title,
            summary=summary,
            date_str=date_str,
            markdown_body="\n".join(body_lines),
            tags=["AI HOT", "动态", "离线示例"],
            category="AI动态",
            slug_suffix="sample-all",
        )

    title = f"AI HOT 日报 {date_str}"
    summary = "AI HOT 离线日报示例数据，用于本地或 CI 校验。"
    markdown_body = f"""# {title}

{summary}

## 今日精编

- OpenAI 发布新模型与 API 能力更新
- Anthropic 分享企业级 Agent 实践
- 多模态与视频生成赛道持续升温
"""
    return DailyDigest(
        title=title,
        summary=summary,
        date_str=date_str,
        markdown_body=markdown_body,
        tags=["AI HOT", "日报", "离线示例"],
        category="AI日报",
        slug_suffix="sample-daily",
    )


def load_aihot_digest() -> DailyDigest:
    if use_offline_sample():
        return build_offline_sample()

    mode = get_mode()
    if mode == "daily":
        date_str = get_today_str()
        attempts = [
            (f"/api/public/daily/{date_str}", None),
            ("/api/public/daily", {"date": date_str}),
            ("/api/public/daily", None),
        ]
        last_error = None
        for path, params in attempts:
            try:
                return parse_daily_payload(fetch_json(path, params))
            except RuntimeError as exc:
                last_error = exc
        raise RuntimeError(f"Failed to fetch AI HOT daily digest: {last_error}")

    if mode not in {"selected", "all"}:
        raise RuntimeError("AIHOT_SOURCE_MODE must be one of: daily, selected, all.")

    payload = fetch_json(
        "/api/public/items",
        {
            "mode": mode,
            "take": str(get_max_items()),
            "since": build_since_iso(),
        },
    )
    return parse_items_payload(payload, mode)
