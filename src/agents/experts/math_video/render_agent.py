import asyncio
from pathlib import Path

import os
import sys
import os.path
import tempfile
import json
import subprocess
import re

import shutil
from pathlib import Path
from collections.abc import Mapping

from playwright.async_api import async_playwright
from typing import Any, AsyncGenerator, List, Dict
from typing_extensions import override

from google.genai.types import Content
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.genai.types import Part, Blob

from src.logger import logger
from src.observability.timing import compact_text, timing_context_from_invocation, timing_stage
from src.utils import clean_json_string


PROJECT_ROOT = Path(__file__).resolve().parents[4]
LEGACY_BYTEDANCE_IMPORT = "from manim_voiceover.services.bytedance import ByteDanceService"
LOCAL_BYTEDANCE_IMPORT = (
    "from src.local_manim_voiceover_services.bytedance import ByteDanceService"
)
MANIM_ANIMATION_RE = re.compile(r"Animation\s+\d+")


def normalize_manim_voiceover_imports(manim_code: str) -> str:
    """Rewrite legacy generated imports to use the project-local voiceover service."""
    return manim_code.replace(LEGACY_BYTEDANCE_IMPORT, LOCAL_BYTEDANCE_IMPORT)


def build_manim_subprocess_env(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the environment used by Manim so temporary render scripts can import src."""
    env = dict(os.environ if base_env is None else base_env)
    project_root = str(PROJECT_ROOT)
    pythonpath = env.get("PYTHONPATH", "")
    paths = [path for path in pythonpath.split(os.pathsep) if path and path != project_root]
    env["PYTHONPATH"] = os.pathsep.join([project_root, *paths])
    return env


def summarize_manim_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact summary of Manim subprocess output."""
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    summary: Dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "code": str(result.get("code")),
        "stdout_chars": len(stdout),
        "stderr_chars": len(stderr),
        "animation_count": len(MANIM_ANIMATION_RE.findall(stdout)),
        "tts_request_count": stdout.count("正在通过字节跳动合成语音"),
        "tts_done_count": stdout.count("done with"),
    }
    if not result.get("ok"):
        summary["stdout_preview"] = compact_text(stdout, 500)
        summary["stderr_preview"] = compact_text(stderr, 500)
    return summary


async def run_render_video(workdir, code_path, scene_name):
    # env_result_1 = subprocess.run(["npm", "init", "-y"],  capture_output=True,cwd=workdir, text=True)
    # env_result_2 = subprocess.run(["npm", "install", "pptxgenjs", "playwright", "sharp"], capture_output=True, cwd=workdir, text=True)
    # env_result_3 = subprocess.run(["npx", "playwright", "install", "chromium"], capture_output=True, cwd=workdir, text=True)

    result = subprocess.run(
        ["manim", "-ql", code_path, scene_name],
        capture_output=True,
        cwd=workdir,
        text=True,
        env=build_manim_subprocess_env(),
    )

    return {
        "ok": result.returncode == 0 ,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "code": str(result.returncode)
    }


async def manim_to_video(
    manim_code: str,
    scene_name: str,
    timing_context: dict[str, str | None] | None = None,
):
    """Render Manim code into an MP4 binary."""
    timing_context = timing_context or {}
    with timing_stage(
        "manim",
        "manim_to_video",
        **timing_context,
        metadata={"scene_name": scene_name, "code_chars": len(manim_code)},
    ) as render_timing:
        video_bin = None
        error_message = ""

        with tempfile.TemporaryDirectory() as td:
            logger.debug("Manim temporary workdir: {}", td)

            manim_code = normalize_manim_voiceover_imports(manim_code)
            manim_code_save_path = os.path.join(td, 'manim.py')
            with open(manim_code_save_path, "w", encoding="utf-8") as fh:
                fh.write(manim_code)

            with timing_stage(
                "manim",
                "manim_subprocess",
                **timing_context,
                metadata={"scene_name": scene_name},
            ) as subprocess_timing:
                subprocess_result = await run_render_video(td, 'manim.py', scene_name)
                subprocess_timing["return_code"] = subprocess_result["code"]
                subprocess_timing["render_ok"] = subprocess_result["ok"]

            manim_summary = summarize_manim_result(subprocess_result)
            logger.info(
                "MANIM_RENDER_SUMMARY {}",
                json.dumps(manim_summary, ensure_ascii=False, sort_keys=True),
            )
            render_timing.update(manim_summary)

            if not subprocess_result['ok']:
                error_message = (
                    subprocess_result['stdout']
                    + '\n'
                    + subprocess_result['stderr']
                    + '\n'
                    + subprocess_result['code']
                )
            else:
                mp4_files = []

                for root, dirs, files in os.walk(td):
                    for file in files:
                        if file.lower().endswith(".mp4"):
                            full_path = os.path.abspath(os.path.join(root, file))
                            if 'partial_movie_files' not in full_path: # partial_movie_files 文件夹下放的是临时文件
                                mp4_files.append(full_path)

                # pptx_files 的长度应该是1
                if len(mp4_files) > 0:
                    mp4_result = mp4_files[0]
                    with open(mp4_result, 'rb') as f:
                        video_bin = f.read()
                    render_timing["video_bytes"] = len(video_bin)
                else:
                    error_message = "mp4 文件生成失败"

        if video_bin is not None:
            return {"status": "success", "message": video_bin}

        render_timing["status"] = "error"
        return {"status": "error", "message": error_message}

class RenderAgent(BaseAgent):

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
            self,
            name: str,
            description: str = ""
    ):
        super().__init__(
            name=name,
            description=description
        )


    def format_event(self, content_text: str = None, state_delta: Dict = None):
        event = Event(author=self.name)
        if state_delta:
            event.actions = EventActions(state_delta=state_delta)
        if content_text:
            event.content = Content(role='model', parts=[Part(text=content_text)])
        return event


    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Runs the HTMLTOImage asynchronously.
        This method achieves transform html page to a single image.
        Args:
            ctx (InvocationContext): The invocation context for the agent.
        Yields:
            Event: The events generated by the sequential agent during the image generation process.
        """

        timing_context = timing_context_from_invocation(ctx)
        with timing_stage(
            "agent",
            self.name,
            **timing_context,
            metadata={"mode": "legacy_math_video"},
        ) as agent_timing:
            current_parameters = ctx.session.state.get('current_parameters', {})
            manim_result_by_agent = ctx.session.state.get('math_video/manim_code', '') # 来自html_generation的结果

            logger.info(
                "RenderAgent received manim json chars={} preview={}",
                len(manim_result_by_agent),
                compact_text(manim_result_by_agent),
            )

            try:
                with timing_stage(
                    "parse",
                    "RenderAgent.parse_manim_json",
                    **timing_context,
                    metadata={"input_chars": len(manim_result_by_agent)},
                ):
                    manim_result_by_agent = clean_json_string(manim_result_by_agent)
                    manim_result = json.loads(manim_result_by_agent)
            except Exception as e:
                agent_timing["status"] = "error"
                current_output = {"author": self.name,
                    "status": "error",
                    "message": '获取代码错误',
                    "message_for_user": '视频生成失败' + str(e),
                    'output_text':''
                }
                text = f"\nmanim2video 视频生成失败。"
                yield self.format_event(text, {'current_output': current_output})
                return

            manim_code = manim_result['manim_code']
            scene_name = manim_result['scene_name']
            agent_timing["scene_name"] = scene_name
            agent_timing["code_chars"] = len(manim_code)

            logger.info(
                "RenderAgent parsed manim code scene={} chars={} preview={}",
                scene_name,
                len(manim_code),
                compact_text(manim_code),
            )

            result = await manim_to_video(manim_code, scene_name, timing_context=timing_context)

            # logger.info(result)
            step = ctx.session.state['step']
            if result["status"] == "error":
                agent_timing["status"] = "error"
                agent_timing["error_chars"] = len(result['message'])
                error_text = f"执行步骤{step + 1}: {self.name}执行出错：{result['message']}"
                message_for_user = f"执行步骤执行出错：{result['message']}"
                current_output = {"author": self.name, "status": "error", "message": error_text, 'message_for_user': message_for_user, 'output_text':''}

                logger.error("RenderAgent failed: {}", compact_text(error_text, 1000))
                yield self.format_event(error_text, {"current_output": current_output})
                return

            # 保存文件
            text = f"执行步骤{step + 1}: {self.name}：从 manim 转视频完成"
            message_for_user = "执行步骤从 manim 转视频完成"
            output_artifacts = []

            artifact_name = f"step{ctx.session.state.get('step') + 1}_manim2video_output.mp4"
            artifact_part = Part(inline_data=Blob(mime_type='video/mp4', data=result['message']))
            agent_timing["video_bytes"] = len(result['message'])

            with timing_stage(
                "artifact",
                "RenderAgent.save_video_artifact",
                **timing_context,
                metadata={"artifact_name": artifact_name, "video_bytes": len(result['message'])},
            ):
                await ctx.artifact_service.save_artifact(
                    app_name=ctx.session.app_name, user_id=ctx.session.user_id, session_id=ctx.session.id,
                    filename=artifact_name, artifact=artifact_part
                )

            text += f"\nmanim2video 视频保存成功，输出视频名称为{artifact_name}"
            description = f"manim文件转换得到的视频。\nmanim_code：{manim_code}\n\n"

            output_artifacts.append({'name': artifact_name, 'description': description})

            # 输出event
            current_output = {"author": self.name,
                "status": "success",
                "message": text,
                "message_for_user": message_for_user,
                "output_artifacts": output_artifacts,
                'output_text':''
            }
            yield self.format_event(text, {'current_output': current_output})
            return


