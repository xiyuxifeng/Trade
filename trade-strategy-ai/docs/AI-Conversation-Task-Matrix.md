# Trade Strategy AI Task 组合与使用示例

本文件只在需要组合 Task 或查询示例时读取，不是每个 Task 的必读文件。

## 可组合执行矩阵

| Stage | Task 组合 | 建议 |
| --- | --- | --- |
| 0 | RT-S0-001 + RT-S0-002 | 可以，同 Session 串行；已完成 |
| 1 | RT-S1-001 | 单独；已完成 |
| 1 | RT-S1-002 | 已执行，不再保留专用 Prompt |
| 1 | RT-S1-003 | 单独；同 Stage 延续时使用 Continuation |
| 2 | RT-S2-001、RT-S2-002、RT-S2-003 | 分别单独，M3 |
| 3 | RT-S3-001 + RT-S3-002 | 有条件；默认分两 Task，同 Session 时串行 |
| 3 | RT-S3-003 | 单独 |
| 3 | RT-S3-004 | 单独且最后 |
| 4 | RT-S4-002 + RT-S4-003 | 可以，同 Session 串行 |
| 4 | RT-S4-001 | 建议后置单独 |
| 5 | RT-S5-001 + RT-S5-002 | 有条件，同 Parent Session 多批次 |
| 5 | RT-S5-003 | 后置单独 |
| 6 | RT-S6-001 + RT-S6-002 | 可以，同 Session 串行 |
| 6 | RT-S6-003 + RT-S6-004 | 可以，同 Session 串行 |
| 7 | RT-S7-001 + RT-S7-002 | 可以，同 Session 多批次 |
| 7 | RT-S7-003 + RT-S7-004 | 有条件，同 Session 串行 |
| 8 | RT-S8-001 + RT-S8-002 | 可以，同 Session 串行 |
| 8 | RT-S8-003 | 单独 |
| 9 | RT-S9-001 + RT-S9-002 | 可以，同 Session 串行 |
| 9 | RT-S9-003 | 后置单独 |
| 10 | RT-S10-001 + RT-S10-002 | 可以，同 Session 串行 |
| 10 | RT-S10-003 + RT-S10-004 | 可以，同 Session 串行 |
| 11 | RT-S11-002 + RT-S11-003 | 有条件，同 Session 串行 |
| 11 | RT-S11-004 + RT-S11-005 | 有条件，同 Session 多批次 |
| 11 | RT-S11-001 + RT-S11-007 | 可以，同 Session |
| 11 | RT-S11-006 | 单独且最后 |
| 12 | RT-S12-001 | 单独，M3 |
| 12 | RT-S12-002 + RT-S12-003 | 有条件，同 Session 串行 |

不得组合：

- RT-S2-001 与 RT-S2-003；
- RT-S3-001 与 RT-S3-004；
- 未稳定的数据任务与 RT-S5-003；
- RT-S8-001 与 RT-S9-003；
- RT-S10-001 与 RT-S10-003；
- 灰度迁移与被灰度实现；
- 旧入口退役与未完成迁移或观察期。

Stage 5 和 Stage 6 的“部分并行”不表示可在一个 Prompt 中跨 Stage 合并。必须由用户明确授权、使用不同 Parent Session/工作范围，并先冻结稳定的数据契约。

## 使用示例

### RT-S1-003

```text
Same-Stage Continuation Prompt
+ Stage 1 产品页面约束
```

新 Session 时改用 `Stage Bootstrap Prompt`。

### RT-S2-002

```text
Same-Stage Continuation Prompt
+ 数据库迁移安全
+ 领域契约冻结（仅在当前 Task 仍修改领域契约时）
```

### RT-S6-002

```text
Same-Stage Continuation Prompt
+ 回测安全
+ 数据时间语义与调度
```

### RT-S12-001

```text
Stage Bootstrap Prompt
+ 最终退役与交付
+ 被退役领域对应专项约束
```

该任务必须使用高风险专项验证，不能仅运行普通 Task 验证。

## Prompt 调用编排核验

仅在 Stage 3、Stage 7、Stage 10，或其他实际修改 LLM 调用链的 Task 中追加：

```text
Verify compliance with trade-strategy-ai/docs/LLM-Prompt-Orchestration.md:
- one article_analysis_v1 main call for a normal article
- at most one targeted article_analysis_repair_v1
- modular extraction Prompts are not four default production calls
- no per-article author total-profile Prompt
- author batches use 10–20 structured articles
- conditional llm_attribution_v1 only
- llm_postmortem_notes_v1 is conditional or once per daily summary
- Prompt/Schema/model/token/cost/input_hash/run_id records
- cache and idempotency
- LLM raw output is not the final formal fact source
- legacy Prompt stops formal writes after cutover
- deletion only after retirement conditions pass
```

不要在与 LLM 调用链无关的 UI、数据库基础设施或系统管理 Task 中追加此段。