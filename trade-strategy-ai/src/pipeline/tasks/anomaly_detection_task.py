from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir
from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
from src.models.trade_log import TradeLog
from src.pipeline.validation import DataValidator, ValidationIssue


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _to_blog_article(record: dict[str, Any]) -> BlogArticle:
    return BlogArticle(
        source=str(record.get("source") or ""),
        source_article_id=record.get("source_article_id"),
        source_url=str(record.get("source_url") or ""),
        title=str(record.get("title") or ""),
        author_name=record.get("author_name"),
        author_id=record.get("author_id"),
        published_at=_parse_dt(record.get("published_at")),
        crawled_at=_parse_dt(record.get("crawled_at")) or datetime.now(UTC),
        content_text=str(record.get("content_text") or ""),
        content_html=record.get("content_html"),
        summary=record.get("summary"),
        tags=record.get("tags") or [],
        content_hash=record.get("content_hash"),
        view_count=int(record.get("view_count") or 0),
        like_count=int(record.get("like_count") or 0),
        bookmark_count=int(record.get("bookmark_count") or 0),
        comment_count=int(record.get("comment_count") or 0),
        comments_payload=record.get("comments_payload") or [],
        raw_payload=record.get("raw_payload") or {},
    )


def _to_trade_log(record: dict[str, Any]) -> TradeLog:
    return TradeLog(
        symbol=str(record.get("symbol") or ""),
        market=record.get("market", ""),
        account_id=record.get("account_id") or "",
        side=record.get("side") or "",
        position_side=record.get("position_side") or "",
        quantity=record.get("quantity", 0),
        price=record.get("price", 0),
        amount=record.get("amount", 0),
        fee=record.get("fee", 0),
        executed_at=_parse_dt(record.get("executed_at")) or datetime.now(UTC),
        external_id=record.get("external_id"),
        raw_payload=record.get("raw_payload") or {},
    )


def _to_market_data(record: dict[str, Any]) -> MarketData:
    return MarketData(
        symbol=str(record.get("symbol") or ""),
        market=record.get("market", ""),
        timeframe=record.get("timeframe", ""),
        traded_at=_parse_dt(record.get("traded_at")) or datetime.now(UTC),
        open=record.get("open", 0),
        high=record.get("high", 0),
        low=record.get("low", 0),
        close=record.get("close", 0),
        volume=record.get("volume", 0),
        turnover=record.get("turnover", 0),
        source=record.get("source", ""),
    )


@dataclass(slots=True)
class AnomalyDetectionResult:
    report_path: Path
    summary_path: Path
    issues_count: int


def run_anomaly_detection_task(
    *, base_dir: Path, input_paths: list[Path], force: bool = False
) -> AnomalyDetectionResult:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "anomaly")
    report_path = out_dir / f"anomaly_report_{timestamp}.jsonl"
    summary_path = out_dir / f"anomaly_summary_{timestamp}.json"

    if report_path.exists() and not force:
        return AnomalyDetectionResult(report_path=report_path, summary_path=summary_path, issues_count=0)

    validator = DataValidator()
    all_issues: list[dict[str, Any]] = []

    articles: list[BlogArticle] = []
    trades: list[TradeLog] = []
    market_records: list[MarketData] = []

    for input_path in input_paths:
        records = _iter_jsonl(input_path)
        for record in records:
            record_type = record.get("_record_type", "")
            if record_type == "trade_log":
                trades.append(_to_trade_log(record))
            elif record_type == "market_data":
                market_records.append(_to_market_data(record))
            else:
                # Default to article
                articles.append(_to_blog_article(record))

    # Run anomaly detection methods
    if articles:
        all_issues.extend(validator.detect_missing_fields(articles))
        all_issues.extend(validator.detect_article_duplicates(articles))
        all_issues.extend(validator.detect_semantic_noise(articles))

    if trades:
        all_issues.extend(validator.detect_missing_fields(trades))
        all_issues.extend(validator.detect_trade_duplicates(trades))

    if market_records:
        all_issues.extend(validator.detect_missing_fields(market_records))
        all_issues.extend(validator.detect_price_outliers(market_records))
        all_issues.extend(validator.detect_sequence_gaps(market_records))

    # Write report
    ensure_dir(report_path.parent)
    with open(report_path, "w", encoding="utf-8") as f:
        for issue in all_issues:
            if isinstance(issue, ValidationIssue):
                f.write(
                    json.dumps(
                        {
                            "code": issue.code,
                            "severity": issue.severity.value,
                            "message": issue.message,
                            "field_name": issue.field_name,
                            "context": issue.context,
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )

    # Write summary
    summary: dict[str, int] = {}
    for issue in all_issues:
        code = issue.code if isinstance(issue, ValidationIssue) else str(issue)
        summary[code] = summary.get(code, 0) + 1
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {"total": len(all_issues), "by_code": summary, "articles": len(articles), "trades": len(trades), "market_records": len(market_records)},
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return AnomalyDetectionResult(report_path=report_path, summary_path=summary_path, issues_count=len(all_issues))
