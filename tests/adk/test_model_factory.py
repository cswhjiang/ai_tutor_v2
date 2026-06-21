from conf.system import AgentLLMConfig
from src.llm.model_factory import (
    SYS_CONFIG,
    _resolve_gemini_thinking_level,
    resolve_agent_llm_settings,
)


def test_resolve_gemini_thinking_level_uses_per_call_effort():
    assert _resolve_gemini_thinking_level("low") == "LOW"
    assert _resolve_gemini_thinking_level("minimal") == "MINIMAL"


def test_resolve_gemini_thinking_level_accepts_explicit_level_name():
    assert _resolve_gemini_thinking_level("HIGH") == "HIGH"


def test_resolve_agent_llm_settings_uses_per_agent_config(monkeypatch):
    monkeypatch.setattr(
        SYS_CONFIG,
        "agent_llm_configs",
        {
            "CodeGenerationAgent": AgentLLMConfig(
                llm_model="openai/gpt-5.5",
                reasoning_level="high",
            )
        },
    )

    assert resolve_agent_llm_settings(
        "gemini/gemini-3.5-flash",
        agent_name="CodeGenerationAgent",
        reasoning_effort="low",
    ) == ("openai/gpt-5.5", "high")


def test_resolve_agent_llm_settings_keeps_fallback_without_agent_config(monkeypatch):
    monkeypatch.setattr(SYS_CONFIG, "agent_llm_configs", {})

    assert resolve_agent_llm_settings(
        "gemini/gemini-3.5-flash",
        agent_name="UnknownAgent",
        reasoning_effort="medium",
    ) == ("gemini/gemini-3.5-flash", "medium")
