# import asyncio
# import time
# from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, List, Dict
from typing_extensions import override
import json
from google.genai import types
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
from google.genai import types


from conf.system import SYS_CONFIG
from src.logger import logger
from src.agents.experts.deep_research.search_worker_agent import DRSearchWorkerAgent
from src.agents.experts.deep_research.extract_worker_agent import DRExtractorAgent


class DRSearchAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name: str, description: str = '', ):
        description = ""

        super().__init__(name=name, description=description)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """

        """
        query_str = ctx.session.state.get('deep_research/query_list', '')
        query_list = json.loads(query_str)
        N = len(query_list)

        yield Event(
            author=self.name,
            content=types.Content(role=self.name, parts=[types.Part(text=f"Run deep research tasks with {N} workers with query {query_list}.")]),
        )

        sequential_agent_list = []
        for i in range(N):
            temp = [DRSearchWorkerAgent(name=f"ds_search_worker_{i}", run_id=i),
                    DRExtractorAgent(name=f"ds_extract_worker_{i}", run_id=i)
                    ]
            sequential_agent_list.append(SequentialAgent(name=f'search_and_extract_id_{i}', sub_agents=temp))

        parallel = ParallelAgent(name='ds_search_and_extract_parallel',
            sub_agents=sequential_agent_list
        )
        async for ev in parallel.run_async(ctx):
            yield ev








