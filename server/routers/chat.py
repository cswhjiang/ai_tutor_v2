from typing import List, Optional
from pathlib import Path
import time
import uuid
import json

from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from server.agents_manager import session_service, artifact_service, expert_runners, expert_agents
from server.utils.common import set_initial_state
from src.agents.orchestrator.orchestrator_agent import Orchestrator
from src.agents.executor.executor_agent import Executor
from conf.system import SYS_CONFIG
from src.logger import logger
from src.context import username_context
from server.utils.util import (save_upload_file_sync, format_sse_event, current_time_str, encode_media,
                         SessionCreateResponse)
from src.utils import database_op_with_retry

router = APIRouter()

# --- 静态文件服务设置 ---
outputs_dir_name = "outputs"
outputs_path = Path(SYS_CONFIG.base_dir) / outputs_dir_name
outputs_path.mkdir(parents=True, exist_ok=True)
# 在output下创建images， videos， uploads目录
# 来自不同session的文件会保存在相同的文件夹，但是通过文件名中包含session id来区分
images_dir_name = "images"
images_dir = outputs_path / images_dir_name
images_dir.mkdir(parents=True, exist_ok=True)

videos_dir_name = "videos" # Note: 暂时未使用，所有都保存到images_dir
videos_dir = outputs_path / videos_dir_name
videos_dir.mkdir(parents=True, exist_ok=True)

uploads_dir_name = "uploads"
uploads_dir = outputs_path / uploads_dir_name
uploads_dir.mkdir(parents=True, exist_ok=True)

router.mount(f"/{outputs_dir_name}", StaticFiles(directory=outputs_path), name="outputs")
logger.info(f"Static files are served at: /{outputs_dir_name}, corresponding directory: {outputs_path}")

DOC_EXT_TO_MIME = {
    # ===== PDF =====
    ".pdf": {
        "application/pdf",
    },

    # ===== Word =====
    ".doc": {
        "application/msword",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },

    # ===== PowerPoint =====
    ".ppt": {
        "application/vnd.ms-powerpoint",
    },
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },

    # ===== Excel =====
    ".xls": {
        "application/vnd.ms-excel",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },

    # ===== CSV =====
    ".csv": {
        "text/csv",
        "application/csv",              # 非标准但真实存在
        "application/vnd.ms-excel",     # Windows/Excel 常见错误上报
    },

    # ===== TXT =====
    ".txt": {
        "text/plain",
    },

    # ===== Markdown =====
    ".md": {
        "text/markdown",
        "text/plain",                  # 浏览器/部分客户端常降级
    },
}

ALLOWED_DOC_EXT = set(DOC_EXT_TO_MIME.keys())

ALLOWED_DOC_MIME = {
    mime
    for mimes in DOC_EXT_TO_MIME.values()
    for mime in mimes
}

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp"}


def _ext(name: str) -> str:
    name = (name or "").lower()
    return name[name.rfind("."):] if "." in name else ""


@router.post("/chat")
async def chat_with_agent(
    message: str = Form(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    documents: Optional[List[UploadFile]] = File(None),
):
    username_context.set(username or "anonymous")

    logger.info(f"user_id: {user_id}, username: {username}, images: {images}, documents: {documents}")
    # 图片
    images = images or []

    # 保存图片
    img_paths = []
    for image in images:
        if image and image.filename:
            ext = _ext(image.filename)
            if ext not in ALLOWED_IMAGE_EXT:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image file type: {image.filename} ({ext})"
                )
            img_path = save_upload_file_sync(image, uploads_dir)
            if len(img_path) > 0:
                img_paths.append(img_path)
                logger.info(f"Received image: {image.filename} ({image.content_type})")
        else:
            img_paths.append(None)

    # 文档
    document_paths = []
    if documents:
        for document in documents:
            if document and document.filename:
                content_type = (document.content_type or "").lower()
                ext = _ext(document.filename)

            if content_type not in ALLOWED_DOC_MIME and ext not in ALLOWED_DOC_EXT:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {document.filename} ({document.content_type})"
                )
            document_path = save_upload_file_sync(document, uploads_dir)
            if len(document_path) > 0:
                document_paths.append(document_path)
                logger.info(f"Received document: {document.filename} ({document.content_type})")

    uid = user_id or SYS_CONFIG.user_id_default
    sid = session_id
    debug_username_set = set(SYS_CONFIG.DEBUG_USERS)
    # logger.info(debug_username_set)

    async def event_stream():
        logger.info(f"workflow stated! uid: {uid}, username: {username}, sid: {sid}, user instruction: {message}")
        # 这个内部生成器现在可以安全地使用上面已经保存好的路径
        # yield format_sse_event({"type": "step", "content": f"用户指令: {message}"})
        if username in debug_username_set:
            yield format_sse_event({"type": "step", "content": f"{current_time_str()}  User instruction: {message}"})
        else:
            yield format_sse_event({"type": "step", "content": f"User instruction: {message}"})

        for index, img_path in enumerate(img_paths, start=1):
            if img_path:
                yield format_sse_event(
                    {"type": "step", "content": f"Image {index} received: {Path(img_path).name}"}
                )

        try: # 尝试获取之前创建的session
            current_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )
            if not current_session:
                logger.info(f"current user & sessions: ")
                for app_name, app in session_service.sessions.items():
                    for user_name, user in app.items():
                        for session_name, session in user.items():
                            logger.info(f"{app_name}/{user_name}/{session_name}")
                            #logger.info(f"state: {session.state}")
                # raise ValueError(f"会话 {sid} (用户 {uid}) 未找到。")
                raise ValueError(f"Session {sid} (User {uid}) not found.")

        except Exception as e:
            logger.error(f"Error occurred while retrieving the current session: {str(e)}")
            yield format_sse_event({"type": "error", "content": "Error occurred while retrieving the current session, please try again later"})
            # logger.error(f"获取当前session出错：{str(e)}")
            # yield format_sse_event({"type": "error", "content": f"获取当前session出错, 请稍后重试"})
            return
        
        try: # 设置initial_state
            await set_initial_state(uid, sid, message, img_paths, document_paths) # 将用户输入放到state里面
        except Exception as e:
            # error_text = f"初始化state失败: {str(e)}"
            error_text = f"Failed to initialize state: {str(e)}"
            logger.error(error_text)
            yield format_sse_event({"type": "error", "content": error_text})
            return

        # 设置orchestrator和executor
        # --- 创建总指挥Agent的Runner ---
        orchestrator = Orchestrator(
            session_service=session_service,
            artifact_service=artifact_service,
            app_name=SYS_CONFIG.app_name,
            llm_model_plan=SYS_CONFIG.orchestrator_llm_model,
            llm_model_critic=SYS_CONFIG.critic_llm_model,
            max_iter=SYS_CONFIG.plan_critic_iter_num,  # 小于1不使用 critic 来优化plan， 大于0的情况下使用。
            internal=True # 启用创建内部新session
        )

        # --- 创建执行agent的Runner ---
        executor = Executor(
            session_service=session_service,
            artifact_service=artifact_service,
            app_name=SYS_CONFIG.app_name,
            expert_runners=expert_runners,
            llm_model=SYS_CONFIG.executor_llm_model,
            executor_replan_enabled=SYS_CONFIG.executor_replan_enabled
        )

        orchestrator.uid = uid
        orchestrator.sid = sid
        orchestrator.username = username
        executor.uid = uid
        executor.sid = sid
        executor.username = username
        executor.save_dir = images_dir


        # 可以选择先生成整体所有步骤，作为后续规划和执行的参考
        global_plan, global_summary = await orchestrator.generate_plan(global_plan=True)  # 先生成全局规划
        # logger.info(f"全局所有步骤规划：\n {global_summary}")
        logger.info(f"Global step planning:\n {global_summary}")
        if username in debug_username_set: # 输出到页面上
            yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Orchestrator global plan: {global_plan}"})
            yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Orchestrator: {global_summary}"})
        else:
            yield format_sse_event({"type": "step", "content": f"Orchestrator: {global_summary}"})


        # --- 任务循环开始 ---
        # final_summary = "任务流程已启动。"
        final_summary = "The task process has been initiated."
        max_loops = SYS_CONFIG.max_iterations_orchestrator
        for i in range(max_loops):
            logger.info(f"--- Workflow loop: Round {i + 1}/{max_loops} (Session: {sid}) ---")

            current_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )
            logger.debug(f"State snapshot (Orchestrator input): {json.dumps(current_session.state, indent=2, ensure_ascii=False)}") # TODO: 确认parameter如何从上一步中填充的

            # 生成单步规划
            # yield format_sse_event({"type": "step", "content": f"Orchestrator is thinking..."}) ## 有时候会在plan出现之前出现
            plan, current_summary = await orchestrator.generate_plan(global_plan=False) # TODO: 这一遍原先是计划放在 executor 里面的。需要确认是否可以看到global-plan

            next_agent_name = plan.get("next_agent")
            params_for_expert = plan.get("parameters", {})
            final_summary = current_summary

            if username in debug_username_set:
                yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Orchestrator next action: {plan}"})

            if not next_agent_name or next_agent_name == "FINISH":
                logger.info(f"Orchestrator: Task finished. Summerization: {final_summary}")
                break

            if next_agent_name not in expert_agents:
                logger.error(f"Orchestrator selected unknown agent: '{next_agent_name}'. End loop.")
                final_summary = f"Orchestrator selected unknown agent '{next_agent_name}', task ends."
                break

            if i == 0:
                if username in debug_username_set:
                    yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Plan has been formulated, and expert agents are executing..."})
                else:
                    yield format_sse_event({"type": "step", "content": "Plan has been formulated, and expert agents are executing..."})

            # yield format_sse_event({"type": "step", "content": f"userid: {uid}, username: {username}, sid: {sid}"})
            if username in debug_username_set:
                yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Delegating task to expert: {next_agent_name}. \n Parameter: {params_for_expert}\n"})

            # 执行当前步骤
            current_output = await executor.execute_plan()

            # logger.info(current_output)

            if username in debug_username_set:
                text = current_output['message']
                if 'output_text' in current_output:
                    text += f"\n{current_output['output_text']}"
                # 执行结果为： message + output_text
                yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Execution result: agent {i} {text}"})
            else:
                if 'message_for_user' in current_output:
                    message_for_user = current_output['message_for_user']
                else:
                    message_for_user = current_output['message']
                if username in debug_username_set:
                    yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Execution result: agent {i} {message_for_user}"})
                else:
                    yield format_sse_event({"type": "step", "content": f"--> Execution result: agent {i} {message_for_user}"})
        else:
            logger.warning(f"Workflow reached the maximum number of loops {max_loops}, forcing termination.")
            final_summary = f"The task reached the maximum step limit ({max_loops}) and has been automatically terminated."
            # logger.warning(f"工作流达到最大循环次数 {max_loops}，强制终止。")
            # final_summary = f"任务达到最大步骤限制 ({max_loops})，已自动终止。"

        final_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )

        # 需要返回的最终结果
        artifacts_history = final_session.state.get('artifacts_history')
        final_steps = len(artifacts_history)
        final_art = []
        for i in range(final_steps):
            if len(artifacts_history[final_steps-1-i]) > 0:
                for art in artifacts_history[final_steps-1-i]:
                    ext_name = _ext(art['name'])
                    # 过滤掉文件比如pptx等无需base64编码的
                    if 'search' not in art['name'] and ext_name not in ALLOWED_DOC_EXT:
                        final_art.append(art)
                # break
        final_filenames = []
        # 使用最新一步的new_artifacts获取是否生成了新的文件
        new_artifacts = final_session.state.get('new_artifacts', [])
        for art in new_artifacts:
            ext_name = _ext(art['name'])
            logger.info(f"final new artifact: {art['name']}, ext: {ext_name}")
            if 'search' not in art['name'] and ext_name in ALLOWED_DOC_EXT:
                final_filenames.append(art['name'])


        # final_art_base64 = [encode_image(art['path']) for art in final_art] # NOTE: 需要判断支持视频

        logger.info(final_art) ## TypeError: expected str, bytes or os.PathLike object, not NoneType
        final_art_base64 = [encode_media(art['path']) for art in final_art]  # TODO: bug. NOTE: 需要判断支持视频
        final_art_base64 = [f for f in final_art_base64 if f is not None]

        # 返回的文本
        final_output_text = ''
        text_history = final_session.state.get('text_history', [])
        if len(text_history) > 0 and text_history[-1]:
            final_output_text = text_history[-1]


        final_output_text = final_output_text +  f"\nThe current task has been completed, number of steps: {final_steps}\n"
        # final_output_text = f"\n当前任务已完成，步骤数量：{final_steps}\n"
        # summary_history = final_session.state.get('summary_history',[])
        # final_output_text += '\n'.join(f" - {summary}" for summary in summary_history)

        # final_summary += final_output_text

        # final_output_text = final_summary
        logger.info(f"final_output_text: {final_output_text}")


        # 这里名字定义的不太好
        final_data = {
            "text": final_summary,  # 整个项目执行的总结
            "final_output_text": str(final_output_text) if final_output_text else None,
            "image": final_art_base64,
            "filenames": final_filenames,
        }
        yield format_sse_event({"type": "final", "content": final_data})

    return StreamingResponse(event_stream(), media_type="text/event-stream")  # type: ignore


@router.post("/session/create", response_model=SessionCreateResponse)
async def create_session_endpoint(
    user_id: Optional[str] = Form(None),
    username: Optional[str] = Form(None)
):
    """
    为当前的user_id创建session
    """
    username_context.set(username or "anonymous")
    uid = user_id or f"{SYS_CONFIG.user_id_default}_{time.strftime('%Y%m%d%H%M%S')}"
    session_id_val = f"{SYS_CONFIG.session_id_default_prefix}{uuid.uuid4()}"
    try:
        # 通过重试机制创建session，避免数据库锁定问题
        await database_op_with_retry(
            session_service.create_session,
            app_name=SYS_CONFIG.app_name,
            user_id=uid,
            state={},
            session_id=session_id_val,
            logger=logger,
            op_name="create_session_endpoint",
        )
        # logger.info(f"会话创建成功: 用户 = {username}, SID = {session_id_val}, UID = {uid}")
        logger.info(f"Session created successfully: User = {username}, SID = {session_id_val}, UID = {uid}")

        return SessionCreateResponse(user_id=uid,
                                     session_id=session_id_val,
                                     # message="会话创建成功。",
                                     message="Session created successfully."
        )

    except Exception as e:
        logger.error(f"Failed to create session (User: {uid}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")
        # logger.error(f"创建会话失败 (用户: {uid}): {e}", exc_info=True)
        # raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/file/download")
async def download_file(
                user_id: str,
                session_id: str,
                filename: str,
):
    """
    下载artifact文件
    """
    try:
        artifact_part = await artifact_service.load_artifact(
            app_name=SYS_CONFIG.app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
        )
        if not artifact_part:
            raise HTTPException(status_code=404, detail="Artifact not found.")

        file_data = artifact_part.inline_data.data
        mime_type = artifact_part.inline_data.mime_type or "application/octet-stream"

        return StreamingResponse(
            iter([file_data]),
            media_type=mime_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"Error downloading file {filename} for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")
