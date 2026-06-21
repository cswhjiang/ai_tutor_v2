from pydantic import ValidationError
import pytest

from src.agents.experts.math_video.manimgl_code_generation_agent import (
    ManimGLCodeGenerationAgent,
    ManimGLCodeOutput,
)


def test_manimgl_code_generation_agent_uses_adk_output_schema():
    agent = ManimGLCodeGenerationAgent(name="ManimGLCodeGenerationAgent")

    assert agent.llm.output_schema is ManimGLCodeOutput


def test_manimgl_code_output_schema_requires_structured_fields():
    parsed = ManimGLCodeOutput.model_validate(
        {
            "scene_name": "ThreeColorBalls",
            "manimgl_code": "from manimlib import *\n",
            "narrations": [{"key": "intro", "text": "题目开场"}],
        }
    )

    assert parsed.scene_name == "ThreeColorBalls"
    assert parsed.narrations[0].key == "intro"

    with pytest.raises(ValidationError):
        ManimGLCodeOutput.model_validate(
            {
                "scene_name": "ThreeColorBalls",
                "manimgl_code": "from manimlib import *\n",
            }
        )
