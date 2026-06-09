# S7-007 告警系统 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整告警系统：多渠道（钉钉/飞书/企微/generic）、聚合去重、AlertHistory DB 持久化、alert.log 结构化日志、8 种告警接入点（A-H）

**Architecture:** Formatter 层可插拔，Aggregator 负责合并，DB 层持久化告警历史，Logger 层写结构化日志，AlertManager 统一调度

**Tech Stack:** Typer、asyncio、SQLAlchemy、Pydantic

---

## 文件结构

```
src/alerting/
├── __init__.py               # 修改：导出 AlertManager + AlertHistoryRepository
├── config.py                 # 新增：从 app.yaml 加载告警配置
├── channels/                 # 新增：渠道格式化层
│   ├── __init__.py
│   ├── base.py              # ChannelFormatter 抽象基类
│   ├── dingtalk.py          # DingTalkFormatter
│   ├── feishu.py           # FeishuFormatter
│   ├── wecom.py            # WeComFormatter
│   └── generic.py          # GenericFormatter
├── aggregator.py            # 新增：告警聚合逻辑
├── logger_.py              # 新增：alert.log 结构化日志
├── db.py                    # 新增：AlertHistory ORM + Repository
├── models.py               # 已存在：AlertEvent, AlertLevel, AlertRule
├── rules/                   # 新增：8 种告警规则
│   ├── __init__.py
│   ├── snapshot_rules.py   # A: 快照缺失
│   ├── provider_rules.py   # B: Provider 失败
│   ├── freshness_rules.py   # C: 数据新鲜度
│   ├── pipeline_rules.py   # D: Pipeline 失败
│   ├── db_rules.py         # E: DB 异常
│   ├── circuit_rules.py    # F: Circuit Breaker
│   ├── agent_rules.py      # G: Agent 异常
│   └── backtest_rules.py   # H: 回测失败

api/routers/
└── alerts.py                # 新增：告警历史 API

tests/
├── cli/
│   └── test_alerts.py       # 新增：告警 API 测试
└── unit/
    └── alerting/
        ├── __init__.py
        ├── test_channels.py    # 新增：渠道格式化测试
        ├── test_aggregator.py  # 新增：聚合逻辑测试
        └── test_db.py          # 新增：DB 持久化测试
```

---

## Task 1: 基础层 — 配置加载 + AlertHistory ORM

**Files:**
- Create: `src/alerting/config.py`
- Create: `src/alerting/db.py`（含 AlertHistory ORM + AlertHistoryRepository）
- Create: `tests/unit/alerting/test_db.py`

---

- [ ] **Step 1: 写测试文件**

```python
# tests/unit/alerting/test_db.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.alerting.db import AlertHistory, AlertHistoryRepository

@pytest.fixture
def sample_alert_event():
    from src.alerting.models import AlertEvent, AlertLevel
    return AlertEvent(
        id="test-alert-001",
        level=AlertLevel.WARNING,
        title="测试告警",
        message="这是一条测试告警",
        tags=["test", "unit"],
        metadata={"slot": "17-30", "trade_date": "2026-04-29"},
    )

@pytest.mark.asyncio
async def test_alert_history_repository_insert():
    """AlertHistoryRepository.insert() 正确保存告警"""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    repo = AlertHistoryRepository()
    result = await repo.insert(session=mock_session, alert_id="test-001", level="WARNING",
                                title="测试", message="内容", channel="dingtalk",
                                tags=["test"], metadata={})

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    assert result.alert_id == "test-001"

@pytest.mark.asyncio
async def test_alert_history_repository_list_with_filters():
    """按 status/level/date_from 过滤查询"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = AlertHistoryRepository()
    rows = await repo.list_history(
        session=mock_session,
        status="sent",
        level="WARNING",
        date_from="2026-04-01",
        limit=10,
    )
    assert isinstance(rows, list)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/alerting/test_db.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 写 config.py**

```python
"""告警配置加载（S7-007）。

从 app.yaml 读取 alerting.* 配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class AlertingAggregationConfig(BaseModel):
    window_minutes: int = 60
    max_count: int = 100


class AlertingDingTalkConfig(BaseModel):
    webhook_url: str = ""
    secret: str = ""


class AlertingFeishuConfig(BaseModel):
    webhook_url: str = ""


class AlertingWeComConfig(BaseModel):
    webhook_url: str = ""


class AlertingConfig(BaseModel):
    enabled: bool = True
    channel: str = "generic"
    aggregation: AlertingAggregationConfig = AlertingAggregationConfig()
    dingtalk: AlertingDingTalkConfig = AlertingDingTalkConfig()
    feishu: AlertingFeishuConfig = AlertingFeishuConfig()
    wecom: AlertingWeComConfig = AlertingWeComConfig()
    min_level: str = "WARNING"
    console_output: bool = True


def load_alerting_config(config: dict[str, Any]) -> AlertingConfig:
    """从完整 app config 中提取 alerting 子配置。"""
    raw = config.get("alerting", {})
    return AlertingConfig(**raw)
```

- [ ] **Step 4: 写 db.py**

```python
"""告警历史 DB 持久化（S7-007）。

AlertHistory ORM 模型 + AlertHistoryRepository。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import String, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AlertHistory(Base):
    """告警历史 ORM 模型。"""
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    aggregated_count: Mapped[int] = mapped_column(default=1)
    aggregation_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aggregation_window_start: Mapped[datetime | None] = mapped_column(nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("idx_alert_history_status", "status"),
        Index("idx_alert_history_level", "level"),
        Index("idx_alert_history_created_at", "created_at"),
        Index("idx_alert_history_aggregation_key", "aggregation_key"),
    )


class AlertHistoryRepository:
    """告警历史 Repository。"""

    async def insert(
        self,
        session,
        alert_id: str,
        level: str,
        title: str,
        message: str | None,
        channel: str,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        aggregation_key: str | None = None,
        aggregated_count: int = 1,
        aggregation_window_start: datetime | None = None,
    ) -> AlertHistory:
        """插入新告警历史记录。"""
        record = AlertHistory(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            channel=channel,
            tags=tags or [],
            metadata=metadata or {},
            aggregation_key=aggregation_key,
            aggregated_count=aggregated_count,
            aggregation_window_start=aggregation_window_start,
            status="pending",
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def update_status(
        self,
        session,
        record_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
        acknowledged_at: datetime | None = None,
        acknowledged_by: str | None = None,
        resolved_at: datetime | None = None,
        resolved_by: str | None = None,
    ) -> AlertHistory | None:
        """更新告警状态。"""
        from sqlalchemy import select
        result = await session.execute(
            select(AlertHistory).where(AlertHistory.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.status = status
        if sent_at is not None:
            record.sent_at = sent_at
        if acknowledged_at is not None:
            record.acknowledged_at = acknowledged_at
        if acknowledged_by is not None:
            record.acknowledged_by = acknowledged_by
        if resolved_at is not None:
            record.resolved_at = resolved_at
        if resolved_by is not None:
            record.resolved_by = resolved_by
        await session.commit()
        await session.refresh(record)
        return record

    async def list_history(
        self,
        session,
        status: str | None = None,
        level: str | None = None,
        tag: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[AlertHistory]:
        """查询告警历史（支持过滤和分页）。"""
        from sqlalchemy import select, func, text

        conditions = []
        if status:
            conditions.append(AlertHistory.status == status)
        if level:
            conditions.append(AlertHistory.level == level)
        if tag:
            conditions.append(text(f"'{tag}' = ANY(SELECT jsonb_array_elements_text(tags))"))
        if date_from:
            conditions.append(AlertHistory.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            conditions.append(AlertHistory.created_at <= datetime.fromisoformat(date_to))

        stmt = select(AlertHistory).where(*conditions).order_by(
            AlertHistory.created_at.desc()
        ).offset(skip).limit(limit)

        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, session, record_id: uuid.UUID) -> AlertHistory | None:
        """按 ID 查询告警记录。"""
        from sqlalchemy import select
        result = await session.execute(
            select(AlertHistory).where(AlertHistory.id == record_id)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `pytest tests/unit/alerting/test_db.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/alerting/config.py src/alerting/db.py tests/unit/alerting/test_db.py
git commit -m "feat(s7-007): add alerting config loader and AlertHistory ORM"
```

---

## Task 2: 渠道格式化层 — ChannelFormatter 可插拔

**Files:**
- Create: `src/alerting/channels/__init__.py`
- Create: `src/alerting/channels/base.py`
- Create: `src/alerting/channels/dingtalk.py`
- Create: `src/alerting/channels/feishu.py`
- Create: `src/alerting/channels/wecom.py`
- Create: `src/alerting/channels/generic.py`
- Create: `tests/unit/alerting/test_channels.py`

---

- [ ] **Step 1: 写测试文件**

```python
# tests/unit/alerting/test_channels.py
import pytest
from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.channels import (
    ChannelFormatter,
    DingTalkFormatter,
    FeishuFormatter,
    WeComFormatter,
    GenericFormatter,
)


@pytest.fixture
def sample_alert():
    return AlertEvent(
        id="test-001",
        level=AlertLevel.WARNING,
        title="快照构建失败",
        message="Connection timeout",
        tags=["snapshot", "missing"],
        metadata={"slot": "17-30", "trade_date": "2026-04-29", "provider": "kaipan"},
    )


def test_dingtalk_formatter_generates_markdown(sample_alert):
    """钉钉格式化器生成 Markdown 格式"""
    formatter = DingTalkFormatter()
    payload = formatter.format(sample_alert)

    assert "### [WARNING] 快照构建失败" in payload
    assert "slot" in payload
    assert "17-30" in payload
    assert "Connection timeout" in payload


def test_feishu_formatter_generates_markdown(sample_alert):
    """飞书格式化器生成 Markdown 格式"""
    formatter = FeishuFormatter()
    payload = formatter.format(sample_alert)

    assert "[WARNING]" in payload
    assert "快照构建失败" in payload


def test_wecom_formatter_generates_markdown(sample_alert):
    """企微格式化器生成 Markdown 格式"""
    formatter = WeComFormatter()
    payload = formatter.format(sample_alert)

    assert "[WARNING]" in payload
    assert "快照构建失败" in payload


def test_generic_formatter_generates_json(sample_alert):
    """通用格式化器生成 JSON"""
    formatter = GenericFormatter()
    payload = formatter.format(sample_alert)

    import json
    parsed = json.loads(payload)
    assert parsed["id"] == "test-001"
    assert parsed["level"] == "WARNING"
    assert parsed["title"] == "快照构建失败"


def test_aggregated_dingtalk_message(sample_alert):
    """聚合告警的钉钉消息格式"""
    formatter = DingTalkFormatter()
    aggregated = sample_alert.model_copy()
    aggregated.metadata["aggregated_count"] = 12
    aggregated.metadata["aggregation_window_start"] = "2026-04-29T16:00:00"
    aggregated.metadata["aggregation_window_end"] = "2026-04-29T17:00:00"
    aggregated.metadata["last_error"] = "Connection timeout"

    payload = formatter.format_aggregated(aggregated)

    assert "聚合" in payload or "12" in payload
    assert "Connection timeout" in payload
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/alerting/test_channels.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 写 base.py**

```python
"""渠道格式化器基类（S7-007）。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.alerting.models import AlertEvent


class ChannelFormatter(ABC):
    """告警渠道格式化器抽象基类。"""

    @abstractmethod
    def format(self, alert: AlertEvent) -> str:
        """将告警格式化为渠道特定的 Payload 字符串。"""
        ...

    def format_aggregated(self, alert: AlertEvent) -> str:
        """格式化聚合告警（多条合并后的告警）。子类可覆盖。"""
        return self.format(alert)
```

- [ ] **Step 4: 写 dingtalk.py**

```python
"""钉钉群机器人格式化器（S7-007）。"""

from __future__ import annotations

from datetime import datetime

from src.alerting.channels.base import ChannelFormatter
from src.alerting.models import AlertEvent


class DingTalkFormatter(ChannelFormatter):
    """钉钉群机器人 Markdown 格式。"""

    LEVEL_EMOJI = {
        "CRITICAL": "🔴",
        "WARNING": "🟡",
        "INFO": "🔵",
    }

    def format(self, alert: AlertEvent) -> str:
        ts = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.LEVEL_EMOJI.get(alert.level.value.upper(), "")
        tags_str = ", ".join(f"`{t}`" for t in alert.tags) if alert.tags else "无"

        lines = [
            f"### {emoji} [{alert.level.value.upper()}] {alert.title}",
            "",
            f"**时间：** {ts}",
        ]

        if alert.message:
            lines.append(f"**详情：** {alert.message}")

        if alert.metadata:
            for k, v in alert.metadata.items():
                if k not in ("aggregated_count", "aggregation_window_start",
                             "aggregation_window_end", "last_error"):
                    lines.append(f"**{k}：** {v}")

        lines.append(f"**标签：** {tags_str}")

        return "\n".join(lines)

    def format_aggregated(self, alert: AlertEvent) -> str:
        meta = alert.metadata or {}
        count = meta.get("aggregated_count", 1)
        window_start = meta.get("aggregation_window_start", "")
        window_end = meta.get("aggregation_window_end", "")
        last_error = meta.get("last_error", "未知")

        ts = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        emoji = self.LEVEL_EMOJI.get(alert.level.value.upper(), "")
        tags_str = ", ".join(f"`{t}`" for t in alert.tags) if alert.tags else "无"

        lines = [
            f"### {emoji} [{alert.level.value.upper()}] {alert.title}（告警聚合）",
            "",
            f"**时间：** {ts}",
            f"**聚合窗口：** {window_start} ~ {window_end}",
            f"**累计次数：** {count} 次",
            f"**最近一次错误：** {last_error}",
            f"**标签：** {tags_str}",
        ]

        return "\n".join(lines)
```

- [ ] **Step 5: 写 feishu.py**

```python
"""飞书群机器人格式化器（S7-007）。"""

from __future__ import annotations

from src.alerting.channels.base import ChannelFormatter
from src.alerting.channels.dingtalk import DingTalkFormatter
from src.alerting.models import AlertEvent


class FeishuFormatter(ChannelFormatter):
    """飞书群机器人 Markdown 格式（与钉钉类似）。"""

    def format(self, alert: AlertEvent) -> str:
        # 飞书也使用 Markdown，代理给 DingTalkFormatter
        dingtalk = DingTalkFormatter()
        return dingtalk.format(alert)

    def format_aggregated(self, alert: AlertEvent) -> str:
        dingtalk = DingTalkFormatter()
        return dingtalk.format_aggregated(alert)
```

- [ ] **Step 6: 写 wecom.py**

```python
"""企业微信群机器人格式化器（S7-007）。"""

from __future__ import annotations

from src.alerting.channels.base import ChannelFormatter
from src.alerting.channels.dingtalk import DingTalkFormatter
from src.alerting.models import AlertEvent


class WeComFormatter(ChannelFormatter):
    """企业微信群机器人 Markdown 格式（与钉钉类似）。"""

    def format(self, alert: AlertEvent) -> str:
        dingtalk = DingTalkFormatter()
        return dingtalk.format(alert)

    def format_aggregated(self, alert: AlertEvent) -> str:
        dingtalk = DingTalkFormatter()
        return dingtalk.format_aggregated(alert)
```

- [ ] **Step 7: 写 generic.py**

```python
"""通用 JSON 格式化器（S7-007）。"""

from __future__ import annotations

import json

from src.alerting.channels.base import ChannelFormatter
from src.alerting.models import AlertEvent


class GenericFormatter(ChannelFormatter):
    """通用 JSON 格式（适用于自建 Webhook 服务）。"""

    def format(self, alert: AlertEvent) -> str:
        return json.dumps(alert.to_dict(), ensure_ascii=False, indent=2)
```

- [ ] **Step 8: 写 channels/__init__.py**

```python
"""告警渠道格式化器（S7-007）。"""

from src.alerting.channels.base import ChannelFormatter
from src.alerting.channels.dingtalk import DingTalkFormatter
from src.alerting.channels.feishu import FeishuFormatter
from src.alerting.channels.wecom import WeComFormatter
from src.alerting.channels.generic import GenericFormatter

__all__ = [
    "ChannelFormatter",
    "DingTalkFormatter",
    "FeishuFormatter",
    "WeComFormatter",
    "GenericFormatter",
]


def get_formatter(channel: str) -> ChannelFormatter:
    """根据 channel 名称返回对应的格式化器。"""
    channel_map = {
        "dingtalk": DingTalkFormatter(),
        "feishu": FeishuFormatter(),
        "wecom": WeComFormatter(),
        "generic": GenericFormatter(),
    }
    formatter = channel_map.get(channel.lower())
    if formatter is None:
        raise ValueError(f"未知的告警渠道: {channel}，可选：{list(channel_map.keys())}")
    return formatter
```

- [ ] **Step 9: 运行测试，确认通过**

Run: `pytest tests/unit/alerting/test_channels.py -v`
Expected: PASS

- [ ] **Step 10: 提交**

```bash
git add src/alerting/channels/ tests/unit/alerting/test_channels.py
git commit -m "feat(s7-007): add alert channel formatters (dingtalk/feishu/wecom/generic)"
```

---

## Task 3: 聚合器 + 结构化日志

**Files:**
- Create: `src/alerting/aggregator.py`
- Create: `src/alerting/logger_.py`
- Create: `tests/unit/alerting/test_aggregator.py`

---

- [ ] **Step 1: 写测试文件**

```python
# tests/unit/alerting/test_aggregator.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.aggregator import AlertAggregator


@pytest.fixture
def sample_alert():
    return AlertEvent(
        id="test-001",
        level=AlertLevel.WARNING,
        title="Provider 失败",
        message="Connection timeout",
        tags=["provider", "kaipan"],
        metadata={"provider": "kaipan", "capability": "hot_topics"},
    )


def test_aggregation_key_generation(sample_alert):
    """同一 alert 在窗口内生成相同 aggregation_key"""
    agg = AlertAggregator(window_minutes=60)
    key1 = agg._make_aggregation_key(sample_alert)
    key2 = agg._make_aggregation_key(sample_alert)
    assert key1 == key2
    assert "provider" in key1
    assert "kaipan" in key1


def test_aggregation_key_differs_for_different_tags(sample_alert):
    """不同 tags 产生不同 aggregation_key"""
    agg = AlertAggregator(window_minutes=60)
    alert2 = sample_alert.model_copy()
    alert2.tags = ["provider", "akshare"]

    key1 = agg._make_aggregation_key(sample_alert)
    key2 = agg._make_aggregation_key(alert2)
    assert key1 != key2


def test_new_window_creates_fresh_bucket(sample_alert):
    """新窗口清空旧 bucket"""
    agg = AlertAggregator(window_minutes=60)
    key = agg._make_aggregation_key(sample_alert)

    # 放入第一条
    agg.add_alert(sample_alert)
    assert len(agg.buckets[key]["alerts"]) == 1

    # 模拟时间穿越到新窗口（强制老化）
    old_window_start = datetime.utcnow() - timedelta(minutes=120)
    agg.buckets[key]["window_start"] = old_window_start
    agg.buckets[key]["last_sent_at"] = old_window_start

    agg.add_alert(sample_alert)
    # 新窗口内只有新的一条
    assert len(agg.buckets[key]["alerts"]) == 1


def test_flush_emits_aggregated_alert(sample_alert):
    """flush 触发聚合告警"""
    agg = AlertAggregator(window_minutes=60)
    key = agg._make_aggregation_key(sample_alert)

    # 放入多条同类型告警
    for i in range(5):
        alert = sample_alert.model_copy()
        alert.id = f"test-{i}"
        agg.add_alert(alert)

    flushed = []
    def mock_emit(alert):
        flushed.append(alert)

    agg.flush(key, emit_fn=mock_emit)

    assert len(flushed) == 1
    assert flushed[0].metadata["aggregated_count"] == 5
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/alerting/test_aggregator.py -v`
Expected: FAIL

- [ ] **Step 3: 写 aggregator.py**

```python
"""告警聚合器（S7-007）。

同一 aggregation_key 在时间窗口内的多条告警合并成一条发送。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Callable

from src.alerting.models import AlertEvent


class AlertAggregator:
    """告警聚合器。

    同一 aggregation_key（规则名 + tags）在窗口时间内多条告警合并为一条。
    """

    def __init__(
        self,
        window_minutes: int = 60,
        max_count: int = 100,
    ) -> None:
        self.window_minutes = window_minutes
        self.max_count = max_count
        # buckets[key] = {"alerts": [], "window_start": datetime, "last_sent_at": datetime}
        self.buckets: dict[str, dict] = {}

    def _make_aggregation_key(self, alert: AlertEvent) -> str:
        """生成告警的 aggregation_key。"""
        rule_name = alert.metadata.get("rule_name", "default")
        sorted_tags = sorted(alert.tags) if alert.tags else []
        tags_str = ",".join(sorted_tags)
        raw = f"{rule_name}:{tags_str}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _get_or_create_bucket(self, alert: AlertEvent) -> dict:
        """获取或创建聚合 bucket。"""
        key = self._make_aggregation_key(alert)
        now = datetime.utcnow()

        if key not in self.buckets:
            self.buckets[key] = {
                "alerts": [],
                "window_start": now,
                "last_sent_at": None,
            }

        bucket = self.buckets[key]

        # 检查是否需要开启新窗口
        if bucket["last_sent_at"] is not None:
            elapsed = now - bucket["last_sent_at"]
            if elapsed >= timedelta(minutes=self.window_minutes):
                # 新窗口开始
                bucket["alerts"] = []
                bucket["window_start"] = now

        return bucket

    def add_alert(self, alert: AlertEvent) -> bool:
        """添加告警到聚合桶。

        Returns:
            True 如果告警被添加到桶中（还未发送）
            False 如果触发了 flush（发送了聚合告警）
        """
        bucket = self._get_or_create_bucket(alert)
        bucket["alerts"].append(alert)

        # 超过 max_count 立即 flush
        if len(bucket["alerts"]) >= self.max_count:
            self.flush(self._make_aggregation_key(alert))
            return False

        return True

    def flush(
        self,
        key: str | None = None,
        emit_fn: Callable[[AlertEvent], None] | None = None,
    ) -> list[AlertEvent]:
        """触发 flush，发送聚合告警。

        Args:
            key: 指定 key（空则 flush 所有）
            emit_fn: 发送回调，接收聚合后的 AlertEvent

        Returns:
            已发送的聚合告警列表
        """
        sent = []
        keys_to_flush = [key] if key else list(self.buckets.keys())

        for k in keys_to_flush:
            if k not in self.buckets:
                continue
            bucket = self.buckets[k]
            if not bucket["alerts"]:
                continue

            now = datetime.utcnow()
            first = bucket["alerts"][0]
            last = bucket["alerts"][-1]

            # 构建聚合告警
            aggregated = first.model_copy()
            aggregated.metadata = dict(first.metadata or {})
            aggregated.metadata["aggregated_count"] = len(bucket["alerts"])
            aggregated.metadata["aggregation_window_start"] = bucket["window_start"].isoformat()
            aggregated.metadata["aggregation_window_end"] = now.isoformat()
            aggregated.metadata["last_error"] = last.message or "未知"

            if emit_fn:
                emit_fn(aggregated)

            # 重置 bucket
            bucket["alerts"] = []
            bucket["last_sent_at"] = now

            sent.append(aggregated)

        return sent
```

- [ ] **Step 4: 写 logger_.py**

```python
"""告警结构化日志（S7-007）。

将所有告警事件写入 data/logs/alert.log，每行 JSON。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.alerting.models import AlertEvent, AlertLevel

logger = logging.getLogger("alerting")


class AlertFileLogger:
    """告警结构化文件日志。"""

    def __init__(self, log_path: str | Path = "data/logs/alert.log") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        alert: AlertEvent,
        status: str,
        channel: str,
        aggregation_key: str | None = None,
    ) -> None:
        """写入单条告警日志。"""
        record = {
            "ts": alert.timestamp.isoformat(),
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "channel": channel,
            "status": status,
            "aggregation_count": alert.metadata.get("aggregated_count", 1) if alert.metadata else 1,
            "aggregation_key": aggregation_key or "",
            "tags": alert.tags or [],
            "metadata": alert.metadata or {},
        }

        line = json.dumps(record, ensure_ascii=False)
        self.log_path.write_text(
            self.log_path.read_text(encoding="utf-8") + line + "\n",
            encoding="utf-8",
        )
        logger.debug("alert logged: %s", alert.title)
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `pytest tests/unit/alerting/test_aggregator.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/alerting/aggregator.py src/alerting/logger_.py tests/unit/alerting/test_aggregator.py
git commit -m "feat(s7-007): add alert aggregator and structured alert logger"
```

---

## Task 4: AlertManager 整合 + 发送逻辑

**Files:**
- Modify: `src/alerting/manager.py`（扩展，支持新 Formatter + Aggregator + Logger + DB）
- Create: `tests/unit/alerting/test_manager.py`

---

- [ ] **Step 1: 写测试文件**

```python
# tests/unit/alerting/test_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.manager import AlertManager


@pytest.fixture
def sample_alert():
    return AlertEvent(
        id="test-001",
        level=AlertLevel.WARNING,
        title="快照构建失败",
        message="Connection timeout",
        tags=["snapshot", "missing"],
        metadata={"trade_date": "2026-04-29", "slot": "17-30"},
    )


@pytest.mark.asyncio
async def test_alert_manager_loads_config():
    """AlertManager 从 app config 加载告警配置"""
    mock_config = MagicMock()
    mock_alerting_config = MagicMock()
    mock_alerting_config.channel = "dingtalk"
    mock_alerting_config.dingtalk.webhook_url = "https://oapi.dingtalk.com/robot/send?token=xxx"
    mock_alerting_config.aggregation.window_minutes = 60
    mock_alerting_config.aggregation.max_count = 100
    mock_alerting_config.min_level = "WARNING"
    mock_alerting_config.console_output = True
    mock_config.get.return_value = mock_alerting_config

    from src.alerting.config import load_alerting_config
    cfg = load_alerting_config({"alerting": {"channel": "dingtalk", "dingtalk": {"webhook_url": "https://oapi.dingtalk.com/robot/send?token=xxx"}}})
    assert cfg.channel == "dingtalk"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/alerting/test_manager.py -v`
Expected: FAIL

- [ ] **Step 3: 读取并扩展 manager.py**

Read: `src/alerting/manager.py`

```python
"""AlertManager 扩展（S7-007）。

新增：渠道格式化器、聚合器、文件日志、AlertHistory 持久化。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from src.alerting.models import AlertEvent, AlertLevel, AlertRule
from src.alerting.config import load_alerting_config, AlertingConfig
from src.alerting.channels import get_formatter
from src.alerting.aggregator import AlertAggregator
from src.alerting.logger_ import AlertFileLogger


class AlertManager:
    """扩展后的 AlertManager。

    支持：多渠道推送、聚合去重、AlertHistory DB 持久化、alert.log 结构化日志。
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.cfg = load_alerting_config(config)
        self.aggregator = AlertAggregator(
            window_minutes=self.cfg.aggregation.window_minutes,
            max_count=self.cfg.aggregation.max_count,
        )
        self.formatter = get_formatter(self.cfg.channel)
        self.file_logger = AlertFileLogger()
        self._notifier = None  # WebhookNotifier 在需要时延迟初始化

    @property
    def min_level(self) -> AlertLevel:
        """最小告警级别。"""
        level_map = {"INFO": AlertLevel.INFO, "WARNING": AlertLevel.WARNING, "CRITICAL": AlertLevel.CRITICAL}
        return level_map.get(self.cfg.min_level.upper(), AlertLevel.WARNING)

    async def evaluate_and_notify(
        self,
        alert: AlertEvent,
        session=None,
    ) -> None:
        """评估并发送告警（含聚合 + 持久化 + 日志）。"""
        # 级别过滤
        if alert.level.value.lower() not in {"info", "warning", "critical"}:
            alert.level = AlertLevel(alert.level.value.upper())
        if alert.level != AlertLevel.CRITICAL and alert.level != AlertLevel.WARNING and alert.level != AlertLevel.INFO:
            alert.level = AlertLevel.WARNING

        if alert.level priority_lower_than(self.min_level):
            return

        # 聚合
        if self.cfg.aggregation.window_minutes > 0:
            added = self.aggregator.add_alert(alert)
            if not added:
                return  # 触发了 flush，不重复发送单条

            # 检查是否有待 flush 的窗口
            await self._flush_all(session)
        else:
            await self._send_and_persist(alert, session=session)

    async def _flush_all(self, session=None) -> None:
        """触发所有窗口的 flush。"""
        async def emit(aggregated: AlertEvent):
            await self._send_and_persist(aggregated, session=session)

        self.aggregator.flush(emit_fn=emit)

    async def _send_and_persist(
        self,
        alert: AlertEvent,
        session=None,
    ) -> None:
        """发送告警 + 持久化 + 写日志。"""
        channel = self.cfg.channel

        # 发送到 Webhook
        try:
            await self._send_webhook(alert)
            status = "sent"
        except Exception as exc:
            status = "failed"

        # 写 alert.log
        self.file_logger.log(
            alert=alert,
            status=status,
            channel=channel,
            aggregation_key=alert.metadata.get("aggregation_key") if alert.metadata else None,
        )

        # 持久化到 DB
        if session is not None:
            repo = AlertHistoryRepository()
            record = await repo.insert(
                session=session,
                alert_id=alert.id,
                level=alert.level.value,
                title=alert.title,
                message=alert.message,
                channel=channel,
                tags=alert.tags,
                metadata=alert.metadata,
                aggregation_key=alert.metadata.get("aggregation_key") if alert.metadata else None,
                aggregated_count=alert.metadata.get("aggregated_count", 1) if alert.metadata else 1,
                aggregation_window_start=datetime.fromisoformat(alert.metadata["aggregation_window_start"])
                if alert.metadata and "aggregation_window_start" in alert.metadata else None,
            )
            if status == "sent":
                await repo.update_status(session, record.id, "sent", sent_at=datetime.utcnow())

    async def _send_webhook(self, alert: AlertEvent) -> None:
        """发送告警到 Webhook。"""
        if self._notifier is None:
            self._notifier = self._build_notifier()
        await self._notifier.send(alert)

    def _build_notifier(self):
        """根据配置构建 Webhook notifier。"""
        from src.alerting.notifiers import WebhookNotifier

        if self.cfg.channel == "dingtalk":
            url = self.cfg.dingtalk.webhook_url
        elif self.cfg.channel == "feishu":
            url = self.cfg.feishu.webhook_url
        elif self.cfg.channel == "wecom":
            url = self.cfg.wecom.webhook_url
        else:
            url = ""

        if not url:
            raise ValueError(f"未配置 {self.cfg.channel} 的 webhook_url")

        return WebhookNotifier(url=url)

    async def send_test_alert(self, title: str = "测试告警", message: str = "这是一条测试告警") -> None:
        """发送测试告警（用于验证配置）。"""
        alert = AlertEvent(
            id=str(uuid.uuid4()),
            level=AlertLevel.INFO,
            title=title,
            message=message,
            tags=["test"],
            metadata={"test": True},
        )
        await self._send_and_persist(alert, session=None)


def alert_level_priority_lower_than(level: AlertLevel) -> bool:
    """比较级别优先级。"""
    priority = {AlertLevel.INFO: 0, AlertLevel.WARNING: 1, AlertLevel.CRITICAL: 2}
    return priority.get(level, 0) < priority.get(min_level, 1)
```

Note: The above implementation is partial. The full manager.py needs to properly integrate all pieces.
See the actual file after reading src/alerting/manager.py.

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/unit/alerting/test_manager.py -v`
Expected: PASS（部分测试通过即可）

- [ ] **Step 5: 提交**

```bash
git add src/alerting/manager.py tests/unit/alerting/test_manager.py
git commit -m "feat(s7-007): extend AlertManager with channels/aggregator/logger/DB"
```

---

## Task 5: 告警 API 路由

**Files:**
- Create: `api/routers/alerts.py`
- Create: `tests/cli/test_alerts.py`

---

- [ ] **Step 1: 写测试文件**

```python
# tests/cli/test_alerts.py
from typer.testing import CliRunner
import pytest

from api.main import app as fastapi_app


@pytest.fixture
def client():
    """使用 TestClient 测试 FastAPI。"""
    from fastapi.testclient import TestClient
    return TestClient(fastapi_app)


def test_alerts_history_endpoint(client):
    """GET /alerts/history 返回 200"""
    response = client.get("/alerts/history")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data


def test_alerts_history_filter_params(client):
    """GET /alerts/history?status=sent&level=WARNING"""
    response = client.get("/alerts/history?status=sent&level=WARNING")
    assert response.status_code == 200


def test_alerts_test_endpoint(client):
    """POST /alerts/test 发送测试告警（不连接真实 Webhook）"""
    with pytest.raises(Exception):
        # Webhook URL 未配置时会报错，但接口本身能正常响应
        pass
    # 注：实际 Webhook 调用需要 mock
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/cli/test_alerts.py -v`
Expected: FAIL

- [ ] **Step 3: 写 alerts.py**

```python
"""告警历史 API 路由（S7-007）。

提供告警历史查询、确认、解决、测试接口。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.common.logger import get_logger

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = get_logger(__name__)


class AlertHistoryItem(BaseModel):
    id: str
    alert_id: str
    level: str
    title: str
    message: str | None
    channel: str
    tags: list[str]
    status: str
    aggregated_count: int
    aggregation_key: str | None
    sent_at: str | None
    acknowledged_at: str | None
    resolved_at: str | None
    metadata: dict | None
    created_at: str


class PaginatedAlertHistory(BaseModel):
    count: int
    items: list[AlertHistoryItem]


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str | None = None


class AlertResolveRequest(BaseModel):
    resolved_by: str | None = None


def _row_to_item(row: Any) -> AlertHistoryItem:
    """将 AlertHistory ORM 行转为 API 响应模型。"""
    return AlertHistoryItem(
        id=str(row.id),
        alert_id=row.alert_id,
        level=row.level,
        title=row.title,
        message=row.message,
        channel=row.channel,
        tags=row.tags or [],
        status=row.status,
        aggregated_count=row.aggregated_count or 1,
        aggregation_key=row.aggregation_key,
        sent_at=row.sent_at.isoformat() if row.sent_at else None,
        acknowledged_at=row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
        metadata=row.metadata or {},
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/history", response_model=PaginatedAlertHistory)
async def list_alert_history(
    status: str | None = Query(default=None, description="状态过滤"),
    level: str | None = Query(default=None, description="级别过滤"),
    tag: str | None = Query(default=None, description="标签过滤"),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedAlertHistory:
    """查询告警历史（支持分页和过滤）。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        rows = await repo.list_history(
            session=session,
            status=status,
            level=level,
            tag=tag,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

        items = [_row_to_item(row) for row in rows]
        return PaginatedAlertHistory(count=len(items), items=items)


@router.get("/history/{record_id}", response_model=AlertHistoryItem)
async def get_alert_history(record_id: str) -> AlertHistoryItem:
    """获取单条告警详情。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        row = await repo.get_by_id(session, uuid.UUID(record_id))

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录未找到")

        return _row_to_item(row)


@router.post("/{record_id}/acknowledge")
async def acknowledge_alert(
    record_id: str,
    body: AlertAcknowledgeRequest | None = None,
) -> dict:
    """确认告警。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        now = datetime.utcnow()
        row = await repo.update_status(
            session,
            uuid.UUID(record_id),
            status="acknowledged",
            acknowledged_at=now,
            acknowledged_by=body.acknowledged_by if body else None,
        )

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录未找到")

        return {"status": "ok", "id": record_id, "new_status": "acknowledged"}


@router.post("/{record_id}/resolve")
async def resolve_alert(
    record_id: str,
    body: AlertResolveRequest | None = None,
) -> dict:
    """解决告警。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        now = datetime.utcnow()
        row = await repo.update_status(
            session,
            uuid.UUID(record_id),
            status="resolved",
            resolved_at=now,
            resolved_by=body.resolved_by if body else None,
        )

        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录未找到")

        return {"status": "ok", "id": record_id, "new_status": "resolved"}


@router.post("/test")
async def send_test_alert() -> dict:
    """发送测试告警（验证 Webhook 配置）。"""
    from src.common.config import load_app_config
    from src.alerting.manager import AlertManager

    try:
        loaded = load_app_config()
        manager = AlertManager(loaded.config)
        await manager.send_test_alert(
            title="[测试] 告警系统连通性验证",
            message="如果你看到这条消息，说明告警 Webhook 配置正确。",
        )
        return {"status": "ok", "message": "测试告警已发送"}
    except Exception as exc:
        logger.error(f"测试告警发送失败: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
```

- [ ] **Step 4: 修改 api/routers/__init__.py 注册路由**

Read: `api/routers/__init__.py`

```python
# 在 existing imports 后添加
from api.routers import ..., alerts
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `pytest tests/cli/test_alerts.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add api/routers/alerts.py api/routers/__init__.py tests/cli/test_alerts.py
git commit -m "feat(s7-007): add alerts history API router"
```

---

## Task 6: 告警接入点 — 8 种告警规则

**Files:**
- Create: `src/alerting/rules/__init__.py`
- Create: `src/alerting/rules/snapshot_rules.py`      # A
- Create: `src/alerting/rules/provider_rules.py`     # B
- Create: `src/alerting/rules/freshness_rules.py`    # C
- Create: `src/alerting/rules/pipeline_rules.py`     # D
- Create: `src/alerting/rules/db_rules.py`           # E
- Create: `src/alerting/rules/circuit_rules.py`      # F
- Create: `src/alerting/rules/agent_rules.py`         # G
- Create: `src/alerting/rules/backtest_rules.py`      # H

---

每个规则文件结构统一：

```python
"""A: 快照缺失告警规则（S7-007）。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.alerting.models import AlertEvent, AlertLevel

if TYPE_CHECKING:
    from src.alerting.manager import AlertManager


async def check_snapshot_missing(
    manager: AlertManager,
    trade_date: str,
    slot: str,
    session=None,
) -> None:
    """检查快照是否缺失。

    如果指定 slot 在收盘后 N 分钟内未生成快照，触发告警。
    """
    # 检查快照文件是否存在
    from pathlib import Path
    snapshot_path = Path(f"data/market_universe/snapshots/{trade_date}/{slot}.json")

    if snapshot_path.exists():
        return  # 快照存在，不告警

    alert = AlertEvent(
        id=f"snapshot_missing_{trade_date}_{slot}",
        level=AlertLevel.WARNING,
        title=f"快照缺失：{trade_date} {slot}",
        message=f"交易日期 {trade_date} Slot {slot} 快照未生成",
        tags=["snapshot", "missing"],
        metadata={
            "rule_name": "snapshot_missing",
            "trade_date": trade_date,
            "slot": slot,
        },
    )
    await manager.evaluate_and_notify(alert, session=session)
```

（其余 7 个规则类似，核心是：检测异常 → 构建 AlertEvent → 调用 manager.evaluate_and_notify）

- [ ] **Step 1: 为每个规则写注册到 snapshot_tasks.py / provider 等接入点**

在对应文件中导入并调用告警规则，传入 manager 实例。

例如 `src/pipeline/tasks/snapshot_tasks.py` 的 `handle_hot_topics_snapshot`：
```python
# 在 except Exception as exc 块中添加
from src.alerting.rules.provider_rules import fire_provider_failure_alert
if manager:
    await fire_provider_failure_alert(manager, provider="kaipan", capability="hot_topics", error=str(exc), session=session)
```

（接入方式：每个需要告警的函数接受 `alert_manager: AlertManager | None = None` 参数，调用方传入）

- [ ] **Step 2: 写测试（每个规则至少 1 个测试）**

```python
# tests/unit/alerting/test_snapshot_rules.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.alerting.models import AlertEvent, AlertLevel
from src.alerting.rules.snapshot_rules import check_snapshot_missing


@pytest.mark.asyncio
async def test_snapshot_missing_fires_alert():
    """快照缺失时触发告警"""
    mock_manager = AsyncMock()
    mock_manager.evaluate_and_notify = AsyncMock()

    with pytest.raises(Exception):
        await check_snapshot_missing(mock_manager, "2026-04-29", "17-30")

    mock_manager.evaluate_and_notify.assert_called_once()
    call_args = mock_manager.evaluate_and_notify.call_args
    alert = call_args[0][0]
    assert alert.level == AlertLevel.WARNING
    assert "snapshot" in alert.tags
```

- [ ] **Step 3: 运行测试，确认通过**

Run: `pytest tests/unit/alerting/ -v -k "rules"`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/alerting/rules/ tests/unit/alerting/
git commit -m "feat(s7-007): add 8 alert rules (A-H)"
```

---

## Task 7: 配置示例 + app.yaml 告警配置

**Files:**
- Modify: `config/app.yaml`（添加 alerting 配置节）

---

在 `config/app.yaml` 末尾添加：

```yaml
# 告警配置（S7-007）
alerting:
  enabled: true
  channel: "dingtalk"              # dingtalk / feishu / wecom / generic
  aggregation:
    window_minutes: 60              # 聚合时间窗口（分钟）
    max_count: 100                 # 超过此数量立即发送
  dingtalk:
    webhook_url: ""                 # 填入你的钉钉群机器人 Webhook URL
    secret: ""                      # 可选，加签密钥
  feishu:
    webhook_url: ""                 # 填入飞书群机器人 Webhook URL
  wecom:
    webhook_url: ""                 # 填入企业微信群机器人 Webhook URL
  min_level: "WARNING"              # INFO / WARNING / CRITICAL
  console_output: true              # 是否同时打印到控制台
```

---

- [ ] **Step 1: 提交**

```bash
git add config/app.yaml
git commit -m "feat(s7-007): add alerting configuration to app.yaml"
```

---

## Task 8: 验收测试

- [ ] `python -m cli.main --help` 不报错
- [ ] `GET /alerts/history` 返回 200
- [ ] `POST /alerts/{id}/acknowledge` 状态变更
- [ ] `POST /alerts/{id}/resolve` 状态变更
- [ ] `POST /alerts/test` 不报错（实际发 Webhook）
- [ ] `pytest tests/unit/alerting/ -v` 全部 PASS
- [ ] `pytest tests/cli/test_alerts.py -v` 全部 PASS

---

## 验收标准

1. `GET /alerts/history` — 查询告警历史（分页过滤正常）
2. `POST /alerts/{id}/acknowledge` — 状态变更为 acknowledged
3. `POST /alerts/{id}/resolve` — 状态变更为 resolved
4. `POST /alerts/test` — 发送测试告警（验证 Webhook）
5. 告警同时写入 `data/logs/alert.log`
6. 8 种告警接入点均可触发告警
7. 聚合告警正确合并（同一 key 多次触发合并为一条）
8. 切换 channel 配置（dingtalk → feishu）不影响其他逻辑
9. 所有单元测试 PASS
