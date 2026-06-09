# Prompt 检查与迁移说明

## 1. 检查结论

现有 Prompt 需要更新，但不建议一次性替换所有生产逻辑。应先增加新 Schema 和新 Prompt，通过版本号并行验证，再逐步迁移。

当前发现的主要问题：

1. `rule_extraction.md` 输出字段过少。
   - 缺少规则标题、描述、数据依赖、时间周期、持有周期、可量化状态、缺失信息、证据列表。
   - `condition` 与 `action` 结构过于开放，容易产生无法执行或难以校验的 JSON。
   - 无法区分作者明确声明的条件与 LLM 推断的条件。

2. `precondition_extraction.md` 强制偏向 `filter.market_regime`。
   - 文章可能根本没有声明市场状态。
   - 容易诱导 LLM 猜测适用状态。
   - 面向中国用户应使用“市场状态”文案，但代码字段可暂时保留兼容映射。

3. `concept_extraction.md` 使用中文弯引号，示例不是严格合法 JSON。
   - 应改成标准英文双引号。
   - 需要输出证据引用和文章方法标签，方便后续画像聚类。

4. 现有 `test_prompt.py` 把输出 Schema 拼接在测试代码中。
   - Prompt 文件和运行时代码可能出现 Schema 分叉。
   - 建议 Schema 由 Pydantic/JSON Schema 单一事实源生成。
   - 测试工具只加载版本化 Prompt 和对应 Schema。

5. 当前没有完整的作者画像 Prompt。
   - 作者画像不能仅由 LLM 自由总结。
   - 应拆成单篇文章结构化、批次画像汇总、最终作者画像、画像变化解释四类 Prompt。
   - 回测数据和规则统计必须作为结构化输入，LLM 只负责归纳和解释。

6. 盘后 Prompt 目前偏向单笔交易摘要。
   - 后续应增加“作者画像证据更新”和“策略优化建议”两个独立 Prompt。
   - 不要让单次盘后结果直接改写正式画像或正式策略。

## 2. 推荐 Prompt 架构

```text
文章层
├─ article_classification_v1
├─ article_structure_extraction_v1
├─ rule_extraction_v1
└─ explicit_precondition_extraction_v1

聚合层
├─ author_method_profile_batch_v1
├─ author_rule_profile_summary_v1
└─ author_profile_merge_v1

验证层
├─ author_validated_profile_v1
├─ author_profile_revision_v1
└─ strategy_revision_proposal_v1
```

## 3. 关键原则

### 3.1 不允许把推断写成事实

必须区分：

- `explicit`：文章明确声明。
- `inferred`：LLM 推断。
- `observed`：回测或统计观察。
- `approved`：人工审核批准。

### 3.2 市场状态允许未知

文章未声明市场状态时：

```json
{
  "market_state": {
    "status": "not_declared",
    "explicit_conditions": [],
    "inferred_hypotheses": []
  }
}
```

不能自动补成“适用于牛市”或“适用于震荡市”。

### 3.3 LLM 不负责计算回测指标

LLM 不得计算或伪造：

- 胜率
- 收益率
- 最大回撤
- 交易次数
- 不同市场状态表现

这些必须由程序计算后作为结构化输入传给画像 Prompt。

### 3.4 作者画像不是作者实盘画像

不得声称：

- 作者真实收益率
- 作者真实胜率
- 作者真实仓位
- 作者真实执行纪律
- 作者真实最大回撤

只能描述：

- 文章表达的方法
- 提取规则的结构
- 规则集合的回测验证结果

### 3.5 100+ 篇文章采用分层汇总

```text
逐篇结构化
→ 每 10～20 篇或按主题/时间聚合
→ 生成批次画像
→ 合并作者总画像
```

不要一次向 LLM 输入全部文章全文。

## 4. 推荐迁移顺序

### Stage 1：兼容升级

- 新增 `rule_extraction_v1.md`。
- 保留旧 `rule_extraction.md`。
- 新增 `prompt_version`、`schema_version`。
- 将新旧结果分别保存，进行对照测试。

### Stage 2：结构化文章与批次画像

- 对已有 100+ 篇文章逐篇生成 `article_structure`。
- 去重和聚类。
- 每批 10～20 篇生成 `author_method_profile_batch`。
- 不重复读取全文。

### Stage 3：生成作者画像

- 程序生成规则结构统计。
- LLM 汇总方法画像。
- 回测完成后生成验证画像。
- 人工审核后发布正式画像版本。

### Stage 4：盘前盘后接入

盘前：

```text
规则正式适用性
> 当前市场状态
> 正式策略
> 数据质量
> 作者验证画像
> 作者方法画像
```

盘后：

```text
累计结构化证据
→ 达到阈值
→ 生成画像修订建议
→ 人工审核
```

## 5. 代码字段兼容建议

用户界面统一使用“市场状态”。

现有代码若已经大量使用 `regime`，短期可保留：

```text
market_regime
regime_version
regime_label
```

API 可增加中文展示字段或 canonical 字段：

```text
market_state
market_state_version
market_state_label
```

迁移期做明确映射，不建议仅为了翻译立即修改所有数据库列和内部代码。

## 5.1 自动审核与人工审核边界

Prompt 输出完成后必须进入自动审核服务，不能直接写为正式规则。

自动审核负责确定：

- Schema 是否合法。
- 证据是否存在。
- 条件是否完整。
- 是否有模糊词或缺失参数。
- 是否存在 LLM 未标记的推断。
- 数据依赖是否可用。
- 是否重复或冲突。
- 是否可回测。
- 风险等级。

自动审核服务应使用确定性规则为主，不应再依赖另一个自由文本 LLM 完成最终裁决。

LLM 可以提供补充解释，但最终自动审核状态应可重复、可测试。

状态建议：

```text
auto_pass
recommend_pass
manual_review
not_backtestable
recommend_reject
```

映射到用户界面：

```text
自动通过
建议通过
需要人工确认
不可回测
建议拒绝
```

以下规则不能自动进入正式可用状态：

- 任何未经回测的规则。
- 涉及风险、仓位或资金管理的规则。
- 市场状态为 LLM 推断的规则。
- 存在参数补全或人工修改的规则。
- 与现有规则冲突的规则。
- 准备加入正式策略的规则。

## 6. 验收标准

更新后的 Prompt 必须满足：

- 严格 JSON。
- 输出可被 Pydantic 校验。
- 每个结论有证据引用。
- 未声明内容保持未知。
- 推断和事实分离。
- 回测指标不由 LLM 生成。
- 作者画像支持时间分段。
- 支持批次和增量更新。
- 新旧 Prompt 可以通过固定文章集做回归比较。


## 7. 回归样本集建立方式

黄金样本集不要求用户在实施前提供。

Stage 3 应从现有文章中自动筛选 10～15 篇候选样本，覆盖主要文章和规则类型。用户只需要确认候选列表和人工审核结论。

固定样本必须记录：

- article_id
- 内容版本或内容哈希
- Prompt 版本
- Schema 版本
- LLM 原始输出
- 自动审核版本和结果
- 人工确认结果

Prompt、Schema 或自动审核规则每次变化后，必须先运行固定样本对比，再决定是否批量处理。


## 8. 统一调用编排

Prompt 文件按职责拆分，不代表生产环境逐个调用。

生产主链路：

```text
article_analysis_v1
→ 单篇普通文章通常 1 次
```

其内部覆盖：

- 分类
- 概念与标的
- 文章结构
- 规则
- 明确前置条件

`concept_extraction_v1`、`article_structure_extraction_v1`、`rule_extraction_v1` 和 `explicit_precondition_extraction_v1` 主要用于模块化设计、独立测试和特殊场景。

Schema 校验失败时使用：

```text
article_analysis_repair_v1
→ 最多 1 次定向修复
```

详细调用条件、批次调用、盘后调用、缓存和成本记录见：

```text
trade-strategy-ai/docs/LLM-Prompt-Orchestration.md
```

## 9. 旧 Prompt 删除验收

旧 Prompt 最终允许彻底删除，但必须全部满足：

```text
[ ] 新 Prompt 已接入全部正式调用链
[ ] 固定回归样本通过
[ ] 批量文章处理验证通过
[ ] 新旧 Schema 映射完成
[ ] 历史结果可继续读取
[ ] 代码无旧 Prompt 引用
[ ] 测试无旧 Prompt 引用
[ ] CLI 和脚本无旧 Prompt 引用
[ ] Job 和 Workflow 无旧 Prompt 引用
[ ] 当前文档无旧 Prompt 使用说明
[ ] 生产观察期无阻塞问题
[ ] 回滚方案已验证
[ ] Prompt 退役报告已完成
```

任一条件未满足：

- 旧 Prompt 只能标记 `deprecated` 或 `compatibility_only`
- 不得删除
- 不得把 Prompt 重构任务标记完成

满足全部条件后：

- 删除旧 Prompt 文件
- 删除旧加载逻辑和测试
- 不建立长期 legacy Prompt 目录
- 通过 Git 历史保留追溯能力
