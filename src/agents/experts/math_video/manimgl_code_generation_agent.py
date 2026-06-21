import datetime
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.genai.types import Content, Part
from pydantic import BaseModel, Field

from conf.system import SYS_CONFIG
from src.agents.experts.math_video.manimgl_shot_agent import MANIMGL_SHOT_DESIGN_KEY
from src.agents.experts.math_video.manimgl_solution_agent import MANIMGL_SOLUTION_KEY
from src.llm.model_factory import build_model_kwargs, resolve_agent_llm_settings
from src.logger import logger
from src.observability.timing import timing_context_from_invocation, timing_stage


class ManimGLNarrationSegment(BaseModel):
    """Narration segment used by generated ManimGL code."""

    key: str = Field(description="Unique narration key referenced by start_voiceover calls.")
    text: str = Field(description="Narration text to synthesize with TTS.")


class ManimGLCodeOutput(BaseModel):
    """Structured output contract for ManimGL code generation."""

    scene_name: str = Field(description="ManimGL Scene class name.")
    manimgl_code: str = Field(description="Complete executable ManimGL Python code.")
    narrations: list[ManimGLNarrationSegment] = Field(
        description="Narration segments matching NARRATION_SEGMENTS in the generated code."
    )


async def manimgl_code_generation_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Build the model request for ManimGL code generation."""
    current_parameters = callback_context.state.get("current_parameters", {})
    solution = callback_context.state.get(MANIMGL_SOLUTION_KEY, "")
    shot_design = callback_context.state.get(MANIMGL_SHOT_DESIGN_KEY, "")

    current_prompt = current_parameters["prompt"]
    current_info = current_parameters.get("current_info", "null")
    llm_request.contents.append(
        Content(
            role="user",
            parts=[
                Part(
                    text=(
                        f"当前的任务是：{current_prompt}\n"
                        f"当前已经收集到的信息是：{current_info}\n"
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
    if shot_design:
        llm_request.contents.append(
            Content(
                role="user",
                parts=[Part(text=f"当前视频分镜设计智能体提供的分镜为：{shot_design}\n")],
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


class ManimGLCodeGenerationAgent(BaseAgent):
    """Generate ManimGL code from solution and shot design."""

    model_config = {"arbitrary_types_allowed": True}
    llm: LlmAgent

    def __init__(
        self,
        name: str,
        description: str = "",
        llm_model: str = "",
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        resolved_llm_model, _ = resolve_agent_llm_settings(llm_model, agent_name=name)
        logger.info(f"{name}: using llm: {resolved_llm_model}")

        model_kwargs = build_model_kwargs(
            llm_model,
            response_json=True,
            agent_name=name,
        )
        time_str = datetime.date.today().strftime("%Y-%m-%d")
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            instruction=MANIMGL_CODE_GENERATION_INSTRUCTION.replace("{TIME_STR}", time_str),
            before_model_callback=manimgl_code_generation_before_model_callback,
            output_schema=ManimGLCodeOutput,
            output_key="math_video/manimgl_code",
        )
        super().__init__(name=name, description=description, llm=llm)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run ManimGL code generation and store the raw JSON output in state."""
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
                metadata={"output_key": "math_video/manimgl_code"},
            ):
                async for event in self.llm.run_async(ctx):
                    if event.is_final_response() and event.content and event.content.parts:
                        generated_text = next((part.text for part in event.content.parts if part.text), None)
                        if not generated_text:
                            continue
                        yield event
                        text_list.append(generated_text)

            if not text_list:
                message = "ManimGLCodeGenerationAgent 生成回复失败"
                logger.error(message)
                agent_timing["status"] = "error"
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": message,
                    "message_for_user": "生成回复失败",
                    "output_text": "",
                }
            else:
                message = "ManimGLCodeGenerationAgent 已完成 ManimGL 代码生成"
                output_text = "\n".join(text_list)
                agent_timing["output_chars"] = len(output_text)
                current_output = {
                    "author": self.name,
                    "status": "success",
                    "message": message,
                    "message_for_user": "已完成当前步骤执行",
                    "output_text": output_text,
                }

            yield Event(
                author=self.name,
                content=Content(role="model", parts=[Part(text=message)]),
                actions=EventActions(state_delta={"current_output": current_output}),
            )


MANIMGL_CODE_GENERATION_INSTRUCTION = """
你是一名【ManimGL（3Blue1Brown 版本 manimlib）】动画工程师，同时也是数学讲解视频工程落地专家。

你的职责是把已有的「问题描述 / 解题步骤 / 分镜脚本」忠实翻译为可执行的 ManimGL Python 代码。你不负责重新解题，不负责重排分镜。

# 必要信息
- 当前时间：{TIME_STR}

# 输出格式
你必须只输出一个 JSON 对象，不要输出 Markdown，不要解释。字段必须是：
{
  "scene_name": "ManimGL 场景类名",
  "manimgl_code": "完整可执行 Python 代码字符串",
  "narrations": [
    {"key": "intro", "text": "旁白文本，必须和代码中的 key 对应"}
  ]
}

# ManimGL 技术约束
- 必须使用 `from manimlib import *`。
- 场景类必须继承 `Scene`，且类名必须等于 `scene_name`。
- 禁止使用 Manim Community Edition 专属 API：`from manim import *`、`MathTex`、`MarkupText`、`Create`、`VoiceoverScene`、`self.voiceover`、`manim_voiceover`。
- 常用对象优先使用：`Text`、`Tex`、`TexText`、`VGroup`、`Rectangle`、`RoundedRectangle`、`SurroundingRectangle`、`Line`、`Arrow`、`Circle`、`Dot`。
- 常用动画优先使用：`Write`、`FadeIn`、`FadeOut`、`ShowCreation`、`Transform`、`ReplacementTransform`、`FadeTransform`。
- 中文文本用 `Text("中文", font="PingFang SC")`；不要把中文放进 `Tex` 公式。
- 公式使用 `Tex(r"...")`，公式里只放数学符号、英文和数字。
- 不依赖外部图片、外部音频、网络资源或第三方字体文件。
- 视频比例按 ManimGL 默认 16:9 坐标系控制，任何文字都不能明显出屏。

# ManimGL 稳定性硬性要求
- 禁止使用 `get_part_by_tex`、`get_parts_by_tex`、`select_part`、`select_parts`、`get_part_by_text`、`select_unisolated_substring`。
- 不要从一个整块 `Tex` 或 `Text` 内部选择局部字符再上色、放大或动画；这在 ManimGL 中容易因为未 isolate 而运行时报 `IndexError`。
- 如果需要突出变量、数字或等号，必须在创建时就拆成独立对象，例如：
```python
r = Tex("R", color=RED)
plus = Tex("+")
y = Tex("Y", color=YELLOW)
eq = Tex("=")
n = Tex("21")
equation = VGroup(r, plus, y, eq, n).arrange(RIGHT, buff=0.12)
```
- 如果需要多行方程，分别创建每一行的独立对象，再用 `VGroup(row1, row2, row3).arrange(DOWN, aligned_edge=LEFT)`。
- 高亮时只能直接操作已命名的独立对象，例如 `Indicate(r)`、`SurroundingRectangle(row)`、`r.set_color(RED)`，不要运行时查找子对象。
- 避免复杂 updater、always_redraw、ValueTracker、3D、相机运动、路径追踪和需要交互窗口的逻辑。
- 生成代码必须可以一次运行到底；不要写依赖人工检查、调试断点、print 调试或条件跳过渲染的逻辑。

# 布局和可读性要求
- 坐标按默认 16:9 画面规划，横向大致在 [-6.7, 6.7]，纵向大致在 [-3.7, 3.7]。
- 标题、题目、公式、答案区域要分层排布，不要让文字和公式重叠。
- 中文长句必须手动拆行，或者限制为简短短语；长段解释放到旁白里，不要全部写到画面上。
- 画面里的公式和文本要少而清晰，每个镜头只保留当前讲解所需内容。
- 颜色不要只依赖白色变量，白色球可以用浅灰描边或标签区分，避免白色文字/白色对象在浅色区域不可见。

# 旁白硬性要求
ManimGL 没有 `manim_voiceover`，旁白由 RenderAgent 通过 Volcengine TTS 合成并注入。

你的代码必须包含下面这两个全局变量，变量名必须完全一致：
```python
NARRATION_AUDIO = {}
NARRATION_SEGMENTS = [
    {"key": "intro", "text": "旁白文本"}
]
```

你的 JSON 顶层 `narrations` 必须和代码里的 `NARRATION_SEGMENTS` 内容一致，key 不能重复。

你的代码必须包含类似如下的辅助函数，并在每个镜头中使用它启动旁白：
```python
def start_voiceover(scene, key, fallback_duration=2.0):
    info = NARRATION_AUDIO.get(key)
    if info:
        scene.add_sound(info["file"])
        return max(float(info.get("duration", fallback_duration)), fallback_duration)
    return fallback_duration
```

每个主要镜头应该这样组织：
```python
duration = start_voiceover(self, "intro", 3.0)
self.play(Write(title), run_time=min(1.5, duration))
self.wait(max(0.2, duration - 1.5))
```

- 每个 `NARRATION_SEGMENTS` key 必须至少被 `start_voiceover(self, key, ...)` 调用一次。
- 不要把一个旁白段拆成很多 1 秒以内的小 `self.play`；每个旁白镜头建议 1 到 3 个主要动画，再用 `self.wait(...)` 补齐声音。
- `fallback_duration` 要接近该段旁白长度，通常 6 到 20 秒。
- `narrations` 顶层列表、`NARRATION_SEGMENTS` 和代码中 `start_voiceover` 使用的 key 必须完全一致。

# 推荐代码结构
你应优先生成清晰、保守、可维护的 ManimGL 代码：
```python
from manimlib import *

NARRATION_AUDIO = {}
NARRATION_SEGMENTS = [...]

FONT = "PingFang SC"
BG = "#101820"
TEXT = "#F3F4F6"

def cn(text, size=36, color=TEXT):
    return Text(text, font=FONT, font_size=size, color=color)

def tx(value, size=42, color=TEXT):
    return Tex(value, font_size=size, color=color)

def equation_row(*items, buff=0.12):
    return VGroup(*items).arrange(RIGHT, buff=buff)

def start_voiceover(scene, key, fallback_duration=2.0):
    info = NARRATION_AUDIO.get(key)
    if info:
        scene.add_sound(info["file"])
        return max(float(info.get("duration", fallback_duration)), fallback_duration)
    return fallback_duration
```

公式示例：
```python
row1 = equation_row(tx("R", color=RED), tx("+"), tx("Y", color=YELLOW), tx("="), tx("21"))
row2 = equation_row(tx("Y", color=YELLOW), tx("+"), tx("W", color=GREY), tx("="), tx("20"))
rows = VGroup(row1, row2).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
```

# 结构要求
- 开头：标题 + 题目。
- 中段：严格按照分镜展示解题过程。
- 结尾：明确展示最终答案和方法总结。
- 旁白段数建议 4 到 8 段，每段 6 到 20 秒可讲完。
- 代码结尾加运行提示注释：`# python -m manimlib file.py SceneName -w -l`

# 最终自检
输出前必须自行检查：
- JSON 是单个对象，不能多一个 `}`，不能包 Markdown。
- `scene_name` 与代码里的 Scene 类名完全一致。
- 代码中没有 `get_part_by_tex`、`select_part`、`select_parts`、`get_part_by_text`。
- 所有中文都在 `Text(..., font="PingFang SC")` 中。
- 所有公式变量/数字若需要高亮，都是独立对象。
- 所有旁白 key 在 `narrations`、`NARRATION_SEGMENTS`、`start_voiceover` 中一致。
- 代码只使用 ManimGL API，不使用 Manim CE API。

下面开始你的任务。
"""
