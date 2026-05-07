from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.models.data_audit_event import DataAuditEvent
from src.models.ohlcv_bar import OHLCVBar
from src.models.trade_log import TradeLog


def test_blog_article_table_metadata() -> None:
    indexes = {index.name for index in BlogArticle.__table__.indexes}
    assert "ix_blog_articles_source_published_at" in indexes
    assert "ix_blog_articles_author_published_at" in indexes
    assert "ix_blog_articles_crawled_at" in indexes
    assert BlogArticle.__table__.c.source_url.unique is True


def test_trade_log_constraints_present() -> None:
    constraint_names = {constraint.name for constraint in TradeLog.__table__.constraints}
    assert "ck_trade_logs_quantity_positive" in constraint_names
    assert "ck_trade_logs_side_allowed" in constraint_names


def test_ohlcv_bar_unique_constraint_present() -> None:
    constraint_names = {constraint.name for constraint in OHLCVBar.__table__.constraints}
    assert "uq_ohlcv_symbol_date" in constraint_names


def test_article_metadata_one_to_one() -> None:
    constraint_names = {constraint.name for constraint in ArticleMetadata.__table__.constraints}
    assert "uq_article_metadata_article_id_version" in constraint_names


def test_data_audit_event_table_metadata() -> None:
    indexes = {index.name for index in DataAuditEvent.__table__.indexes}
    assert "ix_data_audit_events_created_at" in indexes
    assert "ix_data_audit_events_event_type_created_at" in indexes
