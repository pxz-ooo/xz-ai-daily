import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_BASE_URL = "https://aihot.virxact.com"
DEFAULT_TIMEZONE = "Asia/Shanghai"
# AI HOT blocks the default curl UA; use a normal browser-like UA by default.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


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


def debug_enabled() -> bool:
    return os.environ.get("AIHOT_DEBUG", "").strip() == "1"


def get_max_items() -> int:
    raw_value = os.environ.get("AIHOT_MAX_ITEMS", "12").strip() or "12"
    return max(1, min(int(raw_value), 100))


def get_lookback_days() -> int:
    raw_value = os.environ.get("AIHOT_LOOKBACK_DAYS", "3").strip() or "3"
    return max(1, min(int(raw_value), 7))


def fetch_json(path: str, params: dict[str, str] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{get_base_url()}{path}{query}"
    debug_log(f"request url={url}")
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": get_user_agent(),
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            debug_log(f"response keys={list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__}")
            return payload
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


def append_if(lines: list[str], text: str) -> None:
    if text:
        lines.append(text)


def debug_log(message: str) -> None:
    if debug_enabled():
        print(f"[AIHOT_DEBUG] {message}", file=sys.stderr)


def parse_daily_payload(payload: Any) -> DailyDigest:
    if not isinstance(payload, dict):
        raise RuntimeError("AI HOT daily endpoint returned an unexpected payload.")

    date_str = normalize_text(payload.get("date"), get_today_str())
    lead = payload.get("lead") if isinstance(payload.get("lead"), dict) else {}
    lead_title = normalize_text(lead.get("title"))
    lead_paragraph = normalize_text(lead.get("leadParagraph"))
    debug_log(
        "daily schema "
        f"date={date_str} "
        f"has_lead={bool(lead)} "
        f"sections={len(normalize_list(payload.get('sections')))} "
        f"flashes={len(normalize_list(payload.get('flashes')))}"
    )

    title = f"AI HOT 日报 {date_str}"
    summary = lead_paragraph or "来自 AI HOT 的每日精编日报。"

    lines = [f"# {title}", ""]
    if lead_title:
        lines.append(f"## 今日导读")
        lines.append(lead_title)
        lines.append("")
    if lead_paragraph:
        lines.append(lead_paragraph)
        lines.append("")

    sections = [section for section in normalize_list(payload.get("sections")) if isinstance(section, dict)]
    for section in sections:
        label = normalize_text(section.get("label"))
        items = [item for item in normalize_list(section.get("items")) if isinstance(item, dict)]
        debug_log(f"daily section label={label or '(empty)'} items={len(items)}")
        if not label and not items:
            continue

        append_if(lines, f"## {label}" if label else "## 精选条目")
        for item in items[: get_max_items()]:
            item_title = normalize_text(item.get("title"), "未命名条目")
            item_summary = normalize_text(item.get("summary"))
            source_name = normalize_text(item.get("sourceName"))
            source_url = normalize_text(item.get("sourceUrl"))

            lines.append(f"### {item_title}")
            append_if(lines, item_summary)
            if source_name or source_url:
                meta = source_name if source_name and not source_url else f"{source_name} | {source_url}" if source_name else source_url
                append_if(lines, f"来源：{meta}")
            lines.append("")

    flashes = [flash for flash in normalize_list(payload.get("flashes")) if isinstance(flash, dict)]
    if flashes:
        debug_log(f"daily flashes count={len(flashes)}")
        lines.append("## 快讯")
        for flash in flashes[: get_max_items()]:
            flash_title = normalize_text(flash.get("title"), "未命名快讯")
            source_name = normalize_text(flash.get("sourceName"))
            source_url = normalize_text(flash.get("sourceUrl"))
            published_at = normalize_text(flash.get("publishedAt"))

            bullet = flash_title
            meta_parts = [part for part in [source_name, published_at, source_url] if part]
            if meta_parts:
                bullet = f"{bullet} ({' | '.join(meta_parts)})"
            lines.append(f"- {bullet}")

    markdown_body = "\n".join(lines).strip()
    return DailyDigest(
        title=title,
        summary=summary,
        date_str=date_str,
        markdown_body=markdown_body,
        tags=["AI HOT", "日报", "精选"],
        category="AI日报",
        slug_suffix="daily",
    )


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError("AI HOT items endpoint returned an unexpected payload.")
    items = [item for item in normalize_list(payload.get("items")) if isinstance(item, dict)]
    debug_log(
        "items schema "
        f"count={payload.get('count')} "
        f"hasNext={payload.get('hasNext')} "
        f"nextCursor={payload.get('nextCursor')}"
    )
    if not items:
        raise RuntimeError("AI HOT items endpoint did not return any usable items.")
    first = items[0]
    debug_log(
        "items first "
        f"id={normalize_text(first.get('id'))} "
        f"title={normalize_text(first.get('title'))} "
        f"category={normalize_text(first.get('category'))}"
    )
    return items


def parse_items_payload(payload: Any, mode: str) -> DailyDigest:
    items = extract_items(payload)
    date_str = get_today_str()
    mode_label = "全量动态" if mode == "all" else "精选动态"
    summary = f"来自 AI HOT 的{mode_label}，按最近时间窗口聚合。"

    lines = [f"# AI HOT {mode_label} - {date_str}", "", summary, ""]
    for item in items[: get_max_items()]:
        title = normalize_text(item.get("title"), "未命名条目")
        item_summary = normalize_text(item.get("summary"))
        category = normalize_text(item.get("category"))
        source = normalize_text(item.get("source"))
        item_url = normalize_text(item.get("url"))
        published_at = normalize_text(item.get("publishedAt"))
        score = item.get("score")
        selected = item.get("selected")

        lines.append(f"## {title}")
        meta_parts = [part for part in [category, source, published_at] if part]
        if score is not None:
            meta_parts.append(f"score={score}")
        if selected is not None:
            meta_parts.append("selected=true" if selected else "selected=false")
        if meta_parts:
            lines.append(f"信息：{' | '.join(meta_parts)}")
        append_if(lines, item_summary)
        append_if(lines, f"原文链接：{item_url}" if item_url else "")
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
        markdown_body = f"""# {title}

{summary}

## OpenAI 发布新模型
信息：ai-models | OpenAI Blog | 2026-06-09T08:00:00.000Z | score=88 | selected=true
模型与 API 能力同步升级。
原文链接：https://openai.com/

## Anthropic 更新 Claude
信息：ai-models | Anthropic Blog | 2026-06-09T07:00:00.000Z | score=82 | selected=false
企业级 Agent 实践继续推进。
原文链接：https://www.anthropic.com/
"""
        return DailyDigest(
            title=title,
            summary=summary,
            date_str=date_str,
            markdown_body=markdown_body,
            tags=["AI HOT", "动态", "离线示例"],
            category="AI动态",
            slug_suffix="sample-all",
        )

    title = f"AI HOT 日报 {date_str}"
    summary = "AI HOT 离线日报示例数据，用于本地或 CI 校验。"
    markdown_body = f"""# {title}

## 今日导读
OpenAI / Anthropic / Google 持续更新模型与产品能力

{summary}

## 模型发布/更新
### OpenAI 发布新模型
模型与 API 能力同步升级。
来源：OpenAI Blog | https://openai.com/

## 快讯
- Anthropic 更新 Claude (Anthropic Blog | 2026-06-09T07:00:00.000Z | https://www.anthropic.com/)
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
