"""snapshot_service 测试。"""

from datetime import datetime
from src.market_universe.schemas import MarketUniverse, HotTopicsPayload, TopicConstituentsPayload, StrongSymbolsPayload, HotTopic, TopicConstituent, StrongSymbol


class TestSnapshotService:
    """SnapshotService 统一管理候选池快照的写入和读取。"""

    def test_save_and_load_market_universe(self):
        """保存完整 MarketUniverse 后可正常读取。"""
        from src.market_universe.snapshot_service import SnapshotService
        from src.common.paths import project_root

        service = SnapshotService()
        assert service.base_dir == project_root() / "data" / "market_universe" / "snapshots"

        mu = MarketUniverse(
            trade_date="2026-04-23",
            slot="17-30",
            hot_topics=HotTopicsPayload(
                trade_date="2026-04-23",
                slot="17-30",
                topics=[HotTopic(kind="concept", topic_id="BK0001", topic_name="AI", score=85.0)],
                sources=["board_strength"],
                fetched_at=datetime.now(),
            ),
            topic_constituents=TopicConstituentsPayload(
                trade_date="2026-04-23",
                slot="17-30",
                constituents=[TopicConstituent(kind="stock_sector_v2", topic_id="ZS001", topic_name="AI")],
                sources=["stock_sector_v2"],
            ),
            strong_symbols=StrongSymbolsPayload(
                trade_date="2026-04-23",
                slot="17-30",
                symbols=[StrongSymbol(kind="strong_fengkou", symbol="000001", name="平安银行", strength_score=88.0)],
                sources=["strong_fengkou"],
            ),
        )

        service.save(mu)
        loaded = service.load(trade_date="2026-04-23", slot="17-30")

        assert loaded is not None
        assert loaded.trade_date == "2026-04-23"
        assert loaded.hot_topics is not None
        assert len(loaded.hot_topics.topics) == 1
        assert loaded.hot_topics.topics[0].topic_name == "AI"

        assert loaded.topic_constituents is not None
        assert len(loaded.topic_constituents.constituents) == 1

        assert loaded.strong_symbols is not None
        assert len(loaded.strong_symbols.symbols) == 1
        assert loaded.strong_symbols.symbols[0].strength_score == 88.0

    def test_save_and_load_partial_market_universe(self):
        """只包含部分 payload 的 MarketUniverse 也可正常存取。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()

        mu = MarketUniverse(
            trade_date="2026-04-23",
            slot="09-25",
            hot_topics=HotTopicsPayload(
                trade_date="2026-04-23",
                slot="09-25",
                topics=[],
                sources=["board_strength"],
            ),
            # topic_constituents 和 strong_symbols 均为 None
        )

        service.save(mu)
        loaded = service.load(trade_date="2026-04-23", slot="09-25")

        assert loaded is not None
        assert loaded.hot_topics is not None
        assert len(loaded.hot_topics.topics) == 0
        assert loaded.topic_constituents is None
        assert loaded.strong_symbols is None

    def test_load_returns_none_when_not_found(self):
        """不存在的快照应返回 None。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()
        result = service.load(trade_date="2099-01-01", slot="99-99")

        assert result is None

    def test_save_with_metadata(self):
        """保存时 metadata 应正确保留。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()

        mu = MarketUniverse(
            trade_date="2026-04-23",
            slot="17-30",
            metadata={"provider": "kaipan", "version": "1.0"},
        )

        service.save(mu)
        loaded = service.load(trade_date="2026-04-23", slot="17-30")

        assert loaded is not None
        assert loaded.metadata.get("provider") == "kaipan"
        assert loaded.metadata.get("version") == "1.0"

    def test_list_snapshots(self, tmp_path):
        """列出指定日期范围的快照。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService(base_dir=str(tmp_path))

        # 保存多个快照
        service.save(MarketUniverse(trade_date="2026-04-20", slot="17-30"))
        service.save(MarketUniverse(trade_date="2026-04-21", slot="17-30"))
        service.save(MarketUniverse(trade_date="2026-04-22", slot="17-30"))
        service.save(MarketUniverse(trade_date="2026-04-23", slot="17-30"))

        snapshots = service.list_snapshots(trade_date_start="2026-04-21", trade_date_end="2026-04-22")

        assert len(snapshots) == 2
        dates = [s.trade_date for s in snapshots]
        assert "2026-04-21" in dates
        assert "2026-04-22" in dates
        assert "2026-04-23" not in dates

    def test_delete_snapshot(self):
        """删除指定快照。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()

        mu = MarketUniverse(trade_date="2026-04-23", slot="17-30")
        service.save(mu)

        # 删除
        deleted = service.delete(trade_date="2026-04-23", slot="17-30")
        assert deleted is True

        # 再次读取应为 None
        loaded = service.load(trade_date="2026-04-23", slot="17-30")
        assert loaded is None

    def test_delete_nonexistent_returns_false(self):
        """删除不存在的快照应返回 False。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()
        deleted = service.delete(trade_date="2099-01-01", slot="99-99")

        assert deleted is False

    def test_save_overwrites_existing(self):
        """重复保存同一 key 应覆盖。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService()

        mu1 = MarketUniverse(
            trade_date="2026-04-23",
            slot="17-30",
            hot_topics=HotTopicsPayload(
                trade_date="2026-04-23",
                slot="17-30",
                topics=[HotTopic(kind="concept", topic_id="BK0001", topic_name="AI", score=80.0)],
                sources=["board_strength"],
            ),
        )
        mu2 = MarketUniverse(
            trade_date="2026-04-23",
            slot="17-30",
            hot_topics=HotTopicsPayload(
                trade_date="2026-04-23",
                slot="17-30",
                topics=[HotTopic(kind="concept", topic_id="BK0002", topic_name="芯片", score=90.0)],
                sources=["board_strength"],
            ),
        )

        service.save(mu1)
        service.save(mu2)  # 覆盖

        loaded = service.load(trade_date="2026-04-23", slot="17-30")
        assert len(loaded.hot_topics.topics) == 1
        assert loaded.hot_topics.topics[0].topic_name == "芯片"
        assert loaded.hot_topics.topics[0].score == 90.0

    def test_load_returns_none_for_corrupted_json(self, tmp_path):
        """损坏的快照文件应被跳过，不应让读取流程直接抛异常。"""
        from src.market_universe.snapshot_service import SnapshotService

        service = SnapshotService(base_dir=str(tmp_path))
        bad_path = tmp_path / "2026-04-23" / "17-30.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{not-valid-json", encoding="utf-8")

        loaded = service.load(trade_date="2026-04-23", slot="17-30")

        assert loaded is None
