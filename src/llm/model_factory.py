from __future__ import annotations

from typing import Any, Optional

from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from conf.system import SYS_CONFIG


JSON_RESPONSE_MIME_TYPE = "application/json"


def is_gemini_model(model_name: str) -> bool:
    """Return True when the model string points to the Gemini family."""
    value = (model_name or "").lower().strip()
    return "gemini" in value


def _is_anthropic_model(model_name: str) -> bool:
    value = (model_name or "").lower().strip()
    return "anthropic" in value or value.startswith("claude")


def _supports_openai_reasoning_effort(model_name: str) -> bool:
    """Return True for OpenAI reasoning-capable model families."""
    value = (model_name or "").lower().strip()
    if value.startswith("openai/responses/"):
        value = value.removeprefix("openai/responses/")
    elif value.startswith("openai/"):
        value = value.removeprefix("openai/")

    return (
        value.startswith("gpt-5")
        or value.startswith("o1")
        or value.startswith("o3")
        or value.startswith("o4")
    )


def _normalize_gemini_model_name(model_name: str) -> str:
    """Convert LiteLLM-style Gemini names into native Gemini names."""
    value = (model_name or "").strip()
    if value.lower().startswith("gemini/"):
        return value.split("/", 1)[1]
    return value


def _normalize_model_for_litellm(model_name: str) -> str:
    """
    Normalize model name for LiteLLM endpoint routing.

    For OpenAI codex-like models, route through the LiteLLM responses bridge.
    """
    value = (model_name or "").strip()
    lower_name = value.lower()
    if lower_name.startswith("openai/responses/"):
        return value

    if lower_name.startswith("openai/"):
        provider, raw_model = value.split("/", 1)
        if "codex" in raw_model.lower():
            return f"{provider}/responses/{raw_model}"

    return value


def _resolve_gemini_thinking_level(reasoning_effort: Optional[str]) -> Optional[str]:
    """
    Resolve Gemini thinking level.

    A per-call reasoning effort takes precedence over the global setting so
    latency-sensitive agents can explicitly request a cheaper mode.
    """
    if reasoning_effort is not None:
        normalized_effort = reasoning_effort.strip().lower()
        effort_to_level = {
            "minimal": "MINIMAL",
            "low": "LOW",
            "medium": "MEDIUM",
            "high": "HIGH",
        }
        if normalized_effort in effort_to_level:
            return effort_to_level[normalized_effort]

        explicit_level = normalized_effort.upper()
        if explicit_level in types.ThinkingLevel.__members__:
            return explicit_level

        raise ValueError(f"Unsupported Gemini reasoning_effort: {reasoning_effort}")

    thinking_level = (SYS_CONFIG.gemini_thinking_level or "").strip().upper()
    return thinking_level or None


def _build_gemini_thinking_config(reasoning_effort: Optional[str] = None) -> Optional[types.ThinkingConfig]:
    """Build Gemini thinking config from per-call or system settings."""
    thinking_kwargs: dict[str, Any] = {}

    thinking_level = _resolve_gemini_thinking_level(reasoning_effort)
    if thinking_level:
        if thinking_level not in types.ThinkingLevel.__members__:
            raise ValueError(f"Unsupported gemini_thinking_level: {thinking_level}")
        thinking_kwargs["thinking_level"] = types.ThinkingLevel[thinking_level]

    if SYS_CONFIG.gemini_thinking_budget is not None:
        thinking_kwargs["thinking_budget"] = SYS_CONFIG.gemini_thinking_budget

    if not thinking_kwargs:
        return None

    return types.ThinkingConfig(**thinking_kwargs)


def _resolve_openai_reasoning_effort(reasoning_effort: Optional[str]) -> Optional[str]:
    """Resolve OpenAI reasoning effort, falling back to system config."""
    if reasoning_effort is None:
        reasoning_effort = SYS_CONFIG.openai_reasoning_effort

    if reasoning_effort is None:
        return None

    normalized_effort = reasoning_effort.strip().lower()
    return normalized_effort or None


def build_model_and_config(
    model_name: str,
    *,
    response_json: bool = False,
    reasoning_effort: Optional[str] = None,
) -> tuple[Any, Optional[types.GenerateContentConfig]]:
    """
    Build an ADK model instance and optional native Gemini config.

    Gemini models use the native ADK Gemini adapter so thinking config is
    handled by ADK directly. Other models continue to use LiteLLM.
    """
    if is_gemini_model(model_name):
        config_kwargs: dict[str, Any] = {}
        thinking_config = _build_gemini_thinking_config(reasoning_effort)
        if thinking_config is not None:
            config_kwargs["thinking_config"] = thinking_config
        if response_json:
            config_kwargs["response_mime_type"] = JSON_RESPONSE_MIME_TYPE

        generate_content_config = (
            types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        )
        return Gemini(model=_normalize_gemini_model_name(model_name)), generate_content_config

    normalized_model_name = _normalize_model_for_litellm(model_name)
    extra_body: dict[str, Any] = {}
    resolved_reasoning_effort = _resolve_openai_reasoning_effort(reasoning_effort)

    if resolved_reasoning_effort and _supports_openai_reasoning_effort(normalized_model_name):
        extra_body["reasoning_effort"] = resolved_reasoning_effort

    if response_json and not _is_anthropic_model(normalized_model_name):
        extra_body["response_format"] = {"type": "json_object"}

    if extra_body:
        return LiteLlm(model=normalized_model_name, extra_body=extra_body), None

    return LiteLlm(model=normalized_model_name), None


def build_model_kwargs(
    model_name: str,
    *,
    response_json: bool = False,
    reasoning_effort: Optional[str] = None,
) -> dict[str, Any]:
    """Return keyword arguments that can be passed directly to `LlmAgent`."""
    model, generate_content_config = build_model_and_config(
        model_name,
        response_json=response_json,
        reasoning_effort=reasoning_effort,
    )
    model_kwargs = {"model": model}
    if generate_content_config is not None:
        model_kwargs["generate_content_config"] = generate_content_config
    return model_kwargs
