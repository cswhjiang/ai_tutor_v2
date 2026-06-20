import json
from pathlib import PurePosixPath
from typing import Any, AsyncGenerator, Dict, List

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.adk.tools import AgentTool
from google.genai.types import Content, Part

from conf.system import SYS_CONFIG
from src.agents.experts.math_video.math_video_generation_agent import math_video_generation_agent
from src.llm.model_factory import build_model_kwargs
from src.logger import logger


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def _input_image_names(input_artifacts: List[Dict[str, Any]]) -> List[str]:
    """Return image artifact names that can be forwarded to math video agents."""
    image_names = []
    for artifact in input_artifacts:
        name = artifact.get("name")
        if not name:
            continue
        if PurePosixPath(name).suffix.lower() in IMAGE_EXTENSIONS:
            image_names.append(name)
    return image_names


def _build_history_context_from_state(state: Dict[str, Any]) -> str:
    """Build concise execution history for the next expert invocation."""
    summary_history = state.get("summary_history", []) or []
    message_history = state.get("message_history", []) or []
    if not summary_history or not message_history:
        return ""

    lines = []
    for index, (summary, message) in enumerate(zip(summary_history, message_history), start=1):
        lines.append(f"step {index}: goal={summary}; result={message}")
    return "\n".join(lines)


def _content_text(content: Content | None) -> str:
    """Extract text from an ADK content object."""
    if not content or not content.parts:
        return ""
    return "\n".join(part.text for part in content.parts if part.text)


def _parse_math_video_tool_request(request_text: str) -> Dict[str, Any]:
    """Parse the AgentTool request string into math video parameters."""
    request_text = request_text.strip()
    if not request_text:
        return {"prompt": "", "math_video_mode": "legacy"}

    try:
        data = json.loads(request_text)
    except json.JSONDecodeError:
        return {"prompt": request_text, "math_video_mode": "legacy"}

    if isinstance(data, dict) and set(data) == {"request"}:
        nested_request = str(data.get("request") or "").strip()
        try:
            nested_data = json.loads(nested_request)
        except json.JSONDecodeError:
            return {"prompt": nested_request, "math_video_mode": "legacy"}
        if isinstance(nested_data, dict):
            data = nested_data

    if not isinstance(data, dict):
        return {"prompt": str(data), "math_video_mode": "legacy"}

    prompt = str(data.get("prompt") or data.get("request") or request_text)
    mode = str(data.get("math_video_mode") or "legacy")
    return {"prompt": prompt, "math_video_mode": mode}


class MathVideoToolAgent(BaseAgent):
    """ADK AgentTool adapter for the existing MathVideoGenerationAgent."""

    model_config = {"arbitrary_types_allowed": True}

    math_video_agent: BaseAgent

    def __init__(self, math_video_agent: BaseAgent):
        super().__init__(
            name="generate_math_video",
            description=(
                "Generate a math explanation video. The request must be a JSON "
                "string with fields: prompt, math_video_mode. Use legacy mode by default."
            ),
            math_video_agent=math_video_agent,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Adapt AgentTool request text into `current_parameters` and run math video."""
        request = _parse_math_video_tool_request(_content_text(ctx.user_content))
        input_artifacts = ctx.session.state.get("input_artifacts", []) or []
        history_context = _build_history_context_from_state(ctx.session.state)
        parameters = {
            "prompt": request["prompt"],
            "input_img_name": _input_image_names(input_artifacts),
            "current_info": history_context if history_context else "null",
            "math_video_mode": request["math_video_mode"],
        }
        logger.info(f"AgentTool invoking MathVideoGenerationAgent: {parameters}")

        # The existing math-video agent reads `current_parameters` directly from
        # session state. Mutate the child in-memory session for immediate use and
        # emit the delta so AgentTool forwards it to the parent context.
        ctx.session.state["current_parameters"] = parameters
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "current_parameters": parameters,
                    "latest_tool_output_ready": False,
                    "latest_tool_summary": "生成数学讲解视频",
                }
            ),
        )

        async for event in self.math_video_agent.run_async(ctx):
            yield event

        current_output = ctx.session.state.get("current_output", {})
        yield Event(
            author=self.name,
            content=Content(
                role="model",
                parts=[
                    Part(
                        text=(
                            current_output.get("message_for_user")
                            or current_output.get("message")
                            or "数学讲解视频生成完成"
                        )
                    )
                ],
            ),
            actions=EventActions(
                state_delta={
                    "latest_tool_output_ready": True,
                    "latest_tool_summary": "生成数学讲解视频",
                }
            ),
        )


async def direct_orchestrator_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> None:
    """Inject the current request state into the direct orchestrator prompt."""
    user_prompt = callback_context.state.get("user_prompt", "")
    input_artifacts = callback_context.state.get("input_artifacts", []) or []
    artifact_lines = []
    for index, artifact in enumerate(input_artifacts, start=1):
        artifact_lines.append(
            f"{index}. name={artifact.get('name')}; description={artifact.get('description')}"
        )

    aux_text = [
        "# 当前用户任务",
        user_prompt,
        "",
        "# 当前输入或可用文件",
        "\n".join(artifact_lines) if artifact_lines else "无",
    ]
    llm_request.contents.append(
        Content(role="user", parts=[Part(text="\n".join(aux_text))])
    )


def create_tool_calling_orchestrator_agent(
    llm_model: str = "",
) -> LlmAgent:
    """Create an orchestrator that calls math-video generation as an AgentTool."""
    if not llm_model:
        llm_model = SYS_CONFIG.orchestrator_llm_model
    logger.info(f"ToolCallingOrchestratorAgent: using llm: {llm_model}")

    model_kwargs = build_model_kwargs(llm_model)
    return LlmAgent(
        name="ToolCallingOrchestratorAgent",
        **model_kwargs,
        description="Route user tutoring requests to ADK tools.",
        instruction=DIRECT_ORCHESTRATOR_INSTRUCTION,
        before_model_callback=direct_orchestrator_before_model_callback,
        tools=[AgentTool(MathVideoToolAgent(math_video_generation_agent))],
    )


DIRECT_ORCHESTRATOR_INSTRUCTION = """
你是 AI Tutor 的 Orchestrator，负责接收用户任务并调用合适的工具完成任务。

# 核心规则
- 不要生成 global plan。
- 不要生成 single plan。
- 不要把任务拆给多个外层 agent。
- 当用户要求“讲解数学题并生成视频”、"做个视频讲解"、"数学讲解视频" 或类似请求时，必须调用 `generate_math_video` 工具。
- 调用 `generate_math_video` 时，`request` 必须是 JSON 字符串，包含 `prompt` 和 `math_video_mode` 两个字段。
- `prompt` 必须保留用户的完整题目和视频要求。
- 默认 `math_video_mode` 使用 `"legacy"`，只有用户明确要求快速生成时才使用 `"fast"`。
- 不要先自行解题再决定是否调用工具；需要视频时直接调用工具。
- 工具成功返回后，用简短中文告诉用户任务完成即可，不要暴露内部工具名、agent 名称或实现细节。
- 如果用户请求不是数学视频任务，可以直接回答简单问题；如果任务当前不支持，简短说明当前版本主要支持数学讲解视频生成。
"""
