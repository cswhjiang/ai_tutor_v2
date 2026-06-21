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
from src.agents.experts.math_video.routes import resolve_math_video_route
from src.llm.model_factory import build_model_kwargs, resolve_agent_llm_settings
from src.logger import logger
from src.observability.timing import compact_text, timing_context_from_invocation, timing_stage


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
        return {"prompt": "", "math_video_mode": None}

    try:
        data = json.loads(request_text)
    except json.JSONDecodeError:
        return {"prompt": request_text, "math_video_mode": None}

    if isinstance(data, dict) and set(data) == {"request"}:
        nested_request = str(data.get("request") or "").strip()
        try:
            nested_data = json.loads(nested_request)
        except json.JSONDecodeError:
            return {"prompt": nested_request, "math_video_mode": None}
        if isinstance(nested_data, dict):
            data = nested_data

    if not isinstance(data, dict):
        return {"prompt": str(data), "math_video_mode": None}

    prompt = str(data.get("prompt") or data.get("request") or request_text)
    mode = data.get("math_video_mode")
    if mode is None:
        mode = data.get("math_video_route")
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
                "string with field prompt and optional field math_video_mode."
            ),
            math_video_agent=math_video_agent,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Adapt AgentTool request text into `current_parameters` and run math video."""
        timing_context = timing_context_from_invocation(ctx)
        with timing_stage("tool", "math_video_tool", **timing_context) as tool_timing:
            request = _parse_math_video_tool_request(_content_text(ctx.user_content))
            input_artifacts = ctx.session.state.get("input_artifacts", []) or []
            history_context = _build_history_context_from_state(ctx.session.state)
            parameters = {
                "prompt": request["prompt"],
                "input_img_name": _input_image_names(input_artifacts),
                "current_info": history_context if history_context else "null",
                "math_video_mode": request["math_video_mode"],
            }
            try:
                route = resolve_math_video_route(parameters)
            except ValueError as exc:
                message = str(exc)
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": message,
                    "message_for_user": "视频生成失败：不支持的生成路线。",
                    "output_text": "",
                }
                logger.error(message)
                yield Event(
                    author=self.name,
                    content=Content(role="model", parts=[Part(text=message)]),
                    actions=EventActions(state_delta={"current_output": current_output}),
                )
                return
            parameters["math_video_mode"] = route
            tool_timing["mode"] = parameters["math_video_mode"]
            tool_timing["prompt_chars"] = len(parameters["prompt"])
            logger.info(
                "AgentTool invoking MathVideoGenerationAgent: {}",
                {
                    **parameters,
                    "prompt": compact_text(parameters["prompt"]),
                    "current_info": compact_text(parameters["current_info"]),
                },
            )

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

            with timing_stage(
                "agent",
                "MathVideoGenerationAgent",
                **timing_context,
                metadata={"mode": parameters["math_video_mode"]},
            ):
                async for event in self.math_video_agent.run_async(ctx):
                    yield event

            current_output = ctx.session.state.get("current_output", {})
            tool_timing["output_status"] = current_output.get("status")
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


def create_orchestrator_agent(
    llm_model: str = "",
) -> LlmAgent:
    """Create an orchestrator that calls math-video generation as an AgentTool."""
    if not llm_model:
        llm_model = SYS_CONFIG.llm_model
    resolved_llm_model, _ = resolve_agent_llm_settings(
        llm_model,
        agent_name="OrchestratorAgent",
    )
    logger.info(f"OrchestratorAgent: using llm: {resolved_llm_model}")

    model_kwargs = build_model_kwargs(
        llm_model,
        agent_name="OrchestratorAgent",
    )
    return LlmAgent(
        name="OrchestratorAgent",
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
- 调用 `generate_math_video` 时，`request` 必须是 JSON 字符串，包含 `prompt` 字段；`math_video_mode` 是可选字段。
- `prompt` 必须保留用户的完整题目和视频要求。
- 默认路线由系统配置控制。用户没有明确要求路线时，不要强行指定 `math_video_mode`。
- 只有用户明确要求某条路线时才传 `math_video_mode`，可选值是 `"manimce"`、`"fast"`、`"manimgl"`。
- 当前阶段不要自行切换生成路线，也不要做自动 fallback；如果工具失败，不要改用另一条路线重新调用。
- 每条用户请求最多主动调用一次 `generate_math_video`。除非用户在新的消息里明确要求重试，否则不要重复调用。
- 不要先自行解题再决定是否调用工具；需要视频时直接调用工具。
- 工具成功返回后，用简短中文告诉用户任务完成即可，不要暴露内部工具名、agent 名称或实现细节。
- 工具失败返回后，必须忠实告诉用户视频生成失败，并简短反馈工具返回的失败原因；不要把失败结果说成完成。
- 如果用户请求不是数学视频任务，可以直接回答简单问题；如果任务当前不支持，简短说明当前版本主要支持数学讲解视频生成。
"""
