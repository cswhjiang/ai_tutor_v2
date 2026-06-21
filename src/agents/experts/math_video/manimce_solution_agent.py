import datetime
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.genai.types import Content, Part

from conf.system import SYS_CONFIG
from src.llm.model_factory import build_model_kwargs, resolve_agent_llm_settings
from src.logger import logger
from src.observability.timing import timing_context_from_invocation, timing_stage


MANIMCE_SOLUTION_KEY = "math_video/manimce_solution"


async def manimce_solution_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Build the model request for ManimCE solution generation."""
    current_parameters = callback_context.state.get("current_parameters", {})
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

    input_img_name = current_parameters.get("input_img_name", [])
    if input_img_name:
        artifact_parts = [Part(text="以下是和任务相关的图片：\n")]
        for i, art_name in enumerate(input_img_name):
            artifact_parts.append(Part(text=f"这是第{i + 1}张图片，它的名称是{art_name}"))
            art_part = await callback_context.load_artifact(filename=art_name)
            artifact_parts.append(art_part)
        llm_request.contents.append(Content(role="user", parts=artifact_parts))


class ManimCESolutionAgent(BaseAgent):
    """Generate the math solution used by the ManimCE route."""

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
            instruction=MANIMCE_SOLUTION_INSTRUCTION.format(TIME_STR=time_str),
            before_model_callback=manimce_solution_before_model_callback,
            output_key=MANIMCE_SOLUTION_KEY,
        )
        super().__init__(name=name, description=description, llm=llm)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the ManimCE solution agent and publish a step status event."""
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
            metadata={"mode": "manimce_math_video"},
        ) as agent_timing:
            text_list = []
            with timing_stage(
                "llm",
                f"{self.name}.llm",
                **timing_context,
                metadata={"output_key": MANIMCE_SOLUTION_KEY},
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


MANIMCE_SOLUTION_INSTRUCTION = """
你是一个理科、工科、工程方面的天才，擅长数学、物理、化学、生物、计算机等问题的解答。
你会接受用户输入的一个理工科任务或者一个问题，有时还会有数量不定的相关图片。
你的任务是根据任务描述和参考给定信息来输出答案。

你的答案会被用来给用户解释这个问题。

# 必要信息
 - 当前时间：{TIME_STR}


# 任务输入
 - 问题：生成用户描述的理工科相关的任务
 - 图片：数量不定的用于相关的图片，可选项。


# 任务输出
任务的输出为文本，按步骤呈现，易懂。输出需要包含正确的解题步骤，以及相关的解释。
结果以json形式输出出来。只包含如下两个字段：
 - solution: 当前问题的解题步骤，
 - explanation: 针对解题步骤的解释。

输出可以使用 latex，可以使用 $数学公式$，尽量避免其他形式，防止在llm的context中由于转义出现错误。但是不要有其他的字段。

----
下面开始你的任务
"""
