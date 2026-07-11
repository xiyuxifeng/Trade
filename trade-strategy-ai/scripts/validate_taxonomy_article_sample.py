from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from config.database import dispose_cached_engine, get_session_factory
from src.models.blog_article import BlogArticle


CATEGORIES = {
    "情绪周期": ("情绪", "周期", "赚钱效应"),
    "弱转强": ("弱转强", "超预期", "竞价"),
    "龙头 / 主线": ("龙头", "主线", "核心"),
    "退潮 / 冰点": ("退潮", "冰点", "亏钱效应"),
    "放量 / 共振": ("放量", "共振", "量能"),
    "风控纪律": ("仓位", "止损", "空仓", "风险"),
    "纯市场复盘": ("复盘", "明天怎么看", "市场今天"),
}

EXPECTED_TYPES = {
    "情绪周期": ["semantic_experience", "research_hypothesis"],
    "弱转强": ["semantic_experience", "data_requirement_hint"],
    "龙头 / 主线": ["semantic_experience", "research_hypothesis"],
    "退潮 / 冰点": ["semantic_experience", "risk_control_hint"],
    "放量 / 共振": ["research_hypothesis", "rule_candidate"],
    "风控纪律": ["risk_control_hint"],
    "纯市场复盘": ["semantic_experience", "unusable_noise"],
}


def evidence_excerpt(text: str, terms: tuple[str, ...]) -> str:
    for term in terms:
        index = text.find(term)
        if index >= 0:
            return text[max(0, index - 30): index + len(term) + 50].strip()
    return text[:80].strip()


async def main() -> None:
    async with get_session_factory()() as session:
        articles = list(
            (
                await session.execute(
                    select(BlogArticle).order_by(BlogArticle.published_at.desc().nullslast(), BlogArticle.id)
                )
            ).scalars().all()
        )
    selected: list[dict[str, object]] = []
    used: set[str] = set()
    for category, terms in CATEGORIES.items():
        matches = []
        for article in articles:
            material = f"{article.title}\n{article.content_text or ''}"
            if str(article.id) not in used and any(term in material for term in terms):
                matches.append((article, material))
            if len(matches) == 2:
                break
        for article, material in matches:
            used.add(str(article.id))
            types = EXPECTED_TYPES[category]
            selected.append(
                {
                    "article_id": str(article.id),
                    "title": article.title,
                    "category": category,
                    "expected_primary_types": types,
                    "source_quote": evidence_excerpt(material, terms),
                    "source_fidelity": "quote_present",
                    "timestamp_safety": "blocked_pending_explicit_availability"
                    if any(item in {"research_hypothesis", "rule_candidate", "data_requirement_hint"} for item in types)
                    else "not_applicable_non_rule",
                    "formal_route": "blocked",
                }
            )
    counts = Counter(item for row in selected for item in row["expected_primary_types"])
    print(
        json.dumps(
            {
                "article_count": len(selected),
                "category_counts": dict(Counter(row["category"] for row in selected)),
                "type_distribution": dict(counts),
                "executable_rule_count": counts.get("executable_rule", 0),
                "all_formal_routes_blocked": all(row["formal_route"] == "blocked" for row in selected),
                "items": selected,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    await dispose_cached_engine()


if __name__ == "__main__":
    asyncio.run(main())
