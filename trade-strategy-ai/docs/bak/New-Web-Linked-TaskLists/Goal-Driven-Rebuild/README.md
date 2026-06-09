# Goal-Driven Rebuild

这是一组围绕“最终用户目标必须实现”的重构文档，作为本次重构的单独管理目录。

## 使用顺序

1. [产品使用流程与页面说明](./Product-Usage-Flow.md)
2. [市场数据流向与技术契约](./Market-Data-Contract.md)
3. [Web 导航与页面文案清单](./Web-Navigation-and-Copy.md)
4. [重构 TaskList](./TaskList.md)
5. [一级入口与子入口对照表](./Entry-Subentry-Matrix.md)
6. [快速入口](./Quick-Start.md)

## 这组文档的作用

- 明确最终用户目标
- 明确 Web 入口如何变得清晰易用
- 明确哪些概念必须收口
- 明确哪些重复抓取、重复标准化、重复快照必须消除
- 明确这次重构允许调整 Web 页面、数据库和现有代码逻辑，只要服务最终目标

## 统一主线

```text
博客文章
  -> 规则提取
  -> 回测验证
  -> 交易员画像
  -> 盘前预测
  -> 盘后复盘
```

任何实现、页面、数据表、Job、文案，都必须服务于这条主线。
