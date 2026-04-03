from src.models.article_metadata import ArticleMetadata
from src.models.blog_article import BlogArticle
from src.models.market_data import MarketData
from src.models.trade_log import TradeLog


def test_blog_article_table_metadata() -> None:
    indexes = {index.name for index in BlogArticle.__table__.indexes}
    assert "ix_blog_articles_source_published_at" in indexes
    assert "ix_blog_articles_author_published_at" in indexes
    assert BlogArticle.__table__.c.source_url.unique is True


def test_trade_log_constraints_present() -> None:
    constraint_names = {constraint.name for constraint in TradeLog.__table__.constraints}
    assert "ck_trade_logs_quantity_positive" in constraint_names
    assert "ck_trade_logs_side_allowed" in constraint_names


def test_market_data_unique_constraint_present() -> None:
    constraint_names = {constraint.name for constraint in MarketData.__table__.constraints}
    assert "uq_market_data_symbol_market_timeframe_traded_at_source" in constraint_names


def test_article_metadata_one_to_one() -> None:
    assert ArticleMetadata.__table__.c.article_id.unique is True
