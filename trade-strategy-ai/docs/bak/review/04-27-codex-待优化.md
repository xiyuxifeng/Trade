# Stage 6 任务完成情况 Review（Codex）

> 日期：2026-04-27
> 范围：NTL-S6-001 ~ NTL-S6-013（backtest / rule validation / CLI / scoring）

## 结论概览
Stage 6 的主干模块已落地，schema → execution → engine → scoring → reporting → CLI → rule_registry → reproducibility 链路具备可运行骨架。本轮 Review 发现的问题已完成修复，但仍需真实依赖注入与集成测试验证。

## 修复完成情况
- 回测 report 回放链路已补齐，records/summary 可回放。
- SnapshotLoader 已补齐 listing_dates，并支持 symbols 过滤。
- 交易日历默认加载路径已加入（优先 akshare，失败回退）。
- validate-rules 已兼容事件循环并补齐验真状态。
- entry_price 缺失时标记为 invalid。
- 规则注册正则已与注释对齐，支持下划线后缀。

## 关键问题与风险（按严重度）
### P0 / 高
1) 回测报告命令忽略实际结果（已修复）
- backtest report 已按 JSON 构造 records/summary。
- 参考：[cli/backtest.py](trade-strategy-ai/cli/backtest.py#L101-L160)

2) 新股 5 日无涨跌幅规则无法生效（已修复）
- SnapshotLoader 已补齐 listing_dates。
- 参考：[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L476-L525) ，[src/backtest/snapshot_loader.py](trade-strategy-ai/src/backtest/snapshot_loader.py#L64-L131)

### P1 / 中
3) 交易日历只默认跳过周末（已修复）
- TradeCalendar 默认尝试从 akshare 加载。
- 参考：[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L100-L134)

4) CLI 规则验真在已有事件循环中会失败（已修复）
- validate-rules 使用兼容执行器。
- 参考：[cli/backtest.py](trade-strategy-ai/cli/backtest.py#L145-L172)

5) symbols 过滤未生效（已修复）
- bars/indicators/listing_dates 已按 symbols 过滤。
- 参考：[src/backtest/snapshot_loader.py](trade-strategy-ai/src/backtest/snapshot_loader.py#L64-L131)

6) 规则验真状态表达不完整（已修复）
- 已补齐 missing_field / missing_snapshot / invalid_rule。
- 参考：[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L220-L299)

7) akshare 缺失时交易日历会“全不可用”（已修复）
- load_from_akshare 失败时回退为 holidays 逻辑，不再把所有日期判为非交易日。
- 参考：[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L113-L135)

8) SnapshotLoader await 同步 SnapshotService（已修复）
- SnapshotLoader 增加 sync/async 兼容适配。
- 参考：[src/backtest/snapshot_loader.py](trade-strategy-ai/src/backtest/snapshot_loader.py#L33-L139)，[src/market_universe/snapshot_service.py](trade-strategy-ai/src/market_universe/snapshot_service.py#L97-L130)

### P2 / 低
9) 规则注册注释与实现不一致（已修复）
- 正则已支持下划线后缀。
- 参考：[src/backtest/rule_registry.py](trade-strategy-ai/src/backtest/rule_registry.py#L37-L45)

10) 缺省 entry_price 仍被标记为 closed（已修复）
- entry_price 缺失时标记为 invalid。
- 参考：[src/backtest/engine.py](trade-strategy-ai/src/backtest/engine.py#L451-L531)

## 与前序 Stage 串联情况
- 与 Stage 5：scoring 复用 compute_mfe_mae_return，口径一致，链路可复用。
- 与 Stage 3/4：engine 通过 loader 接口读取策略版本和快照，设计上可串联；但 CLI 目前未完成真实依赖注入（仍是 TODO），在实际运行中会全部 skipped。
- 参考：[cli/backtest.py](trade-strategy-ai/cli/backtest.py#L46-L54)

## A 股市场规则符合度
- 已覆盖：涨跌停幅度、T+1、ST 规则日期切换、停牌判定。
- 本轮已补齐：新股 5 日无涨跌幅、法定节假日交易日历默认加载。

## 改进建议（优先级）
1) 补齐真实依赖注入（snapshot_service / strategy_repo），完成集成验证。
2) 新增多日多标的回测与跨节假日的集成测试。
