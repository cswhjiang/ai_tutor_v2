import datetime
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.genai.types import Content, Part

from conf.system import SYS_CONFIG
from src.agents.experts.math_video.manimgl_solution_agent import MANIMGL_SOLUTION_KEY
from src.llm.model_factory import build_model_kwargs, resolve_agent_llm_settings
from src.logger import logger
from src.observability.timing import compact_text, timing_context_from_invocation, timing_stage


MANIMGL_SHOT_DESIGN_KEY = "math_video/manimgl_shot_design"


async def manimgl_shot_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Build the model request for ManimGL shot design."""
    current_parameters = callback_context.state.get("current_parameters", {})
    solution = callback_context.state.get(MANIMGL_SOLUTION_KEY, "")
    logger.debug(
        "ManimGLShotAgent received solution chars={} preview={}",
        len(solution),
        compact_text(solution),
    )

    current_prompt = current_parameters["prompt"]
    current_info = current_parameters.get("current_info", "null")
    llm_request.contents.append(
        Content(
            role="user",
            parts=[
                Part(
                    text=(
                        f"当前的任务是：{current_prompt}\n"
                        f" 当前已经收集到的信息是：{current_info}\n"
                    )
                )
            ],
        )
    )

    if solution:
        llm_request.contents.append(
            Content(
                role="user",
                parts=[Part(text=f"当前答案智能体提供的解题步骤为：{solution}\n")],
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


class ManimGLShotAgent(BaseAgent):
    """Generate shot design used by the ManimGL route."""

    model_config = {"arbitrary_types_allowed": True}
    llm: LlmAgent

    def __init__(self, name: str, description: str = "", llm_model: str = ""):
        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        resolved_llm_model, _ = resolve_agent_llm_settings(llm_model, agent_name=name)
        logger.info(f"{name}: using llm: {resolved_llm_model}")
        model_kwargs = build_model_kwargs(llm_model, response_json=True, agent_name=name)

        time_str = datetime.date.today().strftime("%Y-%m-%d")
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            instruction=MANIMGL_SHOT_INSTRUCTION.replace("{TIME_STR}", time_str),
            before_model_callback=manimgl_shot_before_model_callback,
            output_key=MANIMGL_SHOT_DESIGN_KEY,
        )
        super().__init__(name=name, description=description, llm=llm)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the ManimGL shot agent and publish a step status event."""
        current_parameters = ctx.session.state.get("current_parameters", {})
        if "prompt" not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：prompt"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": error_text,
                "output_text": "",
            }
            logger.error(error_text)
            yield Event(
                author=self.name,
                content=Content(role="model", parts=[Part(text=error_text)]),
                actions=EventActions(state_delta={"current_output": current_output}),
            )
            return

        timing_context = timing_context_from_invocation(ctx)
        with timing_stage(
            "agent",
            self.name,
            **timing_context,
            metadata={"mode": "manimgl_math_video"},
        ) as agent_timing:
            text_list = []
            with timing_stage(
                "llm",
                f"{self.name}.llm",
                **timing_context,
                metadata={"output_key": MANIMGL_SHOT_DESIGN_KEY},
            ):
                async for event in self.llm.run_async(ctx):
                    if event.is_final_response() and event.content and event.content.parts:
                        generated_text = next(
                            (part.text for part in event.content.parts if part.text),
                            None,
                        )
                        if not generated_text:
                            continue
                        yield event
                        text_list.append(generated_text)

            if not text_list:
                message = f"{self.name} 生成回复失败"
                message_for_user = "生成回复失败"
                logger.error(message)
                agent_timing["status"] = "error"
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": message,
                    "message_for_user": message_for_user,
                    "output_text": "",
                }
            else:
                message = f"{self.name} 已完成方案设计"
                message_for_user = " 已完成当前步骤执行"
                output_text = "\n".join(text_list)
                agent_timing["output_chars"] = len(output_text)
                current_output = {
                    "author": self.name,
                    "status": "success",
                    "message": message,
                    "message_for_user": message_for_user,
                    "output_text": output_text,
                }

            yield Event(
                author=self.name,
                content=Content(role="model", parts=[Part(text=message)]),
                actions=EventActions(state_delta={"current_output": current_output}),
            )


MANIMGL_SHOT_INSTRUCTION = """
你是一个视频分镜和视频制作的专家，擅长利用 ManimGL（3Blue1Brown 版本 manimlib）做科普视频的制作。
你会接受用户输入的一个理工科任务或者一个问题，以及其他智能体提供的答案。你的任务是协助生成一个利用 ManimGL 做讲解的视频，你负责的是分镜和代码可落地的画面规划。

你的输出会被 ManimGLCodeGenerationAgent 直接翻译为 Python 代码，所以分镜必须兼顾讲解效果和 ManimGL 的稳定可执行性。


# 任务输出要求
 - 视频画面的宽高比为 16:9
 - 默认按 ManimGL 坐标系规划画面，横向范围约 [-7, 7]，纵向范围约 [-4, 4]
 - 旁白段数建议 4 到 6 段，每段 6 到 20 秒
 - 每个镜头都必须有稳定的 `narration_key`，key 使用英文小写和下划线
 - 每个镜头都要包含：旁白、画面对象、动画步骤、持续时间建议、ManimGL 实现注意事项

# 必要信息
 - 当前时间：{TIME_STR}

# 工作方法
 - 先复述一遍问题，然后呈现问题的讲解，最后总结一下
 - 分镜要忠实跟随 ManimGLSolutionAgent 的解题步骤，不重新解题
 - 把复杂公式拆成多个独立视觉对象来规划，例如 `R`、`+`、`Y`、`=`、`21` 分别是独立 `Tex` 或 `Text` 对象，再用 `VGroup(...).arrange(RIGHT)` 排列
 - 不要要求代码生成阶段从一个整块 `Tex` 内部选择或高亮局部字符
 - 不要在分镜里使用需要 `get_part_by_tex`、`select_part`、`select_parts`、`get_part_by_text` 才能实现的效果
 - 若需要突出某个变量或数字，直接规划为独立对象并对这个对象上色、放大、加框或 Indicate
 - 避免复杂 3D、相机运动、updater、路径跟踪、外部图片、外部字体、网络资源
 - 避免大量 1 秒以内的小碎动画；一个旁白镜头内部可以包含 2 到 4 个动画步骤，然后用 `wait` 对齐旁白

# 任务输入
 - 问题：生成用户描述的理工科相关的任务
 - 图片：数量不定相关的图片，可选项。
 - 答案：ManimGLSolutionAgent 提供的答案。


# 任务输出
只输出 JSON 对象，不要输出 Markdown，不要解释。JSON 字段必须包含：
{
  "title": "视频标题",
  "style": {
    "background": "深色或浅色背景说明",
    "palette": ["主要颜色名称"],
    "layout": "整体布局原则"
  },
  "shots": [
    {
      "narration_key": "intro",
      "duration_seconds": 8,
      "narration": "这一镜头的旁白文本",
      "visual_goal": "这一镜头要让观众看懂什么",
      "objects": [
        "需要创建的对象，写清楚 Text/Tex/VGroup/Rectangle/Line/Arrow/Circle/Dot 等 ManimGL 对象",
        "公式必须说明拆成独立对象，不要整块 Tex 后再取局部"
      ],
      "animations": [
        "Write(title)",
        "FadeIn(problem_group)",
        "wait_to_match_voiceover"
      ],
      "manimgl_notes": [
        "中文使用 Text(..., font='PingFang SC')",
        "数学符号使用独立 Tex 对象",
        "不要使用 get_part_by_tex/select_part/select_parts"
      ]
    }
  ],
  "summary": "最终答案和方法总结"
}

镜头数量控制在 4 到 6 个。每个镜头必须有旁白，且旁白 key 不能重复。

"""
