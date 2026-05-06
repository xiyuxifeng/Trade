"""AkShare 数据 provider 设计说明。

职责：
- 作为公共行情数据的原子适配层，把 AkShare 能力封装为统一的 provider 协议。
- 直接输出标准化的 `ohlcv_1d` 数据，供 `market_data_provider.py`、DataAgent
  或后续 fallback provider 复用。
- 不负责缓存、调度、写盘或任务编排，这些职责保留给 `market_data/service.py`
  和更上层的 pipeline。

后续拓展方式：
- 每新增一种 AkShare 能力，增加一个明确的 capability 分支和对应的 fetch 方法。
- 保持"一个 capability 对应一个输出结构"的原则，避免把 provider 做成大杂烩。
- 如果上层需要更多市场能力，可先在这里补原子适配，再由更上层的 provider
  或服务层组合成业务结构。

设计文档：
- 见 `docs/superpowers/specs/2026-04-23-akshare-provider-design.md`
"""
from __future__ import annotations

import random
import time
from datetime import date
from typing import Any

import pandas as pd

from src.common.akshare_tool import AkshareDailyRequest, AkshareMarketDataTool
from src.common.logger import get_logger
from src.providers.base import ProviderBase, ProviderError

logger = get_logger(__name__)


def _to_date(value: Any) -> date | None:
    """把字符串或日期值统一转换为 `date`。"""

    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _scalar_or_none(value: Any) -> Any:
    """把 DataFrame 单元格值转换为普通 Python 标量。"""

    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return value
    return value


class AkshareProvider(ProviderBase):
    """AkShare 原子 provider。

    作用：
    - 把 AkShare 的行情接口统一包装为 provider 协议
    - 暴露 `fetch_ohlcv_1d()` 供 `MarketDataProvider` 直接复用
    - 为未来扩展更多 AkShare 能力保留清晰边界
    - 内置限速与重试策略，避免触发数据源反爬
    """

    _SUPPORTED_CAPABILITIES = {"ohlcv_1d", "market_data"}

    def __init__(
        self,
        *,
        tool: Any | None = None,
        provider_name: str = "akshare",
        min_request_interval_seconds: float = 1.0,
        max_retries: int = 2,
        retry_backoff_seconds: list[float] | None = None,
        fallback_enabled: bool = True,
    ) -> None:
        super().__init__(provider_name=provider_name)
        self.tool = tool or AkshareMarketDataTool()
        # 限速参数
        self.min_request_interval_seconds = min_request_interval_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds or [1.0, 3.0]
        # fallback 开关：东方财富失败后是否尝试新浪源
        self.fallback_enabled = fallback_enabled
        # 上次请求时间戳，用于限速
        self._last_request_at: float | None = None

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """拉取 AkShare 原始行情数据。"""

        if capability not in self._SUPPORTED_CAPABILITIES:
            self.unsupported(capability)

        symbol = kwargs.get("symbol")
        if not symbol:
            raise ProviderError("symbol is required")

        market_kind = str(kwargs.get("market_kind") or "stock")
        adjust = str(kwargs.get("adjust") or "")
        start_date = _to_date(kwargs.get("start_date"))
        end_date = _to_date(kwargs.get("end_date"))

        frame = self.fetch_ohlcv_1d(
            symbol=symbol,
            market_kind=market_kind,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if frame.empty:
            raise ProviderError(f"AkShare returned empty market data for symbol: {symbol}")

        return {
            "symbol": symbol,
            "market_kind": market_kind,
            "adjust": adjust,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "frame": frame,
            "source": self._infer_source(market_kind=market_kind, symbol=symbol),
        }

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把 AkShare DataFrame 归一成 `ohlcv_1d` bars 列表。"""

        if capability not in self._SUPPORTED_CAPABILITIES:
            self.unsupported(capability)

        frame = raw.get("frame")
        if not isinstance(frame, pd.DataFrame):
            raise ProviderError("AkShare backend must return a pandas DataFrame")
        if frame.empty:
            raise ProviderError("AkShare market data frame is empty")
        if "date" not in frame.columns or "close" not in frame.columns:
            raise ProviderError("AkShare market data frame must contain date and close columns")

        normalized = frame.copy()
        normalized.sort_values("date", inplace=True)

        bars: list[dict[str, Any]] = []
        for _, row in normalized.iterrows():
            close = _scalar_or_none(row.get("close"))
            bars.append(
                {
                    "date": pd.to_datetime(row.get("date")).date().isoformat(),
                    "open": _scalar_or_none(row.get("open", close)),
                    "high": _scalar_or_none(row.get("high", close)),
                    "low": _scalar_or_none(row.get("low", close)),
                    "close": close,
                    "volume": _scalar_or_none(row.get("volume")),
                    "turnover": _scalar_or_none(row.get("turnover")),
                }
            )

        payload = {
            "dataset": "ohlcv_1d",
            "symbol": raw.get("symbol") or (request or {}).get("symbol"),
            "market_kind": raw.get("market_kind") or (request or {}).get("market_kind") or "stock",
            "timeframe": "1d",
            "rows": len(bars),
            "bars": bars,
            "source": raw.get("source") or "akshare",
        }
        return payload

    def fetch_ohlcv_1d(
        self,
        *,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        market_kind: str = "stock",
        adjust: str = "",
    ) -> pd.DataFrame:
        """直接返回标准化后的日线行情 DataFrame（带限速、重试和 fallback）。"""

        req = AkshareDailyRequest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

        # 仅 A 股 stock 类型支持 fallback 到新浪源
        if market_kind == "stock" and self.fallback_enabled:
            return self._fetch_stock_with_fallback(req=req)

        return self._fetch_with_retry(req=req, market_kind=market_kind)

    def _fetch_with_retry(
        self,
        *,
        req: AkshareDailyRequest,
        market_kind: str,
    ) -> pd.DataFrame:
        """带限速和重试的请求逻辑。"""

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                result = self._dispatch_daily_request(req=req, market_kind=market_kind)
                self._last_request_at = time.monotonic()
                return result
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                self._sleep_with_backoff(attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("AkShare 请求失败，且未返回明确错误")

    def _fetch_stock_with_fallback(self, *, req: AkshareDailyRequest) -> pd.DataFrame:
        """A 股日线请求，东方财富失败后自动降级到新浪源。"""

        try:
            return self._fetch_with_retry(req=req, market_kind="stock")
        except Exception as em_exc:
            logger.warning(
                f"东方财富源请求失败 ({req.symbol})，尝试新浪源 fallback: {em_exc}"
            )
            try:
                # fallback 前额外等待，避免连续请求
                self._throttle()
                result = self.tool.fetch_stock_daily_a_sina(req)
                self._last_request_at = time.monotonic()
                logger.info(f"新浪源 fallback 成功: {req.symbol}")
                return result
            except Exception as sina_exc:
                logger.error(f"新浪源 fallback 也失败 ({req.symbol}): {sina_exc}")
                # 抛出原始错误，让上层知道东方财富的失败原因
                raise em_exc from sina_exc

    def _dispatch_daily_request(self, *, req: AkshareDailyRequest, market_kind: str) -> pd.DataFrame:
        """根据 market_kind 调用对应的 AkShare 接口。"""

        if market_kind == "index":
            return self.tool.fetch_index_daily_em(req)
        if market_kind == "industry_board":
            return self.tool.fetch_board_industry_hist_em(req)
        if market_kind == "concept_board":
            return self.tool.fetch_board_concept_hist_em(req)
        if market_kind == "etf" or self._looks_like_etf(req.symbol):
            return self.tool.fetch_etf_daily_em(req)
        return self.tool.fetch_stock_daily_a(req)

    def _throttle(self) -> None:
        """控制请求节奏，避免短时间内连续打爆接口。"""
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _sleep_with_backoff(self, attempt: int) -> None:
        """按退避时间重试，附加少量抖动。"""
        base = self.retry_backoff_seconds[min(attempt, len(self.retry_backoff_seconds) - 1)]
        jitter = random.uniform(0, 0.3)
        time.sleep(base + jitter)

    def _infer_source(self, *, market_kind: str, symbol: str) -> str:
        """推导标准化数据来源标签。"""

        if market_kind == "index":
            return "akshare.index"
        if market_kind == "industry_board":
            return "akshare.board.industry"
        if market_kind == "concept_board":
            return "akshare.board.concept"
        if market_kind == "etf" or self._looks_like_etf(symbol):
            return "akshare.etf"
        return "akshare.stock"

    def _looks_like_etf(self, symbol: str) -> bool:
        """按代码前缀判断常见 ETF 标的。"""

        return symbol.startswith(("51", "52", "56", "58", "15"))
