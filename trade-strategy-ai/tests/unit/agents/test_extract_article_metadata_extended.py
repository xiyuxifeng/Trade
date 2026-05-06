"""扩展 extract_article_metadata 支持 article_type 的集成测试"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.agents.data_agent.skills import extract_article_metadata as mod
from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle


def _make_article(
    *,
    content_text: str,
    title: str = "测试文章标题",
    raw_payload: dict | None = None,
) -> BlogArticle:
    """创建测试用 BlogArticle 对象"""
    return BlogArticle(
        id=uuid4(),
        source="tgb",
        source_article_id="test_article_1",
        source_url=f"https://example.com/{uuid4()}",
        title=title,
        author_name="test_author",
        author_id="123456",
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


def _make_metadata(article: BlogArticle, version: str = "v1") -> ArticleMetadata:
    """创建测试用 ArticleMetadata 对象"""
    return ArticleMetadata(
        id=uuid4(),
        article_id=article.id,
        version=version,
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
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class _Session:
    """模拟数据库 session"""
    def __init__(self, rows: list) -> None:
        self._rows = rows
        self._committed = False

    async def execute(self, _query: object) -> _Result:
        return _Result(self._rows)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    def add(self, obj: object) -> None:
        pass

    async def get(self, _model: type, _id: object) -> object | None:
        """模拟 session.get 方法"""
        for row in self._rows:
            if isinstance(row, tuple) and len(row) == 2:
                article, meta = row
                if hasattr(article, 'id') and article.id == _id:
                    return article
        return None

    async def scalar(self, _query: object) -> object | None:
        """模拟 session.scalar 方法"""
        return None


class _FakeClassificationResult:
    """模拟分类结果"""
    def __init__(self, article_type: str = "rule", confidence: float = 0.9) -> None:
        self.article_type = article_type
        self.confidence = confidence
        self.type_scores = {"rule": 0.9, "record": 0.1, "concept": 0.0, "noise": 0.0}
        self.reason = "test classification"


@pytest.mark.asyncio
async def test_process_one_article_sets_article_type_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试 _process_one_article 在分类成功时正确设置 article_type"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt content", encoding="utf-8")

    article = _make_article(content_text="这是测试内容" * 30)
    meta = _make_metadata(article)

    stats = mod.ExtractStats()
    pending_path = tmp_path / "pending.jsonl"
    error_log_path = tmp_path / "error.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"

    # 模拟分类器
    async def fake_classify_article(
        *, llm_client: object, title: str, content_text: str
    ) -> _FakeClassificationResult:
        return _FakeClassificationResult(article_type="rule", confidence=0.9)

    # 模拟 LLM 客户端
    class FakeClient:
        def is_enabled(self) -> bool:
            return True

        async def complete_json_with_retry(
            self, *, system_prompt: str, user_prompt: str
        ) -> object:
            # 返回一个模拟的 LLMResult
            class FakeResult:
                data = {
                    "extracted_concepts": [],
                    "trading_symbols": [],
                    "strategy_rules": [],
                    "preconditions": [],
                    "comment_insights": [],
                    "sentiment_score": 0.5,
                    "confidence_score": 0.8,
                }
                model = "test-model"

            return FakeResult()

    async def fake_normalize(syms: list[str]) -> list[str]:
        return syms

    @asynccontextmanager
    async def fake_session_scope():
        yield _Session([(article, meta)])

    # 应用 mock - 直接修改模块中的 classify_article 引用
    monkeypatch.setattr(mod, "_normalize_symbols_with_db", fake_normalize)
    monkeypatch.setattr(mod, "session_scope", fake_session_scope)

    # 动态 mock classify_article - 通过替换模块中的引用
    original_import = None

    class FakeModule:
        @staticmethod
        async def classify_article(
            *, llm_client: object, title: str, content_text: str
        ) -> _FakeClassificationResult:
            return _FakeClassificationResult(article_type="rule", confidence=0.9)

    # 直接在函数内部 import 时 monkeypatch 做不到，改用 patch.object
    import src.article_classifier.classifier as classifier_module
    monkeypatch.setattr(classifier_module, "classify_article", fake_classify_article)

    # 创建 fake client 实例
    fake_client = FakeClient()

    # 执行处理
    result = await mod._process_one_article(
        session=_Session([(article, meta)]),
        article=article,
        meta=meta,
        client=fake_client,
        prompts_dir=prompts_dir,
        stats=stats,
        pending_path=pending_path,
        error_log_path=error_log_path,
        checkpoint_path=checkpoint_path,
        version="v1",
    )

    # 验证 article_type 被正确设置
    assert meta.article_type == "rule"
    assert stats.scanned == 1


@pytest.mark.asyncio
async def test_process_one_article_sets_noise_on_classification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试 _process_one_article 在分类失败时默认为噪音"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt content", encoding="utf-8")

    article = _make_article(content_text="这是测试内容" * 30)
    meta = _make_metadata(article)

    stats = mod.ExtractStats()
    pending_path = tmp_path / "pending.jsonl"
    error_log_path = tmp_path / "error.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"

    # 模拟分类器抛出异常
    async def fake_classify_article_failure(
        *, llm_client: object, title: str, content_text: str
    ) -> None:
        raise Exception("Classification failed")

    class FakeClient:
        def is_enabled(self) -> bool:
            return True

        async def complete_json_with_retry(
            self, *, system_prompt: str, user_prompt: str
        ) -> object:
            class FakeResult:
                data = {
                    "extracted_concepts": [],
                    "trading_symbols": [],
                    "strategy_rules": [],
                    "preconditions": [],
                    "comment_insights": [],
                    "sentiment_score": 0.5,
                    "confidence_score": 0.8,
                }
                model = "test-model"

            return FakeResult()

    async def fake_normalize(syms: list[str]) -> list[str]:
        return syms

    @asynccontextmanager
    async def fake_session_scope():
        yield _Session([(article, meta)])

    monkeypatch.setattr(mod, "_normalize_symbols_with_db", fake_normalize)
    monkeypatch.setattr(mod, "session_scope", fake_session_scope)

    import src.article_classifier.classifier as classifier_module
    monkeypatch.setattr(classifier_module, "classify_article", fake_classify_article_failure)

    fake_client = FakeClient()

    result = await mod._process_one_article(
        session=_Session([(article, meta)]),
        article=article,
        meta=meta,
        client=fake_client,
        prompts_dir=prompts_dir,
        stats=stats,
        pending_path=pending_path,
        error_log_path=error_log_path,
        checkpoint_path=checkpoint_path,
        version="v1",
    )

    # 验证分类失败时默认为噪音
    assert meta.article_type == "noise"
    assert stats.scanned == 1


@pytest.mark.asyncio
async def test_process_one_article_no_classification_when_llm_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试 LLM 禁用时不进行分类"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt content", encoding="utf-8")

    article = _make_article(content_text="000001.SZ 看好上涨" * 10)
    meta = _make_metadata(article)

    stats = mod.ExtractStats()
    pending_path = tmp_path / "pending.jsonl"
    error_log_path = tmp_path / "error.jsonl"
    checkpoint_path = tmp_path / "checkpoint.jsonl"

    classify_called = False

    async def fake_classify_article(
        *, llm_client: object, title: str, content_text: str
    ) -> None:
        nonlocal classify_called
        classify_called = True
        return _FakeClassificationResult(article_type="rule")

    class DisabledClient:
        def __init__(self, _cfg: object) -> None:
            pass

        def is_enabled(self) -> bool:
            return False

    async def fake_normalize(syms: list[str]) -> list[str]:
        return syms

    @asynccontextmanager
    async def fake_session_scope():
        yield _Session([(article, meta)])

    monkeypatch.setattr(mod, "_normalize_symbols_with_db", fake_normalize)
    monkeypatch.setattr(mod, "session_scope", fake_session_scope)

    import src.article_classifier.classifier as classifier_module
    monkeypatch.setattr(classifier_module, "classify_article", fake_classify_article)

    fake_client = DisabledClient(None)

    result = await mod._process_one_article(
        session=_Session([(article, meta)]),
        article=article,
        meta=meta,
        client=fake_client,
        prompts_dir=prompts_dir,
        stats=stats,
        pending_path=pending_path,
        error_log_path=error_log_path,
        checkpoint_path=checkpoint_path,
        version="v1",
    )

    # 验证 LLM 禁用时没有调用分类
    assert not classify_called
    # LLM 关闭时 article_type 仍然会被写入噪音类型，避免字段空缺
    assert meta.article_type == "noise"


@pytest.mark.asyncio
async def test_process_article_isolated_sets_article_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试 _process_article_isolated 正确设置 article_type"""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ("concept_extraction.md", "rule_extraction.md", "precondition_extraction.md"):
        (prompts_dir / name).write_text("prompt content", encoding="utf-8")

    article = _make_article(content_text="这是测试内容" * 30, title="测试规则文章")
    meta = _make_metadata(article, version="v1")

    captured_classification = {}

    async def fake_classify_article(
        *, llm_client: object, title: str, content_text: str
    ) -> _FakeClassificationResult:
        result = _FakeClassificationResult(article_type="record", confidence=0.85)
        captured_classification["article_type"] = result.article_type
        return result

    class FakeClient:
        def __init__(self, _cfg: object) -> None:
            pass

        def is_enabled(self) -> bool:
            return True

        async def complete_json_with_retry(
            self, *, system_prompt: str, user_prompt: str
        ) -> object:
            class FakeResult:
                data = {
                    "extracted_concepts": [{"name": "test", "type": "concept", "evidence": "test"}],
                    "trading_symbols": ["000001.SZ"],
                    "strategy_rules": [],
                    "preconditions": [],
                    "comment_insights": [],
                    "sentiment_score": 0.3,
                    "confidence_score": 0.7,
                }
                model = "test-model"

            return FakeResult()

    async def fake_normalize(syms: list[str]) -> list[str]:
        return syms

    @asynccontextmanager
    async def fake_session_scope():
        yield _Session([(article, meta)])

    monkeypatch.setattr(mod, "_normalize_symbols_with_db", fake_normalize)
    monkeypatch.setattr(mod, "session_scope", fake_session_scope)

    import src.article_classifier.classifier as classifier_module
    monkeypatch.setattr(classifier_module, "classify_article", fake_classify_article)

    result = await mod._process_article_isolated(
        article_id=article.id,
        version="v1",
        llm_provider="test",
        client=FakeClient(None),
        prompts_dir=prompts_dir,
        pending_path=tmp_path / "pending.jsonl",
        error_log_path=tmp_path / "error.jsonl",
        checkpoint_path=tmp_path / "checkpoint.jsonl",
    )

    # 验证函数执行成功
    assert result["success"] is True
    # 验证分类器被调用（通过 captured_classification 确认）
    assert "article_type" in captured_classification
    assert captured_classification["article_type"] == "record"
