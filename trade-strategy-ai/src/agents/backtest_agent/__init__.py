"""
历史 backtest agent 目录（已冻结 NTL-S15-008）。

Stage 6 起，回测主路径统一迁移到 src/backtest/。
本目录保留只读，不再承接新功能。

⚠️ 已冻结：BacktestAgent 主线职责已停止开发。
- 本模块不再作为当前核心交付路径的一部分。
- 目录保留为历史参考，不继续投入主线开发。
- 后续回测开发统一进入 src/backtest/ 模块。

历史职责：
  - run_backtest: 执行回测
  - evaluate_metrics: 评估指标
  - parameter_search: 参数搜索
"""
