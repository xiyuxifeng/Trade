# Web 配置模板 Review

## 结论

`config/app.yaml` 的结构已经足够支持 Web 端导入生成 Profile，现有的导入链路也能直接消费 `config_path`。
但原始文件更偏“运行配置”，不适合作为 Web 用户直接编辑的模板，因此补了两份专用模板：

- [config/app.web-template.minimal.yaml](/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.web-template.minimal.yaml)
- [config/app.web-template.yaml](/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.web-template.yaml)

两份模板都保留了当前 `app.yaml` 的顶层 section 结构，方便直接通过现有 Profile 导入接口生成正式 Profile 和 snapshot。

## 现有 `app.yaml` 的特点

- 结构完整，覆盖数据库、调度、评估、数据源、抓取、LLM、Persona、Kaipan、告警等主要配置面。
- 已支持环境变量展开，适合把敏感信息改成 `${VAR}` 占位。
- 直接作为 Web 模板时，缺少“哪些字段需要用户填写”的显式说明。

## 模板设计原则

- 保持与当前 `config/app.yaml` 相同的 section 名称，避免导入后丢字段。
- 敏感字段统一使用环境变量占位，不在模板里写明文。
- 非敏感字段保留当前默认值，降低用户配置成本。
- 允许用户先填模板，再通过 Web 端导入生成 Profile。
- 两个模板都带字段注释，说明每个配置项的用途。

## 需要重点填充的字段

- `database.url`
- `crawl.auth.tgb.cn.cookie`
- `llm.api_key`
- `kaipan.token`
- `kaipan.user_id`
- 告警 webhook：
  - `alerting.dingtalk.webhook_url`
  - `alerting.dingtalk.secret`
  - `alerting.feishu.webhook_url`
  - `alerting.wecom.webhook_url`

## 保留默认即可的字段

- `timezone`
- `schedule`
- `evaluation`
- `data`
- `data_quality`
- `dashboard`
- `storage`
- `persona`
- `api`
- `akshare`

## 使用方式

1. 先选择模板版本。
2. 补齐本地或部署环境里的环境变量。
3. 按业务需要调整模板内容。
4. 在 Web 端使用现有“配置导入”入口，填写该文件路径。
5. 系统会通过 `ConfigProfileService.import_from_config_path()` 生成正式 Profile，并保存 snapshot。

## 备注

- 当前导入流程会对敏感字段做脱敏和 `secret_refs` 记录，所以模板里保留占位符是可接受的。
- 最小版适合快速导入，完整版适合一次性整理完整运行环境。
