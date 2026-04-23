def test_market_universe_package_importable():
    """market_universe 包应可导入。"""
    from src.market_universe import schemas
    assert hasattr(schemas, "HotTopic")
