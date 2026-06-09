# DashboardService 与 alerting 统一设计

## 1. 背景与目标

当前存在两套告警基础设施：

| 位置 | AlertEvent | AlertManager | 问题 |
|------|-----------|--------------|------|
| `src/alerting/` | 完整元数据（level/title/timestamp/id/metadata）| 异步 + 规则评估 + 冷却 + 多通知器 | 业务告警 |
| `src/pipeline/dashboard_service.py` | 简单 `level: str, message: str` | 同步 + Dashboard专用阈值检查 | 数据质量监控 |

目标：将 dashboard 的数据质量阈值检查建模为 `AlertRule`，统一到 `src/alerting/` 下，消除重复代码。

## 2. 核心设计

### 2.1 AlertEvent 统一

删除 `dashboard_service.py` 中的本地 `AlertEvent` dataclass，统一使用 `src.alerting.models.AlertEvent`。

`DashboardReport.alerts` 字段从 `list[str]` 改为 `list[AlertEvent]`。渲染时在 `dashboard.py` 或 renderer 中转换为字符串。

### 2.2 DashboardService 使用 AlertingManager

`DashboardService` 内部 `AlertManager` 类删除，改用 `src.alerting.AlertManager`。

在 `__init__` 中根据参数化配置动态构建告警规则：

```python
def _build_dashboard_rules(
    freshness_threshold_hours: float,
    anomaly_rate_threshold: float,
) -> list[AlertRule]:
    return [
        AlertRule(
            name="articles_data_stale",
            condition=lambda stats, _: (
                stats.articles.freshness_hours is not None
                and stats.articles.freshness_hours > freshness_threshold_hours
            ),
            level=AlertLevel.WARNING,
            title="文章数据过期",
            message_template=f"文章数据超过 {{{freshness_threshold_hours:.1f}}} 小时未更新",
            cooldown_seconds=3600,
            tags=["dashboard"],
        ),
        # ... 类似 threshold 驱动的规则
    ]
```

### 2.3 AlertManager.evaluate() 保持不变

`src.alerting.AlertManager.evaluate()` 签名：

```python
async def evaluate(
    self,
    stats: DashboardStats,
    quality: QualityMetrics,
) -> list[AlertEvent]:
```

调用方传入 `DashboardStats` 和 `QualityMetrics`，无需修改接口。

### 2.4 DashboardReport.alerts 类型

```python
@dataclass(slots=True)
class DashboardReport:
    ...
    alerts: list[AlertEvent] = field(default_factory=list)  # 原来是 list[str]
```

渲染时在 `dashboard.py` 中将 `AlertEvent` 转换为字符串输出。

## 3. 文件变更

| 操作 | 文件 |
|------|------|
| 删除 | `src/pipeline/dashboard_service.py::AlertEvent` dataclass（行18-23） |
| 删除 | `src/pipeline/dashboard_service.py::AlertManager` 类（行367-436） |
| 修改 | `src/pipeline/dashboard_service.py::DashboardService.__init__` |
| 修改 | `src/pipeline/dashboard_service.py::DashboardService.build_report` |
| 修改 | `src/pipeline/dashboard_models.py::DashboardReport.alerts` 类型 |
| 修改 | `src/pipeline/dashboard.py::main` — `critical_alerts` 过滤逻辑适配新类型 |
| 不变 | 所有 `src/alerting/` 模块 |
| 不变 | `AlertingHealthChecker`（仍可注入 AlertManager） |

## 4. 数据流

```
DashboardService.build_report()
  ├── stats_collector.collect() → DashboardStats
  ├── quality_analyzer.analyze() → QualityMetrics
  ├── alert_manager.evaluate(stats, quality) → list[AlertEvent]  ← 复用 alerting/AlertManager
  └── DashboardReport(alerts=list[AlertEvent])
       └── dashboard.py::main()
            ├── CLIRenderer.render(report)  — AlertEvent → "[WARNING] message"
            └── HTMLRenderer.render(report) — 同上
```

## 5. 验证方式

1. `python -m pytest tests/unit/pipeline/test_dashboard.py -v` 无回归
2. `python -m src.pipeline.dashboard --mode cli` 正常输出报告
3. `AlertingHealthChecker` 注入 `DashboardService.alert_manager` 工作正常
4. `report.alerts` 是 `list[AlertEvent]` 类型，`.level` / `.message` / `.timestamp` 可访问
