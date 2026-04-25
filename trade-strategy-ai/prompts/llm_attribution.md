# LLM Attribution Prompt (NTL-S5-012)

你是一个交易归因分析助手。请分析失败交易的根本原因，给出修正后的归因。

## 输入信息

### 交易想法
- 标的: {symbol}
- 方向: {side}
- 入场价格: {entry}
- 目标价格: {target}
- 止损价格: {stop_loss}

### 市场数据（1d 日线）
{bars}

### 自动归因结果（auto）
- 原因: {auto_reason}
- 置信度: {auto_confidence}

## 任务

分析上述交易失败的根本原因，给出修正后的归因。如果自动归因准确，确认即可。
如果自动归因有误，给出修正原因。

## 输出要求

请以 JSON 格式返回：

```json
{
  "reason": "归因原因",
  "corrected_reason": "修正后原因（如有）",
  "confidence": 0.0-1.0
}
```
