"""Evaluation 模块：盘后评估、学习闭环与 ranking。

职责：
- 生成 Evidence Pack（交易想法 + 上下文 + 市场快照）
- 失败归因分类
- 盘后复盘服务
- 策略 ranking
"""

from src.evaluation.evidence_pack import EvidencePack

__all__ = ["EvidencePack"]
