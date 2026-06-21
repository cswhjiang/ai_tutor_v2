from src.agents.experts.math_video.fast_template_renderer import (
    FAST_FRAME_RATE,
    FAST_PIXEL_HEIGHT,
    FAST_PIXEL_WIDTH,
    FAST_SCENE_NAME,
    MAX_FAST_STEPS,
    build_fast_manim_code,
    collect_narration_segments,
    estimate_segment_durations,
    normalize_fast_video_script,
)


def test_normalize_fast_video_script_limits_and_fills_fields():
    script = {
        "title": "简单加法",
        "problem": "小明有4个苹果，又买了4个，一共有几个？",
        "steps": [
            {"heading": f"step-{index}", "explanation": f"explain-{index}"}
            for index in range(10)
        ],
        "answer": "8个",
    }

    normalized = normalize_fast_video_script(script, prompt="fallback prompt")

    assert normalized["title"] == "简单加法"
    assert len(normalized["steps"]) == MAX_FAST_STEPS
    assert normalized["steps"][0]["narration"] == "explain-0"
    assert normalized["summary"] == "结论：8个"


def test_collect_narration_segments_matches_template_order():
    normalized = normalize_fast_video_script(
        {
            "intro_narration": "intro",
            "steps": [
                {"heading": "one", "explanation": "e1", "narration": "n1"},
                {"heading": "two", "explanation": "e2", "narration": "n2"},
            ],
            "summary": "summary",
        },
        prompt="p",
    )

    assert collect_narration_segments(normalized) == ["intro", "n1", "n2", "summary"]


def test_estimate_segment_durations_stays_in_render_bounds():
    durations = estimate_segment_durations(["短", "a" * 500])

    assert durations == [2.2, 7.5]


def test_build_fast_manim_code_contains_quality_and_scene_name():
    normalized = normalize_fast_video_script(
        {
            "title": "两数相加",
            "problem": "4 + 4 = ?",
            "steps": [{"heading": "计算", "explanation": "把两个4相加", "equation": "4 + 4 = 8"}],
            "answer": "8",
            "summary": "同类数量直接相加。",
        },
        prompt="4 + 4 = ?",
    )
    durations = estimate_segment_durations(collect_narration_segments(normalized))

    code = build_fast_manim_code(normalized, durations)

    assert f"class {FAST_SCENE_NAME}(Scene):" in code
    assert f"config.pixel_width = {FAST_PIXEL_WIDTH}" in code
    assert f"config.pixel_height = {FAST_PIXEL_HEIGHT}" in code
    assert f"config.frame_rate = {FAST_FRAME_RATE}" in code
    assert "4 + 4 = 8" in code
