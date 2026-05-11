from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

from src.common.config import load_app_config
from src.db.session import get_session_factory
from src.market_data.ohlcv_service import OHLCVService
from src.models.ohlcv_bar import OHLCVBar
from src.services.base import BaseService, ServiceResult


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def _to_plain(value: Any) -> Any:
    """把 dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


class MarketService(BaseService):
    """OHLCV 抓取与行情查询的共享服务。"""

    service_name = "market"

    def __init__(
        self,
        *,
        ohlcv_service: OHLCVService | None = None,
        ohlcv_service_factory: Callable[..., OHLCVService] | None = None,
        session_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._ohlcv_service = ohlcv_service
        self._ohlcv_service_factory = ohlcv_service_factory
        self._session_factory = session_factory

    def _create_ohlcv_service(self, config_path: str | Path) -> OHLCVService:
        """根据配置创建 OHLCVService。"""
        if self._ohlcv_service is not None:
            return self._ohlcv_service

        loaded = load_app_config(config_path)
        factory = self._ohlcv_service_factory or OHLCVService
        session_factory = get_session_factory()
        akshare_cfg = loaded.config.akshare
        return factory(
            session_factory=session_factory,
            min_request_interval_seconds=akshare_cfg.min_request_interval_seconds,
            max_retries=akshare_cfg.max_retries,
            retry_backoff_seconds=akshare_cfg.retry_backoff_seconds,
            fallback_enabled=akshare_cfg.fallback_enabled,
        )

    def _get_session_factory(self) -> Callable[..., Any]:
        """返回用于行情查询的 session factory。"""
        if self._session_factory is not None:
            return self._session_factory
        return get_session_factory

    async def crawl_ohlcv(
        self,
        *,
        config_path: str | Path,
        mode: str = "incremental",
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> ServiceResult:
        """抓取 OHLCV 日线。"""
        loaded = load_app_config(config_path)
        base_dir = _project_base_dir(loaded.config_path)
        service = self._create_ohlcv_service(config_path)

        if symbols is None:
            raise ValueError("symbols must be provided for the web service wrapper")

        if mode == "full":
            results = await service.crawl_bars(symbols=symbols[:limit], start_date=start_date, end_date=end_date)
        elif mode == "incremental":
            results = await service.crawl_bars(symbols=symbols[:limit], start_date=start_date, end_date=end_date)
        else:
            raise ValueError("mode must be full or incremental")

        return ServiceResult(
            status="ok",
            message="ohlcv crawl completed",
            payload={
                "config_path": str(loaded.config_path),
                "base_dir": str(base_dir),
                "mode": mode,
                "results": results,
            },
        )

    async def get_latest_close(self, symbol: str) -> ServiceResult:
        """查询最新收盘价。"""
        service = self._ohlcv_service or self._create_ohlcv_service("config/app.yaml")
        close = await service.get_latest_close(symbol)
        return ServiceResult(
            status="ok" if close is not None else "partial",
            message="latest close fetched" if close is not None else "latest close missing",
            payload={"symbol": symbol, "close": close},
        )

    async def get_bars(self, symbol: str, start_date: date, end_date: date) -> ServiceResult:
        """查询 OHLCV bars。"""
        service = self._ohlcv_service or self._create_ohlcv_service("config/app.yaml")
        bars = await service.get_bars(symbol, start_date, end_date)
        return ServiceResult(
            status="ok",
            message="bars fetched",
            payload={"symbol": symbol, "count": len(bars), "bars": _to_plain(bars)},
        )

    async def get_bars_as_df(self, symbol: str, start_date: date, end_date: date) -> ServiceResult:
        """查询 OHLCV bars 并返回 DataFrame 结构。"""
        service = self._ohlcv_service or self._create_ohlcv_service("config/app.yaml")
        df = await service.get_bars_as_df(symbol, start_date, end_date)
        return ServiceResult(
            status="ok",
            message="bars dataframe fetched",
            payload={"symbol": symbol, "rows": len(df), "dataframe": _to_plain(df.to_dict(orient="records"))},
        )

    async def list_symbols(self, *, q: str | None = None, limit: int = 200) -> ServiceResult:
        """列出数据库中的行情标的。"""
        session_factory = self._get_session_factory()()
        async with session_factory.begin() as session:
            stmt = select(OHLCVBar.symbol).distinct()
            if q:
                stmt = stmt.where(OHLCVBar.symbol.ilike(f"%{q}%"))
            stmt = stmt.order_by(OHLCVBar.symbol.asc()).limit(limit)
            result = await session.execute(stmt)
            symbols = [row[0] for row in result.all()]

        return ServiceResult(
            status="ok",
            message="symbols listed",
            payload={"count": len(symbols), "items": symbols},
        )

    async def get_ohlcv(self, symbol: str, start_date: date, end_date: date) -> ServiceResult:
        """按 symbol 和日期范围查询 K 线数据。"""
        session_factory = self._get_session_factory()()
        async with session_factory.begin() as session:
            stmt = (
                select(OHLCVBar)
                .where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.trade_date >= start_date,
                    OHLCVBar.trade_date <= end_date,
                )
                .order_by(OHLCVBar.trade_date.asc())
            )
            result = await session.execute(stmt)
            bars = list(result.scalars().all())

        items = [
            {
                "time": bar.trade_date.isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
                "turnover": float(bar.turnover) if bar.turnover is not None else None,
            }
            for bar in bars
        ]
        return ServiceResult(
            status="ok",
            message="ohlcv fetched",
            payload={
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "count": len(items),
                "items": items,
            },
        )
