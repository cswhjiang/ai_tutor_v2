import asyncio
from contextlib import suppress
from typing import Any, List, Optional
from pathlib import Path
import time
import uuid

from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.genai.types import Content, Part

from server.agents_manager import session_service, artifact_service, expert_runners
from server.utils.common import set_initial_state
from src.agents.orchestrator.tool_calling_orchestrator_agent import create_orchestrator_agent
from src.agents.executor.executor_agent import AgentInvocationService
from conf.system import SYS_CONFIG
from src.logger import logger
from src.context import username_context
from src.media.output_urls import outputs_static_url
from src.observability.timing import make_trace_id, log_timing_event, timing_stage
from src.streaming.app_events import (
    register_app_event_queue,
    unregister_app_event_queue,
)
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
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
RUNNER_DONE_EVENT_TYPE = "_runner_done"


def _ext(name: str) -> str:
    name = (name or "").lower()
    return name[name.rfind("."):] if "." in name else ""


def _video_preview_event_from_artifact(
    artifact: dict[str, Any],
    *,
    status: str = "final",
    sequence: int | None = None,
) -> dict[str, Any] | None:
    """Build a video preview SSE event from a persisted output artifact."""
    artifact_path = artifact.get("path")
    artifact_name = str(artifact.get("name") or "")
    ext_name = _ext(str(artifact_path or artifact_name))
    if ext_name not in VIDEO_EXTENSIONS or not artifact_path:
        return None

    url = outputs_static_url(artifact_path)
    if not url:
        return None

    content: dict[str, Any] = {
        "url": url,
        "status": status,
        "label": artifact_name or Path(artifact_path).name,
        "mime_type": "video/mp4",
    }
    if sequence is not None:
        content["sequence"] = sequence
    return {"type": "video_preview", "content": content}


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
    trace_id = make_trace_id(uid, sid)
    debug_username_set = set(SYS_CONFIG.DEBUG_USERS)
    # logger.info(debug_username_set)

    async def event_stream():
        request_start = time.perf_counter()
        log_timing_event(
            event="stage_start",
            stage="http",
            name="chat_request",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
            metadata={
                "image_count": len(img_paths),
                "document_count": len(document_paths),
                "message_chars": len(message),
            },
        )
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
            with timing_stage(
                "storage",
                "session_get_before_request",
                trace_id=trace_id,
                uid=uid,
                sid=sid,
            ):
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
            log_timing_event(
                event="stage_end",
                stage="http",
                name="chat_request",
                trace_id=trace_id,
                uid=uid,
                sid=sid,
                status="error",
                duration_ms=(time.perf_counter() - request_start) * 1000,
                metadata={"error": "session_get_failed"},
            )
            # logger.error(f"获取当前session出错：{str(e)}")
            # yield format_sse_event({"type": "error", "content": f"获取当前session出错, 请稍后重试"})
            return
        
        try: # 设置initial_state
            with timing_stage(
                "storage",
                "state_initialize",
                trace_id=trace_id,
                uid=uid,
                sid=sid,
                metadata={
                    "image_count": len(img_paths),
                    "document_count": len(document_paths),
                },
            ):
                await set_initial_state(
                    uid,
                    sid,
                    message,
                    img_paths,
                    document_paths,
                    timing_trace_id=trace_id,
                ) # 将用户输入放到state里面
        except Exception as e:
            # error_text = f"初始化state失败: {str(e)}"
            error_text = f"Failed to initialize state: {str(e)}"
            logger.error(error_text)
            yield format_sse_event({"type": "error", "content": error_text})
            log_timing_event(
                event="stage_end",
                stage="http",
                name="chat_request",
                trace_id=trace_id,
                uid=uid,
                sid=sid,
                status="error",
                duration_ms=(time.perf_counter() - request_start) * 1000,
                metadata={"error": "state_initialize_failed"},
            )
            return

        # --- 创建执行agent的Runtime ---
        executor = AgentInvocationService(
            session_service=session_service,
            artifact_service=artifact_service,
            app_name=SYS_CONFIG.app_name,
            expert_runners=expert_runners,
        )

        executor.uid = uid
        executor.sid = sid
        executor.username = username
        executor.save_dir = images_dir

        # --- 创建总指挥Agent的Runner：直接通过function call调用工具，不再生成plan ---
        orchestrator_agent = create_orchestrator_agent()
        orchestrator_runner = Runner(
            agent=orchestrator_agent,
            app_name=SYS_CONFIG.app_name,
            session_service=session_service,
            artifact_service=artifact_service,
        )

        if username in debug_username_set:
            yield format_sse_event({"type": "step", "content": f"{current_time_str()}  Orchestrator is handling the request..."})
        else:
            yield format_sse_event({"type": "step", "content": "Orchestrator is handling the request..."})

        with timing_stage(
            "adk_run",
            "OrchestratorAgent",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
        ):
            app_event_queue = register_app_event_queue(trace_id)

            async def pump_orchestrator_events() -> None:
                """Forward ADK stream events into the app-level SSE queue."""
                try:
                    async for app_event in executor.stream_agent_events(
                        orchestrator_runner,
                        user_id=uid,
                        session_id=sid,
                        new_message=Content(
                            role='user',
                            parts=[Part(text=f"请处理用户最新任务：{message}")]
                        ),
                        trace_id=trace_id,
                    ):
                        await app_event_queue.put(app_event)
                except Exception as exc:
                    logger.error("Orchestrator stream failed: {}", exc, exc_info=True)
                    await app_event_queue.put(
                        {
                            "type": "error",
                            "content": f"Agent execution failed: {exc}",
                        }
                    )
                    await app_event_queue.put(
                        {
                            "type": RUNNER_DONE_EVENT_TYPE,
                            "status": "error",
                            "error": str(exc),
                        }
                    )
                else:
                    await app_event_queue.put(
                        {"type": RUNNER_DONE_EVENT_TYPE, "status": "success"}
                    )

            runner_task = asyncio.create_task(pump_orchestrator_events())
            runner_status = "success"
            runner_error = ""
            try:
                while True:
                    app_event = await app_event_queue.get()
                    if app_event.get("type") == RUNNER_DONE_EVENT_TYPE:
                        runner_status = str(app_event.get("status") or "success")
                        runner_error = str(app_event.get("error") or "")
                        break
                    yield format_sse_event(app_event)
            finally:
                unregister_app_event_queue(trace_id)
                if not runner_task.done():
                    runner_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await runner_task

            if runner_status != "success":
                log_timing_event(
                    event="stage_end",
                    stage="http",
                    name="chat_request",
                    trace_id=trace_id,
                    uid=uid,
                    sid=sid,
                    status="error",
                    duration_ms=(time.perf_counter() - request_start) * 1000,
                    metadata={"error": runner_error or "orchestrator_stream_failed"},
                )
                return

        final_summary = executor.latest_final_response_text
        if not final_summary:
            final_summary = "The task process has finished."

        with timing_stage(
            "storage",
            "session_get_after_orchestrator",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
        ):
            post_orchestrator_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )
        if post_orchestrator_session.state.get("latest_tool_output_ready"):
            with timing_stage(
                "storage",
                "persist_current_output",
                trace_id=trace_id,
                uid=uid,
                sid=sid,
            ):
                current_output = await executor.persist_current_output(
                    summary=post_orchestrator_session.state.get("latest_tool_summary", "")
                )
            final_summary = (
                current_output.get("message_for_user")
                or current_output.get("message")
                or final_summary
            )
            for art in current_output.get("output_artifacts", []) or []:
                preview_event = _video_preview_event_from_artifact(art, status="final")
                if preview_event:
                    yield format_sse_event(preview_event)

        with timing_stage(
            "storage",
            "session_get_final",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
        ):
            final_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )

        # 需要返回的最终结果
        artifacts_history = final_session.state.get('artifacts_history', []) or []
        final_steps = len(artifacts_history)
        new_artifacts = final_session.state.get('new_artifacts', []) or []
        candidate_artifacts = new_artifacts
        if not candidate_artifacts and artifacts_history:
            candidate_artifacts = artifacts_history[-1]

        final_art = []
        for art in candidate_artifacts:
            ext_name = _ext(art['name'])
            # 过滤掉文件比如pptx等无需base64编码的
            if 'search' not in art['name'] and ext_name not in ALLOWED_DOC_EXT and art.get('path'):
                final_art.append(art)

        final_filenames = []
        # 使用最新一步的new_artifacts获取是否生成了新的文件
        for art in new_artifacts:
            ext_name = _ext(art['name'])
            logger.info(f"final new artifact: {art['name']}, ext: {ext_name}")
            if 'search' not in art['name'] and ext_name in ALLOWED_DOC_EXT:
                final_filenames.append(art['name'])


        # final_art_base64 = [encode_image(art['path']) for art in final_art] # NOTE: 需要判断支持视频

        logger.info(
            "final artifacts selected: {}",
            [
                {"name": art.get("name"), "path": art.get("path"), "description_chars": len(art.get("description", ""))}
                for art in final_art
            ],
        ) ## TypeError: expected str, bytes or os.PathLike object, not NoneType
        final_video_urls = []
        with timing_stage(
            "postprocess",
            "prepare_final_media",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
            metadata={"artifact_count": len(final_art)},
        ):
            final_art_base64 = []
            for art in final_art:
                art_path = art.get("path")
                ext_name = _ext(str(art_path or art.get("name") or ""))
                if ext_name in VIDEO_EXTENSIONS:
                    video_url = outputs_static_url(art_path) if art_path else None
                    if video_url:
                        final_video_urls.append(video_url)
                    continue
                final_art_base64.append(encode_media(art_path))
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
            "video_urls": final_video_urls,
            "filenames": final_filenames,
        }
        log_timing_event(
            event="stage_end",
            stage="http",
            name="chat_request",
            trace_id=trace_id,
            uid=uid,
            sid=sid,
            status="success",
            duration_ms=(time.perf_counter() - request_start) * 1000,
            metadata={
                "final_steps": final_steps,
                "artifact_count": len(final_art_base64),
            },
        )
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
