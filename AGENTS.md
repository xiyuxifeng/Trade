# AGENTS.md

## 1. 当前阶段

`trade-strategy-ai` 已完成重构阶段，现在处于交付前手动测试、用户需求调整、问题修复和最终稳定阶段。

历史 Stage / Task / Gate 文档只作为事实追溯，不再作为新修改任务的执行规则。之后所有 AI/Codex 修改以本文件为准。

目标：

```text
正确完成用户需求
修复真实问题
删除无用旧路径和重复实现
保持代码单一路径、清晰、可测试、可交付
```

## 2. 最高原则

优先级固定为：

```text
用户明确需求和功能正确
> 数据与业务契约正确
> 单一路径、无重复实现、无旧兼容堆叠
> 可运行、可测试、可恢复
> 用户可理解、可交付
> 非关键视觉细节
```

用户在手动测试中明确提出的 UI、交互、流程、页面结构、信息层级或需求变化，只要影响用户理解、流程完成、交付质量、数据真实性或操作安全，就属于功能正确，不得降级为普通视觉优化。

不得为了减少改动而保留错误实现、重复实现、旧路径、局部绕过或隐藏风险。

## 3. 单一路径规则

本项目按新项目交付处理，不为旧 UI、旧 workflow、旧 route、旧 API 或旧内部工具保留长期兼容。

禁止新增或保留：

- 两套正式入口；
- 两套正式 API；
- 两套页面实现；
- 两套状态机；
- 两套写入路径；
- 两套 schema / DTO；
- 正常业务流程中的旧路径 fallback；
- 正常业务流程中的兼容 wrapper；
- 为了不改旧代码而新增 adapter。

如果旧路径、重复路径或兼容层影响当前功能、用户需求或代码清晰度，应迁移到正式路径并删除旧路径，而不是继续补兼容。

短期保留只允许用于临时诊断、数据恢复或证据追溯；不得出现在普通用户导航、文档或正常流程中，并必须有明确删除条件。

## 4. 三类任务流程

### A. 用户授权的 UI / 需求 / 流程变更

用户明确提出的 UI、交互、页面结构、流程、文案、信息层级或需求变化，以用户需求为第一位，不需要强行编造 Root Cause。

执行前说明：

```text
Change Intent:
Product Reason:
Impact Radius:
Replacement Plan:
Verification Plan:
```

必须判断是否需要删除旧路径、旧 UI、重复逻辑或兼容层。

### B. Bug / 回归 / 错误行为修复

修复 bug、回归、数据错误、权限错误、状态错误、旧路径泄漏、API/service 错误或正式流程阻塞时，必须先说明：

```text
Root Cause:
Impact Radius:
Repair Strategy:
Verification Plan:
```

不得只修当前报错点或只让当前测试通过。

### C. 低风险文案 / 视觉微调

只涉及文案、间距、样式或非关键布局，且不影响流程、数据、权限、状态、路由、API 或测试时，可以轻量处理：

```text
Change:
Affected page/component:
User-visible result:
Verification:
```

一旦影响流程或路径，必须升级为 A 或 B。

## 5. 正确修改规则

所有修改都必须正确完成用户目标，不得只做局部表面调整。

禁止：

- 只修当前按钮但保留错误流程；
- 只隐藏错误提示；
- 只放宽测试断言；
- 只保留旧路径继续工作；
- 新增第二套页面、第二套路由或第二套 API；
- 为避免改动共享层而堆叠局部绕过；
- 用 mock、硬编码成功、默认成功或静默降级冒充正式实现；
- 把缺失、部分、不可用、降级、无效或冲突状态显示为成功。

如果根因或需求影响共享层，必须修共享层。共享层包括 route config、navigation、API client、backend router、application service、repository、DTO/schema、state machine、permission/role guard、data readiness、job/run lifecycle、daily strategy/post-market proposal flow。

## 6. 用户路径和数据真实性

普通用户只能看到正式产品路径。

普通用户正常流程不得依赖内部术语或技术 ID，例如 Job、Workflow、Pipeline、Artifact、Provider、Schema、config_path、prompt_run_id、run_id、raw JSON、数据库表名、内部函数名或本机路径。

缺失、部分、不可用、降级、无效和冲突状态必须真实展示。不得默认为 false、0 或成功，不得静默降级，不得伪造 fingerprint、version、snapshot 或 traceability。

## 7. 验证规则

每个修改必须按影响范围验证，而不是只跑当前失败测试。

至少验证：

1. 当前用户需求或失败功能已正确完成；
2. 相邻页面、按钮、路由和返回路径未破坏；
3. 相邻 API/client/service/repository 未破坏；
4. 权限、角色、只读/可写边界仍正确；
5. unavailable/partial/error/empty/loading 状态仍真实；
6. 普通用户不依赖旧路径或内部术语；
7. 必要的 tests、typecheck、lint、build 或 E2E smoke 已运行。

无法运行测试时，必须记录未运行项、原因、替代验证、剩余风险和是否阻塞交付。

## 8. 停止条件

如果正确完成需求或修复问题需要以下行为，必须停止并说明：

- 引入用户未授权的新产品能力；
- 改变用户明确目标；
- 改变正式对象生命周期；
- 影响现有用户数据安全；
- 无恢复方案的破坏性迁移；
- 无法判断是否应删除某个证据路径；
- 需要真实外部数据源或访问配置才能证明；
- 修改会影响大量正式流程且无法完成验证。

输出：

```text
ESCALATION_REQUIRED
原因：
证据：
已安全完成：
不能继续的风险：
需要用户决定：
建议选项：
```

## 9. 完成回复格式

每次修改完成后，必须输出：

```text
任务：
类型：UI/需求变更 / Bug修复 / 低风险微调
状态：ACCEPTED / NOT_ACCEPTED / ESCALATION_REQUIRED
Change Intent 或 Root Cause：
Impact Radius：
修改内容：
删除的旧路径/重复实现：
保留的临时路径及原因：
修改文件：
已运行验证：
未运行验证及原因：
相邻回归覆盖：
剩余风险：
是否可继续手动测试：
```

不得使用“基本完成”“应该可以”“看起来没问题”等模糊结论。
