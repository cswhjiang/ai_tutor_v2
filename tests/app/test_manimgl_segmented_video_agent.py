import asyncio
import json

import pytest

from src.agents.experts.math_video.manimgl_segmented_video_agent import (
    MANIMGL_SEGMENT_CODE_GENERATION_INSTRUCTION,
    MANIMGL_SEGMENT_RETRY_CONTEXT_KEY,
    ManimGLCodeValidationError,
    ManimGLSegmentCodeOutput,
    concat_segment_videos,
    manimgl_segment_code_before_model_callback,
    normalize_manimgl_shots,
    parse_manimgl_segment_code_output,
    validate_manimgl_code_symbols,
)


def test_normalize_manimgl_shots_builds_semantic_segments_from_json_string():
    raw_design = json.dumps(
        {
            "title": "三色球",
            "style": {"background": "dark"},
            "summary": "最终答案",
            "shots": [
                {
                    "narration_key": "intro",
                    "duration_seconds": 3,
                    "narration": "先看题目。",
                    "objects": ["title"],
                },
                {
                    "narration_key": "intro",
                    "duration_seconds": 50,
                    "narration": "再列方程。",
                    "objects": ["equations"],
                },
            ],
        },
        ensure_ascii=False,
    )

    shots = normalize_manimgl_shots(raw_design)

    assert [shot["narration_key"] for shot in shots] == ["intro", "intro_02"]
    assert shots[0]["duration_seconds"] == 4.0
    assert shots[1]["duration_seconds"] == 30.0
    assert shots[0]["title"] == "三色球"
    assert shots[1]["shot"]["objects"] == ["equations"]


def test_parse_manimgl_segment_code_output_accepts_schema_dict_and_json_string():
    raw_output = {
        "scene_name": "SegmentOne",
        "manimgl_code": "from manimlib import *\n",
        "narrations": [{"key": "intro", "text": "第一段"}],
    }

    assert parse_manimgl_segment_code_output(raw_output) is raw_output
    assert parse_manimgl_segment_code_output(json.dumps(raw_output))["scene_name"] == "SegmentOne"


def test_manimgl_segment_code_schema_requires_structured_fields():
    parsed = ManimGLSegmentCodeOutput.model_validate(
        {
            "scene_name": "SegmentOne",
            "manimgl_code": "from manimlib import *\n",
            "narrations": [{"key": "intro", "text": "第一段"}],
        }
    )

    assert parsed.scene_name == "SegmentOne"
    assert parsed.narrations[0].key == "intro"


def test_manimgl_segment_prompt_keeps_voiceover_and_segment_contract():
    prompt = MANIMGL_SEGMENT_CODE_GENERATION_INSTRUCTION

    assert "只生成一个" in prompt
    assert "NARRATION_AUDIO = {}" in prompt
    assert "start_voiceover" in prompt
    assert "不要生成完整视频的所有片段" in prompt
    assert "get_part_by_tex" in prompt
    assert "TransformFromParagraph" in prompt
    assert "只允许使用下列动画类" in prompt


def test_validate_manimgl_code_symbols_rejects_unsupported_animation():
    code = """
from manimlib import *

class BadScene(Scene):
    def construct(self):
        self.play(TransformFromParagraph(Text("a"), Text("b")))
"""

    with pytest.raises(ManimGLCodeValidationError, match="TransformFromParagraph"):
        validate_manimgl_code_symbols(code)


def test_validate_manimgl_code_symbols_accepts_basic_segment_code():
    code = """
from manimlib import *

class GoodScene(Scene):
    def construct(self):
        title = Text("题目", font="PingFang SC")
        circle = Circle()
        self.play(Write(title), ShowCreation(circle))
        self.play(ReplacementTransform(circle, Dot()))
"""

    validate_manimgl_code_symbols(code)


class FakeCallbackContext:
    def __init__(self, state):
        self.state = state


class FakeLlmRequest:
    def __init__(self):
        self.contents = []


def joined_request_text(request: FakeLlmRequest) -> str:
    return "\n".join(
        part.text
        for content in request.contents
        for part in content.parts
        if part.text
    )


def test_segment_code_callback_includes_retry_context():
    request = FakeLlmRequest()
    context = FakeCallbackContext(
        {
            "current_parameters": {"prompt": "题目", "current_info": "null"},
            "math_video/manimgl_current_segment": {
                "index": 2,
                "total": 5,
                "narration": "第二段",
            },
            MANIMGL_SEGMENT_RETRY_CONTEXT_KEY: {
                "error": "unsupported ManimGL symbol: TransformFromParagraph",
                "previous_code": "self.play(TransformFromParagraph(a, b))",
            },
        }
    )

    asyncio.run(manimgl_segment_code_before_model_callback(context, request))
    text = joined_request_text(request)

    assert "上一次生成的当前片段代码没有通过校验或渲染" in text
    assert "TransformFromParagraph" in text
    assert "previous_code" not in text


def test_concat_segment_videos_copies_single_segment(tmp_path):
    source = tmp_path / "segment_0001.mp4"
    output = tmp_path / "final.mp4"
    source.write_bytes(b"fake mp4")

    result = asyncio.run(concat_segment_videos([source], output))

    assert result["method"] == "copy_single"
    assert output.read_bytes() == b"fake mp4"
