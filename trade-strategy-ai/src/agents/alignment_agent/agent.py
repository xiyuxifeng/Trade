"""
Alignment Agent — P3-022~P3-025。

对齐分析 Agent，负责：
  - P3-022: 集成 Rule Matching / Behavior Fit / Conflict Detection
  - P3-023: 协调各评分模块执行
  - P3-024: 评分输出的持久化存储
  - P3-025: 增量对齐计算
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.alignment import (
    AlignmentReport,
    BehaviorFitScore,
    ConflictDetection,
    ConflictDetectionResult,
    DetailedConfidenceScore,
    RuleMatchScore,
    StrategyRule,
    TradeRecord,
    rule_match_score,
    behavior_fit_score,
    detect_conflicts,
    detailed_confidence_scoring,
    detect_unmatched_trades,
    compute_rule_coverage,
    compute_rule_accuracy,
    generate_text_report,
    generate_optimization_suggestions,
    AlignmentCache,
)
from src.alignment.types import BehaviorProfile


# ---------------------------------------------------------------------------
# P3-022: 请求和结果数据类
# ---------------------------------------------------------------------------

@dataclass
class AlignmentRequest:
    """对齐分析请求。"""
    trader_id: str
    rules: list[StrategyRule]
    trades: list[TradeRecord] | None = None
    profile: BehaviorProfile | None = None
    include_suggestions: bool = True
    use_cache: bool = True
    weights: dict[str, float] | None = None


@dataclass
class AlignmentResult:
    """对齐分析结果。"""
    trader_id: str
    generated_at: datetime = field(default_factory=datetime.now)

    # 规则匹配
    rule_match_scores: list[RuleMatchScore] = field(default_factory=list)
    unmatched_trades: list[Any] = field(default_factory=list)

    # 行为适配度
    behavior_fit: BehaviorFitScore | None = None

    # 冲突检测
    conflicts: ConflictDetection | None = None

    # 综合评分
    detailed_score: DetailedConfidenceScore | None = None

    # 优化建议
    suggestions: list[dict[str, Any]] = field(default_factory=list)

    # 文本报告
    text_report: str = ""

    # 元数据
    rules_analyzed: int = 0
    trades_analyzed: int = 0
    cached: bool = False


# ---------------------------------------------------------------------------
# P3-024: 持久化存储
# ---------------------------------------------------------------------------

class AlignmentStorage:
    """对齐分析结果持久化存储。

    支持：
      - JSON 文件存储
      - 版本化管理
      - 增量数据追加
    """

    def __init__(self, storage_dir: str | Path = "data/processed/alignment"):
        """初始化存储。

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, result: AlignmentResult) -> Path:
        """保存对齐分析结果。

        Args:
            result: 对齐分析结果

        Returns:
            保存的文件路径
        """
        timestamp = result.generated_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{result.trader_id}_{timestamp}.json"
        filepath = self.storage_dir / filename

        data = self._serialize_result(result)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

        # 保存最新版本链接
        self._update_latest_link(result.trader_id, filepath)

        return filepath

    def load(self, trader_id: str, version: str | None = None) -> AlignmentResult | None:
        """加载对齐分析结果。

        Args:
            trader_id: 交易员 ID
            version: 版本标识（None 表示最新版本）

        Returns:
            对齐分析结果，如果没有则返回 None
        """
        if version:
            filepath = self.storage_dir / f"{trader_id}_{version}.json"
        else:
            filepath = self.storage_dir / f"{trader_id}_latest.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._deserialize_result(data)

    def list_versions(self, trader_id: str) -> list[dict[str, Any]]:
        """列出可用的版本。

        Args:
            trader_id: 交易员 ID

        Returns:
            版本信息列表
        """
        pattern = f"{trader_id}_*.json"
        files = sorted(self.storage_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        versions = []
        for f in files:
            if "_latest" in f.name:
                continue
            stat = f.stat()
            # 从文件名提取版本
            parts = f.stem.split("_")
            if len(parts) >= 2:
                versions.append({
                    "version": parts[-1],
                    "filename": f.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        return versions[:10]  # 最多返回 10 个版本

    def _update_latest_link(self, trader_id: str, filepath: Path) -> None:
        """更新最新版本链接。"""
        latest_path = self.storage_dir / f"{trader_id}_latest.json"
        # 复制文件内容
        with open(filepath, "r", encoding="utf-8") as src:
            content = src.read()
        with open(latest_path, "w", encoding="utf-8") as dst:
            dst.write(content)

    def _serialize_result(self, result: AlignmentResult) -> dict[str, Any]:
        """序列化结果为字典。"""
        data = {
            "trader_id": result.trader_id,
            "generated_at": result.generated_at.isoformat(),
            "rules_analyzed": result.rules_analyzed,
            "trades_analyzed": result.trades_analyzed,
            "cached": result.cached,
            "text_report": result.text_report,
        }

        # 序列化详细评分
        if result.detailed_score:
            data["detailed_score"] = {
                "trader_id": result.detailed_score.trader_id,
                "overall_score": result.detailed_score.overall_score,
                "grade": result.detailed_score.grade,
                "grade_label": result.detailed_score.grade_label,
                "score_breakdown": result.detailed_score.score_breakdown,
            }

        # 序列化冲突检测
        if result.conflicts:
            data["conflicts"] = {
                "total_conflicts": result.conflicts.total_conflicts,
                "by_type": result.conflicts.by_type,
                "by_severity": result.conflicts.by_severity,
                "conflicts": [
                    {
                        "conflict_type": c.conflict_type.value,
                        "severity": c.severity,
                        "message": c.message,
                        "involved_rules": c.involved_rules,
                        "evidence": c.evidence,
                    }
                    for c in result.conflicts.conflicts
                ],
            }

        # 序列化规则匹配评分
        if result.rule_match_scores:
            data["rule_match_scores"] = [
                {
                    "rule_id": s.rule_id,
                    "match_rate": s.match_rate,
                    "avg_score": s.avg_score,
                    "matched_trades": s.matched_trades,
                    "total_trades": s.total_trades,
                }
                for s in result.rule_match_scores
            ]

        # 序列化优化建议
        if result.suggestions:
            data["suggestions"] = result.suggestions

        return data

    def _deserialize_result(self, data: dict[str, Any]) -> AlignmentResult:
        """从字典反序列化结果。"""
        result = AlignmentResult(
            trader_id=data["trader_id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            rules_analyzed=data.get("rules_analyzed", 0),
            trades_analyzed=data.get("trades_analyzed", 0),
            cached=data.get("cached", False),
            text_report=data.get("text_report", ""),
        )

        # 反序列化详细评分
        if "detailed_score" in data:
            ds = data["detailed_score"]
            result.detailed_score = DetailedConfidenceScore(
                trader_id=ds["trader_id"],
                overall_score=ds["overall_score"],
                grade=ds.get("grade", "D"),
                grade_label=ds.get("grade_label", ""),
            )

        # 反序列化冲突检测
        if "conflicts" in data:
            c_data = data["conflicts"]
            result.conflicts = ConflictDetection(
                trader_id=result.trader_id,
                total_conflicts=c_data["total_conflicts"],
                by_type=c_data.get("by_type", {}),
                by_severity=c_data.get("by_severity", {}),
                conflicts=[
                    ConflictDetectionResult(
                        conflict_type=ct,
                        severity=conf["severity"],
                        message=conf["message"],
                        involved_rules=conf["involved_rules"],
                        evidence=conf.get("evidence", {}),
                    )
                    for ct, conf_list in [
                        (ConflictDetectionResult, c_data.get("conflicts", []))
                    ]
                    for conf in (c_data.get("conflicts") or [])
                ] if c_data.get("conflicts") else [],
            )

        # 反序列化规则匹配评分
        if "rule_match_scores" in data:
            result.rule_match_scores = [
                RuleMatchScore(
                    rule_id=s["rule_id"],
                    match_rate=s["match_rate"],
                    avg_score=s["avg_score"],
                    matched_trades=s.get("matched_trades", 0),
                    total_trades=s.get("total_trades", 0),
                )
                for s in data["rule_match_scores"]
            ]

        # 反序列化优化建议
        if "suggestions" in data:
            result.suggestions = data["suggestions"]

        return result


class AlignmentAgent:
    """对齐分析 Agent。

    协调各模块执行对齐分析流程：
      1. 规则匹配评分
      2. 行为适配度评分
      3. 冲突检测
      4. 综合可信度评分
      5. 生成优化建议和报告

    支持功能：
      - P3-023: 集成 Rule Matching / Behavior Fit / Conflict Detection
      - P3-024: 评分输出的持久化存储
      - P3-025: 增量对齐计算
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        storage_dir: str | Path | None = None,
        default_weights: dict[str, float] | None = None,
    ):
        """初始化 Alignment Agent。

        Args:
            cache_dir: 缓存目录，None 则使用 AlignmentCache 默认目录
            storage_dir: 持久化存储目录，None 则使用默认目录
            default_weights: 默认评分权重
        """
        self.cache = AlignmentCache(cache_dir) if cache_dir else None
        self.storage = AlignmentStorage(storage_dir) if storage_dir else None
        self.default_weights = default_weights or {
            "rule_match": 0.30,
            "rule_accuracy": 0.15,
            "behavior_fit": 0.25,
            "coverage": 0.10,
            "conflict_penalty": 0.20,
        }

    async def run(self, request: AlignmentRequest) -> AlignmentResult:
        """执行对齐分析。

        Args:
            request: 对齐分析请求

        Returns:
            对齐分析结果
        """
        result = AlignmentResult(trader_id=request.trader_id)
        result.rules_analyzed = len(request.rules)

        # 1. 规则匹配评分
        result.rule_match_scores = self._compute_rule_match_scores(
            request.rules,
            request.trades,
        )

        # 2. 行为适配度评分
        if request.profile and request.rules:
            result.behavior_fit = behavior_fit_score(
                request.profile,
                request.rules,
            )

        # 3. 冲突检测
        result.conflicts = detect_conflicts(
            request.rules,
            request.trades,
        )

        # 4. 计算覆盖率
        coverage_result = None
        if request.trades and request.rules:
            coverage_result = compute_rule_coverage(
                request.trades,
                request.rules,
            )
            result.unmatched_trades = detect_unmatched_trades(
                request.trades,
                request.rules,
            ).unmatched_trades

        # 5. 计算准确度
        accuracy_scores = None
        if request.trades and request.rules:
            accuracy_result = compute_rule_accuracy(
                request.trades,
                request.rules,
            )
            accuracy_scores = accuracy_result.rule_accuracy

        # 6. 综合可信度评分
        weights = request.weights or self.default_weights
        result.detailed_score = detailed_confidence_scoring(
            trader_id=request.trader_id,
            rule_match_scores=result.rule_match_scores,
            rule_accuracy_scores=accuracy_scores,
            behavior_fit=result.behavior_fit,
            coverage_score=coverage_result.overall_coverage if coverage_result else None,
            conflict_penalty=self._compute_conflict_penalty(result.conflicts),
            weights=weights,
        )

        # 7. 生成优化建议
        if request.include_suggestions and result.conflicts:
            result.suggestions = generate_optimization_suggestions(result.conflicts)

        # 8. 生成文本报告
        result.text_report = generate_text_report(
            trader_id=request.trader_id,
            rules=request.rules,
            trades=request.trades,
            rule_match_scores=result.rule_match_scores,
            conflicts=result.conflicts,
            detailed_score=result.detailed_score,
            include_suggestions=request.include_suggestions,
        )

        # 9. 更新元数据
        result.trades_analyzed = len(request.trades) if request.trades else 0

        # 10. 缓存结果
        if request.use_cache and self.cache:
            self.cache.cache_result(
                trader_id=request.trader_id,
                detailed_score=result.detailed_score,
                conflicts=result.conflicts,
            )
            result.cached = True

        # 11. 持久化存储（如果配置了 storage）
        if self.storage:
            self.storage.save(result)

        return result

    def save_result(self, result: AlignmentResult) -> Path | None:
        """保存结果到持久化存储。

        Args:
            result: 对齐分析结果

        Returns:
            保存的文件路径，失败返回 None
        """
        if not self.storage:
            return None
        return self.storage.save(result)

    def load_result(self, trader_id: str, version: str | None = None) -> AlignmentResult | None:
        """从持久化存储加载结果。

        Args:
            trader_id: 交易员 ID
            version: 版本标识（None 表示最新版本）

        Returns:
            对齐分析结果
        """
        if not self.storage:
            return None
        return self.storage.load(trader_id, version)

    def list_result_versions(self, trader_id: str) -> list[dict[str, Any]]:
        """列出可用的结果版本。

        Args:
            trader_id: 交易员 ID

        Returns:
            版本信息列表
        """
        if not self.storage:
            return []
        return self.storage.list_versions(trader_id)

    def _compute_rule_match_scores(
        self,
        rules: list[StrategyRule],
        trades: list[TradeRecord] | None,
    ) -> list[RuleMatchScore]:
        """计算规则匹配评分。"""
        if not trades:
            # 无交易时，返回基于置信度的默认评分
            return [
                RuleMatchScore(
                    rule_id=rule.rule_id,
                    matched_trades=0,
                    total_trades=0,
                    match_rate=rule.confidence,  # 使用置信度作为默认匹配率
                    avg_score=rule.confidence,
                )
                for rule in rules
            ]

        scores = []
        for rule in rules:
            score = rule_match_score(rule, trades)
            scores.append(score)

        return scores

    def _compute_conflict_penalty(self, conflicts: ConflictDetection | None) -> float:
        """计算冲突扣分。

        基于冲突数量和严重程度计算扣分（0-1）。
        """
        if not conflicts or conflicts.total_conflicts == 0:
            return 0.0

        # 严重程度权重
        severity_weights = {
            "critical": 0.3,
            "major": 0.15,
            "minor": 0.05,
        }

        penalty = 0.0
        for conflict in conflicts.conflicts:
            weight = severity_weights.get(conflict.severity, 0.05)
            penalty += weight

        # 限制最大扣分为 1.0
        return min(1.0, penalty)

    async def run_incremental(
        self,
        request: AlignmentRequest,
        previous_result: AlignmentResult | None = None,
    ) -> AlignmentResult:
        """执行增量对齐分析（P3-025）。

        增量策略：
          1. 如果没有历史结果，执行完整分析
          2. 如果只有规则变化（无新交易），重新计算规则匹配和冲突
          3. 如果有新交易，只对增量交易进行分析，然后合并结果

        Args:
            request: 对齐分析请求
            previous_result: 上一次的分析结果（用于增量计算）

        Returns:
            更新后的对齐分析结果
        """
        # 如果没有历史结果，执行完整分析
        if not previous_result:
            return await self.run(request)

        # 如果没有新交易，返回历史结果
        if not request.trades:
            return previous_result

        # 增量分析策略
        result = AlignmentResult(trader_id=request.trader_id)
        result.rules_analyzed = len(request.rules)

        # 1. 增量规则匹配评分
        # 对于增量场景，我们重新计算所有规则匹配（因为交易集合变了）
        result.rule_match_scores = self._compute_rule_match_scores(
            request.rules,
            request.trades,
        )

        # 2. 行为适配度评分（规则变了，需要重新计算）
        if request.profile and request.rules:
            result.behavior_fit = behavior_fit_score(
                request.profile,
                request.rules,
            )

        # 3. 增量冲突检测
        # 检查规则是否变化
        rules_changed = self._check_rules_changed(
            previous_result.rule_match_scores,
            request.rules,
        )

        if rules_changed:
            # 规则变了，重新检测冲突
            result.conflicts = detect_conflicts(
                request.rules,
                request.trades,
            )
        else:
            # 规则没变，复用之前的冲突检测结果
            result.conflicts = previous_result.conflicts

        # 4. 计算覆盖率（基于新交易）
        coverage_result = compute_rule_coverage(
            request.trades,
            request.rules,
        )
        result.unmatched_trades = detect_unmatched_trades(
            request.trades,
            request.rules,
        ).unmatched_trades

        # 5. 计算准确度
        accuracy_scores = None
        accuracy_result = compute_rule_accuracy(
            request.trades,
            request.rules,
        )
        accuracy_scores = accuracy_result.rule_accuracy

        # 6. 综合可信度评分
        weights = request.weights or self.default_weights
        result.detailed_score = detailed_confidence_scoring(
            trader_id=request.trader_id,
            rule_match_scores=result.rule_match_scores,
            rule_accuracy_scores=accuracy_scores,
            behavior_fit=result.behavior_fit,
            coverage_score=coverage_result.overall_coverage,
            conflict_penalty=self._compute_conflict_penalty(result.conflicts),
            weights=weights,
        )

        # 7. 生成优化建议
        if request.include_suggestions and result.conflicts:
            result.suggestions = generate_optimization_suggestions(result.conflicts)

        # 8. 生成文本报告
        result.text_report = generate_text_report(
            trader_id=request.trader_id,
            rules=request.rules,
            trades=request.trades,
            rule_match_scores=result.rule_match_scores,
            conflicts=result.conflicts,
            detailed_score=result.detailed_score,
            include_suggestions=request.include_suggestions,
        )

        # 9. 更新元数据
        result.trades_analyzed = len(request.trades)
        result.cached = False  # 增量结果不自动缓存

        return result

    def _check_rules_changed(
        self,
        previous_scores: list[RuleMatchScore],
        current_rules: list[StrategyRule],
    ) -> bool:
        """检查规则是否发生变化。

        Args:
            previous_scores: 上一次的评分
            current_rules: 当前的规则

        Returns:
            是否变化
        """
        if len(previous_scores) != len(current_rules):
            return True

        # 比较规则 ID 和置信度
        prev_rules = {(s.rule_id, s.avg_score) for s in previous_scores}
        curr_rules = {(r.rule_id, r.confidence) for r in current_rules}

        return prev_rules != curr_rules

    def get_cached_result(self, trader_id: str) -> AlignmentResult | None:
        """获取缓存的对齐分析结果。

        Args:
            trader_id: 交易员 ID

        Returns:
            缓存的结果，如果没有则返回 None
        """
        if not self.cache:
            return None

        cached = self.cache.get_latest_version(trader_id)
        if not cached:
            return None

        version = self.cache.load_version(trader_id, cached.version_id)
        if not version:
            return None

        # 构建简化结果（从缓存恢复）
        result = AlignmentResult(trader_id=trader_id)
        result.cached = True

        # 恢复评分数据
        if version.score_snapshot:
            result.detailed_score = DetailedConfidenceScore(
                trader_id=trader_id,
                overall_score=version.score_snapshot.get("overall_score", 0.0),
                grade=version.score_snapshot.get("grade", "D"),
            )

        # 恢复冲突数据
        if version.conflict_snapshot:
            result.conflicts = ConflictDetection(
                trader_id=trader_id,
                total_conflicts=version.conflict_snapshot.get("total_conflicts", 0),
                by_type=version.conflict_snapshot.get("by_type", {}),
                by_severity=version.conflict_snapshot.get("by_severity", {}),
            )

        return result
