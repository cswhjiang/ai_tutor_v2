from __future__ import annotations

import asyncio
import json
import os
import pprint
import re
import shutil
import sys
import tempfile
import time
from collections.abc import AsyncGenerator, Mapping
from pathlib import Path
from typing import Any, Dict

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai.types import Blob, Content, Part
from typing_extensions import override

from conf.system import SYS_CONFIG
from src.local_manim_voiceover_services.volcengine_tts import (
    VolcengineTTSResult,
    VolcengineTTSService,
)
from src.logger import logger
from src.media.output_urls import OUTPUTS_ROOT, outputs_static_url
from src.observability.timing import compact_text, timing_context_from_invocation, timing_stage
from src.streaming.app_events import publish_app_event
from src.utils import clean_json_string


PROJECT_ROOT = Path(__file__).resolve().parents[4]
NARRATION_AUDIO_RE = re.compile(r"NARRATION_AUDIO\s*=\s*\{\}")
START_VOICEOVER_RE = re.compile(r"start_voiceover\([^,\n]+,\s*[\"'](?P<key>[^\"']+)[\"']")
MANIMGL_READY_FILE_RE = re.compile(r"File ready at (?P<file>.+?\.mp4)(?=\s|$|\x1b)")


def resolve_manimgl_project_path() -> Path:
    """Return the local ManimGL project path used as a PYTHONPATH entry."""
    configured_path = SYS_CONFIG.manimgl_project_path or "../reference-projects/manim"
    path = Path(configured_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def build_manimgl_subprocess_env(
    base_env: Mapping[str, str] | None = None,
    *,
    workdir: Path | None = None,
) -> dict[str, str]:
    """Build the environment used by ManimGL subprocesses."""
    env = dict(os.environ if base_env is None else base_env)
    python_paths = [str(PROJECT_ROOT), str(resolve_manimgl_project_path())]
    existing_pythonpath = env.get("PYTHONPATH", "")
    for path in existing_pythonpath.split(os.pathsep):
        if path and path not in python_paths:
            python_paths.append(path)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)

    if workdir is not None:
        cache_root = workdir / "cache"
        home_dir = workdir / "home"
        matplotlib_dir = cache_root / "matplotlib"
        for path in (cache_root, home_dir, matplotlib_dir):
            path.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home_dir)
        env["XDG_CACHE_HOME"] = str(cache_root)
        env["MPLCONFIGDIR"] = str(matplotlib_dir)
    return env


def write_manimgl_custom_config(workdir: Path) -> None:
    """Write a per-render ManimGL config so cache/output paths are isolated."""
    custom_config = """
directories:
  cache: "cache/manimgl"
"""
    (workdir / "custom_config.yml").write_text(custom_config.lstrip(), encoding="utf-8")


def manimgl_quality_args() -> list[str]:
    """Return ManimGL CLI quality arguments from configuration."""
    quality = SYS_CONFIG.manimgl_render_quality
    if quality == "low":
        return ["-l"]
    if quality == "medium":
        return ["-m"]
    if quality in {"high", "production"}:
        return ["--hd"]
    return ["-l"]


def normalize_narration_segments(raw_segments: Any) -> list[dict[str, str]]:
    """Normalize LLM-produced narration segment data."""
    if not isinstance(raw_segments, list):
        return []

    normalized: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for index, segment in enumerate(raw_segments, start=1):
        if isinstance(segment, str):
            key = f"narration_{index:02d}"
            text = segment
        elif isinstance(segment, dict):
            key = str(segment.get("key") or f"narration_{index:02d}").strip()
            text = str(segment.get("text") or segment.get("narration") or "").strip()
        else:
            continue

        if not text:
            continue
        safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", key).strip("_") or f"narration_{index:02d}"
        if safe_key in seen_keys:
            safe_key = f"{safe_key}_{index:02d}"
        seen_keys.add(safe_key)
        normalized.append({"key": safe_key, "text": text})
    return normalized


def parse_manimgl_generation_output(raw_output: Any) -> dict[str, Any]:
    """
    Parse ManimGL code generation output.

    ADK `output_schema` stores validated agent output as a structured dict.
    Older runs may still provide a JSON string, which remains strictly parsed.
    """
    if isinstance(raw_output, dict):
        return raw_output
    if isinstance(raw_output, str):
        return json.loads(clean_json_string(raw_output))
    raise TypeError(
        "math_video/manimgl_code must be a structured dict or JSON string, "
        f"got {type(raw_output).__name__}"
    )


def manimgl_output_size(raw_output: Any) -> int:
    """Return a stable size hint for logging and timing metadata."""
    if isinstance(raw_output, str):
        return len(raw_output)
    if isinstance(raw_output, dict):
        return len(json.dumps(raw_output, ensure_ascii=False))
    return len(str(raw_output))


def extract_voiceover_keys(manim_code: str) -> set[str]:
    """Return narration keys referenced by generated ManimGL code."""
    return {match.group("key") for match in START_VOICEOVER_RE.finditer(manim_code)}


def validate_voiceover_references(manim_code: str, narrations: list[dict[str, str]]) -> None:
    """Ensure generated code references narration keys that can be synthesized."""
    referenced_keys = extract_voiceover_keys(manim_code)
    if not referenced_keys:
        raise ValueError("ManimGL 代码必须调用 start_voiceover(...) 来启动旁白。")

    narration_keys = {segment["key"] for segment in narrations}
    missing_keys = sorted(referenced_keys - narration_keys)
    if missing_keys:
        raise ValueError(
            "ManimGL 代码引用了未定义的旁白 key: " + ", ".join(missing_keys)
        )


def synthesize_manimgl_narrations(
    narrations: list[dict[str, str]],
    sounds_dir: Path,
) -> dict[str, dict[str, Any]]:
    """Synthesize narration audio and copy it into the ManimGL sounds directory."""
    if not narrations:
        raise ValueError("ManimGL 代码缺少 narrations，无法生成带声音的视频。")

    service = VolcengineTTSService()
    texts = [segment["text"] for segment in narrations]
    results = service.synthesize_many(texts)
    sounds_dir.mkdir(parents=True, exist_ok=True)

    audio_manifest: dict[str, dict[str, Any]] = {}
    for index, (segment, result) in enumerate(zip(narrations, results), start=1):
        source_path = Path(result.final_audio)
        suffix = source_path.suffix or ".mp3"
        file_name = f"voiceover_{index:02d}_{segment['key']}{suffix}"
        target_path = sounds_dir / file_name
        shutil.copy2(source_path, target_path)
        audio_manifest[segment["key"]] = {
            "file": file_name,
            "duration": result.duration_seconds,
            "text": segment["text"],
            "cache_hit": result.cache_hit,
        }
    return audio_manifest


def inject_narration_audio(manim_code: str, audio_manifest: dict[str, dict[str, Any]]) -> str:
    """Inject synthesized audio metadata into generated ManimGL code."""
    audio_literal = pprint.pformat(audio_manifest, width=100, sort_dicts=True)
    if not NARRATION_AUDIO_RE.search(manim_code):
        raise ValueError("ManimGL 代码必须包含占位符 `NARRATION_AUDIO = {}`。")
    return NARRATION_AUDIO_RE.sub(f"NARRATION_AUDIO = {audio_literal}", manim_code, count=1)


def summarize_manimgl_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact summary of ManimGL subprocess output."""
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    summary: Dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "code": str(result.get("code")),
        "stdout_chars": len(stdout),
        "stderr_chars": len(stderr),
        "progress_line_count": result.get("progress_line_count", 0),
    }
    if not result.get("ok"):
        summary["stdout_preview"] = compact_text(stdout, 500)
        summary["stderr_preview"] = compact_text(stderr, 500)
    return summary


def find_rendered_mp4(workdir: Path) -> Path | None:
    """Return the latest non-temporary MP4 emitted by ManimGL."""
    mp4_files = [
        path
        for path in workdir.rglob("*.mp4")
        if not path.name.endswith("_temp.mp4")
        and not path.stem.isdigit()
        and "partial_movie_files" not in str(path)
    ]
    if not mp4_files:
        return None
    return max(mp4_files, key=lambda path: path.stat().st_mtime)


def sanitize_path_part(value: str) -> str:
    """Return a filesystem-safe path segment."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "unknown"


def build_preview_output_dir(ctx: InvocationContext) -> Path:
    """Return the public preview directory for this render invocation."""
    state = ctx.session.state if ctx.session else {}
    trace_id = str(state.get("timing_trace_id") or "")
    uid = str(getattr(ctx.session, "user_id", "") or state.get("uid") or "user")
    sid = str(getattr(ctx.session, "id", "") or state.get("sid") or "session")
    directory_name = sanitize_path_part(trace_id or f"{uid}_{sid}_{int(time.time())}")
    preview_dir = OUTPUTS_ROOT / "videos" / "math_video_preview" / directory_name
    preview_dir.mkdir(parents=True, exist_ok=True)
    return preview_dir


def ready_file_path_from_line(line: str, workdir: Path) -> Path | None:
    """Extract a completed file path from a ManimGL progress line."""
    match = MANIMGL_READY_FILE_RE.search(line)
    if not match or not match.group("file"):
        return None

    file_path = Path(match.group("file").strip())
    if not file_path.is_absolute():
        file_path = (workdir / file_path).resolve()
    if not file_path.exists():
        return None
    return file_path


def copy_preview_video(source_path: Path, preview_dir: Path, target_name: str) -> Path:
    """Copy a completed preview video into the static outputs directory."""
    suffix = source_path.suffix or ".mp4"
    target_path = preview_dir / f"{target_name}{suffix}"
    shutil.copy2(source_path, target_path)
    return target_path


def publish_video_preview(
    *,
    trace_id: str | None,
    source_path: Path,
    preview_dir: Path,
    status: str,
    sequence: int | None = None,
) -> bool:
    """Publish a video preview event for a completed video file."""
    if status == "segment":
        target_name = f"segment_{sequence or 0:04d}"
        label = f"视频片段 {sequence or 0}"
    else:
        target_name = "final"
        label = "完整视频"

    target_path = copy_preview_video(source_path, preview_dir, target_name)
    url = outputs_static_url(target_path)
    if not url:
        logger.warning(
            "MANIMGL_VIDEO_PREVIEW_PUBLISHED {}",
            json.dumps(
                {
                    "published": False,
                    "reason": "static_url_unavailable",
                    "source_path": str(source_path),
                    "status": status,
                    "target_path": str(target_path),
                },
                ensure_ascii=False,
            ),
        )
        return False

    content: dict[str, Any] = {
        "url": url,
        "status": status,
        "label": label,
        "mime_type": "video/mp4",
    }
    if sequence is not None:
        content["sequence"] = sequence

    published = publish_app_event(
        trace_id,
        {
            "type": "video_preview",
            "content": content,
        },
    )
    logger.info(
        "MANIMGL_VIDEO_PREVIEW_PUBLISHED {}",
        json.dumps(
            {
                "published": published,
                "sequence": sequence,
                "status": status,
                "target_path": str(target_path),
                "trace_id": trace_id,
                "url": url,
            },
            ensure_ascii=False,
        ),
    )
    return published


async def stream_manimgl_render(
    *,
    workdir: Path,
    code_path: Path,
    scene_name: str,
    subdivide: bool = True,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run ManimGL and yield progress lines followed by the final result."""
    write_manimgl_custom_config(workdir)
    video_dir = workdir / "videos"
    command = [
        sys.executable,
        "-m",
        "manimlib",
        code_path.name,
        scene_name,
        "-w",
        *manimgl_quality_args(),
        "--video_dir",
        str(video_dir),
        "--show_animation_progress",
    ]
    if subdivide:
        command.append("--subdivide")
    logger.info("Running ManimGL command: {}", command)
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(workdir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=build_manimgl_subprocess_env(workdir=workdir),
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()

    async def pump_stream(stream, stream_name: str, sink: list[str]) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            sink.append(text)
            await queue.put({"stream": stream_name, "line": text})

    pump_tasks = [
        asyncio.create_task(pump_stream(process.stdout, "stdout", stdout_lines)),
        asyncio.create_task(pump_stream(process.stderr, "stderr", stderr_lines)),
    ]
    wait_task = asyncio.create_task(process.wait())
    progress_line_count = 0

    while True:
        if wait_task.done() and queue.empty() and all(task.done() for task in pump_tasks):
            break
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue

        line = item["line"]
        progress_line_count += 1
        logger.info(
            "MANIMGL_RENDER_STREAM {}",
            json.dumps(
                {
                    "stream": item["stream"],
                    "line": compact_text(line, 400),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        yield {
            "type": "progress",
            "stream": item["stream"],
            "line": line,
        }

    await asyncio.gather(*pump_tasks)
    return_code = await wait_task
    yield {
        "type": "result",
        "ok": return_code == 0,
        "stdout": "\n".join(stdout_lines),
        "stderr": "\n".join(stderr_lines),
        "code": str(return_code),
        "progress_line_count": progress_line_count,
    }


class ManimGLRenderAgent(BaseAgent):
    """Render generated ManimGL code into a video artifact."""

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name: str, description: str = ""):
        super().__init__(name=name, description=description)

    def format_event(self, content_text: str | None = None, state_delta: Dict | None = None):
        """Create an ADK event with optional content and state updates."""
        event = Event(author=self.name)
        if state_delta:
            event.actions = EventActions(state_delta=state_delta)
        if content_text:
            event.content = Content(role="model", parts=[Part(text=content_text)])
        return event

    def _progress_event(self, line: str):
        """Create a throttled progress event for frontend status streams."""
        message = f"ManimGL 渲染中：{compact_text(line, 160)}"
        current_output = {
            "author": self.name,
            "status": "running",
            "message": message,
            "message_for_user": "ManimGL 渲染中",
            "output_text": "",
        }
        return self.format_event(message, {"current_output": current_output})

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Parse ManimGL code, synthesize narration, render, and save the video."""
        timing_context = timing_context_from_invocation(ctx)
        with timing_stage(
            "agent",
            self.name,
            **timing_context,
            metadata={"mode": "manimgl_math_video"},
        ) as agent_timing:
            manimgl_result_by_agent = ctx.session.state.get("math_video/manimgl_code", "")
            manimgl_result_size = manimgl_output_size(manimgl_result_by_agent)
            logger.info(
                "ManimGLRenderAgent received output type={} chars={} preview={}",
                type(manimgl_result_by_agent).__name__,
                manimgl_result_size,
                compact_text(manimgl_result_by_agent),
            )

            try:
                with timing_stage(
                    "parse",
                    "ManimGLRenderAgent.parse_manimgl_json",
                    **timing_context,
                    metadata={
                        "input_chars": manimgl_result_size,
                        "input_type": type(manimgl_result_by_agent).__name__,
                    },
                ):
                    manimgl_result = parse_manimgl_generation_output(manimgl_result_by_agent)
            except Exception as exc:
                agent_timing["status"] = "error"
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": "获取 ManimGL 代码错误",
                    "message_for_user": f"视频生成失败：{exc}",
                    "output_text": "",
                }
                yield self.format_event("ManimGL 视频生成失败。", {"current_output": current_output})
                return

            manimgl_code = str(manimgl_result.get("manimgl_code") or "")
            scene_name = str(manimgl_result.get("scene_name") or "").strip()
            narrations = normalize_narration_segments(manimgl_result.get("narrations"))
            if not manimgl_code or not scene_name:
                agent_timing["status"] = "error"
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": "ManimGL 代码或 scene_name 缺失",
                    "message_for_user": "视频生成失败：ManimGL 代码不完整。",
                    "output_text": "",
                }
                yield self.format_event("ManimGL 代码不完整。", {"current_output": current_output})
                return

            agent_timing["scene_name"] = scene_name
            agent_timing["code_chars"] = len(manimgl_code)
            agent_timing["narration_count"] = len(narrations)

            with tempfile.TemporaryDirectory() as temp_dir:
                workdir = Path(temp_dir)
                sounds_dir = workdir / "sounds"
                code_path = workdir / "manimgl_scene.py"
                preview_dir = build_preview_output_dir(ctx)
                previewed_paths: set[Path] = set()
                preview_sequence = 0
                final_preview_published = False
                trace_id = timing_context.get("trace_id")

                try:
                    validate_voiceover_references(manimgl_code, narrations)
                    with timing_stage(
                        "tts",
                        "ManimGLRenderAgent.synthesize_voiceover",
                        **timing_context,
                        metadata={"narration_count": len(narrations)},
                    ) as tts_timing:
                        audio_manifest = await asyncio.to_thread(
                            synthesize_manimgl_narrations,
                            narrations,
                            sounds_dir,
                        )
                        tts_timing["audio_count"] = len(audio_manifest)
                        tts_timing["cache_hit_count"] = sum(
                            1 for item in audio_manifest.values() if item.get("cache_hit")
                        )
                    manimgl_code = inject_narration_audio(manimgl_code, audio_manifest)
                except Exception as exc:
                    agent_timing["status"] = "error"
                    current_output = {
                        "author": self.name,
                        "status": "error",
                        "message": f"ManimGL 旁白合成失败：{exc}",
                        "message_for_user": f"视频生成失败：旁白合成失败。{exc}",
                        "output_text": "",
                    }
                    logger.error("ManimGL voiceover failed: {}", exc)
                    yield self.format_event("ManimGL 旁白合成失败。", {"current_output": current_output})
                    return

                code_path.write_text(manimgl_code, encoding="utf-8")
                last_progress_event_at = 0.0
                render_result: dict[str, Any] | None = None

                with timing_stage(
                    "manimgl",
                    "manimgl_subprocess",
                    **timing_context,
                    metadata={"scene_name": scene_name, "code_chars": len(manimgl_code)},
                ) as subprocess_timing:
                    async for update in stream_manimgl_render(
                        workdir=workdir,
                        code_path=code_path,
                        scene_name=scene_name,
                    ):
                        if update.get("type") == "result":
                            render_result = update
                            subprocess_timing["return_code"] = update["code"]
                            subprocess_timing["render_ok"] = update["ok"]
                            subprocess_timing["progress_line_count"] = update.get(
                                "progress_line_count", 0
                            )
                            if not update["ok"]:
                                subprocess_timing["status"] = "error"
                            continue

                        line = str(update.get("line") or "")
                        now = time.monotonic()
                        ready_path = ready_file_path_from_line(line, workdir)
                        if (
                            ready_path
                            and ready_path.suffix.lower() == ".mp4"
                            and ready_path not in previewed_paths
                        ):
                            previewed_paths.add(ready_path)
                            if ready_path.stem.isdigit():
                                preview_sequence += 1
                                publish_video_preview(
                                    trace_id=trace_id,
                                    source_path=ready_path,
                                    preview_dir=preview_dir,
                                    status="segment",
                                    sequence=preview_sequence,
                                )
                            else:
                                final_preview_published = publish_video_preview(
                                    trace_id=trace_id,
                                    source_path=ready_path,
                                    preview_dir=preview_dir,
                                    status="final",
                                )

                        if line and now - last_progress_event_at >= 2.0:
                            last_progress_event_at = now
                            yield self._progress_event(line)

                render_result = render_result or {
                    "ok": False,
                    "stdout": "",
                    "stderr": "ManimGL subprocess did not return a result.",
                    "code": "-1",
                    "progress_line_count": 0,
                }
                render_summary = summarize_manimgl_result(render_result)
                logger.info(
                    "MANIMGL_RENDER_SUMMARY {}",
                    json.dumps(render_summary, ensure_ascii=False, sort_keys=True),
                )
                agent_timing.update(render_summary)

                if not render_result["ok"]:
                    agent_timing["status"] = "error"
                    error_message = (
                        str(render_result.get("stdout") or "")
                        + "\n"
                        + str(render_result.get("stderr") or "")
                        + "\n"
                        + str(render_result.get("code") or "")
                    )
                    step = ctx.session.state.get("step", 0)
                    error_text = f"执行步骤{step + 1}: {self.name}执行出错：{error_message}"
                    current_output = {
                        "author": self.name,
                        "status": "error",
                        "message": error_text,
                        "message_for_user": "ManimGL 视频渲染失败。",
                        "output_text": "",
                    }
                    logger.error("ManimGLRenderAgent failed: {}", compact_text(error_text, 1000))
                    yield self.format_event(error_text, {"current_output": current_output})
                    return

                mp4_path = find_rendered_mp4(workdir)
                if mp4_path is None:
                    agent_timing["status"] = "error"
                    current_output = {
                        "author": self.name,
                        "status": "error",
                        "message": "ManimGL mp4 文件生成失败",
                        "message_for_user": "ManimGL 视频生成失败：未找到 mp4 文件。",
                        "output_text": "",
                    }
                    yield self.format_event("ManimGL mp4 文件生成失败。", {"current_output": current_output})
                    return

                video_bytes = mp4_path.read_bytes()
                agent_timing["video_bytes"] = len(video_bytes)
                if not final_preview_published:
                    publish_video_preview(
                        trace_id=trace_id,
                        source_path=mp4_path,
                        preview_dir=preview_dir,
                        status="final",
                    )

            step = ctx.session.state.get("step", 0)
            artifact_name = f"step{step + 1}_manimgl_video_output.mp4"
            artifact_part = Part(inline_data=Blob(mime_type="video/mp4", data=video_bytes))
            with timing_stage(
                "artifact",
                "ManimGLRenderAgent.save_video_artifact",
                **timing_context,
                metadata={"artifact_name": artifact_name, "video_bytes": len(video_bytes)},
            ):
                await ctx.artifact_service.save_artifact(
                    app_name=ctx.session.app_name,
                    user_id=ctx.session.user_id,
                    session_id=ctx.session.id,
                    filename=artifact_name,
                    artifact=artifact_part,
                )

            text = (
                f"执行步骤{step + 1}: {self.name}：ManimGL 视频生成完成\n"
                f"视频保存成功，输出视频名称为{artifact_name}"
            )
            output_artifacts = [
                {
                    "name": artifact_name,
                    "description": (
                        "ManimGL 生成的数学讲解视频。"
                        f"\nscene_name：{scene_name}\n"
                        f"manimgl_code：{manimgl_code}\n"
                    ),
                }
            ]
            current_output = {
                "author": self.name,
                "status": "success",
                "message": text,
                "message_for_user": "数学讲解视频生成完成",
                "output_artifacts": output_artifacts,
                "output_text": "",
            }
            yield self.format_event(text, {"current_output": current_output})
