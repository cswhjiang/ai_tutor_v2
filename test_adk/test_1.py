import asyncio
import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# 确保环境变量已设置
os.environ["OPENAI_API_KEY"] = "你的_OPENAI_API_KEY"


async def main():
    # 1. 定义模型配置 (GPT-5.3-Codex)
    # 2026版 LiteLlm 字符串必须带 openai/ 前缀
    codex_model = LiteLlm(model_id="openai/gpt-5.3-codex")

    # 2. 定义 Agent
    # 注意：最新版参数名是 instruction (单数)，tools (代替 skills)
    agent = LlmAgent(
        name="CodexAgent",
        model=codex_model,
        instruction="你是一个精通系统架构的资深开发专家。"
    )

    # 3. 初始化会话服务和运行器 (这是 2026 版的关键)
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    # 4. 运行并获取响应
    # 最新版 Runner.run() 返回的是一个同步的生成器或异步对象
    # 对于简单测试，直接使用 run 即可
    print("--- 正在连接 GPT-5.3-Codex ---")

    try:
        # 传入 session_id 是必须的，用于维持上下文
        response = runner.run(
            input="请分析 Python 的 GIL 对并发死锁的影响。",
            session_id="test_session_1"
        )

        # 打印响应文本
        print(f"\n[Codex 响应]:\n{response.text}")

    except Exception as e:
        print(f"运行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())