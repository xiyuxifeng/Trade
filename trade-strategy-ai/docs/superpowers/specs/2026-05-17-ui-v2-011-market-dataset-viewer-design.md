# UI-V2-011 Market Dataset Viewer Design

## 背景

当前 `/market` 已经作为 `Market Snapshot Browser` 正式收口，负责查看单个 snapshot 的结构、质量报告、sections 和 regime features。

`UI-V2-011` 的目标不是再扩展 snapshot browser，而是提供一个**独立的 Market Dataset Viewer**，用于查看数据库中的市场数据集摘要、分页样本和质量信息，支撑外部系统接入前的人工验证。

这个页面必须保持 `UI-V2-002` 的浅色正式工作台风格，不引入第二套视觉语言，也不把页面做成 demo 式复合控制台。

## 目标

1. 提供独立页面 `/market/datasets`。
2. 让用户能按 `dataset_id / trade_date / symbol / section / market / dataset_type / quality_status` 查询数据集。
3. 支持查看 dataset metadata、分页 sample rows、data quality summary。
4. 支持从 dataset 回跳到对应 snapshot detail。
5. 在后端支持的前提下，提供导出 artifact 下载入口。
6. 所有查询必须走 API，不允许前端直接读文件或拼 SQL。
7. 页面状态必须完整覆盖 loading、empty、pagination loading、permission denied、dataset missing、API unavailable、invalid query。

## 非目标

1. 不改造 `/market` snapshot browser 的主职责。
2. 不把 dataset viewer 做成 second snapshot browser。
3. 不直接读取本地文件。
4. 不在前端拼接 SQL。
5. 不一次性加载超大数据集。
6. 不绕过 API pagination。
7. 不新增 CLI surface。

## 路由与信息架构

### Canonical 路由

- `/market`
  - 继续作为 `Market Snapshot Browser`
- `/market/datasets`
  - 新增为 `Market Dataset Viewer`

### 入口关系

- `/market` 页面顶部提供一个明显但不抢主任务的 `Dataset Viewer` 跳转入口。
- `/market/datasets` 页面顶部提供返回 `/market` 的跳转入口。
- 不新增并行正式入口。
- legacy 入口如果存在，只能保持兼容层，不得成为新的正式工作台。

## 页面结构

### 顶部

- `PageHeader`
- 标题：`Market Dataset Viewer`
- 副标题：说明该页用于查看 DB 中市场数据集摘要和样本，而不是查看 snapshot 结构
- 右上角提供返回 `Market Snapshot Browser` 的入口

### 筛选区

筛选条件采用浅色卡片区，保持 `UI-V2-002` 的视觉节奏。支持：

- `dataset_id`
- `trade_date`
- `symbol`
- `section`
- `market`
- `dataset_type`
- `quality_status`

筛选区需要支持：

- 按输入即更新 URL
- 可一键重置
- 无效查询参数时显示结构化错误提示

### 主体布局

推荐使用列表 + 右侧详情的工作台布局：

- 左侧：dataset 列表
- 右侧：dataset 详情

这种结构可以保持上下文，避免用户在多个页面间反复跳转。

### 左侧列表

列表至少展示：

- `dataset_id`
- `trade_date`
- `market`
- `dataset_type`
- `quality_status`
- `created_at`
- `snapshot_id`

列表支持：

- 选中态高亮
- 加载态
- 空态
- 分页翻页时的局部 loading
- 点击项后刷新右侧详情

### 右侧详情

详情区至少展示：

- dataset metadata
- quality summary
- 分页 sample rows
- snapshot 回链
- 如后端支持，导出 artifact 下载入口

详情区必须保证：

- sample rows 通过分页加载
- 不因高 volume 数据集而一次性全量渲染
- 能明确区分 `dataset missing` 与 `permission denied`

## 数据流

页面只通过现有 API Client 获取数据：

- 列表：`GET /api/ui/v1/market/datasets`
- 详情：`GET /api/ui/v1/market/datasets/{dataset_id}`
- 如需要，后续可复用现有 snapshot detail API 来展示回链信息

前端状态管理原则：

- 列表查询与详情查询分离
- 列表选中项变化时，只刷新目标详情
- 分页变化时只刷新 sample rows，不重刷整个页面
- 所有请求都走统一 API Client，不直接 fetch

## 状态设计

### Loading

- 首次进入页面时，列表和详情都需要清晰 loading。
- 右侧详情如果还未选中任何 dataset，显示引导式 empty state。

### Empty

- 无匹配 dataset 时，左侧列表显示空态。
- 右侧详情保持引导提示，不应呈现误导性的旧数据。

### Pagination Loading

- sample rows 翻页时，详情区只展示局部加载状态。
- 不应让整个页面闪烁重置。

### Permission Denied

- 对 API 返回的权限错误显示明确结构化提示。
- 提供返回 /market 的路径或重试建议。

### Dataset Missing

- dataset 不存在时给出明确说明。
- 不应把 missing 伪装成 empty data。

### API Unavailable

- 网络或后端不可用时显示统一错误态。
- 提供 retry。

### Invalid Query

- 非法 `dataset_id`、分页参数或筛选参数需要给出可读的查询错误。

## 视觉与交互要求

- 保持 `UI-V2-002` 的浅色卡片、边框、留白和中等信息密度。
- 只使用项目现有组件风格，不引入新的视觉体系。
- 可点击区域必须有清晰 hover 和 cursor feedback。
- 页面应优先让用户完成“查找 dataset -> 看摘要 -> 看样本 -> 回到 snapshot”的最短路径。
- 不把质量指标、样本表和回链拆成过多层级页面。

## API Contract 对齐

前端实现必须对齐现有 market API 的 contract：

- `MarketDatasetListResponse`
- `MarketDatasetDetailResponse`
- `MarketSnapshotDetailResponse`
- `MarketSnapshotQualityResponse`

前端类型需要同步补齐或校正：

- dataset metadata
- sample row pagination
- quality summary
- snapshot 回链字段
- 导出 artifact 相关字段（如果后端已提供）

## 测试策略

### 前端测试

至少覆盖：

- 默认进入 `/market/datasets`
- 按筛选条件查询列表
- dataset 选中后展示详情
- sample rows 分页
- 空态
- 权限不足
- dataset missing
- API unavailable
- invalid query

### 路由测试

- `/market/datasets` 必须是 canonical 路由
- `/market` 与 `/market/datasets` 之间跳转可用

### Contract 测试

- API Client 参数映射正确
- response 类型与后端返回一致

## 验收标准

1. 用户可以通过 Web 查询 DB 中的市场数据集。
2. 页面可以展示 dataset metadata。
3. 页面可以分页查看 sample rows。
4. 页面可以展示 data quality summary。
5. 页面可以回跳到 snapshot detail。
6. 大数据集不会一次性全量加载。
7. 页面不暴露服务器绝对路径。
8. 页面状态完整覆盖 loading、empty、pagination loading、permission denied、dataset missing、API unavailable、invalid query。
9. UI 风格与 `UI-V2-002` 一致。

## 建议实现边界

- 页面入口：`web/src/pages/market/datasets/index.tsx`
- 页面组件：`web/src/features/market-datasets/*`
- API Client：`web/src/lib/api/market.ts`
- 类型：`web/src/types/market.ts`
- 路由：`web/src/app/router.tsx`、`web/src/app/route-registry.ts`、`web/src/app/navigation.ts`

## 备注

- `UI-V2-010` 继续专注 snapshot browser。
- `UI-V2-011` 只负责 dataset viewer。
- 两者共享 market API，但不共享页面职责。
