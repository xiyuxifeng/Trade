from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.agents.data_agent.skills.import_trade_logs import (
    import_trade_logs_from_csv,
    import_trade_logs_from_html,
    import_trade_logs_from_excel,
    import_trade_logs_from_pdf,
    _normalize_trade_row,
)


def test_normalize_trade_row_infers_account_and_trader() -> None:
    trade, issue = _normalize_trade_row(
        {
            "trader_id": "trader_a",
            "symbol": "000001.SZ",
            "side": "buy",
            "executed_at": "2026-04-06T09:35:00+08:00",
            "quantity": "100",
            "price": "10.5",
        },
        source="csv_import",
        trader_account_map={"trader_a": "acct-1"},
    )

    assert issue is None
    assert trade is not None
    assert trade.account_id == "acct-1"
    assert trade.raw_payload["trader_id"] == "trader_a"
    assert trade.amount == trade.quantity * trade.price


def test_import_trade_logs_from_csv_dedups_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(
        "\n".join(
            [
                "trader_id,symbol,side,executed_at,quantity,price,account_id",
                "trader_a,000001.SZ,buy,2026-04-06T09:35:00+08:00,100,10.5,acct-1",
                "trader_a,000001.SZ,buy,2026-04-06T09:35:00+08:00,100,10.5,acct-1",
            ]
        ),
        encoding="utf-8",
    )

    records, stats = import_trade_logs_from_csv(csv_path=csv_path, trader_account_map={"trader_a": "acct-1"})

    assert len(records) == 1
    assert stats.rows_seen == 2
    assert stats.duplicates == 1
    assert records[0].account_id == "acct-1"
    assert records[0].symbol == "000001.SZ"


def test_import_trade_logs_from_excel(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "trades.xlsx"
    pd.DataFrame(
        [
            {
                "trader_id": "trader_a",
                "symbol": "510300.SH",
                "side": "sell",
                "executed_at": "2026-04-06T14:55:00+08:00",
                "quantity": 200,
                "price": 3.45,
                "account_id": "acct-2",
            }
        ]
    ).to_excel(xlsx_path, index=False)

    records, stats = import_trade_logs_from_excel(xlsx_path=xlsx_path)

    assert stats.rows_seen == 1
    assert len(records) == 1
    assert records[0].symbol == "510300.SH"
    assert records[0].side == "sell"


def test_import_trade_logs_from_html(tmp_path: Path) -> None:
    html_path = tmp_path / "trades.html"
    pd.DataFrame(
        [
            {
                "trader_id": "trader_a",
                "symbol": "000002.SZ",
                "side": "buy",
                "executed_at": "2026-04-06T10:00:00+08:00",
                "quantity": 50,
                "price": 20.0,
                "account_id": "acct-3",
            }
        ]
    ).to_html(html_path, index=False)

    records, stats = import_trade_logs_from_html(html_path=html_path)

    assert stats.rows_seen == 1
    assert len(records) == 1
    assert records[0].symbol == "000002.SZ"


def test_import_trade_logs_from_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "trades.pdf"
    pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 180 >>
stream
BT
(trader_a 000003.SZ buy 2026-04-06T10:30:00+08:00 120 8.5 acct-4) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
trailer
<< /Root 1 0 R >>
startxref
0
%%EOF
"""
    pdf_path.write_bytes(pdf_bytes)

    records, stats = import_trade_logs_from_pdf(pdf_path=pdf_path)

    assert stats.rows_seen == 1
    assert len(records) == 1
    assert records[0].symbol == "000003.SZ"
    assert records[0].account_id == "acct-4"
