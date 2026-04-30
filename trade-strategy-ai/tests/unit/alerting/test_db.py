"""AlertHistory DB 测试（S7-007）。"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from src.alerting.models import AlertEvent, AlertLevel


class TestAlertHistoryRepository:
    """AlertHistoryRepository 测试。"""

    @pytest.mark.asyncio
    async def test_insert_saves_alert(self):
        """insert() 正确保存告警到 DB"""
        from src.alerting.db import AlertHistory, AlertHistoryRepository

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = AlertHistoryRepository()
        record = await repo.insert(
            session=mock_session,
            alert_id="test-alert-001",
            level="WARNING",
            title="测试告警",
            message="测试内容",
            channel="dingtalk",
            tags=["test"],
            alert_metadata={"slot": "17-30"},
            aggregation_key="abc123",
            aggregated_count=3,
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert record.alert_id == "test-alert-001"
        assert record.level == "WARNING"

    @pytest.mark.asyncio
    async def test_list_history_returns_empty(self):
        """无数据时返回空列表"""
        from src.alerting.db import AlertHistoryRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = AlertHistoryRepository()
        rows = await repo.list_history(session=mock_session, limit=10)

        assert rows == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_to_sent(self):
        """更新状态为 sent"""
        from src.alerting.db import AlertHistory, AlertHistoryRepository

        mock_record = MagicMock(spec=AlertHistory)
        mock_record.status = "pending"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        repo = AlertHistoryRepository()
        record = await repo.update_status(
            session=mock_session,
            record_id=uuid.uuid4(),
            status="sent",
        )

        assert record.status == "sent"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_record(self):
        """按 ID 查询返回记录"""
        from src.alerting.db import AlertHistory, AlertHistoryRepository

        test_id = uuid.uuid4()
        mock_record = MagicMock(spec=AlertHistory)
        mock_record.id = test_id
        mock_record.alert_id = "alert-001"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_session.execute.return_value = mock_result

        repo = AlertHistoryRepository()
        record = await repo.get_by_id(session=mock_session, record_id=test_id)

        assert record.id == test_id
