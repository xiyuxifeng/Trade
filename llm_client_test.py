
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "trade-strategy-ai")))
import asyncio
from src.llm.client import LLMClient, from_env_and_config
from src.common.config import load_app_config

async def main():
    # 加载配置
    loaded = load_app_config("trade-strategy-ai/config/app.yaml")
    llm_cfg = loaded.config.llm

    env_key = os.getenv("DASHSCOPE_API_KEY")
    print("[LLM 配置] provider=", llm_cfg.provider)
    print("[LLM 配置] model=", llm_cfg.model)
    print("[LLM 配置] url=", llm_cfg.url)
    print("[LLM 配置] api_key(from yaml)=", "<set>" if llm_cfg.api_key else "<empty>")
    print("[ENV] DASHSCOPE_API_KEY=", "<set>" if env_key else "<empty>")

    client = LLMClient(from_env_and_config(
        provider=llm_cfg.provider,
        model=llm_cfg.model,
        url=llm_cfg.url,
        api_key=llm_cfg.api_key,
    ))

    system_prompt = "You are a helpful assistant."
    user_prompt = "你是谁？"
    try:
        result = await client.complete_text(system_prompt=system_prompt, user_prompt=user_prompt)
        print("LLM 返回：", result)
    except Exception as e:
        print(f"错误信息：{e}")
        print("请参考文档：https://help.aliyun.com/model-studio/developer-reference/error-code")

if __name__ == "__main__":
    asyncio.run(main())
