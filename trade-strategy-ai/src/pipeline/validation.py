from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Iterable, Sequence

from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
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
        record: MarketData,
        previous_close: Decimal | None = None,
    ) -> ValidationResult:
        result = ValidationResult(record_type="market_data")

        if record.traded_at > datetime.now(UTC) + timedelta(minutes=5):
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
        issues: list[ValidationIssue] = []

        for trade in trades:
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

    def detect_volume_anomalies(self, records: Iterable[MarketData]) -> list[ValidationIssue]:
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
