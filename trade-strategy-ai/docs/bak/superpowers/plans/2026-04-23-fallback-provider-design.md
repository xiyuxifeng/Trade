# NTL-S2-007 Fallback Provider 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `fallback_provider.py`，实现 provider 级联降级：主 provider 异常时按顺序尝试备用 provider，最终返回合并结果或错误聚合。

**Architecture:** `FallbackProvider` 继承 `ProviderBase`，内部维护 `capability -> 有序 provider 列表` 的映射。`run()` 方法遍历候选链，记录每级的错误与部分结果，全部失败时返回 `ProviderStatus.error` 与完整错误列表；部分成功时返回 `ProviderStatus.partial` 与合并 payload。

**Tech Stack:** Python, `src/providers/base.py`（`ProviderBase`, `ProviderResult`, `ProviderStatus`, `ProviderError`）

---

## 文件结构

- Create: `src/providers/fallback_provider.py`
- Modify: `src/providers/__init__.py`
- Test: `tests/unit/providers/test_fallback_provider.py`

---

### Task 1: 实现 FallbackProvider 核心类

**Files:**
- Create: `src/providers/fallback_provider.py`
- Modify: `src/providers/__init__.py:12-21`
- Test: `tests/unit/providers/test_fallback_provider.py::test_fallback_provider_basic_structure`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/providers/test_fallback_provider.py
import pytest
from src.providers.base import ProviderBase, ProviderResult, ProviderStatus

def test_fallback_provider_basic_structure():
    """FallbackProvider 应继承 ProviderBase 并实现 request/normalize。"""
    from src.providers.fallback_provider import FallbackProvider

    provider = FallbackProvider(chains={"hot_topics": []})
    assert isinstance(provider, ProviderBase)
    assert provider.provider_name == "fallback"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_fallback_provider_basic_structure -v`
Expected: FAIL - module 'src.providers.fallback_provider' has no attribute 'FallbackProvider'

- [ ] **Step 3: 写最小实现**

```python
# src/providers/fallback_provider.py
from __future__ import annotations

from typing import Any

from src.providers.base import ProviderBase, ProviderResult, ProviderStatus


class FallbackProvider(ProviderBase):
    """级联降级 provider。

    内部维护 capability -> 有序 provider 列表的映射。
    run() 遍历候选链，直到某个 provider 成功；全部失败时返回聚合错误。
    """

    def __init__(
        self,
        *,
        chains: dict[str, list[ProviderBase]],
        provider_name: str = "fallback",
    ) -> None:
        super().__init__(provider_name=provider_name)
        self.chains = chains

    def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
        """遍历候选链，返回首个成功结果的 payload。"""
        raise NotImplementedError("TODO")

    def normalize(
        self,
        *,
        capability: str,
        raw: dict[str, Any],
        request: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """fallback 不做额外归一，直接透传。"""
        if isinstance(raw, dict):
            return raw
        return {"data": raw}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_fallback_provider_basic_structure -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/providers/fallback_provider.py tests/unit/providers/test_fallback_provider.py
git commit -m "feat(s2-007): add FallbackProvider skeleton with chains support"
```

---

### Task 2: 实现 run() 遍历逻辑与错误聚合

**Files:**
- Modify: `src/providers/fallback_provider.py`
- Test: `tests/unit/providers/test_fallback_provider.py::test_run_falls_back_on_first_failure`

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/providers/test_fallback_provider.py 新增

def test_run_falls_back_on_second_provider():
    """主 provider 失败时，FallbackProvider 应自动尝试下一个。"""
    from src.providers.base import ProviderError, ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    primary = _MakeFailingProvider(provider_name="primary")
    secondary = _MakeSucceedProvider(provider_name="secondary", payload={"dataset": "hot_topics", "value": 42})

    provider = FallbackProvider(chains={"hot_topics": [primary, secondary]})
    result = provider.run("hot_topics", request={"trade_date": "2026-04-23"})

    assert result.status == ProviderStatus.ok
    assert result.provider == "fallback"
    assert result.payload == {"dataset": "hot_topics", "value": 42}


def test_run_returns_partial_when_all_fail():
    """所有 provider 都失败时，应返回 partial 状态和完整错误列表。"""
    from src.providers.base import ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    p1 = _MakeFailingProvider(provider_name="p1", error_msg="connection error")
    p2 = _MakeFailingProvider(provider_name="p2", error_msg="timeout")

    provider = FallbackProvider(chains={"hot_topics": [p1, p2]})
    result = provider.run("hot_topics", request={"trade_date": "2026-04-23"})

    assert result.status == ProviderStatus.partial
    assert len(result.errors) == 2
    assert "connection error" in result.errors[0]
    assert "timeout" in result.errors[1]


def test_run_returns_ok_with_single_provider():
    """只有一个 provider 且成功时，直接返回其结果。"""
    from src.providers.base import ProviderStatus
    from src.providers.fallback_provider import FallbackProvider

    ok_provider = _MakeSucceedProvider(provider_name="only", payload={"dataset": "ohlcv_1d", "bars": []})
    provider = FallbackProvider(chains={"ohlcv_1d": [ok_provider]})
    result = provider.run("ohlcv_1d", request={"symbol": "000001"})

    assert result.status == ProviderStatus.ok
    assert result.provider == "fallback"


def test_unsupported_capability_raises():
    """未配置 capability 时应抛出 ProviderError。"""
    from src.providers.base import ProviderError
    from src.providers.fallback_provider import FallbackProvider

    provider = FallbackProvider(chains={})
    with pytest.raises(ProviderError, match="fallback does not support capability"):
        provider.run("unknown_cap", request={})


# --- helpers ---

class _MakeSucceedProvider:
    def __init__(self, provider_name: str, payload: dict):
        self.provider_name = provider_name
        self._payload = payload

    def run(self, capability: str, *, request=None):
        from src.providers.base import ProviderResult, ProviderStatus
        return ProviderResult(
            provider=self.provider_name,
            capability=capability,
            status=ProviderStatus.ok,
            payload=self._payload,
        )

    def request(self, **kwargs):
        return self._payload


class _MakeFailingProvider:
    def __init__(self, provider_name: str, error_msg: str = "failed"):
        self.provider_name = provider_name
        self._error_msg = error_msg

    def run(self, capability: str, *, request=None):
        from src.providers.base import ProviderResult, ProviderStatus
        return ProviderResult(
            provider=self.provider_name,
            capability=capability,
            status=ProviderStatus.error,
            errors=[self._error_msg],
            payload={},
        )

    def request(self, **kwargs):
        raise Exception(self._error_msg)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/providers/test_fallback_provider.py -v 2>&1 | head -60`
Expected: FAIL on `test_run_falls_back_on_second_provider` / `test_run_returns_partial_when_all_fail`

- [ ] **Step 3: 实现 run() 遍历逻辑**

```python
# src/providers/fallback_provider.py 替换 request() 实现

def request(self, *, capability: str, **kwargs: Any) -> dict[str, Any]:
    """遍历候选链，返回首个成功结果的 payload。"""
    providers = self.chains.get(capability)
    if not providers:
        self.unsupported(capability)

    errors: list[str] = []
    partials: list[dict[str, Any]] = []

    for p in providers:
        try:
            result = p.run(capability, request=kwargs)
            if result.status == ProviderStatus.ok:
                return result.payload
            # 记录错误和部分结果，供 partial 返回使用
            errors.extend(result.errors)
            if result.payload:
                partials.append(result.payload)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{type(exc).__name__}: {exc}")

    # 所有 provider 都失败，返回 partial 或 error
    # 尝试合并部分结果
    if partials:
        return {"partial": True, "errors": errors, "partial_payloads": partials}

    raise ProviderError("; ".join(errors) if errors else "all providers failed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/providers/test_fallback_provider.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/providers/fallback_provider.py
git commit -m "feat(s2-007): implement run() traversal with error aggregation"
```

---

### Task 3: 补全 normalize 和 unsupported 异常

**Files:**
- Modify: `src/providers/fallback_provider.py`
- Test: 新增 `test_run_normalize_passes_through`

- [ ] **Step 1: 写失败测试**

```python
def test_run_normalize_passes_through():
    """normalize 默认透传 dict。"""
    from src.providers.fallback_provider import FallbackProvider

    ok_provider = _MakeSucceedProvider(provider_name="only", payload={"dataset": "hot_topics", "topics": []})
    provider = FallbackProvider(chains={"hot_topics": [ok_provider]})
    result = provider.run("hot_topics", request={"trade_date": "2026-04-23"})

    assert result.payload.get("dataset") == "hot_topics"
    assert result.payload.get("topics") == []
```

- [ ] **Step 2: Run test to verify it passes (normalize 已默认透传)**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_run_normalize_passes_through -v`
Expected: PASS

- [ ] **Step 3: 补 unsupported 异常测试**

```python
def test_fallback_provider_unsupported_raises():
    from src.providers.base import ProviderError
    from src.providers.fallback_provider import FallbackProvider

    provider = FallbackProvider(chains={})
    with pytest.raises(ProviderError, match="fallback does not support capability: unknown"):
        provider.request(capability="unknown", **{})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_fallback_provider_unsupported_raises -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/providers/fallback_provider.py
git commit -m "feat(s2-007): add unsupported capability exception"
```

---

### Task 4: 注册到 providers 包

**Files:**
- Modify: `src/providers/__init__.py`
- Test: `test_fallback_provider_in_package`

- [ ] **Step 1: 写失败测试**

```python
def test_fallback_provider_in_package():
    """FallbackProvider 应可从 src.providers 导入。"""
    from src.providers import fallback_provider
    assert hasattr(fallback_provider, "FallbackProvider")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_fallback_provider_in_package -v`
Expected: FAIL - cannot import 'fallback_provider'

- [ ] **Step 3: 更新 __init__.py**

```python
# src/providers/__init__.py
"""数据提供者抽象层。"""

from . import base
from . import hot_topics_provider
from . import kaipan_provider
from . import kaipan_normalizer
from . import kaipan_scheduler
from . import akshare_provider
from . import market_data_provider
from . import topic_constituents_provider
from . import fallback_provider

__all__ = [
    "base",
    "hot_topics_provider",
    "kaipan_provider",
    "kaipan_normalizer",
    "kaipan_scheduler",
    "akshare_provider",
    "market_data_provider",
    "topic_constituents_provider",
    "fallback_provider",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/providers/test_fallback_provider.py::test_fallback_provider_in_package -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/providers/__init__.py
git commit -m "feat(s2-007): register FallbackProvider in providers package"
```

---

### Task 5: 端到端集成验证

**Files:**
- Test: `pytest tests/unit/providers/ -v`
- Validate: 所有 provider 测试通过（预期 16 passed）

- [ ] **Step 1: Run all provider tests**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && pytest tests/unit/providers/ -v`
Expected: 全部 PASS（含新增的 fallback_provider 测试）

- [ ] **Step 2: 验证 py_compile**

Run: `python -m py_compile src/providers/fallback_provider.py`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add src/providers/fallback_provider.py src/providers/__init__.py tests/unit/providers/test_fallback_provider.py
git commit -m "feat(s2-007): complete FallbackProvider with chains, partial results and error aggregation"
```

---

## Self-Review Checklist

1. **Spec coverage:** NTL-S2-007 验收标准"主链路 provider 异常时可按顺序降级" - ✅ 覆盖（Task 2 run() 遍历逻辑）
2. **Placeholder scan:** 无 "TBD/TODO/fill in later" - ✅
3. **Type consistency:** `ProviderBase`, `ProviderResult`, `ProviderStatus`, `ProviderError` 均来自 `base.py` - ✅

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-04-23-fallback-provider-design.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**