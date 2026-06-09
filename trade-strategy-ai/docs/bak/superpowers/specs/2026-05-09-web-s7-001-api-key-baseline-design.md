# WEB-S7-001 API Key Baseline Design

## 背景

当前 Web 管理后台已经有统一的 `/api/ui/v1` BFF 路由，也已经在多个 UI 路由上挂了 `verify_api_key`。问题在于，这套保护仍然是分散的、默认偏宽松的：当 `api.auth.enabled=true` 但 `api_keys` 为空时，现有实现会退化为匿名放行，前端也在多个 API 模块里手工拼接 `X-API-Key`。

`WEB-S7-001` 的目标不是引入完整登录系统，而是把现有 API Key 机制收口成一个稳定、可配置、可测试的 UI API 鉴权基线，保证：

1. UI API 可以显式启用或关闭鉴权。
2. 开启鉴权时，未授权请求必须统一拒绝。
3. 前端 API client 统一注入 API Key，不再分散实现。
4. 本地开发关闭鉴权必须是显式配置，而不是默认“空配置放行”。

## 目标

- 统一 UI API 的鉴权入口和错误语义。
- 保留 API Key 方案作为当前阶段的唯一鉴权方式。
- 让前端所有 UI BFF 请求都走统一的 API client 注入逻辑。
- 补齐授权和未授权场景的测试。

## 非目标

- 不实现用户名密码登录。
- 不实现 session、cookie 登录态、刷新令牌或 CSRF 体系。
- 不做角色权限模型，`WEB-S7-008` 之后再处理。
- 不修改业务 API 语义，只收口鉴权行为。

## 当前行为

- 服务端已经存在 `api.auth.enabled` 和 `api.auth.api_keys` 配置。
- `api/dependencies.py` 中的 `verify_api_key` 已能读取 `X-API-Key`。
- 多个 `api/routers/ui/*` 路由已经显式依赖 `verify_api_key`。
- 前端 `web/src/lib/api/http.ts` 已能自动从 `localStorage` 读取 `X-API-Key`。
- 但部分前端 API 模块仍在重复实现相同的 header 拼装逻辑。
- 当鉴权启用但未配置任何 key 时，当前实现会回退为匿名放行，这与“启用鉴权”的直觉不一致。

## 设计方案

### 服务端

1. 保留 `api.auth.enabled` 作为总开关。
2. 当 `api.auth.enabled=false` 时，UI API 保持匿名可访问，便于本地开发和离线调试。
3. 当 `api.auth.enabled=true` 时：
   - `X-API-Key` 必须匹配 `api.auth.api_keys` 中的某个值。
   - 若 `api_keys` 为空，鉴权仍视为开启，但所有请求都应被拒绝，并返回统一的 403。
4. 鉴权失败必须返回稳定、可识别的错误 payload，方便前端显示“请配置 API Key”或“凭证无效”。
5. 所有 UI 路由继续使用同一鉴权依赖，不在每个路由里重复实现校验逻辑。

### 前端

1. 将 API Key 读取和 header 注入集中到 `web/src/lib/api/http.ts`。
2. `fetchJson` 继续作为默认 JSON 请求入口。
3. 文件上传、二进制下载等特殊请求，也要通过统一的 `API_KEY_STORAGE_KEY` 读取逻辑，不再在每个模块里手工复制。
4. 对于未授权或 key 失效，前端可以识别 403 并给出明确错误信息，但不在这一步引入复杂登录 UI。

## 关键接口

### 后端鉴权依赖

- 文件：`api/dependencies.py`
- 职责：读取应用配置，判断 UI API 鉴权是否启用，校验 `X-API-Key`，返回统一错误。

### 前端统一 client

- 文件：`web/src/lib/api/http.ts`
- 职责：从 `localStorage` 读取 `trade-strategy-ai.apiKey`，统一注入 `X-API-Key`，并将错误转换成可识别的 `ApiError`。

### 特殊请求

- 文件：`web/src/lib/api/imports.ts`
- 文件：`web/src/lib/api/backtests.ts`
- 文件：`web/src/lib/api/artifacts.ts`
- 文件：`web/src/lib/api/alerts.ts`

这些模块中凡是还在手工拼 header 的地方，都应改为复用统一 client 或统一 helper，避免行为分叉。

## 错误处理

- 未开启鉴权时，不返回认证错误。
- 开启鉴权但缺少或错误的 `X-API-Key` 时，返回 403。
- 前端请求失败时，优先使用后端返回的 JSON `detail/message`，其次再退回 HTTP 状态文本。
- 不记录明文 API key 到日志。

## 测试策略

### 服务端测试

- 验证 `api.auth.enabled=false` 时 UI API 可匿名访问。
- 验证 `api.auth.enabled=true` 且 key 正确时请求成功。
- 验证 `api.auth.enabled=true` 且 key 缺失或错误时请求被拒绝。
- 验证 `api.auth.enabled=true` 但 `api_keys` 为空时不会误放行。

### 前端测试

- 验证 `fetchJson` 会自动附带 `X-API-Key`。
- 验证文件上传和二进制下载仍会带上 `X-API-Key`。
- 验证 API key 不存在时不会错误注入 header。

## 风险与约束

- 这次只做 API Key 基线，不引入 session 和登录 UI，避免范围膨胀。
- 现有前端模块分散使用 fetch，需要逐步统一，但必须保持现有行为不回退。
- 鉴权默认值不能因为便利性而继续“空 key 放行”，否则 `enabled=true` 没有实际意义。

## 验收标准

- UI API 在启用鉴权时会拦截未授权请求。
- UI API 在关闭鉴权时允许本地匿名调试。
- 前端所有 UI API 请求都通过统一 API client 注入 key。
- `api_keys` 为空时不会被当作有效授权。
- 相关测试通过。
