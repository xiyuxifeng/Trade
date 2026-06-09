# S7-007 告警系统 — 设计方案

> 日期：2026-04-29
> 任务：NTL-S7-007

## 1. 目标

扩展告警系统，接入 8 种告警维度（A–H），支持多渠道（钉钉/飞书/企业微信/generic）推送，告警聚合去重，持久化到 DB，结构化日志输出到 `alert.log`。

## 2. 架构概览

```
AlertChannel Formatter（可插拔）
├── DingTalkFormatter   → 钉钉群机器人 Markdown
├── FeishuFormatter     → 飞书群机器人 Markdown
├── WeComFormatter      → 企业微信机器人 Markdown
└── GenericFormatter     → 原始 JSON

AlertAggregator（合并）
└── 同一 aggregation_key 在时间窗口内合并成一条发送

AlertHistory（DB 持久化）
└── alert_history 表 → API 查询/确认/解决

AlertLogger（结构化日志）
└── data/logs/alert.log — JSON 行格式

Alert Channels（8 种告警接入点）
├── A: 快照缺失（snapshot_tasks.py）
├── B: Provider 失败（snapshot_tasks.py / provider）
├── C: 数据新鲜度（已有规则扩展）
├── D: Pipeline 失败（PipelineHealthChecker）
├── E: DB 异常（DB health checker）
├── F: Circuit Breaker（熔断器状态）
├── G: Agent 异常（ManagerAgent）
└── H: 回测任务失败（backtest CLI）
```

## 3. AlertChannel 配置

```yaml
alerting:
  enabled: true
  channel: "dingtalk"          # dingtalk / feishu / wecom / generic
  aggregation:
    window_minutes: 60         # 合并时间窗口（分钟）
    max_count: 100             # 超过此数量则分段发送
  dingtalk:
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
    secret: ""                 # 可选，加签密钥（Webhook 安全性）
  feishu:
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  wecom:
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  min_level: "WARNING"        # 只发送 >= 此级别的告警
```

### 3.1 渠道 Payload 格式

**DingTalk / Feishu / WeCom（Markdown）：**
```
### [WARNING] 快照构建失败

**时间：** 2026-04-29 17:35:00
**交易日期：** 2026-04-29
**Slot：** 17-30
**类型：** hot_topics
**错误：** Connection timeout

> 涉及标签：snapshot, provider
```

**Generic（JSON）：**
```json
{
  "id": "uuid",
  "level": "WARNING",
  "title": "快照构建失败",
  "message": "Connection timeout",
  "timestamp": "2026-04-29T17:35:00",
  "tags": ["snapshot", "provider"],
  "metadata": {...}
}
```

## 4. 告警聚合逻辑

同一 `aggregation_key`（规则名 + tags 组合）在时间窗口内多条告警合并成一条：

```
aggregation_key = "{rule_name}:{sorted_tags_hash}"
# 例如："snapshot_missing:kaipan:hot_topics"
```

- 窗口内每条新告警累加到计数器
- 窗口结束或达到 `max_count` → 发送聚合告警
- 聚合告警包含：`aggregated_count`、`aggregation_window_start`、`last_error`

**合并消息示例：**
```
[WARNING] Provider 失败聚合（告警合并）

时间窗口：2026-04-29 16:00 ~ 17:00
累计次数：12 次
最近一次错误：Connection timeout
涉及 Provider：kaipan
影响数据：hot_topics, topic_constituents
```

## 5. AlertHistory 表

```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    channel VARCHAR(50) NOT NULL,
    tags JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'pending',
    aggregated_count INT DEFAULT 1,
    aggregation_key VARCHAR(255),
    aggregation_window_start TIMESTAMP,
    sent_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alert_history_status ON alert_history(status);
CREATE INDEX idx_alert_history_level ON alert_history(level);
CREATE INDEX idx_alert_history_created_at ON alert_history(created_at);
CREATE INDEX idx_alert_history_aggregation_key ON alert_history(aggregation_key);
```

## 6. 结构化日志

所有告警事件写入 `data/logs/alert.log`，每行 JSON：

```json
{"ts":"2026-04-29T17:35:00","level":"WARNING","title":"快照构建失败","channel":"dingtalk","status":"sent","aggregation_count":1,"tags":["snapshot","missing"],"metadata":{...}}
{"ts":"2026-04-29T17:40:00","level":"WARNING","title":"Provider 失败聚合","channel":"dingtalk","status":"sent","aggregation_count":12,"aggregation_key":"provider:kaipan:hot_topics","tags":["provider","kaipan"],"metadata":{...}}
```

日志字段：
- `ts`：ISO 格式时间戳
- `level`：CRITICAL / WARNING / INFO
- `title`：告警标题
- `channel`：发送渠道
- `status`：pending / sent / failed / acknowledged / resolved
- `aggregation_count`：聚合数量（未合并时为 1）
- `aggregation_key`：聚合 key（未合并时为空）
- `tags`：标签列表
- `metadata`：原始告警元数据

## 7. API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /alerts/history` | GET | 查询告警历史（支持 status/level/date_from/date_to 过滤，分页） |
| `GET /alerts/history/{id}` | GET | 告警详情 |
| `POST /alerts/{id}/acknowledge` | POST | 确认告警 |
| `POST /alerts/{id}/resolve` | POST | 解决告警 |
| `GET /alerts/channels` | GET | 查看已配置的通知渠道状态 |
| `POST /alerts/test` | POST | 发送测试告警（验证 Webhook 配置） |

### 7.1 查询参数（GET /alerts/history）

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 过滤状态：pending / sent / acknowledged / resolved |
| level | string | 过滤级别：CRITICAL / WARNING / INFO |
| tag | string | 过滤标签（可多次指定） |
| date_from | string | 开始日期 YYYY-MM-DD |
| date_to | string | 结束日期 YYYY-MM-DD |
| skip | int | 偏移量（默认 0） |
| limit | int | 返回数量（默认 50，最大 100） |

## 8. 告警接入点（8 种维度）

| 维度 | 触发条件 | 级别 | aggregation_key 示例 | tags |
|------|----------|------|----------------------|------|
| **A 快照缺失** | Slot（如 17-30）在收盘后 N 分钟内未生成快照 | WARNING | `snapshot_missing:{date}:{slot}` | `["snapshot", "missing"]` |
| **B Provider 失败** | Kaipan/AkShare 返回 error status | WARNING | `provider:{provider}:{capability}` | `["provider", "kaipan"]` |
| **C 数据新鲜度** | 文章/交易/行情数据 > 24h 未更新 | WARNING | `freshness:{data_type}` | `["freshness", "articles"]` |
| **D Pipeline 失败** | Pipeline 运行失败或 partial | CRITICAL | `pipeline:{pipeline_name}:{node}` | `["pipeline", "failed"]` |
| **E DB 异常** | DB 连接失败 / 查询超时 | CRITICAL | `database:{error_type}` | `["database", "error"]` |
| **F Circuit Breaker** | 熔断器跳闸 | WARNING | `circuit_breaker:{provider}:{capability}` | `["circuit_breaker", "open"]` |
| **G Agent 异常** | ManagerAgent 跑日报失败 | WARNING | `agent:{agent_name}:{run_type}` | `["agent", "failed"]` |
| **H 回测失败** | 回测任务执行失败 | WARNING | `backtest:{task_id}` | `["backtest", "failed"]` |

## 9. 文件结构

```
src/alerting/
├── __init__.py           # 导出 AlertManager, AlertEvent, AlertLevel
├── models.py             # AlertEvent, AlertLevel, AlertRule（已存在）
├── manager.py            # AlertManager（已存在）
├── notifiers.py          # ConsoleNotifier, WebhookNotifier, MemoryNotifier, CompositeNotifier（已存在）
├── channels/             # 新增：渠道格式化层
│   ├── __init__.py
│   ├── base.py           # ChannelFormatter 抽象基类
│   ├── dingtalk.py       # DingTalkFormatter
│   ├── feishu.py         # FeishuFormatter
│   ├── wecom.py          # WeComFormatter
│   └── generic.py        # GenericFormatter（原始 JSON）
├── aggregator.py         # 新增：告警聚合逻辑
├── logger_.py            # 新增：alert.log 结构化日志
├── db.py                 # 新增：AlertHistory ORM + Repository
├── rules/                # 新增：8 种告警规则
│   ├── __init__.py
│   ├── snapshot_rules.py # A: 快照缺失
│   ├── provider_rules.py # B: Provider 失败
│   ├── freshness_rules.py # C: 数据新鲜度
│   ├── pipeline_rules.py # D: Pipeline 失败
│   ├── db_rules.py       # E: DB 异常
│   ├── circuit_rules.py  # F: Circuit Breaker
│   ├── agent_rules.py    # G: Agent 异常
│   └── backtest_rules.py # H: 回测失败
└── config.py             # 新增：从 app.yaml 加载告警配置

api/routers/
├── alerts.py             # 新增：告警历史 API

tests/
├── cli/
│   └── test_alerts.py    # 新增：告警 API 测试
└── unit/
    └── alerting/         # 新增：告警单元测试
        ├── test_channels.py
        ├── test_aggregator.py
        └── test_db.py
```

## 10. 验收标准

- [ ] `python -m cli.main --help` 显示新子命令（如有）
- [ ] `GET /alerts/history` 返回告警历史（分页过滤正常）
- [ ] `POST /alerts/{id}/acknowledge` 状态变更为 acknowledged
- [ ] `POST /alerts/{id}/resolve` 状态变更为 resolved
- [ ] `POST /alerts/test` 发送测试告警到配置的 Webhook
- [ ] 告警同时写入 `data/logs/alert.log`
- [ ] Provider 失败触发告警（模拟失败场景）
- [ ] 快照缺失触发告警（指定过期 slot）
- [ ] 聚合告警正确合并（同一 key 多次触发合并为一条）
- [ ] 切换 channel 配置（dingtalk → feishu）不影响其他逻辑
- [ ] 单元测试全部 PASS
