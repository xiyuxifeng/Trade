# Web 使用说明

> 适用范围：`trade-strategy-ai` 当前已完成的 Web 管理后台。
>
> 目标：让第一次接触项目的人可以按本文顺序完成 API 启动、Web 启动、登录、主流程浏览，以及常见的敏感配置和高风险操作检查。

---

## 1. 你会用到什么

- 后端 API：`api/main.py`
- Web 前端：`web/`
- 任务状态与产物：Job Center、报表、快照、策略版本、告警、市场数据
- 主手册：[`docs/UserManual.md`](UserManual.md)
- 覆盖矩阵：[`docs/Web-UserManual-Coverage.md`](Web-UserManual-Coverage.md)

如果你只想先跑通最小闭环，建议顺序是：

1. 启动数据库。
2. 启动 API。
3. 启动 Web。
4. 打开 `Overview`、`Jobs`、`Workflows`、`Reports`、`Settings`、`Ops`。

---

## 2. 启动前准备

### 2.1 数据库

Web 管理后台依赖 PostgreSQL。先确保数据库可连接，再启动 API 和 Web。

常见方式：

```bash
brew services start postgresql@15
```

或者使用你自己的数据库实例，并把 `DATABASE_URL` 配好。

### 2.2 必要配置

至少准备这些环境变量或配置项：

- `DATABASE_URL`：数据库连接串
- `TGB_COOKIE`：抓取相关 Cookie
- `config/app.yaml`：项目主配置

注意：

- `config/app.yaml` 中的敏感值应该通过环境变量注入，不要直接把真实密钥写进仓库。
- Web 的设置页会对敏感配置做脱敏展示，但保存时仍会把真实值交回服务端校验与存储。

---

## 3. 启动 API

API 是 Web 的后端入口。先启动它，再启动前端。

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后可以先检查：

```bash
curl http://localhost:8000/health
```

常用入口：

- 文档页：`http://localhost:8000/docs`
- 健康检查：`GET /health`
- Web UI BFF：`/api/ui/v1/*`

### 3.1 鉴权说明

Web 侧会读取 `X-API-Key`。

- 如果你使用了 API key，先在浏览器里登录对应 key。
- 如果没有配置鉴权，部分本地页面仍可访问，但不要把这种状态当成生产配置。
- 受保护页面和高风险操作应该以服务端鉴权结果为准。

---

## 4. 启动 Web

在 `web/` 目录启动前端。

```bash
cd web
pnpm install
pnpm dev
```

如果你本机没有 `pnpm`，先启用 corepack。

```bash
corepack enable
corepack pnpm install
```

启动后通常访问：

- `http://localhost:5173`

---

## 5. 主流程怎么走

### 5.1 先看总览

打开 `Overview` 页面，先确认这三块：

- 系统状态
- 最近任务
- 最近产物

如果这里就报错，先修环境，不要继续往后跑主流程。

### 5.2 看任务

进入 `Jobs` 页面后，通常按这个顺序看：

1. 任务类型
2. 状态
3. 参数快照
4. 日志
5. 产物引用

适合检查：

- 任务有没有被正确创建
- 失败时错误信息是否清晰
- 产物是否落盘

### 5.3 看工作流

进入 `Workflows` 页面，确认常用流程是否可选：

- 初始化
- 抓取
- 盘前/盘后
- 回测
- 优化
- 规则池

这里的重点不是“页面能不能打开”，而是“参数表单和任务入口是不是和用户手册一致”。

### 5.4 看报表

进入 `Reports` 页面，检查：

- 盘前日报
- 盘后考核
- HTML 预览
- JSON 详情

空列表时要能明确提示，没有数据时不要误以为是页面坏了。

### 5.5 看设置

进入 `Settings` 页面，重点确认：

- 配置项是否脱敏
- 保存前是否有校验
- 高风险项是否有二次确认
- 保存后是否保留回滚信息

如果你要修改 Cookie、密钥、数据库连接串，优先通过设置页或环境变量，不要直接手改不透明的配置文件。

### 5.6 看运维恢复中心

进入 `Ops` 页面，重点确认：

- 是否能列出项目级备份包
- 是否能创建新的项目快照
- 恢复前是否强制要求 admin 和显式确认
- 恢复后是否能看到审计与回滚提示

这里处理的是数据库、Job 元数据和 `data/processed` 目录，不是 `config/app.yaml` 的配置恢复。

如果你需要恢复配置文件本身，还是回到 `Settings` 页面。

---

## 6. 高风险操作

以下操作在 Web 上都应该先看摘要，再确认：

- 数据库迁移
- 备份
- 恢复
- 初始化项目
- 调度启停
- 批量规则审核

操作前建议你检查三件事：

1. 目标环境是不是对的。
2. 参数摘要是不是对的。
3. 是否已经生成备份或确认回滚方案。

如果页面没有给出确认弹窗、摘要或审计信息，不要继续执行。

---

## 7. 敏感配置

这些内容不要直接在仓库里明文保存：

- 数据库密码
- Cookie
- API key
- Webhook secret
- 其它密钥类配置

推荐做法：

1. 用环境变量注入。
2. 在 `config/app.yaml` 里使用占位引用。
3. 在 Web 设置页里只看脱敏值。

如果你发现页面把敏感值直接完整显示出来，先停止使用，属于安全问题。

---

## 8. 常见问题

### 8.1 页面一直转圈

先看 API 是否启动：

```bash
curl http://localhost:8000/health
```

然后检查浏览器里 `X-API-Key` 是否正确。

### 8.2 没有数据

先确认：

- 数据库里有没有初始化数据
- Job 是否已经跑过
- 报表或产物是否已生成
- 当前日期是否和数据日期一致

### 8.3 任务失败

优先看：

- Job 详情
- Job 日志
- 相关产物路径
- 后端错误信息

---

## 9. 建议的起步顺序

1. `Overview`
2. `Jobs`
3. `Workflows`
4. `Reports`
5. `Settings`
6. `Snapshots`
7. `Strategies`
8. `Ops`

如果你只想先验证主流程，至少完成前 5 项。
