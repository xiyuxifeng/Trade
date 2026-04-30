# 从文章到规则的生产级交易系统设计

> 日期：2026-04-30
> 目标：从文章提取可执行的交易规则，通过回测验证置信度，实现盘前预测和盘后归因
> 状态：设计初稿，待评审

---

## 1. 背景与目标

### 1.1 现有系统已提供

```
文章爬取 → 存储 blog_articles
    ↓
LLM 提取 → article_metadata (strategy_rules, preconditions)
    ↓
规则分类 → rule_registry (programmatic level)
    ↓
回测引擎 → BacktestEngine (NTL-S6)
    ↓
盘前/盘后 → run-pre-market / run-after-close
```

### 1.2 缺失的关键能力

| 缺失项 | 影响 |
|--------|------|
| 文章类型分类 | 无法区分规则型 vs 交易记录型文章 |
| 分层提取 | 混合文章中规则和交易记录混在一起，数据泄露风险 |
| 规则池 B | 没有独立规则管理 + 审核流程 |
| 两层 DSL | 描述性条件无法映射到可执行指标 |
| 回测触发机制 | 规则进入后不会自动验证 |
| 多指标置信度调整 | 单一置信度不可靠 |
| 盘前预测联动 | 规则池和预测系统没有打通 |
| 盘后规则归因 | 表现差时无法定位根因 |

### 1.3 设计目标

建立完整闭环：

```
文章 → 分类 → 分层提取 → 规则池B → 审核 → 回测验证 → 置信度调整
                                            ↓
盘前预测 ← 高置信度规则 ←──────────────┘
    ↓
盘后归因 → 规则评估/优化 → 更新置信度/移出规则池
```

---

## 2. 核心概念定义

### 2.1 四类文章

| 类型 | 定义 | 处理方式 |
|------|------|---------|
| **规则型** | 描述一般性交易规则/策略（非具体历史操作） | 提取 standalone_rules，进入规则池 B |
| **交易记录型** | 描述具体历史操作（时间、价格、数量明确） | 提取 trade_records，进入交易样本库，不回测 |
| **概念型** | 纯理论/框架/心态分享，无具体条件 | 提取为标签，进入知识库，不生成可执行规则 |
| **噪音型** | 个人观点、闲聊、新闻、无交易逻辑 | 最小化提取，标记"待复核-忽略" |

### 2.2 三类规则

| 类型 | 来源 | 可回测 | 置信度来源 |
|------|------|--------|-----------|
| **standalone_rules** | 规则型文章，原创方法论 | 是 | 回测验证 |
| **derived_rules** | 交易记录型文章反推 | 否 | 标记来源，仅供分析 |
| **经验规则** | derived_rules 中置信度较高者 | 有限验证 | 间接验证（多人使用则可信度高） |

### 2.3 两层 DSL

```
提取层 (Extraction Layer)：
{
    "rule_type": "entry",
    "raw_condition": {
        "raw_text": "放量突破前高",
        "indicators": ["volume", "price"],
        "description": "当成交量放大且价格突破近期高点时买入"
    },
    "mapped_condition": null,  // 暂未映射
    "action": {...}
}

执行层 (Execution Layer)：
{
    "rule_type": "entry",
    "condition": {
        "and": [
            {"volume_ratio_above": 1.5},
            {"close_above": {"ref": "high_20"}}
        ]
    },
    "action": {...},
    "required_fields": ["volume", "close", "high_20"]
}
```

**映射流程**：
1. 提取时，LLM 生成 extraction_layer
2. 进入执行层前，需人工或半自动映射
3. 无法映射的规则标记为"待映射"，只做知识检索
4. 映射后的规则才能参与回测

---

## 3. 数据模型

### 3.1 新增数据库表

#### `rule_pool` - 规则池

```sql
CREATE TABLE rule_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 基本信息
    rule_id VARCHAR(64) UNIQUE NOT NULL,  -- 规则唯一标识
    source_article_ids JSON NOT NULL,       -- 来源文章 ID 列表
    source_type VARCHAR(32) NOT NULL,       -- standalone / derived / experience

    -- 规则内容
    rule_type VARCHAR(32) NOT NULL,         -- entry/exit/filter/sizing/risk
    instrument_focus VARCHAR(32) DEFAULT 'mixed',
    extraction_layer JSONB NOT NULL,        -- 提取层原始内容
    mapped_condition JSONB,                 -- 执行层映射后条件（可空）

    -- 映射状态
    mapping_status VARCHAR(32) DEFAULT 'unmapped',  -- unmapped / pending / mapped / unmappable
    mapped_by VARCHAR(64),                  -- 人工映射者
    mapped_at TIMESTAMPTZ,

    -- 置信度
    initial_confidence FLOAT NOT NULL,      -- 提取时初始置信度
    validated_confidence FLOAT,             -- 回测验证后置信度
    review_status VARCHAR(32) DEFAULT 'pending',  -- pending / approved / rejected
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,

    -- 回测结果
    backtest_triggered_at TIMESTAMPTZ,
    backtest_result JSONB,                  -- 回测详细结果
    backtest_hits INT DEFAULT 0,
    backtest_misses INT DEFAULT 0,
    backtest_samples INT DEFAULT 0,

    -- 使用追踪
    used_in_prediction BOOLEAN DEFAULT FALSE,
    prediction_count INT DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_rule_pool_status ON rule_pool(review_status, mapping_status);
CREATE INDEX idx_rule_pool_confidence ON rule_pool(validated_confidence);
CREATE INDEX idx_rule_pool_rule_type ON rule_pool(rule_type);
```

#### `trade_sample` - 交易样本库

```sql
CREATE TABLE trade_sample (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 来源
    source_article_id UUID NOT NULL REFERENCES blog_articles(id),

    -- 交易信息
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,              -- buy / sell
    entry_price FLOAT,
    exit_price FLOAT,
    quantity FLOAT,
    entry_date DATE,
    exit_date DATE,

    -- 原始描述（用于参考）
    raw_description TEXT,

    -- 提取的规则（如果能从交易反推）
    derived_rule_id UUID REFERENCES rule_pool(id),

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trade_sample_symbol ON trade_sample(symbol);
CREATE INDEX idx_trade_sample_date ON trade_sample(entry_date);
```

#### `article_classification` - 文章分类记录

```sql
CREATE TABLE article_classification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    article_id UUID NOT NULL REFERENCES blog_articles(id) UNIQUE,

    -- 分类结果
    article_type VARCHAR(32) NOT NULL,      -- rule / record / concept / noise
    article_type_confidence FLOAT,          -- LLM 分类置信度
    classification_version VARCHAR(20),      -- 分类模型版本

    -- 各类型置信度（用于人工复核）
    type_scores JSONB,                      -- {"rule": 0.8, "record": 0.1, "concept": 0.05, "noise": 0.05}

    -- 复核状态
    review_status VARCHAR(32) DEFAULT 'pending',  -- pending / confirmed / corrected
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 扩展现有表

#### `article_metadata` 增加字段

```sql
ALTER TABLE article_metadata ADD COLUMN IF NOT EXISTS extraction_version VARCHAR(20);
ALTER TABLE article_metadata ADD COLUMN IF NOT EXISTS standalone_rule_ids JSONB;  -- 进入规则池的 ID 列表
ALTER TABLE article_metadata ADD COLUMN IF NOT EXISTS derived_rule_ids JSONB;
ALTER TABLE article_metadata ADD COLUMN IF NOT EXISTS trade_sample_ids JSONB;
```

#### `rule_pool` 增加回测置信度字段

```python
class RuleBacktestResult(BaseModel):
    """回测结果"""
    run_id: str
    run_at: datetime
    start_date: date
    end_date: date
    total_trades: int
    hit_trades: int
    miss_trades: int
    hit_rate: float
    avg_return: float
    sharpe_ratio: float | None
    max_drawdown: float | None
    sample_count: int  # 有效样本量（过少则不置信）
```

---

## 4. 处理流程

### 4.1 流程总览

```
文章进入
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段一：分类                                                 │
│ 1. 轻量级文章类型分类                                         │
│ 2. 输出：article_type + 各类型置信度                          │
│ 3. 噪音型 → 人工复核                                          │
│ 4. 非噪音型 → 下一阶段                                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段二：分层提取                                              │
│ 根据文章类型选择提取策略：                                      │
│   - 规则型 → standalone_rules 提取                            │
│   - 交易记录型 → trade_records 提取                           │
│   - 概念型 → 标签/概念提取                                     │
│   - 混合型 → 全部提取，分开存储                                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段三：进入规则池 B                                          │
│ standalone_rules                                             │
│   - initial_confidence >= 0.7 → 自动进入，审核通过             │
│   - initial_confidence < 0.7 → 进入待审核队列                  │
│   - 审核通过 → 正式进入规则池                                   │
│   - 审核拒绝 → 标记拒绝，不进入规则池                           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段四：规则映射（两层 DSL）                                   │
│ 进入规则池的规则：                                             │
│   - extraction_layer.mapped_condition = null                  │
│   - mapping_status = 'unmapped'                               │
│   - 可选：人工映射或 AI 辅助映射                                │
│   - 映射成功 → mapping_status = 'mapped'                      │
│   - 无法映射 → mapping_status = 'unmappable'                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段五：回测验证（触发时机）                                    │
│ 触发条件（满足任一）：                                          │
│   - 新规则进入规则池                                           │
│   - 规则映射状态变更（unmapped → mapped）                      │
│   - 人工触发回测                                               │
│   - 定时全量回测（如每周）                                      │
│ 执行回测：                                                     │
│   - 只对 mapping_status = 'mapped' 的规则                      │
│   - 全市场历史数据扫描                                          │
│   - 统计 hit/miss / return / sharpe 等指标                     │
│   - 计算 validated_confidence                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段六：置信度调整                                            │
│ validated_confidence 计算：                                   │
│   - 基础：回测胜率 × 调整系数                                   │
│   - 样本量保护：样本 < 20 时，保守调整                          │
│   - 多指标综合：胜率 + 盈亏比 + 夏普 + 回撤                      │
│ 调整规则：                                                     │
│   - validated_confidence > 0.8 → 高置信度，进入预测池           │
│   - 0.5 < validated_confidence < 0.8 → 中置信度，继续观察       │
│   - validated_confidence < 0.5 → 低置信度，移出预测池           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段七：盘前预测                                               │
│ 每日盘前：                                                    │
│   - 获取所有高置信度规则（validated_confidence >= 0.7）         │
│   - 扫描市场数据，检测规则触发                                   │
│   - 输出预测信号：标的 + 方向 + 置信度 + 触发规则列表            │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段八：盘后归因                                               │
│ 每日盘后：                                                    │
│   - 获取当日预测信号                                            │
│   - 获取当日实际走势                                            │
│   - 按规则归因：                                               │
│     - 规则预测正确 → 该规则 +1 hit                             │
│     - 规则预测错误 → 该规则 +1 miss                            │
│   - 输出归因报告                                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段九：规则优化决策                                           │
│ 表现差的规则分析：                                             │
│   - 市场环境变化 → 标记"环境不适用"，降低权重                    │
│   - 规则本身有问题 → 更新置信度或移出规则池                      │
│   - 提取有问题 → 回溯原始文章，重新提取                          │
│ 决策：                                                        │
│   - 继续观察                                                   │
│   - 更新置信度                                                 │
│   - 移出规则池                                                 │
│   - 标记为"待优化"                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 阶段一：文章分类

**轻量级分类 Prompt**：

```
你是一个文章分类器。请判断以下文章的[主要]类型：

类型定义：
- rule: 描述一般性交易规则/策略，不针对具体历史操作
- record: 描述具体历史操作（包含明确的时间、价格、数量）
- concept: 纯理论/框架/心态分享，无具体条件
- noise: 个人观点、闲聊、新闻、无交易逻辑

输出格式（严格 JSON）：
{
    "article_type": "rule|record|concept|noise",
    "confidence": 0.0~1.0,
    "type_scores": {"rule": 0.x, "record": 0.x, "concept": 0.x, "noise": 0.x},
    "reason": "简短原因"
}

注意：
- 如果是混合类型，选择最主要的类型
- confidence 低于 0.5 时标记为"需要人工复核"
```

**分类结果存储**：写入 `article_classification` 表

**噪音型处理**：进入人工复核队列

### 4.3 阶段二：分层提取

**分类后的差异化 Prompt**：

| 文章类型 | 提取目标 | 额外指令 |
|---------|---------|---------|
| rule | standalone_rules | "只提取一般性规则，不要从具体案例反推" |
| record | trade_records | "只提取具体交易记录，不要泛化为规则" |
| concept | 标签/概念 | "只提取概念性内容，不生成可执行规则" |
| noise | 基本信息 | "最小化提取（代码、情感、作者），不做规则提取" |
| mixed | 全部提取 | "识别并分开提取：方法论规则 + 具体交易记录 + 概念" |

**standalone_rules 提取 Prompt（示例）**：

```
你是一个交易规则提取专家。从文章中提取一般性交易规则。

提取要求：
1. 规则必须是通用的、可执行的描述
2. 条件部分用自然语言描述，可以包含对指标的描述
3. 标注重复出现的指标：volume, price, MA, EMA, MACD, RSI 等

输出格式（严格 JSON）：
{
    "standalone_rules": [
        {
            "rule_type": "entry|exit|filter|sizing|risk",
            "instrument_focus": "stock|etf|cb|mixed",
            "raw_condition": {
                "raw_text": "放量突破前高时买入",
                "indicators": ["volume", "price", "high"],
                "description": "当成交量放大且价格突破近期高点时买入"
            },
            "mapped_condition": null,
            "action": {
                "type": "enter|exit|filter|...",
                "side": "buy|sell",
                "order": "limit|market",
                "price": null,
                "params": {}
            },
            "confidence": 0.0~1.0,
            "quoted_text": "原文引用"
        }
    ]
}
```

**trade_records 提取 Prompt（示例）**：

```
你是一个交易记录提取专家。从文章中提取具体的历史交易记录。

提取要求：
1. 必须是具体的历史操作（有时间、价格、数量）
2. 不要泛化为规则
3. 记录可以是自己的，也可以是他人的

输出格式（严格 JSON）：
{
    "trade_records": [
        {
            "symbol": "000001.SZ",
            "side": "buy|sell",
            "entry_price": 10.5,
            "exit_price": null,
            "quantity": 1000,
            "entry_date": "2024-01-15",
            "exit_date": null,
            "raw_description": "原文描述"
        }
    ]
}
```

### 4.4 阶段三：进入规则池 B

**流程**：

```
standalone_rule 提取完成
    ↓
检查 initial_confidence >= 0.7 ?
    ↓ 是
规则直接进入 rule_pool
review_status = 'approved'（自动审核通过）
    ↓ 否
进入待审核队列
    ↓
人工审核
    ├─ 通过 → review_status = 'approved'，进入规则池
    └─ 拒绝 → review_status = 'rejected'，不进入
```

**自动审核规则**：
- schema 校验通过
- 非空 action
- 非空 rule_type
- 非纯概念性描述（至少包含一个可识别的指标）

### 4.5 阶段四：规则映射（两层 DSL）

**人工映射流程**：

```
规则进入 rule_pool，mapping_status = 'unmapped'
    ↓
人工查看 extraction_layer.raw_condition
    ↓
判断：
    ├─ 可以映射 → 填写 mapped_condition，mapping_status = 'mapped'
    ├─ 需要更多上下文 → mapping_status = 'pending'
    └─ 无法映射 → mapping_status = 'unmappable'
```

**mapped_condition 格式**（标准化 DSL）：

```python
# 操作符
OPERATORS = ["and", "or", "not", "gt", "lt", "eq", "gte", "lte", "in", "not_in", "cross_above", "cross_below"]

# 字段标准库
STANDARD_FIELDS = [
    "close", "open", "high", "low", "volume",
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "ema5", "ema10", "ema20", "ema60",
    "macd", "macd_signal", "macd_hist",
    "rsi6", "rsi12", "rsi24",
    "bollinger_upper", "bollinger_middle", "bollinger_lower",
    "kdj_k", "kdj_d", "kdj_j",
    "volume_ratio", "turnover_rate",
]

# 示例映射
# raw_text: "放量突破前高"
# mapped_condition:
# {
#     "and": [
#         {"volume_ratio_above": 1.5},
#         {"close_above": {"ref": "high_20"}}
#     ]
# }
```

### 4.6 阶段五：回测验证

**触发时机**：

| 触发条件 | 说明 |
|---------|------|
| 新规则进入规则池 | 首次验证 |
| 规则映射完成 | 重新验证（因为条件更精确了） |
| 人工触发 | 手动验证特定规则 |
| 定时全量回测 | 每周日凌晨跑全量 |

**回测执行**：

```
规则池 B → 筛选 mapping_status = 'mapped'
    ↓
遍历全市场历史数据（回测区间可配置，默认近2年）
    ↓
对每个交易日：
    - 检测规则是否触发
    - 触发 → 记录一笔交易
    - 持有 N 日后退出（T+1, T+3, T+5）
    ↓
统计：
    - total_trades: 总交易数
    - hit_trades: 盈利交易数
    - miss_trades: 亏损交易数
    - avg_return: 平均收益率
    - sharpe_ratio: 夏普比率
    - max_drawdown: 最大回撤
    - sample_count: 有效样本量
```

**回测参数**：

```python
BACKTEST_CONFIG = {
    "start_date": "2024-01-01",  # 可配置
    "end_date": "2026-04-30",    # 可配置
    "holding_days": [1, 3, 5],   # 持有期
    "min_sample_count": 10,      # 最小样本量
    "market_scope": "all",       # 全市场
}
```

### 4.7 阶段六：置信度调整

**多指标综合评分**：

```python
def compute_confidence_adjustment(
    initial_confidence: float,
    backtest_result: RuleBacktestResult,
    prior_weight: int = 20,
) -> float:
    """
    多指标综合置信度调整

    参数：
        initial_confidence: 提取时的初始置信度
        backtest_result: 回测结果
        prior_weight: 先验权重（样本少时保护）

    返回：
        validated_confidence: 验证后的置信度
    """

    # 1. 基本胜率
    if backtest_result.sample_count < 10:
        # 样本不足，保护性处理
        return initial_confidence * 0.9  # 轻微下调

    hit_rate = backtest_result.hit_trades / backtest_result.total_trades

    # 2. 盈亏比
    avg_return = backtest_result.avg_return
    profit_loss_ratio = max(avg_return / abs(avg_return) if avg_return != 0 else 0, 0)

    # 3. 夏普比率调整
    sharpe = backtest_result.sharpe_ratio or 0
    sharpe_factor = max(min(sharpe / 2.0, 1.0), -1.0)  # 归一化到 [-1, 1]

    # 4. 最大回撤惩罚
    max_dd = backtest_result.max_drawdown or 0
    dd_penalty = max_dd * 0.5  # 回撤越大，惩罚越大

    # 5. 综合得分
    score = (
        0.4 * hit_rate +                    # 胜率权重 40%
        0.2 * min(profit_loss_ratio, 1.5) / 1.5 +  # 盈亏比权重 20%
        0.2 * (sharpe_factor + 1) / 2 +     # 夏普权重 20%
        0.2 * (1 - dd_penalty)              # 回撤权重 20%
    )

    # 6. 贝叶斯式加权更新
    # 新置信度 = (初始置信度 * 先验权重 + 回测得分 * 样本量) / (先验权重 + 样本量)
    n = backtest_result.sample_count
    validated_confidence = (
        initial_confidence * prior_weight + score * n
    ) / (prior_weight + n)

    return validated_confidence
```

**置信度等级**：

| 等级 | validated_confidence | 含义 | 动作 |
|------|---------------------|------|------|
| A | >= 0.8 | 高置信度 | 进入盘前预测池 |
| B | 0.6 ~ 0.8 | 中高置信度 | 观察，跟踪 |
| C | 0.4 ~ 0.6 | 中置信度 | 降低权重，继续观察 |
| D | < 0.4 | 低置信度 | 移出预测池，标记待优化 |

### 4.8 阶段七：盘前预测

**每日盘前流程**（9:00 前）：

```
获取所有 A 级规则（validated_confidence >= 0.8）
    ↓
获取当日市场数据快照
    ↓
对每个规则：
    - 解析 mapped_condition
    - 遍历候选标的
    - 检测规则是否触发
    ↓
聚合触发结果：
    - 标的 + 方向 + 置信度 + 触发规则列表
    ↓
输出盘前预测信号
```

**预测信号格式**：

```python
class PreMarketPrediction(BaseModel):
    date: date
    predictions: list[PredictionItem]

class PredictionItem(BaseModel):
    symbol: str
    side: str  # buy / sell
    confidence: float  # 加权置信度
    triggered_rules: list[str]  # 触发的规则 ID 列表
    reason: str  # 简要原因
```

### 4.9 阶段八：盘后归因

**每日盘后流程**（15:30 后）：

```
获取当日盘前预测信号
    ↓
获取当日实际市场数据
    ↓
对每个预测：
    - 检查实际走势是否匹配预测
    - 匹配 → 该规则 +1 hit
    - 不匹配 → 该规则 +1 miss
    ↓
更新规则的回测统计
    ↓
输出归因报告
```

**归因分析维度**：

| 维度 | 说明 |
|------|------|
| 规则命中率 | 当日预测正确的规则比例 |
| 规则来源分析 | 哪些类型的规则表现好/差 |
| 环境分析 | 当日市场环境（涨跌家数、热点板块） |
| 规则 vs 市场 | 规则预测错误是因为市场异常还是规则本身问题 |

### 4.10 阶段九：规则优化决策

**表现差的规则分析流程**：

```
规则在某时间段内表现差（如近20个交易日命中率 < 0.4）
    ↓
触发分析：
    ├─ 市场环境分析
    │   - 当期市场环境与规则适用条件是否匹配
    │   - 市场风格是否切换（题材/价值/趋势/震荡）
    │   → 如果环境不匹配 → 标记"环境不适用"，降低权重
    │
    ├─ 规则本身分析
    │   - 规则条件是否过于宽松/严格
    │   - 规则是否过度拟合历史
    │   → 如果规则本身问题 → 更新置信度或移出规则池
    │
    └─ 提取质量分析
        - 回溯原始文章
        - 检查提取是否准确反映了文章意图
        → 如果提取问题 → 重新提取或标记"提取待优化"
```

**优化决策选项**：

| 决策 | 条件 | 动作 |
|------|------|------|
| 继续观察 | 近期表现差但长期还行 | 保持，观察更长周期 |
| 降低权重 | 确认环境不适用 | validated_confidence *= 0.8 |
| 更新置信度 | 新的回测结果 | 重新计算 |
| 移出预测池 | 长期表现差 | 移出，但保留记录 |
| 完全废弃 | 确认无效 | 删除规则记录 |
| 回溯重提 | 提取可能有问题 | 重新调用 LLM 提取 |

---

## 5. 模块设计

### 5.1 新增模块

```
src/
├── article_classifier/          # 阶段一：文章分类（集成到 process 步骤）
│   ├── __init__.py
│   ├── classifier.py            # 分类器主逻辑
│   ├── prompts.py               # 分类 prompt
│   └── schemas.py               # 分类结果 schema
│
│   注：rule_extractor 不需要新建，复用现有 extract_article_metadata.py
│
├── rule_pool/                   # 阶段三~四：规则池管理
│   ├── __init__.py
│   ├── repository.py            # 规则池 CRUD
│   ├── reviewer.py              # 审核流程
│   ├── mapper.py                # DSL 映射工具
│   └── schemas.py               # 规则池 schema
│
├── rule_backtest/               # 阶段五：回测验证
│   ├── __init__.py
│   ├── engine.py                # 回测引擎
│   ├── validator.py             # 规则验证逻辑
│   ├── confidence.py            # 置信度计算
│   └── scheduler.py             # 回测调度
│
├── rule_prediction/             # 阶段七：盘前预测
│   ├── __init__.py
│   ├── predictor.py             # 预测器
│   ├── signal_aggregator.py     # 信号聚合
│   └── schemas.py               # 预测结果 schema
│
├── rule_attribution/            # 阶段八~九：归因与优化
│   ├── __init__.py
│   ├── attributor.py            # 归因分析
│   ├── analyzer.py              # 规则表现分析
│   ├── optimizer.py             # 优化决策
│   └── schemas.py               # 归因结果 schema
│
└── dsl/                         # DSL 相关（扩展现有）
    ├── __init__.py
    ├── extraction_layer.py      # 提取层 DSL
    ├── execution_layer.py       # 执行层 DSL
    └── mapper.py                # 映射工具
```

### 5.2 复用现有模块

| 现有模块 | 复用方式 |
|---------|---------|
| `src/backtest/` | 复用回测引擎核心逻辑，扩展支持规则验证 |
| `src/agents/strategy_agent/` | 复用规则评估逻辑 |
| `src/agents/data_agent/` | 复用 LLM 调用逻辑 |
| `src/dsl/` | 扩展现有 DSL 支持两层模型 |

### 5.3 CLI 命令扩展

**复用现有命令**（不新增）：
- `extract-articles` - 复用现有 LLM 提取逻辑
- `backtest run` - 扩展支持规则池回测
- `run-pre-market` - 扩展高置信度规则预测
- `run-after-close` - 扩展规则归因

**新增独立命令**：

```bash
# 规则池管理
python -m cli.main rule-pool list             # 列出规则
python -m cli.main rule-pool review           # 人工审核待审核规则
python -m cli.main rule-pool map             # DSL 映射工具
python -m cli.main rule-pool trigger-backtest # 触发回测

# 回测
python -m cli.main backtest rules             # 规则回测
python -m cli.main backtest rules-full        # 全量规则回测

# 预测与归因
python -m cli.main prediction run             # 运行盘前预测
python -m cli.main prediction report          # 输出预测报告
python -m cli.main attribution run            # 运行盘后归因
python -m cli.main attribution analyze        # 分析规则表现

# 调度
python -m cli.main scheduler start            # 启动调度器
```

---

## 6. 与现有系统的集成

### 6.1 设计原则：分层而不是平行

**核心原则**：新增层只做现有层做不了的事，不重复现有工作。

```
现有层（不动）                              新增层（在其基础上）
──────────────────────────────────────────────────────────────
blog_articles                               blog_articles
    ↓                                           ↓
extract_article_metadata (process)    ←       继续用，复用 LLM 提取逻辑
    ↓                                           ↓
article_metadata                    ←       扩展：增加 article_type、trade_samples 字段
    │                                           ↓
    │                                    rule_pool (新增表)
    │                                           ↓
    │                                    回测验证 → 置信度调整
    │                                           ↓
StrategyVersion.rules_snapshot ← ← ← ← ← ← 高置信度规则
    ↓                                           ↑
run_pre_market / run_after_close   ← ← ← ← ← 扩展：增加规则归因
```

### 6.2 调度集成

**与现有 PipelineScheduler 的关系**：

| 现有调度 | 时间 | 新增/扩展 | 说明 |
|---------|------|----------|------|
| `run_pipeline` | 08:00 | 不变 | 爬虫+清洗+提取，现有逻辑不变 |
| `run_pre_market` | 08:30 | **扩展** | 增加高置信度规则盘前预测 |
| `run_after_close` | 16:00 | **扩展** | 增加规则归因分析 |
| `backtest run` | 按需 | **扩展** | 增加规则触发式回测 |

**不新建独立调度器**，而是扩展现有调度任务。

**新增独立模块**（不影响现有流程）：
- `rule_pool` 表 + 审核工具
- `article_classifier`（集成到 process）
- `DSL 映射工具`
- `置信度计算模块`

### 6.3 任务重叠分析

| 新任务 | 与现有任务关系 | 处理方式 |
|--------|--------------|---------|
| `article_classify` | 在 process 之前增加 | 集成到 process 步骤 |
| `rule_extract` | 与 process 完全重叠 | **不需要**，复用现有 extract_article_metadata |
| `rule_pool_trigger` | 新任务 | 新增独立模块 |
| `prediction_run` | 部分重叠 run_pre_market | 扩展现有 run_pre_market |
| `attribution_run` | 部分重叠 run_after_close | 扩展现有 run_after_close |
| `rule_analyze` | 新任务 | 新增独立模块 |
| `rule_backtest_full` | 与 backtest run 重叠 | 扩展现有 backtest run |

### 6.4 CLI 命令集成

**扩展现有命令**：

```bash
# 扩展 backtest run
python -m cli.main backtest run --rules-pool  # 规则池回测模式
python -m cli.main backtest run --full-scan   # 全量规则回测

# 扩展 run-pre-market
python -m cli.main run-pre-market --use-rules-pool  # 使用高置信度规则预测

# 扩展 run-after-close
python -m cli.main run-after-close --with-attribution  # 规则归因
```

**新增命令**：

```bash
# 规则池管理
python -m cli.main rule-pool list              # 列出规则
python -m cli.main rule-pool review             # 人工审核
python -m cli.main rule-pool map                # DSL 映射
python -m cli.main rule-pool trigger-backtest   # 触发回测

# 规则分析
python -m cli.main rule-analyze                 # 分析规则表现
```

### 6.5 触发机制

| 触发类型 | 触发条件 | 动作 |
|---------|---------|------|
| 实时 | 新文章处理完成 | 规则自动进入 rule_pool |
| 实时 | 规则审核通过 | 触发回测验证 |
| 定时 | 每日 08:30（run-pre-market） | 扩展：使用高置信度规则预测 |
| 定时 | 每日 16:00（run-after-close） | 扩展：规则归因分析 |
| 定时 | 每周日 00:00 | 全量规则回测 |
| 手动 | CLI 触发 | rule_pool trigger-backtest |

---

## 7. 已知局限与未来优化方向

### 7.1 当前版本局限

| 局限 | 影响 | 缓解措施 |
|------|------|---------|
| 文章分类依赖 LLM | 分类可能不稳定 | 噪音型人工复核 |
| DSL 映射需要人工 | 工作量大 | 考虑 AI 辅助映射 |
| 回测用历史快照 | 可能与实盘有差异 | 使用标准化 OHLCV 数据 |
| 规则来源单一 | 样本量有限 | 逐步积累更多文章 |
| 只支持 A 股 | 局限性强 | 未来扩展到其他市场 |

### 7.2 未来优化方向

#### 短期（1-3个月）

1. **AI 辅助映射**：训练模型自动将 raw_condition 映射为 mapped_condition
2. **规则版本管理**：规则迭代历史记录
3. **更多指标支持**：扩展 STANDARD_FIELDS
4. **历史规则池**：从现有 article_metadata 批量迁移规则

#### 中期（3-6个月）

1. **多市场支持**：港股、美股、期货
2. **实盘对接**：模拟盘/实盘信号
3. **规则组合**：多个规则组合生成更复杂信号
4. **用户反馈集成**：根据实际交易结果反馈优化规则

#### 长期（6个月以上）

1. **规则自动生成**：基于历史数据自动发现规则
2. **强化学习优化**：根据实盘表现自动调整规则权重
3. **跨市场泛化**：发现跨市场有效规则
4. **社交信号挖掘**：从更多来源发现交易想法

### 7.3 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| LLM 分类错误 | 中 | 中 | 人工复核噪音型 |
| 规则过度拟合 | 高 | 高 | 控制回测样本外验证 |
| 映射不一致 | 高 | 中 | 建立映射规范，AI 辅助 |
| 文章来源单一 | 中 | 低 | 扩展爬虫来源 |
| 市场环境变化 | 高 | 高 | 环境感知，动态权重 |

---

## 8. 实施顺序

### Phase 1：基础设施（1-2周）

1. 新增数据库表（rule_pool, trade_sample, article_classification）
2. 实现文章分类器（article_classifier）
3. 扩展现有提取逻辑支持分层提取
4. CLI 命令基础支持

### Phase 2：规则池管理（1-2周）

5. 规则池 CRUD
6. 审核流程
7. DSL 映射工具
8. 与 article_metadata 关联

### Phase 3：回测验证（2-3周）

9. 复用 BacktestEngine，扩展规则验证
10. 置信度计算逻辑
11. 回测触发机制
12. 定时回测调度

### Phase 4：预测与归因（2-3周）

13. 盘前预测流程
14. 盘后归因流程
15. 规则优化决策逻辑
16. 报告输出

### Phase 5：调度与集成（1-2周）

17. 调度器配置
18. 全流程联调
19. 历史数据迁移
20. 监控与告警

---

## 9. 验收标准

### 9.1 功能验收

- [ ] 能对文章进行四分类（rule/record/concept/noise）
- [ ] 能从规则型文章提取 standalone_rules
- [ ] 能从交易记录型文章提取 trade_records
- [ ] 规则能进入规则池并经过审核
- [ ] 规则能完成 DSL 两层映射
- [ ] 规则能触发回测并更新置信度
- [ ] 高置信度规则能生成盘前预测
- [ ] 盘后能进行归因分析
- [ ] 表现差的规则能分析根因

### 9.2 质量验收

- [ ] 分类准确率 > 80%（人工抽检）
- [ ] 回测置信度调整有据可查
- [ ] 所有流程可追溯
- [ ] 规则历史可查询

### 9.3 性能验收

- [ ] 单篇文章分类 < 5 秒
- [ ] 单条规则回测 < 1 分钟（全市场2年数据）
- [ ] 每日盘前预测 < 10 分钟

---

## 10. 附录

### 10.1 参考现有代码

- `src/agents/data_agent/skills/extract_article_metadata.py` - LLM 提取逻辑
- `src/backtest/engine.py` - 回测引擎
- `src/agents/strategy_agent/agent.py` - 规则评估逻辑
- `src/persona/schemas.py` - 现有 rule schema

### 10.2 相关文档

- `docs/TaskList.md` - 任务列表
- `docs/superpowers/plans/2026-04-25-postmortem-metrics-plan.md` - 回测设计参考
- `docs/superpowers/specs/Stage6-summary-desgin.md` - Stage 6 设计参考