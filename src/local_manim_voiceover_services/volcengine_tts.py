from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import requests

from src.media.output_urls import OUTPUTS_ROOT
from src.logger import logger


BOOKMARK_RE = re.compile(r"<bookmark\s+mark=[\"'][^\"']+[\"']\s*/>")


@dataclass(frozen=True)
class VolcengineTTSResult:
    """A synthesized narration audio file and its metadata."""

    input_text: str
    input_data: dict
    original_audio: str
    final_audio: str
    duration_seconds: float
    cache_hit: bool = False

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return asdict(self)


def _remove_voiceover_bookmarks(text: str) -> str:
    """Remove manim-voiceover bookmark tags if upstream text contains them."""
    return BOOKMARK_RE.sub("", text)


def _wav_duration_seconds(path: Path) -> float:
    """Return the duration of a PCM wav file."""
    with wave.open(str(path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        frame_rate = wav_file.getframerate()
        if frame_rate <= 0:
            return 0.0
        return round(frame_count / float(frame_rate), 3)


def _probe_duration_seconds(path: Path) -> float:
    """Return media duration using ffprobe when available."""
    if not shutil.which("ffprobe"):
        if path.suffix.lower() == ".wav":
            return _wav_duration_seconds(path)
        return 0.0

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
    return round(float(result.stdout.strip()), 3)


class VolcengineTTSService:
    """
    Pure-Python Volcengine TTS client for ManimGL.

    This service intentionally does not inherit from `manim_voiceover`
    interfaces. It returns concrete audio files so ManimGL scenes can attach
    them through `Scene.add_sound(...)`.
    """

    def __init__(
        self,
        *,
        app_id: str | None = None,
        access_token: str | None = None,
        speaker: str = "zh_female_yingyujiaoyu_mars_bigtts",
        resource_id: str = "seed-tts-1.0",
        speed_ratio: float = 1.0,
        request_timeout: tuple[int, int] = (10, 120),
    ):
        self.app_id = app_id or os.getenv("VOLCENGINE_APPID")
        self.access_token = access_token or os.getenv("VOLCENGINE_ACCESS_TOKEN")
        self.speaker = speaker
        self.resource_id = resource_id
        self.speed_ratio = speed_ratio
        self.request_timeout = request_timeout
        self.url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

        if not self.app_id or not self.access_token:
            raise ValueError("需要提供 VOLCENGINE_APPID 和 VOLCENGINE_ACCESS_TOKEN 环境变量")

    @staticmethod
    def default_cache_dir() -> Path:
        """Return the default TTS cache directory for ManimGL math videos."""
        return OUTPUTS_ROOT / "tts_cache" / "math_video_manimgl"

    @classmethod
    def has_credentials(cls) -> bool:
        """Return whether Volcengine credentials are available in the environment."""
        return bool(os.getenv("VOLCENGINE_APPID") and os.getenv("VOLCENGINE_ACCESS_TOKEN"))

    def _input_data(self, input_text: str) -> dict:
        """Return the deterministic cache input payload."""
        return {
            "input_text": input_text,
            "service": "volcengine",
            "config": {
                "speaker": self.speaker,
                "resource_id": self.resource_id,
                "speed_ratio": self.speed_ratio,
            },
        }

    @staticmethod
    def _audio_basename(input_data: dict) -> str:
        """Return a deterministic audio basename for cached TTS output."""
        payload = json.dumps(input_data, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"volcengine-{digest[:32]}"

    def _read_cached_result(
        self,
        *,
        input_text: str,
        input_data: dict,
        cache_dir: Path,
        basename: str,
    ) -> VolcengineTTSResult | None:
        """Return cached metadata when the final audio file exists."""
        metadata_path = cache_dir / f"{basename}.json"
        if not metadata_path.exists():
            return None

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        final_audio = str(metadata.get("final_audio") or "")
        if not final_audio:
            return None
        final_path = Path(final_audio)
        if not final_path.is_absolute():
            final_path = cache_dir / final_path
        if not final_path.exists():
            return None

        duration = float(metadata.get("duration_seconds") or _probe_duration_seconds(final_path))
        return VolcengineTTSResult(
            input_text=input_text,
            input_data=input_data,
            original_audio=str(metadata.get("original_audio") or final_path.name),
            final_audio=str(final_path),
            duration_seconds=duration,
            cache_hit=True,
        )

    def _request_pcm_audio(self, input_text: str) -> bytes:
        """Request PCM audio bytes from Volcengine."""
        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "Content-Type": "application/json",
        }
        payload = {
            "user": {"uid": "manim_user"},
            "req_params": {
                "speaker": self.speaker,
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                },
                "additions": json.dumps(
                    {
                        "explicit_language": "zh-cn",
                        "latex_parser": "v2",
                        "disable_markdown_filter": True,
                        "enable_timestamp": True,
                    },
                    ensure_ascii=False,
                ),
            },
        }

        if input_text.strip().startswith("<speak>"):
            payload["req_params"]["ssml"] = input_text
        else:
            payload["req_params"]["text"] = input_text

        logger.info("Synthesizing Volcengine TTS audio: {}", input_text[:120])
        response = requests.post(
            self.url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=self.request_timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP Error: {response.status_code} - {response.text}")

        audio_data = bytearray()
        for line in response.iter_lines():
            if not line:
                continue

            try:
                resp_json = json.loads(line)
            except Exception as exc:
                logger.warning("Failed to parse Volcengine TTS response line: {}", exc)
                continue

            code = int(resp_json.get("code", 0) or 0)
            if code == 0 and resp_json.get("data"):
                audio_data.extend(base64.b64decode(resp_json["data"]))
                continue
            if code == 20000000:
                break
            if code > 0:
                raise RuntimeError(f"Volcengine TTS error response: {resp_json}")

        if not audio_data:
            raise RuntimeError("未接收到音频数据，请检查配置或额度。")
        return bytes(audio_data)

    @staticmethod
    def _write_pcm_wav(path: Path, audio_data: bytes) -> None:
        """Write raw PCM bytes to a 24 kHz mono wav file."""
        temp_path = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp.wav")
        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(audio_data)
        os.replace(temp_path, path)

    @staticmethod
    def _convert_to_mp3(wav_path: Path, mp3_path: Path) -> Path:
        """Convert wav to mp3 when ffmpeg is available; otherwise keep wav."""
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg is unavailable; using wav audio for ManimGL.")
            return wav_path

        temp_path = mp3_path.with_name(f"{mp3_path.stem}.{uuid.uuid4().hex}.tmp.mp3")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(wav_path),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-b:a",
                "64k",
                str(temp_path),
            ],
            check=True,
        )
        os.replace(temp_path, mp3_path)
        return mp3_path

    def synthesize(
        self,
        text: str,
        *,
        cache_dir: str | Path | None = None,
        path: str | None = None,
    ) -> VolcengineTTSResult:
        """Synthesize one text segment and return its local audio file."""
        cache_root = Path(cache_dir) if cache_dir is not None else self.default_cache_dir()
        cache_root.mkdir(parents=True, exist_ok=True)

        input_text = _remove_voiceover_bookmarks(text)
        input_data = self._input_data(input_text)
        basename = self._audio_basename(input_data)
        if path:
            wav_path = cache_root / path
            if wav_path.suffix.lower() != ".wav":
                wav_path = wav_path.with_suffix(".wav")
            basename = wav_path.stem
        else:
            wav_path = cache_root / f"{basename}.wav"
        mp3_path = wav_path.with_suffix(".mp3")

        cached = self._read_cached_result(
            input_text=input_text,
            input_data=input_data,
            cache_dir=cache_root,
            basename=basename,
        )
        if cached is not None:
            return cached

        audio_data = self._request_pcm_audio(input_text)
        self._write_pcm_wav(wav_path, audio_data)
        final_path = self._convert_to_mp3(wav_path, mp3_path)
        duration = _probe_duration_seconds(final_path)

        result = VolcengineTTSResult(
            input_text=text,
            input_data=input_data,
            original_audio=str(wav_path),
            final_audio=str(final_path),
            duration_seconds=duration,
            cache_hit=False,
        )
        metadata_path = cache_root / f"{basename}.json"
        metadata_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Volcengine TTS done: path={} duration={}s cache_hit={}",
            final_path,
            duration,
            result.cache_hit,
        )
        return result

    def synthesize_many(
        self,
        texts: Iterable[str],
        *,
        cache_dir: str | Path | None = None,
        max_workers: int = 4,
    ) -> list[VolcengineTTSResult]:
        """Synthesize multiple text segments concurrently while preserving order."""
        text_list = list(texts)
        if not text_list:
            return []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.synthesize, text, cache_dir=cache_dir)
                for text in text_list
            ]
            return [future.result() for future in futures]
