from google.adk.agents import SequentialAgent

from conf.agent import expert_name_2_desc
from src.agents.experts.math_video.code_generation_agent import CodeGenerationAgent
from src.agents.experts.math_video.fast_math_video_agent import FastMathVideoGenerationAgent
from src.agents.experts.math_video.manimgl_code_generation_agent import ManimGLCodeGenerationAgent
from src.agents.experts.math_video.manimgl_render_agent import ManimGLRenderAgent
from src.agents.experts.math_video.render_agent import RenderAgent
from src.agents.experts.math_video.routed_math_video_agent import RoutedMathVideoGenerationAgent
from src.agents.experts.math_video.shot_agent import ShotAgent
from src.agents.experts.math_video.solution_agent import SolutionAgent


manimce_math_video_generation_agent = SequentialAgent(
    name="ManimCEMathVideoGenerationAgent",
    sub_agents=[
        SolutionAgent(name="SolutionAgent"),
        ShotAgent(name="ShotAgent"),
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
        SolutionAgent(name="SolutionAgent"),
        ShotAgent(name="ShotAgent"),
        ManimGLCodeGenerationAgent(name="ManimGLCodeGenerationAgent"),
        ManimGLRenderAgent(name="ManimGLRenderAgent"),
    ],
)

math_video_generation_agent = RoutedMathVideoGenerationAgent(
    name="MathVideoGenerationAgent",
    description=expert_name_2_desc.get("MathVideoGenerationAgent", ""),
    manimce_agent=manimce_math_video_generation_agent,
    fast_agent=fast_math_video_generation_agent,
    manimgl_agent=manimgl_math_video_generation_agent,
)
