from __future__ import annotations


def test_config_profile_model_defines_expected_columns() -> None:
    """ConfigProfile 模型应定义正式 Profile 事实源字段。"""
    from src.models.config_profile import ConfigProfile

    columns = ConfigProfile.__table__.columns.keys()

    assert ConfigProfile.__tablename__ == "config_profiles"
    assert "profile_id" in columns
    assert "name" in columns
    assert "environment" in columns
    assert "version" in columns
    assert "sections" in columns
    assert "secret_refs" in columns
    assert "validation_status" in columns
    assert "created_by" in columns
    assert "archived_at" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

