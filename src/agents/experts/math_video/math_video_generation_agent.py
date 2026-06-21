from google.adk.agents import SequentialAgent

from conf.agent import expert_name_2_desc
from src.agents.experts.math_video.code_generation_agent import CodeGenerationAgent
from src.agents.experts.math_video.fast_math_video_agent import FastMathVideoGenerationAgent
from src.agents.experts.math_video.manimce_shot_agent import ManimCEShotAgent
from src.agents.experts.math_video.manimce_solution_agent import ManimCESolutionAgent
from src.agents.experts.math_video.manimgl_segmented_video_agent import (
    ManimGLSegmentedVideoAgent,
)
from src.agents.experts.math_video.manimgl_shot_agent import ManimGLShotAgent
from src.agents.experts.math_video.manimgl_solution_agent import ManimGLSolutionAgent
from src.agents.experts.math_video.render_agent import RenderAgent
from src.agents.experts.math_video.routed_math_video_agent import RoutedMathVideoGenerationAgent


manimce_math_video_generation_agent = SequentialAgent(
    name="ManimCEMathVideoGenerationAgent",
    sub_agents=[
        ManimCESolutionAgent(name="ManimCESolutionAgent"),
        ManimCEShotAgent(name="ManimCEShotAgent"),
        CodeGenerationAgent(name="CodeGenerationAgent"),
        RenderAgent(name="RenderAgent"),
    ],
)

fast_math_video_generation_agent = FastMathVideoGenerationAgent(
    name="FastMathVideoGenerationAgent",
    description=expert_name_2_desc.get("MathVideoGenerationAgent", ""),
)

manimgl_math_video_generation_agent = SequentialAgent(
    name="ManimGLMathVideoGenerationAgent",
    sub_agents=[
        ManimGLSolutionAgent(name="ManimGLSolutionAgent"),
        ManimGLShotAgent(name="ManimGLShotAgent"),
        ManimGLSegmentedVideoAgent(name="ManimGLSegmentedVideoAgent"),
    ],
)

math_video_generation_agent = RoutedMathVideoGenerationAgent(
    name="MathVideoGenerationAgent",
    description=expert_name_2_desc.get("MathVideoGenerationAgent", ""),
    manimce_agent=manimce_math_video_generation_agent,
    fast_agent=fast_math_video_generation_agent,
    manimgl_agent=manimgl_math_video_generation_agent,
)
