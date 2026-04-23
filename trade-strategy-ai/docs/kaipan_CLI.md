# KaipanScheduler CLI 使用说明

> 本文档描述 `kaipan_scheduler.py` 的使用方法，用于调度 kaipan 开盘啦数据的抓取和快照转换。

---

## 基础用法

```bash
python -m src.providers.kaipan_scheduler <command> [options]
```

---

## 命令一览

| 命令 | 说明 |
|------|------|
| `fetch` | 抓取指定日期和时间槽的数据（raw → snapshot 全流程） |
| `normalize` | 仅执行 raw → snapshot 转换 |
| `status` | 查看最近一次抓取的状态 |
| `run` | 启动自动调度（APScheduler，后台运行） |

---

## fetch

抓取指定日期和时间槽的原始数据，完成后自动转换为快照。

### 命令

```bash
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 09-25
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 17-30
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot all
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 交易日期，格式 `YYYY-MM-DD` | 当天 |
| `--slot` | 时间槽：`09-25`（盘前）、`17-30`（盘后）、`all`（两者都跑） | `all` |

### 数据集分配

| 时间槽 | 接口数 | 说明 |
|--------|--------|------|
| `09-25`（盘前） | 12 个 | 含竞价数据（竞价总体信息、竞价数量统计、竞价列表），无龙虎榜 |
| `17-30`（盘后） | 10 个 | 含龙虎榜列表，无竞价数据 |

### 输出示例

```
[fetch] 开始抓取 2026-04-22 09-25，共 12 个接口
[fetch] [1/12] fetch_board_strength 成功
[fetch] [2/12] fetch_industry_ranking 成功
...
[fetch] normalize 完成，结果: {'09-25': {...}, '17-30': {...}}
```

---

## normalize

仅执行 raw → snapshot 转换，不重新抓取数据。适用于已抓取 raw 数据后需要重新转换的场景。

### 命令

```bash
python -m src.providers.kaipan_scheduler normalize --date 2026-04-22 --slot 09-25
python -m src.providers.kaipan_scheduler normalize --date 2026-04-22 --slot 17-30
python -m src.providers.kaipan_scheduler normalize --date 2026-04-22 --slot all
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 交易日期，格式 `YYYY-MM-DD` | 当天 |
| `--slot` | 时间槽：`09-25`、`17-30`、`all` | `all` |

### 输出示例

```
normalize 2026-04-22 09-25: 4 ok, 0 failed
normalize 2026-04-22 17-30: 4 ok, 0 failed
```

---

## status

查看最近一次抓取的时间槽信息。

### 命令

```bash
python -m src.providers.kaipan_scheduler status
```

### 输出示例

```
# 有数据时
status: latest slot 2026-04-22_09-25

# 无数据时
status: no data yet
```

---

## run

启动后台自动调度，在每个交易日自动执行抓取和转换。进程会持续运行，直到收到中断信号（`Ctrl+C` 或 `SIGTERM`）。

### 命令

```bash
python -m src.providers.kaipan_scheduler run
```

### 行为

1. 通过 `akshare.trade_cal()` 判断今天是否为 A 股交易日
2. 非交易日 → 跳过并退出
3. 是交易日 → 注册 APScheduler Job：
   - `09:25` — 盘前抓取（12 个接口）
   - `17:30` — 盘后抓取（10 个接口）
4. 持续运行，等待信号关闭

### 退出

```bash
# Ctrl+C 或 kill
SIGINT/SIGTERM → 优雅关闭调度器
```

---

## 配置依赖

CLI 从 `config/app.yaml` 的 `kaipan` 配置节读取参数：

```yaml
kaipan:
  data_dir: data/kaipan            # 数据存储根目录
  schema_dir: src/providers/kaipan_schema  # YAML schema 目录
  auth:
    device_id: "your_device_id"   # 从 kaipan App 获取，必填
  fetch_schedule:
    pre_market: "9:25"             # 盘前抓取时间
    post_close: "17:30"            # 盘后抓取时间
```

---

## 目录结构

抓取后的数据按以下结构存储：

```
data/kaipan/
  raw/
    {dataset}/
      {trade_date}_{slot}/
        {api_name}.json            # 原始响应，内嵌 meta
  snapshots/
    {dataset}/
      {trade_date}_{slot}/
        {dataset}.json             # 标准化快照
```

示例：

```
data/kaipan/raw/hot_topics/2026-04-22_09-25/RealRankingInfo_ZSType7.json
data/kaipan/snapshots/hot_topics/2026-04-22_09-25/hot_topics.json
```

---

## 注意事项

1. **首次使用需填写 `device_id`**：在 `config/app.yaml` 的 `kaipan.auth.device_id` 中填入从 kaipan App 获取的设备 ID
2. **非交易自动跳过**：`run` 命令在非交易日会自动退出，不会报错
3. **接口失败不影响其余**：`fetch` 命令中单个接口失败会打印警告，继续执行其余接口
4. **日志输出**：`run` 命令使用 `logging.basicConfig`，默认输出到 stderr
