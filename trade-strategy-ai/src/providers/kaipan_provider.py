"""Kaipan 私有接口 provider。

职责：
- 组装 Kaipan 私有接口请求参数。
- 保留现有 raw fetch 方法，供调度器和补抓脚本直接复用。
- 对外提供标准化 capability：
  - `hot_topics`
  - `topic_constituents`
  - `strong_symbols`

扩展方式：
- 新增能力时，优先增加一个 capability 分支和对应的 normalize 逻辑。
- 原始抓取方法可以继续保留，用于 CLI、scheduler 和调试场景。
- 如果后续要扩展到 `market_context` 或 `postmarket_evidence`，沿用“原始抓取 + 标准化输出”的模式即可。

设计文档：
- 见 `docs/superpowers/specs/2026-04-23-kaipan-provider-design.md`
"""

from __future__ import annotations

import json
import random
import time
import requests
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from common.config import KaipanConfig
except ImportError:  # pragma: no cover - 兼容不同 PYTHONPATH 启动方式
    from src.common.config import KaipanConfig

import pandas as pd

from src.providers.base import ProviderBase, ProviderError, ProviderStatus


@dataclass(frozen=True)
class KaipanAuth:
    """开盘啦私有接口鉴权参数。"""

    device_id: str = field(default_factory=lambda: str(uuid4()))
    phone_os_new: str = "1"
    version: str = "5.23.0.1"
    apiv: str = "w44"
    token: str | None = None
    user_id: str | None = None


@dataclass(frozen=True)
class KaipanRequest:
    """单次接口请求的规范化描述。"""

    endpoint: str
    method: str
    controller: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KaipanSnapshotMeta:
    """抓取快照元信息。

    该结构用于 raw/normalized/snapshot 三层存储时写入元数据。
    """

    dataset: str
    trade_date: date | None
    fetched_at: datetime
    request: KaipanRequest
    page_key: str | None = None
    source: str = "kaipan"


class KaipanProvider(ProviderBase):
    """开盘啦数据提供者。

    现阶段负责把 Kaipan 私有接口包装成可调用 provider，
    同时保留原始抓取方法，方便 scheduler 和调试脚本复用。
    """

    def __init__(
        self,
        *,
        auth: KaipanAuth,
        raw_dir: str | Path,
        normalized_dir: str | Path,
        snapshots_dir: str | Path,
        kaipan_config: KaipanConfig | dict[str, Any] | None = None,
        provider_name: str = "kaipan",
    ) -> None:
        super().__init__(provider_name=provider_name)
        self.auth = auth
        self.raw_dir = Path(raw_dir)
        self.normalized_dir = Path(normalized_dir)
        self.snapshots_dir = Path(snapshots_dir)
        self.session = requests.Session()
        self.kaipan_config = kaipan_config
        self.default_headers = dict(self._config_value("default_headers", {}))
        if not self.default_headers:
            self.default_headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
            }
        self.session.headers.update(self.default_headers)
        self.base_urls = {
            "apphis": "https://apphis.longhuvip.com/w1/api/index.php",
            "apphwhq": "https://apphwhq.longhuvip.com/w1/api/index.php",
            "apphwshhq": "https://apphwshhq.longhuvip.com/w1/api/index.php",
            "applhb": "https://applhb.longhuvip.com/w1/api/index.php",
        }
        self.min_request_interval_seconds = float(self._config_value("min_request_interval_seconds", 0.8))
        self.max_retries = int(self._config_value("max_retries", 3))
        self.retry_backoff_seconds = tuple(self._config_value("retry_backoff_seconds", [1.0, 2.0, 4.0]))
        self.retry_status_codes = set(int(code) for code in self._config_value("retry_status_codes", [403, 429, 500, 502, 503, 504]))
        self._last_request_at: float | None = None
        self._trade_date: date | None = None
        self._slot: str | None = None

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """拉取 capability 对应的 raw 数据。"""

        if capability == "hot_topics":
            return self._request_hot_topics(**kwargs)
        if capability == "topic_constituents":
            return self._request_topic_constituents(**kwargs)
        if capability == "strong_symbols":
            return self._request_strong_symbols(**kwargs)
        if capability == "market_sentiment":
            return self._request_market_sentiment(**kwargs)
        if capability == "market_index":
            return self._request_market_index(**kwargs)
        if capability == "sharp_withdrawal":
            return self._request_sharp_withdrawal(**kwargs)
        if capability == "sector_ranking":
            return self._request_sector_ranking(**kwargs)
        if capability == "sector_limit_up_ladder":
            return self._request_sector_limit_up_ladder(**kwargs)
        if capability == "market_limit_up_ladder":
            return self._request_market_limit_up_ladder(**kwargs)
        if capability == "sector_strength":
            return self._request_sector_strength(**kwargs)
        if capability == "multiple_sectors_strength":
            return self._request_multiple_sectors_strength(**kwargs)
        if capability == "market_stock_zd_num":
            return self._request_market_stock_zd_num(**kwargs)
        if capability == "zhang_ting_expression":
            return self._request_zhang_ting_expression(**kwargs)
        if capability == "daily_limit_index":
            return self._request_daily_limit_index(**kwargs)
        if capability == "weight_performance":
            return self._request_weight_performance(**kwargs)
        if capability == "get_feng_k_list":
            return self._request_get_feng_k_list(**kwargs)
        self.unsupported(capability)

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """把 raw 响应转换为标准 provider payload。"""

        if capability == "hot_topics":
            return self._normalize_hot_topics(raw=raw, request=request)
        if capability == "topic_constituents":
            return self._normalize_topic_constituents(raw=raw, request=request)
        if capability == "strong_symbols":
            return self._normalize_strong_symbols(raw=raw, request=request)
        if capability == "market_sentiment":
            return self._normalize_market_sentiment(raw=raw, request=request)
        if capability == "market_index":
            return self._normalize_market_index(raw=raw, request=request)
        if capability == "sharp_withdrawal":
            return self._normalize_sharp_withdrawal(raw=raw, request=request)
        if capability == "sector_ranking":
            return self._normalize_sector_ranking(raw=raw, request=request)
        if capability == "sector_limit_up_ladder":
            return self._normalize_sector_limit_up_ladder(raw=raw, request=request)
        if capability == "market_limit_up_ladder":
            return self._normalize_market_limit_up_ladder(raw=raw, request=request)
        if capability == "sector_strength":
            return self._normalize_sector_strength(raw=raw, request=request)
        if capability == "multiple_sectors_strength":
            return self._normalize_multiple_sectors_strength(raw=raw, request=request)
        if capability == "market_stock_zd_num":
            return self._normalize_market_stock_zd_num(raw=raw, request=request)
        if capability == "zhang_ting_expression":
            return self._normalize_zhang_ting_expression(raw=raw, request=request)
        if capability == "daily_limit_index":
            return self._normalize_daily_limit_index(raw=raw, request=request)
        if capability == "weight_performance":
            return self._normalize_weight_performance(raw=raw, request=request)
        if capability == "get_feng_k_list":
            return self._normalize_get_feng_k_list(raw=raw, request=request)
        self.unsupported(capability)

    def fetch_hot_topics(self, *, trade_date: date | str, slot: str = "09-25", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回标准化热点结构。

        offline=True 时跳过 HTTP 请求，直接从 data/kaipan/raw/ 加载已有 raw 数据。
        """

        if offline:
            raw = self._load_hot_topics_raw(trade_date=trade_date, slot=slot)
            return self._normalize_hot_topics(raw=raw, request={"trade_date": trade_date, "slot": slot})

        result = self.run("hot_topics", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch hot_topics")
        return result.payload

    def fetch_topic_constituents(
        self,
        *,
        trade_date: date | str,
        slot: str = "17-30",
        offline: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """获取并返回标准化题材成分结构。

        offline=True 时跳过 HTTP 请求，直接从 data/kaipan/raw/ 加载已有 raw 数据。
        """

        if offline:
            raw = self._load_topic_constituents_raw(trade_date=trade_date, slot=slot)
            return self._normalize_topic_constituents(raw=raw, request={"trade_date": trade_date, "slot": slot})

        result = self.run("topic_constituents", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch topic_constituents")
        return result.payload

    def fetch_strong_symbols(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回标准化强势标的结构。

        offline=True 时跳过 HTTP 请求，直接从 data/kaipan/raw/ 加载已有 raw 数据。
        """

        if offline:
            raw = self._load_strong_symbols_raw(trade_date=trade_date, slot=slot)
            return self._normalize_strong_symbols(raw=raw, request={"trade_date": trade_date, "slot": slot})

        result = self.run("strong_symbols", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch strong_symbols")
        return result.payload

    def fetch_market_sentiment(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回市场情绪数据。"""

        if offline:
            raw = self._load_canonical_raw("market_sentiment", trade_date=trade_date, slot=slot)
            return self._normalize_market_sentiment(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("market_sentiment", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch market_sentiment")
        return result.payload

    def fetch_market_index(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回指数概览数据。"""

        if offline:
            raw = self._load_canonical_raw("market_index", trade_date=trade_date, slot=slot)
            return self._normalize_market_index(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("market_index", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch market_index")
        return result.payload

    def fetch_sharp_withdrawal(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回大幅回撤数据。"""

        if offline:
            raw = self._load_canonical_raw("sharp_withdrawal", trade_date=trade_date, slot=slot)
            return self._normalize_sharp_withdrawal(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("sharp_withdrawal", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch sharp_withdrawal")
        return result.payload

    def fetch_sector_ranking(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回板块排行数据。"""

        if offline:
            raw = self._load_canonical_raw("sector_ranking", trade_date=trade_date, slot=slot)
            return self._normalize_sector_ranking(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("sector_ranking", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch sector_ranking")
        return result.payload

    def fetch_sector_limit_up_ladder(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回板块连板梯队。"""

        if offline:
            raw = self._load_canonical_raw("sector_limit_up_ladder", trade_date=trade_date, slot=slot)
            return self._normalize_sector_limit_up_ladder(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("sector_limit_up_ladder", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch sector_limit_up_ladder")
        return result.payload

    def fetch_market_limit_up_ladder(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回全市场连板梯队。"""

        if offline:
            raw = self._load_canonical_raw("market_limit_up_ladder", trade_date=trade_date, slot=slot)
            return self._normalize_market_limit_up_ladder(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("market_limit_up_ladder", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch market_limit_up_ladder")
        return result.payload

    def fetch_sector_strength(self, *, trade_date: date | str, slot: str = "17-30", sector_code: str, offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """获取并返回单个板块强度。"""

        if offline:
            raw = self._load_canonical_raw("sector_strength", trade_date=trade_date, slot=slot)
            request = {"trade_date": trade_date, "slot": slot, "sector_code": sector_code}
            return self._normalize_sector_strength(raw=raw, request=request)
        request = {"trade_date": trade_date, "slot": slot, "sector_code": sector_code, **kwargs}
        result = self.run("sector_strength", request=request)
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch sector_strength")
        return result.payload

    def fetch_multiple_sectors_strength(self, *, trade_date: date | str, slot: str = "17-30", sector_codes: list[str], offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """批量获取多个板块强度。"""

        if offline:
            raw = self._load_canonical_raw("multiple_sectors_strength", trade_date=trade_date, slot=slot)
            request = {"trade_date": trade_date, "slot": slot, "sector_codes": sector_codes}
            return self._normalize_multiple_sectors_strength(raw=raw, request=request)
        request = {"trade_date": trade_date, "slot": slot, "sector_codes": sector_codes, **kwargs}
        result = self.run("multiple_sectors_strength", request=request)
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch multiple_sectors_strength")
        return result.payload

    def _config_value(self, key: str, default: Any) -> Any:
        """从 kaipan 配置中读取值，兼容 Pydantic 模型和普通字典。"""
        if self.kaipan_config is None:
            return default
        if isinstance(self.kaipan_config, dict):
            return self.kaipan_config.get(key, default)
        return getattr(self.kaipan_config, key, default)

    def _resolve_history_or_today_url(self, *, trade_date: date | None = None, use_today_url: bool | None = None) -> str:
        """按接口文档选择历史或今日数据域名。

        默认根据 `trade_date` 是否等于今天自动判断；`use_today_url`
        作为显式覆盖开关保留，便于特殊场景手工指定。
        """
        if use_today_url is not None:
            return "apphwhq" if use_today_url else "apphis"
        if trade_date is not None and trade_date == date.today():
            return "apphwhq"
        return "apphis"

    def build_common_params(self) -> dict[str, Any]:
        """构造私有接口公共参数。"""
        params: dict[str, Any] = {
            "DeviceID": self.auth.device_id,
            "PhoneOSNew": self.auth.phone_os_new,
            "VerSion": self.auth.version,
            "apiv": self.auth.apiv,
        }
        token = self._config_value("token", self.auth.token)
        user_id = self._config_value("user_id", self.auth.user_id)
        if token:
            params["Token"] = token
        if user_id:
            params["UserID"] = str(user_id)
        return params

    def build_request(
        self,
        *,
        api_name: str,
        controller: str,
        base_url_key: str = "apphis",
        method: str = "GET",
        **params: Any,
    ) -> KaipanRequest:
        """生成规范化请求对象。"""
        merged = self.build_common_params()
        merged.update(params)
        merged["a"] = api_name
        merged["c"] = controller
        return KaipanRequest(
            endpoint=self.base_urls[base_url_key],
            method=method,
            controller=controller,
            action=api_name,
            params=merged,
        )

    def _fetch_single(self, request: KaipanRequest) -> dict[str, Any]:
        """发起单次 HTTP 请求，返回解析后的 JSON 响应。"""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.request(
                    method=request.method,
                    url=request.endpoint,
                    params=request.params if request.method != "POST" else None,
                    data=request.params if request.method == "POST" else None,
                    timeout=30,
                    headers=self.default_headers,
                )
                self._last_request_at = time.monotonic()
                if resp.status_code in self.retry_status_codes and attempt < self.max_retries:
                    self._sleep_with_backoff(attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                self._sleep_with_backoff(attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Kaipan 请求失败，且未返回明确错误")

    def _throttle(self) -> None:
        """控制请求节奏，避免短时间内连续打爆接口。"""
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _sleep_with_backoff(self, attempt: int) -> None:
        """按固定退避时间重试，附加少量抖动。"""
        base = self.retry_backoff_seconds[min(attempt, len(self.retry_backoff_seconds) - 1)]
        jitter = random.uniform(0, 0.3)
        time.sleep(base + jitter)

    def _read_raw_files(self, dataset: str, subdir: str, prefix: str, *, required: bool = True) -> dict[str, Any]:
        """从本地 raw 目录读取匹配前缀的所有 API 响应文件，合并分页后返回 data 部分。

        离线模式下：扫描 {raw_dir}/{dataset}/{subdir}/{prefix}*.json，
        将多页数据的 list 数组合并，输出与单次请求相同的结构。

        required=False 时，文件不存在返回空 dict 而不抛异常（用于可选数据源）。
        """
        dir_path = self.raw_dir / dataset / subdir
        if not dir_path.exists():
            if not required:
                return {}
            raise ProviderError(f"离线模式: raw 目录不存在 {dir_path}")

        matches = sorted(dir_path.glob(f"{prefix}*.json"))
        if not matches:
            if not required:
                return {}
            raise ProviderError(f"离线模式: raw 文件不存在 {dir_path}/{prefix}*.json")

        merged: dict[str, Any] = {}
        total_list: list[Any] = []

        for path in matches:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            data = raw.get("data", {})
            # 第一个文件提供基础结构
            if not merged:
                merged = {k: v for k, v in data.items() if k != "list"}
            # 合并 list 数组
            page_list = data.get("list", [])
            if isinstance(page_list, list):
                total_list.extend(page_list)

        merged["list"] = total_list
        merged["Count"] = len(total_list)
        return merged

    def _save_raw(self, raw_path: Path, request: KaipanRequest, response_data: Any, dataset: str) -> None:
        """将 raw JSON 保存到文件，顶部嵌入 meta 元信息。

        Args:
            raw_path: 原始文件存储路径
            request: 请求对象
            response_data: 响应数据
            dataset: 标准 dataset 名称（从设计文档规定，不是方法名）
        """
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "dataset": dataset,
                "trade_date": self._trade_date.isoformat() if self._trade_date else None,
                "slot": self._slot,
                "fetched_at": datetime.now().isoformat(),
                "source": "kaipan",
                "request": {
                    "endpoint": request.endpoint,
                    "controller": request.controller,
                    "action": request.action,
                    "params": request.params,
                },
            },
            "data": response_data,
        }
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _fetch_and_save(
        self,
        *,
        dataset: str,
        api_name: str,
        controller: str,
        base_url_key: str = "apphis",
        method: str = "GET",
        page_key: str | None = None,
        canonical_name: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """通用抓取保存方法。

        统一处理请求构造、HTTP抓取和原始文件存储。

        Args:
            dataset: 标准 dataset 名称（必须与设计文档一致）
            api_name: API 接口名
            controller: 控制器名
            base_url_key: Base URL key（默认 apphis）
            method: HTTP 方法（默认 GET）
            page_key: 分页文件名后缀，用于区分页数据
            **params: 传递给 build_request 的额外参数

        Returns:
            API 响应原始数据
        """
        params = {key: value for key, value in params.items() if value is not None}
        request = self.build_request(
            api_name=api_name,
            controller=controller,
            base_url_key=base_url_key,
            method=method,
            **params,
        )
        # 根据 api_name 和关键参数区分文件名，避免同 dataset 下数据互相覆盖
        filename_parts = [dataset, api_name]
        if api_name == "RealRankingInfo":
            filename_parts.append(f"ZSType{params.get('ZSType', '')}")
        elif api_name == "GetInterviewsByDateStock":
            filename_parts.append(f"Type{params.get('Type', '')}")
        elif api_name == "MorningBiddingList":
            filename_parts.append(f"PidType{params.get('PidType', '')}")
        elif api_name == "GetPlateInfo_w38":
            filename_parts.append(f"Index{params.get('Index', '')}")
        elif api_name == "GetZhangTingTianTi":
            filename_parts.append(f"Index{params.get('Index', '')}")
        elif api_name == "GetFengKListBest":
            filename_parts.append(f"Time{params.get('Time', '')}")
        elif api_name == "GetFengKList":
            filename_parts.append(f"Time{params.get('Time', '')}")
        elif api_name == "GetInterviewsByDateZS":
            filename_parts.append(f"Type{params.get('Type', '')}")
        if page_key:
            filename_parts.append(page_key)
        raw_filename = "_".join(filter(None, filename_parts))
        raw_path = self.raw_dir / dataset / f"{self._trade_date.isoformat()}_{self._slot}" / f"{raw_filename}.json"
        response = self._fetch_single(request)
        self._save_raw(raw_path, request, response, dataset)
        if canonical_name:
            canonical_path = self.raw_dir / dataset / f"{self._trade_date.isoformat()}_{self._slot}" / f"{canonical_name}.json"
            if canonical_path != raw_path:
                self._save_raw(canonical_path, request, response, dataset)
        return response

    def fetch_custom(
        self,
        *,
        trade_date: date,
        slot: str,
        dataset: str,
        api_name: str,
        controller: str,
        base_url_key: str = "apphis",
        method: str = "GET",
        page_key: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """通用抓取入口，供脚本或特殊验证任务直接调用。

        适合批量验证、分页回放或临时补抓，不影响现有显式封装方法。
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset=dataset,
            api_name=api_name,
            controller=controller,
            base_url_key=base_url_key,
            method=method,
            page_key=page_key,
            **params,
        )

    def dataset_raw_path(self, *, trade_date: date, dataset: str, page_key: str | None = None) -> Path:
        """返回原始 JSON 存储路径。"""
        suffix = f"_{page_key}" if page_key else ""
        return self.raw_dir / trade_date.isoformat() / f"{dataset}{suffix}.json"

    def dataset_normalized_path(self, *, trade_date: date, dataset: str) -> Path:
        """返回标准化 JSON 存储路径。"""
        return self.normalized_dir / trade_date.isoformat() / f"{dataset}.json"

    def dataset_snapshot_path(self, *, trade_date: date, dataset: str) -> Path:
        """返回快照 JSON 存储路径。"""
        return self.snapshots_dir / trade_date.isoformat() / f"{dataset}.json"

    # -----------------------------
    # capability 级别的请求与归一化逻辑
    # -----------------------------

    def _coerce_trade_date(self, value: Any) -> date:
        """把字符串或日期值统一转换为 `date`。"""

        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ProviderError("trade_date is required and must be a date or ISO string")
        return parsed.date()

    # -----------------------------
    # 离线模式：从本地 raw 文件加载数据（跳过 HTTP 请求）
    # -----------------------------

    def _load_hot_topics_raw(self, *, trade_date: date | str, slot: str) -> dict[str, Any]:
        """从本地 raw 文件加载热点主题原始数据（与 _request_hot_topics 返回结构一致）。

        自动合并分页：按文件前缀匹配所有分页文件，合并 list 数组。
        """
        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        date_str = td.isoformat()
        subdir = f"{date_str}_{slot}"
        return {
            "trade_date": date_str,
            "slot": slot,
            "board_strength": self._read_raw_files("hot_topics", subdir, "hot_topics_RealRankingInfo_ZSType7"),
            "industry": self._read_raw_files("hot_topics", subdir, "hot_topics_RealRankingInfo_ZSType4"),
            "concept_fengkou": self._read_raw_files("hot_topics", subdir, "hot_topics_GetFengKYDPlate"),
        }

    def _load_topic_constituents_raw(
        self,
        *,
        trade_date: date | str,
        slot: str,
        stock_id: str | None = None,
        topic_ids: list[str] | None = None,
        theme_id: str | None = None,
    ) -> dict[str, Any]:
        """从本地 raw 文件加载题材成分原始数据（与 _request_topic_constituents 返回结构一致）。"""
        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        date_str = td.isoformat()
        subdir = f"{date_str}_{slot}"

        raw: dict[str, Any] = {
            "trade_date": date_str,
            "slot": slot,
            "limit_up_reason": self._read_raw_files("topic_constituents", subdir, "topic_constituents_GetPlateInfo_w38"),
            "limit_up_info": self._read_raw_files("topic_constituents", subdir, "topic_constituents_GetZhangTingTianTi"),
            "lhb_list": self._read_raw_files("topic_constituents", subdir, "topic_constituents_GetStockList", required=False),
        }

        if stock_id:
            raw["stock_sector_v2"] = self._read_raw_files("topic_constituents", subdir, "topic_constituents_GetFeaturedSection")

        requested_topic_ids = list(topic_ids or [])
        if theme_id:
            requested_topic_ids.append(theme_id)
        if requested_topic_ids:
            theme_details = []
            for _tid in requested_topic_ids:
                try:
                    theme_details.append(self._read_raw_files("topic_constituents", subdir, "topic_constituents_InfoGet"))
                except ProviderError:
                    pass  # 可选文件，缺失时跳过
            raw["theme_detail"] = theme_details
        else:
            raw["theme_detail"] = []

        return raw

    def _load_strong_symbols_raw(
        self,
        *,
        trade_date: date | str,
        slot: str,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        universe: list[str] | None = None,
    ) -> dict[str, Any]:
        """从本地 raw 文件加载强势标的原始数据（与 _request_strong_symbols 返回结构一致）。"""
        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        date_str = td.isoformat()
        subdir = f"{date_str}_{slot}"

        raw: dict[str, Any] = {
            "trade_date": date_str,
            "slot": slot,
            "strong_fengkou": self._read_raw_files("strong_symbols", subdir, "strong_symbols_GetFengKListBest"),
            "interval_stats_stock": self._read_raw_files("strong_symbols", subdir, "strong_symbols_GetInterviewsByDateStock_Type2"),
            "universe": universe or [],
        }

        if slot == "09-25":
            raw["morning_bidding_list"] = self._read_raw_files("strong_symbols", subdir, "strong_symbols_MorningBiddingList_PidType0")
        else:
            raw["morning_bidding_list"] = {"info": []}

        return raw

    def _load_canonical_raw(self, dataset: str, *, trade_date: date | str, slot: str) -> dict[str, Any]:
        """从 canonical raw 文件加载单接口数据。"""
        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        path = self.raw_dir / dataset / f"{td.isoformat()}_{slot}" / f"{dataset}.json"
        if not path.exists():
            raise ProviderError(f"离线模式: canonical raw 文件不存在 {path}")
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {"value": data}

    def _normalize_market_sentiment(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化市场情绪数据。"""

        info = raw.get("info") if isinstance(raw, dict) else {}
        info = info if isinstance(info, dict) else {}
        up_count = int(info.get("SZJS", 0) or 0)
        down_count = int(info.get("XDJS", 0) or 0)
        flat_count = int(info.get("0", 0) or 0)
        total = up_count + down_count + flat_count
        payload = {
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "summary": {
                "limit_up_count": int(info.get("ZT", 0) or 0),
                "actual_limit_up": int(info.get("SJZT", 0) or 0),
                "limit_down_count": int(info.get("DT", 0) or 0),
                "actual_limit_down": int(info.get("SJDT", 0) or 0),
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "up_ratio": round(up_count / total, 4) if total else None,
                "down_ratio": round(down_count / total, 4) if total else None,
            },
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_market_index(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化指数概览数据。"""

        items = raw.get("StockList") if isinstance(raw, dict) else []
        normalized: list[dict[str, Any]] = []
        if isinstance(items, list):
            for row in items:
                if not isinstance(row, dict):
                    continue
                normalized.append(
                    {
                        "symbol": row.get("StockID"),
                        "name": row.get("prod_name"),
                        "latest_price": row.get("last_px"),
                        "change_pct": row.get("increase_rate"),
                        "turnover": row.get("turnover"),
                        "change_amount": row.get("increase_amount"),
                    }
                )
        payload = {
            "date": raw.get("Date") if isinstance(raw, dict) else None,
            "items": normalized,
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_sharp_withdrawal(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化大幅回撤数据。"""

        items = raw.get("info") if isinstance(raw, dict) else []
        normalized: list[dict[str, Any]] = []
        if isinstance(items, list):
            for row in items:
                if not isinstance(row, list) or len(row) < 5:
                    continue
                normalized.append(
                    {
                        "symbol": row[0],
                        "name": row[1],
                        "change_pct": row[2],
                        "withdrawal_pct": row[3],
                        "latest_price": row[4],
                    }
                )
        payload = {
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "count": raw.get("num", len(normalized)) if isinstance(raw, dict) else len(normalized),
            "items": normalized,
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_sector_ranking(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化板块排行数据。"""

        nums = raw.get("nums", {}) if isinstance(raw, dict) else {}
        sectors_raw = raw.get("list", []) if isinstance(raw, dict) else []
        sectors: list[dict[str, Any]] = []
        if isinstance(sectors_raw, list):
            for sector_data in sectors_raw:
                if not isinstance(sector_data, dict):
                    continue
                stocks: list[dict[str, Any]] = []
                for stock in sector_data.get("StockList", []) if isinstance(sector_data.get("StockList"), list) else []:
                    if not isinstance(stock, list) or len(stock) < 19:
                        continue
                    stocks.append(
                        {
                            "symbol": stock[0],
                            "name": stock[1],
                            "limit_up_price": stock[4] if len(stock) > 4 else None,
                            "circulating_market_cap": stock[8] if len(stock) > 8 else None,
                            "consecutive_days": stock[9] if len(stock) > 9 else None,
                            "consecutive_count": stock[10] if len(stock) > 10 else None,
                            "concept_tags": stock[11] if len(stock) > 11 else None,
                            "seal_amount": stock[12] if len(stock) > 12 else None,
                            "main_force_net": stock[13] if len(stock) > 13 else None,
                            "first_seal_time": stock[14] if len(stock) > 14 else None,
                            "total_market_cap": stock[15] if len(stock) > 15 else None,
                            "limit_reason": stock[16] if len(stock) > 16 else None,
                            "theme": stock[17] if len(stock) > 17 else None,
                            "is_first_board": stock[18] if len(stock) > 18 else None,
                        }
                    )
                sectors.append(
                    {
                        "sector_code": sector_data.get("ZSCode"),
                        "sector_name": sector_data.get("ZSName"),
                        "stock_count": sector_data.get("num", len(stocks)),
                        "stocks": stocks,
                    }
                )
        payload = {
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "summary": {
                "up_count": nums.get("SZJS", 0),
                "down_count": nums.get("XDJS", 0),
                "limit_up_count": nums.get("ZT", 0),
                "limit_down_count": nums.get("DT", 0),
                "rise_ratio": nums.get("ZBL", 0),
                "yesterday_rise_ratio": nums.get("yestRase", 0),
            },
            "sectors": sectors,
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_sector_limit_up_ladder(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化板块连板梯队。"""

        payload = {
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "is_realtime": raw.get("is_realtime") if isinstance(raw, dict) else None,
            "sectors": raw.get("sectors") if isinstance(raw, dict) and isinstance(raw.get("sectors"), list) else [],
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_market_limit_up_ladder(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化全市场连板梯队。"""

        payload = {
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "is_realtime": raw.get("is_realtime") if isinstance(raw, dict) else None,
            "statistics": raw.get("statistics") if isinstance(raw, dict) and isinstance(raw.get("statistics"), dict) else {},
            "ladder": raw.get("ladder") if isinstance(raw, dict) and isinstance(raw.get("ladder"), dict) else {},
            "broken_stocks": raw.get("broken_stocks") if isinstance(raw, dict) and isinstance(raw.get("broken_stocks"), list) else [],
            "height_marks": raw.get("height_marks") if isinstance(raw, dict) and isinstance(raw.get("height_marks"), list) else [],
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_sector_strength(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化单个板块强度。"""

        payload = {
            "sector_code": raw.get("sector_code") if isinstance(raw, dict) else None,
            "strength": raw.get("strength") if isinstance(raw, dict) else None,
            "date": raw.get("date") if isinstance(raw, dict) else None,
            "time": raw.get("time") if isinstance(raw, dict) else None,
            "raw_data": raw.get("raw_data") if isinstance(raw, dict) else None,
            "success": raw.get("success") if isinstance(raw, dict) else False,
            "error": raw.get("error") if isinstance(raw, dict) else None,
            "is_historical": raw.get("is_historical") if isinstance(raw, dict) else None,
            "min_day": raw.get("min_day") if isinstance(raw, dict) else None,
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    def _normalize_multiple_sectors_strength(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """标准化多个板块强度。"""

        payload = {
            "results": raw if isinstance(raw, dict) else {},
            "raw": raw,
        }
        if request is not None:
            payload["request"] = request
        return payload

    # -----------------------------
    # capability 级别的请求与归一化逻辑
    # -----------------------------

    def _request_hot_topics(self, *, trade_date: Any, slot: str = "09-25", **kwargs: Any) -> dict[str, Any]:
        """拉取热点主题所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return {
            "trade_date": td.isoformat(),
            "slot": slot,
            "board_strength": self.fetch_board_strength(trade_date=td, slot=slot, use_today_url=kwargs.get("use_today_url")),
            "industry": self.fetch_industry_ranking(trade_date=td, slot=slot, use_today_url=kwargs.get("use_today_url")),
            "concept_fengkou": self.fetch_concept_fengkou(trade_date=td, slot=slot),
        }

    def _request_topic_constituents(
        self,
        *,
        trade_date: Any,
        slot: str = "17-30",
        stock_id: str | None = None,
        topic_ids: list[str] | None = None,
        theme_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """拉取题材成分所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot

        raw: dict[str, Any] = {
            "trade_date": td.isoformat(),
            "slot": slot,
            "limit_up_reason": self.fetch_limit_up_reason(trade_date=td, slot=slot),
            "limit_up_info": self.fetch_limit_up_info(trade_date=td, slot=slot),
            "lhb_list": self.fetch_lhb_list(trade_date=td, slot=slot),
        }

        if stock_id:
            raw["stock_sector_v2"] = self.fetch_stock_sector_v2(trade_date=td, slot=slot, stock_id=stock_id)

        requested_topic_ids = list(topic_ids or [])
        if theme_id:
            requested_topic_ids.append(theme_id)
        if requested_topic_ids:
            raw["theme_detail"] = [
                self.fetch_theme_detail(trade_date=td, slot=slot, theme_id=topic)
                for topic in requested_topic_ids
            ]
        else:
            raw["theme_detail"] = []
        return raw

    def _request_strong_symbols(
        self,
        *,
        trade_date: Any,
        slot: str = "17-30",
        start_date: Any | None = None,
        end_date: Any | None = None,
        universe: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """拉取强势标的所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        sd = self._coerce_trade_date(start_date or td)
        ed = self._coerce_trade_date(end_date or td)

        raw: dict[str, Any] = {
            "trade_date": td.isoformat(),
            "slot": slot,
            "strong_fengkou": self.fetch_strong_fengkou(trade_date=td, slot=slot, use_today_url=kwargs.get("use_today_url")),
            "interval_stats_stock": self.fetch_interval_stats_stock(
                trade_date=td,
                slot=slot,
                start_date=sd,
                end_date=ed,
                use_today_url=kwargs.get("use_today_url"),
            ),
            "universe": universe or [],
        }
        if slot == "09-25":
            raw["morning_bidding_list"] = self.fetch_morning_bidding_list(trade_date=td, slot=slot)
        else:
            raw["morning_bidding_list"] = {"info": []}
        return raw

    def _request_market_sentiment(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取市场情绪所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_sentiment",
            api_name="HisZhangFuDetail",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
            Day=td.strftime("%Y-%m-%d"),
        )

    def _request_market_index(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取指数概览所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_index",
            api_name="GetZsReal",
            controller="StockL2History",
            base_url_key="apphis",
            method="POST",
            Day=td.strftime("%Y-%m-%d"),
        )

    def _request_sharp_withdrawal(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取大幅回撤所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="sharp_withdrawal",
            api_name="SharpWithdrawal",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
            Day=td.strftime("%Y-%m-%d"),
        )

    def _request_sector_ranking(self, *, trade_date: Any, slot: str = "17-30", index: int = 0, st: int = 100, **kwargs: Any) -> dict[str, Any]:
        """拉取板块排行所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="sector_ranking",
            api_name="GetPlateInfo_w38",
            controller="DailyLimitResumption",
            base_url_key="apphis",
            method="POST",
            Day=td.strftime("%Y-%m-%d"),
            Index=index,
            st=st,
        )

    def _request_sector_limit_up_ladder(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取板块连板梯队所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="sector_limit_up_ladder",
            api_name="GetYTFP_BKHX",
            controller="FuPanLa",
            base_url_key=self._resolve_history_or_today_url(trade_date=td, use_today_url=kwargs.get("use_today_url")),
            method="POST",
            Date=td.strftime("%Y-%m-%d") if td != date.today() else None,
            apiv="w42",
        )

    def _request_market_limit_up_ladder(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取全市场连板梯队所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_limit_up_ladder",
            api_name="GetYTFP_SCTD",
            controller="FuPanLa",
            base_url_key=self._resolve_history_or_today_url(trade_date=td, use_today_url=kwargs.get("use_today_url")),
            method="POST",
            Date=td.strftime("%Y-%m-%d") if td != date.today() else None,
            apiv="w42",
        )

    def _request_sector_strength(self, *, trade_date: Any, slot: str = "17-30", sector_code: str, **kwargs: Any) -> dict[str, Any]:
        """拉取单个板块强度所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="sector_strength",
            api_name="GetPlate_Info_QJ",
            controller="ZhiShuRanking",
            base_url_key="apphwhq" if td == date.today() else "apphis",
            method="POST",
            Date=td.strftime("%Y-%m-%d"),
            PlateID=sector_code,
        )

    def _request_multiple_sectors_strength(self, *, trade_date: Any, slot: str = "17-30", sector_codes: list[str], **kwargs: Any) -> dict[str, Any]:
        """拉取多个板块强度所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        results: dict[str, Any] = {}
        for sector_code in sector_codes:
            results[sector_code] = self._request_sector_strength(trade_date=td, slot=slot, sector_code=sector_code, **kwargs)
        return {
            "trade_date": td.isoformat(),
            "slot": slot,
            "sector_codes": sector_codes,
            "results": results,
        }

    def _request_market_stock_zd_num(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取涨跌停统计所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_stock_zd_num",
            api_name="MarketStockZDNum",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="POST",
            canonical_name="market_stock_zd_num",
            Date=td.strftime("%Y-%m-%d"),
        )

    def _request_zhang_ting_expression(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取涨停表达式所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="zhang_ting_expression",
            api_name="ZhangTingExpression",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="GET",
            canonical_name="zhang_ting_expression",
            Day=td.strftime("%Y-%m-%d"),
        )

    def _request_daily_limit_index(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取连板结构所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        base_url_key = self._resolve_history_or_today_url(trade_date=td, use_today_url=kwargs.get("use_today_url"))
        params: dict[str, Any] = {}
        if base_url_key != "apphwhq":
            params["Day"] = td.strftime("%Y-%m-%d")
        return self._fetch_and_save(
            dataset="daily_limit_index",
            api_name="DailyLimitIndex",
            controller="HisHomeDingPan",
            base_url_key=base_url_key,
            method="GET",
            canonical_name="daily_limit_index",
            **params,
        )

    def _request_weight_performance(self, *, trade_date: Any, slot: str = "17-30", **kwargs: Any) -> dict[str, Any]:
        """拉取权重板块表现所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        return self._fetch_and_save(
            dataset="weight_performance",
            api_name="WeightPerformance",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="GET",
            canonical_name="weight_performance",
            Day=td.strftime("%Y-%m-%d"),
        )

    def _request_get_feng_k_list(
        self,
        *,
        trade_date: Any,
        slot: str = "17-30",
        time: str = "1500",
        index: int = 0,
        order: int = 17,
        st: int = 500,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """拉取最强风口所需的 raw 数据。"""

        td = self._coerce_trade_date(trade_date)
        self._trade_date = td
        self._slot = slot
        time_value = time or "1500"
        return self._fetch_and_save(
            dataset="get_feng_k_list",
            api_name="GetFengKListBest",
            controller="StockFengKData",
            base_url_key=self._resolve_history_or_today_url(trade_date=td, use_today_url=kwargs.get("use_today_url")),
            method="POST",
            canonical_name="get_feng_k_list",
            Day=td.strftime("%Y%m%d"),
            Time=time_value,
            Index=index,
            Order=order,
            st=st,
        )

    def _normalize_hot_topics(self, *, raw: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
        """把热点主题 raw 数据归一为标准 payload。"""

        topics: list[dict[str, Any]] = []
        topics.extend(self._parse_ranked_topics(raw.get("board_strength", {}), kind="concept"))
        topics.extend(self._parse_ranked_topics(raw.get("industry", {}), kind="industry"))
        topics.extend(self._parse_fengkou_topics(raw.get("concept_fengkou", {}), kind="concept_fengkou"))
        return {
            "dataset": "hot_topics",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "topics": topics,
            "sources": ["board_strength", "industry", "concept_fengkou"],
        }

    def _normalize_topic_constituents(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把题材成分 raw 数据归一为标准 payload。"""

        constituents: list[dict[str, Any]] = []
        constituents.extend(self._parse_stock_sector_v2(raw.get("stock_sector_v2", {})))
        theme_detail = raw.get("theme_detail", [])
        if isinstance(theme_detail, list):
            for item in theme_detail:
                constituents.extend(self._parse_theme_detail(item))
        constituents.extend(self._parse_limit_up_reason(raw.get("limit_up_reason", {})))
        constituents.extend(self._parse_limit_up_info(raw.get("limit_up_info", {})))
        constituents.extend(self._parse_lhb_list(raw.get("lhb_list", {})))
        return {
            "dataset": "topic_constituents",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "constituents": constituents,
            "sources": ["stock_sector_v2", "theme_detail", "limit_up_reason", "limit_up_info", "lhb_list"],
        }

    def _normalize_strong_symbols(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把强势标的 raw 数据归一为标准 payload。"""

        symbols: list[dict[str, Any]] = []
        symbols.extend(self._parse_strong_fengkou(raw.get("strong_fengkou", {})))
        symbols.extend(self._parse_interval_stats_stock(raw.get("interval_stats_stock", {})))
        symbols.extend(self._parse_morning_bidding_list(raw.get("morning_bidding_list", {})))
        return {
            "dataset": "strong_symbols",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "symbols": symbols,
            "sources": ["strong_fengkou", "interval_stats_stock", "morning_bidding_list"],
        }

    def _normalize_market_stock_zd_num(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把涨跌停统计 raw 数据归一为标准 payload。"""

        info = raw.get("info", {})
        return {
            "dataset": "market_stock_zd_num",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "limit_up_count": self._extract_numeric(info, ("SJZT", "limit_up_count", "up_count", "zt_count")),
            "limit_down_count": self._extract_numeric(info, ("SJDT", "limit_down_count", "down_count", "dt_count")),
            "panic": self._extract_numeric(info, ("panic", "PANIC", "panic_index")),
            "summary": info if isinstance(info, dict) else {"value": info},
        }

    def _normalize_zhang_ting_expression(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把涨停表达式 raw 数据归一为标准 payload。"""

        info = raw.get("info", [])
        summary = self._sequence_summary(
            info,
            keys=("total_limit_up", "first_board", "second_board", "third_board", "high_board", "break_board_rate", "promotion_rate", "panic", "limit_up_close_rate", "limit_up_open_rate", "limit_up_persistence_rate", "summary"),
        )
        return {
            "dataset": "zhang_ting_expression",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "items": [summary],
            "sources": ["info"],
        }

    def _normalize_daily_limit_index(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把连板结构 raw 数据归一为标准 payload。"""

        info = raw.get("info", [])
        summary = self._sequence_summary(
            info,
            keys=("one_board_count", "two_board_count", "three_board_count", "high_board_count", "limit_up_count"),
        )
        return {
            "dataset": "daily_limit_index",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "items": [summary],
            "sources": ["info"],
        }

    def _normalize_weight_performance(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把权重板块表现 raw 数据归一为标准 payload。"""

        info = raw.get("info", {})
        segments: list[dict[str, Any]] = []
        if isinstance(info, dict):
            for market, rows in info.items():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if isinstance(row, list):
                        segments.append(
                            {
                                "market": market,
                                "symbol": row[0] if len(row) > 0 else None,
                                "name": row[1] if len(row) > 1 else None,
                                "change_pct": row[2] if len(row) > 2 else None,
                            }
                        )
                    elif isinstance(row, dict):
                        segment = dict(row)
                        segment["market"] = market
                        segments.append(segment)
        return {
            "dataset": "weight_performance",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "items": segments,
            "sources": ["info"],
        }

    def _normalize_get_feng_k_list(
        self,
        *,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """把收盘强势标的 raw 数据归一为标准 payload。"""

        items = raw.get("List") or raw.get("info") or raw.get("list") or []
        rows: list[dict[str, Any]] = []
        if isinstance(items, list):
            for row in items:
                if isinstance(row, list):
                    rows.append(
                        {
                            "symbol": row[0] if len(row) > 0 else None,
                            "name": row[1] if len(row) > 1 else None,
                            "strength_score": row[2] if len(row) > 2 else None,
                            "change_pct": row[4] if len(row) > 4 else None,
                            "turnover": row[5] if len(row) > 5 else None,
                            "main_force_buy": row[8] if len(row) > 8 else None,
                            "main_force_sell": row[9] if len(row) > 9 else None,
                            "topic_tags": row[10] if len(row) > 10 else None,
                        }
                    )
                elif isinstance(row, dict):
                    rows.append(dict(row))
        return {
            "dataset": "get_feng_k_list",
            "trade_date": raw.get("trade_date") or (request or {}).get("trade_date"),
            "slot": raw.get("slot") or (request or {}).get("slot"),
            "items": rows,
            "sources": ["List", "info", "list"],
        }

    def _extract_numeric(self, value: Any, keys: tuple[str, ...]) -> Any:
        """从 dict/list 中抽取首个可用数值字段。"""

        if isinstance(value, dict):
            for key in keys:
                item = value.get(key)
                if item is not None:
                    return item
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for key in keys:
                        nested = item.get(key)
                        if nested is not None:
                            return nested
        return None

    def _sequence_summary(self, value: Any, *, keys: tuple[str, ...]) -> dict[str, Any]:
        """把数组或字典转换成具名摘要。"""

        if isinstance(value, dict):
            summary = {key: value.get(key) for key in keys}
            summary["raw"] = value
            return summary
        if isinstance(value, list):
            summary = {key: value[index] if index < len(value) else None for index, key in enumerate(keys)}
            summary["raw"] = value
            return summary
        return {"raw": value}

    def _parse_ranked_topics(self, raw: dict[str, Any], *, kind: str) -> list[dict[str, Any]]:
        """解析 RealRankingInfo 的 list 数组。"""

        items = raw.get("list")
        if not isinstance(items, list):
            return []

        topics: list[dict[str, Any]] = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            topics.append(
                {
                    "kind": kind,
                    "topic_id": row[0],
                    "topic_name": row[1],
                    "score": row[2] if len(row) > 2 else None,
                    "increase_pct": row[3] if len(row) > 3 else None,
                    "speed_pct": row[4] if len(row) > 4 else None,
                    "turnover": row[5] if len(row) > 5 else None,
                    "net_inflow": row[6] if len(row) > 6 else None,
                }
            )
        return topics

    def _parse_fengkou_topics(self, raw: dict[str, Any], *, kind: str) -> list[dict[str, Any]]:
        """解析 GetFengKYDPlate 的 List 数组。"""

        items = raw.get("List") or raw.get("list")
        if not isinstance(items, list):
            return []

        topics: list[dict[str, Any]] = []
        for idx, row in enumerate(items):
            if not isinstance(row, list) or not row:
                continue
            topics.append(
                {
                    "kind": kind,
                    "topic_id": f"fengkou_{idx}",
                    "topic_name": row[0],
                    "score": row[1] if len(row) > 1 else None,
                }
            )
        return topics

    def _parse_stock_sector_v2(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("info")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "stock_sector_v2",
                    "topic_id": row[0],
                    "topic_name": row[1],
                    "topic_change_pct": row[2] if len(row) > 2 else None,
                    "leader_symbol": row[3] if len(row) > 3 else None,
                    "leader_name": row[4] if len(row) > 4 else None,
                    "leader_change_pct": row[5] if len(row) > 5 else None,
                }
            )
        return results

    def _parse_theme_detail(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        if not raw:
            return []
        return [
            {
                "kind": "theme_detail",
                "topic_id": raw.get("ID"),
                "topic_name": raw.get("Name"),
                "brief_intro": raw.get("BriefIntro"),
            }
        ]

    def _parse_limit_up_reason(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("list")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "kind": "limit_up_reason",
                    "topic_id": row.get("ZSCode"),
                    "topic_name": row.get("ZSName"),
                }
            )
        return results

    def _parse_limit_up_info(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("StockList")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "limit_up_info",
                    "symbol": row[0],
                    "name": row[1],
                    "board_num": row[2] if len(row) > 2 else None,
                }
            )
        return results

    def _parse_lhb_list(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("list")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, dict):
                continue
            results.append(
                {
                    "kind": "lhb_list",
                    "symbol": row.get("ID"),
                    "name": row.get("Name"),
                    "net_buy": row.get("BuyIn"),
                }
            )
        return results

    def _parse_strong_fengkou(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("List") or raw.get("list")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "strong_fengkou",
                    "symbol": row[0],
                    "name": row[1],
                    "strength_score": row[2] if len(row) > 2 else None,
                    "change_pct": row[4] if len(row) > 4 else None,
                    "turnover": row[5] if len(row) > 5 else None,
                    "main_force_buy": row[8] if len(row) > 8 else None,
                    "main_force_sell": row[9] if len(row) > 9 else None,
                    "topic_tags": row[10] if len(row) > 10 else None,
                }
            )
        return results

    def _parse_interval_stats_stock(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("List")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "interval_stats_stock",
                    "symbol": row[0],
                    "name": row[1],
                    "return_pct": row[3] if len(row) > 3 else None,
                    "net_inflow": row[6] if len(row) > 6 else None,
                    "turnover_ratio": row[7] if len(row) > 7 else None,
                    "topic_tags": row[10] if len(row) > 10 else None,
                }
            )
        return results

    def _parse_morning_bidding_list(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw.get("info")
        if not isinstance(items, list):
            return []
        results = []
        for row in items:
            if not isinstance(row, list) or len(row) < 2:
                continue
            results.append(
                {
                    "kind": "morning_bidding_list",
                    "symbol": row[0],
                    "name": row[1],
                    "rt_change_pct": row[3] if len(row) > 3 else None,
                    "bid_net": row[6] if len(row) > 6 else None,
                    "bid_turnover": row[8] if len(row) > 8 else None,
                    "topic_tags": row[11] if len(row) > 11 else None,
                }
            )
        return results

    # ================================
    # 13 个具体接口实现
    # ================================

    def fetch_board_strength(self, *, trade_date: date, slot: str, use_today_url: bool | None = None) -> dict[str, Any]:
        """板块强度 - RealRankingInfo (ZSType=7)。

        Args:
            trade_date: 交易日期
            slot: 时段标识，如 "09-30"

        Returns:
            板块强度排名原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="hot_topics",
            api_name="RealRankingInfo",
            controller="ZhiShuRanking",
            base_url_key=self._resolve_history_or_today_url(trade_date=trade_date, use_today_url=use_today_url),
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Type="1",
            Order="1",
            ZSType="7",
            Index=0,
            st=20,
        )

    def fetch_industry_ranking(self, *, trade_date: date, slot: str, use_today_url: bool | None = None) -> dict[str, Any]:
        """行业排名 - RealRankingInfo (ZSType=4)。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            行业排名原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="hot_topics",
            api_name="RealRankingInfo",
            controller="ZhiShuRanking",
            base_url_key=self._resolve_history_or_today_url(trade_date=trade_date, use_today_url=use_today_url),
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Type="2",
            Order="1",
            ZSType="4",
            Index=0,
            st=20,
        )

    def fetch_concept_fengkou(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """概念风口 - GetFengKYDPlate。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            概念风口原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="hot_topics",
            api_name="GetFengKYDPlate",
            controller="StockFengKData",
            base_url_key="apphis",
            method="POST",
            Day=trade_date.strftime("%Y%m%d"),
        )

    def fetch_theme_detail(self, *, trade_date: date, slot: str, theme_id: str = "") -> dict[str, Any]:
        """主题详情 - InfoGet。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            主题详情原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="InfoGet",
            controller="Theme",
            base_url_key="applhb",
            method="POST",
            ID=theme_id,
        )

    def fetch_stock_sector_v2(self, *, trade_date: date, slot: str, stock_id: str = "") -> dict[str, Any]:
        """股票板块 v2 - GetFeaturedSection。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            股票板块 v2 原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetFeaturedSection",
            controller="StockL2Data",
            base_url_key="apphwshhq",
            method="GET",
            StockID=stock_id,
        )

    def fetch_strong_fengkou(self, *, trade_date: date, slot: str, time: str = "", use_today_url: bool | None = None) -> dict[str, Any]:
        """强势风口 - GetFengKListBest。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            强势风口原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="GetFengKListBest",
            controller="StockFengKData",
            base_url_key=self._resolve_history_or_today_url(trade_date=trade_date, use_today_url=use_today_url),
            method="POST",
            Day=trade_date.strftime("%Y%m%d"),
            Time=time,
        )

    def fetch_interval_stats_stock(
        self,
        *,
        trade_date: date,
        slot: str,
        start_date: date | None = None,
        end_date: date | None = None,
        use_today_url: bool | None = None,
    ) -> dict[str, Any]:
        """区间统计股票 - GetInterviewsByDateStock。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            区间统计股票原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="GetInterviewsByDateStock",
            controller="StockLineData",
            base_url_key=self._resolve_history_or_today_url(trade_date=trade_date, use_today_url=use_today_url),
            method="POST",
            DStart=(start_date or trade_date).strftime("%Y-%m-%d"),
            DEnd=(end_date or trade_date).strftime("%Y-%m-%d"),
            Type="2",
            FilterBJS="1",
            Order="1",
            Index=0,
            st=20,
        )

    def fetch_morning_bidding_list(
        self,
        *,
        trade_date: date,
        slot: str,
        pid_type: int = 0,
        data_type: int = 4,
        index: int = 0,
        order: int = 1,
        st: int = 20,
    ) -> dict[str, Any]:
        """早盘竞价列表 - MorningBiddingList。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            早盘竞价列表原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="strong_symbols",
            api_name="MorningBiddingList",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="GET",
            Date=trade_date.strftime("%Y-%m-%d"),
            PidType=pid_type,
            Type=data_type,
            Index=index,
            Order=order,
            st=st,
        )

    def fetch_limit_up_reason(self, *, trade_date: date, slot: str, index: int = 0, st: int = 20) -> dict[str, Any]:
        """涨停原因 - GetPlateInfo_w38。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            涨停原因原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetPlateInfo_w38",
            controller="HisLimitResumption",
            base_url_key="apphis",
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Index=index,
            st=st,
        )

    def fetch_pre_market_bid(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """盘前竞价 - MorningBidding。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            盘前竞价原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_context",
            api_name="MorningBidding",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="GET",
            Date=trade_date.strftime("%Y-%m-%d"),
        )

    def fetch_pre_market_stats(self, *, trade_date: date, slot: str) -> dict[str, Any]:
        """盘前统计 - MorningBiddingNum。

        Args:
            trade_date: 交易日期
            slot: 09-25 时段

        Returns:
            盘前统计原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="market_context",
            api_name="MorningBiddingNum",
            controller="HisHomeDingPan",
            base_url_key="apphis",
            method="GET",
            Date=trade_date.strftime("%Y-%m-%d"),
        )

    def fetch_limit_up_info(self, *, trade_date: date, slot: str, index: int = 0, st: int = 20, use_today_url: bool | None = None) -> dict[str, Any]:
        """涨停信息 - GetZhangTingTianTi。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            涨停信息原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetZhangTingTianTi",
            controller="FuPanLa",
            base_url_key=self._resolve_history_or_today_url(trade_date=trade_date, use_today_url=use_today_url),
            method="POST",
            Date=trade_date.strftime("%Y-%m-%d"),
            Index=index,
            st=st,
        )

    def fetch_lhb_list(self, *, trade_date: date, slot: str, index: int = 0, st: int = 300) -> dict[str, Any]:
        """龙虎榜列表 - GetStockList。

        Args:
            trade_date: 交易日期
            slot: 17-30 时段

        Returns:
            龙虎榜列表原始响应
        """
        self._trade_date = trade_date
        self._slot = slot
        return self._fetch_and_save(
            dataset="topic_constituents",
            api_name="GetStockList",
            controller="LongHuBang",
            base_url_key="applhb",
            method="POST",
            Time=trade_date.strftime("%Y-%m-%d"),
            Index=index,
            st=st,
        )

    def fetch_market_stock_zd_num(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """涨跌停统计 - MarketStockZDNum。"""

        if offline:
            raw = self._load_canonical_raw("market_stock_zd_num", trade_date=trade_date, slot=slot)
            return self._normalize_market_stock_zd_num(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("market_stock_zd_num", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch market_stock_zd_num")
        return result.payload

    def fetch_zhang_ting_expression(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """涨停表达式 - ZhangTingExpression。"""

        if offline:
            raw = self._load_canonical_raw("zhang_ting_expression", trade_date=trade_date, slot=slot)
            return self._normalize_zhang_ting_expression(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("zhang_ting_expression", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch zhang_ting_expression")
        return result.payload

    def fetch_daily_limit_index(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """连板结构 - DailyLimitIndex。"""

        if offline:
            raw = self._load_canonical_raw("daily_limit_index", trade_date=trade_date, slot=slot)
            return self._normalize_daily_limit_index(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("daily_limit_index", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch daily_limit_index")
        return result.payload

    def fetch_weight_performance(self, *, trade_date: date | str, slot: str = "17-30", offline: bool = False, **kwargs: Any) -> dict[str, Any]:
        """权重板块表现 - WeightPerformance。"""

        if offline:
            raw = self._load_canonical_raw("weight_performance", trade_date=trade_date, slot=slot)
            return self._normalize_weight_performance(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run("weight_performance", request={"trade_date": trade_date, "slot": slot, **kwargs})
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch weight_performance")
        return result.payload

    def fetch_get_feng_k_list(
        self,
        *,
        trade_date: date | str,
        slot: str = "17-30",
        offline: bool = False,
        time: str = "1500",
        index: int = 0,
        order: int = 17,
        st: int = 500,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """收盘强势标的 - GetFengKListBest。"""

        if offline:
            raw = self._load_canonical_raw("get_feng_k_list", trade_date=trade_date, slot=slot)
            return self._normalize_get_feng_k_list(raw=raw, request={"trade_date": trade_date, "slot": slot})
        result = self.run(
            "get_feng_k_list",
            request={
                "trade_date": trade_date,
                "slot": slot,
                "time": time,
                "index": index,
                "order": order,
                "st": st,
                **kwargs,
            },
        )
        if result.status != ProviderStatus.ok:
            raise ProviderError("; ".join(result.errors) or "failed to fetch get_feng_k_list")
        return result.payload
