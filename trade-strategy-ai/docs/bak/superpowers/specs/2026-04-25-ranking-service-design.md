# NTL-S5-004 Ranking Service 设计文档

> 状态：已批准
> 创建：2026-04-25
> 目标：建立 ranking service，为盘后 ranking 和策略版本筛选提供基础能力

---

## 1. 背景与目标

NTL-S5-001 建立了 EvidencePack 结构，NTL-S5-002 建立了失败归因分类，NTL-S5-003 建立了盘后复盘 Service。NTL-S5-004 在此基础上建立 **ranking service**，对盘后评估结果按多维度排序，为 NTL-S5-011（盘后 ranking 报告）和 Stage 7（策略版本筛选）提供数据基础。

### 1.1 核心能力

1. **多级排序**：以 `return_pct` 为主键，`mfe - mae`（赔率）为副键
2. **嵌套分组**：按 `trader_id` → `strategy_version_id` → `symbol` 层级组织
3. **双视图输出**：嵌套字典（默认）和扁平列表（可选）
4. **自动持久化**：每次 postmortem 生成后自动写入 DB
5. **评分修正同步**：postmortem 被 LLM 修正时自动更新 ranking
6. **版本状态追踪**：标记 `is_latest` 用于识别当前有效版本

### 1.2 架构位置

```
PostmortemService.generate()
       │
       ▼
RankingService.add_entry()
       │
       ├──→ RankingEntryRecord (DB persist)
       │
       ▼
RankingService.generate_ranking()  ← 批量计算 rank（所有 entry 收集完后）
       │
       ▼
RankingEntry (with rank populated)
```

---

## 2. 数据结构

### 2.1 RankingEntry（内存 dataclass）

```python
@dataclass
class RankingEntry:
    """单条 ranking 条目。

    对应 DB 中的 RankingEntryRecord。
    排序逻辑：
      - 先按 return_pct 降序
      - return_pct 相同时按 (mfe - mae) 降序（赔率优选）
      - return_pct 为 None 的排在最后，组内按赔率排序
    """
    entry_id: UUID
    trade_date: str
    trader_id: str
    strategy_version_id: str
    symbol: str

    # 排序指标
    return_pct: float | None       # 主排序键
    mfe: float | None              # 最大有利偏移
    mae: float | None              # 最大不利偏移

    # 复合分（可选，用于调试和对账）
    composite_score: float | None

    # 排序结果
    rank: int                      # 组内排名（generate_ranking 时计算）
    is_latest: bool = True         # 是否为该版本的最新 entry

    # 来源追踪
    idea_id: UUID | None
    attribution_source: str        # 来自 postmortem_result.attribution_source

    extra: dict[str, object] = field(default_factory=dict)
```

### 2.2 ORM 模型

```python
class RankingEntryRecord(Base):
    """ranking 条目持久化模型。"""
    __tablename__ = "ranking_entries"

    entry_id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    trade_date: str = Column(String, nullable=False, index=True)
    trader_id: str = Column(String, nullable=False, index=True)
    strategy_version_id: str = Column(String, nullable=False, index=True)
    symbol: str = Column(String, nullable=False)

    # 排序指标
    return_pct: FloatNullable = Column(Float, nullable=True)
    mfe: FloatNullable = Column(Float, nullable=True)
    mae: FloatNullable = Column(Float, nullable=True)
    composite_score: FloatNullable = Column(Float, nullable=True)

    # 排名（生成 ranking 时回填）
    rank: IntNullable = Column(Integer, nullable=True)

    # 版本状态
    is_latest: bool = Column(Boolean, default=True, nullable=False)

    # 来源追踪
    idea_id: UUIDNullable = Column(UUID(as_uuid=True), nullable=True)
    attribution_source: str = Column(String, nullable=False, default="auto")

    # 扩展字段（JSONB）
    extra: dict = Column(JSONB, nullable=False, default=dict)

    # 唯一约束：同一交易日 + 同一策略版本 + 同一标的只有一条
    __table_args__ = (
        UniqueConstraint("trade_date", "strategy_version_id", "symbol", name="uq_ranking_entry"),
        Index("ix_ranking_trader_version", "trader_id", "strategy_version_id"),
    )
```

### 2.3 Composite Score 计算

```python
def _compute_composite(entry: RankingEntry) -> float | None:
    """计算复合分，供调试和对账使用。"""
    if entry.return_pct is None:
        return None
    odds_bonus = max(0, (entry.mfe or 0) - (entry.mae or 0))
    return entry.return_pct + odds_bonus
```

---

## 3. Service 接口

### 3.1 RankingService

```python
class RankingService:
    """盘后 ranking service。

    职责：
      - 接收 postmortem 结果和 evidence pack，生成 ranking 条目并持久化
      - 支持批量生成 ranking（计算组内 rank）
      - 支持 postmortem 修正后的同步更新
      - 提供嵌套视图和扁平视图两种输出格式
    """

    def __init__(self, session: Session):
        self.session = session
        self._repo = RankingRepository(session)

    def add_entry(
        self,
        postmortem: PostmortemResult,
        evidence_pack: EvidencePack,
    ) -> RankingEntry:
        """接收一个 postmortem 结果，生成并持久化一条 ranking 条目。

        rank 字段在 add_entry 时为 None，由 generate_ranking() 批量计算。

        如果同一 (trade_date, strategy_version_id, symbol) 已存在：
          - 新 entry 写入（upsert 行为，保留历史）
          - 旧 entry.is_latest = False（标记为非最新）
          - 这保证了历史 ranking 可追溯，同时 latest 条目能反映最新评估

        Args:
            postmortem: 盘后复盘结果
            evidence_pack: 交易证据包

        Returns:
            新建的 RankingEntry
        """
        ...

    async def generate_ranking(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        view: Literal["nested", "flat"] = "nested",
    ) -> dict | list:
        """批量生成并更新指定日期的 ranking（计算 rank）。

        调用时机：当日所有 add_entry 完成后（NTL-S5-011 盘后流程末尾）。

        排序规则：
          1. return_pct 降序
          2. return_pct 相同时按 (mfe - mae) 降序
          3. return_pct 为 None 的排在最后，组内按赔率排序

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            trader_id: 可选，限定 trader
            strategy_version_id: 可选，限定策略版本
            view: "nested"（默认，嵌套字典）| "flat"（扁平列表）

        Returns:
            nested view: {trader_id: {strategy_version_id: [ranking_entries...]}}
            flat view: [ranking_entries...]（所有维度混合，按 composite_score 全局排序）
        """
        ...

    def update_entry(self, entry_id: UUID, postmortem: PostmortemResult) -> RankingEntry | None:
        """当 postmortem 被 LLM 修正时，同步更新对应的 ranking 条目。

        修正场景（NTL-S5-010）：
          - postmortem.attribution_source = "llm_corrected" 或 "llm_rejected"
          - return_pct / mfe / mae 被更新

        实现逻辑：
          1. 查找 entry_id 对应的 record
          2. 更新 return_pct / mfe / mae / attribution_source / extra
          3. 重新计算 composite_score
          4. 将同一 strategy_version_id 下的所有条目标记为 is_latest=False（因为有新的修正）
          5. 新 entry 写入，is_latest=True

        Args:
            entry_id: 被修正的 entry ID
            postmortem: 更新后的 postmortem 结果

        Returns:
            更新后的 RankingEntry，或 None（未找到）
        """
        ...

    def get_latest_by_version(self, version_id: str) -> list[RankingEntry]:
        """获取指定策略版本的最新 ranking 条目（is_latest=True）。"""
        ...

    def get_by_trader(self, trader_id: str, trade_date: str | None = None) -> dict:
        """获取指定 trader 的 ranking（嵌套视图）。"""
        ...
```

### 3.2 RankingRepository

```python
class RankingRepository:
    """ranking 条目数据访问层。"""

    def save(self, entry: RankingEntry) -> RankingEntry:
        """Upsert 一条 ranking entry。"""
        ...

    def find_latest(
        self,
        strategy_version_id: str,
        symbol: str,
        trade_date: str,
    ) -> RankingEntry | None:
        """查找指定版本+标的的最新 entry。"""
        ...

    def mark_outdated(
        self,
        strategy_version_id: str,
        exclude_entry_id: UUID,
    ) -> int:
        """将指定策略版本的所有条目标记为 is_latest=False（排除当前新 entry）。"""
        ...

    def query_by_date(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
    ) -> list[RankingEntry]:
        """按日期查询 entry（用于 generate_ranking）。"""
        ...

    def update_rank(self, entry_ids: list[UUID], ranks: list[int]) -> None:
        """批量更新 rank。"""
        ...
```

---

## 4. 数据流

### 4.1 正常路径（add_entry → generate_ranking）

```
1. PostmortemService.generate() 返回 PostmortemResult
2. ManagerAgent 调用 RankingService.add_entry(postmortem, evidence_pack)
   └─→ UPSERT RankingEntryRecord（is_latest=True）
   └─→ 同一 (trade_date, strategy_version_id, symbol) 的旧条目标记 is_latest=False
   └─→ rank = None（尚未计算）
3. 当日所有 add_entry 完成后，ManagerAgent 调用 RankingService.generate_ranking(trade_date)
   └─→ 查询该日期所有 is_latest=True 的 entry
   └─→ 按排序规则计算 rank，回填到 DB
   └─→ 返回嵌套/扁平视图
```

### 4.2 修正路径（postmortem 修正 → update_entry）

```
1. LLMValidator.validate() 返回 llm_corrected / llm_rejected
2. ManagerAgent 调用 RankingService.update_entry(entry_id, updated_postmortem)
   └─→ 查找旧 entry，标记 is_latest=False
   └─→ 写入新 entry（is_latest=True，rank=None）
3. 下次 generate_ranking 时重新排序
```

---

## 5. 与其他模块的关系

### 5.1 上游

- `PostmortemService`：消费 postmortem 结果作为输入
- `EvidencePack`：获取 symbol、strategy_version_id、trader_id、指标数据

### 5.2 下游

- **NTL-S5-011（盘后生成 ranking）**：直接消费 RankingService.generate_ranking() 输出
- **NTL-S7-001（筛选活跃 trader）**：基于 ranking 结果统计 trader 表现
- **NTL-S5-012（差评触发记忆写回）**：ranking 低的触发记忆写回流程

---

## 6. 实现计划

### 6.1 文件结构

```
src/evaluation/
    __init__.py
    evidence_pack.py         # NTL-S5-001（已有）
    failure_taxonomy.py      # NTL-S5-002（已有）
    postmortem_service.py    # NTL-S5-003（已有）
    ranking_service.py       # NTL-S5-004（新增）
    ranking_repository.py    # NTL-S5-004（新增）

src/models/
    ranking_entry.py         # NTL-S5-004（新增，RankingEntryRecord ORM）
```

### 6.2 导出内容

```python
# src/evaluation/__init__.py
from .ranking_service import RankingService, RankingEntry

__all__ = [
    "RankingService",
    "RankingEntry",
]
```

### 6.3 验收标准

1. `add_entry` 正确 upsert，新 entry 的 `is_latest=True`，旧 entry 的 `is_latest=False`
2. `generate_ranking` 正确计算 rank：return_pct 降序，相同时按 mfe-mae 降序，None 排最后
3. `update_entry` 能同步 postmortem 修正，更新对应 entry 并标记旧条目的 `is_latest=False`
4. 支持 nested/flat 两种视图输出
5. 唯一约束 `uq_ranking_entry` 防止重复写入
6. 单元测试覆盖核心逻辑（排序逻辑、upsert 行为、版本淘汰）

---

## 7. Self-Review Checklist

- [x] 所有 placeholder（TBD/TODO）已清理
- [x] 排序逻辑明确：无 return_pct 按赔率排，None 排最后
- [x] is_latest 淘汰机制清晰：修正时标记旧 entry，新 entry 写入
- [x] 唯一约束设计合理：`(trade_date, strategy_version_id, symbol)` 不允许重复最新 entry
- [x] 与 postmortem_service 的数据流清晰
- [x] 与 NTL-S5-011、NTL-S7-001 的下游关系明确
- [x] rank 计算时机明确：add_entry 时为 None，generate_ranking 时批量计算
- [x] 并发安全：唯一约束 + ON CONFLICT DO UPDATE 原子 upsert
- [x] async 风格统一：所有 service 方法为 async def
- [x] flat view 分组内排序：先 trader 分组，组内按 composite_score 排序

---

## 8. 已确认设计决策

| 问题 | 决策 |
|------|------|
| 问题 1 并发一致性 | A — DB 层唯一约束 + ON CONFLICT DO UPDATE |
| 问题 2 async 风格 | A — 全 async（RankingService 全部 async def） |
| 问题 3 flat view 排序 | B — 先按 trader 分组，组内按 composite_score 排序 |
| 问题 4 add_entry 后立即可用 | 无区别，设计保持现状（rank 在 generate_ranking 时批量计算） |
| 问题 5 update_entry | 异步（async def） |

---

## 9. 并发安全设计

### 9.1 Upsert 原子性

`add_entry` 的 upsert 使用 `ON CONFLICT DO UPDATE`，确保：

- 并发写入同一 `(trade_date, strategy_version_id, symbol)` 时，只有一条 `is_latest=True`
- 旧 entry 的 `is_latest` 被原子性地设为 `False`
- 不需要应用层悲观锁

### 9.2 约束声明（PostgreSQL）

```python
__table_args__ = (
    UniqueConstraint(
        "trade_date", "strategy_version_id", "symbol",
        name="uq_ranking_entry_latest",
        where=(Column("is_latest") == True),  # 部分唯一约束，仅对 is_latest=True 的记录生效
    ),
    Index("ix_ranking_trader_version", "trader_id", "strategy_version_id"),
)
```

部分唯一约束使用 `WHERE is_latest = true` 子句实现，确保同一 `(trade_date, version, symbol)` 只允许同时存在一条 `is_latest=True` 的记录。