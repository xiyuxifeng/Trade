# AGENTS.md

## 1. 当前项目状态

`trade-strategy-ai` 的重构 Stage 已完成。当前工作不再是继续执行历史 Stage、扩展旧兼容层或追加新的重构任务，而是进入交付前手动测试、修复和最终稳定阶段。

历史重构文档如果已归档到 `refactor-stage-docs` 或其他归档目录，仅用于追溯事实，不再作为新修复任务的执行协议。之后所有 AI/Codex 修改都必须以本文件为最高约束。

当前目标：

```text
手动测试发现问题
→ 找到真实根因
→ 全面修复受影响功能
→ 删除错误路径和重复路径
→ 验证相邻流程
→ 保持代码整洁、单一路径、可交付
```

## 2. 最高优先级

之后所有修改的优先级固定为：

```text
功能正确
> 数据和业务契约正确
> 单一路径、无重复实现、无兼容堆叠
> 可运行、可测试、可恢复
> 用户可理解、可交付
> 视觉细节和非关键体验优化
```

功能正确永远第一。不得为了“最小 diff”“少改文件”“避免扩大范围”而保留错误实现、重复实现、旧路径、局部绕过或隐藏风险。

“控制范围”的含义不是只改当前报错点，而是修改范围必须覆盖真实根因和所有受影响功能；不得包含无关新功能、无关视觉重设计或未经授权的产品扩展。

## 3. 新项目单一路径原则

本项目按新项目交付处理，不为旧 UI、旧 workflow、旧 route、旧 API 或旧内部工具保留长期兼容。

禁止为了兼容而新增或保留：

- 两套路由入口；
- 两套正式 API；
- 两套页面实现；
- 两套状态机；
- 两套 service/repository 写入路径；
- 两套 schema/DTO；
- legacy fallback；
- compatibility wrapper；
- silent redirect 作为正常业务路径；
- 为了不改旧代码而新增 adapter/bypass。

如果发现旧路径、重复路径或兼容层影响当前功能，应优先迁移到正式路径并删除旧路径，而不是继续补兼容。

允许短期保留的唯一情况：删除会立即导致当前正式功能无法验证、数据无法恢复或证据不可追溯。即便保留，也必须满足：

1. 只作为临时诊断或数据恢复入口；
2. 不出现在普通用户导航、文档或正常流程；
3. 有明确删除条件；
4. 不继续承载新功能；
5. 不作为修复当前问题的捷径。

## 4. 手动测试修复任务定义

之后的任务统一称为 `RELEASE-STABILIZATION-FIX-xxx`，除非用户明确授权新功能或新重构任务。

允许处理：

- 手动测试发现的真实问题；
- 正式用户流程阻塞；
- 数据、权限、迁移、备份、恢复、初始化等交付风险；
- 文档与最终 UI 不一致；
- 页面显示虚假成功、虚假数据、错误状态被隐藏；
- 普通用户仍被迫使用旧路径、内部术语或开发工具入口；
- 代码中因兼容、重复实现、局部 patch 导致的真实缺陷。

禁止处理：

- 未经授权的新产品功能；
- 大型视觉重设计；
- 与当前缺陷无关的技术探索；
- 无验证目标的性能优化；
- 为旧路径继续补兼容；
- 为了局部通过测试而引入新的 wrapper、fallback 或临时层。

## 5. Root Cause + Impact Radius 强制流程

任何修复在写代码前必须先完成并输出：

```text
Root Cause:
- 真实根因是什么？
- 为什么会发生？
- 是局部问题还是共享逻辑问题？

Impact Radius:
- 受影响页面/路由：
- 受影响 API/client：
- 受影响 backend router：
- 受影响 service/repository：
- 受影响 DTO/schema/state machine：
- 受影响数据状态：
- 受影响权限/角色：
- 受影响测试：
- 可能被连带破坏的相邻流程：

Repair Strategy:
- 修根因还是修症状？
- 为什么这个方案能消除错误路径？
- 是否需要删除重复实现或旧路径？
- 明确不改什么，为什么？

Verification Plan:
- 当前失败功能如何验证？
- 相邻功能如何验证？
- negative/unavailable/partial/error 状态如何验证？
- 哪些测试/检查必须运行？
```

没有完成以上分析，不得开始写代码。

## 6. 全面修复原则

修复必须是：

```text
smallest complete root-cause repair
```

含义：在不引入无关新功能的前提下，完整修复根因和受影响功能。

明确禁止把“最小修复”理解为：

- 只修当前报错点；
- 只让当前测试通过；
- 只改当前按钮；
- 只在当前页面加条件分支；
- 只加 fallback 绕过错误；
- 只隐藏错误提示；
- 只放宽测试断言；
- 只保留旧路径继续工作。

如果根因位于共享层，必须修共享层。共享层包括但不限于：

- route config；
- navigation；
- API client；
- backend router；
- application service；
- repository；
- DTO/schema；
- state machine；
- permission/role guard；
- data readiness/unavailable handling；
- job/run lifecycle；
- daily strategy/post-market proposal flow。

不得在单个页面做 page-specific bypass 来规避共享层错误。

## 7. 禁止的坏味道

任何修改不得引入以下模式：

- fake default；
- silent fallback；
- test-only workaround；
- page-specific bypass；
- legacy shortcut；
- duplicate source of truth；
- compatibility shim for normal workflow；
- mock pretending to be production；
- hard-coded success；
- empty placeholder as finished feature；
- catch-all error swallowing；
- deleting tests to remove failures；
- weakening assertions to match wrong behavior；
- hiding missing data as success；
- converting `unavailable` / `partial` / `degraded` / `invalid` / `conflict` into success；
- making users understand internal IDs, raw job types, run IDs, prompt IDs, schema names, provider names or file paths to complete normal work。

发现上述模式时，应删除或重构，而不是继续堆叠。

## 8. 用户路径和术语

普通用户只能看到正式产品路径。页面和文档必须使用业务中文说明：

- 当前页面做什么；
- 用户需要提供什么；
- 系统会处理什么；
- 输出结果是什么；
- 下一步应该做什么；
- 失败或数据不足时如何处理。

普通用户正常流程不得要求理解：

- Job；
- Workflow；
- Pipeline；
- Artifact；
- Provider；
- Schema；
- config_path；
- prompt_run_id；
- run_id；
- raw JSON；
- 数据库表名；
- 内部函数名；
- 本机路径。

管理员诊断可以出现必要技术信息，但必须与普通用户路径分离，并默认不作为完成业务流程的前提。

## 9. 数据真实性和可追溯

缺失、部分、不可用、降级、无效和冲突状态必须真实展示。

不得：

- 默认为 false；
- 默认为 0；
- 默认为成功；
- 静默降级；
- 用最新数据替代历史版本；
- 用实时 Provider 替代固定回测数据；
- 伪造 fingerprint、version、snapshot、traceability；
- 用单日结果覆盖正式规则、画像或策略。

正式对象必须保持单一事实源和可追溯关系，包括但不限于：

- article revision；
- prompt/schema version；
- rule version；
- dataset snapshot；
- market snapshot/state model；
- backtest run/result；
- applicability profile；
- author profile version；
- strategy version；
- daily plan；
- post-market review；
- optimization proposal。

## 10. 测试和验证要求

每个修复必须按影响半径运行或补充验证，而不是只跑当前失败测试。

至少验证：

1. 当前失败功能已恢复；
2. 同一页面相邻 primary/secondary actions 未破坏；
3. 同一路由组导航、深链、返回路径未破坏；
4. 同一 API client 的相邻调用未破坏；
5. 同一 backend router/service/repository 的相邻业务未破坏；
6. 权限、角色、只读/可写边界仍正确；
7. unavailable/partial/error/empty/loading 状态仍真实；
8. 普通用户不依赖 legacy route 或内部术语；
9. 必要的 focused tests、typecheck、lint、build、backend tests 或 E2E smoke 已运行。

无法运行测试时，必须记录：

```text
未运行项：
原因：
替代验证：
剩余风险：
是否阻塞交付：
```

不得声称未运行的测试已通过。

## 11. 删除和重构规则

如果一个问题的根因是旧路径、重复实现、临时兼容或错误抽象，应优先删除或替换错误结构，而不是继续在其上修补。

允许大范围修改，当且仅当它是为了：

- 修复真实根因；
- 消除重复事实源；
- 删除旧路径；
- 合并重复页面/API/service；
- 让正式用户流程单一路径可用；
- 保证数据真实性；
- 让测试覆盖真实业务链路。

大范围修改必须同时给出：

- 为什么局部修复不正确；
- 哪些旧路径/重复实现被删除；
- 哪些正式路径替代它；
- 受影响功能清单；
- 回归验证结果。

## 12. 升级和停止条件

如果正确修复需要以下任一行为，必须停止并向用户说明，不得用 workaround 继续：

- 新增产品功能；
- 改变业务目标；
- 改变正式对象生命周期；
- 破坏现有用户数据；
- 无恢复方案的破坏性迁移；
- 无法判断应该删除还是保留某个证据路径；
- 需要真实外部数据源或访问配置才能证明；
- 测试环境无法复现但生产风险高；
- 修改会影响大量正式流程且无法在当前会话内完成验证。

输出格式：

```text
ESCALATION_REQUIRED
原因：
证据：
已安全完成：
不能继续的风险：
需要用户决定：
建议选项：
```

## 13. 完成回复格式

每次修复完成后，必须输出：

```text
任务：
状态：ACCEPTED / NOT_ACCEPTED / ESCALATION_REQUIRED
Root Cause：
Impact Radius：
修复内容：
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

## 14. 交付标准

最终交付前必须满足：

1. 普通用户从首页能理解下一步；
2. 文章导入到规则、审核、回测、策略、盘前、盘后、优化建议形成闭环；
3. 所有主流程只有一个正式入口；
4. 旧入口不再作为普通用户路径；
5. 页面不依赖内部开发术语；
6. 数据缺失和失败状态真实可见；
7. 规则、画像、策略、每日计划和优化建议可追溯；
8. 管理员能完成数据、任务、运行告警、迁移、备份恢复检查；
9. 测试和手动验收中的 P0/P1 已修复或明确不阻塞；
10. 没有为了兼容旧路径形成的新堆叠代码。
