import pytest
from src.logging.audit import log_agent_call, _sanitize

@pytest.mark.asyncio
async def test_log_agent_call():
    await log_agent_call(
        agent="test_agent",
        action="test_action",
        input_data={"key": "value"},
        output_data={"result": "ok"},
        duration_ms=10.5
    )

def test_sanitize_removes_sensitive():
    result = _sanitize({"password": "secret", "username": "user"})
    assert "password" not in result
    assert "username" in result