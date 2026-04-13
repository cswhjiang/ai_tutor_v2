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

from src.agents.experts.math_video.solution_agent import SolutionAgent
from src.agents.experts.math_video.shot_agent import ShotAgent
from src.agents.experts.math_video.code_generation_agent import CodeGenerationAgent
from src.agents.experts.math_video.render_agent import RenderAgent

math_video_generation_agent = SequentialAgent(
    name="MathVideoGenerationAgent",
    sub_agents=[SolutionAgent(name="SolutionAgent"),
                ShotAgent(name="ShotAgent"),
                CodeGenerationAgent(name="CodeGenerationAgent"),
                RenderAgent(name='RenderAgent')
                ]
)