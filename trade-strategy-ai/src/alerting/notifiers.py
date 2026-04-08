"""告警通知器。

提供多种告警通知渠道：
- AlertNotifier: 通知器基类接口
- ConsoleNotifier: 控制台通知器
- WebhookNotifier: 通用 Webhook 通知器
- MemoryNotifier: 内存通知器（用于测试）
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from src.common.logger import get_logger
from src.alerting.models import AlertEvent, AlertLevel


logger = get_logger("alerting.notifier")


class AlertNotifier(ABC):
    """告警通知器抽象基类。"""

    @abstractmethod
    async def send(self, alert: AlertEvent) -> None:
        """发送单条告警通知。

        Args:
            alert: 告警事件
        """
        ...

    async def send_batch(self, alerts: list[AlertEvent]) -> None:
        """批量发送告警通知。

        默认实现是遍历发送，可以被子类优化。

        Args:
            alerts: 告警事件列表
        """
        for alert in alerts:
            try:
                await self.send(alert)
            except Exception as e:
                logger.error("failed to send alert: %s", str(e), extra={"alert_id": alert.id})


class ConsoleNotifier(AlertNotifier):
    """控制台通知器（开发/调试用）。

    将告警以彩色格式输出到控制台。
    """

    def __init__(self, colorize: bool = True) -> None:
        """初始化控制台通知器。

        Args:
            colorize: 是否使用 ANSI 颜色
        """
        self.colorize = colorize

    async def send(self, alert: AlertEvent) -> None:
        """发送告警到控制台。"""
        level_str = str(alert.level)
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        if self.colorize:
            color = self._get_color(alert.level)
            prefix = f"\033[{color}m"
            suffix = "\033[0m"
            header = f"{prefix}[{level_str}]{suffix}"
        else:
            header = f"[{level_str}]"

        logger.warning(
            "%s %s | %s: %s",
            timestamp,
            header,
            alert.title,
            alert.message,
        )

        # 如果有额外元数据，也打印出来
        if alert.metadata:
            logger.debug("alert metadata: %s", alert.metadata)

    def _get_color(self, level: AlertLevel) -> str:
        """获取 ANSI 颜色代码。"""
        colors = {
            AlertLevel.INFO: "94",  # 蓝色
            AlertLevel.WARNING: "93",  # 黄色
            AlertLevel.CRITICAL: "91",  # 红色
        }
        return colors.get(level, "0")


class WebhookNotifier(AlertNotifier):
    """通用 Webhook 通知器。

    将告警以 JSON 格式 POST 到指定 URL。
    支持：
    - 自定义 HTTP 方法（POST/PUT）
    - 自定义请求头
    - 超时配置
    """

    def __init__(
        self,
        url: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
        verify_ssl: bool = True,
    ) -> None:
        """初始化 Webhook 通知器。

        Args:
            url: Webhook URL
            method: HTTP 方法（POST 或 PUT）
            headers: 自定义请求头
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证 SSL 证书
        """
        self.url = url
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    async def send(self, alert: AlertEvent) -> None:
        """发送告警到 Webhook。"""
        payload = json.dumps(alert.to_dict()).encode("utf-8")

        request = Request(
            self.url,
            data=payload,
            headers=self.headers,
            method=self.method,
        )

        try:
            # Webhook 调用是同步的，放在线程池中执行
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._do_request,
                request,
            )
            logger.info("alert sent to webhook: %s", self.url, extra={"alert_id": alert.id})
        except Exception as e:
            logger.error(
                "failed to send alert to webhook %s: %s",
                self.url,
                str(e),
                extra={"alert_id": alert.id},
            )
            raise

    def _do_request(self, request: Request) -> None:
        """执行 HTTP 请求（同步）。"""
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if response.status >= 400:
                    logger.warning(
                        "webhook returned error status: %d",
                        response.status,
                    )
        except HTTPError as e:
            logger.error("webhook HTTP error: %d %s", e.code, e.reason)
            raise
        except URLError as e:
            logger.error("webhook URL error: %s", str(e.reason))
            raise


class MemoryNotifier(AlertNotifier):
    """内存通知器（用于测试和开发）。

    将所有告警存储在内存列表中，可以通过 get_alerts() 获取。
    """

    def __init__(self) -> None:
        """初始化内存通知器。"""
        self._alerts: list[AlertEvent] = []
        self._lock = asyncio.Lock()

    async def send(self, alert: AlertEvent) -> None:
        """将告警存储到内存。"""
        async with self._lock:
            self._alerts.append(alert)

    async def send_batch(self, alerts: list[AlertEvent]) -> None:
        """批量存储告警。"""
        async with self._lock:
            self._alerts.extend(alerts)

    def get_alerts(self) -> list[AlertEvent]:
        """获取所有存储的告警。"""
        return list(self._alerts)

    def clear(self) -> None:
        """清空所有告警。"""
        self._alerts.clear()

    @property
    def count(self) -> int:
        """获取告警数量。"""
        return len(self._alerts)

    def filter_by_level(self, level: AlertLevel) -> list[AlertEvent]:
        """按级别过滤告警。"""
        return [a for a in self._alerts if a.level == level]


class CompositeNotifier(AlertNotifier):
    """组合通知器。

    将告警同时发送到多个通知器。
    """

    def __init__(self, notifiers: list[AlertNotifier]) -> None:
        """初始化组合通知器。

        Args:
            notifiers: 子通知器列表
        """
        self.notifiers = notifiers

    async def send(self, alert: AlertEvent) -> None:
        """发送告警到所有子通知器。"""
        tasks = [notifier.send(alert) for notifier in self.notifiers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_batch(self, alerts: list[AlertEvent]) -> None:
        """批量发送告警到所有子通知器。"""
        tasks = [notifier.send_batch(alerts) for notifier in self.notifiers]
        await asyncio.gather(*tasks, return_exceptions=True)
