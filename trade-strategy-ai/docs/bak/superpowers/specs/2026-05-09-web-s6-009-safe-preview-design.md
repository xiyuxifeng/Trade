# WEB-S6-009 Safe Preview Design

> 目标：为报表和通用产物提供统一的安全预览层，避免不可信 HTML / Markdown 在前端直接执行，同时收紧下载路径边界。

## 1. 设计目标

### 1.1 核心目标

- 提供一个共享的预览层，统一承接 `reports` 和 `artifacts` 两类页面的内容展示。
- HTML 预览必须隔离脚本执行，避免把外部或 LLM 生成内容当作可信页面直接渲染。
- Markdown 预览必须走安全解析，不把原始 HTML 注入到 DOM 中执行。
- 下载接口必须限制在允许的产物目录内，防止越权读取文件系统上的其他路径。
- 保持现有 UI 风格一致，采用数据密集型工作台的高密度布局，不额外引入新的页面结构复杂度。

### 1.2 设计边界

- 不在本任务中引入完整 Markdown 富文本引擎，也不做 WYSIWYG 编辑。
- 不新增独立的安全预览页面，沿用现有 `Reports` 和 `Artifacts` 页面。
- 不把服务端安全策略扩展成复杂的通用内容沙箱；本任务只覆盖当前报表和主要产物预览场景。
- 不改变报表列表、产物列表和详情抽屉的业务语义，只替换预览实现和下载校验。

## 2. 功能范围

### 2.1 必须支持

- 共享安全预览组件
- HTML 预览 sandbox 隔离
- Markdown 安全渲染
- 纯文本 / JSON / 其他文本类内容的只读展示
- 下载路径允许目录校验
- 相关测试覆盖

### 2.2 暂不支持

- 复杂 Markdown 语法全集
- 富文本交互编辑
- 远程资源代理或内容重写
- 服务端 CSP 策略统一配置

## 3. 架构设计

### 3.1 共享预览层

新增共享组件目录：

- `web/src/components/artifacts/`

核心组件：

- `web/src/components/artifacts/artifact-preview.tsx`

职责划分：

- `ArtifactPreview`：对外统一入口，根据 `kind` 决定渲染方式。
- `HtmlPreviewFrame`：封装 `iframe`，固定使用 `sandbox`。
- `MarkdownPreview`：把 Markdown 解析为受限结构，再映射为 React 节点。
- `RawPreview`：渲染纯文本类内容，不做 HTML 解释。

### 3.2 页面接入方式

两个页面只负责传参，不再自己拼接预览逻辑：

- `web/src/features/reports/report-center.tsx`
- `web/src/pages/artifacts/index.tsx`

页面只决定：

- 当前选中的对象
- 当前选中的预览内容
- 载入状态与错误状态

预览实现本身统一交给 `ArtifactPreview`。

### 3.3 后端下载校验

在 `src/services/artifact_service.py` 中增加允许目录判断：

- 根据候选根目录判断某个路径是否属于允许索引范围
- 下载前先校验路径是否在允许根目录内
- 不通过时返回 404，避免泄露文件系统结构

`api/routers/ui/artifacts.py` 只负责调用服务层校验，不再自己拼文件系统规则。

## 4. 渲染策略

### 4.1 HTML

HTML 内容只能以 `iframe` 方式展示，且必须包含：

- `sandbox="allow-same-origin"`
- 固定标题
- 只读预览，不注入到主页面 DOM

这样可以避免预览中的脚本直接执行到宿主页面上下文里。

### 4.2 Markdown

Markdown 使用一个轻量级的受限解析器处理，只支持：

- 标题
- 段落
- 无序列表
- 引用
- 代码块
- 行内反引号代码

策略要求：

- 不使用会直接输出任意 HTML 的第三方渲染器
- 原始 HTML 标签按普通文本处理
- 脚本标签不会进入可执行 DOM

这套实现的目标不是“完整 Markdown 兼容”，而是“安全、可预测、足够可读”。

### 4.3 其他文本类内容

对于 JSON、YAML、CSV、文本等内容，直接在 `pre` 容器中只读展示。
如果内容为空，则显示空状态，不做额外推断。

## 5. 数据流

### 5.1 Reports

1. 页面加载日报 / 考核报告列表。
2. 用户选择某个日期。
3. 页面请求对应 HTML 或详情数据。
4. 预览内容传入 `ArtifactPreview`。
5. HTML 使用 sandbox iframe 展示，JSON 切换保留原有详情面板。

### 5.2 Artifacts

1. 页面加载产物列表。
2. 用户打开某个产物详情抽屉。
3. 页面请求产物详情。
4. `ArtifactPreview` 根据 `kind` 渲染对应安全视图。
5. 下载动作先经过服务层路径校验，再返回文件响应。

## 6. 安全策略

### 6.1 前端安全

- HTML 不直出到主页面 DOM
- Markdown 不使用 `dangerouslySetInnerHTML`
- 原始内容按文本处理，不做浏览器可执行拼接
- 预览容器保持只读

### 6.2 后端安全

- 下载前校验路径是否处于允许根目录
- 失败时统一返回 404
- 不把内部文件系统结构暴露给前端

## 7. 测试设计

### 7.1 前端测试

- 验证 HTML 预览存在 `sandbox`
- 验证 Markdown 中的 `<script>` 只作为文本呈现
- 验证 `reports` 和 `artifacts` 页面都复用同一预览组件

### 7.2 后端测试

- 验证 Artifact 下载接口可正常返回允许目录内文件
- 验证允许目录外的路径会被拒绝
- 验证服务层路径判断函数对合法 / 非法路径的结果正确

## 8. 验收标准

- `Reports` 页面和 `Artifacts` 页面都已接入共享预览层。
- HTML 预览使用 sandbox iframe。
- Markdown 不执行原始 HTML。
- 允许目录外的下载请求被拦截。
- 相关测试、`typecheck` 和 `lint` 全部通过。

## 9. 实际落地结果

本设计已在代码中完成实现，对应落地文件包括：

- `web/src/components/artifacts/artifact-preview.tsx`
- `web/src/features/reports/report-center.tsx`
- `web/src/pages/artifacts/index.tsx`
- `src/services/artifact_service.py`
- `api/routers/ui/artifacts.py`
- `tests/api/routers/test_artifacts.py`
- `tests/unit/services/test_artifact_service.py`

