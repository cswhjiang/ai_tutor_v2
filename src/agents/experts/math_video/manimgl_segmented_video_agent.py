from __future__ import annotations

import ast
import asyncio
import datetime
import json
import re
import shutil
import tempfile
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Dict

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models import LlmRequest
from google.genai.types import Blob, Content, Part
from pydantic import BaseModel, Field
from typing_extensions import override

from conf.system import SYS_CONFIG
from src.agents.experts.math_video.manimgl_render_agent import (
    build_preview_output_dir,
    find_rendered_mp4,
    inject_narration_audio,
    normalize_narration_segments,
    publish_video_preview,
    stream_manimgl_render,
    summarize_manimgl_result,
    synthesize_manimgl_narrations,
    sanitize_path_part,
    validate_voiceover_references,
)
from src.agents.experts.math_video.manimgl_shot_agent import MANIMGL_SHOT_DESIGN_KEY
from src.agents.experts.math_video.manimgl_solution_agent import MANIMGL_SOLUTION_KEY
from src.llm.model_factory import build_model_kwargs, resolve_agent_llm_settings
from src.logger import logger
from src.media.output_urls import OUTPUTS_ROOT
from src.observability.timing import compact_text, timing_context_from_invocation, timing_stage
from src.utils import clean_json_string


MANIMGL_CURRENT_SEGMENT_KEY = "math_video/manimgl_current_segment"
MANIMGL_SEGMENT_CODE_KEY = "math_video/manimgl_segment_code"
MANIMGL_SEGMENT_RETRY_CONTEXT_KEY = "math_video/manimgl_segment_retry_context"
MAX_SEGMENT_RENDER_ATTEMPTS = 2

FORBIDDEN_MANIMGL_SYMBOLS = {
    "Create",
    "MathTex",
    "MarkupText",
    "TransformFromParagraph",
    "TransformMatchingShapes",
    "TransformMatchingTex",
    "VoiceoverScene",
    "always_redraw",
    "get_part_by_tex",
    "get_parts_by_tex",
    "get_part_by_text",
    "manim_voiceover",
    "select_part",
    "select_parts",
    "select_unisolated_substring",
    "voiceover",
}

ALLOWED_MANIMGL_CALL_SYMBOLS = {
    "AnimationGroup",
    "ApplyMethod",
    "Arrow",
    "Brace",
    "Circle",
    "DecimalNumber",
    "Dot",
    "FadeIn",
    "FadeOut",
    "FadeTransform",
    "GrowArrow",
    "Indicate",
    "Integer",
    "LaggedStart",
    "Line",
    "NumberLine",
    "Polygon",
    "Rectangle",
    "ReplacementTransform",
    "RoundedRectangle",
    "Scene",
    "ShowCreation",
    "SurroundingRectangle",
    "Tex",
    "TexText",
    "Text",
    "Transform",
    "VGroup",
    "Write",
}


class ManimGLCodeValidationError(ValueError):
    """Raised when generated ManimGL code fails local static validation."""


class ManimGLSegmentNarration(BaseModel):
    """Narration segment used by one semantic ManimGL video segment."""

    key: str = Field(description="Unique narration key referenced by start_voiceover.")
    text: str = Field(description="Narration text to synthesize with TTS.")


class ManimGLSegmentCodeOutput(BaseModel):
    """Structured output contract for one self-contained ManimGL segment."""

    scene_name: str = Field(description="ManimGL Scene class name for this segment.")
    manimgl_code: str = Field(description="Complete executable ManimGL Python code for this segment.")
    narrations: list[ManimGLSegmentNarration] = Field(
        description="Narration list matching NARRATION_SEGMENTS in the segment code."
    )


def sanitize_narration_key(value: Any, fallback: str) -> str:
    """Return a stable narration key for generated segment state."""
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value or "").strip()).strip("_")
    return normalized or fallback


def parse_manimgl_shot_design(raw_output: Any) -> dict[str, Any]:
    """Parse ManimGL shot-design output into a dictionary."""
    if isinstance(raw_output, dict):
        return raw_output
    if isinstance(raw_output, str):
        parsed = json.loads(clean_json_string(raw_output))
        if isinstance(parsed, dict):
            return parsed
    raise TypeError(
        "math_video/manimgl_shot_design must be a structured dict or JSON string, "
        f"got {type(raw_output).__name__}"
    )


def normalize_manimgl_shots(raw_output: Any) -> list[dict[str, Any]]:
    """Return normalized semantic shots that can be generated and rendered independently."""
    shot_design = parse_manimgl_shot_design(raw_output)
    raw_shots = shot_design.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        raise ValueError("ManimGL 分镜缺少 shots，无法分段生成视频。")

    title = str(shot_design.get("title") or "数学讲解视频").strip()
    summary = str(shot_design.get("summary") or "").strip()
    style = shot_design.get("style") if isinstance(shot_design.get("style"), dict) else {}

    normalized: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    total = len(raw_shots)
    for index, raw_shot in enumerate(raw_shots, start=1):
        if not isinstance(raw_shot, dict):
            continue

        narration = str(raw_shot.get("narration") or "").strip()
        if not narration:
            continue

        fallback_key = f"segment_{index:02d}"
        narration_key = sanitize_narration_key(raw_shot.get("narration_key"), fallback_key)
        if narration_key in seen_keys:
            narration_key = f"{narration_key}_{index:02d}"
        seen_keys.add(narration_key)

        try:
            duration_seconds = float(raw_shot.get("duration_seconds") or 8.0)
        except (TypeError, ValueError):
            duration_seconds = 8.0
        duration_seconds = max(4.0, min(duration_seconds, 30.0))

        normalized.append(
            {
                "index": index,
                "total": total,
                "title": title,
                "summary": summary,
                "style": style,
                "narration_key": narration_key,
                "duration_seconds": duration_seconds,
                "narration": narration,
                "shot": {
                    **raw_shot,
                    "narration_key": narration_key,
                    "duration_seconds": duration_seconds,
                    "narration": narration,
                },
            }
        )

    if not normalized:
        raise ValueError("ManimGL 分镜中没有有效旁白镜头，无法分段生成视频。")
    return normalized


def parse_manimgl_segment_code_output(raw_output: Any) -> dict[str, Any]:
    """Parse one segment code-generation output."""
    if isinstance(raw_output, dict):
        return raw_output
    if isinstance(raw_output, str):
        parsed = json.loads(clean_json_string(raw_output))
        if isinstance(parsed, dict):
            return parsed
    raise TypeError(
        "math_video/manimgl_segment_code must be a structured dict or JSON string, "
        f"got {type(raw_output).__name__}"
    )


def called_symbol_name(node: ast.AST) -> str | None:
    """Return the direct call symbol name for an AST call function."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def validate_manimgl_code_symbols(manim_code: str) -> None:
    """
    Reject generated code that clearly uses unsupported ManimGL symbols.

    This is intentionally conservative: prompts reduce bad output, but this
    local gate prevents known ManimCE APIs and hallucinated animation classes
    from reaching the expensive TTS/render stages.
    """
    errors: list[str] = []
    if "from manimlib import *" not in manim_code:
        errors.append("missing required import: from manimlib import *")
    if re.search(r"from\s+manim\s+import|import\s+manim(?:\s|$)", manim_code):
        errors.append("ManimCE import is not allowed")

    for symbol in sorted(FORBIDDEN_MANIMGL_SYMBOLS):
        if re.search(rf"\b{re.escape(symbol)}\b", manim_code):
            errors.append(f"unsupported ManimGL symbol: {symbol}")

    try:
        tree = ast.parse(manim_code)
    except SyntaxError as exc:
        raise ManimGLCodeValidationError(f"generated Python syntax error: {exc}") from exc

    defined_symbols = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        symbol = called_symbol_name(node.func)
        if not symbol:
            continue
        if symbol in FORBIDDEN_MANIMGL_SYMBOLS:
            errors.append(f"unsupported ManimGL symbol: {symbol}")
            continue
        if (
            symbol[:1].isupper()
            and symbol not in ALLOWED_MANIMGL_CALL_SYMBOLS
            and symbol not in defined_symbols
        ):
            errors.append(f"unknown ManimGL call symbol: {symbol}")

    unique_errors = sorted(set(errors))
    if unique_errors:
        raise ManimGLCodeValidationError("; ".join(unique_errors))


def build_segment_debug_dir(trace_id: str | None) -> Path:
    """Return a stable debug output directory for generated segment code."""
    directory_name = sanitize_path_part(trace_id or f"unknown_{int(time.time())}")
    debug_dir = OUTPUTS_ROOT / "debug" / "manimgl_segment_code" / directory_name
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir


def write_segment_debug_artifacts(
    *,
    trace_id: str | None,
    segment: dict[str, Any],
    segment_result: dict[str, Any],
    attempt: int,
    label: str,
) -> dict[str, str]:
    """Persist generated segment code and context for debugging."""
    segment_index = int(segment["index"])
    debug_dir = build_segment_debug_dir(trace_id)
    prefix = f"segment_{segment_index:02d}_attempt_{attempt:02d}_{label}"
    code_path = debug_dir / f"{prefix}.py"
    output_path = debug_dir / f"{prefix}_generation_output.json"
    context_path = debug_dir / f"segment_{segment_index:02d}_context.json"

    code_path.write_text(str(segment_result.get("manimgl_code") or ""), encoding="utf-8")
    output_path.write_text(
        json.dumps(segment_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context_path.write_text(json.dumps(segment, ensure_ascii=False, indent=2), encoding="utf-8")

    paths = {
        "code_path": str(code_path.resolve()),
        "generation_output_path": str(output_path.resolve()),
        "context_path": str(context_path.resolve()),
    }
    logger.info(
        "MANIMGL_SEGMENT_CODE_DEBUG_FILES {}",
        json.dumps(
            {
                "attempt": attempt,
                "label": label,
                "segment_index": segment_index,
                **paths,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return paths


def build_segment_retry_context(
    *,
    error: Exception,
    segment_result: dict[str, Any] | None,
) -> dict[str, str]:
    """Build retry instructions from a failed segment generation/render attempt."""
    previous_code = ""
    if segment_result:
        previous_code = str(segment_result.get("manimgl_code") or "")
    return {
        "error": compact_text(str(error), 2000),
        "previous_code": previous_code[:8000],
    }


def escape_ffmpeg_concat_path(path: Path) -> str:
    """Escape one path for ffmpeg concat demuxer file syntax."""
    return str(path.resolve()).replace("'", "'\\''")


async def run_subprocess_capture(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run a subprocess and return captured text output."""
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return {
        "code": process.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    }


async def concat_segment_videos(segment_paths: list[Path], output_path: Path) -> dict[str, Any]:
    """Concatenate semantic segment videos into one final mp4."""
    if not segment_paths:
        raise ValueError("No segment videos to concatenate.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(segment_paths) == 1:
        shutil.copy2(segment_paths[0], output_path)
        return {"code": 0, "stdout": "", "stderr": "", "method": "copy_single"}

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to concatenate ManimGL segment videos.")

    concat_file = output_path.with_suffix(".concat.txt")
    concat_file.write_text(
        "\n".join(f"file '{escape_ffmpeg_concat_path(path)}'" for path in segment_paths) + "\n",
        encoding="utf-8",
    )

    copy_command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(output_path),
    ]
    result = await run_subprocess_capture(copy_command, cwd=output_path.parent)
    if result["code"] == 0 and output_path.exists():
        result["method"] = "stream_copy"
        return result

    reencode_command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    fallback = await run_subprocess_capture(reencode_command, cwd=output_path.parent)
    fallback["method"] = "reencode"
    if fallback["code"] != 0 or not output_path.exists():
        raise RuntimeError(
            "ffmpeg concat failed: "
            + compact_text(result.get("stderr", ""), 500)
            + " | fallback: "
            + compact_text(fallback.get("stderr", ""), 500)
        )
    return fallback


async def manimgl_segment_code_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Build the model request for one semantic ManimGL segment."""
    current_parameters = callback_context.state.get("current_parameters", {})
    solution = callback_context.state.get(MANIMGL_SOLUTION_KEY, "")
    segment = callback_context.state.get(MANIMGL_CURRENT_SEGMENT_KEY, {})
    retry_context = callback_context.state.get(MANIMGL_SEGMENT_RETRY_CONTEXT_KEY)

    current_prompt = current_parameters["prompt"]
    current_info = current_parameters.get("current_info", "null")
    segment_json = json.dumps(segment, ensure_ascii=False, indent=2)

    llm_request.contents.append(
        Content(
            role="user",
            parts=[
                Part(
                    text=(
                        f"当前任务：{current_prompt}\n"
                        f"当前已经收集到的信息：{current_info}\n"
                        f"当前要生成的是第 {segment.get('index')} / {segment.get('total')} 个视频片段。\n"
                        f"当前片段分镜 JSON：\n{segment_json}\n"
                    )
                )
            ],
        )
    )

    if solution:
        llm_request.contents.append(
            Content(
                role="user",
                parts=[Part(text=f"完整解题步骤，仅用于保持数学正确性：\n{solution}\n")],
            )
        )

    if isinstance(retry_context, dict) and retry_context.get("error"):
        llm_request.contents.append(
            Content(
                role="user",
                parts=[
                    Part(
                        text=(
                            "上一次生成的当前片段代码没有通过校验或渲染。"
                            "请只修复当前片段，保持 JSON 输出格式不变，不要复用错误 API。\n"
                            f"错误信息：\n{retry_context.get('error')}\n\n"
                            f"上一次代码：\n```python\n{retry_context.get('previous_code', '')}\n```\n"
                        )
                    )
                ],
            )
        )


class ManimGLSegmentedVideoAgent(BaseAgent):
    """Generate, render, preview, and concatenate ManimGL semantic video segments."""

    model_config = {"arbitrary_types_allowed": True}
    segment_code_llm: LlmAgent

    def __init__(
        self,
        name: str,
        description: str = "",
        llm_model: str = "",
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.llm_model
        segment_agent_name = "ManimGLSegmentCodeGenerationAgent"
        resolved_llm_model, _ = resolve_agent_llm_settings(
            llm_model,
            agent_name=segment_agent_name,
        )
        logger.info(f"{segment_agent_name}: using llm: {resolved_llm_model}")

        model_kwargs = build_model_kwargs(
            llm_model,
            response_json=True,
            agent_name=segment_agent_name,
        )
        time_str = datetime.date.today().strftime("%Y-%m-%d")
        segment_code_llm = LlmAgent(
            name=segment_agent_name,
            **model_kwargs,
            description="Generate one self-contained ManimGL code segment.",
            instruction=MANIMGL_SEGMENT_CODE_GENERATION_INSTRUCTION.replace(
                "{TIME_STR}",
                time_str,
            ),
            before_model_callback=manimgl_segment_code_before_model_callback,
            output_schema=ManimGLSegmentCodeOutput,
            output_key=MANIMGL_SEGMENT_CODE_KEY,
        )
        super().__init__(
            name=name,
            description=description,
            segment_code_llm=segment_code_llm,
        )

    def format_event(self, content_text: str | None = None, state_delta: Dict | None = None):
        """Create an ADK event with optional content and state updates."""
        event = Event(author=self.name)
        if state_delta:
            event.actions = EventActions(state_delta=state_delta)
        if content_text:
            event.content = Content(role="model", parts=[Part(text=content_text)])
        return event

    def _status_event(self, message: str):
        """Create a user-facing running status event."""
        current_output = {
            "author": self.name,
            "status": "running",
            "message": message,
            "message_for_user": message,
            "output_text": "",
        }
        return self.format_event(message, {"current_output": current_output})

    def _progress_event(self, segment_index: int, line: str):
        """Create a throttled progress event for frontend status streams."""
        message = f"第 {segment_index} 段 ManimGL 渲染中：{compact_text(line, 120)}"
        current_output = {
            "author": self.name,
            "status": "running",
            "message": message,
            "message_for_user": "ManimGL 分段渲染中",
            "output_text": "",
        }
        return self.format_event(message, {"current_output": current_output})

    async def _generate_segment_code(
        self,
        ctx: InvocationContext,
        segment: dict[str, Any],
        timing_context: dict[str, Any],
        *,
        attempt: int,
        retry_context: dict[str, str] | None = None,
    ) -> AsyncGenerator[Event | dict[str, Any], None]:
        """Generate executable ManimGL code for one segment."""
        segment_index = int(segment["index"])
        segment_name = f"segment_{segment_index:02d}_attempt_{attempt:02d}"
        ctx.session.state[MANIMGL_CURRENT_SEGMENT_KEY] = segment
        ctx.session.state[MANIMGL_SEGMENT_CODE_KEY] = None
        ctx.session.state[MANIMGL_SEGMENT_RETRY_CONTEXT_KEY] = retry_context

        yield self.format_event(
            None,
            {
                MANIMGL_CURRENT_SEGMENT_KEY: segment,
                MANIMGL_SEGMENT_CODE_KEY: None,
                MANIMGL_SEGMENT_RETRY_CONTEXT_KEY: retry_context,
            },
        )

        with timing_stage(
            "agent",
            f"ManimGLSegmentCodeGenerationAgent.{segment_name}",
            **timing_context,
            metadata={"attempt": attempt, "segment_index": segment_index},
        ) as agent_timing:
            text_list: list[str] = []
            with timing_stage(
                "llm",
                f"ManimGLSegmentCodeGenerationAgent.{segment_name}.llm",
                **timing_context,
                metadata={
                    "attempt": attempt,
                    "output_key": MANIMGL_SEGMENT_CODE_KEY,
                    "segment_index": segment_index,
                },
            ):
                async for event in self.segment_code_llm.run_async(ctx):
                    if event.is_final_response() and event.content and event.content.parts:
                        generated_text = next(
                            (part.text for part in event.content.parts if part.text),
                            None,
                        )
                        if generated_text:
                            text_list.append(generated_text)
                    yield event

            raw_output = ctx.session.state.get(MANIMGL_SEGMENT_CODE_KEY)
            if raw_output is None and text_list:
                raw_output = "\n".join(text_list)
            if raw_output is None:
                agent_timing["status"] = "error"
                raise RuntimeError(f"第 {segment_index} 段 ManimGL 代码生成失败。")

            parsed_output = parse_manimgl_segment_code_output(raw_output)
            agent_timing["output_chars"] = len(json.dumps(parsed_output, ensure_ascii=False))
            yield parsed_output

    async def _render_segment(
        self,
        *,
        ctx: InvocationContext,
        segment: dict[str, Any],
        segment_result: dict[str, Any],
        segment_workdir: Path,
        preview_dir: Path,
        trace_id: str | None,
        timing_context: dict[str, Any],
        attempt: int,
    ) -> AsyncGenerator[Event | dict[str, Any], None]:
        """Render one generated ManimGL segment and publish its preview."""
        segment_index = int(segment["index"])
        segment_name = f"segment_{segment_index:02d}"
        segment_workdir.mkdir(parents=True, exist_ok=True)
        sounds_dir = segment_workdir / "sounds"
        code_path = segment_workdir / "manimgl_segment.py"

        manimgl_code = str(segment_result.get("manimgl_code") or "")
        scene_name = str(segment_result.get("scene_name") or "").strip()
        narrations = normalize_narration_segments(segment_result.get("narrations"))
        if not narrations:
            narrations = [
                {
                    "key": str(segment["narration_key"]),
                    "text": str(segment["narration"]),
                }
            ]
        if not manimgl_code or not scene_name:
            raise ValueError(f"第 {segment_index} 段 ManimGL 代码或 scene_name 缺失。")

        raw_debug_paths = write_segment_debug_artifacts(
            trace_id=trace_id,
            segment=segment,
            segment_result=segment_result,
            attempt=attempt,
            label="raw",
        )
        with timing_stage(
            "validation",
            f"ManimGLSegmentedRender.{segment_name}.validate_code",
            **timing_context,
            metadata={
                "attempt": attempt,
                "code_chars": len(manimgl_code),
                "code_path": raw_debug_paths["code_path"],
                "scene_name": scene_name,
                "segment_index": segment_index,
            },
        ):
            try:
                validate_manimgl_code_symbols(manimgl_code)
                validate_voiceover_references(manim_code=manimgl_code, narrations=narrations)
            except Exception as exc:
                raise ManimGLCodeValidationError(
                    f"{exc}；生成代码已保存到 {raw_debug_paths['code_path']}"
                ) from exc

        with timing_stage(
            "tts",
            f"ManimGLSegmentedRender.{segment_name}.tts",
            **timing_context,
            metadata={
                "attempt": attempt,
                "segment_index": segment_index,
                "narration_count": len(narrations),
            },
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
        render_segment_result = {**segment_result, "manimgl_code": manimgl_code}
        render_debug_paths = write_segment_debug_artifacts(
            trace_id=trace_id,
            segment=segment,
            segment_result=render_segment_result,
            attempt=attempt,
            label="render",
        )
        code_path.write_text(manimgl_code, encoding="utf-8")

        render_result: dict[str, Any] | None = None
        last_progress_event_at = 0.0
        with timing_stage(
            "manimgl",
            f"ManimGLSegmentedRender.{segment_name}.render",
            **timing_context,
            metadata={
                "attempt": attempt,
                "segment_index": segment_index,
                "scene_name": scene_name,
                "code_chars": len(manimgl_code),
                "code_path": render_debug_paths["code_path"],
            },
        ) as render_timing:
            async for update in stream_manimgl_render(
                workdir=segment_workdir,
                code_path=code_path,
                scene_name=scene_name,
                subdivide=False,
            ):
                if update.get("type") == "result":
                    render_result = update
                    render_timing["return_code"] = update["code"]
                    render_timing["render_ok"] = update["ok"]
                    render_timing["progress_line_count"] = update.get("progress_line_count", 0)
                    if not update["ok"]:
                        render_timing["status"] = "error"
                    continue

                line = str(update.get("line") or "")
                now = time.monotonic()
                if line and now - last_progress_event_at >= 2.0:
                    last_progress_event_at = now
                    yield self._progress_event(segment_index, line)

        render_result = render_result or {
            "ok": False,
            "stdout": "",
            "stderr": "ManimGL subprocess did not return a result.",
            "code": "-1",
            "progress_line_count": 0,
        }
        render_summary = summarize_manimgl_result(render_result)
        logger.info(
            "MANIMGL_SEGMENT_RENDER_SUMMARY {}",
            json.dumps(
                {
                    **render_summary,
                    "segment_index": segment_index,
                    "scene_name": scene_name,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        if not render_result["ok"]:
            raise RuntimeError(
                f"第 {segment_index} 段 ManimGL 渲染失败："
                + compact_text(
                    str(render_result.get("stdout") or "")
                    + "\n"
                    + str(render_result.get("stderr") or ""),
                    1000,
                )
                + f"；生成代码已保存到 {render_debug_paths['code_path']}"
            )

        mp4_path = find_rendered_mp4(segment_workdir)
        if mp4_path is None:
            raise RuntimeError(f"第 {segment_index} 段 ManimGL 未生成 mp4 文件。")

        semantic_path = segment_workdir / f"semantic_segment_{segment_index:04d}.mp4"
        shutil.copy2(mp4_path, semantic_path)
        publish_video_preview(
            trace_id=trace_id,
            source_path=semantic_path,
            preview_dir=preview_dir,
            status="segment",
            sequence=segment_index,
        )
        yield {
            "path": semantic_path,
            "scene_name": scene_name,
            "code": manimgl_code,
            "debug_code_path": render_debug_paths["code_path"],
            "video_bytes": semantic_path.stat().st_size,
        }

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Generate semantic ManimGL segments, preview each segment, and save the final video."""
        current_parameters = ctx.session.state.get("current_parameters", {})
        if "prompt" not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：prompt"
            current_output = {
                "author": self.name,
                "status": "error",
                "message": error_text,
                "output_text": "",
            }
            logger.error(error_text)
            yield self.format_event(error_text, {"current_output": current_output})
            return

        timing_context = timing_context_from_invocation(ctx)
        with timing_stage(
            "agent",
            self.name,
            **timing_context,
            metadata={"mode": "manimgl_segmented_math_video"},
        ) as agent_timing:
            try:
                segments = normalize_manimgl_shots(
                    ctx.session.state.get(MANIMGL_SHOT_DESIGN_KEY, "")
                )
            except Exception as exc:
                agent_timing["status"] = "error"
                current_output = {
                    "author": self.name,
                    "status": "error",
                    "message": f"ManimGL 分镜解析失败：{exc}",
                    "message_for_user": f"视频生成失败：分镜解析失败。{exc}",
                    "output_text": "",
                }
                yield self.format_event("ManimGL 分镜解析失败。", {"current_output": current_output})
                return

            agent_timing["segment_count"] = len(segments)
            trace_id = timing_context.get("trace_id")

            with tempfile.TemporaryDirectory() as temp_dir:
                workdir = Path(temp_dir)
                preview_dir = build_preview_output_dir(ctx)
                segment_paths: list[Path] = []
                segment_outputs: list[dict[str, Any]] = []

                for segment in segments:
                    segment_index = int(segment["index"])
                    yield self._status_event(
                        f"正在生成第 {segment_index}/{len(segments)} 段讲解视频..."
                    )

                    rendered_segment: dict[str, Any] | None = None
                    retry_context: dict[str, str] | None = None
                    last_error: Exception | None = None
                    for attempt in range(1, MAX_SEGMENT_RENDER_ATTEMPTS + 1):
                        if attempt > 1:
                            yield self._status_event(
                                f"第 {segment_index} 段生成失败，正在修复后重试第 {attempt} 次..."
                            )

                        generated_segment: dict[str, Any] | None = None
                        try:
                            async for item in self._generate_segment_code(
                                ctx=ctx,
                                segment=segment,
                                timing_context=timing_context,
                                attempt=attempt,
                                retry_context=retry_context,
                            ):
                                if isinstance(item, Event):
                                    yield item
                                else:
                                    generated_segment = item

                            if generated_segment is None:
                                raise RuntimeError(f"第 {segment_index} 段代码生成结果为空。")

                            async for item in self._render_segment(
                                ctx=ctx,
                                segment=segment,
                                segment_result=generated_segment,
                                segment_workdir=workdir
                                / f"segment_{segment_index:02d}_attempt_{attempt:02d}",
                                preview_dir=preview_dir,
                                trace_id=trace_id,
                                timing_context=timing_context,
                                attempt=attempt,
                            ):
                                if isinstance(item, Event):
                                    yield item
                                else:
                                    rendered_segment = item

                            if rendered_segment is None:
                                raise RuntimeError(f"第 {segment_index} 段渲染结果为空。")
                            break
                        except Exception as exc:
                            last_error = exc
                            retry_context = build_segment_retry_context(
                                error=exc,
                                segment_result=generated_segment,
                            )
                            logger.warning(
                                "ManimGL segment {} attempt {} failed: {}",
                                segment_index,
                                attempt,
                                exc,
                            )
                            if attempt < MAX_SEGMENT_RENDER_ATTEMPTS:
                                continue

                    if rendered_segment is None:
                        exc = last_error or RuntimeError(f"第 {segment_index} 段生成失败。")
                        agent_timing["status"] = "error"
                        current_output = {
                            "author": self.name,
                            "status": "error",
                            "message": f"ManimGL 分段视频生成失败：{exc}",
                            "message_for_user": f"视频生成失败：第 {segment_index} 段生成失败。{exc}",
                            "output_text": "",
                        }
                        logger.error("ManimGL segmented video failed: {}", exc)
                        yield self.format_event(
                            "ManimGL 分段视频生成失败。",
                            {"current_output": current_output},
                        )
                        return

                    segment_paths.append(Path(rendered_segment["path"]))
                    segment_outputs.append(rendered_segment)

                final_path = workdir / "final.mp4"
                try:
                    with timing_stage(
                        "artifact",
                        "ManimGLSegmentedRender.concat_final",
                        **timing_context,
                        metadata={"segment_count": len(segment_paths)},
                    ) as concat_timing:
                        concat_result = await concat_segment_videos(segment_paths, final_path)
                        concat_timing["method"] = concat_result.get("method")
                        concat_timing["return_code"] = concat_result.get("code")
                    publish_video_preview(
                        trace_id=trace_id,
                        source_path=final_path,
                        preview_dir=preview_dir,
                        status="final",
                    )
                    video_bytes = final_path.read_bytes()
                except Exception as exc:
                    agent_timing["status"] = "error"
                    current_output = {
                        "author": self.name,
                        "status": "error",
                        "message": f"ManimGL 最终视频拼接失败：{exc}",
                        "message_for_user": f"视频生成失败：最终视频拼接失败。{exc}",
                        "output_text": "",
                    }
                    logger.error("ManimGL final concat failed: {}", exc)
                    yield self.format_event("ManimGL 最终视频拼接失败。", {"current_output": current_output})
                    return

            agent_timing["video_bytes"] = len(video_bytes)
            step = ctx.session.state.get("step", 0)
            artifact_name = f"step{step + 1}_manimgl_segmented_video_output.mp4"
            artifact_part = Part(inline_data=Blob(mime_type="video/mp4", data=video_bytes))
            with timing_stage(
                "artifact",
                "ManimGLSegmentedVideoAgent.save_video_artifact",
                **timing_context,
                metadata={
                    "artifact_name": artifact_name,
                    "video_bytes": len(video_bytes),
                    "segment_count": len(segment_outputs),
                },
            ):
                await ctx.artifact_service.save_artifact(
                    app_name=ctx.session.app_name,
                    user_id=ctx.session.user_id,
                    session_id=ctx.session.id,
                    filename=artifact_name,
                    artifact=artifact_part,
                )

            text = (
                f"执行步骤{step + 1}: {self.name}：ManimGL 分段视频生成完成\n"
                f"视频保存成功，输出视频名称为{artifact_name}"
            )
            output_artifacts = [
                {
                    "name": artifact_name,
                    "description": (
                        "ManimGL 分段生成并拼接的数学讲解视频。"
                        f"\nsegment_count：{len(segment_outputs)}\n"
                        f"scene_names：{[item.get('scene_name') for item in segment_outputs]}\n"
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


MANIMGL_SEGMENT_CODE_GENERATION_INSTRUCTION = """
你是一名【ManimGL（3Blue1Brown 版本 manimlib）】动画工程师。

你现在不是生成完整视频，而是只生成一个【可独立运行、带音频的语义视频片段】。
每个片段会被系统单独渲染，渲染完成后立即推送给前端，最后由系统用 ffmpeg 拼接成完整视频。

# 必要信息
- 当前时间：{TIME_STR}

# 输出格式
你必须只输出一个 JSON 对象，不要输出 Markdown，不要解释。字段必须是：
{
  "scene_name": "ManimGL 场景类名",
  "manimgl_code": "当前片段的完整可执行 Python 代码字符串",
  "narrations": [
    {"key": "intro", "text": "当前片段的旁白文本，必须和代码中的 key 对应"}
  ]
}

# 当前片段约束
- 只实现输入里的当前片段，不要生成其他片段，不要总结完整视频结构。
- 场景类必须继承 `Scene`，且类名必须等于 `scene_name`。
- 代码必须可以独立保存为单个 `.py` 文件并通过 `python -m manimlib file.py SceneName -w -l` 运行。
- 每个片段必须有音频：代码必须包含 `NARRATION_AUDIO = {}`、`NARRATION_SEGMENTS = [...]` 和 `start_voiceover(...)`。
- `narrations`、`NARRATION_SEGMENTS`、`start_voiceover(self, key, ...)` 三处 key 必须完全一致。
- 当前片段通常只需要 1 个 narration key。除非分镜明确要求，否则不要拆成多个旁白 key。

# ManimGL 技术约束
- 必须使用 `from manimlib import *`。
- 禁止使用 Manim Community Edition 专属 API：`from manim import *`、`MathTex`、`MarkupText`、`Create`、`VoiceoverScene`、`self.voiceover`、`manim_voiceover`。
- 只允许使用下列常用对象/辅助类：`Text`、`Tex`、`TexText`、`VGroup`、`Rectangle`、`RoundedRectangle`、`SurroundingRectangle`、`Line`、`Arrow`、`Circle`、`Dot`、`Brace`、`NumberLine`、`DecimalNumber`、`Integer`。
- 只允许使用下列动画类：`Write`、`FadeIn`、`FadeOut`、`ShowCreation`、`Transform`、`ReplacementTransform`、`FadeTransform`、`Indicate`、`ApplyMethod`、`GrowArrow`、`AnimationGroup`、`LaggedStart`。
- 禁止使用任何未列出的动画类，尤其禁止：`TransformFromParagraph`、`TransformMatchingTex`、`TransformMatchingShapes`。
- 中文文本用 `Text("中文", font="PingFang SC")`；不要把中文放进 `Tex` 公式。
- 公式使用 `Tex(r"...")`，公式里只放数学符号、英文和数字。
- 不依赖外部图片、外部音频、网络资源或第三方字体文件。

# 稳定性硬性要求
- 禁止使用 `get_part_by_tex`、`get_parts_by_tex`、`select_part`、`select_parts`、`get_part_by_text`、`select_unisolated_substring`。
- 不要从一个整块 `Tex` 或 `Text` 内部选择局部字符再上色、放大或动画。
- 如果需要突出变量、数字或等号，必须在创建时就拆成独立对象，例如：
```python
r = Tex("R", color=RED)
plus = Tex("+")
y = Tex("Y", color=YELLOW)
eq = Tex("=")
n = Tex("21")
equation = VGroup(r, plus, y, eq, n).arrange(RIGHT, buff=0.12)
```
- 高亮时只能直接操作已命名的独立对象，例如 `Indicate(r)`、`SurroundingRectangle(row)`、`r.set_color(RED)`。
- 避免复杂 updater、always_redraw、ValueTracker、3D、相机运动、路径追踪和需要交互窗口的逻辑。

# 布局要求
- 坐标按默认 16:9 画面规划，横向大致在 [-6.7, 6.7]，纵向大致在 [-3.7, 3.7]。
- 当前片段画面要自洽：即使单独播放，也能看懂这一段在讲什么。
- 不要把大量旁白文字塞进画面；画面只保留短标题、关键公式、关键对象。
- 中文长句必须手动拆行，或拆成多个短 `Text` 对象。

# 必须包含的辅助代码
生成代码中必须包含等价于下面的结构：
```python
from manimlib import *

NARRATION_AUDIO = {}
NARRATION_SEGMENTS = [
    {"key": "intro", "text": "旁白文本"}
]

FONT = "PingFang SC"
BG = "#101820"
TEXT = "#F3F4F6"

def cn(text, size=36, color=TEXT):
    return Text(text, font=FONT, font_size=size, color=color)

def tx(value, size=42, color=TEXT):
    return Tex(value, font_size=size, color=color)

def equation_row(*items, buff=0.12):
    return VGroup(*items).arrange(RIGHT, buff=buff)

def start_voiceover(scene, key, fallback_duration=2.0):
    info = NARRATION_AUDIO.get(key)
    if info:
        scene.add_sound(info["file"])
        return max(float(info.get("duration", fallback_duration)), fallback_duration)
    return fallback_duration
```

片段主体建议这样写：
```python
class SegmentScene(Scene):
    def construct(self):
        self.camera.background_color = BG
        duration = start_voiceover(self, "intro", 8.0)
        title = cn("片段标题", 38)
        self.play(Write(title), run_time=min(1.5, duration))
        self.wait(max(0.2, duration - 1.5))
```

# 最终自检
- JSON 是单个对象，不能多一个 `}`，不能包 Markdown。
- `scene_name` 与代码里的 Scene 类名完全一致。
- 代码没有 Manim CE API。
- 代码没有 `get_part_by_tex`、`select_part`、`select_parts`、`get_part_by_text`。
- 所有中文都在 `Text(..., font="PingFang SC")` 中。
- 所有旁白 key 在 `narrations`、`NARRATION_SEGMENTS`、`start_voiceover` 中一致。
- 只生成当前片段，不要生成完整视频的所有片段。

下面开始生成当前片段。
"""
