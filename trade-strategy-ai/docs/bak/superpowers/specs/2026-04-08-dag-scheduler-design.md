# P5-013 任务调度器 DAG 设计

## 1. 背景与目标

设计一个通用的任务调度器，支持有向无环图（DAG）执行顺序，满足以下场景：

- **Phase 0 闭环**：盘前 → 盘后 → 复盘的定时调度
- **Phase 1 数据管道**：crawl → clean → validate → store
- **Phase 2 增量处理**：pending_tasks 消费 → 规则抽取 → 对齐分析
- **Phase 4 策略执行**：规则编译 → 执行引擎 → 风控评估

**目标**：
1. 支持任务依赖声明（via DAG）
2. 支持定时触发（cron 表达式）
3. 支持事件触发（webhook / 消息队列）
4. 支持重试、死链、超时
5. 支持任务优先级和并发控制

## 2. 核心概念

### 2.1 Task（任务）

```python
@dataclass
class Task:
    task_id: str
    name: str
    fn: Callable[..., Coroutine[Any, Any, Any]]  # async 函数
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    retry_policy: RetryPolicy | None = None
    timeout: float | None = None  # 秒
    priority: int = 0
```

### 2.2 RetryPolicy（重试策略）

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 1.0  # 秒
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on: tuple[type[Exception], ...] = (Exception,)
```

### 2.3 DAG 定义

```python
class DAG:
    """DAG 定义。

    用法：
        dag = DAG("daily_pipeline")

        # 添加任务
        dag.add_task(Task(task_id="fetch_market", ...))
        dag.add_task(Task(task_id="generate_ideas", ...))
        dag.add_task(Task(task_id="evaluate", ...))

        # 声明依赖
        dag.add_edge("fetch_market", "generate_ideas")  # fetch → ideas
        dag.add_edge("generate_ideas", "evaluate")         # ideas → evaluate

        # 验证无环
        dag.validate()
    """

    def __init__(self, dag_id: str, description: str | None = None):
        self.dag_id = dag_id
        self.description = description
        self._tasks: dict[str, Task] = {}
        self._graph: dict[str, set[str]] = {}  # task_id -> 下游依赖

    def add_task(self, task: Task) -> None: ...
    def add_edge(self, upstream: str, downstream: str) -> None: ...
    def get_downstream(self, task_id: str) -> set[str]: ...
    def get_upstream(self, task_id: str) -> set[str]: ...
    def get_execution_order(self) -> list[str]: ...  # 返回拓扑排序
    def validate(self) -> bool: ...  # 检测环
```

### 2.4 Execution Plan（执行计划）

```python
@dataclass
class ExecutionPlan:
    dag_id: str
    tasks: list[str]  # 按拓扑排序的任务 ID 列表
    levels: dict[str, int]  # task_id -> 层级（可并行执行的同一层级）
```

## 3. 调度器设计

### 3.1 Scheduler（调度器）

```python
class Scheduler:
    """任务调度器。

    用法：
        scheduler = Scheduler()

        # 注册 DAG
        scheduler.register_dag(dag)

        # 添加触发器
        scheduler.add_cron_trigger("daily_pipeline", "0 8 * * *")  # 每天 8 点
        scheduler.add_cron_trigger("daily_pipeline", "0 15 * * *")  # 每天 15 点

        # 启动调度器
        await scheduler.start()
    """

    def __init__(self, max_concurrency: int = 10):
        self._dags: dict[str, DAG] = {}
        self._triggers: dict[str, list[Trigger]] = {}
        self._max_concurrency = max_concurrency
        self._running_tasks: set[str] = set()
        self._semaphore: asyncio.Semaphore

    def register_dag(self, dag: DAG) -> None: ...
    def add_cron_trigger(self, dag_id: str, cron_expr: str) -> None: ...
    def add_event_trigger(self, dag_id: str, event: str) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def trigger_dag(self, dag_id: str, context: dict | None = None) -> ExecutionResult: ...
```

### 3.2 Trigger（触发器）

```python
class Trigger(ABC):
    """触发器基类。"""
    @abstractmethod
    async def wait(self) -> None: ...
    @abstractmethod
    def describe(self) -> str: ...


class CronTrigger(Trigger):
    """Cron 触发器。"""
    def __init__(self, cron_expr: str): ...
    async def wait(self) -> None: ...


class EventTrigger(Trigger):
    """事件触发器。"""
    def __init__(self, event_name: str, queue: asyncio.Queue): ...
    async def wait(self) -> None: ...


class ManualTrigger(Trigger):
    """手动触发器。"""
    async def wait(self) -> None: ...  # 立即返回
```

## 4. 执行引擎

### 4.1 DAGExecutor

```python
class DAGExecutor:
    """DAG 执行器。

    按拓扑顺序执行 DAG 中的任务，支持并行和错误处理。
    """

    def __init__(self, max_concurrency: int = 10):
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute(
        self,
        dag: DAG,
        context: dict | None = None,
    ) -> DAGExecutionResult:
        """执行 DAG。

        Args:
            dag: DAG 定义
            context: 执行上下文（传递给每个任务）

        Returns:
            DAGExecutionResult
        """
        ...


@dataclass
class DAGExecutionResult:
    dag_id: str
    success: bool
    task_results: dict[str, TaskResult]
    start_time: datetime
    end_time: datetime
    duration_ms: float
    error: str | None


@dataclass
class TaskResult:
    task_id: str
    success: bool
    output: Any | None
    error: str | None
    attempts: int
    start_time: datetime
    end_time: datetime
```

### 4.2 并行执行策略

同一层级的任务可以并行执行：

```
Level 0: [task_a]
Level 1: [task_b, task_c]  → 并行
Level 2: [task_d]           → 等待 Level 1 完成
```

```python
async def _execute_level(
    self,
    tasks: list[str],
    dag: DAG,
    context: dict,
) -> dict[str, TaskResult]:
    """执行同一层级的任务（并行）。"""
    async with self._semaphore:
        results = await asyncio.gather(
            *[self._execute_task(tid, dag, context) for tid in tasks],
            return_exceptions=True,
        )
    return dict(zip(tasks, results))
```

## 5. 错误处理与重试

### 5.1 错误分类

```python
class TaskError(Exception):
    """任务执行错误。"""
    def __init__(self, task_id: str, original: Exception): ...

class DAGValidationError(Exception):
    """DAG 验证失败（如环检测）。"""
    pass

class CircularDependencyError(DAGValidationError):
    """循环依赖错误。"""
    pass
```

### 5.2 重试策略实现

```python
async def _execute_task_with_retry(
    self,
    task: Task,
    context: dict,
) -> TaskResult:
    """带重试的任务执行。"""
    policy = task.retry_policy or default_retry_policy
    last_error: Exception | None = None

    for attempt in range(policy.max_attempts):
        try:
            result = await asyncio.wait_for(
                task.fn(*task.args, **task.kwargs, **context),
                timeout=task.timeout,
            )
            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=result,
                error=None,
                attempts=attempt + 1,
                ...
            )
        except policy.retry_on as e:
            last_error = e
            if attempt < policy.max_attempts - 1:
                delay = min(
                    policy.initial_delay * (policy.exponential_base ** attempt),
                    policy.max_delay,
                )
                await asyncio.sleep(delay)

    return TaskResult(
        task_id=task.task_id,
        success=False,
        output=None,
        error=str(last_error),
        attempts=policy.max_attempts,
        ...
    )
```

## 6. 使用示例

### 6.1 盘前日报 DAG

```python
dag = DAG("daily_pre_market", "盘前日报流水线")

dag.add_task(Task(
    task_id="fetch_market",
    name="获取市场数据",
    fn=fetch_market_data,
))
dag.add_task(Task(
    task_id="analyze_regime",
    name="分析市场状态",
    fn=analyze_market_regime,
))
dag.add_task(Task(
    task_id="generate_ideas",
    name="生成交易建议",
    fn=generate_trade_ideas,
))
dag.add_task(Task(
    task_id="route_persona",
    name="Persona 路由",
    fn=route_by_persona,
))
dag.add_task(Task(
    task_id="compile_report",
    name="生成日报",
    fn=compile_daily_report,
))

# 声明依赖
dag.add_edge("fetch_market", "analyze_regime")
dag.add_edge("analyze_regime", "generate_ideas")
dag.add_edge("generate_ideas", "route_persona")
dag.add_edge("route_persona", "compile_report")

# 注册到调度器
scheduler.register_dag(dag)
scheduler.add_cron_trigger("daily_pre_market", "0 8 * * 1-5")  # 工作日 8 点
```

### 6.2 数据管道 DAG

```python
dag = DAG("data_pipeline", "数据管道")

dag.add_task(Task(task_id="crawl", fn=crawl_blogs, retry_policy=RetryPolicy(max_attempts=3)))
dag.add_task(Task(task_id="clean", fn=clean_content))
dag.add_task(Task(task_id="validate", fn=validate_data))
dag.add_task(Task(task_id="store", fn=store_to_db))
dag.add_task(Task(task_id="notify", fn=notify_completion))

dag.add_edge("crawl", "clean")
dag.add_edge("clean", "validate")
dag.add_edge("validate", "store")
dag.add_edge("store", "notify")
```

## 7. 文件结构

```
src/scheduler/
    __init__.py           # 统一导出
    task.py               # Task, RetryPolicy 定义
    dag.py                 # DAG 定义和验证
    executor.py           # DAGExecutor 实现
    scheduler.py          # Scheduler 主类
    triggers.py           # CronTrigger, EventTrigger
    exceptions.py         # 异常类
    context.py            # ExecutionContext

tests/unit/scheduler/
    test_dag.py          # DAG 测试
    test_executor.py     # Executor 测试
    test_scheduler.py    # Scheduler 测试
```

## 8. 技术选型

- **异步框架**：asyncio（Python 内置）
- **Cron 解析**：croniter
- **不需要额外依赖**：使用标准库实现

## 9. 验证方式

1. **DAG 环检测**：给定包含环的 DAG，`validate()` 抛出 `CircularDependencyError`
2. **拓扑排序**：给定 DAG，`get_execution_order()` 返回正确的执行顺序
3. **并行执行**：Level 0 → Level 1 → ... 的顺序，Level 内并行
4. **重试机制**：任务失败时按策略重试
5. **超时处理**：任务超时抛出 `asyncio.TimeoutError`
