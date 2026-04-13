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
from src.agents.experts.ppt_v2.ppt_draft_agent import PPTDraftAgent
from src.agents.experts.ppt_v2.ppt_image_generation_agent import PPTImageGenerationAgent
from src.agents.experts.ppt_v2.ppt_finalize_agent import PPTFinalizeAgent
from src.agents.experts.ppt_v2.ppt_html_to_png_pptx import HTMLToImageAndPPTXAgent

# TODO: 透明图像处理、美化。PptxGenJS、Reveal.js
ppt_generation_agent_v2 = SequentialAgent(
    name="PPTGenerationAgentv2",
    sub_agents=[PPTDraftAgent(name="PPTDraftAgent"),
                PPTImageGenerationAgent(name="PPTImageGenerationAgent"),
                PPTFinalizeAgent(name="PPTFinalizeAgent"),
                HTMLToImageAndPPTXAgent(name='HTMLToImageAndPPTXAgent')
                ]
)