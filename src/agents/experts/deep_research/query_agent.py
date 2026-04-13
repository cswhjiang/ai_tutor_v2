# import asyncio
# import uuid
# from typing_extensions import override
import datetime
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

time_str = datetime.date.today().strftime("%Y-%m-%d")

async def dr_query_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
    """
    构造发送给model的信息
    """
    current_parameters = callback_context.state.get('current_parameters', {})

    input_text = f"当前 deep research 的任务是：{current_parameters['task_query']}\n"
    llm_request.contents.append(Content(role='user', parts=[Part(text=input_text)]))

    return


class DRQueryAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}
    llm: LlmAgent

    def __init__(
            self,
            name: str,
            description: str = '',
            llm_model: str = ''
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        logger.info(f"DRQueryAgent: using llm: {llm_model}")
        description = "可以根据用户的任务信息，分析并输出需要搜索的query列表。"

        model_kwargs = build_model_kwargs(llm_model)

        # llm无法获取session中之前的content
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            include_contents='none',
            instruction=dr_search_query_instruction.format(TIME_STR=time_str),
            before_model_callback=dr_query_before_model_callback,
            output_key= "deep_research/query_list"
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
            current_output = {"status": "error", "message": error_text}
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
            message = "DRQueryAgent 生成回复失败"
            message_for_user = "生成回复失败"
            logger.error(message)
            current_output = {"author": self.name, 'status': 'error', 'message': message, 'message_for_user':message_for_user, 'output_text': ''}
        else:
            message = "DRQueryAgent 已完成长文本分析和相关信息总结"
            message_for_user = "已完成长文本分析和相关信息总结"
            output_text = '\n'.join(text_list)
            current_output = {"author": self.name, 'status': 'success', 'message': message, 'message_for_user':message_for_user, 'output_text': output_text}

        yield Event(
            author='DRQueryAgent',
            content=Content(role='model', parts=[Part(text=message)]),
            actions=EventActions(state_delta={'current_output': current_output}) # 那个信息会放在output_key中？
        )


dr_search_query_instruction = """
# 角色和任务
你是一个专业搜索专家，你擅长用搜索引擎来解决用户的问题。

你的任务是根据用户的任务要求，生成一个需要搜索的query列表。

# 任务输入
 - 任务描述：用户的任务的描述

# 任务输出
 - 摘要：需要搜索的query列表。

# 任务步骤（严格遵守）

只以json格式输出你认为需要搜索的query列表，格式为以英文逗号隔开的列表，不需要有其他信息，也不需要解释，举例：
把结果放在json里面，如下所示：
["keyword1", "keyword2", "keyword3 keyword4"] 



# 特别注意
1. 不要有遗漏
2. 不要输出搜索意义不大的query。比如：你已经了解的、常识类的等等。
3. 不要输出不确定的信息
4. query 的语言限定为中文或者英文。仅仅搜索中文的query可能信息不完备。
5. 可以使用搜索引擎的技巧，比如
  - site: 限定网站范围
  - filetype: 查找特定文件类型
  - intitle: 仅搜索标题中包含的词

# query的例子
1. query 可以是单独的一个关键词，比如： `女装`
2. query 可以是几个相关的关键词一起，用空格隔开，比如：'纽约 女装'


# 必要信息
 - 当前时间：{TIME_STR}

下面开始任务

"""

