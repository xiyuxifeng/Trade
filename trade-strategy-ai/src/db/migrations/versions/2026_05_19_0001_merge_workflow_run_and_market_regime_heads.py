"""merge workflow run and market regime heads

Revision ID: 2026_05_19_0001
Revises: 2026_05_17_0002, 2026_05_18_0001
Create Date: 2026-05-19
"""
from __future__ import annotations

from typing import Sequence, Union


revision: str = "2026_05_19_0001"
down_revision: Union[str, tuple[str, ...], None] = ("2026_05_17_0002", "2026_05_18_0001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """合并两条并行迁移分支，不执行额外 DDL。"""
    pass


def downgrade() -> None:
    """回滚时仅拆分版本树，不执行额外 DDL。"""
    pass
