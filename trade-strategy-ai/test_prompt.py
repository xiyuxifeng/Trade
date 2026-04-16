"""
Prompt 测试脚本

用于测试 prompts 目录中的 prompt 文件的返回值。

使用方法：
    python test_prompt.py --id <article_id>
    python test_prompt.py --id <article_id> --prompt concept_extraction
    python test_prompt.py --id <article_id> --prompt all
    python test_prompt.py --id <article_id> --prompt rule_extraction --max-tokens 2000
    python test_prompt.py --id <article_id> --source comments

示例：
    python test_prompt.py --id 123e4567-e89b-12d3-a456-426614174000
    python test_prompt.py --id 400ecb1a-851d-480c-82a2-5d077451180a --prompt concept_extraction
    python test_prompt.py --id 123e4567-e89b-12d3-a456-426614174000 --prompt all
    python test_prompt.py --id 123e4567-e89b-12d3-a456-426614174000 --source comments
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from src.common.config import load_app_config, apply_database_config_to_env
from src.db.session import session_scope
from src.llm.client import LLMClient, from_env_and_config
from src.models.raw_article import RawArticle

# 400ecb1a-851d-480c-82a2-5d077451180a 龙虎榜
# 75f1b488-d463-4703-9064-ef27a3c2afe1 一字首开

# 12f873fc-c3bf-44ca-aae8-f26596649b38 周总结贴(8.11-8.15)
# 988494d3-606d-4a2d-bb5d-2e429b60f259 周总结帖（1.12-1.16）

def load_prompt(prompts_dir: Path, prompt_name: str) -> str:
    """加载 prompt 文件内容"""
    prompt_path = prompts_dir / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def build_system_prompt(prompt_name: str, prompts_dir: Path) -> str:
    """根据 prompt 类型构建 system prompt"""
    if prompt_name == "concept_extraction":
        prompt = load_prompt(prompts_dir, "concept_extraction")
        return f"""{prompt}

最终输出必须合并为一个 JSON 对象，包含字段：extracted_concepts, trading_symbols, strategy_rules, preconditions, comment_insights, sentiment_score, confidence_score。

输出格式要求：
{{
  "extracted_concepts": [...],   // 0-10 条，太多说明提取不精准
  "trading_symbols": [...],       // 0-5 个，优先提取有把握的
  "strategy_rules": [...],        // 0-5 条，宁缺毋滥
  "preconditions": [...],         // 0-5 条
  "comment_insights": [...],      // 0-3 条，从评论中提炼
  "sentiment_score": float,       // -1.0 ~ 1.0
  "confidence_score": float       // 0.0 ~ 1.0
}}

你必须只输出严格 JSON，不要输出 Markdown、不要解释。"""

    elif prompt_name == "rule_extraction":
        prompt = load_prompt(prompts_dir, "rule_extraction")
        return f"""{prompt}

最终输出必须是一个 JSON 对象，包含 strategy_rules 字段。

输出格式要求：
{{
  "strategy_rules": [
    {{
      "schema_version": "v0",
      "claim_key": "...",
      "rule_type": "entry|exit|filter|sizing|risk",
      "instrument_focus": "stock|etf|cb|mixed",
      "condition": {{"op": "..."}},
      "action": {{"type": "...", "side": "buy|sell", ...}},
      "params": {{}},
      "confidence": 0.6,
      "quoted_text": "触发该规则的原文片段"
    }}
  ]
}}

你必须只输出严格 JSON，不要输出 Markdown、不要解释。"""

    elif prompt_name == "precondition_extraction":
        prompt = load_prompt(prompts_dir, "precondition_extraction")
        return f"""{prompt}

最终输出必须是一个 JSON 对象，包含 preconditions 字段。

输出格式要求：
{{
  "preconditions": [
    {{
      "schema_version": "v0",
      "claim_key": "filter.market_regime|filter.volatility|filter.liquidity|filter.event_risk",
      "instrument_focus": "stock|etf|cb|mixed",
      "condition": {{"op": "..."}},
      "confidence": 0.5,
      "quoted_text": "原文片段"
    }}
  ]
}}

你必须只输出严格 JSON，不要输出 Markdown、不要解释。"""

    elif prompt_name == "all":
        concept_p = load_prompt(prompts_dir, "concept_extraction")
        rule_p = load_prompt(prompts_dir, "rule_extraction")
        pre_p = load_prompt(prompts_dir, "precondition_extraction")
        return f"""你必须只输出严格 JSON，不要输出 Markdown、不要解释。

{concept_p}

{rule_p}

{pre_p}

最终输出必须合并为一个 JSON 对象，包含字段：extracted_concepts, trading_symbols, strategy_rules, preconditions, comment_insights, sentiment_score, confidence_score。

输出格式要求：
{{
  "extracted_concepts": [...],   // 0-10 条
  "trading_symbols": [...],       // 0-5 个，优先提取有把握的
  "strategy_rules": [...],        // 0-5 条，宁缺毋滥
  "preconditions": [...],         // 0-5 条
  "comment_insights": [...],      // 0-3 条，从评论中提炼
  "sentiment_score": float,       // -1.0 ~ 1.0
  "confidence_score": float       // 0.0 ~ 1.0
}}"""

    else:
        raise ValueError(f"未知的 prompt 类型: {prompt_name}")


async def get_article_content(article_id: UUID, source: str = "content") -> tuple[str, str, list]:
    """从数据库获取文章内容

    Args:
        article_id: 文章 UUID
        source: 数据源，可选 'content'（content_text）、'comments'（评论）、'raw'（原始内容）
    """
    async with session_scope() as session:
        stmt = select(RawArticle).where(RawArticle.id == article_id)
        result = await session.scalar(stmt)

        if result is None:
            raise ValueError(f"未找到 article_id={article_id} 的文章")

        content_text = result.content_text or ""
        comments = result.comments or []
        raw_payload = result.raw_payload or {}

        if source == "comments":
            # 使用评论作为输入
            return "\n".join([json.dumps(c, ensure_ascii=False) for c in comments]), result.source_url, comments
        elif source == "raw":
            # 使用 raw_payload 作为输入
            return json.dumps(raw_payload, ensure_ascii=False), result.source_url, comments
        else:
            # 默认使用 content_text
            return content_text, result.source_url, comments


async def test_prompt(
    article_id: UUID,
    prompt_name: str,
    prompts_dir: Path,
    source: str = "content",
    max_tokens: int | None = None,
    llm_config: object | None = None,
) -> dict:
    """测试单个 prompt

    Args:
        article_id: 文章 UUID
        prompt_name: prompt 类型
        prompts_dir: prompts 目录
        source: 数据源，可选 'content'、'comments'、'raw'
        max_tokens: 最大 token 数
        llm_config: LLM 配置对象
    """
    content_text, source_url, comments = await get_article_content(article_id, source)

    if not content_text:
        raise ValueError("文章内容为空")

    # 截断过长内容
    if len(content_text) > 12000:
        content_text = content_text[:12000]
        print(f"⚠️ 内容过长，已截断至 12000 字符")

    # 构建 system prompt
    system_prompt = build_system_prompt(prompt_name, prompts_dir)

    # 构建 user prompt
    if prompt_name == "all":
        user_prompt = json.dumps({
            "title": "",
            "source_url": source_url,
            "content_text": content_text,
        }, ensure_ascii=False)
    else:
        user_prompt = json.dumps({
            "title": "",
            "source_url": source_url,
            "content_text": content_text,
        }, ensure_ascii=False)

    # 调用 LLM
    from src.common.config import AppConfig
    llm_cfg = from_env_and_config(
        provider=llm_config.provider if llm_config else None,
        model=llm_config.model if llm_config else None,
        url=llm_config.url if llm_config else None,
        api_key=llm_config.api_key if llm_config else None,
    )
    client = LLMClient(llm_cfg)

    print(f"\n{'='*60}")
    print(f"📝 测试 Prompt: {prompt_name}")
    print(f"📦 数据源: {source}")
    print(f"{'='*60}")
    print(f"📄 文章 ID: {article_id}")
    print(f"🔗 来源: {source_url}")
    print(f"📊 内容长度: {len(content_text)} 字符")
    print(f"💬 评论数: {len(comments)}")
    print(f"{'='*60}")
    print(f"\n📤 System Prompt:\n{system_prompt[:500]}..." if len(system_prompt) > 500 else f"\n📤 System Prompt:\n{system_prompt}")
    print(f"\n📥 User Prompt:\n{user_prompt[:500]}..." if len(user_prompt) > 500 else f"\n📥 User Prompt:\n{user_prompt}")
    print(f"\n{'='*60}")
    print(f"🤖 正在调用 LLM...")

    try:
        response = await client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        print(f"✅ LLM 返回成功!")
        print(f"\n📥 Response:\n{json.dumps(response, ensure_ascii=False, indent=2)}")
        return response
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        raise


async def main():
    parser = argparse.ArgumentParser(description="测试 Prompt 效果")
    parser.add_argument("--id", required=True, help="文章 UUID")
    parser.add_argument(
        "--prompt",
        default="all",
        choices=["concept_extraction", "rule_extraction", "precondition_extraction", "all"],
        help="Prompt 类型 (默认: all)",
    )
    parser.add_argument(
        "--source",
        default="content",
        choices=["content", "comments", "raw"],
        help="数据源: content=content_text, comments=评论, raw=raw_payload (默认: content)",
    )
    parser.add_argument("--max-tokens", type=int, default=None, help="最大 token 数")
    parser.add_argument("--config", default="config/app.yaml", help="配置文件路径")
    args = parser.parse_args()

    # 加载配置
    loaded = load_app_config(Path(args.config))
    apply_database_config_to_env(loaded.config)

    # 解析 article_id
    try:
        article_id = UUID(args.id)
    except ValueError:
        print(f"❌ 无效的 article_id: {args.id}")
        sys.exit(1)

    # prompts 目录
    prompts_dir = Path("prompts")
    if not prompts_dir.exists():
        prompts_dir = Path(".") / "prompts"
        if not prompts_dir.exists():
            print(f"❌ 找不到 prompts 目录")
            sys.exit(1)

    try:
        await test_prompt(
            article_id=article_id,
            prompt_name=args.prompt,
            prompts_dir=prompts_dir,
            source=args.source,
            max_tokens=args.max_tokens,
            llm_config=loaded.config.llm,
        )
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
