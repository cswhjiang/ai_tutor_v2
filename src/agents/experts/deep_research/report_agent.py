# import asyncio
# import uuid
# from typing_extensions import override
from typing import AsyncGenerator, List

# from google.adk.agents import LlmAgent
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from google.adk.models import LlmRequest
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Part
from google.genai.types import Content

from conf.system import SYS_CONFIG
from src.logger import logger
from src.llm.model_factory import build_model_kwargs


async def report_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
    """
    构造发送给model的信息
    """
    current_parameters = callback_context.state.get('current_parameters', {})

    input_text = f"当前 deep research 的任务是：{current_parameters['task_query']}\n"
    llm_request.contents.append(Content(role='user', parts=[Part(text=input_text)]))

    input_text = "当前任务需要处理的长文本是：\n"
    # for k, v in callback_context.state.items():  # TODO: items 出错
    #     if k.startswith("deep_research/extract_result"):
    #         input_text = input_text + v + '\n\n'

    for i in range(1000):
        t = callback_context.state.get(f'deep_research/extract_result_{i}', '')
        if len(t) == 0:
            continue
        else:
            input_text = input_text + f'worker {i} 的搜索结果经过总结为：\n' +  t + '\n  ----  \n'

    llm_request.contents.append(Content(role='user', parts=[Part(text=input_text)]))

    logger.info(input_text)
    logger.info(llm_request)

    return


class DRReportAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}
    llm: LlmAgent

    def __init__(
            self,
            name: str,
            description: str = '',
            llm_model: str = '',
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        logger.info(f"DRReportAgent: using llm: {llm_model}")
        # description = "根据用户的任务信息，分析搜索得到的长文本，提取出来里面和任务相关的要点信息。"

        model_kwargs = build_model_kwargs(llm_model)

        # llm无法获取session中之前的content
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            include_contents='none',
            instruction=report_instruction,
            before_model_callback=report_before_model_callback
        )

        super().__init__(
            name=name,
            description=description,
            llm=llm,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        从state中读取参数：requirement
        输出：文本形式的设计方案，具体的返回通道：
         - 中途的content：llm每一步输出会通过event添加到主session
         - state：llm生成所有回复后，所有的文本会被保存的state.current_output.output_text中
        """
        current_parameters = ctx.session.state.get('current_parameters', {})
        if 'task_query' not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：task_query"
            current_output = {"author": self.name, "status": "error", "message": error_text, 'output_text':''}
            logger.error(error_text)

            yield Event(
                author=self.name,
                content=Content(role='model', parts=[Part(text=error_text)]),
                actions=EventActions(state_delta={"current_output": current_output})
            )
            return

        text_list = []
        async for event in self.llm.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                generated_text = next((part.text for part in event.content.parts if part.text), None)
                if not generated_text:
                    continue
                yield event  # 模型生成的回复会被添加到content中
                text_list.append(generated_text)

        if len(text_list) == 0:
            message = f"ExtractorAgent 生成回复失败"
            message_for_user = "生成回复失败"
            logger.error(message)
            current_output = {"author": self.name, 'status': 'error', 'message': message, 'message_for_user':message_for_user, 'output_text':''}
        else:
            message = f"ExtractorAgent 已完成长文本分析和相关信息总结"
            message_for_user = "已完成长文本分析和相关信息总结"
            output_text = '\n'.join(text_list)
            current_output = {"author": self.name, 'status': 'success', 'message': message, 'message_for_user':message_for_user, 'output_text': output_text}

        yield Event(
            author='ExtractorAgent',
            content=Content(role='model', parts=[Part(text=message)]),
            actions=EventActions(state_delta={'current_output': current_output})
        )


report_instruction = """
你是一个专业的报告撰写专家。

你的任务是根据用户的任务要求和从搜索引擎中搜索&总结的多份信息，总结输出一个报告。

# 任务输入
 - 任务描述：用户的任务的描述
 - 搜索总结结果：一般是搜索的结果，几篇文章的总结结果。

# 任务输出
 - 报告：和用户任务相关的所有信息。

# 输出形式 
 - 形式：输出以md格式输出
 - 只输出md形式的结果，不需要其他的解释和说明。


# 特别注意
1. 不要有遗漏
2. 不要输出不确定的信息

下面开始任务
"""

