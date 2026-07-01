#!/usr/bin/env python3
"""
ReviewOMG daily industry news collector.

Reads config/industry_news_queries.yml from the GitHub repo, queries Google News RSS,
and writes a dated Markdown intelligence note into 20.行业情报/.

Design goals:
- Cloud-first automation: all query rules live in the repo.
- Copyright-safe: stores short summaries, links, and analysis prompts, not full articles.
- Obsidian-native Markdown with YAML frontmatter and wikilink-friendly structure.
"""
from __future__ import annotations

import email.utils
import html
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:
    print("Missing dependency: pyyaml. Install with `pip install pyyaml`.", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "industry_news_queries.yml"


@dataclass
class NewsItem:
    category: str
    query: str
    title: str
    link: str
    source: str
    published: datetime | None
    summary: str


def strip_tags(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def google_news_rss_url(query: str, language: str, region: str) -> str:
    country = region.upper()
    lang_code = language.split("-")[0].lower()
    params = {
        "q": query,
        "hl": language,
        "gl": country,
        "ceid": f"{country}:{lang_code}",
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def fetch_url(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ReviewOMG industry news collector/1.0 (+https://reviewomg.com)",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def source_from_item(item: ET.Element) -> str:
    source_el = item.find("source")
    if source_el is not None and source_el.text:
        return strip_tags(source_el.text)
    title = item.findtext("title") or ""
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return "Unknown"


def fetch_query(
    category: str,
    query: str,
    *,
    language: str,
    region: str,
    max_items: int,
    cutoff: datetime,
) -> list[NewsItem]:
    url = google_news_rss_url(query, language, region)
    try:
        raw = fetch_url(url)
    except Exception as exc:
        print(f"WARN fetch failed for {query!r}: {exc}", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        print(f"WARN parse failed for {query!r}: {exc}", file=sys.stderr)
        return []

    items: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = strip_tags(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        published = parse_date(item.findtext("pubDate") or "")
        if published and published < cutoff:
            continue
        summary = strip_tags(item.findtext("description") or "")
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."
        if not title or not link:
            continue
        items.append(
            NewsItem(
                category=category,
                query=query,
                title=title,
                link=link,
                source=source_from_item(item),
                published=published,
                summary=summary,
            )
        )
        if len(items) >= max_items:
            break
    return items


def dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    for item in sorted(items, key=lambda x: x.published or min_dt, reverse=True):
        key = re.sub(r"\W+", "", item.title.lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def blog_angles(items: list[NewsItem]) -> list[str]:
    blob = "\n".join((i.title + " " + i.query).lower() for i in items)
    angles = []
    if "tiktok" in blob or "youtube" in blob or "instagram" in blob:
        angles.append("社媒爆款拆解：哪些星空灯/氛围灯视频角度更容易带来购买意图？")
    if "amazon" in blob:
        angles.append("Amazon 热度观察：星空灯买家最关心的功能、价格和差评风险。")
    if any(name in blob for name in ["govee", "rosetta", "onefire", "flylily", "homestar", "sega"]):
        angles.append("品牌对比选题：Rossetta、Govee、OneFire、FlyLily、Sega Homestar 的定位差异。")
    if "kids" in blob or "night light" in blob:
        angles.append("儿童夜灯安全与场景选题：睡眠、亮度、定时、噪音和材质。")
    if "gaming" in blob:
        angles.append("游戏房灯光方案：从 gaming room lighting 切入星空灯和 RGB 氛围灯组合。")
    angles.extend(
        [
            "Best Star Projector 购买指南：从亮度、投影面积、噪音、蓝牙音箱、APP 控制维度打分。",
            "Galaxy Projector vs Ambient Light：不同房间场景该选哪类产品？",
            "Bedroom LED Projector 选购误区：真实星空效果、旋转速度、遥控器与定时功能。",
        ]
    )
    out = []
    for angle in angles:
        if angle not in out:
            out.append(angle)
    return out[:8]


def render_markdown(today: datetime, config: dict[str, Any], items: list[NewsItem]) -> str:
    date_str = today.strftime("%Y-%m-%d")
    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        grouped[item.category].append(item)

    lines: list[str] = []
    lines.append("---")
    lines.append(f"date: {date_str}")
    lines.append("category: industry-news")
    lines.append("site: reviewomg.com")
    lines.append("niche:")
    for niche in config.get("site", {}).get("niche", []):
        lines.append(f"  - {niche}")
    lines.append("tags:")
    lines.append("  - reviewomg")
    lines.append("  - 行业情报")
    lines.append("  - 星空灯")
    lines.append("  - 氛围灯")
    lines.append("  - star-projector")
    lines.append(f"source_count: {len(items)}")
    lines.append("generated_by: GitHub Actions")
    lines.append("---")
    lines.append("")
    lines.append(f"# {date_str} 星空灯与氛围灯行业新闻")
    lines.append("")
    lines.append("> 自动生成说明：本笔记由 GitHub Actions 从仓库内配置读取关键词并抓取公开 Google News RSS。内容仅保留标题、短摘要、发布时间和来源链接，用于 ReviewOMG 博客选题和知识库积累。")
    lines.append("")
    lines.append("## 今日重点摘要")
    if items:
        for item in items[:8]:
            pub = item.published.strftime("%Y-%m-%d") if item.published else "unknown date"
            lines.append(f"- **{md_escape(item.title)}**（{md_escape(item.source)}，{pub}）")
    else:
        lines.append("- 今日未抓取到符合条件的新闻。可放宽 `config/industry_news_queries.yml` 的关键词或时间范围。")
    lines.append("")
    lines.append("## 可转化为博客的选题")
    for angle in blog_angles(items):
        lines.append(f"- {angle}")
    lines.append("")
    lines.append("## 分类新闻")
    if grouped:
        for category in sorted(grouped):
            lines.append("")
            lines.append(f"### {category}")
            lines.append("")
            lines.append("| 发布时间 | 来源 | 标题 | 关键词 |")
            lines.append("|---|---|---|---|")
            for item in grouped[category]:
                pub = item.published.strftime("%Y-%m-%d %H:%M") if item.published else "unknown"
                title_link = f"[{md_escape(item.title)}]({item.link})"
                lines.append(f"| {pub} | {md_escape(item.source)} | {title_link} | `{md_escape(item.query)}` |")
                if item.summary:
                    lines.append(f"|  |  | <small>{md_escape(item.summary)}</small> |  |")
    else:
        lines.append("")
        lines.append("暂无分类新闻。")
    lines.append("")
    lines.append("## 后续人工判断清单")
    lines.append("- 哪些新闻能支持 ReviewOMG 的购买指南、对比测评或 FAQ？")
    lines.append("- 是否出现新的产品功能趋势：APP 控制、音乐同步、低噪音马达、儿童安全、RGBIC、激光星云等？")
    lines.append("- 是否有可跟踪品牌：Rossetta、Govee、OneFire、FlyLily、Sega Homestar？")
    lines.append("- 是否适合拆成英文博客、中文研究笔记、Amazon 竞品卡片？")
    lines.append("")
    lines.append("## 配置来源")
    lines.append("- [[config/industry_news_queries.yml]]")
    lines.append("- [[scripts/fetch_industry_news.py]]")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    output_cfg = config.get("output", {})
    days_back = int(output_cfg.get("days_back", 7))
    max_items = int(output_cfg.get("max_items_per_query", 8))
    language = output_cfg.get("language", "en-US")
    region = output_cfg.get("region", "US")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    all_items: list[NewsItem] = []
    for category, queries in config.get("queries", {}).items():
        for query in queries or []:
            all_items.extend(
                fetch_query(category, query, language=language, region=region, max_items=max_items, cutoff=cutoff)
            )

    unique = dedupe(all_items)
    today = datetime.now()
    out_dir = ROOT / output_cfg.get("directory", "20.行业情报")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today.strftime('%Y-%m-%d')} 星空灯与氛围灯行业新闻.md"
    out_path.write_text(render_markdown(today, config, unique), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)} with {len(unique)} unique items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
