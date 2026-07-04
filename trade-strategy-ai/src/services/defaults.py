from __future__ import annotations

"""服务层共享的默认模板与常量。"""

DEFAULT_CONFIG_YAML = """## trade-strategy-ai 配置文件（YAML）
## - 配置加载支持环境变量展开：例如 "${TGB_COOKIE}"
## - 建议不要把 Cookie/API Key 明文写入仓库，优先用环境变量注入

# 数据库（推荐：本机安装 PostgreSQL；Docker 仅作为可选方案）
database:
  # SQLAlchemy Async URL（示例：postgresql+asyncpg://user:pass@localhost:5432/trade_strategy_ai）
  # 若不填写（null），则使用 .env / 环境变量中的 DATABASE_URL（或 Settings 默认值）。
  url: null
  echo: false
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 1800

# 时区（影响调度时间解析）
timezone: Asia/Shanghai

# 运行模式：interactive（手动/本地验证） / service（长期运行服务，后续可扩展）
run_mode: interactive

schedule:
  # 是否启用定时调度（Phase 0 默认 false，仅手动跑）
  enable: false
  # 盘前时间（HH:MM，按 timezone 解释）
  pre_market_time: "08:30"
  # 盘后时间（HH:MM，按 timezone 解释）
  after_close_time: "15:30"

evaluation:
  # 收益率不达标阈值（如 0.01 表示 1%）
  min_expected_return: 0.0
  # 是否“亏损即触发复盘”
  loss_trigger: true

data:
  # 数据提供者列表：交付默认建议使用 akshare，便于直接跑真实行情链路
  providers: ["akshare"]
  # 候选池快照目录，用于市场快照/盘前/回测相关流程
  market_universe_snapshot_dir: data/market_universe/snapshots

crawl:
  # 站点认证信息（按域名/站点名分组）
  auth: {}
  # 示例（淘股吧，建议通过环境变量注入 Cookie）：
  # auth:
  #   tgb.cn:
  #     mode: cookie
  #     cookie: "${TGB_COOKIE}"

  throttling:
    # 每次请求之间的随机间隔区间（秒）
    min_interval_seconds: 1.0
    max_interval_seconds: 2.0
    # 失败时退避序列（秒），按序重试
    backoff_seconds: [5, 15, 30]

  # 抓取来源列表（支持同站点多作者增量抓取）
  sources: []
  # 示例（建议把 trader_id 绑定到 traders[].trader_id，便于后续聚类/路由）：
  # sources:
  #   - source: tgb
  #     site: tgb.cn
  #     trader_id: trader_a
  #     author_id: "10461311"
  #     author_name: "某交易员"
  #     list_url: "https://www.tgb.cn/xxxxx"
  #     enabled: true

runtime:
  # 输出目录（日报、persona_route 等产物默认写到这里）
  output_dir: data/processed/phase0

llm:
  # 大模型提供商（预留）：openai/anthropic/...
  provider: null
  # 模型名（随 provider 而定）
  model: null
  # 第三方大模型 API Base URL（可选）
  url: null
  # 大模型 API Key（建议通过环境变量注入）
  api_key: null

# 盘前正式主链路开关：交付默认开启盘前候选池快照流程
pre_market_formal_flow:
  # 是否启用盘前正式主链路
  enabled: true
  # 候选池快照时段
  market_universe_slot: "09-25"

traders:
  - trader_id: trader_a
    # 展示名（用于报告展示）
    display_name: Trader A
    article_sources:
      urls: []
      rss: []
      site_type: null
      crawl_frequency_minutes: null
    trade_log_sources:
      csv_paths: []
    # 默认止盈/止损
    default_target_pct: 0.05
    default_stop_pct: 0.03

# API 服务配置
api:
  host: "0.0.0.0"
  port: 8000
  timeout_seconds: 300  # 5分钟，0 表示不限制
  auth:
    enabled: true
    api_keys:
      - key: trade-strategy-ai-local-viewer
        role: viewer
        label: Local Viewer
      - key: trade-strategy-ai-local-operator
        role: operator
        label: Local Operator
      - key: trade-strategy-ai-local-admin
        role: admin
        label: Local Admin

# Kaipan 开盘啦私有接口配置
kaipan:
  # 数据存储根目录
  data_dir: data/kaipan
  # Schema 文件目录
  schema_dir: src/providers/kaipan_schema
  # 可选鉴权参数（建议通过环境变量注入）
  token: null
  user_id: null
  # 默认请求头，模拟 Android 客户端
  default_headers:
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    User-Agent: Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)
    Connection: Keep-Alive
    Accept-Encoding: gzip
  # 抓取时间表（可配置）
  fetch_schedule:
    pre_market: "9:25"    # 盘前
    post_close: "17:30"   # 盘后
  # 交易日历来源
  trading_calendar:
    source: akshare
  # 简单反爬与重试策略
  min_request_interval_seconds: 3.0
  max_retries: 3
  retry_backoff_seconds: [1.0, 2.0, 4.0]
  retry_status_codes: [403, 429, 500, 502, 503, 504]
"""
