"""告警规则集（S7-007）。

原有默认规则 + 8 种新告警规则：
- A: 快照缺失（snapshot_rules）
- B: Provider 失败（provider_rules）
- C: 数据新鲜度（freshness_rules）
- D: Pipeline 失败（pipeline_rules）
- E: DB 异常（db_rules）
- F: Circuit Breaker（circuit_rules）
- G: Agent 异常（agent_rules）
- H: 回测失败（backtest_rules）
"""

from src.alerting.rules.rules import (
    DEFAULT_ALERT_RULES,
    get_default_rules,
    create_custom_rule,
    AlertRule,
)

from src.alerting.rules.snapshot_rules import fire_snapshot_missing_alert
from src.alerting.rules.provider_rules import fire_provider_failure_alert
from src.alerting.rules.freshness_rules import fire_freshness_alert
from src.alerting.rules.pipeline_rules import fire_pipeline_failure_alert
from src.alerting.rules.db_rules import fire_db_failure_alert
from src.alerting.rules.circuit_rules import fire_circuit_breaker_open_alert
from src.alerting.rules.agent_rules import fire_agent_failure_alert
from src.alerting.rules.backtest_rules import fire_backtest_failure_alert

from src.alerting.rules.akshare_stale_rules import fire_akshare_stale_alert

__all__ = [
    # 原有导出
    "DEFAULT_ALERT_RULES",
    "get_default_rules",
    "create_custom_rule",
    "AlertRule",
    # S7-007 新规则
    "fire_snapshot_missing_alert",
    "fire_provider_failure_alert",
    "fire_freshness_alert",
    "fire_pipeline_failure_alert",
    "fire_db_failure_alert",
    "fire_circuit_breaker_open_alert",
    "fire_agent_failure_alert",
    "fire_backtest_failure_alert",
    "fire_akshare_stale_alert",
]
