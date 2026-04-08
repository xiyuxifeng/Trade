"""健康检查服务。"""
from __future__ import annotations

import asyncio
from typing import Any

from src.health.models import (
    ComponentCheck,
    DetailedHealthResponse,
    HealthStatus,
    LiveHealthResponse,
    OverallStatus,
    ReadyHealthResponse,
)


class HealthCheckService:
    """编排所有健康检查器。"""

    def __init__(
        self,
        db_checker: DatabaseHealthChecker | None = None,
        pipeline_checker: PipelineHealthChecker | None = None,
        agent_net_checker: AgentNetHealthChecker | None = None,
        alerting_checker: AlertingHealthChecker | None = None,
        circuit_breaker_checker: CircuitBreakerHealthChecker | None = None,
    ) -> None:
        from src.health.db_checker import DatabaseHealthChecker
        from src.health.pipeline_checker import PipelineHealthChecker
        from src.health.agent_net_checker import AgentNetHealthChecker
        from src.health.alerting_checker import AlertingHealthChecker
        from src.health.circuit_breaker_checker import CircuitBreakerHealthChecker

        self.db_checker = db_checker or DatabaseHealthChecker()
        self.pipeline_checker = pipeline_checker or PipelineHealthChecker()
        self.agent_net_checker = agent_net_checker or AgentNetHealthChecker()
        self.alerting_checker = alerting_checker or AlertingHealthChecker()
        self.circuit_breaker_checker = circuit_breaker_checker or CircuitBreakerHealthChecker()

    async def check_live(self) -> LiveHealthResponse:
        """Liveness 检查：进程存活即返回 alive。"""
        return LiveHealthResponse(status="alive")

    async def check_ready(self) -> ReadyHealthResponse:
        """Readiness 检查：只验证 DB 连接。"""
        check = await self.db_checker.check()
        db_ok = check.status.value == "ok"
        return ReadyHealthResponse(
            status="ready" if db_ok else "not_ready",
            checks={"database": "ok" if db_ok else "failed"},
        )

    async def check_detailed(self, timeout: float = 10.0) -> DetailedHealthResponse:
        """详细健康检查：并行执行所有组件检查。"""
        checkers: list[Any] = [
            self.db_checker,
            self.pipeline_checker,
            self.agent_net_checker,
            self.alerting_checker,
            self.circuit_breaker_checker,
        ]

        results: dict[str, ComponentCheck] = {}
        issues: list[str] = []

        async def run_checker(checker: Any) -> tuple[str, ComponentCheck]:
            try:
                return (checker.name, await asyncio.wait_for(checker.check(), timeout=timeout))
            except asyncio.TimeoutError:
                return (checker.name, ComponentCheck(
                    name=checker.name,
                    status=HealthStatus.ERROR,
                    error=f"Check timed out after {timeout}s",
                ))
            except Exception as e:
                return (checker.name, ComponentCheck(
                    name=checker.name,
                    status=HealthStatus.ERROR,
                    error=str(e),
                ))

        results_list = await asyncio.gather(*[run_checker(c) for c in checkers])
        for name, check in results_list:
            results[name] = check
            if check.status == HealthStatus.ERROR:
                issues.append(f"[ERROR] {name}: {check.error}")
            elif check.status == HealthStatus.WARNING:
                issues.append(f"[WARN] {name}: {check.error or 'unknown warning'}")

        # 计算整体状态
        error_count = sum(1 for c in results.values() if c.status == HealthStatus.ERROR)
        warning_count = sum(1 for c in results.values() if c.status == HealthStatus.WARNING)

        if error_count > 0:
            overall = OverallStatus.UNHEALTHY
        elif warning_count > 0:
            overall = OverallStatus.DEGRADED
        else:
            overall = OverallStatus.HEALTHY

        return DetailedHealthResponse(
            status=overall,
            components=results,
            issues=issues,
        )