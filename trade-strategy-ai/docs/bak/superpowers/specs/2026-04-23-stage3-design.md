# Stage 3 设计文档

> 日期：2026-04-23
> 状态：已完成
> 对应任务：NTL-S3-001 ~ NTL-S3-011

---

## 1. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     StrategyLibraryService                    │
│              （策略库统一入口，整合 repository + builder）      │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │ StrategyVersion      │    │ StrategyVersion      │        │
│  │ Builder             │    │ Repository           │        │
│  │                     │───►│                      │        │
│  │ build_draft()       │    │ save()               │        │
│  │ build_released()    │    │ get_current_*()      │        │
│  │ release_version()   │    │ list_versions()     │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                                │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │ TraderProfile        │    │ ArticleEvidence      │        │
│  │ Service              │    │                      │        │
│  │                     │───►│ 来源：article_metadata │        │
│  │ → StrategyPreference│    │ → confidence_score   │        │
│  │ → RiskStyle         │    │ → sentiment_score    │        │
│  │ → ThemeStat         │    │ → source_url         │        │
│  │ → PositionBias      │    │ → published_at       │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

### 核心目标

- 每个 trader 每日生成**独立策略版本**
- 策略版本可追溯到**文章证据**、**画像**、**规则**和质量门禁
- 同一 trader 同日**只有一个 released 版本**

---

## 2. 策略版本状态机

```
draft ────► released
  │            │
  │            │ release_version() 会检查是否已存在
  │            │ 存在则抛出 ValueError，防止重复发布
  │            │
  │            ▼
  └──────► archived （预留，暂未实现）
```

### 版本 ID 格式

```
{trader_id}:{strategy_date}:{status}:v{version_number}
示例：trader_a:2026-04-23:released:v2
```

---

## 3. 核心数据结构

### StrategyVersion

```python
class StrategyVersion(BaseModel):
    version_id: str                          # 唯一标识，格式 {trader_id}:{date}:{status}:v{n}
    trader_id: str                           # 绑定 trader
    strategy_date: date                       # 策略日期
    status: StrategyVersionStatus            # draft / released

    # 版本内容
    recommendations: list[StrategyRecommendation] = []  # 标的推荐列表
    rules_snapshot: list[dict] = []          # NTL-S4-003：评估规则快照

    # 证据来源
    source_articles: list[ArticleEvidence] = []  # 引用文章证据

    # 质量门禁
    quality_gate: QualityGate | None = None

    # 元信息
    schema_version: str = "v1"               # schema 版本
    created_at: datetime | None = None
    released_at: datetime | None = None
```

### StrategyRecommendation

```python
class StrategyRecommendation(BaseModel):
    symbol: str                              # 标的代码
    decision: str                            # buy / hold / sell
    confidence: float                        # 0.0 ~ 1.0

    # 可选：来源文章
    source_article_id: str | None = None
    source_topic_id: str | None = None

    # 可选：规则命中
    triggered_rules: list[str] = []          # 命中的规则 ID 列表
```

### QualityGate

```python
class QualityGate(BaseModel):
    passed: bool
    min_articles: int                        # 最少引用文章数
    min_confidence: float                    # 最低置信度
    min_diversity: float                      # 最低标的分散度
    reasons: list[str] = []                   # 未通过原因
```

---

## 4. Builder 输入输出

### build_draft()

**输入：**
- `trader_id`
- `strategy_date`
- `profile: TraderProfile`（风格偏好、风险偏好、主题偏好）
- `articles: list[ArticleMetadata]`（可选，文章证据）

**输出：**
- `StrategyVersion(status=draft)`

**逻辑：**
1. 按 `profile.theme_preference` 过滤和排序标的
2. 按 `profile.risk_style` 设置止损比例
3. 按 `profile.max_positions` 限制标的数量
4. 引用质量合格的文章作为 `source_articles`
5. 触发质量门禁

### build_released()

**输入：**
- 已有的 `draft` 版本

**输出：**
- 新 `StrategyVersion(status=released)`，released_at 已填充

**约束：**
- 同 trader 同日只允许一个 released 版本
- 重复发布抛出 `ValueError`

---

## 5. Repository 查询契约

```python
class StrategyLibraryRepository:
    async def get_current_released_version(
        self,
        session: AsyncSession,
        trader_id: str,
        strategy_date: date,
    ) -> StrategyVersion | None: ...

    async def save(
        self,
        session: AsyncSession,
        version: StrategyVersion,
    ) -> None: ...

    async def list_versions(
        self,
        session: AsyncSession,
        trader_id: str | None = None,
        status: StrategyVersionStatus | None = None,
        limit: int = 10,
    ) -> list[StrategyVersion]: ...
```

### 版本唯一性约束（NTL-S3-010, NTL-S3-011）

- **同 trader 同日唯一 released**：`get_current_released_version` 查询并去重
- **trader 严格隔离**：所有查询默认带 `trader_id` 过滤
- **version_id 含 trader_id**：`version_id` 格式本身包含 `trader_id`，防止跨 trader 污染

---

## 6. TraderProfile 增强（NTL-S3-006, NTL-S3-009）

### 扩展字段

| 字段 | 类型 | 用途 |
|------|------|------|
| `style_preference` | TraderStylePreference | CONSERVATIVE / MODERATE / AGGRESSIVE |
| `max_positions` | int | 最大持仓标的数量 |
| `position_bias` | PositionBias | 仓位倾向（轻仓/重仓/满仓） |
| `theme_preference` | list[str] | 偏好主题 |
| `entry_price` | float \| None | 参考入场价（文章中抽取） |

### Builder 消费方式

- **`theme_preference`**：过滤和优先排序符合偏好的标的
- **`risk_style`**：控制止损比例（保守型 → 紧止损）
- **`max_positions`**：限制 recommendations 数量
- **`position_bias`**：调整每只标的的仓位权重

---

## 7. ArticleEvidence（NTL-S3-005）

从 `article_metadata` 抽取，作为策略版本的可信证据。

```python
class ArticleEvidence(BaseModel):
    article_id: str
    source_url: str
    published_at: datetime | None
    title: str
    sentiment_score: float | None   # -1.0 ~ 1.0
    confidence_score: float | None  # 0.0 ~ 1.0
    clamped_sentiment: float        # sentiment_score 归一化
    clamped_confidence: float       # confidence_score 归一化
    entry_price: float | None      # 文章中提及的参考价
```

---

## 8. 与 Stage 4 的关系

```
Stage 3                          Stage 4
┌─────────────────┐              ┌─────────────────┐
│ StrategyVersion │ ──────────► │ TraderAgent     │
│                 │  generate   │                 │
│ recommendations │   trade_ideas│ ideas           │
│ rules_snapshot  │ ──────────► │ StrategyAgent   │
│                 │  evaluate   │                 │
└─────────────────┘              └─────────────────┘
```

- **Stage 3** 负责**构建**策略版本（生成 recommendations + rules_snapshot）
- **Stage 4** 负责**消费**策略版本（TraderAgent 生成 TradeIdea，StrategyAgent 按规则评估）
- 两者通过 `StrategyVersion` 解耦：Stage 3 输出 → Stage 4 输入

---

## 9. 测试覆盖

| 测试 | 验证内容 |
|------|----------|
| `test_build_draft_persists_to_repository` | draft 版本构建并持久化 |
| `test_build_released` | released 版本状态转换 |
| `test_get_current_released_version_returns_none_when_empty` | 空库返回 None |
| `test_release_version_checks_existing` | 同日重复发布抛出 ValueError |
| `test_different_trader_can_have_released_same_day` | 不同 trader 可同日发布 |
| `test_version_id_contains_trader_id` | version_id 含 trader_id |
| `test_get_versions_only_returns_matching_trader` | 查询严格按 trader_id 过滤 |
| `test_repository_query_filters_by_trader_id` | repository 层隔离 |

**合计：39 tests PASS**

---

## 10. 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `src/strategy_library/schemas.py` | 新增 StrategyVersion / StrategyRecommendation / QualityGate |
| `src/strategy_library/repository.py` | 新增 StrategyLibraryRepository |
| `src/strategy_library/builder.py` | 新增 StrategyVersionBuilder |
| `src/strategy_library/service.py` | 新增 StrategyLibraryService |
| `src/trader_profile/schemas.py` | 扩展 TraderProfile 字段 |
| `src/trader_profile/service.py` | 扩展 TraderProfileService |
| `src/pipeline/tasks/strategy_version_tasks.py` | 新增 handle_build_trader_strategy_version |
| `tests/unit/strategy_library/` | 39 tests |
