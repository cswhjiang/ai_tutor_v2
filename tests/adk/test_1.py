import asyncio
import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


APP_NAME = "ai_tutor_adk_demo"
USER_ID = "demo_user"
SESSION_ID = "demo_session"
DEFAULT_MODEL = "openai/gpt-4o"


def build_demo_agent(model_name: str = DEFAULT_MODEL) -> LlmAgent:
    """Build a minimal ADK 2.3 LiteLLM agent for local smoke testing."""
    return LlmAgent(
        name="CodexAgent",
        model=LiteLlm(model=model_name),
        instruction="你是一个精通系统架构的资深开发专家。",
    )


def test_build_demo_agent_uses_adk_23_litellm_model_argument():
    """Verify the demo uses ADK 2.3 compatible LiteLLM construction."""
    agent = build_demo_agent()

    assert agent.name == "CodexAgent"
    assert isinstance(agent.model, LiteLlm)


async def main():
    """Run the demo against a real LiteLLM provider when credentials exist."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY must be set before running this demo.")

    agent = build_demo_agent(os.getenv("DEMO_LITELLM_MODEL", DEFAULT_MODEL))
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="请分析 Python 的 GIL 对并发死锁的影响。")],
    )

    print(f"--- Running {agent.model.model} through ADK 2.3 ---")

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)



if __name__ == "__main__":
    asyncio.run(main())
