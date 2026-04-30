
# User Manual

## 配置文件

默认配置文件位于 `config/app.yaml`，启动 CLI/API 时可以通过 `--config` 指定。

### data 相关配置

```yaml
data:
	providers: ["mock"]
	mock_prices:
		000001.SZ: 10.0
		510300.SH: 3.5
	market_data_cache_dir: data/processed/market_data
	market_universe_snapshot_dir: data/market_universe/snapshots
```

- `providers`: 数据提供者列表，Phase 0 默认 `mock`。
- `mock_prices`: mock 模式下的示例价格。
- `market_data_cache_dir`: 行情缓存目录。
- `market_universe_snapshot_dir`: 候选池快照目录。

### 与回测 CLI 的关系

`cli/backtest.py` 会读取 `data.market_universe_snapshot_dir` 初始化 `SnapshotService`，
用于离线回测加载候选池与行情快照。

