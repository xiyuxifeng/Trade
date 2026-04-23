"""
Alignment Agent — P3-022~P3-025（已冻结）。

⚠️ 已冻结：AlignmentAgent 主线职责已停止开发。
- 本模块不再作为当前核心交付路径的一部分。
- 目录保留为历史参考，不继续投入主线开发。
- 后续若有需求，应在 evaluation / backtest / strategy_library 模块中实现。

主要类和函数：
  - AlignmentAgent: 对齐分析 Agent 主类（已冻结）
  - AlignmentRequest: 对齐分析请求（已冻结）
  - AlignmentResult: 对齐分析结果（已冻结）
  - AlignmentStorage: 持久化存储（已冻结）
"""

from src.agents.alignment_agent.agent import (
    AlignmentAgent,
    AlignmentRequest,
    AlignmentResult,
    AlignmentStorage,
)

__all__ = [
    "AlignmentAgent",
    "AlignmentRequest",
    "AlignmentResult",
    "AlignmentStorage",
]
