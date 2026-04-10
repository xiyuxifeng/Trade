"""审计日志"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

async def log_agent_call(
    agent: str,
    action: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    duration_ms: float,
    error: str | None = None
):
    """
    记录 Agent 调用日志

    Args:
        agent: Agent 名称
        action: 操作名称
        input_data: 输入参数（脱敏后）
        output_data: 输出结果
        duration_ms: 耗时（毫秒）
        error: 错误信息（如有）
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "agent": agent,
        "action": action,
        "input": _sanitize(input_data),
        "output": _sanitize(output_data),
        "duration_ms": duration_ms,
        "error": error
    }

    logger.info(json.dumps(log_entry))

def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    """脱敏处理"""
    # 移除敏感信息
    sensitive_keys = {"password", "token", "secret", "api_key"}
    return {k: v for k, v in data.items() if k.lower() not in sensitive_keys}