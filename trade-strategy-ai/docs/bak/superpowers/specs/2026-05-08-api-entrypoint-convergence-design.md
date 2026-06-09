# 2026-05-08 API 入口收敛设计

> 注：这是一份迁移期设计记录。最终落地结果已经收敛为单一对外入口 `api/main.py`，`src/api/main.py` 已删除。下述内容保留为历史设计依据，不再作为当前运行时契约。

## 背景

在入口收敛前，仓库里同时存在两套 FastAPI 应用入口：

- [api/main.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/api/main.py)
- [src/api/main.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/api/main.py)

两者已经开始承担不同职责，并且各自挂载了不同路由集合。继续让它们并行维护，会导致路由分叉、测试分叉、文档分叉和后续 Web BFF 分叉。

另外，仓库根目录下的 `src/` 目录里曾保留少量历史兼容代码，尤其是 `src/providers/kaipan_scheduler.py` 这一类命令入口。该重复 wrapper 已删除，当前只保留项目目录内的实现与历史文档。

## 目标

- 将 API 构建逻辑收敛到单一源码。
- 保留现有导入路径作为兼容层，避免一次性切断老测试和老脚本。
- 明确哪个入口是 canonical entrypoint，避免后续继续新增第二套应用定义。
- 为后续删除根目录 `src/` 中的遗留兼容代码预留出口，但不在本轮强制删除。

## 设计决策

### 1. 单一 app factory

新增一个共享的应用工厂模块，作为唯一的 FastAPI app 构建来源。

建议位置：

- [src/api/app.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/api/app.py)

这个模块负责：

- 创建 `FastAPI` 实例
- 挂载旧的 `api/routers/*`
- 挂载新的 `src/api/routes/*`
- 挂载 `src/api/routers/ui/*`
- 统一 CORS、lifespan、health 路由和 root 路由

### 2. 双入口兼容层

保留下面两个导入路径：

- [api/main.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/api/main.py)
- [src/api/main.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/api/main.py)

但它们都只做一件事：

- 从 `src/api/app.py` 导入同一个 `app`

这样可以避免外部调用方和测试在迁移期间失效，同时把“应用定义”收束到一个地方。

### 3. canonical entrypoint

本轮建议以 [api/main.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/api/main.py) 作为对外主入口。

原因：

- 现有测试和运行脚本已经更接近这个入口。
- 顶层 `api/` 路径更适合作为实际服务入口。
- `src/api/main.py` 更适合做兼容或过渡导入，不适合作为长期主入口。

### 4. 遗留 `src/` 目录处理原则

根目录 [src/](/Users/wanghui/Documents/Vibe/Trade/src) 已在本轮清理完成，重复兼容 wrapper 已删除，不再作为运行时目录使用。

处理原则是：

1. 先完成 API 入口收敛。
2. 再梳理 `docs/UserManual.md`、测试和脚本中对根目录 `src` 的引用。
3. 所有引用都迁移完后，再单独决定是删除、归档还是保留兼容壳。

## 业务边界

本设计不做以下事情：

- 不重写现有业务路由实现。
- 不删除 `src/api/main.py` 的兼容层。
- 不在本轮强制删除根目录 `src/`。
- 不调整 Job 白名单规则本身，白名单策略仍由 `src/services/job_registry.py` 负责。

## 验收标准

API 入口收敛完成后应满足：

- `api.main` 与 `src.api.main` 导入到同一个 app 构建结果。
- `/run/*`、`/reports/*`、`/api/ui/v1/jobs/*` 等关键路径都可在同一个应用中访问。
- 新增路由只需要改一个 app factory，不再需要同步改两份入口定义。
- 文档能明确说明 canonical entrypoint、兼容层和后续清理边界。

## 风险

- 如果直接删除 `src/api/main.py`，可能会破坏仍在使用该导入路径的测试和脚本。
- 如果不先收敛 app factory，后续 UI 路由和旧业务路由仍会继续分叉。
- 如果在文档和脚本迁移完成前删除兼容入口，会影响 `src.providers.kaipan_scheduler` 这一类历史命令入口。

## 结论

本次收敛的正确做法不是“直接删文件”，而是先建立单一 app factory，再让两个入口共同依赖它。根目录 `src/` 作为遗留兼容层，先保留，后清理。
