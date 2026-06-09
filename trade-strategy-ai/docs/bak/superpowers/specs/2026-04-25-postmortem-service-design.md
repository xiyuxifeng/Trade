# NTL-S5-003 盘后复盘 Service 设计文档

> 状态：草稿，待评审
> 创建：2026-04-25
> 目标：建立盘后复盘 service，对单笔交易生成结构化复盘结果

---

## 1. 背景与目标

### 1.1 背景

NTL-S5-001 建立了 `EvidencePack` 结构，NTL-S5-002 建立了失败归因分类体系（多维度标签）。NTL-S5-003 在此基础上建立**盘后复盘 service**，将 EvidencePack 转化为结构化复盘结果。

### 1.2 目标

- 对单笔交易生成结构化复盘结果（`PostmortemResult`）
- 支持自动归因 + LLM 校验的混合模式
- 输出可供 ranking、报告生成、记忆写回使用

### 1.3 架构决策

**数据流：**

```
EvidencePack
    │
    ▼
[Step 1] 自动归因（基于 failure_taxonomy 标签体系）
    │ failure_categories ← 结构化标签
    │
    ▼
[Step 2] LLM 校验（可选）
    │ 读取 EvidencePack + 自动归因结果
    │ 返回：confirm / correct / reject
    │
    ▼
[Step 3] 最终归因结果
    │ final failure_categories（带 source 追踪）
    │ auto_original 保存在 extra（用于分析）
```

**LLM 配置**：复用现有 LLM 配置，不单独配置

---

## 2. 数据结构

### 2.1 LLMValidationResult

```python
class ValidationDecision(StrEnum):
    """LLM 校验决策。"""
    CONFIRM = "confirm"      # 自动归因正确
    CORRECT = "correct"     # LLM 修正了自动归因
    REJECT = "reject"       # LLM 拒绝归因


@dataclass
class LLMValidationResult:
    """LLM 校验结果。"""
    decision: ValidationDecision
    # 当 decision == "confirm" 时，corrected_categories 为空
    corrected_categories: list[str] = field(default_factory=list)
    reasoning: str = ""
```

### 2.2 PostmortemResult

```python
@dataclass
class PostmortemResult:
    """单笔交易的结构化复盘结果。"""
    idea_id: UUID | None
    trade_date: str

    # 归因结果
    failure_attribution: FailureAttribution
    attribution_source: str  # "auto" | "llm_confirmed" | "llm_corrected" | "llm_rejected"

    # LLM 生成的自然语言复盘（可为 None）
    postmortem_notes: str | None = None

    # 评分指标（NTL-S5-010 实现，当前占位）
    mfe: float | None = None      # Maximum Favorable Excursion
    mae: float | None = None      # Maximum Adverse Excursion
    return_pct: float | None = None

    # 扩展字段
    extra: dict[str, Any] = field(default_factory=dict)
```

### 2.3 source 字段含义

| attribution_source | 含义 |
|-------------------|------|
| `auto` | 仅自动归因，未经过 LLM 校验 |
| `llm_confirmed` | LLM 确认自动归因正确 |
| `llm_corrected` | LLM 修正了自动归因 |
| `llm_rejected` | LLM 拒绝归因 |

---

## 3. 归因判断逻辑

### 3.1 自动归因（必须）

基于 NTL-S5-002 的标签体系，通过 EvidencePack 内的数据计算 failure_categories：

| 归因 | 判断依据 |
|------|----------|
| `rule_precondition_failed` | rules_snapshot 中未满足的条件 |
| `signal_quality_low` | SignalContext.confidence < 阈值 或 triggered_rules 冲突 |
| `entry_timing_poor` | entry_price vs 盘中价格走势 |
| `exit_timing_poor` | stop_loss 被扫 vs 后续反弹幅度 |
| `position_size_mismatch` | position_size vs 风险限额 |
| `market_mismatch` | 波动率、趋势强度等指标与环境判断 |
| `external_event` | 价格异常跳变 + 已知事件列表 |
| `symbol_selection_suboptimal` | 同板块其他标的对比 |
| `data_quality_issue` | 价格/成交量异常检测 |

### 3.2 LLM 校验（可选）

**触发条件**：`enable_llm_validation=True` 且 `llm_validator` 可用

**输入**：EvidencePack.to_dict() + 自动归因结果

**输出**：`LLMValidationResult(decision, corrected_categories, reasoning)`

**处理逻辑**：

```python
if validation_result.decision == ValidationDecision.CONFIRM:
    final_categories = auto_categories
    source = "llm_confirmed"

elif validation_result.decision == ValidationDecision.CORRECT:
    final_categories = validation_result.corrected_categories
    source = "llm_corrected"
    extra["auto_original"] = auto_categories  # 保留原始结果用于分析

elif validation_result.decision == ValidationDecision.REJECT:
    final_categories = []  # 清空
    source = "llm_rejected"
    extra["auto_original"] = auto_categories  # 保留原始结果用于分析
```

---

## 4. Service 接口

### 4.1 LLMValidator Protocol

```python
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from src.evaluation.evidence_pack import EvidencePack
    from src.evaluation.failure_taxonomy import FailureAttribution

class LLMValidator(Protocol):
    """LLM 校验器接口。"""
    async def validate(
        self,
        evidence_pack: EvidencePack,
        auto_attribution: FailureAttribution,
    ) -> LLMValidationResult:
        """校验自动归因结果。"""
        ...
```

### 4.2 PostmortemService

```python
class PostmortemService:
    """盘后复盘 service。

    Args:
        llm_validator: LLM 校验器（可选，不提供则只做自动归因）
        enable_llm_notes: 是否生成 LLM 复盘笔记（需要 llm_validator）
    """

    def __init__(
        self,
        llm_validator: LLMValidator | None = None,
        enable_llm_notes: bool = False,
    ):
        self.llm_validator = llm_validator
        self.enable_llm_notes = enable_llm_notes

    async def generate(
        self,
        evidence_pack: EvidencePack,
    ) -> PostmortemResult:
        """对单笔交易生成复盘结果。

        Args:
            evidence_pack: 交易证据包

        Returns:
            PostmortemResult: 结构化复盘结果
        """
        # Step 1: 自动归因
        auto_attribution = self._auto_attribution(evidence_pack)

        # Step 2: LLM 校验（可选）
        source = "auto"
        extra: dict[str, Any] = {}
        final_attribution = auto_attribution

        if self.llm_validator is not None:
            validation = await self.llm_validator.validate(evidence_pack, auto_attribution)
            final_attribution, source, extra = self._apply_validation(
                auto_attribution, validation
            )

        # Step 3: LLM 笔记生成（可选）
        notes = None
        if self.enable_llm_notes and self.llm_validator is not None:
            notes = await self._generate_notes(evidence_pack, final_attribution)

        return PostmortemResult(
            idea_id=evidence_pack.idea_id,
            trade_date=evidence_pack.trade_date,
            failure_attribution=final_attribution,
            attribution_source=source,
            postmortem_notes=notes,
            extra=extra,
        )
```

### 4.3 内部方法

```python
def _auto_attribution(self, evidence_pack: EvidencePack) -> FailureAttribution:
    """基于 EvidencePack 数据做自动归因。"""
    # 使用 NTL-S5-002 的 failure_taxonomy 标签体系
    # 返回 FailureAttribution(root_causes, stage, rule_type)
    ...

def _apply_validation(
    self,
    auto: FailureAttribution,
    validation: LLMValidationResult,
) -> tuple[FailureAttribution, str, dict[str, Any]]:
    """应用 LLM 校验结果，返回 (final_attribution, source, extra)。"""
    ...

async def _generate_notes(
    self,
    evidence_pack: EvidencePack,
    attribution: FailureAttribution,
) -> str | None:
    """生成自然语言复盘笔记。"""
    ...
```

---

## 5. 与其他模块的关系

### 5.1 上游

- `EvidencePack`：核心输入（NTL-S5-001）
- `failure_taxonomy`：自动归因的标签体系（NTL-S5-002）

### 5.2 下游

- **NTL-S5-004（ranking service）**：消费 PostmortemResult
- **NTL-S5-012（记忆写回）**：基于 failure_attribution 写入 TraderMemory
- **NTL-S5-010（评分口径升级）**：填充 mfe/mae/return_pct

---

## 6. 实现计划

### 6.1 文件结构

```
src/evaluation/
    __init__.py                        # 更新：导出新增类型
    evidence_pack.py                    # NTL-S5-001（已有）
    failure_taxonomy.py                 # NTL-S5-002（已有）
    postmortem_service.py              # NTL-S5-003（新增）

tests/unit/evaluation/
    test_postmortem_service.py         # NTL-S5-003（新增）
```

### 6.2 导出内容

```python
# src/evaluation/__init__.py
from .postmortem_service import (
    ValidationDecision,
    LLMValidationResult,
    PostmortemResult,
    PostmortemService,
    LLMValidator,
)
```

---

## 7. 验收标准

1. `PostmortemService` 可对 EvidencePack 生成 `PostmortemResult`
2. 自动归因（无 LLM）正常工作
3. LLM 校验（启用时）正确处理 confirm/correct/reject
4. `attribution_source` 正确标识结果来源
5. `extra["auto_original"]` 在 correct/reject 时保留原始结果
6. `enable_llm_notes=True` 时生成 postmortem_notes
7. 测试覆盖：自动归因、LLM 校验 confirm/correct/reject、notes 生成

---

## 8. Self-Review Checklist

- [ ] PostmortemResult 字段完整，mfe/mae/return_pct 占位明确
- [ ] LLMValidationResult 的 confirm/correct/reject 处理逻辑清晰
- [ ] source 字段含义明确（auto/llm_confirmed/llm_corrected/llm_rejected）
- [ ] extra["auto_original"] 在 correct/reject 时保留
- [ ] LLMValidator protocol 定义清晰，可 mock
- [ ] 复用现有 LLM 配置，不单独配置
- [ ] 上游/下游数据流关系清晰
