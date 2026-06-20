from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, FunctionCall, FunctionResponse, Part

from src.agents.executor.executor_agent import AgentInvocationService


def make_service() -> AgentInvocationService:
    """Create the event adapter service with in-memory ADK dependencies."""
    return AgentInvocationService(
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )


def test_partial_text_becomes_assistant_delta():
    service = make_service()
    event = Event(
        author="RootAgent",
        content=Content(role="model", parts=[Part(text="hello")]),
        partial=True,
    )

    app_events = service._event_to_app_stream_events(
        event=event,
        root_agent_name="RootAgent",
        partial_text_buffer="",
        tool_call_started=set(),
        tool_call_finished=set(),
    )

    assert app_events == [{"type": "assistant_delta", "content": "hello"}]


def test_aggregated_text_after_partial_is_not_displayed_twice():
    service = make_service()
    event = Event(
        author="RootAgent",
        content=Content(role="model", parts=[Part(text="hello world")]),
        partial=False,
    )

    app_events = service._event_to_app_stream_events(
        event=event,
        root_agent_name="RootAgent",
        partial_text_buffer="hello world",
        tool_call_started=set(),
        tool_call_finished=set(),
    )

    assert app_events == [{"_reset_partial_buffer": True}]


def test_math_video_function_events_become_status_steps():
    service = make_service()
    started = set()
    finished = set()
    function_call_event = Event(
        author="RootAgent",
        content=Content(
            role="model",
            parts=[
                Part(
                    function_call=FunctionCall(
                        name="generate_math_video",
                        args={},
                    )
                )
            ],
        ),
        partial=False,
    )
    function_response_event = Event(
        author="RootAgent",
        content=Content(
            role="model",
            parts=[
                Part(
                    function_response=FunctionResponse(
                        name="generate_math_video",
                        response={"result": "ok"},
                    )
                )
            ],
        ),
        partial=False,
    )

    assert service._event_to_app_stream_events(
        event=function_call_event,
        root_agent_name="RootAgent",
        partial_text_buffer="",
        tool_call_started=started,
        tool_call_finished=finished,
    ) == [{"type": "step", "content": "正在生成数学讲解视频..."}]
    assert service._event_to_app_stream_events(
        event=function_response_event,
        root_agent_name="RootAgent",
        partial_text_buffer="",
        tool_call_started=started,
        tool_call_finished=finished,
    ) == [{"type": "step", "content": "数学讲解视频生成完成，正在整理结果..."}]
