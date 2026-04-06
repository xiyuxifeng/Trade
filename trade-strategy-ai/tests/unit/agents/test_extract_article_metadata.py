from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.agents.data_agent.skills import extract_article_metadata as mod
from src.llm.client import LLMError
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.persona.claim_keys import ClaimKey
from src.persona.schemas import ActionSpec, ArticlePrecondition, ArticleStrategyRule, InstrumentFocus


def _make_article(*, content_text: str, raw_payload: dict | None = None) -> BlogArticle:
    return BlogArticle(
        id=uuid4(),
        source="tgb",
        source_article_id="a1",
        source_url=f"https://example.com/{uuid4()}",
        title="sample",
        author_name="javxsp",
        author_id="10461311",
        published_at=datetime(2026, 4, 6, tzinfo=UTC),
        crawled_at=datetime(2026, 4, 6, tzinfo=UTC),
        content_text=content_text,
        content_html=None,
        summary=None,
        tags=[],
        content_hash=str(uuid4()),
        view_count=0,
        like_count=0,
        bookmark_count=0,
        comment_count=0,
        comments_payload=[],
        raw_payload=raw_payload or {},
    )


def _make_metadata(article: BlogArticle) -> ArticleMetadata:
    return ArticleMetadata(
        id=uuid4(),
        article_id=article.id,
        schema_version="v1",
        processed_at=None,
        extracted_concepts=[],
        trading_symbols=[],
        strategy_rules=[],
        preconditions=[],
        comment_insights=[],
        raw_llm_output={},
        sentiment_score=None,
        confidence_score=None,
    )


class _Result:
    def __init__(self, rows: list[tuple[BlogArticle, ArticleMetadata]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[BlogArticle, ArticleMetadata]]:
        return self._rows


class _Session:
    def __init__(self, rows: list[tuple[BlogArticle, ArticleMetadata]]) -> None:
        self._rows = rows

    async def execute(self, _query: object) -> _Result:
        return _Result(self._rows)

    async def flush(self) -> None:
        return None


def test_extract_stats_tracks_llm_and_fallback_calls() -> None:
    stats = mod.ExtractStats()
    assert stats.llm_calls == 0
    assert stats.fallback_calls == 0


def test_heuristic_extract_extracts_symbols_concepts_and_sentiment() -> None:
    article = _make_article(
        content_text="000001.SZ 今天强势涨停，继续看好 600000.SH，若跌破则止损。",
        raw_payload={"trader_id": "trader_a"},
    )

    raw = mod._heuristic_extract(article)

    assert raw["trading_symbols"] == ["000001.SZ", "600000.SH"]
    assert raw["extracted_concepts"][0]["name"] == "trader_a"
    assert raw["sentiment_score"] == pytest.approx(1 / 3)
    assert raw["confidence_score"] == 0.1


def test_validate_rules_and_preconditions_are_json_serializable() -> None:
    published_at = datetime(2026, 4, 6, tzinfo=UTC)
    rule = ArticleStrategyRule(
        claim_key=ClaimKey.entry_trigger,
        rule_type="entry",
        instrument_focus=InstrumentFocus.etf,
        condition={"op": "trend_up"},
        action=ActionSpec(type="enter", side="buy"),
        source_url="https://example.com/a",
        quoted_text="text",
        published_at=published_at,
    )
    precondition = ArticlePrecondition(
        claim_key=ClaimKey.filter_market_regime,
        instrument_focus=InstrumentFocus.mixed,
        condition={"op": "regime"},
        source_url="https://example.com/a",
        quoted_text="text",
        published_at=published_at,
    )

    rules = mod._validate_rules([rule.model_dump()], source_url=rule.source_url, published_at=published_at)
    preconditions = mod._validate_preconditions(
        [precondition.model_dump()],
        source_url=precondition.source_url,
        published_at=published_at,
    )

    assert isinstance(rules[0]["published_at"], str)
    assert isinstance(preconditions[0]["published_at"], str)


@pytest.mark.asyncio
async def test_extract_one_prompt_includes_structured_limits(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text(f"{name} content", encoding="utf-8")

    article = _make_article(content_text="这是一段足够长的正文。" * 20)
    captured: dict[str, str] = {}

    class FakeClient:
        async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return {}

    await mod._extract_one(client=FakeClient(), prompts_dir=prompts_dir, article=article)

    assert '"extracted_concepts": [...],   // 0-10 条' in captured["system_prompt"]
    assert '"comment_insights": [...],      // 0-3 条，从评论中提炼' in captured["system_prompt"]


@pytest.mark.asyncio
async def test_extract_and_store_metadata_uses_heuristic_when_llm_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt", encoding="utf-8")

    article = _make_article(
        content_text="000001.SZ 看好上涨机会，准备买入。" * 10,
        raw_payload={"trader_id": "trader_a"},
    )
    meta = _make_metadata(article)

    @asynccontextmanager
    async def fake_session_scope() -> object:
        yield _Session([(article, meta)])

    class DisabledClient:
        def __init__(self, _cfg: object) -> None:
            pass

        def is_enabled(self) -> bool:
            return False

    monkeypatch.setattr(mod, "session_scope", fake_session_scope)
    monkeypatch.setattr(mod, "LLMClient", DisabledClient)
    monkeypatch.setattr(mod, "from_env_and_config", lambda **_: SimpleNamespace())

    config = SimpleNamespace(llm=SimpleNamespace(provider=None, model=None, url=None, api_key=None))
    pending_path = tmp_path / "data" / "processed" / "pipeline" / "pending_tasks.jsonl"

    stats = await mod.extract_and_store_metadata(
        config=config,
        base_dir=tmp_path,
        limit=1,
        pending_tasks_path=pending_path,
    )

    assert stats.extracted == 1
    assert stats.fallback_calls == 1
    assert stats.llm_calls == 0
    assert meta.raw_llm_output["mode"] == "fallback_heuristic"
    assert meta.trading_symbols == ["000001.SZ"]
    assert pending_path.exists()


@pytest.mark.asyncio
async def test_extract_and_store_metadata_falls_back_on_llm_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt", encoding="utf-8")

    article = _make_article(content_text="600000.SH 走弱，考虑止损。" * 10)
    meta = _make_metadata(article)

    @asynccontextmanager
    async def fake_session_scope() -> object:
        yield _Session([(article, meta)])

    class EnabledClient:
        def __init__(self, _cfg: object) -> None:
            pass

        def is_enabled(self) -> bool:
            return True

    async def fake_extract_one(**_: object) -> dict[str, object]:
        raise LLMError("network timeout")

    monkeypatch.setattr(mod, "session_scope", fake_session_scope)
    monkeypatch.setattr(mod, "LLMClient", EnabledClient)
    monkeypatch.setattr(mod, "from_env_and_config", lambda **_: SimpleNamespace())
    monkeypatch.setattr(mod, "_extract_one", fake_extract_one)

    config = SimpleNamespace(llm=SimpleNamespace(provider="qwen", model="qwen-plus", url="u", api_key="k"))

    stats = await mod.extract_and_store_metadata(config=config, base_dir=tmp_path, limit=1)

    assert stats.extracted == 1
    assert stats.failed == 1
    assert stats.llm_calls == 1
    assert stats.fallback_calls == 1
    assert meta.raw_llm_output["mode"] == "fallback_on_error"
    assert meta.raw_llm_output["error"] == "network timeout"
    assert meta.trading_symbols == ["600000.SH"]
