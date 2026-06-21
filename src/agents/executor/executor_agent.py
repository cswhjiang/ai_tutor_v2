import json
import os.path
from typing import AsyncGenerator, Optional, Any, Dict


from google.adk.artifacts import InMemoryArtifactService
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.logger import logger
from conf.system import SYS_CONFIG
from src.observability.timing import get_trace_id_from_state, timing_stage
from src.utils import database_op_with_retry


class AgentInvocationService:
    def __init__(
        self,
        session_service: InMemorySessionService,
        artifact_service: InMemoryArtifactService,
        app_name: str = SYS_CONFIG.app_name,
        save_dir: str = '',
        uid: str = '',
        sid: str = '',
        username: str = '',
    ) -> None:
        self.app_name = app_name
        self.session_service = session_service
        self.artifact_service = artifact_service
        self.save_dir = save_dir
        self.uid = uid
        self.sid = sid
        self.username = username

        self.latest_final_response_text = ""

    async def stream_agent_events(
        self,
        runner: Runner,
        user_id: str,
        session_id: str,
        new_message: Optional[Content] = None,
        trace_id: str | None = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run an ADK agent with native SSE streaming and yield app events.

        This method is the transport-neutral boundary between ADK runtime
        events and the web app protocol. HTTP routers should send the returned
        dictionaries through their chosen transport instead of exposing raw ADK
        Event objects to clients.
        """
        final_response_text = ""
        partial_text_buffer = ""
        tool_call_started = set()
        tool_call_finished = set()
        run_config = RunConfig(streaming_mode=StreamingMode.SSE)

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
            run_config=run_config,
        ):
            self._log_event_summary(event, trace_id=trace_id)

            for app_event in self._event_to_app_stream_events(
                event=event,
                root_agent_name=runner.agent.name,
                partial_text_buffer=partial_text_buffer,
                tool_call_started=tool_call_started,
                tool_call_finished=tool_call_finished,
            ):
                if app_event.pop("_reset_partial_buffer", False):
                    partial_text_buffer = ""
                    continue
                if app_event.get("type") == "assistant_delta":
                    partial_text_buffer += str(app_event.get("content") or "")
                yield app_event

            if event.is_final_response() and event.content and event.content.parts:
                text_part = self._event_text(event)
                if text_part:
                    final_response_text = text_part
                    logger.info(f"[{runner.agent.name}] final response chars={len(final_response_text)}")

        self.latest_final_response_text = final_response_text

    def _event_to_app_stream_events(
        self,
        event: Event,
        root_agent_name: str,
        partial_text_buffer: str,
        tool_call_started: set[str],
        tool_call_finished: set[str],
    ) -> list[Dict[str, Any]]:
        """Convert one ADK Event into stable app-level stream events."""
        app_events: list[Dict[str, Any]] = []

        if getattr(event, "error_code", None):
            app_events.append(
                {
                    "type": "error",
                    "content": getattr(event, "error_message", None)
                    or f"Agent runtime error: {event.error_code}",
                }
            )
            return app_events

        for function_call in event.get_function_calls():
            if event.partial:
                continue
            if function_call.name in tool_call_started:
                continue
            tool_call_started.add(function_call.name)
            app_events.append(
                {
                    "type": "step",
                    "content": self._tool_status_message(function_call.name, started=True),
                }
            )

        for function_response in event.get_function_responses():
            if event.partial:
                continue
            if function_response.name in tool_call_finished:
                continue
            tool_call_finished.add(function_response.name)
            app_events.append(
                {
                    "type": "step",
                    "content": self._tool_status_message(function_response.name, started=False),
                }
            )

        text = self._event_text(event)
        if not text or event.author != root_agent_name:
            return app_events

        has_function_call = bool(event.get_function_calls())
        has_function_response = bool(event.get_function_responses())
        if has_function_call or has_function_response:
            return app_events

        if event.partial:
            app_events.append({"type": "assistant_delta", "content": text})
            return app_events

        if partial_text_buffer:
            if text == partial_text_buffer or text.startswith(partial_text_buffer):
                app_events.append({"_reset_partial_buffer": True})
                return app_events
            app_events.append({"_reset_partial_buffer": True})

        app_events.append({"type": "assistant_message", "content": text})
        return app_events

    def _event_text(self, event: Event) -> str:
        """Return concatenated text parts from an ADK Event."""
        if not event.content or not event.content.parts:
            return ""
        return "".join(
            part.text or ""
            for part in event.content.parts
            if part.text
            and not getattr(part, "thought", False)
            and not part.function_call
            and not part.function_response
        )

    def _event_summary(self, event: Event, trace_id: str | None = None) -> Dict[str, Any]:
        """Return a compact, non-payload ADK event summary for debug logs."""
        state_delta = {}
        if event.actions and event.actions.state_delta:
            state_delta = event.actions.state_delta

        function_calls = event.get_function_calls()
        function_responses = event.get_function_responses()
        text = self._event_text(event)
        summary = {
            "author": event.author,
            "partial": bool(event.partial),
            "final": event.is_final_response(),
            "text_chars": len(text),
            "function_calls": [call.name for call in function_calls],
            "function_responses": [response.name for response in function_responses],
            "state_delta_keys": sorted(str(key) for key in state_delta.keys()),
            "error_code": getattr(event, "error_code", None),
        }
        if trace_id:
            summary["trace_id"] = trace_id
        return summary

    def _log_event_summary(self, event: Event, trace_id: str | None = None) -> None:
        """Write a compact ADK event debug log instead of the full event JSON."""
        logger.debug(
            "ADK_EVENT {}",
            json.dumps(
                self._event_summary(event, trace_id=trace_id),
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    def _tool_status_message(self, tool_name: str, started: bool) -> str:
        """Return a user-facing status line for a tool boundary event."""
        if tool_name == "generate_math_video":
            if started:
                return "正在生成数学讲解视频..."
            return "数学讲解视频生成完成，正在整理结果..."

        if started:
            return "正在调用工具处理任务..."
        return "工具执行完成，正在整理结果..."
    
    async def add_event(self, text:str='', state_delta:Dict=None):
        if state_delta is None:
            state_delta = {}

        if text:
            event = Event(
                author='api_server',   # TODO: 确认author是否合理
                content=Content(role='model', parts=[Part(text=text)]),
                actions=EventActions(state_delta=state_delta)
            )
        else:
            event = Event(
                author='api_server',
                actions=EventActions(state_delta=state_delta)
            )

        current_session = await database_op_with_retry(
                self.session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=self.uid,
                session_id=self.sid,
            )

        # await self.session_service.append_event(current_session, event) # TODO: 确定作用域
        # 使用带重试的写入，防止数据库锁定失败
        await database_op_with_retry(
            self.session_service.append_event,
            session=current_session,
            event=event,
            logger=logger,
            op_name="add_event_append_event"
        )

    async def save_artifact(self, art_name: str, current_uid:str, current_sid:str):
        art_part = await self.artifact_service.load_artifact(
            app_name=self.app_name, user_id=self.uid, session_id=self.sid, filename=art_name
        )

        if art_part is not None:
            art_name = f"{current_uid}_{current_sid}_{art_name}"
            art_path = os.path.join(self.save_dir, art_name)
            with open(art_path, mode='wb') as f:
                f.write(art_part.inline_data.data)
        else:
            logger.error(f'load {art_name} return none and save failed') # TODO: 确定原因
            return None
        return art_path

    async def persist_current_output(
        self,
        summary: str = "",
        current_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist the current expert output into local files and session history."""
        # 专家agent的输出：state['current_output']
        # 所有专家agent的输出结构：
        # {
        #     "author": 专家agent名称
        #     "status": 执行成功或失败
        #     "message": 执行日志输出
        #     "output_artifact": 输出图片信息：list[dict]，每个dict包含{'name', 'description'}
        #     "output_text": 输出文本信息：str
        # }

        # todo: 专家输出使用统一对象进行封装，而不是靠注释规范，zyh

        current_session = await database_op_with_retry(
                self.session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=self.uid,
                session_id=self.sid,
            )
        # 如果上面expert运行了，current_output会被设置，从state中读取
        if not current_output:
            current_output = current_session.state.get('current_output')
        
        current_step = current_session.state.get('step', 0) or 0
        trace_id = get_trace_id_from_state(current_session.state)
        artifacts_history = current_session.state.get('artifacts_history', []) or []
        text_history = current_session.state.get('text_history', []) or []
        message_history = current_session.state.get('message_history', []) or []
        summary_history = current_session.state.get('summary_history', []) or []

        # 对于pending状态，是否需要特殊处理？
        if not current_output:
            current_output = {'status': 'pending'}

        state_delta = {
            'step': current_step + 1,
            'current_plan': {},  # 清空当前的plan，防止重复执行
            'latest_tool_output_ready': False,
            'latest_tool_summary': '',
        }

        # 把新生成的artifact保存到本地
        if current_output['status'] == 'success' and 'output_artifacts' in current_output:
            for art in current_output['output_artifacts']:
                current_sid = current_session.state['sid']
                current_uid = current_session.state['uid']
                logger.info(f"saving artifact {art['name']}")
                with timing_stage(
                    "artifact",
                    "save_output_artifact",
                    trace_id=trace_id,
                    uid=current_uid,
                    sid=current_sid,
                    metadata={"artifact_name": art.get("name")},
                ) as timing:
                    art_path = await self.save_artifact(art['name'], current_uid, current_sid)
                    timing["artifact_path"] = art_path
                art['path'] = art_path

                logger.info(f"saved to {art_path}")

        # 设置event保存到session中
        if current_output['status'] == 'success':
            # 保存output_artifacts和artifacts_history
            if 'output_artifacts' in current_output:
                state_delta['new_artifacts'] = current_output['output_artifacts']
                state_delta['artifacts_history'] = artifacts_history + [current_output['output_artifacts']] # 这里保存的是文本： name、description 。
            else:
                state_delta['new_artifacts'] = []
                state_delta['artifacts_history'] = artifacts_history + [[]]

            # 保存text_history
            if 'output_text' in current_output and len(current_output['output_text']) > 0:
                state_delta['text_history'] = text_history + [current_output['author'] + '的 output_text: \n' + str(current_output['output_text']) + '\n']
            else:
                state_delta['text_history'] = text_history + [None]

            # 保存summary_history
            state_delta['summary_history'] = summary_history + [summary]

            # 保存message_history
            state_delta['message_history'] = message_history + [current_output['message']]

            await self.add_event(text=f"第{current_step+1}轮执行已完成。这一步的原始目标：`{summary}`，执行完成后的总结：`{current_output['message']}`", state_delta=state_delta)

        elif current_output['status'] == 'error':
            state_delta['new_artifacts'] = []
            state_delta['artifacts_history'] = artifacts_history + [[]]
            state_delta['text_history'] = text_history + [None]
            state_delta['message_history'] = message_history + [current_output['message']]
            state_delta['summary_history'] = summary_history + [summary]

            await self.add_event(text=f"第{current_step+1}轮专家执行出错。这一步的原始目标：`{summary}`, 执行错误描述：`{current_output['message']}`。当前步骤目标可能未完成，需要视情况重新执行或使用新的参数或方法。", state_delta=state_delta)

        return current_output
