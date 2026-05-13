# New-Web-Roadmap

> 本 Roadmap 连接 `New-Web-TaskList.md`、`New-Web-V2-TaskList.md`、`New-Web-V3-TaskList.md`，用于说明 Demo 到最终交付版本的阶段边界。

## V1：产品化底座 + article_pipeline 完整切片

目标：证明系统可以从 Demo 变成可交付架构。

交付：
- Runtime Contract
- Job/Workflow/Step 底座
- ConfigSnapshot
- Artifact Metadata
- Job Detail
- article_pipeline Web/API/Worker 闭环
- 最小权限、文档、E2E

不交付：
- 正式 Profile 全量迁移
- 完整正式 Web UI
- 市场数据、策略、回测、规则池完整链路

## V2：正式 Profile + 正式 Web 工作台 + 市场数据/策略链路

目标：从“可交付骨架”进入“可持续使用版本”。

交付：
- ProfileDefinition / ProfileVersion / ProfileSnapshot / EffectiveConfig
- ProfileResolver
- Profile API 和设置页
- 正式 Web IA、API Client、Job Detail
- Market Data 切片
- Strategy Run 切片
- CLI 正式降级

## V3：完整业务闭环 + 管理员运维 + 最终交付验收

目标：达到完整项目交付要求。

交付：
- Backtest Center
- Optimize Candidate
- Rule Pool 审核闭环
- Admin Health
- Backup / Restore
- Audit Center
- Permission Matrix
- Final Web UI
- 用户手册、API 文档、部署文档、运维手册
- 最终 E2E 和 Release Checklist

## 版本关系

- V1 是架构和第一条业务链路验证。
- V2 是配置、Web、市场数据、策略运行产品化。
- V3 是回测、规则池、运维、安全、文档和最终交付收口。

## 长期 Future

V3 之后可以继续规划：
- 分布式 Worker
- 高级调度
- 多租户
- 高级监控告警
- 高级可视化
- 插件化 Provider
- 更完整的自动化测试平台
