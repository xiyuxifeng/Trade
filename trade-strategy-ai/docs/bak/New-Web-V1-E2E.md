# New Web V1 E2E

## 目标

这份说明只覆盖 `NW-V1-S4-001` 的回归验收，不定义新的正式用户入口。

V1 E2E 的作用是把已经完成的 Web 交付链串成一条可重复验证的路径：

- Web acceptance：验证关键页面、路由和 UI contract
- CLI smoke gate：在显式启用时，验证底层回归命令仍然可用

## 默认执行方式

默认只跑仓内可复现的回归：

```bash
python -m pytest tests/e2e/test_e2e_runner.py tests/e2e/test_web_acceptance.py tests/e2e/test_article_pipeline_v1.py -q
```

其中 `test_article_pipeline_v1` 默认会跳过真实 CLI 回归，只保留编排结构和调用顺序的验证。

## 真实 CLI smoke

如果本地已经具备可用的数据库和运行环境，可以显式启用真实 CLI 回归：

```bash
RUN_V1_E2E=1 python -m pytest tests/e2e/test_article_pipeline_v1.py -q
```

或者直接执行回归命令：

```bash
python -m cli.main e2e-regression --config config/app.yaml --max-articles 1 --extract-limit 1
```

这个 CLI 只作为内部验证工具，不作为对外用户入口。

## 验证范围

这条回归链应当至少覆盖：

- 成功路径
- 失败路径
- 空数据路径
- 权限不足路径
- Job
- Timeline
- Artifact
- Config Snapshot

## 失败定位顺序

如果回归失败，优先按以下顺序排查：

1. `tests/e2e/test_web_acceptance.py`
2. `web/src/e2e/web-acceptance.test.tsx`
3. `tests/e2e/test_article_pipeline_v1.py`
4. `cli.main e2e-regression`

如果是 UI 文案或页面结构变更，先更新 acceptance 测试，再回头看 TaskList 是否需要同步说明。
