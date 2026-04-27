from src.llm.model_factory import _resolve_gemini_thinking_level


def test_resolve_gemini_thinking_level_uses_per_call_effort():
    assert _resolve_gemini_thinking_level("low") == "LOW"
    assert _resolve_gemini_thinking_level("minimal") == "MINIMAL"


def test_resolve_gemini_thinking_level_accepts_explicit_level_name():
    assert _resolve_gemini_thinking_level("HIGH") == "HIGH"
