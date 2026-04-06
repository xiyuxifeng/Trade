from __future__ import annotations

import csv
import re
import zlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.session import session_scope
from src.models.trade_log import TradeLog
from src.pipeline.validation import DataValidator, ValidationIssue, ValidationSeverity


@dataclass(slots=True)
class TradeLogImportStats:
    rows_seen: int = 0
    imported: int = 0
    skipped: int = 0
    invalid: int = 0
    duplicates: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)


def _parse_decimal(value: Any, *, default: Decimal | None = None) -> Decimal | None:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _normalize_side(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"buy", "sell"}:
        return text
    if text in {"b", "long"}:
        return "buy"
    if text in {"s", "short"}:
        return "sell"
    return None


def _resolve_account_and_trader(
    *,
    row: dict[str, Any],
    trader_account_map: dict[str, str] | None,
) -> tuple[str | None, str | None]:
    trader_id = str(row.get("trader_id") or row.get("trader") or "").strip() or None
    account_id = str(row.get("account_id") or row.get("account") or "").strip() or None

    if trader_account_map:
        if trader_id and not account_id:
            account_id = trader_account_map.get(trader_id, account_id)
        if account_id and not trader_id:
            reverse = {v: k for k, v in trader_account_map.items()}
            trader_id = reverse.get(account_id, trader_id)

    if not account_id and trader_id:
        account_id = trader_id
    if not trader_id and account_id:
        trader_id = account_id
    return account_id, trader_id


def _normalize_trade_row(
    row: dict[str, Any],
    *,
    source: str,
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[TradeLog | None, ValidationIssue | None]:
    symbol = str(row.get("symbol") or row.get("ticker") or "").strip()
    if not symbol:
        return None, ValidationIssue(
            code="trade.import.symbol.missing",
            severity=ValidationSeverity.ERROR,
            message="Symbol is missing.",
        )

    side = _normalize_side(row.get("side"))
    if side is None:
        return None, ValidationIssue(
            code="trade.import.side.invalid",
            severity=ValidationSeverity.ERROR,
            message="Side is invalid or missing.",
            context={"value": row.get("side")},
        )

    executed_at = _parse_datetime(row.get("executed_at") or row.get("trade_time") or row.get("datetime"))
    if executed_at is None:
        return None, ValidationIssue(
            code="trade.import.executed_at.missing",
            severity=ValidationSeverity.ERROR,
            message="Executed timestamp is missing or invalid.",
        )

    quantity = _parse_decimal(row.get("quantity") or row.get("qty"))
    price = _parse_decimal(row.get("price") or row.get("fill_price"))
    if quantity is None or quantity <= 0:
        return None, ValidationIssue(
            code="trade.import.quantity.invalid",
            severity=ValidationSeverity.ERROR,
            message="Quantity must be positive.",
            context={"value": row.get("quantity") or row.get("qty")},
        )
    if price is None or price <= 0:
        return None, ValidationIssue(
            code="trade.import.price.invalid",
            severity=ValidationSeverity.ERROR,
            message="Price must be positive.",
            context={"value": row.get("price") or row.get("fill_price")},
        )

    amount = _parse_decimal(row.get("amount"))
    if amount is None:
        amount = (quantity * price).quantize(Decimal("0.000001"))

    fee = _parse_decimal(row.get("fee"), default=Decimal("0")) or Decimal("0")
    position_side = str(row.get("position_side") or "long").strip().lower()
    if position_side not in {"long", "short", "flat"}:
        position_side = "long"

    account_id, trader_id = _resolve_account_and_trader(
        row=row,
        trader_account_map=trader_account_map,
    )

    if not account_id:
        return None, ValidationIssue(
            code="trade.import.account.missing",
            severity=ValidationSeverity.ERROR,
            message="Account id is missing and could not be inferred.",
        )

    raw_payload = {**row}
    if trader_id:
        raw_payload["trader_id"] = trader_id

    trade = TradeLog(
        source=source,
        external_id=str(row.get("external_id") or row.get("order_id") or "").strip() or None,
        account_id=account_id,
        symbol=symbol,
        market=str(row.get("market") or market).strip() or market,
        side=side,
        position_side=position_side,
        order_type=str(row.get("order_type") or row.get("order") or "").strip() or None,
        executed_at=executed_at,
        quantity=quantity,
        price=price,
        amount=amount,
        fee=fee,
        currency=str(row.get("currency") or currency).strip() or currency,
        strategy_tag=str(row.get("strategy_tag") or row.get("tag") or "").strip() or None,
        rationale=str(row.get("rationale") or row.get("note") or "").strip() or None,
        raw_payload=raw_payload,
    )
    return trade, None


def _import_trade_rows(
    rows: list[dict[str, Any]],
    *,
    source: str,
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    stats = TradeLogImportStats()
    records: list[TradeLog] = []
    validator = DataValidator()
    seen_keys: set[tuple[str, str, datetime, Decimal, Decimal]] = set()

    for row in rows:
        stats.rows_seen += 1
        trade, issue = _normalize_trade_row(
            row,
            source=source,
            market=market,
            currency=currency,
            trader_account_map=trader_account_map,
        )
        if issue is not None:
            stats.invalid += 1
            stats.issues.append(issue)
            continue
        if trade is None:
            stats.invalid += 1
            continue

        key = (
            trade.account_id,
            trade.symbol,
            trade.executed_at,
            Decimal(trade.quantity),
            Decimal(trade.price),
        )
        if key in seen_keys:
            stats.duplicates += 1
            stats.issues.append(
                ValidationIssue(
                    code="trade.import.duplicate",
                    severity=ValidationSeverity.ERROR,
                    message="Duplicate trade row detected within import file.",
                    context={"symbol": trade.symbol, "account_id": trade.account_id},
                )
            )
            continue
        seen_keys.add(key)

        result = validator.validate_trade(trade)
        stats.issues.extend(result.issues)
        if not result.is_valid:
            stats.invalid += 1
            continue

        records.append(trade)

    return records, stats


def _decode_pdf_string(data: bytes) -> str:
    text = data.decode("latin-1", errors="ignore")
    text = text.replace(r"\\", "\\")
    text = text.replace(r"\(", "(").replace(r"\)", ")")
    text = text.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
    return text


def _extract_pdf_text(pdf_path: Path) -> str:
    raw = pdf_path.read_bytes()
    texts: list[str] = []

    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, flags=re.S):
        chunk = match.group(1)
        try:
            chunk = zlib.decompress(chunk)
        except Exception:
            pass

        for string_match in re.finditer(rb"\(((?:\\.|[^\\)])*)\)\s*T[jJ]", chunk):
            texts.append(_decode_pdf_string(string_match.group(1)))

        for tj_match in re.finditer(rb"\[(.*?)\]\s*TJ", chunk, flags=re.S):
            array = tj_match.group(1)
            for literal_match in re.finditer(rb"\(((?:\\.|[^\\)])*)\)", array):
                texts.append(_decode_pdf_string(literal_match.group(1)))

    if texts:
        return "\n".join(texts)

    return raw.decode("latin-1", errors="ignore")


def _parse_trade_text_lines(
    text: str,
    *,
    source: str,
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "\t" in line:
            parts = [part.strip() for part in line.split("\t")]
        elif "," in line:
            parts = [part.strip() for part in line.split(",")]
        else:
            parts = [part.strip() for part in re.split(r"\s+", line)]
        if len(parts) < 6:
            continue
        row = {
            "trader_id": parts[0],
            "symbol": parts[1],
            "side": parts[2],
            "executed_at": parts[3],
            "quantity": parts[4],
            "price": parts[5],
        }
        if len(parts) > 6:
            row["account_id"] = parts[6]
        rows.append(row)

    return _import_trade_rows(
        rows,
        source=source,
        market=market,
        currency=currency,
        trader_account_map=trader_account_map,
    )


def import_trade_logs_from_csv(
    *,
    csv_path: Path,
    source: str = "csv_import",
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    return _import_trade_rows(
        rows,
        source=source,
        market=market,
        currency=currency,
        trader_account_map=trader_account_map,
    )


def import_trade_logs_from_excel(
    *,
    xlsx_path: Path,
    source: str = "excel_import",
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    df = pd.read_excel(xlsx_path)
    rows = df.fillna("").to_dict(orient="records")
    return _import_trade_rows(
        rows,
        source=source,
        market=market,
        currency=currency,
        trader_account_map=trader_account_map,
    )


def import_trade_logs_from_html(
    *,
    html_path: Path,
    source: str = "html_import",
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    tables = pd.read_html(html_path)
    rows: list[dict[str, Any]] = []
    for table in tables:
        rows.extend(table.fillna("").to_dict(orient="records"))
    return _import_trade_rows(
        rows,
        source=source,
        market=market,
        currency=currency,
        trader_account_map=trader_account_map,
    )


def import_trade_logs_from_pdf(
    *,
    pdf_path: Path,
    source: str = "pdf_import",
    market: str = "CN",
    currency: str = "CNY",
    trader_account_map: dict[str, str] | None = None,
) -> tuple[list[TradeLog], TradeLogImportStats]:
    text = _extract_pdf_text(pdf_path)
    return _parse_trade_text_lines(
        text,
        source=source,
        market=market,
        currency=currency,
        trader_account_map=trader_account_map,
    )


async def store_trade_logs(trades: list[TradeLog]) -> int:
    if not trades:
        return 0
    async with session_scope() as session:
        session.add_all(trades)
        await session.flush()
    return len(trades)
