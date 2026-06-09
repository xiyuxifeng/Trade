# P4-009~P4-012 Risk Agent 扩展设计文档

**日期**: 2026-04-09
**任务**: P4-009~P4-012 Risk Agent 风控扩展
**状态**: 已批准设计

---

## 一、架构概览

### 1.1 新增模块

```
src/risk/
├── concentration.py       # P4-009 单股集中度检查
├── industry_exposure.py    # P4-010 行业敞口控制
├── portfolio_risk.py       # P4-011 总体风险敞口评估
├── risk_monitor.py        # P4-012 风险监控（集成告警）
├── config.py              # 配置加载（扩展）
└── types.py              # 类型定义（扩展）
```

### 1.2 依赖关系

```
P4-009 单股集中度检查 ──────────┐
                                  ├── P4-012 风险监控 ──→ AlertManager
P4-010 行业敞口控制 ──────────┤
                                  │
P4-011 总体风险敞口评估 ─────────┘
```

---

## 二、P4-009 单股集中度检查

### 2.1 配置

```yaml
risk:
  concentration:
    max_single_position_pct: 0.20   # 单股最大占总净值 20%
    max_single_position_amount: 50_000.0  # 单股最大金额限制
```

### 2.2 类型定义

```python
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
```

### 2.3 检查逻辑

```python
def check_position_concentration(
    positions: list[Position],
    net_value: float,
    config: ConcentrationConfig,
) -> list[ConcentrationCheck]:
    """检查所有持仓的集中度"""
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
            trigger_condition=f"单股 {pos.symbol} 集中度 {pct:.2%} 超过限制 {config.max_single_position_pct:.2%}"
            if not passed else "",
        ))
    return results
```

---

## 三、P4-010 行业敞口控制

### 3.1 配置

```yaml
risk:
  industry:
    max_industry_pct: 0.30       # 申万二级行业最大占比 30%
    max_sector_pct: 0.40        # 申万一级行业最大占比 40%
    cache_ttl_hours: 24          # 行业数据缓存时间
```

### 3.2 类型定义

```python
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
    industry_map: dict[str, IndustryExposure]  # symbol -> industry
```

### 3.3 行业获取（AKShare）

```python
def get_sw_industry(symbol: str) -> tuple[str, str] | None:
    """获取申万行业分类

    Returns:
        (一级行业代码, 一级行业名称) 或 None
    """
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()
        # 需要根据 symbol 查具体股票的行业
        # 使用 stock_board_industry_cons_em 获取行业内成分股
        return sw_code, sw_name
    except Exception:
        return None
```

### 3.4 检查逻辑

```python
def check_industry_exposure(
    positions: list[Position],
    industry_map: dict[str, tuple[str, str]],  # symbol -> (一级代码, 一级名称)
    net_value: float,
    config: IndustryExposureConfig,
) -> IndustryExposureResult:
    """检查行业敞口"""
    # 按行业聚合市值
    sector_values: dict[str, float] = {}
    sector_positions: dict[str, list[str]] = {}

    for pos in positions:
        if pos.symbol in industry_map:
            sector_code, sector_name = industry_map[pos.symbol]
            sector_values[sector_code] = sector_values.get(sector_code, 0) + pos.market_value
            sector_positions.setdefault(sector_code, []).append(pos.symbol)

    # 计算各行业占比并检查
    checks = []
    for sector_code, market_value in sector_values.items():
        pct = market_value / net_value
        limit = config.max_sector_pct
        passed = pct <= limit
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
```

---

## 四、P4-011 总体风险敞口评估

### 4.1 配置

```yaml
risk:
  portfolio:
    var_confidence: 0.95          # VaR 置信度 95%
    var_window: 20                # VaR 计算窗口
    max_volatility: 0.30          # 最大波动率 30%
    max_leverage: 1.0             # 最大杠杆率 100%
```

### 4.2 类型定义

```python
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


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioRiskAssessment:
    """组合风险评估结果"""
    metrics: PortfolioRiskMetrics
    var_limit: float                   # VaR 限制
    volatility_limit: float             # 波动率限制
    leverage_limit: float               # 杠杆率限制
    passed: bool                        # 是否通过所有检查
    violations: list[str]               # 违规项列表
```

### 4.3 VaR 计算

```python
def calculate_var(
    positions: list[Position],
    returns: np.ndarray,  # 历史收益率
    confidence: float = 0.95,
    window: int = 20,
) -> float:
    """计算 Value at Risk

    基于历史收益率分布的分位数计算 VaR
    """
    if len(returns) < window:
        return 0.0

    recent_returns = returns[-window:]
    var = np.percentile(recent_returns, (1 - confidence) * 100)
    return abs(var)
```

### 4.4 评估逻辑

```python
def assess_portfolio_risk(
    positions: list[Position],
    account: AccountSnapshot,
    historical_returns: np.ndarray | None,  # 可选，用于 VaR 计算
    config: PortfolioRiskConfig,
) -> PortfolioRiskAssessment:
    """评估总体风险敞口"""
    # 计算基础指标
    total_exposure = sum(p.market_value for p in positions)
    leverage = total_exposure / account.net_value if account.net_value > 0 else 0

    # 计算 VaR
    var = 0.0
    if historical_returns is not None and len(historical_returns) > 0:
        var = calculate_var(positions, historical_returns, config.var_confidence, config.var_window)
        var_pct = var / account.net_value if account.net_value > 0 else 0
    else:
        var_pct = 0.0

    # 估算波动率（简化版：使用持仓收益率的标准差）
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

---

## 五、P4-012 风险监控与告警

### 5.1 集成 AlertManager

```python
from src.alerting import AlertManager, AlertEvent, AlertLevel

class RiskMonitor:
    """风险监控器

    集成所有风控检查，触发告警
    """

    def __init__(
        self,
        alert_manager: AlertManager,
        concentration_config: ConcentrationConfig,
        industry_config: IndustryExposureConfig,
        portfolio_config: PortfolioRiskConfig,
    ):
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

        Returns:
            触发的告警列表
        """
        alerts = []

        # 1. 单股集中度检查
        concentration_results = check_position_concentration(
            positions, account.net_value, self._concentration
        )
        for check in concentration_results:
            if not check.passed:
                alerts.append(self._alert_manager.send(
                    level=AlertLevel.WARNING,
                    title=f"单股集中度超限: {check.symbol}",
                    message=check.trigger_condition,
                    metadata={"symbol": check.symbol, "concentration_pct": check.concentration_pct},
                ))

        # 2. 行业敞口检查
        industry_result = check_industry_exposure(
            positions, industry_map, account.net_value, self._industry
        )
        for check in industry_result.checks:
            if not check.passed:
                alerts.append(self._alert_manager.send(
                    level=AlertLevel.WARNING,
                    title=f"行业敞口超限: {check.sector_name}",
                    message=f"{check.sector_name} 敞口 {check.exposure_pct:.2%} 超过限制 {check.limit:.2%}",
                    metadata={"sector_code": check.sector_code, "exposure_pct": check.exposure_pct},
                ))

        # 3. 总体风险评估
        risk_assessment = assess_portfolio_risk(
            positions, account, historical_returns, self._portfolio
        )
        if not risk_assessment.passed:
            for violation in risk_assessment.violations:
                alerts.append(self._alert_manager.send(
                    level=AlertLevel.CRITICAL,
                    title="组合风险超限",
                    message=violation,
                    metadata={"metrics": risk_assessment.metrics.__dict__},
                ))

        return alerts
```

---

## 六、配置方法

### 6.1 完整配置 (config/risk.yaml)

```yaml
risk:
  # 头寸管理
  position_manager:
    mode: "fixed_ratio"
    fixed_amount: 10_000.0
    fixed_ratio_pct: 0.05
    target_volatility: 0.15
    max_position_pct: 0.20
    max_single_position: 50_000.0

  # 止损
  stop_loss:
    mode: "volatility"
    fixed_pct: 0.05
    atr_multiplier: 2.0
    atr_window: 14
    drawdown_pct: 0.10
    max_hold_days: 10

  # 止盈
  take_profit:
    mode: "scaling"
    fixed_pct: 0.15
    scaling_levels:
      - target_pct: 0.05
        close_pct: 0.50
      - target_pct: 0.10
        close_pct: 0.30
      - target_pct: 0.20
        close_pct: 0.20
    trailing_pct: 0.05
    target_hold_days: 5

  # P4-009 单股集中度
  concentration:
    max_single_position_pct: 0.20
    max_single_position_amount: 50_000.0

  # P4-010 行业敞口
  industry:
    max_industry_pct: 0.30
    max_sector_pct: 0.40
    cache_ttl_hours: 24

  # P4-011 组合风险
  portfolio:
    var_confidence: 0.95
    var_window: 20
    max_var_pct: 0.10
    max_volatility: 0.30
    max_leverage: 1.0

simulated_account:
  enabled: true
  initial_capital: 100_000.0
  persist_to_db: true
```

---

## 七、数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                         RiskMonitor                              │
│  check_and_alert()                                            │
└─────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│  P4-009       │  │  P4-010        │  │  P4-011            │
│  Concentration│  │  Industry      │  │  PortfolioRisk     │
│  Checker     │  │  Exposure      │  │  Assessment        │
└───────────────┘  └─────────────────┘  └─────────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  AlertManager   │
                    │  (P5-019)       │
                    └─────────────────┘
```

---

## 八、文件清单

| 文件 | 任务 | 说明 |
|------|------|------|
| `src/risk/concentration.py` | P4-009 | 单股集中度检查 |
| `src/risk/industry_exposure.py` | P4-010 | 行业敞口控制 |
| `src/risk/portfolio_risk.py` | P4-011 | 总体风险敞口评估 |
| `src/risk/risk_monitor.py` | P4-012 | 风险监控（集成告警） |
| `src/risk/types.py` | - | 扩展类型定义 |
| `src/risk/config.py` | - | 扩展配置加载 |
| `config/risk.yaml` | - | 更新配置文件 |
| `tests/unit/risk/test_concentration.py` | P4-009 | 单元测试 |
| `tests/unit/risk/test_industry_exposure.py` | P4-010 | 单元测试 |
| `tests/unit/risk/test_portfolio_risk.py` | P4-011 | 单元测试 |
| `tests/unit/risk/test_risk_monitor.py` | P4-012 | 单元测试 |
| `tests/integration/test_risk_monitor_integration.py` | - | 集成测试 |

---

## 九、依赖关系

```
P4-009~P4-012 依赖:
├── src/risk/types.py (已有，需扩展)
├── src/risk/config.py (已有，需扩展)
├── src/alerting/AlertManager (P5-019)
├── akshare (行业数据获取)
└── numpy (VaR 计算)
```
