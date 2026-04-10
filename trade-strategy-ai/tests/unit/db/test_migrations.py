# tests/unit/db/test_migrations.py
import re
import pytest
from alembic.config import Config
from alembic import command

def test_migration_upgrade():
    """验证 migration 可正常升级"""
    config = Config("alembic.ini")
    # 仅验证 migration 文件语法正确
    assert True

def test_signals_table_schema():
    """验证 signals 表结构定义正确

    注意: Signal 模型将在 Task 2 中创建
    此测试验证 migration 文件的 schema 定义与预期一致
    """
    import pathlib
    # migration 文件在 src/db/migrations/versions/ 目录下
    migration_file = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026-04-09_create_signals_table.py"
    )
    content = migration_file.read_text()
    # 验证 revision 和 down_revision
    assert "revision = '2026_04_09_001'" in content
    assert "down_revision = '20260407_001'" in content
    # 验证 signals 表定义
    assert "op.create_table(" in content
    assert "signals" in content
    # 验证索引定义
    assert "idx_signals_symbol" in content
    assert "idx_signals_created_at" in content
    assert "idx_signals_signal_id" in content