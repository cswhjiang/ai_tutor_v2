# import asyncio
# import uuid
# from typing_extensions import override
from typing import AsyncGenerator, List

# from google.adk.agents import LlmAgent
from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
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
from src.agents.experts.deep_research.query_agent import DRQueryAgent
from src.agents.experts.deep_research.search_agent import DRSearchAgent
from src.agents.experts.deep_research.extract_worker_agent import DRExtractorAgent
from src.agents.experts.deep_research.report_agent import DRReportAgent

# from src.agents.experts.deep_research.tool import ddgs_text_search



# available_agents: str = '\n'.join([str(expert) for expert in sub_agents if expert.enable])
#
# async def deep_research_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
#     """
#     构造发送给model的信息
#     """
#     current_parameters = callback_context.state.get('current_parameters', {})
#
#     llm_request.contents.append(Content(role='user', parts=[Part(text=f"当前deer research的任务是：{current_parameters['task_query']}")]))
#
#     if len(current_parameters.get('input_name', [])) == 0:
#         return
#
#     return
#
#
# class DeepResearchAgent(BaseAgent):
#     llm: LlmAgent
#
#     def __init__(
#             self,
#             name: str,
#             description: str = '',
#             llm_model: str = ''
#     ):
#         if not llm_model:
#             llm_model = SYS_CONFIG.llm_model
#         logger.info(f"DeepResearchAgent: using llm: {llm_model}")
#         description = "专业的搜索专家和报告书写专家，可以根据用户需求搜索信息，并输出一个报告给用户。"
#
#         if 'gemini' not in llm_model:
#             if 'gpt-5' in llm_model:
#                 llm_model = LiteLlm(model=llm_model, extra_body={"reasoning_effort": "low"})
#             else:
#                 llm_model = LiteLlm(model=llm_model)
#
#         code_writer_agent = LlmAgent(
#             name="CodeWriterAgent",
#             model=GEMINI_MODEL,
#             # Change 3: Improved instruction
#             instruction="""You are a Python Code Generator.
#         Based *only* on the user's request, write Python code that fulfills the requirement.
#         Output *only* the complete Python code block, enclosed in triple backticks (```python ... ```).
#         Do not add any other text before or after the code block.
#         """,
#             description="Writes initial Python code based on a specification.",
#             output_key="generated_code"  # Stores output in state['generated_code']
#         )
#
#         # llm无法获取session中之前的content
#         llm = LlmAgent(
#             name=name,
#             model=llm_model,
#             description=description,
#             instruction=deep_research_instruction,
#             tools=[ddgs_text_search],
#             before_model_callback=deep_research_before_model_callback
#         )
#
#         super().__init__(
#             name=name,
#             description=description,
#             llm=llm,
#         )
#
#     async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
#         """
#         从state中读取参数：requirement
#         输出：文本形式的报告，具体的返回通道：
#          - 中途的content：llm每一步输出会通过event添加到主session
#          - state：llm生成所有回复后，所有的文本会被保存的state.current_output.output_text中
#         """
#         current_parameters = ctx.session.state.get('current_parameters', {})
#         if 'task_query' not in current_parameters:
#             error_text = f"提供给{self.name}的参数缺失，必须包含：task_query"
#             current_output = {"status": "error", "message": error_text}
#             logger.error(error_text)
#
#             yield Event(
#                 author=self.name,
#                 content=Content(role='model', parts=[Part(text=error_text)]),
#                 actions=EventActions(state_delta={"current_output": current_output})
#             )
#             return
#
#         text_list = []
#         async for event in self.llm.run_async(ctx):
#             if event.is_final_response() and event.content and event.content.parts:
#                 generated_text = next((part.text for part in event.content.parts if part.text), None)
#                 if not generated_text:
#                     continue
#                 yield event  # 模型生成的回复会被添加到content中
#                 text_list.append(generated_text)
#
#         if len(text_list) == 0:
#             message = f"DeepResearchAgent生成回复失败"
#             logger.error(message)
#             current_output = {'status': 'error', 'message': message}
#         else:
#             message = f"DeepResearchAgent已完成方案设计"
#             output_text = '\n'.join(text_list)
#             current_output = {'status': 'success', 'message': message, 'output_text': output_text}
#
#         yield Event(
#             author='DeepResearchAgent',
#             content=Content(role='model', parts=[Part(text=message)]),
#             actions=EventActions(state_delta={'current_output': current_output})
#         )
#
#
# deep_research_instruction = """
# 你是一个专业的搜索专家，你会接受用户输入的一个任务需求描述。你的任务是根据需求，生成一个详尽的报告。
#
# # 任务输入
#  - 任务需求：用户描述的任务需求
#
# # 任务输出
#  - 报告：详细的报告
#
# # 任务步骤（严格遵守）
# 首先你需要理解用户的任务，以及需要输出的信息元素，然后分如下的两个步骤输出：
# 第一步：输出一个具体的规划执行方案，要求md格式，包含对每个步骤的详细说明。
# 第二步：参考上一步生成的规划步骤，完成最终的报告。
#
# 在执行的时候可以使用你配备有的工具。
# """

deep_research_agent = SequentialAgent(
    name="DeepResearchAgent",
    sub_agents=[DRQueryAgent(name="DRQueryAgent"), # 包含了 query生成
                DRSearchAgent(name="DRSearchAgent"), #  并行搜索、并行提取
                DRReportAgent(name="DRReportAgent")]
)