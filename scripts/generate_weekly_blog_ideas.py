#!/usr/bin/env python3
"""Generate a weekly ReviewOMG blog topic pool from recent industry notes."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDUSTRY_DIR = ROOT / "20.行业情报"
OUTPUT_DIR = ROOT / "30.博客选题池"

KEYWORD_GROUPS = {
    "star projector": ["star projector", "galaxy projector", "3d galaxy projector", "homestar", "sega"],
    "ambient light": ["ambient light", "ambient lighting", "rgb", "rgbic", "smart lighting"],
    "gaming room lighting": ["gaming room lighting", "game room lights", "gaming lights"],
    "kids night light": ["kids night light", "night light", "kids", "children"],
    "bedroom led projector": ["bedroom led projector", "bedroom", "home decor"],
    "social video": ["tiktok", "youtube", "instagram", "viral", "shorts"],
    "amazon": ["amazon", "best seller", "bestseller", "review"],
    "brands": ["rosetta", "govee", "onefire", "flylily", "sega", "homestar"],
}

BASE_IDEAS = [
    ("Best Star Projectors for Bedroom: What Actually Matters Before You Buy", "Commercial investigation", "best star projector, bedroom galaxy projector, star projector for adults", "用亮度、投影面积、噪音、定时、遥控/APP、蓝牙音箱、价格段建立 ReviewOMG 评分标准。"),
    ("Galaxy Projector vs Ambient Light: Which Is Better for Your Room?", "Comparison", "galaxy projector vs ambient light, bedroom ambient lighting", "解释两类产品的场景差异：沉浸式天花板效果 vs 局部氛围补光。"),
    ("Best Gaming Room Lighting Ideas Using Galaxy Projectors and RGB Lights", "Informational + affiliate", "gaming room lighting, gaming lights, galaxy projector gaming room", "围绕桌面、墙面、天花板、显示器背光、音乐同步构建方案。"),
    ("Are Star Projectors Safe for Kids? A Parent-Focused Buying Checklist", "Trust / safety", "kids night light projector, star projector for kids, night light safety", "重点讨论亮度、激光安全、材质、定时、噪音、线材、遥控器小零件。"),
    ("Rossetta vs Govee vs OneFire vs Sega Homestar: Which Galaxy Projector Brand Fits You?", "Brand comparison", "Rossetta vs Govee, OneFire projector, Sega Homestar review", "品牌定位对比：入门装饰、智能灯生态、儿童夜灯、天文真实性、高端投影体验。"),
    ("TikTok Made Me Buy It: Are Viral Galaxy Projectors Worth It?", "Trend validation", "TikTok galaxy projector, viral star projector, TikTok room lights", "拆解热门视频卖点和真实购买风险，适合做 ReviewOMG 观点型博客。"),
    ("How to Choose a Bedroom LED Projector Without Getting a Cheap Gimmick", "Buying guide", "bedroom LED projector, LED galaxy projector, projector light for bedroom", "聚焦低价产品常见问题：噪音、图案重复、亮度不足、遥控失灵、APP 体验差。"),
    ("Amazon Star Projector Reviews: What Buyers Complain About Most", "Review mining", "Amazon star projector reviews, galaxy projector complaints", "把评论痛点转化为测评清单：耐用性、真实效果、声音、包装、退货原因。"),
]


def recent_notes(days: int = 7) -> list[Path]:
    if not INDUSTRY_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days + 1)
    notes = []
    for path in INDUSTRY_DIR.glob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
        if not m:
            continue
        try:
            note_date = datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if note_date >= cutoff:
            notes.append(path)
    return sorted(notes)


def extract_titles(text: str) -> list[str]:
    titles = []
    for line in text.splitlines():
        m = re.match(r"- \*\*(.+?)\*\*", line)
        if m:
            titles.append(m.group(1).strip())
            continue
        m = re.search(r"\| \[([^\]]+)\]\(https?://", line)
        if m:
            titles.append(m.group(1).strip())
    seen, out = set(), []
    for title in titles:
        if title not in seen:
            seen.add(title)
            out.append(title)
    return out[:25]


def score_topics(corpus: str) -> Counter[str]:
    lower = corpus.lower()
    scores = Counter()
    for group, terms in KEYWORD_GROUPS.items():
        for term in terms:
            scores[group] += lower.count(term)
    return scores


def rank_ideas(scores: Counter[str]) -> list[tuple[str, str, str, str]]:
    ranked_groups = [group for group, count in scores.most_common() if count > 0]

    def rank(idea: tuple[str, str, str, str]) -> int:
        text = " ".join(idea).lower()
        for idx, group in enumerate(ranked_groups):
            if any(term in text for term in KEYWORD_GROUPS[group]):
                return idx
        return 99

    return sorted(BASE_IDEAS, key=rank)


def render() -> str:
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    notes = recent_notes()
    corpus = "\n\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in notes)
    scores = score_topics(corpus)
    titles = extract_titles(corpus)

    lines = [
        "---",
        f"date: {date_str}",
        "category: weekly-blog-topic-pool",
        "site: reviewomg.com",
        "tags:",
        "  - reviewomg",
        "  - 博客选题池",
        "  - SEO",
        "  - 星空灯",
        "  - 氛围灯",
        f"source_note_count: {len(notes)}",
        "generated_by: GitHub Actions",
        "---",
        "",
        f"# {date_str} ReviewOMG 每周博客选题池",
        "",
        "> 自动生成说明：每周日北京时间 15:01 生成。输入来自最近 7 天的 [[20.行业情报/README.md|行业情报库]]，用于规划 reviewomg.com 的博客、测评和 SEO 内容。",
        "",
        "## 本周信号强度",
    ]
    positive_scores = [(group, count) for group, count in scores.most_common() if count > 0]
    if positive_scores:
        for group, count in positive_scores:
            lines.append(f"- **{group}**：{count}")
    else:
        lines.append("- 暂无足够历史情报；以下为基础 evergreen 选题池。")

    lines += ["", "## 本周可写博客选题", "", "| 优先级 | 标题 | 搜索意图 | 关键词 | 写作角度 |", "|---|---|---|---|---|"]
    for idx, (title, intent, keywords, angle) in enumerate(rank_ideas(scores), start=1):
        lines.append(f"| P{idx} | {title} | {intent} | {keywords} | {angle} |")

    lines += [
        "",
        "## 可做成短视频/社媒的角度",
        "- 15 秒房间改造：关灯前/关灯后对比，突出 galaxy projector 的即时视觉冲击。",
        "- 买前避坑：展示噪音、亮度、图案清晰度、遥控器、定时功能。",
        "- 品牌盲测：只看效果不看品牌，让用户猜 Rossetta / Govee / OneFire / Sega。",
        "- Gaming setup before/after：RGB 灯带 + star projector + 桌面背光组合。",
        "",
        "## 本周参考新闻标题",
    ]
    if titles:
        lines.extend(f"- {title}" for title in titles)
    else:
        lines.append("- 暂无最近 7 天行业新闻标题。")

    lines += ["", "## 来源笔记"]
    if notes:
        lines.extend(f"- [[{path.as_posix()}]]" for path in notes)
    else:
        lines.append("- 暂无来源笔记。")

    lines += [
        "",
        "## 下周人工补充建议",
        "- 从 Amazon 手动补充 3-5 个高热 SKU 的价格、评分、评论痛点。",
        "- 从 TikTok / YouTube / Instagram 手动补充 5 个热门视频链接和开头 3 秒钩子。",
        "- 标记哪些选题适合 affiliate review，哪些适合 informational SEO。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{datetime.now().strftime('%Y-%m-%d')} ReviewOMG 每周博客选题池.md"
    out_path.write_text(render(), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
