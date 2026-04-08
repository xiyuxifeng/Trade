# P5-018 Prometheus + Grafana 配置

## 1. 背景与目标

配置 Prometheus 指标采集和 Grafana 可视化面板，实现对系统的全面监控。

**目标**：
1. 定义核心指标（DSL 执行、Agent 调用、Pipeline 状态）
2. 配置 Prometheus scrape targets
3. 创建 Grafana 仪表板
4. 定义告警规则

## 2. 核心指标定义

### 2.1 DSL 相关指标

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `dsl_compile_total` | Counter | `status=success/failure` | DSL 编译次数 |
| `dsl_compile_duration_seconds` | Histogram | `rule_type` | 编译耗时 |
| `dsl_execute_total` | Counter | `rule_id`, `status` | DSL 执行次数 |
| `dsl_execute_duration_seconds` | Histogram | `rule_id` | 执行耗时 |
| `dsl_rule_matches_total` | Counter | `rule_id`, `rule_type` | 规则匹配次数 |

### 2.2 Agent 相关指标

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `agent_invoke_total` | Counter | `agent`, `status` | Agent 调用次数 |
| `agent_invoke_duration_seconds` | Histogram | `agent` | Agent 调用耗时 |
| `agent_errors_total` | Counter | `agent`, `error_type` | Agent 错误次数 |
| `llm_calls_total` | Counter | `provider`, `model`, `status` | LLM 调用次数 |
| `llm_call_duration_seconds` | Histogram | `provider`, `model` | LLM 调用耗时 |
| `llm_tokens_total` | Counter | `provider`, `model`, `type=input/output` | Token 消耗 |

### 2.3 Pipeline 相关指标

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `pipeline_tasks_total` | Counter | `task_type`, `status` | Pipeline 任务数 |
| `pipeline_task_duration_seconds` | Histogram | `task_type` | 任务执行耗时 |
| `pipeline_pending_tasks` | Gauge | `task_type` | 待处理任务数 |
| `pipeline_failed_tasks` | Gauge | `task_type` | 失败任务数 |
| `crawl_articles_total` | Counter | `source`, `status` | 爬取文章数 |
| `crawl_duration_seconds` | Histogram | `source` | 爬取耗时 |

### 2.4 系统指标

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `system_uptime_seconds` | Gauge | `service` | 服务运行时间 |
| `memory_usage_bytes` | Gauge | `service` | 内存使用 |
| `cpu_usage_percent` | Gauge | `service` | CPU 使用率 |

## 3. Prometheus 配置

### 3.1 prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - "rules/*.yml"

scrape_configs:
  # trade-strategy-ai 应用
  - job_name: 'trade-strategy-ai'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 3.2 告警规则 rules/alerts.yml

```yaml
groups:
  - name: dsl_alerts
    rules:
      - alert: DSLCompileFailureRate
        expr: |
          rate(dsl_compile_total{status="failure"}[5m])
          / rate(dsl_compile_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DSL 编译失败率超过 10%"
          description: "DSL 编译连续 5 分钟失败率超过 10%"

      - alert: DSLExecuteSlow
        expr: |
          histogram_quantile(0.95, rate(dsl_execute_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DSL 执行 P95 延迟超过 1 秒"

  - name: agent_alerts
    rules:
      - alert: AgentHighErrorRate
        expr: |
          rate(agent_errors_total[5m])
          / rate(agent_invoke_total[5m]) > 0.05
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Agent 错误率超过 5%"

      - alert: LLMCallLatencyHigh
        expr: |
          histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM 调用 P95 延迟超过 30 秒"

  - name: pipeline_alerts
    rules:
      - alert: PipelineTasksStuck
        expr: pipeline_pending_tasks > 100
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "Pipeline 任务堆积超过 100 个"

      - alert: CrawlFailureRate
        expr: |
          rate(crawl_articles_total{status="failure"}[5m])
          / rate(crawl_articles_total[5m]) > 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "爬虫失败率超过 20%"
```

## 4. Grafana 配置

### 4.1 数据源 provisioning datasources/datasource.yml

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"
```

### 4.2 仪表板 provisioning dashboards/dashboards.yml

```yaml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

### 4.3 DSL 执行仪表板 dashboards/dsl-execution.json

```json
{
  "dashboard": {
    "title": "DSL 执行监控",
    "uid": "dsl-execution",
    "timezone": "browser",
    "panels": [
      {
        "title": "DSL 编译 QPS",
        "type": "stat",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "rate(dsl_compile_total[5m])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "DSL 编译耗时 P50/P95/P99",
        "type": "timeseries",
        "gridPos": {"x": 6, "y": 0, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(dsl_compile_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(dsl_compile_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(dsl_compile_duration_seconds_bucket[5m]))",
            "legendFormat": "P99"
          }
        ]
      },
      {
        "title": "DSL 执行次数（按规则）",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(dsl_execute_total[5m])",
            "legendFormat": "{{rule_id}}"
          }
        ]
      },
      {
        "title": "规则匹配率",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(dsl_rule_matches_total[5m]) / rate(dsl_execute_total[5m])",
            "legendFormat": "{{rule_id}}"
          }
        ]
      }
    ]
  }
}
```

### 4.4 Agent 监控仪表板 dashboards/agent-monitoring.json

```json
{
  "dashboard": {
    "title": "Agent 监控",
    "uid": "agent-monitoring",
    "panels": [
      {
        "title": "Agent 调用 QPS",
        "type": "stat",
        "gridPos": {"x": 0, "y": 0, "w": 8, "h": 4},
        "targets": [
          {
            "expr": "sum(rate(agent_invoke_total[5m])) by (agent)",
            "legendFormat": "{{agent}}"
          }
        ]
      },
      {
        "title": "Agent 调用耗时 P95",
        "type": "timeseries",
        "gridPos": {"x": 8, "y": 0, "w": 16, "h": 4},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_invoke_duration_seconds_bucket[5m])) by (agent)",
            "legendFormat": "{{agent}}"
          }
        ]
      },
      {
        "title": "LLM 调用耗时 P95",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(llm_call_duration_seconds_bucket[5m])) by (model)",
            "legendFormat": "{{model}}"
          }
        ]
      },
      {
        "title": "LLM Token 消耗",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(llm_tokens_total[5m]) by (type)",
            "legendFormat": "{{type}}"
          }
        ]
      }
    ]
  }
}
```

### 4.5 Pipeline 监控仪表板 dashboards/pipeline-monitoring.json

```json
{
  "dashboard": {
    "title": "Pipeline 监控",
    "uid": "pipeline-monitoring",
    "panels": [
      {
        "title": "任务队列深度",
        "type": "gauge",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "pipeline_pending_tasks",
            "legendFormat": "{{task_type}}"
          }
        ]
      },
      {
        "title": "任务执行速率",
        "type": "timeseries",
        "gridPos": {"x": 6, "y": 0, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(pipeline_tasks_total[5m]) by (task_type)",
            "legendFormat": "{{task_type}}"
          }
        ]
      },
      {
        "title": "任务失败数",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(pipeline_tasks_total{status=\"failure\"}[5m]) by (task_type)",
            "legendFormat": "{{task_type}}"
          }
        ]
      },
      {
        "title": "爬虫文章数",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 4, "w": 12, "h": 4},
        "targets": [
          {
            "expr": "rate(crawl_articles_total[5m]) by (source, status)",
            "legendFormat": "{{source}}/{{status}}"
          }
        ]
      }
    ]
  }
}
```

## 5. 指标埋点代码

### 5.1 指标注册中心

```python
# src/metrics/registry.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# 全局注册表
REGISTRY = CollectorRegistry()

# DSL 指标
DSL_COMPILE_TOTAL = Counter(
    "dsl_compile_total",
    "DSL 编译次数",
    ["status"],
    registry=REGISTRY,
)

DSL_COMPILE_DURATION = Histogram(
    "dsl_compile_duration_seconds",
    "DSL 编译耗时",
    ["rule_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=REGISTRY,
)

DSL_EXECUTE_TOTAL = Counter(
    "dsl_execute_total",
    "DSL 执行次数",
    ["rule_id", "status"],
    registry=REGISTRY,
)

DSL_EXECUTE_DURATION = Histogram(
    "dsl_execute_duration_seconds",
    "DSL 执行耗时",
    ["rule_id"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=REGISTRY,
)

# Agent 指标
AGENT_INVOKE_TOTAL = Counter(
    "agent_invoke_total",
    "Agent 调用次数",
    ["agent", "status"],
    registry=REGISTRY,
)

AGENT_INVOKE_DURATION = Histogram(
    "agent_invoke_duration_seconds",
    "Agent 调用耗时",
    ["agent"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
    registry=REGISTRY,
)

# LLM 指标
LLM_CALLS_TOTAL = Counter(
    "llm_calls_total",
    "LLM 调用次数",
    ["provider", "model", "status"],
    registry=REGISTRY,
)

LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM 调用耗时",
    ["provider", "model"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "LLM Token 消耗",
    ["provider", "model", "type"],
    registry=REGISTRY,
)

# Pipeline 指标
PIPELINE_TASKS_TOTAL = Counter(
    "pipeline_tasks_total",
    "Pipeline 任务数",
    ["task_type", "status"],
    registry=REGISTRY,
)

PIPELINE_PENDING_TASKS = Gauge(
    "pipeline_pending_tasks",
    "待处理任务数",
    ["task_type"],
    registry=REGISTRY,
)

PIPELINE_FAILED_TASKS = Gauge(
    "pipeline_failed_tasks",
    "失败任务数",
    ["task_type"],
    registry=REGISTRY,
)

# Crawl 指标
CRAWL_ARTICLES_TOTAL = Counter(
    "crawl_articles_total",
    "爬取文章数",
    ["source", "status"],
    registry=REGISTRY,
)
```

### 5.2 DSL 执行埋点

```python
# src/persona/dsl_executor.py
import time
from src.metrics.registry import (
    DSL_EXECUTE_TOTAL,
    DSL_EXECUTE_DURATION,
    DSL_RULE_MATCHES_TOTAL,
)

class DSLExecutor:
    def execute(self, rule: CompiledRule, context: dict) -> bool:
        start = time.perf_counter()
        try:
            result = rule.matches(state=context.get("state"), bar=context.get("bar"))
            DSL_EXECUTE_TOTAL.labels(rule_id=rule.rule_id, status="success").inc()
            if result:
                DSL_RULE_MATCHES_TOTAL.labels(rule_id=rule.rule_id, rule_type=rule.rule_type).inc()
            return result
        except Exception as e:
            DSL_EXECUTE_TOTAL.labels(rule_id=rule.rule_id, status="failure").inc()
            raise
        finally:
            duration = time.perf_counter() - start
            DSL_EXECUTE_DURATION.labels(rule_id=rule.rule_id).observe(duration)
```

### 5.3 Agent 埋点

```python
# src/agents/base.py
import time
from src.metrics.registry import (
    AGENT_INVOKE_TOTAL,
    AGENT_INVOKE_DURATION,
)

class BaseAgent:
    async def invoke(self, input_data: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await self._do_invoke(input_data)
            AGENT_INVOKE_TOTAL.labels(agent=self.__class__.__name__, status="success").inc()
            return result
        except Exception as e:
            AGENT_INVOKE_TOTAL.labels(agent=self.__class__.__name__, status="failure").inc()
            raise
        finally:
            duration = time.perf_counter() - start
            AGENT_INVOKE_DURATION.labels(agent=self.__class__.__name__).observe(duration)
```

## 6. FastAPI 集成

### 6.1 /metrics 端点

```python
# src/api/metrics.py
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    from src.metrics.registry import REGISTRY
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
```

## 7. 文件结构

```
config/
  prometheus/
    prometheus.yml          # Prometheus 配置
    rules/
      alerts.yml            # 告警规则

provisioning/
  grafana/
    datasources/
      datasource.yml       # 数据源配置
    dashboards/
      dashboards.yml       # 仪表板配置
      dsl-execution.json   # DSL 执行仪表板
      agent-monitoring.json # Agent 监控仪表板
      pipeline-monitoring.json  # Pipeline 监控仪表板

src/
  metrics/
    __init__.py
    registry.py             # 指标注册表
    decorators.py          # @track_duration 等装饰器

docker-compose.yml           # Prometheus + Grafana 启动配置
```

## 8. Docker Compose 配置

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.45.0
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./provisioning/grafana:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana

  alertmanager:
    image: prom/alertmanager:v0.26.0
    ports:
      - "9093:9093"
    volumes:
      - ./config/alertmanager:/etc/alertmanager

volumes:
  prometheus_data:
  grafana_data:
```

## 9. 验证方式

1. **指标端点**：`curl localhost:8000/metrics` 返回 Prometheus 格式指标
2. **Grafana 仪表板**：登录 http://localhost:3000 查看仪表板
3. **告警触发**：模拟高错误率，观察告警是否触发
