import os.path
from typing import Optional, Any, Dict


from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.logger import logger
from conf.system import SYS_CONFIG
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
        expert_runners: Dict[str, Runner] = {}, # 用于运行expert的runner
    ) -> None:
        self.app_name = app_name
        self.session_service = session_service
        self.artifact_service = artifact_service
        self.save_dir = save_dir
        self.uid = uid
        self.sid = sid
        self.username = username

        self.expert_runners = expert_runners

    async def run_agent_and_log_events(self, runner: Runner, user_id: str, session_id: str, new_message: Optional[Content] = None) -> str:
        final_response_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message): # 这个是那个agent运行的？
            logger.debug(f"Event: {event.model_dump_json(indent=2, exclude_none=True)}")
            if event.is_final_response() and event.content and event.content.parts:
                text_part = next((part.text for part in event.content.parts if part.text), None)
                if text_part:
                    final_response_text = text_part
                    logger.info(f"[{runner.agent.name}] 最终响应文本: '{final_response_text}'")
        return final_response_text
    
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
    
    async def check_paramters_valid(self, agent_name: str, params_for_expert: Dict[str, Any]) -> str:
        error_text = ''
        error_arifact_names = []

        # 检查调用的agent名称是否在提供的expert_runners中
        if agent_name not in self.expert_runners:
            error_text = f"请求调用了未知的Agent: '{agent_name}'，它不在提供的agent列表中"
            return error_text

        # 检查调用的artifact名称是否存在于artifact service中
        artifact_parameter_names = ["input_name", "input_img_name"]
        for artifact_parameter_name in artifact_parameter_names:
            if artifact_parameter_name not in params_for_expert:
                continue

            art_list = await self.artifact_service.list_artifact_keys(
                app_name=self.app_name, user_id=self.uid, session_id=self.sid
            )

            parameter_value = params_for_expert[artifact_parameter_name]
            input_names = []
            if isinstance(parameter_value, str):
                input_names = [parameter_value]
            elif isinstance(parameter_value, list):
                input_names = parameter_value
            else:
                error_text += f"当前的parameters['{artifact_parameter_name}']格式错误，需要为string或list"
                return error_text

            for name in input_names:
                if name in art_list:
                    continue

                logger.info(art_list)
                error_arifact_names.append(name)

        if len(error_arifact_names) > 0:
            all_artifact_names = ', '.join(error_arifact_names)
            error_text += f"请求选择了未知的 artifact: {all_artifact_names}，它们不在artifacts列表中"

        return error_text

    async def execute_agent(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        summary: str = "",
    ) -> Dict[str, Any]:
        """Run one expert agent directly and persist its output into session state.

        This is the reusable runtime path for both the legacy plan-based executor
        and the new tool-calling orchestrator. It writes `current_parameters`,
        invokes the target agent runner, saves generated artifacts to disk, and
        appends execution history back to the shared session.
        """
        # 检查参数有效性
        error_text = await self.check_paramters_valid(agent_name, parameters)
        # 如果参数有问题，那么error_text会有值
        if error_text:
            logger.error(error_text)
            
            # 2026.1.12之前版本出错后没有更新state delta，这里会有相应更新，是否正确需要确认？？？

            # 2026.1.12之前版本遇到错误会直接返回None，鲁棒性不强，外层函数判断麻烦，这里改成统一的。
            # 这里author直接使用Executor，因为没有执行expert agent
            current_output = {
                "author": "Executor",
                "status": "error",
                "message": error_text,
                "message_for_user": error_text,
                "output_artifacts": [],
                "output_text": ""
            }
        else:
            # 参数没有问题，运行expert agent
            # 将当前的参数写入state
            await self.add_event(state_delta={'current_parameters': parameters})
            # 运行expert，运行的结果位于state['current_output']
            expert_runner = self.expert_runners[agent_name]
            new_message = Content(role='user', parts=[Part(text="根据原始任务和当前输入参数，调用对应的agent来执行")]) # TODO: 没有author，确认
            await self.run_agent_and_log_events(expert_runner, user_id=self.uid, session_id=self.sid, new_message=new_message) # 调用这个runner下的agent。TODO: 这个message 在 llm_request 里面没有author
            current_output = {} # 先置空，下面会从state中读取

        return await self.persist_current_output(summary=summary, current_output=current_output)

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
                art_path = await self.save_artifact(art['name'], current_uid, current_sid)
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

    async def execute_plan(self):
        """
        执行plan函数，直接从主session的state中的 `current_plan` 字段读取当前规划的参数并执行
        """
        # load state['current_plan']
        current_session = await database_op_with_retry(
                self.session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=self.uid,
                session_id=self.sid,
            )

        # TODO: 有潜在问题，使用完之后没有清空。如果当前 next_agent 决策没有填充这个字段的话，会继续执行上一个步骤。
        # 增加这个todo，在最后面执行完之后清空 current_plan，使用state_delta进行覆盖
        plan = current_session.state.get('current_plan') or {}

        return await self.execute_agent(
            agent_name=plan.get("next_agent"),
            parameters=plan.get("parameters", {}),
            summary=plan.get("summary", {}),
        )


# Backward-compatible alias for the legacy plan-based route.
Executor = AgentInvocationService
