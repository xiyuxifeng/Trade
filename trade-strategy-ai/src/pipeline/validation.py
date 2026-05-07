from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Iterable, Sequence

from src.models.blog_article import BlogArticle
from src.models.ohlcv_bar import OHLCVBar
from src.models.trade_log import TradeLog


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    message: str
    field_name: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationResult:
    record_type: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return all(issue.severity != ValidationSeverity.ERROR for issue in self.issues)

    def add_issue(
        self,
        code: str,
        severity: ValidationSeverity,
        message: str,
        *,
        field_name: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                severity=severity,
                message=message,
                field_name=field_name,
                context=context or {},
            )
        )


class DataValidator:
    def validate_article(self, article: BlogArticle) -> ValidationResult:
        result = ValidationResult(record_type="blog_article")

        if not article.title.strip():
            result.add_issue("article.title.empty", ValidationSeverity.ERROR, "Article title is empty.")
        if len(article.content_text.strip()) < 80:
            result.add_issue(
                "article.content.short",
                ValidationSeverity.WARNING,
                "Article body is too short for reliable rule extraction.",
                field_name="content_text",
            )
        if article.published_at and article.published_at > article.crawled_at + timedelta(minutes=10):
            result.add_issue(
                "article.published_at.future",
                ValidationSeverity.ERROR,
                "Published timestamp is later than crawl timestamp.",
                field_name="published_at",
            )
        if article.comment_count and not article.comments_payload:
            result.add_issue(
                "article.comments.missing_payload",
                ValidationSeverity.WARNING,
                "Comment count is non-zero but no comment payload was stored.",
                field_name="comments_payload",
            )
        if article.comments_payload and article.comment_count != len(article.comments_payload):
            result.add_issue(
                "article.comments.count_mismatch",
                ValidationSeverity.WARNING,
                "Comment count does not match the number of captured comments.",
                field_name="comment_count",
                context={"payload_count": len(article.comments_payload)},
            )
        if not article.content_hash:
            result.add_issue(
                "article.content_hash.missing",
                ValidationSeverity.INFO,
                "Content hash is missing; deduplication will rely on source_url only.",
                field_name="content_hash",
            )

        return result

    def validate_trade(self, trade: TradeLog) -> ValidationResult:
        result = ValidationResult(record_type="trade_log")

        if trade.executed_at > datetime.now(UTC) + timedelta(minutes=5):
            result.add_issue(
                "trade.executed_at.future",
                ValidationSeverity.ERROR,
                "Trade execution time is in the future.",
                field_name="executed_at",
            )

        expected_amount = (Decimal(trade.quantity) * Decimal(trade.price)).quantize(Decimal("0.000001"))
        actual_amount = Decimal(trade.amount).quantize(Decimal("0.000001"))
        if abs(expected_amount - actual_amount) > Decimal("0.01"):
            result.add_issue(
                "trade.amount.mismatch",
                ValidationSeverity.ERROR,
                "Trade amount does not match quantity * price.",
                field_name="amount",
                context={"expected_amount": str(expected_amount), "actual_amount": str(actual_amount)},
            )

        if trade.fee == 0:
            result.add_issue(
                "trade.fee.zero",
                ValidationSeverity.INFO,
                "Fee is zero; confirm whether the broker waived fees or the field is missing.",
                field_name="fee",
            )
        if not trade.external_id and not trade.raw_payload:
            result.add_issue(
                "trade.identity.weak",
                ValidationSeverity.WARNING,
                "Trade has no external ID and no raw payload, duplicate detection may be unreliable.",
            )

        return result

    def validate_market_record(
        self,
        record: OHLCVBar,
        previous_close: Decimal | None = None,
    ) -> ValidationResult:
        result = ValidationResult(record_type="market_data")

        if record.trade_date > datetime.now(UTC).date() + timedelta(days=1):
            result.add_issue(
                "market.traded_at.future",
                ValidationSeverity.ERROR,
                "Market candle timestamp is in the future.",
                field_name="traded_at",
            )

        candle_range = Decimal(record.high) - Decimal(record.low)
        if candle_range == 0 and Decimal(record.volume) > 0:
            result.add_issue(
                "market.ohlc.flat_with_volume",
                ValidationSeverity.WARNING,
                "OHLC values are flat while volume is non-zero.",
                field_name="high",
            )

        if previous_close and previous_close > 0:
            change_ratio = abs(Decimal(record.close) - previous_close) / previous_close
            if change_ratio > Decimal("0.20"):
                result.add_issue(
                    "market.close.large_gap",
                    ValidationSeverity.WARNING,
                    "Close price gap exceeds 20%; treat as anomaly until verified.",
                    field_name="close",
                    context={"previous_close": str(previous_close), "change_ratio": str(change_ratio)},
                )

        return result

    def detect_trade_duplicates(self, trades: Sequence[TradeLog]) -> list[ValidationIssue]:
        seen_keys: set[tuple[str, str, datetime, Decimal, Decimal]] = set()
        seen_external_ids: set[str] = set()
        issues: list[ValidationIssue] = []

        for trade in trades:
            # Check external_id duplicate first
            ext_id = getattr(trade, "external_id", None) or ""
            if ext_id and ext_id in seen_external_ids:
                issues.append(
                    ValidationIssue(
                        code="trade.duplicate.external_id",
                        severity=ValidationSeverity.ERROR,
                        message="Duplicate trade detected by external_id.",
                        context={"external_id": ext_id, "symbol": trade.symbol},
                    )
                )
            elif ext_id:
                seen_external_ids.add(ext_id)

            # Check composite key duplicate
            key = (
                trade.account_id,
                trade.symbol,
                trade.executed_at,
                Decimal(trade.quantity),
                Decimal(trade.price),
            )
            if key in seen_keys:
                issues.append(
                    ValidationIssue(
                        code="trade.duplicate.composite_key",
                        severity=ValidationSeverity.ERROR,
                        message="Duplicate trade detected by composite business key.",
                        context={"symbol": trade.symbol, "account_id": trade.account_id},
                    )
                )
            else:
                seen_keys.add(key)

        return issues

    def detect_volume_anomalies(self, records: Iterable[OHLCVBar]) -> list[ValidationIssue]:
        record_list = list(records)
        volumes = [Decimal(record.volume) for record in record_list]
        if len(volumes) < 3:
            return []

        average_volume = sum(volumes) / Decimal(len(volumes))
        threshold = average_volume * Decimal("5")
        issues: list[ValidationIssue] = []

        for record, volume in zip(record_list, volumes, strict=False):
            if average_volume > 0 and volume > threshold:
                issues.append(
                    ValidationIssue(
                        code="market.volume.spike",
                        severity=ValidationSeverity.WARNING,
                        message="Volume exceeds five times the series average.",
                        field_name="volume",
                        context={"symbol": record.symbol, "volume": str(volume)},
                    )
                )

        return issues

    def detect_price_outliers(
        self, records: Sequence[OHLCVBar], iqr_multiplier: float = 1.5
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        by_symbol: dict[str, list[OHLCVBar]] = {}
        for r in records:
            by_symbol.setdefault(r.symbol, []).append(r)

        try:
            import numpy as np
        except ImportError:
            return issues

        for symbol, symbol_records in by_symbol.items():
            closes = [float(r.close) for r in symbol_records]
            if len(closes) < 3:
                continue
            q1 = float(np.percentile(closes, 25))
            q3 = float(np.percentile(closes, 75))
            iqr = q3 - q1
            lower = q3 - iqr_multiplier * iqr
            upper = q1 + iqr_multiplier * iqr

            for r in symbol_records:
                c = float(r.close)
                if c < lower or c > upper:
                    issues.append(
                        ValidationIssue(
                            code="market.price.outlier",
                            severity=ValidationSeverity.WARNING,
                            message=f"Close price {c} is outside IQR bounds [{lower:.4f}, {upper:.4f}].",
                            field_name="close",
                            context={
                                "symbol": symbol,
                                "close": str(r.close),
                                "iqr_lower": str(lower),
                                "iqr_upper": str(upper),
                            },
                        )
                    )
        return issues

    def detect_missing_fields(
        self, records: Sequence[BlogArticle | TradeLog | OHLCVBar]
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for record in records:
            if isinstance(record, BlogArticle):
                for field in ("title", "content_text", "source_url"):
                    val = getattr(record, field, None)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        issues.append(
                            ValidationIssue(
                                code="article.field.missing",
                                severity=ValidationSeverity.ERROR,
                                message=f"Required field '{field}' is missing or empty.",
                                field_name=field,
                                context={"field": field, "article_id": getattr(record, "id", None)},
                            )
                        )

            elif isinstance(record, TradeLog):
                for field in ("symbol", "executed_at", "quantity", "price", "side"):
                    val = getattr(record, field, None)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        issues.append(
                            ValidationIssue(
                                code="trade.field.missing",
                                severity=ValidationSeverity.ERROR,
                                message=f"Required field '{field}' is missing or empty.",
                                field_name=field,
                                context={"field": field, "trade_id": getattr(record, "id", None)},
                            )
                        )

            elif isinstance(record, OHLCVBar):
                for field in ("symbol", "trade_date", "open", "high", "low", "close", "volume"):
                    val = getattr(record, field, None)
                    if val is None or (isinstance(val, (int, float, Decimal)) and val == 0):
                        issues.append(
                            ValidationIssue(
                                code="market.field.missing",
                                severity=ValidationSeverity.ERROR,
                                message=f"Required field '{field}' is missing or zero.",
                                field_name=field,
                                context={"field": field, "market_id": getattr(record, "id", None)},
                            )
                        )

        return issues

    def detect_sequence_gaps(
        self, records: Sequence[OHLCVBar], expected_interval_minutes: int = 1440
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        by_symbol: dict[str, list[OHLCVBar]] = {}
        for r in records:
            by_symbol.setdefault(r.symbol, []).append(r)

        for symbol, symbol_records in by_symbol.items():
            sorted_records = sorted(symbol_records, key=lambda r: r.trade_date)
            for i in range(len(sorted_records) - 1):
                curr = sorted_records[i]
                next_r = sorted_records[i + 1]
                gap = next_r.trade_date - curr.trade_date
                expected = timedelta(minutes=expected_interval_minutes)
                if gap > expected * 1.5:
                    issues.append(
                        ValidationIssue(
                            code="market.series.gap",
                            severity=ValidationSeverity.WARNING,
                            message=f"Gap of {gap.days} days detected between {curr.trade_date} and {next_r.trade_date}.",
                            field_name="traded_at",
                            context={
                                "symbol": symbol,
                                "before": str(curr.trade_date),
                                "after": str(next_r.trade_date),
                                "gap_days": gap.days,
                            },
                        )
                    )
        return issues

    def detect_article_duplicates(self, articles: Sequence[BlogArticle]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        seen_hash: set[str] = set()
        seen_url: set[str] = set()

        for article in articles:
            h = getattr(article, "content_hash", None)
            h_duplicate = False
            if h and h in seen_hash:
                issues.append(
                    ValidationIssue(
                        code="article.duplicate.hash",
                        severity=ValidationSeverity.ERROR,
                        message="Duplicate article detected by content_hash.",
                        context={"hash": h, "source_url": article.source_url},
                    )
                )
                h_duplicate = True
            elif h:
                seen_hash.add(h)

            # Skip url check if hash already flagged as duplicate (same article)
            if h_duplicate:
                continue

            u = getattr(article, "source_url", None)
            if u and u in seen_url:
                issues.append(
                    ValidationIssue(
                        code="article.duplicate.url",
                        severity=ValidationSeverity.WARNING,
                        message="Duplicate article detected by source_url.",
                        context={"source_url": u},
                    )
                )
            elif u:
                seen_url.add(u)

        return issues

    def detect_market_duplicates(self, records: Sequence[OHLCVBar]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        seen_keys: set[tuple[str, str, str, datetime]] = set()

        for record in records:
            key = (record.symbol, record.trade_date)
            if key in seen_keys:
                issues.append(
                    ValidationIssue(
                        code="market.duplicate.key",
                        severity=ValidationSeverity.ERROR,
                        message="Duplicate market data record detected.",
                        context={"symbol": record.symbol, "traded_at": str(record.trade_date)},
                    )
                )
            else:
                seen_keys.add(key)
        return issues

    ADVERTISEMENT_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"Buy now!", re.IGNORECASE),
        re.compile(r"Click here", re.IGNORECASE),
        re.compile(r"\d{3}[-.]?\d{3}[-.]?\d{4}"),  # phone numbers
        re.compile(r"http[s]?://[^\s]+", re.IGNORECASE),  # URLs in content
    ]

    def detect_semantic_noise(self, articles: Sequence[BlogArticle]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for article in articles:
            content = getattr(article, "content_text", "") or ""
            matched: list[str] = []
            for pattern in self.ADVERTISEMENT_PATTERNS:
                if pattern.search(content):
                    matched.append(pattern.pattern)
            if len(matched) >= 2:
                issues.append(
                    ValidationIssue(
                        code="article.noise.semantic",
                        severity=ValidationSeverity.WARNING,
                        message="Article content matches multiple advertisement/semantic noise patterns.",
                        context={"patterns": matched, "article_id": getattr(article, "id", None)},
                    )
                )
        return issues

    def detect_trade_high_fee(
        self, trades: Sequence[TradeLog], threshold: Decimal = Decimal("0.01")
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for trade in trades:
            amount = Decimal(trade.amount)
            if amount <= 0:
                continue
            fee_ratio = Decimal(trade.fee) / amount
            if fee_ratio > threshold:
                issues.append(
                    ValidationIssue(
                        code="trade.fee.high",
                        severity=ValidationSeverity.WARNING,
                        message=f"Trade fee ratio {fee_ratio:.4%} exceeds threshold {threshold:.2%}.",
                        field_name="fee",
                        context={"fee": str(trade.fee), "amount": str(amount), "ratio": str(fee_ratio), "threshold": str(threshold)},
                    )
                )
        return issues
