import asyncio

from src.agents.experts.math_video.code_generation_agent import (
    code_generation_agent_before_model_callback,
)
from src.agents.experts.math_video.manimce_shot_agent import MANIMCE_SHOT_DESIGN_KEY
from src.agents.experts.math_video.manimce_solution_agent import MANIMCE_SOLUTION_KEY
from src.agents.experts.math_video.manimgl_code_generation_agent import (
    manimgl_code_generation_before_model_callback,
)
from src.agents.experts.math_video.manimgl_shot_agent import MANIMGL_SHOT_DESIGN_KEY
from src.agents.experts.math_video.manimgl_solution_agent import MANIMGL_SOLUTION_KEY
from src.agents.experts.math_video.math_video_generation_agent import (
    manimce_math_video_generation_agent,
    manimgl_math_video_generation_agent,
)


class FakeCallbackContext:
    def __init__(self, state):
        self.state = state

    async def load_artifact(self, filename):
        raise AssertionError(f"Unexpected artifact load: {filename}")


class FakeLlmRequest:
    def __init__(self):
        self.contents = []


def _joined_request_text(request: FakeLlmRequest) -> str:
    texts = []
    for content in request.contents:
        for part in content.parts:
            if part.text:
                texts.append(part.text)
    return "\n".join(texts)


def test_manimce_and_manimgl_routes_use_distinct_planning_agents():
    assert [agent.name for agent in manimce_math_video_generation_agent.sub_agents] == [
        "ManimCESolutionAgent",
        "ManimCEShotAgent",
        "CodeGenerationAgent",
        "RenderAgent",
    ]
    assert [agent.name for agent in manimgl_math_video_generation_agent.sub_agents] == [
        "ManimGLSolutionAgent",
        "ManimGLShotAgent",
        "ManimGLSegmentedVideoAgent",
    ]


def test_manimce_code_generation_reads_manimce_state_keys():
    request = FakeLlmRequest()
    context = FakeCallbackContext(
        {
            "current_parameters": {"prompt": "题目", "current_info": "null"},
            MANIMCE_SOLUTION_KEY: "MANIMCE_SOLUTION",
            MANIMCE_SHOT_DESIGN_KEY: "MANIMCE_SHOT",
            MANIMGL_SOLUTION_KEY: "MANIMGL_SOLUTION",
            MANIMGL_SHOT_DESIGN_KEY: "MANIMGL_SHOT",
        }
    )

    asyncio.run(code_generation_agent_before_model_callback(context, request))
    text = _joined_request_text(request)

    assert "MANIMCE_SOLUTION" in text
    assert "MANIMCE_SHOT" in text
    assert "MANIMGL_SOLUTION" not in text
    assert "MANIMGL_SHOT" not in text


def test_manimgl_code_generation_reads_manimgl_state_keys():
    request = FakeLlmRequest()
    context = FakeCallbackContext(
        {
            "current_parameters": {"prompt": "题目", "current_info": "null"},
            MANIMCE_SOLUTION_KEY: "MANIMCE_SOLUTION",
            MANIMCE_SHOT_DESIGN_KEY: "MANIMCE_SHOT",
            MANIMGL_SOLUTION_KEY: "MANIMGL_SOLUTION",
            MANIMGL_SHOT_DESIGN_KEY: "MANIMGL_SHOT",
        }
    )

    asyncio.run(manimgl_code_generation_before_model_callback(context, request))
    text = _joined_request_text(request)

    assert "MANIMGL_SOLUTION" in text
    assert "MANIMGL_SHOT" in text
    assert "MANIMCE_SOLUTION" not in text
    assert "MANIMCE_SHOT" not in text
