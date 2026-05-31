from __future__ import annotations

import asyncio
import signal
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from src.common.config import load_app_config
from src.db.session import get_session_factory
from src.market_data.ohlcv_service import OHLCVService
from src.models.ohlcv_bar import OHLCVBar
from src.models.stock_info import StockInfo
from src.services.config_profile_service import ConfigProfileService
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
    _scheduler_lock = Lock()
    _scheduler: BackgroundScheduler | None = None
    _scheduler_pre_market: str | None = None
    _scheduler_post_close: str | None = None
    _scheduler_config_path: Path | None = None

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

    def _progress_payload(
        self,
        *,
        job_type: str,
        stage: str,
        current: int,
        total: int,
        current_step: str,
        current_fetcher: str | None = None,
        current_trade_date: str | None = None,
        status: str = "running",
        error: str | None = None,
    ) -> dict[str, Any]:
        """构造结构化进度载荷。"""
        percent = round((current / total) * 100, 2) if total else 0.0
        payload: dict[str, Any] = {
            "job_type": job_type,
            "stage": stage,
            "current": current,
            "total": total,
            "percent": percent,
            "remaining": max(total - current, 0),
            "current_step": current_step,
            "current_fetcher": current_fetcher,
            "current_trade_date": current_trade_date,
            "status": status,
            "error": error,
        }
        return payload

    def _emit_progress(self, progress_callback: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
        """安全触发进度回调。"""
        if progress_callback is not None:
            progress_callback(payload)

    def _create_ohlcv_service(self, config_source: Any) -> OHLCVService:
        """根据配置创建 OHLCVService。"""
        if self._ohlcv_service is not None:
            return self._ohlcv_service

        loaded = config_source if hasattr(config_source, "akshare") else load_app_config(config_source)
        factory = self._ohlcv_service_factory or OHLCVService
        session_factory = get_session_factory()
        akshare_cfg = loaded.akshare if hasattr(loaded, "akshare") else loaded.config.akshare
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

    async def _load_profile_runtime(self, profile_id: str) -> tuple[Any, Path]:
        """从 Profile materialize 行情运行态。"""
        runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
        return runtime.config, runtime.base_dir

    async def _resolve_config_path(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
    ) -> Path | None:
        """优先按 Profile 解析配置路径，兼容旧的 config_path 入口。"""
        if profile_id is not None and str(profile_id).strip():
            resolved = await ConfigProfileService().resolve_profile_config_path(str(profile_id).strip())
            if resolved is None:
                raise ValueError(f"profile not found: {profile_id}")
            return resolved
        if config_path is not None:
            return Path(config_path)
        return Path("config/app.yaml")

    @classmethod
    def _scheduler_snapshot(cls) -> dict[str, Any]:
        """返回当前 OHLCV 调度器状态。"""
        with cls._scheduler_lock:
            started = cls._scheduler is not None and cls._scheduler.running
            if not started:
                cls._scheduler = None
                cls._scheduler_pre_market = None
                cls._scheduler_post_close = None
                cls._scheduler_config_path = None
            return {
                "started": started,
                "pre_market": cls._scheduler_pre_market,
                "post_close": cls._scheduler_post_close,
                "config_path": str(cls._scheduler_config_path) if cls._scheduler_config_path else None,
            }

    @classmethod
    def _clear_scheduler(cls) -> None:
        """清理当前 OHLCV 调度器状态。"""
        with cls._scheduler_lock:
            scheduler = cls._scheduler
            cls._scheduler = None
            cls._scheduler_pre_market = None
            cls._scheduler_post_close = None
            cls._scheduler_config_path = None
        if scheduler is not None:
            scheduler.shutdown(wait=False)

    async def _run_ohlcv_incremental_crawl(self, *, config_path: str | Path) -> dict[str, int]:
        """执行 OHLCV 增量抓取，供调度器复用。"""
        service = self._create_ohlcv_service(config_path)
        session_factory = self._get_session_factory()()
        async with session_factory.begin() as session:
            stmt = (
                select(StockInfo.symbol, StockInfo.security_type)
                .where(StockInfo.security_type.in_(["stock", "index"]))
                .order_by(StockInfo.symbol.asc())
            )
            result = await session.execute(stmt)
            rows = result.all()

        symbols = [row[0] for row in rows]
        market_kind_by_symbol = {row[0]: row[1] for row in rows}
        if not symbols:
            return {}
        return await service.crawl_bars(
            symbols=symbols,
            start_date=date.today(),
            end_date=date.today(),
            market_kind_by_symbol=market_kind_by_symbol,
        )

    async def crawl_ohlcv(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        mode: str = "incremental",
        symbols: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
        runtime_state: dict[str, Any] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ServiceResult:
        """抓取 OHLCV 日线。"""
        runtime_profile_id = str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None
        if runtime_profile_id is not None:
            loaded_config, base_dir = await self._load_profile_runtime(runtime_profile_id)
            service = self._create_ohlcv_service(loaded_config)
            resolved_config_path: Path | None = None
        else:
            resolved_config_path = await self._resolve_config_path(profile_id=profile_id, config_path=config_path)
            if resolved_config_path is None:
                raise ValueError("missing required param: profile_id or config_path")
            loaded = load_app_config(resolved_config_path)
            base_dir = _project_base_dir(loaded.config_path)
            service = self._create_ohlcv_service(resolved_config_path)

        if symbols is None:
            raise ValueError("symbols must be provided for the web service wrapper")

        crawl_symbols = symbols if limit is None else symbols[:limit]
        total = len(crawl_symbols)

        crawl_kwargs = {
            "symbols": crawl_symbols,
            "start_date": start_date,
            "end_date": end_date,
        }
        if runtime_state is not None:
            crawl_kwargs["runtime_state"] = runtime_state
        if progress_callback is not None:
            crawl_kwargs["progress_callback"] = progress_callback

        if mode not in {"full", "incremental"}:
            raise ValueError("mode must be full or incremental")
        try:
            results = await service.crawl_bars(**crawl_kwargs)
        except TypeError as exc:
            if "progress_callback" not in str(exc):
                raise
            crawl_kwargs.pop("progress_callback", None)
            results = await service.crawl_bars(**crawl_kwargs)

        if progress_callback is not None and total > 0:
            completed = sum(1 for count in results.values() if count > 0)
            self._emit_progress(
                progress_callback,
                self._progress_payload(
                    job_type="ohlcv-crawl",
                    stage="crawl",
                    current=total,
                    total=total,
                    current_step=f"crawl:{crawl_symbols[-1]}",
                    current_fetcher=crawl_symbols[-1],
                    current_trade_date=start_date.isoformat() if start_date else None,
                    status="success" if completed == total else "partial",
                    error=None if completed == total else "some symbols failed",
                ),
            )

        return ServiceResult(
            status="ok",
            message="ohlcv crawl completed",
            payload={
                "config_path": str(resolved_config_path) if resolved_config_path is not None else None,
                "profile_id": runtime_profile_id,
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

    async def ohlcv_scheduler_status(self, *, profile_id: str | None = None, config_path: str | Path | None = None) -> ServiceResult:
        """查看 OHLCV 调度器状态和最新行情日期。"""
        runtime_profile_id = str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None
        if runtime_profile_id is not None:
            _loaded_config, base_dir = await self._load_profile_runtime(runtime_profile_id)
            config_path_value = None
        else:
            resolved_config_path = config_path or Path("config/app.yaml")
            loaded = load_app_config(resolved_config_path)
            base_dir = _project_base_dir(loaded.config_path)
            config_path_value = str(loaded.config_path)
        scheduler_state = self._scheduler_snapshot()
        session_factory = self._get_session_factory()()
        async with session_factory.begin() as session:
            latest_trade_date = await session.scalar(select(func.max(OHLCVBar.trade_date)))
            latest_record_count = 0
            if latest_trade_date is not None:
                latest_record_count = await session.scalar(
                    select(func.count()).select_from(OHLCVBar).where(OHLCVBar.trade_date == latest_trade_date)
                )

        if latest_trade_date is None:
            return ServiceResult(
                status="partial",
                message="no ohlcv data yet",
                payload={
                    "profile_id": runtime_profile_id,
                    "config_path": config_path_value,
                    "base_dir": str(base_dir),
                    "latest_trade_date": None,
                    "latest_record_count": 0,
                    "scheduler_started": scheduler_state["started"],
                    "scheduler_pre_market": scheduler_state["pre_market"],
                    "scheduler_post_close": scheduler_state["post_close"],
                },
            )

        return ServiceResult(
            status="ok",
            message="ohlcv status fetched",
            payload={
                "profile_id": runtime_profile_id,
                "config_path": config_path_value,
                "base_dir": str(base_dir),
                "latest_trade_date": latest_trade_date.isoformat(),
                "latest_record_count": int(latest_record_count or 0),
                "scheduler_started": scheduler_state["started"],
                "scheduler_pre_market": scheduler_state["pre_market"],
                "scheduler_post_close": scheduler_state["post_close"],
            },
        )

    async def run_ohlcv_scheduler(
        self,
        *,
        profile_id: str | None = None,
        config_path: str | Path | None = None,
        start_scheduler: bool = False,
        block: bool = False,
    ) -> ServiceResult:
        """构建 OHLCV 调度计划或启动调度器。"""
        runtime_profile_id = str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None
        if runtime_profile_id is not None:
            loaded_config, base_dir = await self._load_profile_runtime(runtime_profile_id)
            cfg = loaded_config.kaipan
            config_path_value = None
        else:
            resolved_config_path = config_path or Path("config/app.yaml")
            loaded = load_app_config(resolved_config_path)
            cfg = loaded.config.kaipan
            base_dir = _project_base_dir(loaded.config_path)
            config_path_value = str(loaded.config_path)
        pre_market = cfg.fetch_schedule.get("pre_market", "9:25")
        post_close = cfg.fetch_schedule.get("post_close", "17:30")
        scheduler_state = self._scheduler_snapshot()

        if not start_scheduler:
            return ServiceResult(
                status="ok",
                message="ohlcv scheduler plan prepared",
                payload={
                    "profile_id": runtime_profile_id,
                    "config_path": config_path_value,
                    "base_dir": str(base_dir),
                    "pre_market": pre_market,
                    "post_close": post_close,
                    "scheduler_started": scheduler_state["started"],
                },
            )

        if scheduler_state["started"]:
            return ServiceResult(
                status="partial",
                message="ohlcv scheduler already running",
                payload={
                    "profile_id": runtime_profile_id,
                    "config_path": config_path_value,
                    "base_dir": str(base_dir),
                    "pre_market": scheduler_state["pre_market"] or pre_market,
                    "post_close": scheduler_state["post_close"] or post_close,
                    "started": True,
                    "scheduler_started": True,
                },
            )

        def _run_crawl() -> None:
            asyncio.run(self._run_ohlcv_incremental_crawl(config_path=config_path_value or Path("config/app.yaml")))

        scheduler = BackgroundScheduler()
        pre_hour, pre_min = map(int, pre_market.split(":"))
        post_hour, post_min = map(int, post_close.split(":"))
        scheduler.add_job(_run_crawl, CronTrigger(hour=pre_hour, minute=pre_min, second=0), id="pre_market", replace_existing=True)
        scheduler.add_job(_run_crawl, CronTrigger(hour=post_hour, minute=post_min, second=0), id="post_close", replace_existing=True)
        scheduler.start()

        cls = type(self)
        with cls._scheduler_lock:
            cls._scheduler = scheduler
            cls._scheduler_pre_market = pre_market
            cls._scheduler_post_close = post_close
            cls._scheduler_config_path = Path(config_path_value) if config_path_value is not None else None

        if block:
            signal.signal(signal.SIGINT, lambda *_: scheduler.shutdown())
            signal.signal(signal.SIGTERM, lambda *_: scheduler.shutdown())
            scheduler._thread.join()

        return ServiceResult(
                status="ok",
                message="ohlcv scheduler started",
                payload={
                    "profile_id": runtime_profile_id,
                    "config_path": config_path_value,
                    "base_dir": str(base_dir),
                "pre_market": pre_market,
                "post_close": post_close,
                "started": True,
                "scheduler_started": True,
            },
        )

    async def stop_ohlcv_scheduler(self, *, profile_id: str | None = None, config_path: str | Path | None = None) -> ServiceResult:
        """停止当前 OHLCV 调度器。"""
        runtime_profile_id = str(profile_id).strip() if profile_id is not None and str(profile_id).strip() else None
        if runtime_profile_id is not None:
            _loaded_config, base_dir = await self._load_profile_runtime(runtime_profile_id)
            config_path_value = None
        else:
            resolved_config_path = config_path or Path("config/app.yaml")
            loaded = load_app_config(resolved_config_path)
            base_dir = _project_base_dir(loaded.config_path)
            config_path_value = str(loaded.config_path)
        scheduler_state = self._scheduler_snapshot()
        if not scheduler_state["started"]:
            return ServiceResult(
                status="partial",
                message="ohlcv scheduler is not running",
                payload={
                    "profile_id": runtime_profile_id,
                    "config_path": config_path_value,
                    "base_dir": str(base_dir),
                    "started": False,
                    "pre_market": scheduler_state["pre_market"],
                    "post_close": scheduler_state["post_close"],
                },
            )
        self._clear_scheduler()
        return ServiceResult(
            status="ok",
            message="ohlcv scheduler stopped",
            payload={
                "profile_id": runtime_profile_id,
                "config_path": config_path_value,
                "base_dir": str(base_dir),
                "started": False,
                "pre_market": scheduler_state["pre_market"],
                "post_close": scheduler_state["post_close"],
            },
        )
