import asyncio
import json
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.agents.orchestrator.tool_calling_orchestrator_agent import (
    _build_history_context_from_state,
    _input_image_names,
    _parse_math_video_tool_request,
    create_orchestrator_agent,
    MathVideoToolAgent,
)


class FakeMathVideoAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        parameters = ctx.session.state["current_parameters"]
        current_output = {
            "author": "FakeMathVideoAgent",
            "status": "success",
            "message": "fake video ready",
            "message_for_user": "视频生成完成",
            "output_artifacts": [],
            "output_text": parameters["prompt"],
        }
        yield Event(
            author=self.name,
            content=Content(role="model", parts=[Part(text="fake video ready")]),
            actions=EventActions(state_delta={"current_output": current_output}),
        )


def test_input_image_names_keeps_supported_image_artifacts():
    artifacts = [
        {"name": "problem.png"},
        {"name": "nested/diagram.JPG"},
        {"name": "notes.md"},
        {"name": ""},
        {},
    ]

    assert _input_image_names(artifacts) == ["problem.png", "nested/diagram.JPG"]


def test_build_history_context_pairs_summary_and_message():
    state = {
        "summary_history": ["solve", "render"],
        "message_history": ["done", "video ready"],
    }

    assert _build_history_context_from_state(state) == (
        "step 1: goal=solve; result=done\n"
        "step 2: goal=render; result=video ready"
    )


def test_build_history_context_returns_empty_without_history():
    assert _build_history_context_from_state({}) == ""


def test_parse_math_video_tool_request_accepts_json_payload():
    request = '{"prompt": "2点后时针分针何时重合？", "math_video_mode": "legacy"}'

    assert _parse_math_video_tool_request(request) == {
        "prompt": "2点后时针分针何时重合？",
        "math_video_mode": "legacy",
    }


def test_parse_math_video_tool_request_accepts_nested_agenttool_request():
    request = '{"request": "{\\"prompt\\": \\"题目\\", \\"math_video_mode\\": \\"fast\\"}"}'

    assert _parse_math_video_tool_request(request) == {
        "prompt": "题目",
        "math_video_mode": "fast",
    }


def test_parse_math_video_tool_request_falls_back_to_legacy_prompt():
    assert _parse_math_video_tool_request("直接生成视频") == {
        "prompt": "直接生成视频",
        "math_video_mode": "legacy",
    }


def test_create_orchestrator_agent_uses_runtime_name():
    agent = create_orchestrator_agent()

    assert agent.name == "OrchestratorAgent"


def test_math_video_tool_agent_sets_current_parameters_and_output():
    async def run_case():
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        await session_service.create_session(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
            state={
                "input_artifacts": [{"name": "diagram.png", "description": "input"}],
                "summary_history": [],
                "message_history": [],
            },
        )
        agent = MathVideoToolAgent(FakeMathVideoAgent(name="FakeMathVideoAgent"))
        runner = Runner(
            agent=agent,
            app_name="test_app",
            session_service=session_service,
            artifact_service=artifact_service,
        )
        request = json.dumps(
            {
                "request": json.dumps(
                    {
                        "prompt": "测试题目",
                        "math_video_mode": "legacy",
                    }
                )
            }
        )
        async for _ in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=Content(role="user", parts=[Part(text=request)]),
        ):
            pass

        session = await session_service.get_session(
            app_name="test_app",
            user_id="test_user",
            session_id="test_session",
        )
        assert session.state["current_parameters"] == {
            "prompt": "测试题目",
            "input_img_name": ["diagram.png"],
            "current_info": "null",
            "math_video_mode": "legacy",
        }
        assert session.state["current_output"]["status"] == "success"
        assert session.state["latest_tool_output_ready"] is True

    asyncio.run(run_case())
