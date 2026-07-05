# LLM Prompt 调用编排

## 1. 目的

本文件定义 Prompt 文件与实际 LLM 调用次数之间的关系，避免按照“一个 Prompt 文件一次调用”重复处理同一文章。

## 2. 单篇文章调用

生产主链路：

```text
article_analysis_v1
→ 通常调用 1 次
```

该调用一次输出：

- 文章分类
- 概念和标的
- 文章结构
- 候选规则
- 明确前置条件

以下 Prompt 可作为 Schema 设计模块和独立测试模块：

- `concept_extraction_v1.md`
- `article_structure_extraction_v1.md`
- `rule_extraction_v1.md`
- `explicit_precondition_extraction_v1.md`

生产环境默认由 `article_analysis_v1.md` 统一编排，不应对同一篇普通文章分别调用四次。

## 3. 修复调用

当出现以下情况时，调用：

```text
article_analysis_repair_v1
```

触发条件：

- JSON 解析失败
- Schema 校验失败
- 证据缺失
- 局部字段冲突
- 输出截断
- 指定规则需要定向修复

调用次数：

```text
通常 0 次
最多 1 次
超过 1 次仍失败则进入人工处理
```

修复调用必须只修改目标字段。

## 4. 超长文章

超长文章可以：

```text
程序分段
→ 各段抽取
→ 程序合并
→ 必要时调用一次合并/修复
```

不得无上限重复调用。

## 5. 作者画像调用

### 批次方法画像

```text
每 10～20 篇结构化文章
→ author_method_profile_batch_v1
→ 调用 1 次
```

### 规则画像

```text
程序生成规则统计快照
→ author_rule_profile_summary_v1
→ 每个统计快照调用 1 次
```

### 验证画像

```text
回测批次完成
→ author_validated_profile_v1
→ 每个作者/验证批次调用 1 次
```

### 合并画像

```text
需要生成新画像草稿
→ author_profile_merge_v1
→ 按事件调用
```

### 画像修订

```text
新证据达到阈值
→ author_profile_revision_v1
→ 按事件调用
```

不得逐篇文章调用作者总画像 Prompt。

## 6. 盘后调用

程序先完成客观计算和自动归因。

```text
自动归因置信度高
→ 不调用 llm_attribution_v1

自动归因置信度低、证据冲突或重要信号
→ 调用 llm_attribution_v1
```

`llm_postmortem_notes_v1` 用于用户可读说明：

- 普通信号优先使用程序模板。
- 重要、失败或有争议的信号按需调用。
- 每日汇总可以调用一次，不应默认每个信号都调用。

策略修订：

```text
累计证据达到阈值
→ strategy_revision_proposal_v1
```

不得由单笔交易直接触发正式策略修改。

## 7. 缓存与幂等

缓存键至少包含：

- 内容哈希
- Prompt 版本
- Schema 版本
- 模型
- 关键参数

相同输入和相同版本不得重复计费调用。

## 8. 重试

建议：

- 网络或服务错误：指数退避重试
- JSON/Schema 错误：最多一次定向修复
- 业务证据不足：不重试，进入人工审核或等待更多证据

## 9. 调用记录

每次调用记录：

- run_id
- prompt_name
- prompt_version
- schema_version
- model
- input_hash
- token_usage
- cost
- start/end time
- status
- retry_count
- output reference

## 10. 正式事实源

LLM 原始输出不是最终正式事实源。

```text
LLM 输出
→ Schema 校验
→ 自动审核
→ 必要时人工审核
→ 正式业务对象
```
