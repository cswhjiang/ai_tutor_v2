import pytest

from src.agents.experts.math_video import routes


def test_resolve_math_video_route_uses_system_default(monkeypatch):
    monkeypatch.setattr(routes.SYS_CONFIG, "math_video_generation_route", "manimgl")

    assert routes.resolve_math_video_route({}) == "manimgl"


def test_resolve_math_video_route_allows_explicit_override(monkeypatch):
    monkeypatch.setattr(routes.SYS_CONFIG, "math_video_generation_route", "manimce")

    assert routes.resolve_math_video_route({"math_video_mode": "fast"}) == "fast"
    assert routes.resolve_math_video_route({"use_fast": True}) == "fast"
    assert routes.resolve_math_video_route({"use_manimce": True}) == "manimce"


def test_resolve_math_video_route_rejects_unknown_route():
    with pytest.raises(ValueError):
        routes.resolve_math_video_route({"math_video_mode": "unknown"})
