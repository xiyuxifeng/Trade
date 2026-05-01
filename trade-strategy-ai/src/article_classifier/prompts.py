"""文章分类 Prompt 定义"""

# 分类类型常量
ARTICLE_TYPES = ["rule", "record", "concept", "mixed", "noise"]

# 文章分类提示词模板
CLASSIFICATION_PROMPT = """你是一个文章分类器。请判断以下文章的[主要]类型：

类型定义：
- rule: 描述一般性交易规则/策略，不针对具体历史操作
- record: 描述具体历史操作（包含明确的时间、价格、数量）
- concept: 纯理论/框架/心态分享，无具体条件
- mixed: 同一篇文章包含多种类型内容（如：先讲方法论，再列具体案例）
- noise: 个人观点、闲聊、新闻、无交易逻辑

输出格式（严格 JSON，不要输出任何其他内容）：
{{
    "article_type": "rule|record|concept|mixed|noise",
    "confidence": 0.0~1.0,
    "type_scores": {{"rule": 0.x, "record": 0.x, "concept": 0.x, "mixed": 0.x, "noise": 0.x}},
    "reason": "简短原因"
}}

注意：
- 如果是混合类型，选择最主要的类型
- confidence 低于 0.5 时标记为"需要人工复核"
- 只输出 JSON，不要输出任何解释或markdown
"""

# 内容最大长度限制
MAX_CONTENT_LENGTH = 10000