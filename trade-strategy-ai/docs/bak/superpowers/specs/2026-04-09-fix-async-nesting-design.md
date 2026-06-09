# Fix: FastAPI 异步嵌套问题

> 日期：2026-04-09
> 问题来源：`docs/issues.md` 高优先级问题 1

## 目标

修复 `src/api/main.py` 中 `/run/pre_market`、`/run/after_close`、`/host/command` 三个接口在 FastAPI 异步上下文中的事件循环嵌套问题。

## 问题根因

- FastAPI 路由是 `async def`，运行在已有事件循环中
- `handle_command()` 是同步函数，内部调用 `asyncio.run()` 创建新循环
- 在已有事件循环中调用 `asyncio.run()` 会触发嵌套循环错误

## 方案 B：职责分离

**新增 `handle_command_async()`**：
- 异步版本，供 FastAPI 路由直接 `await` 调用
- 内部直接 `await mgr.run_pre_market()` / `await mgr.run_after_close()`

**保留 `handle_command()`**：
- 标记 `@deprecated`
- 保留给 CLI 或其他同步调用方使用（少见场景）

### 接口设计

**新增 `src/host/handler.py`**：

```python
async def handle_command_async(command: dict[str, Any]) -> dict[str, Any]:
    """Async handler for FastAPI integration.

    Args:
        command: HostCommand dict

    Returns:
        HostResponse as dict
    """
    cmd = HostCommand.model_validate(command)
    loaded = load_app_config(cmd.config_path)
    base_dir = _project_base_dir(loaded.config_path)
    mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
    as_of = cmd.as_of_date or date.today()

    try:
        if cmd.type == "run_pre_market":
            report = await mgr.run_pre_market(as_of_date=as_of, force=cmd.force)
            return HostResponse(type=cmd.type, payload=report.model_dump()).model_dump()
        if cmd.type == "run_after_close":
            result = await mgr.run_after_close(as_of_date=as_of, force=cmd.force)
            return HostResponse(type=cmd.type, payload=result.model_dump()).model_dump()
        # ... persona_init_sample 逻辑保持不变
        return HostResponse(ok=False, type=cmd.type, errors=[f"Unknown command type: {cmd.type}"]).model_dump()
    except Exception as exc:
        return HostResponse(ok=False, type=cmd.type, errors=[str(exc)]).model_dump()
```

**修改 `src/host/__init__.py`**：

```python
from .handler import handle_command, handle_command_async

__all__ = ["handle_command", "handle_command_async"]
```

**修改 `src/api/main.py`**：

- `trigger_pre_market`：改为 `await handle_command_async(command)`
- `trigger_after_close`：改为 `await handle_command_async(command)`
- `host_command`：改为 `await handle_command_async(command)`

## 错误语义修复

原问题：业务失败（如 force=False 但报告已存在）时返回 `ok=True`。

修改 `HostResponse` 返回逻辑：
- 只有真正成功时才返回 `ok=True`（默认）
- 命令类型未知或异常时才返回 `ok=False`

对于 `run_pre_market`/`run_after_close`：
- 如果 `force=False` 且报告/评估已存在，返回已有的结果（业务上这不是错误，不应触发 `ok=False`）
- 如果真正发生异常（如数据库错误），返回 `ok=False`

## 测试验证点

1. 直接调用 `handle_command_async` 不再触发嵌套事件循环错误
2. FastAPI 路由在 `uvicorn` 下正常响应
3. `HostResponse` 语义正确：真正失败返回 `ok=False`

## 涉及文件

- `src/host/handler.py` - 新增 `handle_command_async`，保留 `handle_command`（标记 deprecated）
- `src/host/__init__.py` - 导出 `handle_command_async`
- `src/api/main.py` - 三个路由改为调用 `handle_command_async`
