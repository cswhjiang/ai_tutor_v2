import json
from typing import AsyncGenerator, Dict

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.genai.types import Blob, Content, Part

from conf.system import SYS_CONFIG
from src.agents.experts.math_video.fast_template_renderer import fast_manim_to_video
from src.llm.model_factory import build_model_kwargs
from src.logger import logger
from src.utils import clean_json_string


async def fast_math_video_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Build the single model request used by the fast math video path."""
    current_parameters = callback_context.state.get("current_parameters", {})
    current_prompt = current_parameters["prompt"]
    current_info = current_parameters.get("current_info", "null")
    llm_request.contents.append(
        Content(
            role="user",
            parts=[
                Part(
                    text=(
                        f"当前任务：{current_prompt}\n"
                        f"当前已经收集到的信息：{current_info}\n"
                    )
                )
            ],
        )
    )
    input_img_name = current_parameters.get("input_img_name", [])
    if input_img_name:
        artifact_parts = [Part(text="以下是和任务相关的图片：\n")]
        for i, art_name in enumerate(input_img_name):
            artifact_parts.append(Part(text=f"这是第{i + 1}张图片，它的名称是{art_name}"))
            art_part = await callback_context.load_artifact(filename=art_name)
            artifact_parts.append(art_part)
        llm_request.contents.append(Content(role="user", parts=artifact_parts))


class FastMathVideoGenerationAgent(BaseAgent):
    """Generate math explanation videos with one script LLM call and a local template."""

    model_config = {"arbitrary_types_allowed": True}

    llm: LlmAgent
    legacy_agent: BaseAgent | None = None

    def __init__(
        self,
        name: str,
        description: str = "",
        llm_model: str = "",
        legacy_agent: BaseAgent | None = None,
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.science_llm_model
        logger.info(f"FastMathVideoGenerationAgent: using llm: {llm_model}")
        model_kwargs = build_model_kwargs(
            llm_model,
            response_json=True,
            reasoning_effort="low",
        )
        llm = LlmAgent(
            name=f"{name}ScriptAgent",
            **model_kwargs,
            description="Generate a concise structured math video script.",
            instruction=FAST_MATH_VIDEO_SCRIPT_INSTRUCTION,
            before_model_callback=fast_math_video_before_model_callback,
            output_key="math_video/fast_script",
        )
        super().__init__(
            name=name,
            description=description,
            llm=llm,
            legacy_agent=legacy_agent,
        )

    def format_event(self, content_text: str = None, state_delta: Dict = None):
        """Create an ADK event with optional content and state updates."""
        event = Event(author=self.name)
        if state_delta:
            event.actions = EventActions(state_delta=state_delta)
        if content_text:
            event.content = Content(role="model", parts=[Part(text=content_text)])
        return event

    async def _run_legacy(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the previous multi-agent Manim-code pipeline when requested."""
        if self.legacy_agent is None:
            current_output = {
                "author": self.name,
                "status": "error",
                "message": "Legacy math video pipeline is not configured.",
                "message_for_user": "旧版视频生成流程不可用。",
                "output_text": "",
            }
            yield self.format_event(
                "Legacy math video pipeline is not configured.",
                {"current_output": current_output},
            )
            return
        async for event in self.legacy_agent.run_async(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the fast structured-script video generation pipeline."""
        current_parameters = ctx.session.state.get("current_parameters", {})
        if "prompt" not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：prompt"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": error_text,
                "message_for_user": "视频生成失败：缺少题目描述。",
                "output_text": "",
            }
            logger.error(error_text)
            yield self.format_event(error_text, {"current_output": current_output})
            return

        mode = str(current_parameters.get("math_video_mode", "")).lower()
        if mode == "legacy" or current_parameters.get("use_legacy", False):
            async for event in self._run_legacy(ctx):
                yield event
            return

        text_list: list[str] = []
        async for event in self.llm.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                generated_text = next((part.text for part in event.content.parts if part.text), None)
                if not generated_text:
                    continue
                yield event
                text_list.append(generated_text)

        if not text_list:
            message = "FastMathVideoGenerationAgent 生成脚本失败"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": message,
                "message_for_user": "视频脚本生成失败。",
                "output_text": "",
            }
            logger.error(message)
            yield self.format_event(message, {"current_output": current_output})
            return

        raw_script = "\n".join(text_list)
        try:
            script = json.loads(clean_json_string(raw_script))
        except Exception as exc:
            message = f"FastMathVideoGenerationAgent 解析脚本 JSON 失败: {exc}"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": message,
                "message_for_user": "视频脚本格式错误。",
                "output_text": raw_script,
            }
            logger.error(message)
            yield self.format_event(message, {"current_output": current_output})
            return

        render_result = await fast_manim_to_video(script, current_parameters["prompt"])
        if render_result["status"] == "error":
            message = f"快速数学视频渲染失败：{render_result['message']}"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": message,
                "message_for_user": "视频渲染失败。",
                "output_text": json.dumps(render_result.get("script", script), ensure_ascii=False),
            }
            logger.error(message)
            yield self.format_event(message, {"current_output": current_output})
            return

        step = ctx.session.state.get("step", 0)
        artifact_name = f"step{step + 1}_fast_math_video_output.mp4"
        artifact_part = Part(
            inline_data=Blob(mime_type="video/mp4", data=render_result["message"])
        )
        await ctx.artifact_service.save_artifact(
            app_name=ctx.session.app_name,
            user_id=ctx.session.user_id,
            session_id=ctx.session.id,
            filename=artifact_name,
            artifact=artifact_part,
        )

        normalized_script = render_result.get("script", script)
        has_voiceover = bool(render_result.get("has_voiceover"))
        voiceover_text = "包含并发合成语音" if has_voiceover else "无语音，包含字幕式讲解"
        text = (
            f"执行步骤{step + 1}: {self.name}：快速数学视频生成完成\n"
            f"视频保存成功，输出视频名称为{artifact_name}。"
        )
        description = (
            "快速模板生成的数学讲解视频。"
            f"渲染规格：{render_result.get('render_quality')}；{voiceover_text}。"
        )
        output_artifacts = [{"name": artifact_name, "description": description}]
        current_output = {
            "author": self.name,
            "status": "success",
            "message": text,
            "message_for_user": "数学讲解视频生成完成",
            "output_artifacts": output_artifacts,
            "output_text": json.dumps(normalized_script, ensure_ascii=False),
        }
        yield self.format_event(text, {"current_output": current_output})


FAST_MATH_VIDEO_SCRIPT_INSTRUCTION = """
你是一名数学老师和短视频脚本设计师。你的任务是把用户提供的数学题转成一个结构化讲解脚本。

这个脚本会被本地固定 Manim 模板直接渲染成视频。你不要输出 Manim 代码，不要输出 Markdown，不要解释你的工作过程。

# 输出格式
只输出一个 JSON 对象，字段如下：
{
  "title": "视频标题，48字以内",
  "problem": "题目原文或精简复述，保持数学条件完整",
  "intro_narration": "开场旁白，口语化，一两句话",
  "steps": [
    {
      "heading": "步骤标题，短句",
      "explanation": "屏幕上显示的讲解，尽量短，讲清本步逻辑",
      "equation": "可选，纯文本公式，例如 4 + 4 = 8",
      "narration": "本步骤旁白，口语化，不要太长"
    }
  ],
  "answer": "最终答案，短句",
  "summary": "总结方法，短句"
}

# 规则
- steps 控制在 3 到 5 步。
- 必须先保证答案正确。
- equation 使用纯文本，不使用 LaTeX，不使用 Markdown。
- explanation 和 narration 使用用户语言。
- 不要引用系统、工具、Manim、JSON、代码生成等内部信息。
- 如果题目比较简单，也要给出清晰的思路步骤。
"""
