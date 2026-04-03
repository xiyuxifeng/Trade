from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
from src.models.trade_log import TradeLog
from src.pipeline.validation import DataValidator, ValidationSeverity


def test_article_comment_count_mismatch_warns() -> None:
    validator = DataValidator()
    article = BlogArticle(
        source="tgb",
        source_url="https://example.com/a/1",
        title="A" * 12,
        author_name="author",
        crawled_at=datetime.now(UTC),
        content_text="B" * 200,
        comment_count=2,
        comments_payload=[{"id": "1"}],
    )

    result = validator.validate_article(article)

    assert result.is_valid is True
    assert any(issue.code == "article.comments.count_mismatch" for issue in result.issues)


def test_trade_amount_mismatch_is_error() -> None:
    validator = DataValidator()
    trade = TradeLog(
        source="manual",
        account_id="acct-1",
        symbol="000001.SZ",
        market="CN",
        side="buy",
        position_side="long",
        executed_at=datetime.now(UTC),
        quantity=Decimal("100"),
        price=Decimal("10"),
        amount=Decimal("999"),
        fee=Decimal("0"),
        currency="CNY",
    )

    result = validator.validate_trade(trade)

    assert result.is_valid is False
    assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)


def test_market_gap_is_flagged() -> None:
    validator = DataValidator()
    record = MarketData(
        source="akshare",
        symbol="000001.SZ",
        market="CN",
        timeframe="1d",
        traded_at=datetime.now(UTC) - timedelta(days=1),
        open=Decimal("12"),
        high=Decimal("12.5"),
        low=Decimal("11.8"),
        close=Decimal("12.4"),
        volume=Decimal("1000000"),
        turnover=Decimal("12400000"),
    )

    result = validator.validate_market_record(record, previous_close=Decimal("10"))

    assert any(issue.code == "market.close.large_gap" for issue in result.issues)
