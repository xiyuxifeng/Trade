# P5-019 关键指标告警实现计划

## Context

当前告警系统现状：
1. **AlertManager** (`dashboard_service.py`): 告警判断逻辑，支持数据新鲜度、异常率、异常趋势等
2. **AlertEvent**: 仅包含 `level` 和 `message`，无告警ID、时间戳等元数据
3. **Prometheus 配置**: 文档中定义了告警规则，但缺少实际的指标埋点
4. **告警通知**: 只有日志输出，无统一的通知机制

目标：实现关键指标告警系统，支持：
- 告警规则定义（配置化）
- 多渠道通知（Console/Email/Slack/Webhook）
- 告警聚合和抑制（防止告警风暴）
- 与现有 Prometheus 监控体系集成

---

## 方案概述

### 1. 扩展 AlertEvent

```python
@dataclass
class AlertEvent:
    """告警事件（增强版）。"""
    id: str = field(default_factory=lambda: str(uuid4()))
    level: AlertLevel  # INFO / WARNING / CRITICAL
    source: str  # 告警来源，如 "AlertManager", "Prometheus"
    title: str  # 简短标题
    message: str  # 详细描述
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外上下文
    tags: list[str] = field(default_factory=list)  # 用于分组和过滤
```

### 2. 告警规则定义

```python
@dataclass
class AlertRule:
    """告警规则配置。"""
    name: str
    condition: Callable[[DashboardStats, QualityMetrics], bool]  # 触发条件
    level: AlertLevel
    title: str
    message_template: str  # 支持模板变量
    cooldown_seconds: int = 300  # 告警冷却时间
    enabled: bool = True

# 预定义规则
DEFAULT_ALERT_RULES = [
    AlertRule(
        name="data_stale",
        condition=lambda stats, _: stats.articles.freshness_hours > 24,
        level=AlertLevel.WARNING,
        title="数据过期",
        message_template="数据超过 {freshness_hours:.1f} 小时未更新",
    ),
    AlertRule(
        name="high_anomaly_rate",
        condition=lambda _, quality: quality.anomaly_rate > 5.0,
        level=AlertLevel.CRITICAL,
        title="异常率过高",
        message_template="异常率 {anomaly_rate:.1f}% 超过阈值",
    ),
]
```

### 3. 告警通知接口

```python
class AlertNotifier(ABC):
    """告警通知器接口。"""

    @abstractmethod
    async def send(self, alert: AlertEvent) -> None:
        """发送告警通知。"""
        ...

    @abstractmethod
    async def send_batch(self, alerts: list[AlertEvent]) -> None:
        """批量发送告警。"""
        ...

class ConsoleNotifier(AlertNotifier):
    """控制台通知器（开发用）。"""

class EmailNotifier(AlertNotifier):
    """邮件通知器。"""

class SlackNotifier(AlertNotifier):
    """Slack 通知器。"""

class WebhookNotifier(AlertNotifier):
    """通用 Webhook 通知器。"""
```

### 4. AlertManager 增强

```python
class AlertManager:
    """增强版告警管理器。"""

    def __init__(
        self,
        rules: list[AlertRule],
        notifiers: list[AlertNotifier],
        cooldown_seconds: int = 300,
    ):
        self.rules = rules
        self.notifiers = notifiers
        self._last_alert_time: dict[str, datetime] = {}  # 记录每个规则上次告警时间

    async def evaluate_and_notify(
        self,
        stats: DashboardStats,
        quality: QualityMetrics,
    ) -> list[AlertEvent]:
        """评估告警规则并发送通知。"""
        alerts = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.condition(stats, quality):
                # 检查冷却时间
                if self._is_in_cooldown(rule.name):
                    continue

                alert = self._create_alert(rule, stats, quality)
                alerts.append(alert)
                self._last_alert_time[rule.name] = datetime.now(UTC)

        # 发送所有告警
        for notifier in self.notifiers:
            await notifier.send_batch(alerts)

        return alerts

    def _is_in_cooldown(self, rule_name: str) -> bool:
        """检查规则是否在冷却期。"""
        if rule_name not in self._last_alert_time:
            return False
        elapsed = (datetime.now(UTC) - self._last_alert_time[rule_name]).total_seconds()
        return elapsed < self._get_rule_cooldown(rule_name)
```

---

## 文件结构

```
src/alerting/
├── __init__.py              # 统一导出
├── models.py                # AlertEvent, AlertLevel, AlertRule
├── notifiers.py             # AlertNotifier, ConsoleNotifier, WebhookNotifier
├── manager.py               # AlertManager（增强版）
├── rules.py                 # 预定义告警规则
├── config.py                # 告警配置加载
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_notifiers.py
    └── test_manager.py
```

---

## 实现步骤

### Phase 1: 核心模型
1. [ ] 创建 `src/alerting/` 目录
2. [ ] 实现 `models.py` - AlertEvent, AlertLevel, AlertRule
3. [ ] 实现 `notifiers.py` - AlertNotifier 接口 + ConsoleNotifier
4. [ ] 编写单元测试（15+ tests）

### Phase 2: 告警管理
1. [ ] 实现 `rules.py` - 预定义告警规则
2. [ ] 实现 `manager.py` - AlertManager（增强版，支持冷却时间）
3. [ ] 实现 `config.py` - 告警配置加载
4. [ ] 编写单元测试（10+ tests）

### Phase 3: 扩展通知器
1. [ ] 实现 `WebhookNotifier` - 通用 Webhook 通知
2. [ ] 实现 `SlackNotifier`（可选）
3. [ ] 实现 `EmailNotifier`（可选）

### Phase 4: 集成
1. [ ] 修改 `dashboard_service.py` 使用新的 AlertManager
2. [ ] 更新 `config/app.yaml` 添加告警配置
3. [ ] 端到端测试

---

## 关键文件

| 操作 | 文件 |
|------|------|
| 新建 | `src/alerting/models.py` |
| 新建 | `src/alerting/notifiers.py` |
| 新建 | `src/alerting/manager.py` |
| 新建 | `src/alerting/rules.py` |
| 新建 | `src/alerting/config.py` |
| 修改 | `src/pipeline/dashboard_service.py` |

---

## 验证

1. **单元测试**: `pytest src/alerting/tests/ -v`
2. **集成测试**: 修改 DashboardService 后运行 `pytest tests/unit/pipeline/test_dashboard.py -v`
3. **手动测试**: 触发告警条件，观察控制台输出

---

## 与 Prometheus 的关系

Prometheus 告警是**指标驱动**的（基于时间序列数据），而我们的 AlertManager 是**事件驱动**的（基于 DashboardStats/QualityMetrics）。

两者互补：
- Prometheus: 适合系统级指标（CPU、内存、网络）
- AlertManager: 适合业务级指标（数据新鲜度、异常率、交易员行为）

**不需要在 AlertManager 中实现 Prometheus metrics**，只需确保：
1. 日志中使用结构化格式，便于 Prometheus 抓取
2. 告警触发时记录相应指标（可选）
