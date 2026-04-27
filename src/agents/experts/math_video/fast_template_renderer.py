from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from conf.system import SYS_CONFIG
from src.logger import logger


FAST_SCENE_NAME = "FastMathVideoScene"
FAST_PIXEL_WIDTH = 854
FAST_PIXEL_HEIGHT = 480
FAST_FRAME_RATE = 15
MAX_FAST_STEPS = 5


def _clean_text(value: Any, fallback: str = "", max_chars: int = 600) -> str:
    """Return compact display-safe text with a conservative length cap."""
    if value is None:
        return fallback
    text = str(value).replace("\r", "\n").strip()
    while "\n\n" in text:
        text = text.replace("\n\n", "\n")
    text = " ".join(part.strip() for part in text.splitlines() if part.strip())
    if not text:
        return fallback
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "..."
    return text


def _normalize_steps(raw_steps: Any, prompt: str) -> list[dict[str, str]]:
    """Normalize LLM-produced steps into a small deterministic schema."""
    steps: list[dict[str, str]] = []
    if isinstance(raw_steps, list):
        for index, raw_step in enumerate(raw_steps[:MAX_FAST_STEPS], start=1):
            if isinstance(raw_step, dict):
                heading = _clean_text(
                    raw_step.get("heading") or raw_step.get("title"),
                    fallback=f"Step {index}",
                    max_chars=40,
                )
                explanation = _clean_text(
                    raw_step.get("explanation")
                    or raw_step.get("body")
                    or raw_step.get("content"),
                    fallback="Explain this step clearly.",
                    max_chars=220,
                )
                equation = _clean_text(
                    raw_step.get("equation") or raw_step.get("formula"),
                    fallback="",
                    max_chars=100,
                )
                narration = _clean_text(
                    raw_step.get("narration") or explanation,
                    fallback=explanation,
                    max_chars=260,
                )
            else:
                heading = f"Step {index}"
                explanation = _clean_text(
                    raw_step,
                    fallback="Explain this step clearly.",
                    max_chars=220,
                )
                equation = ""
                narration = explanation
            steps.append(
                {
                    "heading": heading,
                    "explanation": explanation,
                    "equation": equation,
                    "narration": narration,
                }
            )
    if steps:
        return steps
    return [
        {
            "heading": "解题思路",
            "explanation": "先读题，再找关键关系，最后代入计算并检查答案。",
            "equation": "",
            "narration": f"我们先分析这道题：{_clean_text(prompt, max_chars=180)}",
        }
    ]


def normalize_fast_video_script(script: dict[str, Any], prompt: str) -> dict[str, Any]:
    """
    Normalize the structured script returned by the LLM.

    The renderer intentionally accepts a small schema so video generation stays
    predictable and does not depend on arbitrary Manim code from the model.
    """
    if not isinstance(script, dict):
        script = {}
    problem = _clean_text(script.get("problem") or prompt, fallback=prompt, max_chars=360)
    steps = _normalize_steps(script.get("steps"), prompt)
    answer = _clean_text(script.get("answer"), fallback="", max_chars=120)
    summary = _clean_text(
        script.get("summary") or ("结论：" + answer if answer else "按步骤整理条件并计算，就能得到答案。"),
        fallback="按步骤整理条件并计算，就能得到答案。",
        max_chars=220,
    )
    return {
        "title": _clean_text(script.get("title"), fallback="数学题讲解", max_chars=48),
        "problem": problem,
        "answer": answer,
        "summary": summary,
        "intro_narration": _clean_text(
            script.get("intro_narration") or f"我们来看这道题：{problem}",
            fallback=f"我们来看这道题：{problem}",
            max_chars=260,
        ),
        "steps": steps,
    }


def collect_narration_segments(script: dict[str, Any]) -> list[str]:
    """Return narration text in the exact order used by the template."""
    segments = [script["intro_narration"]]
    segments.extend(step["narration"] for step in script["steps"])
    segments.append(script["summary"])
    return segments


def estimate_segment_durations(narrations: list[str]) -> list[float]:
    """Estimate readable segment durations when audio is unavailable."""
    durations: list[float] = []
    for text in narrations:
        duration = max(2.2, min(7.5, len(text) / 5.0))
        durations.append(round(duration, 2))
    return durations


def build_fast_manim_code(script: dict[str, Any], durations: list[float]) -> str:
    """Build a deterministic low-cost Manim scene from normalized script data."""
    payload = {"script": script, "durations": durations}
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f'''from manim import *
import json

config.pixel_width = {FAST_PIXEL_WIDTH}
config.pixel_height = {FAST_PIXEL_HEIGHT}
config.frame_rate = {FAST_FRAME_RATE}
config.disable_caching = True

DATA = json.loads({payload_json!r})
SCRIPT = DATA["script"]
DURATIONS = DATA["durations"]


def wrap_text(text, max_chars):
    text = str(text or "").replace("\\r", " ").replace("\\n", " ").strip()
    if not text:
        return " "
    lines = []
    while len(text) > max_chars:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    lines.append(text)
    return "\\n".join(lines)


def fit_width(mobj, max_width):
    if mobj.width > max_width:
        mobj.set_width(max_width)
    return mobj


def card_with_text(lines, width=12.0, height=4.2, stroke_color="#5D738A"):
    bg = RoundedRectangle(
        corner_radius=0.15,
        width=width,
        height=height,
        stroke_color=stroke_color,
        stroke_width=1.4,
        fill_color="#101820",
        fill_opacity=0.92,
    )
    text_group = VGroup()
    for line, size, color in lines:
        text_group.add(Text(wrap_text(line, 26), font_size=size, color=color, line_spacing=0.82))
    text_group.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
    fit_width(text_group, width - 0.7)
    if text_group.height > height - 0.45:
        text_group.set_height(height - 0.45)
    text_group.move_to(bg.get_center())
    return VGroup(bg, text_group)


class {FAST_SCENE_NAME}(Scene):
    def construct(self):
        self.camera.background_color = "#16202A"

        title = Text(SCRIPT["title"], font_size=30, color=YELLOW)
        fit_width(title, 12.2)
        title.to_edge(UP, buff=0.28)
        underline = Line(LEFT * 6.1, RIGHT * 6.1, color="#31404E", stroke_width=2)
        underline.next_to(title, DOWN, buff=0.14)
        self.play(FadeIn(title, shift=DOWN * 0.08), Create(underline), run_time=0.35)

        intro_card = card_with_text(
            [
                ("题目", 25, YELLOW),
                (SCRIPT["problem"], 23, WHITE),
            ],
            height=3.7,
            stroke_color="#4A6075",
        )
        intro_card.move_to(ORIGIN).shift(UP * 0.1)
        self.play(FadeIn(intro_card, shift=UP * 0.12), run_time=0.42)
        self.wait(max(0.8, DURATIONS[0] - 0.35))
        self.play(FadeOut(intro_card, shift=UP * 0.08), run_time=0.25)

        steps = SCRIPT["steps"]
        for index, step in enumerate(steps, start=1):
            progress = Text(f"{{index}} / {{len(steps)}}", font_size=20, color=GRAY_B)
            progress.next_to(underline, DOWN, buff=0.12).align_to(underline, RIGHT)

            lines = [
                (step["heading"], 27, YELLOW),
                (step["explanation"], 23, WHITE),
            ]
            if step.get("equation"):
                lines.append((step["equation"], 26, ORANGE))

            step_card = card_with_text(lines, height=4.0, stroke_color="#526D84")
            step_card.move_to(ORIGIN).shift(UP * 0.05)

            self.play(FadeIn(progress), FadeIn(step_card, shift=RIGHT * 0.18), run_time=0.38)
            self.wait(max(0.9, DURATIONS[index] - 0.42))
            self.play(FadeOut(step_card, shift=LEFT * 0.18), FadeOut(progress), run_time=0.24)

        summary_lines = [
            ("总结", 27, YELLOW),
            (SCRIPT["summary"], 23, WHITE),
        ]
        if SCRIPT.get("answer"):
            summary_lines.append((SCRIPT["answer"], 29, ORANGE))

        summary_card = card_with_text(summary_lines, height=4.0, stroke_color=ORANGE)
        summary_card.move_to(ORIGIN).shift(UP * 0.05)
        self.play(FadeIn(summary_card, scale=0.96), run_time=0.42)
        self.wait(max(1.3, DURATIONS[-1] - 0.2))
        self.wait(0.2)
'''


def _probe_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _synthesize_one_narration(text: str, cache_dir: Path) -> Path:
    from src.local_manim_voiceover_services.bytedance import ByteDanceService

    service = ByteDanceService()
    result = service.generate_from_text(text, cache_dir=str(cache_dir))
    audio_name = result.get("final_audio") or result.get("original_audio")
    if not audio_name:
        raise RuntimeError("ByteDanceService did not return an audio filename.")
    audio_path = Path(audio_name)
    if not audio_path.is_absolute():
        audio_path = cache_dir / audio_path
    if not audio_path.exists():
        raise FileNotFoundError(f"TTS output file was not found: {audio_path}")
    return audio_path


async def _maybe_generate_voiceover_audio(
    narrations: list[str],
    workdir: Path,
) -> tuple[list[float] | None, Path | None]:
    """
    Generate narration audio when credentials are available.

    The default mode is auto: use voiceover only when credentials and ffmpeg are
    present. Set MATH_VIDEO_FAST_VOICEOVER=0 to force silent fast videos.
    """
    voice_setting = os.getenv("MATH_VIDEO_FAST_VOICEOVER", "auto").strip().lower()
    if voice_setting in {"0", "false", "no", "off", "silent"}:
        return None, None

    has_credentials = bool(os.getenv("VOLCENGINE_APPID") and os.getenv("VOLCENGINE_ACCESS_TOKEN"))
    if voice_setting == "auto" and not has_credentials:
        logger.info("Fast math video voiceover skipped because Volcengine credentials are not set.")
        return None, None

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        logger.warning("Fast math video voiceover skipped because ffmpeg/ffprobe is unavailable.")
        return None, None

    cache_dir = Path(SYS_CONFIG.base_dir) / "outputs" / "tts_cache" / "math_video_fast"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        audio_paths = await asyncio.gather(
            *[
                asyncio.to_thread(_synthesize_one_narration, text, cache_dir)
                for text in narrations
            ]
        )
        durations = [
            await asyncio.to_thread(_probe_duration_seconds, audio_path)
            for audio_path in audio_paths
        ]
    except Exception as exc:
        logger.warning(
            f"Fast math video voiceover generation failed; falling back to silent video: {exc}"
        )
        return None, None

    concat_file = workdir / "voiceover_concat.txt"
    concat_audio = workdir / "voiceover.mp3"
    with concat_file.open("w", encoding="utf-8") as fh:
        for audio_path in audio_paths:
            escaped = str(audio_path.resolve()).replace("'", "'\\''")
            fh.write(f"file '{escaped}'\n")

    concat_result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-ac",
            "1",
            "-ar",
            "24000",
            str(concat_audio),
        ],
        capture_output=True,
        text=True,
    )
    if concat_result.returncode != 0:
        logger.warning(f"Fast math video audio concat failed: {concat_result.stderr}")
        return None, None
    return [round(duration + 0.25, 2) for duration in durations], concat_audio


def _find_rendered_mp4(workdir: Path) -> Path | None:
    mp4_files: list[Path] = []
    for path in workdir.rglob("*.mp4"):
        if "partial_movie_files" not in str(path):
            mp4_files.append(path)
    if not mp4_files:
        return None
    return max(mp4_files, key=lambda path: path.stat().st_mtime)


def _mux_audio(video_path: Path, audio_path: Path, workdir: Path) -> Path:
    muxed_path = workdir / "fast_math_video_with_audio.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(muxed_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return muxed_path


async def fast_manim_to_video(script: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Render a fast math explanation video from structured script data."""
    normalized_script = normalize_fast_video_script(script, prompt)
    narrations = collect_narration_segments(normalized_script)
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        audio_durations, audio_path = await _maybe_generate_voiceover_audio(narrations, workdir)
        durations = audio_durations or estimate_segment_durations(narrations)
        manim_code = build_fast_manim_code(normalized_script, durations)
        code_path = workdir / "fast_math_scene.py"
        code_path.write_text(manim_code, encoding="utf-8")
        render_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "manim",
                "-ql",
                "--disable_caching",
                code_path.name,
                FAST_SCENE_NAME,
            ],
            capture_output=True,
            cwd=workdir,
            text=True,
        )
        if render_result.returncode != 0:
            return {
                "status": "error",
                "message": render_result.stdout + "\n" + render_result.stderr,
                "script": normalized_script,
            }
        mp4_path = _find_rendered_mp4(workdir)
        if mp4_path is None:
            return {
                "status": "error",
                "message": "mp4 文件生成失败",
                "script": normalized_script,
            }

        final_video_path = mp4_path
        has_voiceover = False
        if audio_path is not None:
            try:
                final_video_path = _mux_audio(mp4_path, audio_path, workdir)
                has_voiceover = True
            except Exception as exc:
                logger.warning(f"Fast math video audio mux failed; returning silent video: {exc}")

        return {
            "status": "success",
            "message": final_video_path.read_bytes(),
            "script": normalized_script,
            "has_voiceover": has_voiceover,
            "render_quality": f"{FAST_PIXEL_WIDTH}x{FAST_PIXEL_HEIGHT}@{FAST_FRAME_RATE}fps",
        }
