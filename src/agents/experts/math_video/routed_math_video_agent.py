from __future__ import annotations

from typing import AsyncGenerator, Dict

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

from src.agents.experts.math_video.routes import resolve_math_video_route
from src.logger import logger


class RoutedMathVideoGenerationAgent(BaseAgent):
    """Route math-video requests to the configured implementation pipeline."""

    model_config = {"arbitrary_types_allowed": True}

    manimce_agent: BaseAgent
    fast_agent: BaseAgent
    manimgl_agent: BaseAgent

    def __init__(
        self,
        name: str,
        description: str = "",
        manimce_agent: BaseAgent | None = None,
        fast_agent: BaseAgent | None = None,
        manimgl_agent: BaseAgent | None = None,
    ):
        super().__init__(
            name=name,
            description=description,
            manimce_agent=manimce_agent,
            fast_agent=fast_agent,
            manimgl_agent=manimgl_agent,
        )

    def _format_event(self, content_text: str | None = None, state_delta: Dict | None = None):
        """Create an ADK event with optional content and state updates."""
        event = Event(author=self.name)
        if state_delta:
            event.actions = EventActions(state_delta=state_delta)
        if content_text:
            event.content = Content(role="model", parts=[Part(text=content_text)])
        return event

    def _agent_for_route(self, route: str) -> BaseAgent | None:
        """Return the agent implementation for a route."""
        if route == "manimce":
            return self.manimce_agent
        if route == "fast":
            return self.fast_agent
        if route == "manimgl":
            return self.manimgl_agent
        return None

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Resolve the configured route and delegate to the matching pipeline."""
        current_parameters = ctx.session.state.get("current_parameters", {})
        if "prompt" not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：prompt"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": error_text,
                "message_for_user": "视频生成失败：缺少题目描述。",
                "output_text": "",
            }
            logger.error(error_text)
            yield self._format_event(error_text, {"current_output": current_output})
            return

        try:
            route = resolve_math_video_route(current_parameters)
        except ValueError as exc:
            message = str(exc)
            current_output = {
                "author": self.name,
                "status": "error",
                "message": message,
                "message_for_user": "视频生成失败：不支持的生成路线。",
                "output_text": "",
            }
            logger.error(message)
            yield self._format_event(message, {"current_output": current_output})
            return

        route_agent = self._agent_for_route(route)
        if route_agent is None:
            message = f"Math video route is not configured: {route}"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": message,
                "message_for_user": "视频生成失败：当前路线不可用。",
                "output_text": "",
            }
            logger.error(message)
            yield self._format_event(message, {"current_output": current_output})
            return

        parameters = dict(current_parameters)
        parameters["math_video_mode"] = route
        ctx.session.state["current_parameters"] = parameters
        logger.info("MathVideoGenerationAgent selected route: {}", route)
        yield self._format_event(
            state_delta={
                "current_parameters": parameters,
                "math_video/selected_route": route,
            }
        )

        async for event in route_agent.run_async(ctx):
            yield event
