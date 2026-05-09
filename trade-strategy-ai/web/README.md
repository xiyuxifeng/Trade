# trade-strategy-ai web

`web/` 是项目的 React + TypeScript + Vite 前端控制台，用来承接 Web 管理后台的 Stage 4 基线能力。

## 快速启动

```bash
corepack pnpm install
corepack pnpm dev
```

默认开发服务器会启动在 Vite 的本地地址，前端通过 `/api/ui/v1` 访问 UI BFF。

## 可用脚本

```bash
corepack pnpm dev
corepack pnpm build
corepack pnpm preview
corepack pnpm lint
corepack pnpm typecheck
```

## 当前前端入口

- `/` - 总览
- `/jobs` - 任务中心
- `/workflows` - 工作流
- `/artifacts` - 产物中心
- `/market` - 市场数据
- `/strategies` - 策略版本
- `/backtests` - 回测中心
- `/reports` - 报表中心
- `/settings` - 系统设置
- `/ops` - 运维中心

## 当前支持的 UI BFF

前端优先对接以下接口：

- `/api/ui/v1/system/status`
- `/api/ui/v1/jobs*`
- `/api/ui/v1/workflows*`
- `/api/ui/v1/artifacts*`
- `/api/ui/v1/market*`

## API Key

如果需要透传 API Key，可在浏览器本地存储中设置 `trade-strategy-ai.apiKey`。
前端请求层会自动读取该值，并以 `X-API-Key` 头发送给后端。

## 验证

```bash
corepack pnpm build
corepack pnpm typecheck
corepack pnpm lint
```

## 说明

- 前端默认采用深色数据密集型控制台风格。
- 任务中心、工作流、产物中心和市场页是 Stage 4 的首批可用页面。
- 后续页面会继续沿用同一套路由、布局和数据访问方式扩展。
