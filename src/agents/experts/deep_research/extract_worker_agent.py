# import asyncio
# import uuid
# from typing_extensions import override
from typing import AsyncGenerator, List
from functools import partial

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

# 从 deep_research/search_output_{run_id} 读取搜索结果
async def extractor_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest, run_id: int):
    """
    构造发送给model的信息
    """
    current_parameters = callback_context.state.get('current_parameters', {})
    search_output = callback_context.state.get(f'deep_research/search_output_{run_id}', '')

    input_text = f"当前的任务是：{current_parameters['task_query']}\n需要处理的搜索文本是：{search_output}"
    llm_request.contents.append(Content(role='user', parts=[Part(text=input_text)]))


    # for debug
    deep_research_query_list = callback_context.state.get('deep_research/query_list', "")

    logger.info(deep_research_query_list)
    logger.info(search_output)

    return


class DRExtractorAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}
    run_id: int = 0
    llm: LlmAgent

    def __init__(
            self,
            name: str,
            description: str = '',
            llm_model: str = '',
            run_id: int = 0
    ):

        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        logger.info(f"DRExtractorAgent: using llm: {llm_model}")
        # description = "根据用户的任务信息，分析搜索得到的长文本，提取出来里面和任务相关的要点信息。"

        model_kwargs = build_model_kwargs(llm_model)

        # llm无法获取session中之前的content
        extractor_before_model_callback_partial = partial(extractor_before_model_callback, run_id=run_id )
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            include_contents='none',
            instruction=dr_extractor_instruction,
            before_model_callback=extractor_before_model_callback_partial,
            # input_key=f"deep_research/search_output_{run_id}",
            output_key=f"deep_research/extract_result_{run_id}"
        )

        super().__init__(
            name=name,
            description=description,
            llm=llm,
            run_id=run_id
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        从state中读取参数：requirement
        输出：文本形式的设计方案，具体的返回通道：
         - 中途的content：llm每一步输出会通过event添加到主session
         - state：llm生成所有回复后，所有的文本会被保存的state.current_output.output_text中
        """
        current_parameters = ctx.session.state.get('current_parameters', {})
        if 'task_query' not in current_parameters :
            error_text = f"提供给{self.name}的参数缺失，必须包含：task_query 和 search_result"
            current_output = {"author": self.name, "status": "error", "message": error_text, 'output_text':''}
            logger.error(error_text)

            yield Event(
                author=self.name,
                content=Content(role='model', parts=[Part(text=error_text)]),
                actions=EventActions(state_delta={f"current_output_{self.run_id}": current_output})
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
            message = "DRExtractorAgent 生成回复失败"
            message_for_user = "生成回复失败"
            logger.error(message)
            current_output = {"author": self.name, 'status': 'error', 'message': message, 'message_for_user':message_for_user, 'output_text':''}
        else:
            message = "DRExtractorAgent 已完成长文本分析和相关信息总结"
            message_for_user = "已完成长文本分析和相关信息总结"
            output_text = '\n'.join(text_list)
            current_output = {"author": self.name, 'status': 'success', 'message': message, 'message_for_user':message_for_user, 'output_text': output_text}

        yield Event(
            author='DRExtractorAgent',
            content=Content(role='model', parts=[Part(text=message)]),
            actions=EventActions(state_delta={f'current_output_{self.run_id}': current_output})
        )
        return


dr_extractor_instruction = """
你是一个专业的文本分析、提取和总结专家。

你的任务是根据用户的任务要求，分析一个长文本（一般情况下是搜索的结果，也就是几篇文章），并提取里面和用户任务相关的信息，然后总结输出出来。

# 任务输入
 - 任务描述：用户的任务的描述
 - 长文本：一般是搜索的结果，几篇文章。

# 任务输出
 - 摘要：和用户任务相关的所有信息。
 - 形式：输出以md格式输出。可以选择以表格形式总结主要的信息。

# 任务步骤（严格遵守）
首先你需要理解用户的任务，然后分如下的两个步骤输出：
第一步：先分析用户的任务需求，明确相关的事项
第二步：分析长文本并输出相关信息

# 特别注意
1. 不要有遗漏
2. 不要输出不确定的信息

下面开始任务
"""

