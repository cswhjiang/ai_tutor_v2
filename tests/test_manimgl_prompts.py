from src.agents.experts.math_video.manimgl_code_generation_agent import (
    MANIMGL_CODE_GENERATION_INSTRUCTION,
)
from src.agents.experts.math_video.manimgl_shot_agent import MANIMGL_SHOT_INSTRUCTION


def test_manimgl_shot_prompt_requires_code_oriented_safe_plan():
    prompt = MANIMGL_SHOT_INSTRUCTION

    assert "narration_key" in prompt
    assert "duration_seconds" in prompt
    assert "manimgl_notes" in prompt
    assert "公式必须说明拆成独立对象" in prompt
    assert "get_part_by_tex" in prompt
    assert "select_part" in prompt


def test_manimgl_code_prompt_bans_fragile_tex_selection():
    prompt = MANIMGL_CODE_GENERATION_INSTRUCTION

    assert "禁止使用 `get_part_by_tex`" in prompt
    assert "select_parts" in prompt
    assert "IndexError" in prompt
    assert "equation_row" in prompt
    assert "所有公式变量/数字若需要高亮，都是独立对象" in prompt


def test_manimgl_code_prompt_keeps_voiceover_contract():
    prompt = MANIMGL_CODE_GENERATION_INSTRUCTION

    assert "NARRATION_AUDIO = {}" in prompt
    assert "NARRATION_SEGMENTS" in prompt
    assert "start_voiceover" in prompt
    assert "narrations" in prompt
