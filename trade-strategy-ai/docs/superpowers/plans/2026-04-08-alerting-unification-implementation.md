# DashboardService 与 alerting 统一实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 dashboard_service.py 中的本地 AlertEvent 和 AlertManager 删除，改用 src/alerting/ 模块，实现告警系统统一。

**Architecture:**
- 删除 `dashboard_service.py` 中的 `AlertEvent` dataclass 和 `AlertManager` 类
- `DashboardService` 持有 `src.alerting.AlertManager` 实例，注入参数化规则
- `DashboardReport.alerts` 类型从 `list[str]` 改为 `list[AlertEvent]`
- `dashboard.py` 中 alert 渲染逻辑适配新类型

**Tech Stack:** SQLAlchemy async, Pydantic, asyncio

---

## 文件清单

### 修改
- `src/pipeline/dashboard_models.py` — `DashboardReport.alerts` 类型变更 + import AlertEvent
- `src/pipeline/dashboard_service.py` — 删除本地 AlertEvent/AlertManager，DashboardService 改用 alerting 模块
- `src/pipeline/dashboard.py` — `critical_alerts` 过滤逻辑适配 AlertEvent
- `tests/unit/pipeline/test_dashboard.py` — AlertManager 引用路径更新

---

## Task 1: 修改 dashboard_models.py — AlertEvent 类型导入

**Files:**
- Modify: `src/pipeline/dashboard_models.py`

- [ ] **Step 1: 修改 dashboard_models.py**

在文件顶部添加 AlertEvent 导入：

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.alerting.models import AlertEvent  # 新增导入
```

将 `DashboardReport.alerts` 字段类型从 `list[str]` 改为 `list[AlertEvent]`：

```python
# 原来：
alerts: list[str] = field(default_factory=list)

# 改为：
alerts: list[AlertEvent] = field(default_factory=list)
```

- [ ] **Step 2: 验证**

```bash
python -c "from src.pipeline.dashboard_models import DashboardReport; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add src/pipeline/dashboard_models.py
git commit -m "refactor: DashboardReport.alerts uses AlertEvent from alerting module"
```

---

## Task 2: 修改 dashboard_service.py — 删除重复代码，改用 alerting 模块

**Files:**
- Modify: `src/pipeline/dashboard_service.py`

需要执行以下修改：

1. **删除** `AlertEvent` dataclass（行18-23）

2. **删除** `AlertManager` 类（行367-436，含 `__init__` 的 `freshness_threshold_hours` / `anomaly_rate_threshold` 属性和 `check()` 方法）

3. **修改** `DashboardService.__init__` — 用 `src.alerting.AlertManager` 替代本地 AlertManager，并注入参数化规则：

```python
from src.alerting.models import AlertLevel, AlertRule
from src.alerting.manager import AlertManager as AlertingManager

def _build_dashboard_rules(
    freshness_threshold_hours: float,
    anomaly_rate_threshold: float,
) -> list[AlertRule]:
    """根据配置参数构建 Dashboard 专用告警规则。"""
    total_threshold = anomaly_rate_threshold
    return [
        AlertRule(
            name="articles_data_stale",
            condition=lambda stats, _: (
                stats.articles.freshness_hours is not None
                and stats.articles.freshness_hours > freshness_threshold_hours
            ),
            level=AlertLevel.WARNING,
            title="文章数据过期",
            message_template=f"文章数据超过 {freshness_threshold_hours:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="trades_data_stale",
            condition=lambda stats, _: (
                stats.trades.freshness_hours is not None
                and stats.trades.freshness_hours > freshness_threshold_hours
            ),
            level=AlertLevel.WARNING,
            title="交易数据过期",
            message_template=f"交易数据超过 {freshness_threshold_hours:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="market_data_stale",
            condition=lambda stats, _: (
                stats.market_data.freshness_hours is not None
                and stats.market_data.freshness_hours > freshness_threshold_hours
            ),
            level=AlertLevel.WARNING,
            title="市场数据过期",
            message_template=f"市场数据超过 {freshness_threshold_hours:.1f} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard", "freshness"],
        ),
        AlertRule(
            name="high_anomaly_rate",
            condition=lambda stats, quality: (
                _calc_anomaly_rate(stats, quality) > total_threshold
            ),
            level=AlertLevel.CRITICAL,
            title="数据异常率过高",
            message_template=f"数据异常率 {{anomaly_rate:.1f}}% 超过阈值 {total_threshold}%",
            cooldown_seconds=1800,
            tags=["dashboard", "quality"],
        ),
    ]


def _calc_anomaly_rate(stats: "DashboardStats", quality: "QualityMetrics") -> float:
    """计算异常率。"""
    total = stats.articles.total + stats.trades.total + stats.market_data.total
    if total <= 0:
        return 0.0
    return (quality.total_issues / total) * 100
```

4. **修改** `DashboardService.__init__` — 将 `self.alert_manager` 改为使用 alerting 模块：

```python
# 原来：
self.alert_manager = AlertManager(freshness_threshold_hours, anomaly_rate_threshold)

# 改为：
rules = _build_dashboard_rules(freshness_threshold_hours, anomaly_rate_threshold)
self.alert_manager = AlertingManager(rules=rules, notifiers=[])
```

5. **修改** `DashboardService.build_report` — 用 `evaluate()` 替代 `check()`：

```python
# 原来：
alerts = self.alert_manager.check(
    stats, quality,
    quality_trend=quality_trend,
    source_freshness=source_freshness,
    trader_stats=trader_stats,
)
alert_messages = [f"[{alert.level.upper()}] {alert.message}" for alert in alerts]

# 改为：
# AlertManager.evaluate() 只接受 stats 和 quality，其他参数暂时忽略
events = await self.alert_manager.evaluate(stats, quality)
alert_messages = [f"[{e.level.value.upper()}] {e.message}" for e in events]
```

> **注意:** `AlertingManager.evaluate()` 当前签名是 `(stats, quality)`，不接受 `quality_trend`, `source_freshness`, `trader_stats` 参数。暂时只评估 stats + quality 相关规则。后续可扩展 AlertManager 支持更多参数。

6. **添加必要的导入**（在文件顶部）：

```python
from src.alerting.models import AlertLevel, AlertRule
from src.alerting.manager import AlertManager as AlertingManager
```

- [ ] **Step 2: 验证语法**

```bash
python -c "from src.pipeline.dashboard_service import DashboardService; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add src/pipeline/dashboard_service.py
git commit -m "refactor: DashboardService uses AlertingManager, removes duplicate AlertEvent"
```

---

## Task 3: 修改 dashboard.py — 适配 AlertEvent 类型

**Files:**
- Modify: `src/pipeline/dashboard.py`

需要修改 `critical_alerts` 的过滤逻辑：

```python
# 原来：
critical_alerts = [a for a in report.alerts if "[CRITICAL]" in a]

# 改为（因为 report.alerts 现在是 list[AlertEvent]）：
from src.alerting.models import AlertLevel
critical_alerts = [e for e in report.alerts if e.level == AlertLevel.CRITICAL]
```

- [ ] **Step 2: 验证**

```bash
python -c "from src.pipeline.dashboard import main; print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add src/pipeline/dashboard.py
git commit -m "refactor: dashboard.py filters AlertEvent by level instead of string"
```

---

## Task 4: 更新测试 — AlertManager 引用路径

**Files:**
- Modify: `tests/unit/pipeline/test_dashboard.py`

检查所有对 `AlertManager` 的导入引用：

```python
# 原来：
from src.pipeline.dashboard_service import AlertManager, QualityAnalyzer

# 改为：
from src.alerting.manager import AlertManager as AlertingManager
# 或者如果测试需要的是 dashboard_service 的 AlertManager，则删除相关测试
```

搜索 `test_dashboard.py` 中是否有使用 `AlertManager` 的测试，如果有需要检查测试逻辑是否仍然有效。

运行验证：

```bash
python -m pytest tests/unit/pipeline/test_dashboard.py -v --tb=short 2>&1 | tail -20
```

根据测试失败情况决定如何修改。

- [ ] **Step 2: 提交**

```bash
git add tests/unit/pipeline/test_dashboard.py
git commit -m "test: update AlertManager import path after unification"
```

---

## 自检清单

1. **Spec coverage:**
   - ✅ 删除 dashboard_service.py 中的 AlertEvent → Task 2
   - ✅ 删除 dashboard_service.py 中的 AlertManager → Task 2
   - ✅ DashboardReport.alerts 改为 list[AlertEvent] → Task 1
   - ✅ DashboardService 使用 src.alerting.AlertManager → Task 2
   - ✅ dashboard.py 过滤逻辑适配 → Task 3
   - ⚠️ dashboard.py 中的 quality_trend / source_freshness / trader_stats 相关告警暂时移除（AlertManager.evaluate() 暂不支持）

2. **Placeholder scan:** 无 TBD/TODO

3. **Type consistency:**
   - `AlertEvent.level` 是 `AlertLevel` 枚举，访问用 `.value` 或直接与 `AlertLevel.CRITICAL` 比较
   - `AlertEvent.message` 是 `str`

---

## 执行后预期结果

- `src/pipeline/dashboard_service.py` 中无本地 `AlertEvent` 和 `AlertManager`
- `DashboardReport.alerts` 是 `list[AlertEvent]`
- `DashboardService` 内部使用 `src.alerting.AlertManager`
- 所有 dashboard 相关测试仍通过
