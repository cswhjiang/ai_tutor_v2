from google.adk.agents import SequentialAgent

from conf.agent import expert_name_2_desc
from src.agents.experts.math_video.code_generation_agent import CodeGenerationAgent
from src.agents.experts.math_video.fast_math_video_agent import FastMathVideoGenerationAgent
from src.agents.experts.math_video.render_agent import RenderAgent
from src.agents.experts.math_video.shot_agent import ShotAgent
from src.agents.experts.math_video.solution_agent import SolutionAgent


legacy_math_video_generation_agent = SequentialAgent(
    name="MathVideoGenerationAgent",
    sub_agents=[
        SolutionAgent(name="SolutionAgent"),
        ShotAgent(name="ShotAgent"),
        CodeGenerationAgent(name="CodeGenerationAgent"),
        RenderAgent(name="RenderAgent"),
    ],
)

math_video_generation_agent = FastMathVideoGenerationAgent(
    name="MathVideoGenerationAgent",
    description=expert_name_2_desc.get("MathVideoGenerationAgent", ""),
    legacy_agent=legacy_math_video_generation_agent,
)
