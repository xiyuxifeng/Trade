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
        import json
        from pathlib import Path
        from src.pipeline.tasks.snapshot_tasks import handle_hot_topics_snapshot, _build_provider

        with tempfile.TemporaryDirectory() as tmpdir:
            # 先保存一个已有快照（hot_topics 已存在，force=False）
            from datetime import datetime
            from src.market_universe.schemas import HotTopic, HotTopicsPayload, MarketUniverse

            existing_mu = MarketUniverse(
                trade_date="2026-04-23",
                slot="17-30",
                hot_topics=HotTopicsPayload(
                    trade_date="2026-04-23",
                    slot="17-30",
                    topics=[HotTopic(kind="concept", topic_id="BK0001", topic_name="AI", score=85.0)],
                    sources=["board_strength"],
                    fetched_at=datetime(2026, 4, 23, 17, 30),
                ),
            )

            from src.market_universe.snapshot_service import SnapshotService
            svc = SnapshotService(base_dir=tmpdir)
            svc.save(existing_mu)

            normalized_path = Path(tmpdir) / "data" / "kaipan" / "snapshots" / "hot_topics" / "2026-04-23_17-30"
            normalized_path.mkdir(parents=True, exist_ok=True)
            (normalized_path / "hot_topics.json").write_text(
                json.dumps(
                    {
                        "meta": {"trade_date": "2026-04-23", "slot": "17-30"},
                        "concept": [
                            {"topic_id": "BK0001", "topic_name": "AI", "score": 85.0},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            # 注入 mock provider
            class FakeConfig:
                class _Kaipan:
                    pass
                kaipan = _Kaipan()

            async def run():
                # 用 mock provider 注入
                import src.pipeline.tasks.snapshot_tasks as st
                original = st._build_provider
                original_resolve = st.resolve_project_path
                original_snapshot_service = st.SnapshotService
                st._build_provider = lambda cfg, offline=False: _MockHotTopicsProvider()
                st.resolve_project_path = lambda path: Path(tmpdir) / path
                st.SnapshotService = lambda: svc

                try:
                    await handle_hot_topics_snapshot(
                        {"trade_date": "2026-04-23", "slot": "17-30"},
                        config=FakeConfig(),
                    )
                finally:
                    st._build_provider = original
                    st.resolve_project_path = original_resolve
                    st.SnapshotService = original_snapshot_service

            asyncio.run(run())

    def test_hot_topics_snapshot_prefers_normalized_snapshot(self, tmp_path, monkeypatch):
        """存在标准化快照时，hot_topics 应优先消费标准化产物。"""
        import asyncio
        import json
        from pathlib import Path

        import src.pipeline.tasks.snapshot_tasks as st

        normalized_path = tmp_path / "data" / "kaipan" / "snapshots" / "hot_topics" / "2026-04-23_17-30"
        normalized_path.mkdir(parents=True, exist_ok=True)
        (normalized_path / "hot_topics.json").write_text(
            json.dumps(
                {
                    "meta": {"trade_date": "2026-04-23", "slot": "17-30"},
                    "concept": [
                        {"topic_id": "BK0001", "topic_name": "AI", "score": 85.0, "increase_pct": 5.2},
                    ],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(st, "resolve_project_path", lambda path: Path(tmp_path) / path)

        class _FakeProvider:
            def fetch_hot_topics(self, **kwargs):
                raise AssertionError("provider should not be called when normalized snapshot exists")

        class _FakeSnapshotService:
            def __init__(self):
                self.saved = None

            def load(self, trade_date: str, slot: str):
                return None

            def save(self, market_universe):
                self.saved = market_universe

        fake_snapshot_service = _FakeSnapshotService()
        monkeypatch.setattr(st, "SnapshotService", lambda: fake_snapshot_service)
        monkeypatch.setattr(st, "_build_provider", lambda cfg, offline=False: _FakeProvider())

        class FakeConfig:
            class _Kaipan:
                pass

            kaipan = _Kaipan()

        async def run():
            await handle_hot_topics_snapshot(
                {"trade_date": "2026-04-23", "slot": "17-30"},
                config=FakeConfig(),
            )

        asyncio.run(run())

        assert fake_snapshot_service.saved is not None
        assert fake_snapshot_service.saved.hot_topics is not None
        assert fake_snapshot_service.saved.hot_topics.trade_date == "2026-04-23"
        assert fake_snapshot_service.saved.hot_topics.slot == "17-30"
        assert fake_snapshot_service.saved.hot_topics.topics[0].kind == "concept"
        assert fake_snapshot_service.saved.hot_topics.topics[0].topic_id == "BK0001"

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
