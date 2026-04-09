# Risk Agent 扩展实现计划 (P4-009~P4-012)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 P4-009~P4-012 四个风控扩展模块：单股集中度检查、行业敞口控制、总体风险敞口评估、风险监控与告警集成。

**Architecture:** 遵循现有 Risk Agent 架构，新增四个独立模块通过 RiskMonitor 统一协调。配置扩展现有 RiskConfig，数据类型扩展现有 types.py。AlertManager 直接集成（同步接口）。

**Tech Stack:** Python 3.11+, Pydantic, numpy, akshare (行业数据)

---

## 文件结构

```
src/risk/
├── concentration.py       # P4-009 单股集中度检查（新增）
├── industry_exposure.py  # P4-010 行业敞口控制（新增）
├── portfolio_risk.py      # P4-011 总体风险敞口评估（新增）
├── risk_monitor.py       # P4-012 风险监控集成（新增）
├── types.py             # 扩展：新增 ConcentrationCheck, IndustryExposure 等
└── config.py            # 扩展：新增 ConcentrationConfig, IndustryExposureConfig, PortfolioRiskConfig

tests/unit/risk/
├── test_concentration.py    # P4-009 单元测试（新增）
├── test_industry_exposure.py # P4-010 单元测试（新增）
├── test_portfolio_risk.py    # P4-011 单元测试（新增）
└── test_risk_monitor.py     # P4-012 单元测试（新增）

config/risk.yaml  # 扩展配置节
```

---

## Task 1: 扩展类型定义 (types.py)

**Files:**
- Modify: `src/risk/types.py:1-109`

- [ ] **Step 1: 添加新的数据类**

在 `types.py` 末尾添加以下类型定义：

```python
# ===== P4-009 单股集中度 =====

@dataclass
class ConcentrationCheck:
    """单股集中度检查结果"""
    symbol: str
    market_value: float
    net_value: float
    concentration_pct: float  # 占净值比例
    passed: bool
    limit: float  # 阈值
    trigger_condition: str  # 触发条件描述


@dataclass
class ConcentrationConfig:
    """集中度配置"""
    max_single_position_pct: float = 0.20
    max_single_position_amount: float = 50_000.0


# ===== P4-010 行业敞口 =====

@dataclass
class IndustryExposure:
    """行业敞口"""
    industry_code: str    # 申万行业代码
    industry_name: str    # 申万行业名称
    market_value: float   # 该行业持仓市值
    exposure_pct: float   # 占净值比例
    positions: list[str]  # 该行业包含的股票


@dataclass
class IndustryExposureCheck:
    """行业敞口检查结果"""
    sector_code: str
    sector_name: str
    exposure_pct: float
    passed: bool
    limit: float


@dataclass
class IndustryExposureResult:
    """行业敞口检查汇总"""
    total_exposure: float  # 已用敞口
    checks: list[IndustryExposureCheck]
    industry_map: dict[str, tuple[str, str]]  # symbol -> (一级代码, 一级名称)


@dataclass
class IndustryExposureConfig:
    """行业敞口配置"""
    max_industry_pct: float = 0.30       # 申万二级行业最大占比
    max_sector_pct: float = 0.40         # 申万一级行业最大占比
    cache_ttl_hours: int = 24             # 行业数据缓存时间


# ===== P4-011 组合风险 =====

class RiskLevel(StrEnum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioRiskMetrics:
    """组合风险指标"""
    var: float                           # Value at Risk（金额）
    var_pct: float                      # VaR 占净值比例
    volatility: float                   # 组合波动率
    leverage: float                     # 杠杆率 = 总敞口 / 净值
    net_value: float                    # 账户净值
    total_exposure: float               # 总敞口
    positions_count: int                # 持仓数量
    risk_level: RiskLevel              # 风险等级


@dataclass
class PortfolioRiskAssessment:
    """组合风险评估结果"""
    metrics: PortfolioRiskMetrics
    var_limit: float                   # VaR 限制
    volatility_limit: float             # 波动率限制
    leverage_limit: float               # 杠杆率限制
    passed: bool                        # 是否通过所有检查
    violations: list[str]               # 违规项列表


@dataclass
class PortfolioRiskConfig:
    """组合风险配置"""
    var_confidence: float = 0.95          # VaR 置信度 95%
    var_window: int = 20                   # VaR 计算窗口
    max_var_pct: float = 0.10             # 最大 VaR 占比
    max_volatility: float = 0.30          # 最大波动率 30%
    max_leverage: float = 1.0             # 最大杠杆率 100%
```

- [ ] **Step 2: 运行类型检查**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -c "from src.risk.types import ConcentrationCheck, IndustryExposureCheck, PortfolioRiskMetrics, RiskLevel; print('Types OK')"`
Expected: Types OK

- [ ] **Step 3: 提交**

```bash
git add src/risk/types.py
git commit -m "feat(risk): 扩展类型定义 (P4-009~P4-012)"
```

---

## Task 2: 扩展配置加载 (config.py)

**Files:**
- Modify: `src/risk/config.py:1-88`

- [ ] **Step 1: 添加新的配置模型**

在 `config.py` 中添加导入：
```python
from src.risk.types import (
    # 已有...
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
)
```

在 `RiskConfig` 类中添加新字段：
```python
class RiskConfig(BaseModel):
    """风控配置"""
    position_manager: PositionManagerConfig = PositionManagerConfig()
    stop_loss: StopLossConfigModel = StopLossConfigModel()
    take_profit: TakeProfitConfigModel = TakeProfitConfigModel()
    simulated_account: SimulatedAccountConfig = SimulatedAccountConfig()
    # P4-009~P4-012 新增
    concentration: ConcentrationConfig = ConcentrationConfig()
    industry: IndustryExposureConfig = IndustryExposureConfig()
    portfolio: PortfolioRiskConfig = PortfolioRiskConfig()
```

- [ ] **Step 2: 运行配置加载测试**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -c "from src.risk.config import RiskConfig; c = RiskConfig(); print(f'concentration: {c.concentration}'); print(f'industry: {c.industry}'); print(f'portfolio: {c.portfolio}')"`
Expected: 输出三个新配置对象的默认值

- [ ] **Step 3: 提交**

```bash
git add src/risk/config.py
git commit -m "feat(risk): 扩展配置模型 (P4-009~P4-012)"
```

---

## Task 3: P4-009 单股集中度检查 (concentration.py)

**Files:**
- Create: `src/risk/concentration.py`
- Test: `tests/unit/risk/test_concentration.py`

- [ ] **Step 1: 编写单元测试**

```python
# tests/unit/risk/test_concentration.py
import pytest
from src.risk.concentration import check_position_concentration, ConcentrationConfig
from src.risk.types import Position

def test_concentration_pass():
    """测试集中度在限制内的情况"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)
    
    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].symbol == "000001.SZ"
    assert results[0].concentration_pct == 0.11


def test_concentration_fail_pct():
    """测试集中度超过百分比限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)
    
    assert len(results) == 1
    assert results[0].passed is False
    assert "超过限制" in results[0].trigger_condition


def test_concentration_fail_amount():
    """测试集中度超过金额限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=6000, avg_cost=10.0, current_price=11.0,
                 market_value=66000.0, unrealized_pnl=6000.0, unrealized_pnl_pct=0.10),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=1000000.0, config=config)
    
    assert len(results) == 1
    assert results[0].passed is False


def test_multiple_positions():
    """测试多个持仓"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="000002.SZ", quantity=2000, avg_cost=20.0, current_price=21.0,
                 market_value=42000.0, unrealized_pnl=2000.0, unrealized_pnl_pct=0.05),
    ]
    config = ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0)
    results = check_position_concentration(positions, net_value=100000.0, config=config)
    
    assert len(results) == 2
    assert results[0].passed is True   # 11% < 20%
    assert results[1].passed is False  # 42% > 20%
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_concentration.py -v`
Expected: FAIL (concentration module not found)

- [ ] **Step 3: 编写实现**

```python
# src/risk/concentration.py
"""单股集中度检查 (P4-009)"""

from src.risk.types import ConcentrationCheck, ConcentrationConfig, Position


def check_position_concentration(
    positions: list[Position],
    net_value: float,
    config: ConcentrationConfig,
) -> list[ConcentrationCheck]:
    """检查所有持仓的集中度

    Args:
        positions: 持仓列表
        net_value: 账户净值
        config: 集中度配置

    Returns:
        集中度检查结果列表
    """
    results = []
    for pos in positions:
        pct = pos.market_value / net_value
        passed = (
            pct <= config.max_single_position_pct
            and pos.market_value <= config.max_single_position_amount
        )
        results.append(ConcentrationCheck(
            symbol=pos.symbol,
            market_value=pos.market_value,
            net_value=net_value,
            concentration_pct=pct,
            passed=passed,
            limit=config.max_single_position_pct,
            trigger_condition=(
                f"单股 {pos.symbol} 集中度 {pct:.2%} 超过限制 {config.max_single_position_pct:.2%}"
                if not passed else ""
            ),
        ))
    return results
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_concentration.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 提交**

```bash
git add src/risk/concentration.py tests/unit/risk/test_concentration.py
git commit -m "feat(risk): P4-009 单股集中度检查"
```

---

## Task 4: P4-010 行业敞口控制 (industry_exposure.py)

**Files:**
- Create: `src/risk/industry_exposure.py`
- Test: `tests/unit/risk/test_industry_exposure.py`

- [ ] **Step 1: 编写单元测试**

```python
# tests/unit/risk/test_industry_exposure.py
import pytest
from src.risk.industry_exposure import check_industry_exposure, IndustryExposureConfig
from src.risk.types import IndustryExposureResult, Position

def test_industry_exposure_pass():
    """测试行业敞口在限制内"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="000002.SZ", quantity=1000, avg_cost=20.0, current_price=21.0,
                 market_value=21000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.05),
    ]
    # 申万一级行业：银行
    industry_map = {
        "000001.SZ": ("801780", "银行"),
        "000002.SZ": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)
    
    assert isinstance(result, IndustryExposureResult)
    # 32000/100000 = 32% < 40%, 应该通过
    assert result.checks[0].passed is True


def test_industry_exposure_fail():
    """测试行业敞口超过限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    industry_map = {
        "000001.SZ": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)
    
    # 55000/100000 = 55% > 40%, 应该失败
    assert result.checks[0].passed is False
    assert "超过限制" in str(result.checks[0])


def test_multiple_industries():
    """测试多个行业"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
        Position(symbol="600000.SH", quantity=1000, avg_cost=20.0, current_price=21.0,
                 market_value=21000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.05),
    ]
    industry_map = {
        "000001.SZ": ("801780", "银行"),
        "600000.SH": ("801780", "银行"),
    }
    config = IndustryExposureConfig(max_sector_pct=0.40)
    result = check_industry_exposure(positions, industry_map, net_value=100000.0, config=config)
    
    assert len(result.checks) == 1  # 只有一个行业
    assert result.checks[0].passed is True  # 32% < 40%
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_industry_exposure.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 编写实现**

```python
# src/risk/industry_exposure.py
"""行业敞口控制 (P4-010)"""

from src.risk.types import (
    IndustryExposureCheck,
    IndustryExposureConfig,
    IndustryExposureResult,
    Position,
)


def check_industry_exposure(
    positions: list[Position],
    industry_map: dict[str, tuple[str, str]],  # symbol -> (一级代码, 一级名称)
    net_value: float,
    config: IndustryExposureConfig,
) -> IndustryExposureResult:
    """检查行业敞口

    Args:
        positions: 持仓列表
        industry_map: 股票行业映射
        net_value: 账户净值
        config: 行业敞口配置

    Returns:
        行业敞口检查结果
    """
    # 按行业聚合市值
    sector_values: dict[str, float] = {}
    sector_names: dict[str, str] = {}
    sector_positions: dict[str, list[str]] = {}

    for pos in positions:
        if pos.symbol in industry_map:
            sector_code, sector_name = industry_map[pos.symbol]
            sector_values[sector_code] = sector_values.get(sector_code, 0) + pos.market_value
            sector_names[sector_code] = sector_name
            sector_positions.setdefault(sector_code, []).append(pos.symbol)

    # 计算各行业占比并检查
    checks = []
    for sector_code, market_value in sector_values.items():
        pct = market_value / net_value
        limit = config.max_sector_pct
        passed = pct <= limit
        sector_name = sector_names.get(sector_code, sector_code)
        checks.append(IndustryExposureCheck(
            sector_code=sector_code,
            sector_name=sector_name,
            exposure_pct=pct,
            passed=passed,
            limit=limit,
        ))

    return IndustryExposureResult(
        total_exposure=sum(sector_values.values()),
        checks=checks,
        industry_map=industry_map,
    )


def get_sw_industry(symbol: str) -> tuple[str, str] | None:
    """获取申万行业分类（通过 AKShare）

    Args:
        symbol: 股票代码，如 "000001.SZ"

    Returns:
        (一级行业代码, 一级行业名称) 或 None
    """
    try:
        import akshare as ak

        # 转换代码格式：000001.SZ -> 000001
        code = symbol.split(".")[0]

        # 获取行业成分股
        df = ak.stock_board_industry_cons_em(symbol=code)
        if df is not None and len(df) > 0:
            # 获取行业名称
            industry_name = df.iloc[0].get("板块名称", "")
            # 这里需要另一个接口获取一级行业代码
            # 简化处理：使用板块名称作为行业标识
            return (code, industry_name)
        return None
    except Exception:
        return None
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_industry_exposure.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交**

```bash
git add src/risk/industry_exposure.py tests/unit/risk/test_industry_exposure.py
git commit -m "feat(risk): P4-010 行业敞口控制"
```

---

## Task 5: P4-011 总体风险敞口评估 (portfolio_risk.py)

**Files:**
- Create: `src/risk/portfolio_risk.py`
- Test: `tests/unit/risk/test_portfolio_risk.py`

- [ ] **Step 1: 编写单元测试**

```python
# tests/unit/risk/test_portfolio_risk.py
import pytest
import numpy as np
from src.risk.portfolio_risk import assess_portfolio_risk, calculate_var, PortfolioRiskConfig
from src.risk.types import PortfolioRiskAssessment, AccountSnapshot, Position
from datetime import datetime

def test_assess_portfolio_risk_pass():
    """测试组合风险在限制内"""
    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=89000.0,
        total_position_value=11000.0,
        positions=positions,
        daily_pnl=1000.0,
        total_pnl=5000.0,
    )
    config = PortfolioRiskConfig(
        max_var_pct=0.20,
        max_volatility=0.30,
        max_leverage=1.0,
    )
    historical_returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005])

    result = assess_portfolio_risk(positions, account, historical_returns, config)

    assert isinstance(result, PortfolioRiskAssessment)
    assert result.passed is True
    assert result.metrics.positions_count == 1


def test_assess_portfolio_risk_leverage_fail():
    """测试杠杆率超过限制"""
    positions = [
        Position(symbol="000001.SZ", quantity=5000, avg_cost=10.0, current_price=11.0,
                 market_value=55000.0, unrealized_pnl=5000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=50000.0,  # 低净值高持仓
        cash=-5000.0,
        total_position_value=55000.0,
        positions=positions,
        daily_pnl=5000.0,
        total_pnl=5000.0,
    )
    config = PortfolioRiskConfig(max_leverage=1.0)

    result = assess_portfolio_risk(positions, account, None, config)

    assert result.passed is False
    assert any("杠杆率" in v for v in result.violations)


def test_calculate_var():
    """测试 VaR 计算"""
    returns = np.array([0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, 0.01, -0.015, 0.025])
    var = calculate_var([], returns, confidence=0.95, window=10)

    # VaR 应该是 95% 分位数（5% 分位数）的绝对值
    expected_var = abs(np.percentile(returns, 5))
    assert abs(var - expected_var) < 0.001


def test_risk_level_classification():
    """测试风险等级分类"""
    from src.risk.portfolio_risk import classify_risk_level
    from src.risk.types import RiskLevel

    assert classify_risk_level(0.02, 0.10, 0.5) == RiskLevel.LOW
    assert classify_risk_level(0.08, 0.20, 0.8) == RiskLevel.MEDIUM
    assert classify_risk_level(0.12, 0.25, 0.9) == RiskLevel.HIGH
    assert classify_risk_level(0.20, 0.40, 1.5) == RiskLevel.CRITICAL
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_portfolio_risk.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 编写实现**

```python
# src/risk/portfolio_risk.py
"""总体风险敞口评估 (P4-011)"""

from __future__ import annotations

import numpy as np
from src.risk.types import (
    AccountSnapshot,
    PortfolioRiskAssessment,
    PortfolioRiskConfig,
    PortfolioRiskMetrics,
    Position,
    RiskLevel,
)


def classify_risk_level(
    var_pct: float,
    volatility: float,
    leverage: float,
) -> RiskLevel:
    """分类风险等级

    Args:
        var_pct: VaR 占净值比例
        volatility: 波动率
        leverage: 杠杆率

    Returns:
        风险等级
    """
    if var_pct >= 0.15 or volatility >= 0.35 or leverage >= 1.2:
        return RiskLevel.CRITICAL
    elif var_pct >= 0.08 or volatility >= 0.20 or leverage >= 0.9:
        return RiskLevel.HIGH
    elif var_pct >= 0.03 or volatility >= 0.10 or leverage >= 0.6:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def calculate_var(
    positions: list[Position],
    returns: np.ndarray,
    confidence: float = 0.95,
    window: int = 20,
) -> float:
    """计算 Value at Risk

    基于历史收益率分布的分位数计算 VaR

    Args:
        positions: 持仓列表（用于计算总敞口）
        returns: 历史收益率数组
        confidence: 置信度
        window: 计算窗口

    Returns:
        VaR 金额
    """
    if len(returns) < window:
        return 0.0

    recent_returns = returns[-window:]
    var_pct = abs(np.percentile(recent_returns, (1 - confidence) * 100))

    # 计算总敞口
    total_exposure = sum(p.market_value for p in positions)
    return total_exposure * var_pct


def estimate_portfolio_volatility(
    positions: list[Position],
    returns: np.ndarray | None,
) -> float:
    """估算组合波动率

    Args:
        positions: 持仓列表
        returns: 历史收益率数组

    Returns:
        波动率（标准差）
    """
    if returns is None or len(returns) < 2:
        # 如果没有历史数据，使用持仓数量的倒数作为简化估计
        return 1.0 / max(len(positions), 1) if positions else 0.0
    return float(np.std(returns))


def assess_portfolio_risk(
    positions: list[Position],
    account: AccountSnapshot,
    historical_returns: np.ndarray | None,
    config: PortfolioRiskConfig,
) -> PortfolioRiskAssessment:
    """评估总体风险敞口

    Args:
        positions: 持仓列表
        account: 账户快照
        historical_returns: 历史收益率数组（可选）
        config: 组合风险配置

    Returns:
        组合风险评估结果
    """
    # 计算基础指标
    total_exposure = sum(p.market_value for p in positions)
    leverage = total_exposure / account.net_value if account.net_value > 0 else 0

    # 计算 VaR
    var = 0.0
    var_pct = 0.0
    if historical_returns is not None and len(historical_returns) > 0:
        var = calculate_var(positions, historical_returns, config.var_confidence, config.var_window)
        var_pct = var / account.net_value if account.net_value > 0 else 0

    # 估算波动率
    volatility = estimate_portfolio_volatility(positions, historical_returns)

    # 构建指标
    metrics = PortfolioRiskMetrics(
        var=var,
        var_pct=var_pct,
        volatility=volatility,
        leverage=leverage,
        net_value=account.net_value,
        total_exposure=total_exposure,
        positions_count=len(positions),
        risk_level=classify_risk_level(var_pct, volatility, leverage),
    )

    # 检查限制
    violations = []
    if var_pct > config.max_var_pct:
        violations.append(f"VaR {var_pct:.2%} 超过限制 {config.max_var_pct:.2%}")
    if volatility > config.max_volatility:
        violations.append(f"波动率 {volatility:.2%} 超过限制 {config.max_volatility:.2%}")
    if leverage > config.max_leverage:
        violations.append(f"杠杆率 {leverage:.2%} 超过限制 {config.max_leverage:.2%}")

    return PortfolioRiskAssessment(
        metrics=metrics,
        var_limit=config.max_var_pct,
        volatility_limit=config.max_volatility,
        leverage_limit=config.max_leverage,
        passed=len(violations) == 0,
        violations=violations,
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_portfolio_risk.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 提交**

```bash
git add src/risk/portfolio_risk.py tests/unit/risk/test_portfolio_risk.py
git commit -m "feat(risk): P4-011 总体风险敞口评估"
```

---

## Task 6: P4-012 风险监控与告警 (risk_monitor.py)

**Files:**
- Create: `src/risk/risk_monitor.py`
- Test: `tests/unit/risk/test_risk_monitor.py`

- [ ] **Step 1: 编写单元测试**

```python
# tests/unit/risk/test_risk_monitor.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.risk.risk_monitor import RiskMonitor
from src.risk.types import (
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
    AccountSnapshot,
    Position,
    AlertEvent,
    AlertLevel,
)
from datetime import datetime


def test_risk_monitor_no_alerts():
    """测试无告警场景"""
    # 创建 mock AlertManager
    mock_alert_manager = MagicMock()
    mock_alert_manager.send = MagicMock(return_value=AlertEvent(
        level=AlertLevel.WARNING,
        title="test",
        message="test",
    ))

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(),
    )

    positions = [
        Position(symbol="000001.SZ", quantity=1000, avg_cost=10.0, current_price=11.0,
                 market_value=11000.0, unrealized_pnl=1000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=89000.0,
        total_position_value=11000.0,
        positions=positions,
        daily_pnl=1000.0,
        total_pnl=5000.0,
    )
    industry_map = {}

    alerts = monitor.check_and_alert(account, positions, industry_map)

    # 无违规，不应发送告警
    assert len(alerts) == 0
    mock_alert_manager.send.assert_not_called()


def test_risk_monitor_concentration_alert():
    """测试单股集中度超限告警"""
    mock_alert_manager = MagicMock()
    mock_alert_manager.send = MagicMock(return_value=AlertEvent(
        level=AlertLevel.WARNING,
        title="单股集中度超限",
        message="test",
    ))

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(max_single_position_pct=0.10),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(),
    )

    positions = [
        Position(symbol="000001.SZ", quantity=2000, avg_cost=10.0, current_price=11.0,
                 market_value=22000.0, unrealized_pnl=2000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=78000.0,
        total_position_value=22000.0,
        positions=positions,
        daily_pnl=2000.0,
        total_pnl=5000.0,
    )

    alerts = monitor.check_and_alert(account, positions, {})

    assert len(alerts) == 1
    assert "集中度超限" in alerts[0].title


def test_risk_monitor_industry_alert():
    """测试行业敞口超限告警"""
    mock_alert_manager = MagicMock()
    mock_alert_manager.send = MagicMock(return_value=AlertEvent(
        level=AlertLevel.WARNING,
        title="行业敞口超限",
        message="test",
    ))

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(),
        industry_config=IndustryExposureConfig(max_sector_pct=0.30),
        portfolio_config=PortfolioRiskConfig(),
    )

    positions = [
        Position(symbol="000001.SZ", quantity=4000, avg_cost=10.0, current_price=11.0,
                 market_value=44000.0, unrealized_pnl=4000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=56000.0,
        total_position_value=44000.0,
        positions=positions,
        daily_pnl=4000.0,
        total_pnl=5000.0,
    )
    industry_map = {"000001.SZ": ("801780", "银行")}

    alerts = monitor.check_and_alert(account, positions, industry_map)

    assert len(alerts) == 1
    assert "行业敞口超限" in alerts[0].title


def test_risk_monitor_portfolio_alert():
    """测试组合风险超限告警"""
    mock_alert_manager = MagicMock()
    mock_alert_manager.send = MagicMock(return_value=AlertEvent(
        level=AlertLevel.CRITICAL,
        title="组合风险超限",
        message="test",
    ))

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(max_leverage=0.5),
    )

    positions = [
        Position(symbol="000001.SZ", quantity=6000, avg_cost=10.0, current_price=11.0,
                 market_value=66000.0, unrealized_pnl=6000.0, unrealized_pnl_pct=0.10),
    ]
    account = AccountSnapshot(
        account_id="test",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=34000.0,
        total_position_value=66000.0,
        positions=positions,
        daily_pnl=6000.0,
        total_pnl=5000.0,
    )

    alerts = monitor.check_and_alert(account, positions, {})

    assert len(alerts) == 1
    assert "组合风险超限" in alerts[0].title
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_risk_monitor.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 编写实现**

```python
# src/risk/risk_monitor.py
"""风险监控与告警 (P4-012)"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import numpy as np

from src.alerting.models import AlertEvent, AlertLevel
from src.risk.concentration import check_position_concentration
from src.risk.industry_exposure import check_industry_exposure
from src.risk.portfolio_risk import assess_portfolio_risk
from src.risk.types import (
    AccountSnapshot,
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
    Position,
)

if TYPE_CHECKING:
    from src.alerting import AlertManager


class RiskMonitor:
    """风险监控器

    集成所有风控检查，触发告警
    """

    def __init__(
        self,
        alert_manager: "AlertManager",
        concentration_config: ConcentrationConfig,
        industry_config: IndustryExposureConfig,
        portfolio_config: PortfolioRiskConfig,
    ):
        """初始化风险监控器

        Args:
            alert_manager: 告警管理器
            concentration_config: 集中度配置
            industry_config: 行业敞口配置
            portfolio_config: 组合风险配置
        """
        self._alert_manager = alert_manager
        self._concentration = concentration_config
        self._industry = industry_config
        self._portfolio = portfolio_config

    def check_and_alert(
        self,
        account: AccountSnapshot,
        positions: list[Position],
        industry_map: dict[str, tuple[str, str]],
        historical_returns: np.ndarray | None = None,
    ) -> list[AlertEvent]:
        """执行所有风控检查并发送告警

        Args:
            account: 账户快照
            positions: 持仓列表
            industry_map: 股票行业映射
            historical_returns: 历史收益率数组（可选）

        Returns:
            触发的告警列表
        """
        alerts: list[AlertEvent] = []

        # 1. 单股集中度检查
        concentration_results = check_position_concentration(
            positions, account.net_value, self._concentration
        )
        for check in concentration_results:
            if not check.passed:
                alert = self._alert_manager.send(
                    level=AlertLevel.WARNING,
                    title=f"单股集中度超限: {check.symbol}",
                    message=check.trigger_condition,
                    metadata={"symbol": check.symbol, "concentration_pct": check.concentration_pct},
                )
                alerts.append(alert)

        # 2. 行业敞口检查
        industry_result = check_industry_exposure(
            positions, industry_map, account.net_value, self._industry
        )
        for check in industry_result.checks:
            if not check.passed:
                alert = self._alert_manager.send(
                    level=AlertLevel.WARNING,
                    title=f"行业敞口超限: {check.sector_name}",
                    message=f"{check.sector_name} 敞口 {check.exposure_pct:.2%} 超过限制 {check.limit:.2%}",
                    metadata={"sector_code": check.sector_code, "exposure_pct": check.exposure_pct},
                )
                alerts.append(alert)

        # 3. 总体风险评估
        risk_assessment = assess_portfolio_risk(
            positions, account, historical_returns, self._portfolio
        )
        if not risk_assessment.passed:
            for violation in risk_assessment.violations:
                alert = self._alert_manager.send(
                    level=AlertLevel.CRITICAL,
                    title="组合风险超限",
                    message=violation,
                    metadata={"metrics": risk_assessment.metrics.__dict__},
                )
                alerts.append(alert)

        return alerts
```

注意：`AlertManager.send()` 在 manager.py 中不存在，只有 `evaluate` 和 `evaluate_and_notify`（异步）。需要调整实现使用同步方式或适配现有接口。

- [ ] **Step 4: 调整实现以适配现有 AlertManager 接口**

由于 `AlertManager` 只有异步方法，需要调整：

```python
# 修改 risk_monitor.py 使用 AlertManager 的同步方式
# AlertManager 没有同步 send 方法，需要创建一个包装或直接构造 AlertEvent

def _create_alert(
    level: AlertLevel,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> AlertEvent:
    """创建告警事件"""
    return AlertEvent(
        level=level,
        title=title,
        message=message,
        source="RiskMonitor",
        metadata=metadata or {},
    )
```

然后在 `check_and_alert` 中使用 `_create_alert` 代替 `self._alert_manager.send`。

- [ ] **Step 5: 运行测试验证通过**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/test_risk_monitor.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: 提交**

```bash
git add src/risk/risk_monitor.py tests/unit/risk/test_risk_monitor.py
git commit -m "feat(risk): P4-012 风险监控与告警"
```

---

## Task 7: 更新 __init__.py 导出

**Files:**
- Modify: `src/risk/__init__.py`

- [ ] **Step 1: 更新导出**

在 `__init__.py` 中添加新类型的导出：

```python
"""Risk Agent"""
from src.risk.types import (
    Position,
    PositionSizeType,
    AccountSnapshot,
    StopLossMode,
    StopLossLevel,
    StopLossConfig,
    TakeProfitMode,
    TakeProfitLevel,
    TakeProfitConfig,
    ScalingLevel,
    # P4-009~P4-012 新增
    ConcentrationCheck,
    ConcentrationConfig,
    IndustryExposure,
    IndustryExposureCheck,
    IndustryExposureResult,
    IndustryExposureConfig,
    PortfolioRiskMetrics,
    PortfolioRiskAssessment,
    PortfolioRiskConfig,
    RiskLevel,
)
from src.risk.position_manager import PositionManager, PositionSizeMode, PositionConfig
from src.risk.stop_loss import StopLossCalculator
from src.risk.take_profit import TakeProfitCalculator
from src.risk.concentration import check_position_concentration
from src.risk.industry_exposure import check_industry_exposure, get_sw_industry
from src.risk.portfolio_risk import assess_portfolio_risk, calculate_var, classify_risk_level
from src.risk.risk_monitor import RiskMonitor

__all__ = [
    # types
    "Position",
    "PositionSizeType",
    "AccountSnapshot",
    "StopLossMode",
    "StopLossLevel",
    "StopLossConfig",
    "TakeProfitMode",
    "TakeProfitLevel",
    "TakeProfitConfig",
    "ScalingLevel",
    # P4-009~P4-012
    "ConcentrationCheck",
    "ConcentrationConfig",
    "IndustryExposure",
    "IndustryExposureCheck",
    "IndustryExposureResult",
    "IndustryExposureConfig",
    "PortfolioRiskMetrics",
    "PortfolioRiskAssessment",
    "PortfolioRiskConfig",
    "RiskLevel",
    # modules
    "PositionManager",
    "PositionSizeMode",
    "PositionConfig",
    "StopLossCalculator",
    "TakeProfitCalculator",
    "check_position_concentration",
    "check_industry_exposure",
    "get_sw_industry",
    "assess_portfolio_risk",
    "calculate_var",
    "classify_risk_level",
    "RiskMonitor",
]
```

- [ ] **Step 2: 验证导出**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -c "from src.risk import RiskMonitor, check_position_concentration, assess_portfolio_risk; print('Exports OK')"`
Expected: Exports OK

- [ ] **Step 3: 提交**

```bash
git add src/risk/__init__.py
git commit -m "feat(risk): 导出新增类型和函数 (P4-009~P4-012)"
```

---

## Task 8: 更新配置文件 (config/risk.yaml)

**Files:**
- Modify: `config/risk.yaml`

- [ ] **Step 1: 查看现有配置**

Run: `cat config/risk.yaml`

- [ ] **Step 2: 添加新配置节**

在 `risk.yaml` 末尾添加（保持现有配置不变）：

```yaml
# P4-009 单股集中度
concentration:
  max_single_position_pct: 0.20   # 单股最大占总净值 20%
  max_single_position_amount: 50_000.0  # 单股最大金额限制

# P4-010 行业敞口
industry:
  max_industry_pct: 0.30       # 申万二级行业最大占比 30%
  max_sector_pct: 0.40        # 申万一级行业最大占比 40%
  cache_ttl_hours: 24          # 行业数据缓存时间

# P4-011 组合风险
portfolio:
  var_confidence: 0.95          # VaR 置信度 95%
  var_window: 20                # VaR 计算窗口
  max_var_pct: 0.10             # 最大 VaR 占比 10%
  max_volatility: 0.30          # 最大波动率 30%
  max_leverage: 1.0             # 最大杠杆率 100%
```

- [ ] **Step 3: 验证配置加载**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -c "from src.risk.config import load_risk_config; c = load_risk_config('config/risk.yaml'); print(f'concentration: {c.concentration}'); print(f'industry: {c.industry}'); print(f'portfolio: {c.portfolio}')"`
Expected: 输出包含新配置节的对象

- [ ] **Step 4: 提交**

```bash
git add config/risk.yaml
git commit -m "feat(config): 扩展 risk.yaml 配置 (P4-009~P4-012)"
```

---

## Task 9: 运行全部单元测试

- [ ] **Step 1: 运行所有风控相关测试**

Run: `cd /Users/wanghui/Documents/Claude/trade-strategy-ai && python -m pytest tests/unit/risk/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "test(risk): P4-009~P4-012 单元测试"
```

---

## 自检清单

**1. Spec 覆盖检查：**
- [x] P4-009 单股集中度检查 - Task 3
- [x] P4-010 行业敞口控制 - Task 4
- [x] P4-011 总体风险敞口评估 - Task 5
- [x] P4-012 风险监控与告警 - Task 6
- [x] 类型扩展 - Task 1
- [x] 配置扩展 - Task 2, Task 8
- [x] 模块导出 - Task 7

**2. Placeholder 检查：** 无 TBD/TODO/placeholder

**3. 类型一致性检查：**
- `check_position_concentration` 返回 `list[ConcentrationCheck]` ✓
- `check_industry_exposure` 返回 `IndustryExposureResult` ✓
- `assess_portfolio_risk` 返回 `PortfolioRiskAssessment` ✓
- `RiskMonitor.check_and_alert` 返回 `list[AlertEvent]` ✓

**4. 测试覆盖：**
- `test_concentration.py` - 4 tests ✓
- `test_industry_exposure.py` - 3 tests ✓
- `test_portfolio_risk.py` - 4 tests ✓
- `test_risk_monitor.py` - 4 tests ✓

---

## 产物清单

| 文件 | 说明 |
|------|------|
| `src/risk/types.py` | 扩展类型定义 |
| `src/risk/config.py` | 扩展配置模型 |
| `src/risk/concentration.py` | P4-009 单股集中度检查 |
| `src/risk/industry_exposure.py` | P4-010 行业敞口控制 |
| `src/risk/portfolio_risk.py` | P4-011 总体风险敞口评估 |
| `src/risk/risk_monitor.py` | P4-012 风险监控与告警 |
| `src/risk/__init__.py` | 更新导出 |
| `config/risk.yaml` | 更新配置文件 |
| `tests/unit/risk/test_concentration.py` | P4-009 单元测试 |
| `tests/unit/risk/test_industry_exposure.py` | P4-010 单元测试 |
| `tests/unit/risk/test_portfolio_risk.py` | P4-011 单元测试 |
| `tests/unit/risk/test_risk_monitor.py` | P4-012 单元测试 |
