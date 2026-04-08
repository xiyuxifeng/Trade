"""
对齐分析缓存和版本管理 — P3-021。

实现评分结果缓存和版本管理：
  - P3-021: 评分结果缓存和版本管理
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.alignment.types import (
    AlignmentReport,
    ConflictDetection,
    ConflictType,
    ConfidenceScore,
)
from src.alignment.scoring import DetailedConfidenceScore


# ---------------------------------------------------------------------------
# P3-021: 评分结果缓存和版本管理
# ---------------------------------------------------------------------------

# 默认缓存目录
DEFAULT_CACHE_DIR = Path("data/processed/alignment_cache")


@dataclass
class AlignmentVersion:
    """对齐分析版本记录。"""
    version_id: str  # 版本 ID（UUID 或 hash）
    trader_id: str
    generated_at: datetime
    data_hash: str  # 数据指纹
    score_snapshot: dict[str, Any]  # 评分快照
    conflict_snapshot: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CachedAlignmentResult:
    """缓存的对齐分析结果。"""
    trader_id: str
    version_id: str
    cached_at: datetime
    overall_score: float | None = None
    grade: str | None = None
    conflict_count: int = 0
    data_hash: str | None = None
    file_path: Path | None = None


class AlignmentCache:
    """对齐分析缓存管理器。"""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR):
        """初始化缓存管理器。

        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / "index.json"
        self._index: dict[str, CachedAlignmentResult] = {}
        self._load_index()

    def _load_index(self) -> None:
        """加载缓存索引。"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._index = {
                        k: CachedAlignmentResult(**v, file_path=Path(v["file_path"]) if v.get("file_path") else None)
                        for k, v in data.items()
                    }
            except (json.JSONDecodeError, TypeError):
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """保存缓存索引。"""
        data = {
            k: {
                **v.__dict__,
                "file_path": str(v.file_path) if v.file_path else None,
            }
            for k, v in self._index.items()
        }
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    def compute_data_hash(
        self,
        rules: list[dict],
        trades: list[dict] | None = None,
    ) -> str:
        """计算数据指纹。

        Args:
            rules: 规则列表
            trades: 交易列表（可选）

        Returns:
            数据指纹字符串
        """
        data = {
            "rules": rules,
            "trades": trades or [],
        }
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def cache_result(
        self,
        trader_id: str,
        detailed_score: DetailedConfidenceScore | None = None,
        conflicts: ConflictDetection | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AlignmentVersion:
        """缓存分析结果。

        Args:
            trader_id: 交易员 ID
            detailed_score: 详细可信度评分
            conflicts: 冲突检测结果
            metadata: 额外元数据

        Returns:
            版本记录
        """
        version_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        generated_at = datetime.now()

        # 构建评分快照
        score_snapshot: dict[str, Any] = {}
        if detailed_score:
            score_snapshot = {
                "overall_score": detailed_score.overall_score,
                "grade": detailed_score.grade,
                "grade_label": detailed_score.grade_label,
                "score_breakdown": detailed_score.score_breakdown,
                "component_scores": detailed_score.component_scores,
            }

        # 构建冲突快照
        conflict_snapshot: dict[str, Any] | None = None
        if conflicts:
            conflict_snapshot = {
                "total_conflicts": conflicts.total_conflicts,
                "by_type": conflicts.by_type,
                "by_severity": conflicts.by_severity,
            }

        # 创建版本记录
        version = AlignmentVersion(
            version_id=version_id,
            trader_id=trader_id,
            generated_at=generated_at,
            data_hash="",  # 稍后填充
            score_snapshot=score_snapshot,
            conflict_snapshot=conflict_snapshot,
            metadata=metadata or {},
        )

        # 计算数据指纹
        data_hash = self.compute_data_hash(
            [score_snapshot],
            [conflict_snapshot] if conflict_snapshot else None,
        )
        version.data_hash = data_hash

        # 保存完整结果到文件
        file_path = self.cache_dir / f"{trader_id}_{version_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": version_id,
                "trader_id": trader_id,
                "generated_at": generated_at.isoformat(),
                "score_snapshot": score_snapshot,
                "conflict_snapshot": conflict_snapshot,
                "metadata": metadata or {},
            }, f, indent=2, default=str, ensure_ascii=False)

        # 更新索引
        cached = CachedAlignmentResult(
            trader_id=trader_id,
            version_id=version_id,
            cached_at=generated_at,
            overall_score=detailed_score.overall_score if detailed_score else None,
            grade=detailed_score.grade if detailed_score else None,
            conflict_count=conflicts.total_conflicts if conflicts else 0,
            data_hash=data_hash,
            file_path=file_path,
        )
        self._index[f"{trader_id}_{version_id}"] = cached
        self._save_index()

        return version

    def get_latest_version(self, trader_id: str) -> CachedAlignmentResult | None:
        """获取最新的缓存版本。

        Args:
            trader_id: 交易员 ID

        Returns:
            最新缓存结果，如果没有则返回 None
        """
        candidates = [
            v for v in self._index.values() if v.trader_id == trader_id
        ]
        if not candidates:
            return None

        return max(candidates, key=lambda x: x.cached_at)

    def get_version_history(
        self,
        trader_id: str,
        limit: int = 10,
    ) -> list[CachedAlignmentResult]:
        """获取版本历史。

        Args:
            trader_id: 交易员 ID
            limit: 返回数量限制

        Returns:
            版本历史列表（按时间倒序）
        """
        candidates = [
            v for v in self._index.values() if v.trader_id == trader_id
        ]
        candidates.sort(key=lambda x: x.cached_at, reverse=True)
        return candidates[:limit]

    def load_version(
        self,
        trader_id: str,
        version_id: str,
    ) -> AlignmentVersion | None:
        """加载指定版本。

        Args:
            trader_id: 交易员 ID
            version_id: 版本 ID

        Returns:
            版本记录，如果没有则返回 None
        """
        cache_key = f"{trader_id}_{version_id}"
        if cache_key not in self._index:
            return None

        file_path = self._index[cache_key].file_path
        if not file_path or not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return AlignmentVersion(
            version_id=data["version"],
            trader_id=data["trader_id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            data_hash=data.get("data_hash", ""),
            score_snapshot=data.get("score_snapshot", {}),
            conflict_snapshot=data.get("conflict_snapshot"),
            metadata=data.get("metadata", {}),
        )

    def is_cache_valid(
        self,
        trader_id: str,
        current_data_hash: str,
        max_age_hours: float = 24.0,
    ) -> bool:
        """检查缓存是否有效。

        Args:
            trader_id: 交易员 ID
            current_data_hash: 当前数据指纹
            max_age_hours: 缓存最大有效期（小时）

        Returns:
            是否有效
        """
        latest = self.get_latest_version(trader_id)
        if not latest:
            return False

        # 检查数据指纹
        if latest.data_hash != current_data_hash:
            return False

        # 检查时间
        age = (datetime.now() - latest.cached_at).total_seconds() / 3600
        if age > max_age_hours:
            return False

        return True

    def clear_old_versions(
        self,
        trader_id: str | None = None,
        keep_latest: int = 5,
    ) -> int:
        """清理旧版本。

        Args:
            trader_id: 交易员 ID（None 表示所有交易员）
            keep_latest: 保留的最新版本数量

        Returns:
            删除的版本数量
        """
        deleted = 0

        if trader_id:
            traders = [trader_id]
        else:
            traders = set(v.trader_id for v in self._index.values())

        for tid in traders:
            history = self.get_version_history(tid)
            for version in history[keep_latest:]:
                cache_key = f"{version.trader_id}_{version.version_id}"
                if cache_key in self._index:
                    # 删除文件
                    if version.file_path and version.file_path.exists():
                        version.file_path.unlink()
                    # 从索引移除
                    del self._index[cache_key]
                    deleted += 1

        if deleted > 0:
            self._save_index()

        return deleted

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息。

        Returns:
            统计信息字典
        """
        traders = set(v.trader_id for v in self._index.values())
        total_versions = len(self._index)

        return {
            "total_versions": total_versions,
            "total_traders": len(traders),
            "cache_dir": str(self.cache_dir),
            "by_trader": {
                tid: len([v for v in self._index.values() if v.trader_id == tid])
                for tid in traders
            },
        }


def incremental_score_update(
    previous_score: DetailedConfidenceScore,
    new_trades: list[dict],
    new_conflicts: list[dict],
    decay_factor: float = 0.95,
) -> DetailedConfidenceScore:
    """增量更新评分（考虑历史评分的影响）。

    增量更新策略：
      - 新数据权重 = 1 - decay_factor
      - 历史评分权重 = decay_factor

    Args:
        previous_score: 历史评分
        new_trades: 新交易数据
        new_conflicts: 新冲突数据
        decay_factor: 历史权重衰减因子

    Returns:
        更新后的评分
    """
    # 计算新数据的基础评分
    new_score = len(new_trades) / max(1, len(new_trades) + 10)  # 简化计算

    # 加权合并
    updated_score = (
        decay_factor * previous_score.overall_score +
        (1 - decay_factor) * new_score
    )

    # 构建更新后的评分
    updated = DetailedConfidenceScore(
        trader_id=previous_score.trader_id,
        overall_score=updated_score,
        grade=previous_score.grade,
        grade_label=previous_score.grade_label,
        dimensions=previous_score.dimensions,
        score_breakdown=previous_score.score_breakdown.copy(),
        component_scores=previous_score.component_scores.copy(),
        weights_used=previous_score.weights_used.copy(),
    )

    return updated


def compare_versions(
    version1: AlignmentVersion,
    version2: AlignmentVersion,
) -> dict[str, Any]:
    """比较两个版本的差异。

    Args:
        version1: 版本 1
        version2: 版本 2

    Returns:
        差异报告
    """
    diff = {
        "version1": version1.version_id,
        "version2": version2.version_id,
        "time_diff_hours": (
            version2.generated_at - version1.generated_at
        ).total_seconds() / 3600,
    }

    # 比较评分
    score1 = version1.score_snapshot.get("overall_score", 0)
    score2 = version2.score_snapshot.get("overall_score", 0)
    diff["score_change"] = score2 - score1
    diff["score_change_pct"] = (score2 - score1) / max(0.01, score1) if score1 > 0 else 0

    # 比较冲突
    conflict1 = version1.conflict_snapshot or {}
    conflict2 = version2.conflict_snapshot or {}
    diff["conflict_change"] = (
        conflict2.get("total_conflicts", 0) -
        conflict1.get("total_conflicts", 0)
    )

    return diff
