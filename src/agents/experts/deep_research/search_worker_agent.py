# import asyncio
# import time
# from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, List, Dict
from typing_extensions import override
from typing import AsyncGenerator, Dict
from pydantic import BaseModel
import json

from asyncddgs import aDDGS
import trafilatura
from tavily import TavilyClient
from tavily import AsyncTavilyClient

from google.genai.types import Content
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.genai.types import Part, Blob

from conf.system import SYS_CONFIG
from src.logger import logger
# from src.agents.experts.deep_research.tool import ddgs_text_search

def get_text_from_url(url: str):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded) if downloaded else None


async def search_text(query):
    try:
        async with aDDGS() as ddgs:
            result = await ddgs.text(
                keywords=query,
                region='wt-wt',  # world wide
                max_results=10,
                timelimit='y'
            )
            for i, item in enumerate(result):
                url = item.get('href', 'no_url')
                if 'no_url' not in url:
                    text_content = get_text_from_url(url)
                    if text_content is not None and len(text_content) > 30 and not text_content.startswith('Error'):
                        result[i]['body'] = text_content
            message = f"找到{len(result)}条相关文本：\n\n"
            output_text = ''
            for i, item in enumerate(result):
                output_text += f"【结果{i + 1}】 标题：{item.get('title', '无标题')}，内容：{item.get('body', '无内容')}\n"

            return {
                "status": "success",
                "message": message,
                "output_text": output_text
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"duckduckgo-search error: {str(e)}",
            "output_text": output_text
        }

async def tavily_search_text(query):
    try:
        tavily_client = TavilyClient()
        # tavily_client = AsyncTavilyClient()
        response =  tavily_client.search(query=query, include_raw_content=True)
        # print(response)
        if response is not None:
            result = response['results']  # url、title、content

    except Exception as e:
        return {
            "status": "error",
            "message": f"tavily-search error: {str(e)}"
        }
    return {
        "status": "success",
        "message": result
    }



class DRSearchWorkerAgent(BaseAgent):
    # v2 写法：用 ConfigDict 或字典都行
    model_config = {"arbitrary_types_allowed": True}

    # 声明成字段（Pydantic 会允许设置/验证它）
    run_id: int = 0

    def __init__(self, name: str, description: str = "", run_id: int = 0):
        # 把 run_id 一起交给 pydantic 的初始化（不要手动 self.run_id = ...）
        super().__init__(name=name, description=description, run_id=run_id)

    def format_event(self, content_text: str = None, state_delta: Dict = None):
        event = Event(author=self.name)

        if state_delta: event.actions = EventActions(state_delta=state_delta)
        if content_text: event.content = Content(role='model', parts=[Part(text=content_text)])
        return event


    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """从query list 中取第 self.run_id 个query搜索。"""
        query_str = ctx.session.state.get('deep_research/query_list', '[]')  # 这里用字符串默认更安全
        query_list = json.loads(query_str)
        current_query = query_list[self.run_id]
        # search_output = await search_text(current_query)
        search_output = await tavily_search_text(current_query)

        yield self.format_event(
            search_output['message'],
            {f"deep_research/search_output_{self.run_id}": search_output["output_text"]},
        )
        return

