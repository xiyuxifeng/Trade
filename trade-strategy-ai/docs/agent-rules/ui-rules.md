# UI Rules

## 1. UI 设计与实现规范

涉及 UI 创建或修改时：

- 优先使用 `skill:ui-ux-pro-max`
- 必须遵循 UI TaskList
- 必须确认 UI 与 API contract 对齐
- 必须覆盖基本状态

每个核心页面至少需要考虑：

- Loading State
- Error State
- Empty State
- Retry State
- Success State

---

## 2. UI TaskList

开始 UI 任务前，必须阅读：

```text
docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md
```

重点阅读：

- `## 0. 执行关系`
- `## 1. AI UI Implementation Rules`
- `## 2. UI 架构目标`

---

## 3. UI 与主 Task 的绑定

UI 不是孤立任务。

实现主 Task 时，必须同步检查相关 UI Task：

- 页面是否存在
- 状态是否完整
- API contract 是否对齐
- Loading/Error/Empty/Retry 是否覆盖
- 用户操作路径是否闭环
- 验收标准是否一致

---

## 4. Mock 数据约束

允许临时 mock，但必须满足：

- 明确标记 mock
- 不得冒充真实 API
- 必须创建收口任务
- 不得在 DONE 状态遗留未追踪 mock

---

## 5. UI 变更输出

完成 UI 修改后，输出应包含：

```md
## 修改页面 / 组件

## 对应 UI Task

## 对应主 Task

## API contract 对齐情况

## 状态覆盖
- Loading:
- Error:
- Empty:
- Retry:
- Success:

## 未完成 / 风险
```

---

## 6. 独立 UI 规则文件

如果存在：

```text
docs/standards/ui-implementation-rules.md
```

应优先阅读。

如果不存在，不要自动创建，除非：

- 用户明确要求
- 或 TaskList 明确要求
