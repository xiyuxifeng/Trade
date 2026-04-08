# P1-026 数据监控 Dashboard 设计方案

## 状态
- **日期**：2026-04-07
- **状态**：已批准，待实现
- **对应任务**：P1-026

## 目标
建立数据监控 Dashboard，持续跟踪数据新鲜度、完整性，实现日常巡检自动化。

## 需求摘要
- **用途**：运营状态监控 + 质量问题追踪（两者兼顾）
- **部署**：本地 CLI 巡检 + 定时推送 + 静态 HTML 浏览 + 预留 FastAPI 接口
- **数据来源**：JSONL 报告（异常检测） + PostgreSQL（基础统计）
- **核心指标**：记录统计 + 新增数 + 最后入库时间 + 缺失率/重复率/异常率 + 异常详情
- **告警**：CLI 高亮输出（已实现），Webhook 推送（ backlog）

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│  DashboardService (核心服务层)                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │ StatsCollector│ │ QualityAnalyzer│ │ AlertManager     │   │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘   │
│         │                │                    │              │
│  ┌──────▼────────────────▼────────────────────▼─────────┐   │
│  │              DataSourceAdapter                       │   │
│  │         (JSONL Reader + PostgreSQL)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │  CLIRenderer │      │ HTMLRenderer│      │ APIRenderer │
    │  (Rich)      │      │ (Jinja2)     │      │ (FastAPI)   │
    └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 核心组件

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `StatsCollector` | 统计记录数、新增数、最后入库时间 | PG DB | `DashboardStats` |
| `QualityAnalyzer` | 分析缺失率/重复率/异常率 | JSONL 报告 + PG | `QualityMetrics` |
| `AlertManager` | 告警判断（日志高亮/退出码） | `QualityMetrics` | 告警事件 |
| `DashboardService` | 编排上述组件 | config | 统一数据模型 |
| `CLIRenderer` | Rich 表格渲染 | `DashboardStats` + `QualityMetrics` | 终端输出 |
| `HTMLRenderer` | Jinja2 模板渲染 | 同上 | 静态 HTML 文件 |
| `APIRenderer` | FastAPI 路由接口（后续） | 同上 | JSON 响应 |

---

## 数据模型

```python
@dataclass
class DashboardStats:
    articles: EntityStats
    trades: EntityStats
    market_data: EntityStats

@dataclass
class EntityStats:
    total: int
    today_new: int
    last_crawled_at: datetime | None
    freshness_hours: float | None

@dataclass
class QualityMetrics:
    total_issues: int
    by_severity: dict[str, int]
    by_code: dict[str, int]
    article_dup_rate: float
    market_missing_rate: float
    anomaly_details: list[ValidationIssue]
```

---

## 配置项

```yaml
# config/app.yaml 新增
dashboard:
  alerts:
    enabled: true
    freshness_threshold_hours: 24
    anomaly_rate_threshold: 5.0
  html_output_dir: data/processed/dashboard
  max_anomaly_details: 20
  alert_mode: both
```

---

## CLI 命令

```bash
# 终端巡检
python -m src.pipeline.dashboard --mode cli

# 生成静态 HTML
python -m src.pipeline.dashboard --mode html

# 两种都输出
python -m src.pipeline.dashboard --mode both
```

---

## 目录结构

```
src/pipeline/
  ├── dashboard.py              # 入口 + CLI
  ├── dashboard_service.py      # 核心服务
  ├── dashboard_renderers.py   # 渲染器（CLI/HTML）
  └── dashboard_models.py      # 数据模型
```

---

## 依赖
- `jinja2`：HTML 模板渲染
- `rich`：CLI 美化输出（可选，快速落地）

---

## 定时任务

通过 `schedule.dashboard_check_time` 配置每日定时巡检时间，结果输出到 CLI 和 HTML。

---

## 待后续实现（Backlog）
- Webhook 告警推送（飞书/Slack/钉钉）
- FastAPI 接口（APIRenderer）
- 前端 Web 页面

---

## 验证
- `python -m src.pipeline.dashboard --mode both` 无报错
- HTML 文件生成到 `data/processed/dashboard/`
- CLI 输出包含统计摘要和质量指标
- 单元测试覆盖核心逻辑
