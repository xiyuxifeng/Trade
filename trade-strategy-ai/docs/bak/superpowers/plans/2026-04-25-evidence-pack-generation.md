# NTL-S5-009 Implementation Plan: Manager 生成 Evidence Pack

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `run_after_close` 中为每条盘前建议生成并持久化完整 EvidencePack（signal_context + full market_data + rules_snapshot），供 postmortem_analysis 任务直接加载。

**Architecture:**
- `run_after_close` 遍历每个 idea 时，调用 `_generate_evidence_pack()` 构造完整 EvidencePack
- EvidencePack 写入 `{output_dir}/evidence_packs/{pack_id}.json`（JSON 文件，与 DailyReport 模式一致）
- `postmortem_tasks` 从 JSON 文件加载，替换 NTL-S5-008 的 ad-hoc 构造
- 需新增 `StrategyLibraryRepository.get_by_version_id()` 和 `StrategyLibraryService.get_version()`

**Tech Stack:** Python asyncio, JSON, SQLAlchemy AsyncSession, EvidencePack, SignalVersioning

---

## File Structure

| 文件 | 操作 |
|------|------|
| `src/strategy_library/repository.py` | 修改（新增 `get_by_version_id`）|
| `src/strategy_library/service.py` | 修改（新增 `get_version`）|
| `src/agents/manager_agent/agent.py` | 修改（新增 5 个方法 + run_after_close 调用）|
| `src/pipeline/tasks/postmortem_tasks.py` | 修改（从 JSON 加载 EvidencePack）|

---

## Task 1: 新增 StrategyLibraryRepository.get_by_version_id

**Files:**
- Modify: `trade-strategy-ai/src/strategy_library/repository.py`
- Test: `trade-strategy-ai/tests/unit/strategy_library/test_repository.py`（如存在）

---

- [ ] **Step 1: 在 repository.py 新增 `get_by_version_id` 方法**

在 `get_released_by_trader_and_date` 方法之后（大约第 56 行）添加：

```python
async def get_by_version_id(
    self, session: AsyncSession, version_id: str
) -> StrategyVersion | None:
    """按 version_id 精确查询策略版本。

    Args:
        session: 数据库 session
        version_id: 版本 ID（如 "trader_001_2026-04-25_released"）

    Returns:
        StrategyVersion 或 None（不存在时）
    """
    stmt = select(TraderStrategyVersion).where(
        TraderStrategyVersion.version_name == version_id,
    )
    result = await session.execute(stmt)
    orm_obj = result.scalar_one_or_none()
    if orm_obj is None:
        return None
    return self._from_orm_model(orm_obj)
```

---

- [ ] **Step 2: 验证 repository 可导入**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "from src.strategy_library.repository import StrategyLibraryRepository; print('OK')"
```

Expected: OK

---

- [ ] **Step 3: Commit**

```bash
git add src/strategy_library/repository.py
git commit -m "feat(NTL-S5-009): add StrategyLibraryRepository.get_by_version_id"
```

---

## Task 2: 新增 StrategyLibraryService.get_version

**Files:**
- Modify: `trade-strategy-ai/src/strategy_library/service.py`

---

- [ ] **Step 1: 在 service.py 新增 `get_version` 方法**

在 `get_latest_draft_version` 方法之后（大约第 65 行）添加：

```python
async def get_version(
    self,
    session: AsyncSession,
    version_id: str,
) -> StrategyVersion | None:
    """按 version_id 读取策略版本。

    用于 EvidencePack 构造时加载 rules_snapshot。

    Args:
        session: 数据库 session
        version_id: 版本 ID

    Returns:
        StrategyVersion 或 None
    """
    return await self._repo.get_by_version_id(session=session, version_id=version_id)
```

---

- [ ] **Step 2: 验证 service 可导入**

```bash
python -c "from src.strategy_library.service import StrategyLibraryService; print('OK')"
```

Expected: OK

---

- [ ] **Step 3: Commit**

```bash
git add src/strategy_library/service.py
git commit -m "feat(NTL-S5-009): add StrategyLibraryService.get_version"
```

---

## Task 3: 修改 manager_agent/agent.py — 新增 5 个方法

**Files:**
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`

---

先确认文件中已有的 import 和 SignalVersioning 的位置：

- `signal_versioning: SignalVersioning` 实例在 `__init__` 中创建（self.signal_versioning）
- `from src.strategy_library.service import StrategyLibraryService` 已有
- `from src.common.utils import read_json, write_json` 已有

---

- [ ] **Step 1: 在 `_append_review_memory` 方法之前（大约行 230）添加 5 个新方法**

```python
def _load_signal_context(self, idea_id: UUID) -> "SignalContext | None":
    """从 signal_versioning 加载 SignalContext。

    signal_versioning 将 {idea_id} 的完整上下文存储在
    {output_dir}/signals/idea_{idea_id}.json 文件中。

    Args:
        idea_id: TradeIdea.idea_id

    Returns:
        SignalContext 或 None（不存在时）
    """
    signal_with_ctx = self.signal_versioning.get_version(f"idea_{idea_id}")
    return signal_with_ctx.context if signal_with_ctx else None


async def _fetch_full_market_data(
    self,
    symbols: list[str],
    config: AppConfig,
) -> dict[str, Any]:
    """从 DataAgent 获取完整行情（ohlcv_1d + indicators）。

    用于 EvidencePack.market_data，供后续 MFE/MAE 计算。

    Args:
        symbols: 标的代码列表
        config: 应用配置

    Returns:
        market_data dict，包含 ohlcv_1d 和 indicators
    """
    if not symbols:
        return {}

    agent = DataAgent(config=config)
    req = DataRequest(
        trader_id="manager",
        symbols=symbols,
        fields=["ohlcv_1d", "indicators"],
    )
    resp = await agent.handle(req)

    if resp.status == DataResponseStatus.ok:
        return resp.payload
    return {}


async def _load_strategy_version_snapshot(
    self,
    strategy_version_id: str | None,
    config: AppConfig,
) -> list[dict]:
    """从 StrategyLibraryService 加载 rules_snapshot。

    Args:
        strategy_version_id: 策略版本 ID
        config: 应用配置

    Returns:
        rules_snapshot 列表
    """
    if not strategy_version_id:
        return []

    service = StrategyLibraryService()
    async with session_scope() as session:
        version = await service.get_version(session, strategy_version_id)
        return version.rules_snapshot if version else []


def _save_evidence_pack(self, pack: EvidencePack) -> Path:
    """将 EvidencePack 写入 JSON 文件。

    路径：{output_dir}/evidence_packs/{pack_id}.json

    Args:
        pack: EvidencePack 实例

    Returns:
        文件路径
    """
    pack_dir = self.output_dir / "evidence_packs"
    pack_dir.mkdir(parents=True, exist_ok=True)
    path = pack_dir / f"{pack.pack_id}.json"
    write_json(path, pack.to_dict())
    return path


async def _generate_evidence_pack(
    self,
    idea: "TradeIdea",
    daily_report: DailyReport,
    last_prices: dict[str, float],
    config: AppConfig,
) -> EvidencePack:
    """为单条 TradeIdea 生成完整 EvidencePack。

    包含：
    - trade_idea：原始交易想法
    - signal_context：从 signal_versioning 加载（NTL-S4-005 扩展的完整上下文）
    - market_data：完整行情（ohlcv_1d + indicators + entry_price + current_price）
    - strategy_version_snapshot：从 StrategyLibraryService 加载的 rules_snapshot

    Args:
        idea: 单条 TradeIdea
        daily_report: 当前 DailyReport
        last_prices: symbol -> current_price 字典
        config: 应用配置

    Returns:
        EvidencePack 实例
    """
    # 1. 加载 SignalContext
    signal_context = self._load_signal_context(idea.idea_id)

    # 2. 获取完整行情
    market_data = await self._fetch_full_market_data([idea.symbol], config)
    market_data["entry_price"] = float(idea.entry.price) if idea.entry and idea.entry.price else None
    market_data["current_price"] = last_prices.get(idea.symbol)

    # 3. 获取策略版本快照
    rules_snapshot = await self._load_strategy_version_snapshot(idea.strategy_version_id, config)

    return EvidencePack.from_trade_idea(
        trade_idea=idea,
        signal_context=signal_context,
        market_data=market_data,
        strategy_version_id=idea.strategy_version_id,
        strategy_version_snapshot=rules_snapshot,
    )
```

---

- [ ] **Step 2: 验证 agent 可导入**

```bash
python -c "from src.agents.manager_agent.agent import ManagerAgent; print('OK')"
```

Expected: OK（如有导入错误，检查是否缺少新的 import）

---

- [ ] **Step 3: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(NTL-S5-009): add 5 helper methods for EvidencePack generation"
```

---

## Task 4: 修改 run_after_close — 调用 EvidencePack 生成

**Files:**
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`（行 630-715 附近）

---

- [ ] **Step 1: 确认插入位置**

在 `run_after_close` 的评估循环中，每个 idea 评估完成后（return_pct 计算后、memory 创建前），需要添加 EvidencePack 生成。

当前结构（大约在行 630-650）：

```python
            return_pct = (float(current_price) - float(entry_price)) / float(entry_price)
            evaluations.append(
                IdeaEvaluation(
                    idea_id=idea.idea_id,
                    ...
                )
            )

            # trigger review tasks
            min_ret = float(self.config.evaluation.min_expected_return)
            memory_type = ...
```

需要在 `evaluations.append(...)` 之后、trigger review 判断之前添加 EvidencePack 生成。

---

- [ ] **Step 2: 添加 EvidencePack 生成调用**

在 `evaluations.append(...)` 之后（大约行 642 之后）添加：

```python
            # NTL-S5-009: 生成并持久化 EvidencePack
            evidence_pack = await self._generate_evidence_pack(
                idea=idea,
                daily_report=daily_report,
                last_prices=last_prices,
                config=self.config,
            )
            self._save_evidence_pack(evidence_pack)
```

同时在文件顶部确认以下 import 存在（如没有则添加）：
- `from src.evaluation.evidence_pack import EvidencePack`
- `from src.common.utils import write_json`（应该已有）
- `from src.db.session import session_scope`

---

- [ ] **Step 3: 验证运行**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
python -c "
from src.common.config import AppConfig
from src.agents.manager_agent.agent import ManagerAgent
print('ManagerAgent import OK')
"
```

Expected: OK

---

- [ ] **Step 4: Commit**

```bash
git add src/agents/manager_agent/agent.py
git commit -m "feat(NTL-S5-009): call EvidencePack generation in run_after_close"
```

---

## Task 5: 修改 postmortem_tasks.py — 从 JSON 加载 EvidencePack

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/postmortem_tasks.py`

---

- [ ] **Step 1: 替换 EvidencePack 构造逻辑**

在 `handle_postmortem_analysis` 中，找到当前构造 EvidencePack 的代码（约在行 68-74）：

```python
    # 构造 EvidencePack（NTL-S5-009 完成前：最小实现）
    evidence_pack = EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        signal_context=None,
        market_data={"last_price": last_prices.get(symbol or trade_idea.symbol)},
        strategy_version_id=trade_idea.strategy_version_id,
        strategy_version_snapshot=[],
    )
```

替换为：

```python
    # NTL-S5-009: 从持久化的 JSON 文件加载 EvidencePack
    pack_id = _find_evidence_pack_id(idea_id_str, config)
    if pack_id:
        pack_path = _evidence_pack_path(pack_id, config)
        if pack_path.exists():
            pack_data = read_json(pack_path)
            evidence_pack = EvidencePack.from_dict(pack_data)
        else:
            # fallback：降级到最小实现（保留容错）
            evidence_pack = EvidencePack(
                idea_id=trade_idea.idea_id,
                trade_date=str(trade_idea.as_of_date),
                trade_idea=trade_idea,
                signal_context=None,
                market_data={"last_price": last_prices.get(symbol or trade_idea.symbol)},
                strategy_version_id=trade_idea.strategy_version_id,
                strategy_version_snapshot=[],
            )
    else:
        # fallback：降级到最小实现
        evidence_pack = EvidencePack(
            idea_id=trade_idea.idea_id,
            trade_date=str(trade_idea.as_of_date),
            trade_idea=trade_idea,
            signal_context=None,
            market_data={"last_price": last_prices.get(symbol or trade_idea.symbol)},
            strategy_version_id=trade_idea.strategy_version_id,
            strategy_version_snapshot=[],
        )
```

同时在文件顶部添加辅助函数：

```python
def _find_evidence_pack_id(idea_id_str: str, config: AppConfig) -> str | None:
    """从 evidence_packs 目录中查找对应 idea_id 的 pack_id。

    遍历 evidence_packs 目录，按 idea_id 匹配。

    Returns:
        pack_id 字符串或 None
    """
    from pathlib import Path
    pack_dir = Path(".") / config.storage.output_dir / "evidence_packs"
    if not pack_dir.exists():
        return None
    # 由于 pack_id 是 UUID，只能通过读取文件内容匹配 idea_id
    for pack_file in pack_dir.glob("*.json"):
        try:
            data = read_json(pack_file)
            if data.get("idea_id") == idea_id_str:
                return pack_file.stem
        except Exception:
            continue
    return None


def _evidence_pack_path(pack_id: str, config: AppConfig) -> Path:
    """获取 EvidencePack JSON 文件路径。"""
    from pathlib import Path
    return Path(".") / config.storage.output_dir / "evidence_packs" / f"{pack_id}.json"
```

---

- [ ] **Step 2: 验证文件可导入**

```bash
python -c "from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis; print('OK')"
```

Expected: OK

---

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/tasks/postmortem_tasks.py
git commit -m "feat(NTL-S5-009): load EvidencePack from JSON in postmortem_tasks"
```

---

## Task 6: 验证集成

---

- [ ] **Step 1: 运行相关测试**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
pytest tests/unit/evaluation/ tests/unit/agents/test_manager_agent.py tests/unit/strategy_library/ -v --tb=short 2>&1 | tail -30
```

---

- [ ] **Step 2: 检查 imports 链**

```bash
python -c "
from src.agents.manager_agent.agent import ManagerAgent
from src.pipeline.tasks.postmortem_tasks import handle_postmortem_analysis
from src.strategy_library.service import StrategyLibraryService
from src.strategy_library.repository import StrategyLibraryRepository
print('All imports OK')
"
```

---

- [ ] **Step 3: 检查 postmortem_tasks 的 EvidencePack 加载逻辑**

```bash
python -c "
from src.common.config import AppConfig
from src.pipeline.tasks.postmortem_tasks import _find_evidence_pack_id, _evidence_pack_path
config = AppConfig()
print('Helper functions import OK')
"
```

---

## Task 7: 更新 TaskList.md

**Files:**
- Modify: `trade-strategy-ai/docs/TaskList.md`

---

- [ ] **Step 1: 标记 NTL-S5-009 完成**

找到 NTL-S5-009 条目（约在行 1210-1218），更新为：

```
- [x] `NTL-S5-009` `P1` ✅ 2026-04-25
  目标：让 Manager 生成 Evidence Pack。
  ...
  完成情况：新增 StrategyLibraryRepository.get_by_version_id + StrategyLibraryService.get_version；manager_agent 新增 5 个辅助方法（_generate_evidence_pack / _save_evidence_pack / _load_signal_context / _fetch_full_market_data / _load_strategy_version_snapshot）；run_after_close 中调用 EvidencePack 生成并持久化到 JSON；postmortem_tasks 从 JSON 加载。
```

---

- [ ] **Step 2: Commit**

```bash
git add docs/TaskList.md
git commit -m "docs(NTL-S5-009): mark complete in TaskList"
```

---

## Spec Coverage Check

- [x] Repository.get_by_version_id → Task 1
- [x] Service.get_version → Task 2
- [x] 5 个 helper methods → Task 3
- [x] run_after_close 调用生成 → Task 4
- [x] postmortem_tasks 从 JSON 加载 → Task 5
- [x] 验证集成 → Task 6
- [x] TaskList 更新 → Task 7

## Self-Review

- **Placeholder scan**: 无 TBD/TODO，所有方法签名和路径都明确
- **Type consistency**: 所有方法签名与现有代码一致
- **Spec coverage**: 所有 spec 条目均有对应 task
- **Path 确认**: `output_dir / "evidence_packs"` 路径与 spec 一致
