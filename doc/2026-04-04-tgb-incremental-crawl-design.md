# 淘股吧增量抓取与去重设计（2026-04-04）

## 1. 目标

为淘股吧作者 `javxsp` 建立第一版真实可用的数据抓取链路，满足以下目标：

- 支持登录后访问的文章列表、文章正文、评论抓取
- 支持按作者进行增量抓取
- 支持 `source_url` + `content_hash` 双层去重
- 支持评论清洗、作者/读者分类
- 第一版使用手工提供的 Cookie
- 为后续自动登录、浏览器回退抓取预留接口

本阶段优先验证真实数据链路，不在第一版实现自动登录、代理池、大规模并发抓取。

## 2. 范围

### 2.1 第一版交付

- 淘股吧单站点抓取器
- 单作者配置化抓取
- 配置化 Cookie 认证
- 低频反爬策略
- 增量抓取状态持久化
- 文章正文与评论落盘为 JSONL
- 评论清洗与无效评论标记
- 评论作者身份标记：作者本人 / 读者

### 2.2 暂不实现

- 自动登录
- Cookie 自动续期
- 代理池
- 高并发抓取
- 多站点统一适配层的完整抽象
- 楼中楼评论恢复为树结构展示

## 3. 核心设计决策

### 3.1 抓取方式

第一版采用 `requests + 手工 Cookie + HTML/接口解析`。

原因：

- 能最快验证真实数据链路
- 把复杂度集中在“增量、去重、清洗、结构化”
- 避免在第一版就被自动登录和浏览器控制拖慢

后续预留 `AuthProvider` 和动态抓取回退接口，未来可接 `Playwright`。

### 3.2 认证方式

认证配置按域名管理，形态类似：

```yaml
crawl:
  auth:
    tgb.cn:
      mode: cookie
      cookie: "${TGB_COOKIE}"
```

第一版支持两种来源：

- 直接写入配置文件
- 通过环境变量注入

代码只依赖认证提供者接口，不把 Cookie 硬编码在抓取逻辑中。

### 3.3 增量策略

列表页按从新到旧抓取，遇到已见文章时尽快停止。

增量判断优先级：

1. `source_url` 已存在
2. `content_hash` 已存在
3. `published_at` 早于最近一次已确认的新文章边界

同时记录抓取状态到 `state.json`，包括：

- `last_seen_article_url`
- `last_seen_published_at`
- `last_success_crawled_at`
- `last_success_article_count`
- `failure_stats`

### 3.4 评论处理策略

第一版将评论对外视图拍平成普通列表，但保留可恢复楼层结构的字段。

每条评论建议字段：

- `comment_id`
- `parent_comment_id`
- `root_comment_id`
- `reply_to_user`
- `author_name`
- `is_author`
- `published_at`
- `raw_text`
- `clean_text`
- `is_filtered`
- `filter_reasons`
- `raw_html`
- `raw_payload`

这样后续需要恢复“楼中楼 / 回复某人”的关系时，可以直接基于现有字段重建。

### 3.5 评论清洗策略

第一版采用“标记过滤，不直接删除”的策略。

清洗规则：

- 去除表情符号和明显噪声字符
- 规范空白字符
- 标记低信息评论，例如“谢谢”“打卡”“感谢”“点赞”“666”
- 保留作者评论优先级
- 不丢弃原始文本，便于后续重新过滤

## 4. 反爬基线

第一版默认启用以下轻量反爬策略：

- 请求之间加入随机间隔
- 限制单次运行最大抓取页数、最大文章数、最大评论页数
- 使用稳定 Session 和正常浏览器请求头
- 对 `403`、`429`、未登录页、验证码页执行退避或终止
- 使用有限次指数退避重试
- 增量抓取时遇到已见文章及时停止翻页

第一版明确不做并发抓取。

## 5. 数据产物

### 5.1 落盘路径

```text
trade-strategy-ai/data/processed/crawl/tgb/javxsp/articles.jsonl
trade-strategy-ai/data/processed/crawl/tgb/javxsp/state.json
```

### 5.2 `articles.jsonl` 记录字段

- `source`
- `author_id`
- `author_name`
- `source_url`
- `source_article_id`
- `title`
- `published_at`
- `crawled_at`
- `content_text`
- `content_html`
- `content_hash`
- `comment_count`
- `comments`
- `raw_payload`

### 5.3 去重原则

- 主去重键：`source_url`
- 辅去重键：`content_hash`

如果文章正文不变但评论区新增，允许对文章进行轻量复抓并更新评论快照，不重复生成新的文章记录。

## 6. 代码边界

建议主要落点如下：

- `trade-strategy-ai/src/agents/data_agent/skills/crawl_blog.py`
  - 抓取主入口
  - 列表页/详情页/评论页调度
  - 增量与去重编排

- `trade-strategy-ai/src/agents/data_agent/skills/crawl_dynamic.py`
  - 后续预留 Playwright 自动登录或动态抓取回退

- `trade-strategy-ai/cli/crawl.py`
  - 手动触发抓取命令

- `trade-strategy-ai/config/app.yaml`
  - 认证、限频、站点源配置

## 7. 自动登录预留

后续扩展方向：

- 增加 `playwright_login` 认证模式
- 自动检测 Cookie 失效并刷新
- 在 `requests` 路径被反爬阻断时回退到浏览器态抓取

建议接口形态：

- `AuthProvider.get_session_headers()`
- `AuthProvider.is_authenticated(response)`
- `AuthProvider.refresh_auth()`

第一版仅实现 Cookie 认证版本。

## 8. 测试策略

第一版采用 TDD，优先覆盖：

- 增量状态判断
- 文章去重
- 评论清洗与无效评论标记
- 评论作者身份识别
- 评论结构字段保留
- 配置读取与 Cookie 注入

真实联网抓取不纳入单元测试，网络行为通过夹具样本和解析测试覆盖。

## 9. 风险

- 淘股吧页面结构或接口可能变化
- Cookie 可能失效
- 登录态请求可能仍触发限频或验证码
- 评论区结构可能存在多种展示形态，需要解析逻辑兼容

## 10. 实施顺序

1. 定义配置与数据结构
2. 实现评论清洗与去重逻辑
3. 实现状态文件与 JSONL 存储
4. 实现淘股吧列表页/详情页/评论页解析
5. 增加 CLI 入口
6. 用真实作者 `javxsp` 做一次手工验证
