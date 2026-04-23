# KaipanScheduler 调度层设计

> 日期：2026-04-22
> 状态：已确认

---

## 1. 功能定位

调度层，统一管理"手动触发"和"自动调度"两条路径。处于抓取层（KaipanProvider）和转换层（KaipanNormalizer）之上，不承担业务逻辑。

---

## 2. 架构位置

```
KaipanScheduler（调度层）
    ├── KaipanProvider（抓取层）
    └── KaipanNormalizer（转换层）
```

三层各司其职：
- **KaipanProvider**：发起 HTTP 请求，写 raw JSON，内嵌 meta，不做数据转换
- **KaipanNormalizer**：读取 YAML 映射文件，执行字段转换，输出 snapshots JSON
- **KaipanScheduler**：CLI 入口 + APScheduler 定时调度，协调 provider 和 normalizer

---

## 3. CLI 接口

### 3.1 命令设计（纯命令式）

```bash
# 抓取
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 09-25
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 17-30
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot all

# 转换
python -m src.providers.kaipan_scheduler normalize --date 2026-04-22 --slot 09-25
python -m src.providers.kaipan_scheduler normalize --date 2026-04-22 --slot all

# 启动自动调度
python -m src.providers.kaipan_scheduler run

# 查看状态（最近一次抓取时间、结果）
python -m src.providers.kaipan_scheduler status
```

### 3.2 参数说明

| 参数 | 说明 |
|------|------|
| `--date` | 交易日期，格式 `YYYY-MM-DD`，默认当天 |
| `--slot` | 时间槽，`09-25`（盘前）、`17-30`（盘后）、`all`（两者都跑） |

---

## 4. 数据集分配

按设计文档（2026-04-20-kaipan-data-pipeline-design.md）6.3 节：

| 时间 | 抓取数据集 |
|------|-----------|
| 9:25（盘前） | 竞价总体信息、竞价数量统计、竞价列表、涨停信息、涨停原因、板块强度、行业涨幅、最强风口、区间统计-按股票/板块、题材详情、股票所属板块 V2 |
| 17:30（盘后） | 涨停信息、涨停原因、板块强度、行业涨幅、龙虎榜列表、最强风口、区间统计-按股票/板块、题材详情、股票所属板块 V2 |

**注意**：
- 9:25 有**竞价数据**，无**龙虎榜**
- 17:30 有**龙虎榜列表**，无竞价数据

---

## 5. 自动调度逻辑

### 5.1 APScheduler 配置

- 每个交易日 `9:25` 触发盘前抓取 + 转换
- 每个交易日 `17:30` 触发盘后抓取 + 转换
- 使用 `akshare.trade_cal()` 判断是否为交易日，非交易自动跳过

### 5.2 异常处理

- 单个接口失败：记录日志，继续抓取其余接口
- 全部接口失败：记录错误，不写入 snapshot
- 网络超时：重试 1 次，仍失败则跳过

---

## 6. 核心流程

### 6.1 `fetch` 流程

```
1. 解析 date / slot 参数
2. 判断是否为交易日（非交易则跳过）
3. 构造 KaipanAuth（从配置读取 device_id）
4. 实例化 KaipanProvider
5. 按数据集分配表，依次调用对应 fetch 方法
6. 抓取完成后，调用 KaipanNormalizer.normalize_date() 转换
7. 输出汇总日志（成功/失败接口数）
```

### 6.2 `normalize` 流程（独立调用）

```
1. 解析 date / slot 参数
2. 实例化 KaipanNormalizer
3. 调用 normalize_date() 批量转换
4. 输出汇总日志（成功/失败 dataset 数）
```

### 6.3 `run` 流程

```
1. 读取配置文件中的 fetch_schedule
2. 注册 APScheduler Job（盘前 9:25，盘后 17:30）
3. 启动调度器，保持进程运行
4. 每触发一次，执行 fetch 流程
```

---

## 7. 配置依赖

复用 `config/app.yaml` 中已有的 `kaipan` 配置节：

```yaml
kaipan:
  data_dir: data/kaipan
  schema_dir: src/providers/kaipan_schema
  fetch_schedule:
    pre_market: "9:25"
    post_close: "17:30"
  trading_calendar:
    source: akshare
```

额外需要新增配置项：

```yaml
kaipan:
  auth:
    device_id: "your_device_id"  # 必填，从 kaipan App 获取
```

---

## 8. 文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 新增 | `src/providers/kaipan_scheduler.py` |

---

## 9. 验收标准

1. CLI 命令 `fetch --date YYYY-MM-DD --slot 09-25` 可成功抓取盘前数据到 raw 目录
2. CLI 命令 `normalize --date YYYY-MM-DD --slot 09-25` 可成功转换 raw → snapshot
3. `run` 命令启动后，调度器保持运行，按时触发抓取
4. 非交易日自动跳过，不报错
5. 任意接口失败不影响其余接口，日志记录清晰
6. `status` 命令可查看最近一次抓取状态
