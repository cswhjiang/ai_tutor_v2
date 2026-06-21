import pytest

from src.agents.experts.math_video.manimgl_render_agent import (
    extract_voiceover_keys,
    inject_narration_audio,
    parse_manimgl_generation_output,
    normalize_narration_segments,
    ready_file_path_from_line,
    sanitize_path_part,
    validate_voiceover_references,
)


def test_normalize_narration_segments_deduplicates_keys():
    segments = normalize_narration_segments(
        [
            {"key": "intro", "text": "第一段"},
            {"key": "intro", "text": "第二段"},
            "第三段",
        ]
    )

    assert [segment["key"] for segment in segments] == [
        "intro",
        "intro_02",
        "narration_03",
    ]


def test_parse_manimgl_generation_output_accepts_adk_schema_dict():
    raw_output = {
        "scene_name": "ThreeColorBalls",
        "manimgl_code": "from manimlib import *\n",
        "narrations": [{"key": "intro", "text": "题目开场"}],
    }

    assert parse_manimgl_generation_output(raw_output) is raw_output


def test_parse_manimgl_generation_output_keeps_string_json_strict():
    valid_json = (
        '{"scene_name": "ThreeColorBalls", '
        '"manimgl_code": "from manimlib import *\\n", '
        '"narrations": []}'
    )
    invalid_json = valid_json + "}"

    assert parse_manimgl_generation_output(valid_json)["scene_name"] == "ThreeColorBalls"
    with pytest.raises(ValueError):
        parse_manimgl_generation_output(invalid_json)


def test_inject_narration_audio_replaces_placeholder():
    code = "from manimlib import *\nNARRATION_AUDIO = {}\n"
    injected = inject_narration_audio(
        code,
        {"intro": {"file": "voiceover_intro.mp3", "duration": 2.5}},
    )

    assert "NARRATION_AUDIO = {}" not in injected
    assert "voiceover_intro.mp3" in injected
    assert "'duration': 2.5" in injected


def test_inject_narration_audio_uses_python_literals():
    code = "from manimlib import *\nNARRATION_AUDIO = {}\n"
    injected = inject_narration_audio(
        code,
        {
            "intro": {
                "file": "voiceover_intro.mp3",
                "duration": None,
                "cache_hit": False,
            }
        },
    )

    assert "'cache_hit': False" in injected
    assert "'duration': None" in injected
    assert "false" not in injected
    assert "null" not in injected


def test_inject_narration_audio_requires_placeholder():
    with pytest.raises(ValueError):
        inject_narration_audio("from manimlib import *\n", {"intro": {}})


def test_validate_voiceover_references_requires_matching_narration_keys():
    code = 'duration = start_voiceover(self, "intro", 3.0)'

    assert extract_voiceover_keys(code) == {"intro"}
    validate_voiceover_references(code, [{"key": "intro", "text": "第一段"}])

    with pytest.raises(ValueError):
        validate_voiceover_references(code, [{"key": "other", "text": "第一段"}])


def test_ready_file_path_from_line_extracts_completed_video(tmp_path):
    video_path = tmp_path / "videos" / "00000.mp4"
    video_path.parent.mkdir()
    video_path.write_bytes(b"fake")

    assert ready_file_path_from_line(f"File ready at {video_path}", tmp_path) == video_path


def test_ready_file_path_from_line_handles_real_manimgl_log_suffix(tmp_path):
    video_path = tmp_path / "videos" / "ThreeColorBalls" / "00028.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"fake")
    line = (
        "ThreeColorBalls.mp4 28 WriteText: 76%| 34 /45 336.96it/s "
        f"[15:36:02] INFO File ready at {video_path} scene_file_writer.py:399"
    )

    assert ready_file_path_from_line(line, tmp_path) == video_path


def test_sanitize_path_part_removes_unsafe_characters():
    assert sanitize_path_part("user:session/id") == "user_session_id"
