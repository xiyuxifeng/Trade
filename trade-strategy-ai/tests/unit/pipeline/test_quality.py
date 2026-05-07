from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from src.models.blog_article import BlogArticle
from src.models.ohlcv_bar import OHLCVBar
from src.models.trade_log import TradeLog
from src.pipeline.validation import (
    DataValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


# =============================================================================
# P1-023: detect_price_outliers tests
# =============================================================================


def test_price_outliers_detected():
    validator = DataValidator()
    records = [
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 1),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        ),
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 2),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        ),
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 3),
            open=10.0,
            high=10.0,
            low=10.0,
            close=100.0,
            volume=1000.0,
        ),
    ]
    issues = validator.detect_price_outliers(records)
    assert len(issues) == 1
    assert issues[0].code == "market.price.outlier"
    assert issues[0].severity == ValidationSeverity.WARNING


def test_price_outliers_no_false_positive():
    validator = DataValidator()
    records = [
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, i),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        )
        for i in range(1, 8)
    ]
    issues = validator.detect_price_outliers(records)
    assert len(issues) == 0


# =============================================================================
# P1-023: detect_missing_fields tests
# =============================================================================


def test_missing_fields_article():
    validator = DataValidator()
    article = BlogArticle(
        title="",  # empty - should trigger error
        content_text="some content",
        source_url="http://example.com",
    )
    issues = validator.detect_missing_fields([article])
    assert any(i.code == "article.field.missing" and i.field_name == "title" for i in issues)


def test_missing_fields_trade():
    validator = DataValidator()
    trade = TradeLog(
        symbol="",
        executed_at=datetime.now(UTC),
        quantity=Decimal("100"),
        price=Decimal("10"),
        side="buy",
    )
    issues = validator.detect_missing_fields([trade])
    assert any(i.code == "trade.field.missing" and i.field_name == "symbol" for i in issues)


def test_missing_fields_market_data():
    validator = DataValidator()
    record = OHLCVBar(
        symbol="",
        trade_date=date(2026, 4, 1),
        open=0.0,
        high=0.0,
        low=0.0,
        close=0.0,
        volume=1000.0,
    )
    issues = validator.detect_missing_fields([record])
    assert len(issues) >= 1


# =============================================================================
# P1-023: detect_sequence_gaps tests
# =============================================================================


def test_sequence_gap_detected():
    validator = DataValidator()
    records = [
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 1),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        ),
        # Gap: missing 2026-04-02
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 3),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        ),
    ]
    issues = validator.detect_sequence_gaps(records)
    assert len(issues) == 1
    assert issues[0].code == "market.series.gap"


# =============================================================================
# P1-023: run_anomaly_detection_task tests
# =============================================================================


def test_anomaly_detection_task_output(tmp_path):
    from src.pipeline.tasks.anomaly_detection_task import run_anomaly_detection_task

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    input_file = input_dir / "articles.jsonl"
    input_file.write_text(json.dumps({"title": "", "content_text": "test", "source_url": "http://x.com"}) + "\n")

    result = run_anomaly_detection_task(base_dir=tmp_path, input_paths=[input_file], force=False)

    assert result.report_path.exists()
    assert result.summary_path.exists()
    summary_data = json.loads(result.summary_path.read_text())
    assert summary_data["total"] >= 0


# =============================================================================
# P1-024: detect_article_duplicates + detect_market_duplicates tests
# =============================================================================


def test_article_duplicate_by_hash():
    validator = DataValidator()
    articles = [
        BlogArticle(title="A", content_text="content", source_url="http://a.com", content_hash="abc123"),
        BlogArticle(title="A", content_text="content", source_url="http://different.com", content_hash="abc123"),
        BlogArticle(title="B", content_text="content2", source_url="http://b.com", content_hash="def456"),
    ]
    issues = validator.detect_article_duplicates(articles)
    assert len(issues) == 1
    assert issues[0].code == "article.duplicate.hash"


def test_article_duplicate_by_url():
    validator = DataValidator()
    articles = [
        BlogArticle(title="A", content_text="content1", source_url="http://same.com", content_hash="hash1"),
        BlogArticle(title="B", content_text="content2", source_url="http://same.com", content_hash="hash2"),
    ]
    issues = validator.detect_article_duplicates(articles)
    url_issues = [i for i in issues if i.code == "article.duplicate.url"]
    assert len(url_issues) == 1


def test_article_duplicate_hash_and_url_same_article():
    """When both hash and url are duplicates for the same article, only hash issue is reported."""
    validator = DataValidator()
    articles = [
        BlogArticle(title="A", content_text="content1", source_url="http://same.com", content_hash="abc123"),
        BlogArticle(title="A", content_text="content1", source_url="http://same.com", content_hash="abc123"),
    ]
    issues = validator.detect_article_duplicates(articles)
    assert len(issues) == 1
    assert issues[0].code == "article.duplicate.hash"


def test_market_duplicate_by_key():
    validator = DataValidator()
    records = [
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 1),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=1000.0,
        ),
        OHLCVBar(
            symbol="000001",
            trade_date=date(2026, 4, 1),
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            volume=2000.0,
        ),
    ]
    issues = validator.detect_market_duplicates(records)
    assert len(issues) == 1
    assert issues[0].code == "market.duplicate.key"


# =============================================================================
# P1-024: detect_semantic_noise + detect_trade_high_fee tests
# =============================================================================


def test_semantic_noise_article():
    validator = DataValidator()
    article = BlogArticle(
        title="Test Article",
        content_text="This is a great article! Buy now! Click here for more info! Call 888-888-8888",
        source_url="http://example.com",
    )
    issues = validator.detect_semantic_noise([article])
    assert len(issues) >= 1
    assert any(i.code == "article.noise.semantic" for i in issues)


def test_trade_high_fee_detected():
    validator = DataValidator()
    trade = TradeLog(
        symbol="000001",
        account_id="acc1",
        executed_at=datetime.now(UTC),
        quantity=Decimal("100"),
        price=Decimal("10"),
        amount=Decimal("1000"),
        fee=Decimal("20"),  # 2% fee - above 1% threshold
        side="buy",
        position_side="long",
    )
    issues = validator.detect_trade_high_fee([trade], threshold=Decimal("0.01"))
    assert len(issues) == 1
    assert issues[0].code == "trade.fee.high"


def test_trade_high_fee_threshold_configurable():
    validator = DataValidator()
    trade = TradeLog(
        symbol="000001",
        account_id="acc1",
        executed_at=datetime.now(UTC),
        quantity=Decimal("100"),
        price=Decimal("10"),
        amount=Decimal("1000"),
        fee=Decimal("15"),  # 1.5% fee
        side="buy",
        position_side="long",
    )
    # threshold 0.02 (2%) - should NOT trigger
    issues_loose = validator.detect_trade_high_fee([trade], threshold=Decimal("0.02"))
    assert len(issues_loose) == 0
    # threshold 0.01 (1%) - should trigger
    issues_strict = validator.detect_trade_high_fee([trade], threshold=Decimal("0.01"))
    assert len(issues_strict) == 1


# =============================================================================
# P1-024: dedup_task tests
# =============================================================================


def test_dedup_task_output(tmp_path):
    from src.pipeline.tasks.dedup_task import run_dedup_task

    input_file = tmp_path / "trades.jsonl"
    lines = [
        json.dumps({
            "symbol": "000001",
            "account_id": "acc1",
            "executed_at": "2026-04-01T10:00:00Z",
            "quantity": "100",
            "price": "10",
            "amount": "1000",
            "fee": "1",
            "side": "buy",
            "position_side": "long",
        }),
        json.dumps({
            "symbol": "000001",
            "account_id": "acc1",
            "executed_at": "2026-04-01T10:00:00Z",
            "quantity": "100",
            "price": "10",
            "amount": "1000",
            "fee": "1",
            "side": "buy",
            "position_side": "long",
        }),  # duplicate
    ]
    input_file.write_text("\n".join(lines) + "\n")

    result = run_dedup_task(base_dir=tmp_path, input_paths=[input_file], force=False)
    assert result.deduped_path.exists()
    report = json.loads(result.report_path.read_text())
    assert report["total_input"] == 2
    assert report["duplicates_removed"] == 1


# =============================================================================
# P1-024: clean_task remove_duplicates tests
# =============================================================================


def test_clean_task_removes_duplicates(tmp_path):
    from src.pipeline.tasks.clean_task import run_clean_task

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    input_file = input_dir / "articles.jsonl"
    lines = [
        json.dumps({"title": "A", "content_text": "test", "source_url": "http://a.com", "content_hash": "hash1"}),
        json.dumps({"title": "A", "content_text": "test", "source_url": "http://different.com", "content_hash": "hash1"}),
    ]
    input_file.write_text("\n".join(lines) + "\n")

    result = run_clean_task(base_dir=tmp_path, input_paths=[input_file], remove_duplicates=True, force=True)
    assert result.cleaned_paths[0].exists()
    lines_out = result.cleaned_paths[0].read_text().strip().split("\n")
    # One should remain (one duplicate removed)
    assert len(lines_out) == 1


# =============================================================================
# P1-025: trade_duplicate_by_external_id test
# =============================================================================


def test_trade_duplicate_by_external_id():
    validator = DataValidator()
    trades = [
        TradeLog(
            symbol="000001",
            account_id="acc1",
            external_id="EXT001",
            executed_at=datetime.now(UTC),
            quantity=Decimal("100"),
            price=Decimal("10"),
            amount=Decimal("1000"),
            fee=Decimal("1"),
            side="buy",
            position_side="long",
        ),
        TradeLog(
            symbol="000001",
            account_id="acc1",
            external_id="EXT001",
            executed_at=datetime.now(UTC),
            quantity=Decimal("100"),
            price=Decimal("10"),
            amount=Decimal("1000"),
            fee=Decimal("1"),
            side="buy",
            position_side="long",
        ),
    ]
    issues = validator.detect_trade_duplicates(trades)
    ext_issues = [i for i in issues if i.code == "trade.duplicate.external_id"]
    assert len(ext_issues) == 1
