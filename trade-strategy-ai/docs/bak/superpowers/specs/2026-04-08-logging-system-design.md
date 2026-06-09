# P5-017 日志系统结构设计

## 1. 背景与目标

设计一个统一的日志系统，支持结构化日志采集、过滤、输出，满足以下场景：

- **日常调试**：CLI 运行时查看实时日志
- **问题排查**：日志持久化到文件，支持关键字搜索
- **监控告警**：日志级别告警（如 ERROR 触发告警）
- **审计追踪**：记录关键业务操作（交易建议生成、复盘触发等）

**目标**：
1. 结构化日志（JSON 格式）
2. 多输出目标（console / file / remote）
3. 日志级别控制
4. 上下文注入（trader_id、timestamp、trace_id）
5. 统一日志接口

## 2. 核心概念

### 2.1 LogEntry（日志条目）

```python
@dataclass
class LogEntry:
    """结构化日志条目。"""
    timestamp: datetime
    level: LogLevel  # DEBUG / INFO / WARNING / ERROR / CRITICAL
    logger: str  # logger 名称，如 "trader_agent"
    message: str
    trace_id: str | None  # 分布式追踪 ID
    trader_id: str | None  # 交易员 ID
    extra: dict[str, Any]  # 额外字段
```

### 2.2 LogLevel（日志级别）

```python
class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
```

## 3. 日志系统架构

```
+----------------+
|  Application   |
|   (structured  |
|    log calls)  |
+--------+-------+
         |
         v
+--------+---------+
|  LogProcessor   |  ← Filter → Transform → Enrich
+--------+---------+
         |
         v
+--------+---------+
|  OutputHandlers |  ← Console / File / Remote(Syslog/OTLP)
+-----------------+
```

## 4. 核心组件

### 4.1 StructuredLogger

```python
class StructuredLogger:
    """结构化日志记录器。

    用法：
        logger = get_logger("trader_agent")

        # 基本日志
        logger.info("生成交易建议", extra={"symbol": "000001.SZ"})

        # 带 trader_id
        logger.info("生成交易建议",
            trader_id="trader_a",
            extra={"symbol": "000001.SZ", "action": "buy"}
        )

        # 异常日志
        try:
            ...
        except Exception as e:
            logger.error("交易建议生成失败", exc_info=e)
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        handlers: list[OutputHandler] | None = None,
    ):
        self.name = name
        self.level = level
        self.handlers = handlers or [ConsoleHandler()]
        self._context: dict[str, Any] = {}

    def set_context(self, **kwargs) -> None:
        """设置日志上下文（自动注入到每条日志）。"""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """清除日志上下文。"""
        self._context.clear()

    def debug(self, message: str, **kwargs) -> None: ...
    def info(self, message: str, **kwargs) -> None: ...
    def warning(self, message: str, **kwargs) -> None: ...
    def error(self, message: str, exc_info: Exception | None = None, **kwargs) -> None: ...
    def critical(self, message: str, **kwargs) -> None: ...
```

### 4.2 OutputHandler（输出处理器）

```python
class OutputHandler(ABC):
    """输出处理器基类。"""

    @abstractmethod
    def emit(self, entry: LogEntry) -> None:
        """输出单条日志。"""
        ...

    @abstractmethod
    def flush(self) -> None:
        """刷新缓冲区。"""
        ...


class ConsoleHandler(OutputHandler):
    """控制台输出。"""
    def __init__(self, colorize: bool = True): ...


class FileHandler(OutputHandler):
    """文件输出。"""
    def __init__(
        self,
        path: str | Path,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        format: str = "json",  # "json" | "text"
    ): ...


class SyslogHandler(OutputHandler):
    """Syslog 输出（支持远程日志收集）。"""
    def __init__(self, host: str, port: int = 514, protocol: str = "udp"): ...


class RotatingFileHandler(FileHandler):
    """滚动文件输出。"""
    def __init__(
        self,
        path: str | Path,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ): ...
```

### 4.3 LogProcessor（日志处理器）

```python
class LogProcessor:
    """日志处理器。

    支持过滤、转换、丰富化。
    """

    def __init__(self):
        self._filters: list[Filter] = []
        self._transformers: list[Transformer] = []

    def add_filter(self, filter: Filter) -> None: ...
    def add_transformer(self, transformer: Transformer) -> None: ...

    def process(self, entry: LogEntry) -> LogEntry | None:
        """处理日志条目。

        - 先过过滤器
        - 再过转换器
        - 返回处理后的条目（None 表示丢弃）
        """
        ...


class Filter(ABC):
    """过滤器。"""

    @abstractmethod
    def accept(self, entry: LogEntry) -> bool: ...


class LevelFilter(Filter):
    """级别过滤器。"""
    def __init__(self, min_level: LogLevel): ...


class RegexFilter(Filter):
    """正则过滤器。"""
    def __init__(self, pattern: str): ...


class ContextFilter(Filter):
    """上下文过滤器。"""
    def __init__(self, key: str, value: Any): ...


class Transformer(ABC):
    """转换器。"""

    @abstractmethod
    def transform(self, entry: LogEntry) -> LogEntry: ...


class AddTraceId(Transformer):
    """添加 Trace ID。"""
    def __init__(self, generator: Callable[[], str]): ...


class AddTimestamp(Transformer):
    """添加时间戳。"""
    ...
```

## 5. 日志配置

### 5.1 YAML 配置

```yaml
logging:
  version: 1
  level: INFO  # 全局级别

  handlers:
    console:
      type: console
      colorize: true

    file:
      type: rotating_file
      path: logs/app.log
      max_bytes: 10485760  # 10MB
      backup_count: 5
      format: json

    error_file:
      type: rotating_file
      path: logs/error.log
      level: ERROR
      format: json

  loggers:
    trader_agent:
      level: INFO
      handlers: [console, file]
      propagate: false

    alignment_agent:
      level: DEBUG
      handlers: [console, file]
      propagate: false

    scheduler:
      level: INFO
      handlers: [console, file]
      propagate: false

  # 全局上下文
  context:
    app_name: trade-strategy-ai
    version: "1.0.0"
```

### 5.2 配置加载器

```python
class LogConfig:
    """日志配置加载器。"""

    @staticmethod
    def from_yaml(path: str | Path) -> "LogConfig": ...

    def setup(self) -> None:
        """配置全局日志系统。"""
        ...

    def get_logger(self, name: str) -> StructuredLogger:
        """获取 logger。"""
        ...
```

## 6. 使用示例

### 6.1 基本使用

```python
from src.logging import get_logger, setup_logging

# 初始化（从配置文件）
setup_logging("config/logging.yaml")

# 获取 logger
logger = get_logger("trader_agent")

# 记录日志
logger.info("生成交易建议", extra={
    "symbol": "000001.SZ",
    "action": "buy",
    "confidence": 0.85,
})

# 带 trader_id
logger.info("Trader A 生成建议",
    trader_id="trader_a",
    extra={"symbol": "000001.SZ"}
)
```

### 6.2 带异常的日志

```python
try:
    result = generate_idea()
except Exception as e:
    logger.error(
        "生成交易建议失败",
        exc_info=e,
        extra={"symbol": symbol, "trader_id": trader_id}
    )
```

### 6.3 上下文注入

```python
# 设置全局上下文
logger.set_context(trader_id="trader_a", session_id="sess_123")

# 后续所有日志自动带上 trader_id 和 session_id
logger.info("操作1")
logger.info("操作2")

# 清除上下文
logger.clear_context()
```

## 7. 日志输出格式

### 7.1 JSON 格式

```json
{
  "timestamp": "2026-04-08T10:30:00.123456",
  "level": "INFO",
  "logger": "trader_agent",
  "message": "生成交易建议",
  "trace_id": "abc123",
  "trader_id": "trader_a",
  "extra": {
    "symbol": "000001.SZ",
    "action": "buy",
    "confidence": 0.85
  }
}
```

### 7.2 文本格式（Console）

```
2026-04-08 10:30:00 [INFO] trader_agent: 生成交易建议 symbol=000001.SZ action=buy confidence=0.85
```

### 7.3 错误日志（Console）

```
2026-04-08 10:30:00 [ERROR] trader_agent: 生成交易建议失败
  Traceback (most recent call last):
    ...
  ValueError: invalid symbol
    extra={symbol: "INVALID"}
```

## 8. 文件结构

```
src/logging/
    __init__.py        # 统一导出
    levels.py          # LogLevel
    entry.py           # LogEntry
    handlers.py        # OutputHandler, ConsoleHandler, FileHandler
    processor.py       # LogProcessor, Filter, Transformer
    logger.py          # StructuredLogger
    config.py          # LogConfig, YAML 加载
    context.py         # LogContext

tests/unit/logging/
    test_logger.py
    test_handlers.py
    test_processor.py
    test_config.py
```

## 9. 技术选型

- **标准库实现**：使用 `logging` 模块作为底层
- **结构化**：自定义 `StructuredLogger` 封装
- **配置格式**：YAML（与 app.yaml 保持一致）
- **无需额外依赖**

## 10. 与现有系统集成

### 10.1 与 Scheduler 集成

```python
class Scheduler:
    def __init__(self):
        self.logger = get_logger("scheduler")
        self.logger.set_context(component="scheduler")

    async def trigger_dag(self, dag_id: str):
        self.logger.info(f"触发 DAG: {dag_id}")
        try:
            await self._execute(dag_id)
            self.logger.info(f"DAG 完成: {dag_id}")
        except Exception as e:
            self.logger.error(f"DAG 失败: {dag_id}", exc_info=e)
```

### 10.2 与 Agent 集成

```python
class TraderAgent:
    def __init__(self, trader_id: str):
        self.logger = get_logger("trader_agent")
        self.logger.set_context(trader_id=trader_id)

    async def generate_idea(self):
        self.logger.info("生成交易建议")
        # ...
```

## 11. 验证方式

1. **配置加载**：从 YAML 加载配置并正确设置 logger
2. **日志输出**：JSON 格式包含所有必要字段
3. **上下文注入**：logger.set_context() 后所有日志自动带上下文
4. **级别过滤**：低于配置的日志级别不输出
5. **异常日志**：exc_info=True 时正确输出堆栈
