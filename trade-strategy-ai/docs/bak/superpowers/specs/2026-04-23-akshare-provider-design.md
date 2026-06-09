# AkShare Provider 设计

## 背景

项目里已经有 `market_data/service.py` 负责缓存、同步和校验，也已经有 `market_data_provider.py` 负责对外输出统一的 `ohlcv_1d` 结构。`akshare_provider.py` 的职责不是替代这些层，而是把 AkShare 本身包装成一个可复用的原子 provider，给上层组合使用。

## 目标

- 把 AkShare 的行情能力封装为统一 provider 协议。
- 直接输出标准化 `ohlcv_1d` 数据。
- 同时提供 `fetch_ohlcv_1d()`，让 `market_data_provider.py` 或后续 fallback provider 可以把它当作 backend 使用。

## 职责边界

- 负责：调用 AkShare、选择具体接口、把结果归一为统一 DataFrame / bars。
- 不负责：缓存写盘、任务调度、重试编排、快照持久化、候选池构建。
- 不直接依赖 `DataAgent` 或 `market_universe` 的业务逻辑。

## 结构

- `request()`：接收 capability 和参数，拉取原始行情 DataFrame。
- `normalize()`：把 DataFrame 统一成 `dataset=ohlcv_1d` 的 `bars` 结构。
- `fetch_ohlcv_1d()`：提供给其他 provider 直接复用的原子行情入口。
- `_dispatch_daily_request()`：按 `market_kind` 路由到 AkShare 的具体接口。

## 后续拓展方法

- 每新增一个 AkShare 能力，优先新增一个明确的 capability 分支。
- 每个 capability 保持单一输出结构，避免一个类承载过多业务语义。
- 如果某个能力将来需要做缓存或快照，不要把这些逻辑塞进 `akshare_provider.py`，而是放到更上层的 service 或 provider 组合层。
- 如果后续要支持 `market_calendar`、`fundamentals`、`technical_indicators`，沿用同样的“原子能力 + 统一归一”的方式扩展。

## 验证

- `tests/unit/providers/test_akshare_provider.py`
- `tests/unit/providers/test_market_data_provider.py`
- `tests/unit/providers/test_base.py`

