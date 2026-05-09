"""信号版本控制 - 支持按日期分目录和归档压缩读取。

存储结构：
    data/signals/
    ├── 2026-04-30/
    │   ├── idea_a1b2c3d4.json
    │   └── idea_e5f6g7h8.json
    ├── 2026-04-29/
    │   └── ...
    └── archive/
        ├── 2026-04-25.tar.gz
        ├── 2026-04-24.tar.gz
        └── ...

归档策略：
    - 最近 N 天保留原始 JSON 文件（默认 10 天）
    - 超过 N 天的目录压缩为 tar.gz 归档
    - 读取时自动从归档流读取，不落临时文件
"""

from __future__ import annotations

import json
import tarfile
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any

from src.common.logger import get_logger
from src.common.paths import resolve_project_path
from src.strategy.types import Signal, SignalContext, SignalWithContext

logger = get_logger(__name__)

# 日期格式（用于目录名和 signal_id 编码）
_DATE_FMT = "%Y-%m-%d"


class SignalVersioning:
    """信号版本控制，支持按日期分目录和归档压缩读取。

    record() 保存时：
    - 内存：始终存储在 self._versions
    - 文件：保存到 self._storage_path / {trade_date} / {signal_id}.json

    get_version() 读取时（优先级递减）：
    1. 内存缓存 self._versions
    2. 原始文件（扫描日期目录或根目录兼容旧格式）
    3. 归档文件（从 tar.gz 流读取，不落临时文件）

    归档策略由 archive_old_signals() 触发，不自动执行。
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        *,
        retention_days: int = 10,
    ):
        """初始化信号版本控制器。

        Args:
            storage_path: 存储根目录，默认 data/signals
            retention_days: 原始 JSON 保留天数，默认 10 天
                             超过此天数的目录会被 archive_old_signals() 压缩
        """
        self._storage_path = resolve_project_path(storage_path or "data/signals")
        self._versions: dict[str, SignalWithContext] = {}
        self._retention_days = retention_days
        self._archive_dir = self._storage_path / "archive"

    # -------------------------------------------------------------------------
    # 公共接口
    # -------------------------------------------------------------------------

    def record(self, signal: Signal, context: SignalContext) -> str:
        """记录信号及其上下文。

        保存路径：self._storage_path / {trade_date} / {signal_id}.json

        Args:
            signal: 信号
            context: 上下文

        Returns:
            版本 ID（signal.signal_id）
        """
        version_id = signal.signal_id
        trade_date = self._get_trade_date(signal.timestamp)

        # 内存存储（始终保留）
        self._versions[version_id] = SignalWithContext(
            signal=signal,
            context=context,
        )

        # 文件存储（按日期分目录）
        if self._storage_path:
            day_dir = self._storage_path / trade_date
            day_dir.mkdir(parents=True, exist_ok=True)
            file_path = day_dir / f"{version_id}.json"
            data = {
                "signal": self._signal_to_dict(signal),
                "context": self._context_to_dict(context),
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

        return version_id

    def get_version(self, signal_id: str) -> SignalWithContext | None:
        """获取信号完整版本。

        读取优先级：内存缓存 > 原始文件 > 归档文件

        Args:
            signal_id: 信号 ID，格式：idea_{uuid} 或 idea_{date}_{uuid}

        Returns:
            SignalWithContext 或 None（不存在时）
        """
        # 1. 内存缓存
        if signal_id in self._versions:
            return self._versions[signal_id]

        # 2. 原始文件
        result = self._find_and_load_raw_file(signal_id)
        if result is not None:
            # 缓存到内存（避免下次重复读文件）
            self._versions[signal_id] = result
            return result

        # 3. 归档文件
        result = self._find_and_load_from_archive(signal_id)
        if result is not None:
            self._versions[signal_id] = result
            return result

        return None

    def list_versions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SignalWithContext]:
        """列出信号版本（仅内存和原始文件，不扫描归档）。

        Args:
            symbol: 按标的过滤（暂不支持）
            since: 按时间过滤
            limit: 返回数量限制

        Returns:
            SignalWithContext 列表（按时间倒序）
        """
        results: list[SignalWithContext] = []

        # 从内存过滤
        for v in self._versions.values():
            if symbol and v.signal.symbol != symbol:
                continue
            if since and v.context.timestamp < since:
                continue
            results.append(v)

        # 从日期目录扫描（不扫归档）
        if self._storage_path and self._storage_path.exists():
            for day_dir in self._storage_path.iterdir():
                if not day_dir.is_dir():
                    continue
                if not self._is_valid_date(day_dir.name):
                    continue
                day_date = datetime.strptime(day_dir.name, _DATE_FMT).date()
                if since and day_date < since.date():
                    continue
                for file_path in day_dir.glob("*.json"):
                    signal_id = file_path.stem
                    if signal_id in self._versions:
                        continue  # 已加入
                    data = self._load_json_file(file_path)
                    if data is None:
                        continue
                    try:
                        sc = SignalWithContext(
                            signal=self._dict_to_signal(data["signal"]),
                            context=self._dict_to_context(data["context"]),
                        )
                        if symbol and sc.signal.symbol != symbol:
                            continue
                        results.append(sc)
                    except Exception:
                        logger.warning("信号文件解析失败: %s", file_path)

        # 按时间倒序
        results.sort(key=lambda x: x.context.timestamp, reverse=True)
        return results[:limit]

    def archive_old_signals(self, *, before_date: date | None = None) -> list[Path]:
        """归档超过 retention_days 的日期目录。

        将 self._storage_path / {date} 压缩为 self._archive_dir / {date}.tar.gz，
        然后删除原始目录。

        Args:
            before_date: 归档此日期之前的目录，默认 (today - retention_days)

        Returns:
            已归档的目录列表
        """
        if before_date is None:
            before_date = date.today() - timedelta(days=self._retention_days)

        archived: list[Path] = []
        self._archive_dir.mkdir(parents=True, exist_ok=True)

        if not self._storage_path or not self._storage_path.exists():
            return archived

        for day_dir in self._storage_path.iterdir():
            if not day_dir.is_dir():
                continue
            if not self._is_valid_date(day_dir.name):
                continue

            day_date = datetime.strptime(day_dir.name, _DATE_FMT).date()
            if day_date >= before_date:
                continue  # 在保留期内

            # 检查目录是否为空
            json_files = list(day_dir.glob("*.json"))
            if not json_files:
                day_dir.rmdir()
                logger.debug("删除空目录: %s", day_dir)
                continue

            # 压缩为 tar.gz
            archive_file = self._archive_dir / f"{day_dir.name}.tar.gz"
            try:
                with tarfile.open(archive_file, "w:gz") as tf:
                    for json_file in json_files:
                        # 归档内路径只用文件名（不带日期目录层）
                        tf.add(json_file, arcname=json_file.name)
                logger.info("归档完成: %s -> %s (%d 个文件)", day_dir, archive_file, len(json_files))
                archived.append(day_dir)

                # 删除原始目录
                import shutil
                shutil.rmtree(day_dir)
                logger.debug("删除原始目录: %s", day_dir)
            except Exception as e:
                logger.error("归档失败: %s -> %s, error=%s", day_dir, archive_file, e)

        return archived

    # -------------------------------------------------------------------------
    # 私有方法：文件查找与加载
    # -------------------------------------------------------------------------

    def _find_and_load_raw_file(self, signal_id: str) -> SignalWithContext | None:
        """在原始文件中查找并加载信号。

        查找顺序：
        1. 按日期目录（新版）：self._storage_path / {date} / {signal_id}.json
        2. 根目录（兼容旧版）：self._storage_path / {signal_id}.json
        """
        if not self._storage_path or not self._storage_path.exists():
            return None

        # 尝试从 signal_id 解析日期（格式：idea_{date}_{uuid}）
        signal_date = self._try_parse_date_from_signal_id(signal_id)
        if signal_date:
            day_dir = self._storage_path / signal_date
            file_path = day_dir / f"{signal_id}.json"
            if file_path.exists():
                data = self._load_json_file(file_path)
                if data:
                    return SignalWithContext(
                        signal=self._dict_to_signal(data["signal"]),
                        context=self._dict_to_context(data["context"]),
                    )

        # 扫描所有日期目录（不知道日期时）
        for day_dir in self._storage_path.iterdir():
            if not day_dir.is_dir() or not self._is_valid_date(day_dir.name):
                continue
            file_path = day_dir / f"{signal_id}.json"
            if file_path.exists():
                data = self._load_json_file(file_path)
                if data:
                    return SignalWithContext(
                        signal=self._dict_to_signal(data["signal"]),
                        context=self._dict_to_context(data["context"]),
                    )

        # 兼容旧版：根目录下的单个文件
        legacy_path = self._storage_path / f"{signal_id}.json"
        if legacy_path.exists():
            data = self._load_json_file(legacy_path)
            if data:
                return SignalWithContext(
                    signal=self._dict_to_signal(data["signal"]),
                    context=self._dict_to_context(data["context"]),
                )

        return None

    def _find_and_load_from_archive(self, signal_id: str) -> SignalWithContext | None:
        """从归档文件中查找并加载信号（流读取，不落临时文件）。

        通过 signal_id 中的日期直接定位归档文件：
        idea_{date}_{uuid} -> archive/{date}.tar.gz
        """
        if not self._archive_dir or not self._archive_dir.exists():
            return None

        # 从 signal_id 解析日期
        signal_date = self._try_parse_date_from_signal_id(signal_id)
        if not signal_date:
            # 不知道日期，遍历归档文件
            for archive_file in self._archive_dir.glob("*.tar.gz"):
                result = self._load_from_tar_gz(archive_file, signal_id)
                if result is not None:
                    return result
            return None

        # 直接定位归档文件
        archive_file = self._archive_dir / f"{signal_date}.tar.gz"
        if not archive_file.exists():
            return None

        return self._load_from_tar_gz(archive_file, signal_id)

    def _load_from_tar_gz(
        self,
        archive_file: Path,
        signal_id: str,
    ) -> SignalWithContext | None:
        """从 tar.gz 归档中流读取指定信号文件。

        使用 tarfile.extractfile() 直接读取成员内容，不落临时文件。

        Args:
            archive_file: 归档文件路径
            signal_id: 信号 ID（用于 arcname 查找）

        Returns:
            SignalWithContext 或 None
        """
        try:
            with tarfile.open(archive_file, "r:gz") as tf:
                # 归档内文件名就是 signal_id.json
                member = tf.extractfile(f"{signal_id}.json")
                if member is None:
                    return None
                data = json.load(member)
                return SignalWithContext(
                    signal=self._dict_to_signal(data["signal"]),
                    context=self._dict_to_context(data["context"]),
                )
        except Exception as e:
            logger.warning("从归档读取失败: %s / %s, error=%s", archive_file, signal_id, e)
            return None

    @staticmethod
    def _load_json_file(file_path: Path) -> dict | None:
        """安全加载 JSON 文件。"""
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("JSON 文件读取失败: %s, error=%s", file_path, e)
            return None

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_trade_date(ts: datetime | None) -> str:
        """从时间戳获取交易日字符串（YYYY-MM-DD）。"""
        if ts is None:
            ts = datetime.now()
        return ts.strftime(_DATE_FMT)

    @staticmethod
    def _is_valid_date(s: str) -> bool:
        """判断字符串是否为有效日期格式 YYYY-MM-DD。"""
        if len(s) != 10 or s[4] != "-" or s[7] != "-":
            return False
        try:
            datetime.strptime(s, _DATE_FMT)
            return True
        except ValueError:
            return False

    @staticmethod
    def _try_parse_date_from_signal_id(signal_id: str) -> str | None:
        """从 signal_id 解析日期部分。

        格式：idea_{date}_{uuid} 或 idea_{uuid}

        Returns:
            日期字符串（YYYY-MM-DD）或 None
        """
        # 格式：idea_2026-04-25_a1b2c3d4
        parts = signal_id.split("_")
        if len(parts) >= 3 and SignalVersioning._is_valid_date(parts[1]):
            return parts[1]

        # 格式：idea_20260425_a1b2c3d4（无连字符）
        if len(parts) >= 3 and len(parts[1]) == 8 and parts[1].isdigit():
            try:
                datetime.strptime(parts[1], "%Y%m%d")
                return f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}"
            except ValueError:
                pass

        # 旧格式：idea_a1b2c3d4（无日期）
        return None

    # -------------------------------------------------------------------------
    # 序列化/反序列化（供外部调用）
    # -------------------------------------------------------------------------

    def _signal_to_dict(self, signal: Signal) -> dict[str, Any]:
        """信号转字典。"""
        return {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "side": signal.side.value if hasattr(signal.side, "value") else signal.side,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            "triggered_rules": signal.triggered_rules,
            "synthesis_mode": signal.synthesis_mode.value if signal.synthesis_mode else None,
            "entry_price": {
                "type": signal.entry_price.type if signal.entry_price else None,
                "value": signal.entry_price.value if signal.entry_price else None,
            } if signal.entry_price else None,
            "position_size": {
                "type": signal.position_size.type.value if signal.position_size else None,
                "value": signal.position_size.value if signal.position_size else None,
            } if signal.position_size else None,
            "version": signal.version,
            "strategy_version_id": signal.strategy_version_id,
            "metadata": signal.metadata,
        }

    def _context_to_dict(self, context: SignalContext) -> dict[str, Any]:
        """上下文转字典。"""
        return {
            "features_snapshot": context.features_snapshot,
            "market_state": context.market_state,
            "rules_snapshot": context.rules_snapshot,
            "timestamp": context.timestamp.isoformat() if context.timestamp else None,
            "strategy_version_id": context.strategy_version_id,
            "market_universe_snapshot": context.market_universe_snapshot,
            "topic_source_ids": context.topic_source_ids,
        }

    def _dict_to_signal(self, data: dict) -> Signal:
        """字典转信号。"""
        from src.strategy.types import SignalSide, SynthesisMode, PriceSpec, PositionSize

        return Signal(
            signal_id=data["signal_id"],
            symbol=data["symbol"],
            side=SignalSide(data["side"]) if data["side"] else SignalSide.HOLD,
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
            triggered_rules=data["triggered_rules"],
            synthesis_mode=SynthesisMode(data["synthesis_mode"]) if data["synthesis_mode"] else None,
            entry_price=PriceSpec(**data["entry_price"]) if data["entry_price"] else None,
            position_size=PositionSize(**data["position_size"]) if data["position_size"] else None,
            version=data.get("version", "v1"),
            strategy_version_id=data.get("strategy_version_id"),
            metadata=data.get("metadata", {}),
        )

    def _dict_to_context(self, data: dict) -> SignalContext:
        """字典转上下文。"""
        return SignalContext(
            features_snapshot=data["features_snapshot"],
            market_state=data["market_state"],
            rules_snapshot=data["rules_snapshot"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
            strategy_version_id=data.get("strategy_version_id"),
            market_universe_snapshot=data.get("market_universe_snapshot"),
            topic_source_ids=data.get("topic_source_ids", []),
        )
