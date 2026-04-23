"""snapshot_tasks 测试。"""

import tempfile
from datetime import date
from src.pipeline.tasks.snapshot_tasks import (
    handle_hot_topics_snapshot,
    handle_topic_constituents_snapshot,
    handle_strong_symbols_snapshot,
    _build_provider,
)


class TestSnapshotTasks:
    """测试候选池快照 pipeline handlers。"""

    def test_build_provider_returns_none_when_no_kaipan_config(self):
        """无 kaipan 配置时返回 None。"""
        from src.pipeline.tasks.snapshot_tasks import _build_provider

        class FakeConfig:
            class _Empty:
                pass
            kaipan = None

        result = _build_provider(FakeConfig())
        assert result is None

    def test_hot_topics_snapshot_skips_without_provider(self):
        """无 provider 时不抛异常，正常返回。"""
        import asyncio
        from src.pipeline.tasks.snapshot_tasks import handle_hot_topics_snapshot

        class FakeConfig:
            class _Kaipan:
                pass
            kaipan = None

        async def run():
            await handle_hot_topics_snapshot(
                {"trade_date": "2026-04-23", "slot": "17-30"},
                config=FakeConfig(),
            )

        asyncio.run(run())  # 不抛异常

    def test_hot_topics_snapshot_with_mock_provider(self):
        """有 mock provider 时正确保存快照。"""
        import asyncio
        from src.pipeline.tasks.snapshot_tasks import handle_hot_topics_snapshot, _build_provider

        with tempfile.TemporaryDirectory() as tmpdir:
            # 先保存一个已有快照（hot_topics 已存在，force=False）
            from src.market_universe.schemas import MarketUniverse, HotTopicsPayload
            from src.market_universe.hot_topics_builder import HotTopicsBuilder
            from datetime import datetime

            mock_provider = _MockHotTopicsProvider()
            builder = HotTopicsBuilder()
            hot = builder.build(mock_provider.fetch_hot_topics(trade_date=date(2026, 4, 23), slot="17-30"))

            existing_mu = MarketUniverse(
                trade_date="2026-04-23",
                slot="17-30",
                hot_topics=hot,
            )

            from src.market_universe.snapshot_service import SnapshotService
            svc = SnapshotService(base_dir=tmpdir)
            svc.save(existing_mu)

            # 注入 mock provider
            class FakeConfig:
                class _Kaipan:
                    pass
                kaipan = _Kaipan()

            async def run():
                # 用 mock provider 注入
                import src.pipeline.tasks.snapshot_tasks as st
                original = st._build_provider
                st._build_provider = lambda cfg: _MockHotTopicsProvider()

                try:
                    await handle_hot_topics_snapshot(
                        {"trade_date": "2026-04-23", "slot": "17-30"},
                        config=FakeConfig(),
                    )
                finally:
                    st._build_provider = original

            asyncio.run(run())

    def test_topic_constituents_snapshot_skips_without_provider(self):
        """无 provider 时不抛异常。"""
        import asyncio
        from src.pipeline.tasks.snapshot_tasks import handle_topic_constituents_snapshot

        class FakeConfig:
            class _Kaipan:
                pass
            kaipan = None

        async def run():
            await handle_topic_constituents_snapshot(
                {"trade_date": "2026-04-23", "slot": "17-30"},
                config=FakeConfig(),
            )

        asyncio.run(run())

    def test_strong_symbols_snapshot_skips_without_provider(self):
        """无 provider 时不抛异常。"""
        import asyncio
        from src.pipeline.tasks.snapshot_tasks import handle_strong_symbols_snapshot

        class FakeConfig:
            class _Kaipan:
                pass
            kaipan = None

        async def run():
            await handle_strong_symbols_snapshot(
                {"trade_date": "2026-04-23", "slot": "17-30"},
                config=FakeConfig(),
            )

        asyncio.run(run())

    def test_snapshot_task_requires_trade_date(self):
        """缺少 trade_date 时抛出 ValueError。"""
        import asyncio
        from src.pipeline.tasks.snapshot_tasks import handle_hot_topics_snapshot

        class FakeConfig:
            class _Kaipan:
                pass
            kaipan = _Kaipan()

        async def run():
            await handle_hot_topics_snapshot(
                {"slot": "17-30"},  # 缺少 trade_date
                config=FakeConfig(),
            )

        try:
            asyncio.run(run())
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "trade_date is required" in str(e)


class _MockHotTopicsProvider:
    """模拟 HotTopicsProvider。"""

    def fetch_hot_topics(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "hot_topics",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "topics": [
                {"kind": "concept", "topic_id": "BK0001", "topic_name": "AI", "score": 85.0},
            ],
            "sources": ["board_strength"],
        }