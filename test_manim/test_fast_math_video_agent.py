from src.agents.experts.math_video.fast_math_video_agent import should_use_fast_math_video


def test_math_video_defaults_to_legacy_path():
    assert should_use_fast_math_video({}) is False
    assert should_use_fast_math_video({"math_video_mode": "legacy"}) is False
    assert should_use_fast_math_video({"use_legacy": True}) is False


def test_math_video_fast_path_requires_explicit_request():
    assert should_use_fast_math_video({"math_video_mode": "fast"}) is True
    assert should_use_fast_math_video({"use_fast": True}) is True
    assert should_use_fast_math_video({"use_fast": "true"}) is True


def test_math_video_use_legacy_overrides_fast_request():
    assert should_use_fast_math_video(
        {"math_video_mode": "fast", "use_legacy": True}
    ) is False
