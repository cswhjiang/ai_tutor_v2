# Copy this file into:
#   ai_tutor/.venv/lib/python3.11/site-packages/manim_voiceover/services/bytedance.py
#
# ByteDance (Volcengine OpenSpeech) TTS v3 HTTP unidirectional streaming.
#
# Env vars expected:
#   VOLCENGINE_APPID
#   VOLCENGINE_ACCESS_TOKEN

import json
import os
import sys
import base64
from pathlib import Path

import requests
from dotenv import find_dotenv, load_dotenv
from manim import logger

from manim_voiceover.helper import (
    create_dotenv_file,
    remove_bookmarks,
)
from manim_voiceover.services.base import SpeechService


load_dotenv(find_dotenv(usecwd=True))


def create_dotenv_volcengine():
    logger.info(
        "ByteDance (Volcengine OpenSpeech) TTS needs VOLCENGINE_APPID and "
        "VOLCENGINE_ACCESS_TOKEN. You can also create a .env file in your project root."
    )
    if not create_dotenv_file(["VOLCENGINE_APPID", "VOLCENGINE_ACCESS_TOKEN"]):
        raise ValueError(
            "Environment variables VOLCENGINE_APPID / VOLCENGINE_ACCESS_TOKEN are not set. "
            "Please set them or create a .env file with the variables."
        )
    logger.info("The .env file has been created. Please run Manim again.")
    sys.exit()


class ByteDanceService(SpeechService):
    """
    Speech service class for ByteDance (Volcengine OpenSpeech) TTS streaming API.

    Endpoint used (v3):
      https://openspeech.bytedance.com/api/v3/tts/unidirectional

    Notes:
    - The API returns line-delimited JSON in a streaming response.
    - Audio chunks are base64 encoded in the `data` field when code == 0.
    - A terminal message is usually returned with code == 20000000.
    """

    def __init__(
        self,
        speaker: str = "zh_female_yingyujiaoyu_mars_bigtts",
        resource_id: str = "seed-tts-1.0",
        url: str = "https://openspeech.bytedance.com/api/v3/tts/unidirectional",
        audio_format: str = "mp3",
        sample_rate: int = 24000,
        explicit_language: str = "zh-cn",
        latex_parser: str = "v2",
        disable_markdown_filter: bool = True,
        enable_timestamp: bool = True,
        use_ssml: bool = False,
        uid: str = "manim_user",
        transcription_model="base",
        **kwargs,
    ):
        """
        Args:
            speaker: ByteDance speaker id.
            resource_id: Usually "seed-tts-1.0" or "seed-tts-2.0" depending on your account.
            url: API endpoint.
            audio_format: "mp3" recommended for manim_voiceover.
            sample_rate: e.g. 24000.
            explicit_language: e.g. "zh-cn".
            latex_parser: "v2" (recommended by ByteDance docs).
            disable_markdown_filter: keep markdown symbols in text.
            enable_timestamp: request timestamp info (API may also stream `sentence` messages).
            use_ssml: send `ssml` instead of `text` (only basic <speak>/<break> is recommended).
            uid: user uid in payload.
        """
        self.app_id = os.getenv("VOLCENGINE_APPID")
        self.access_token = os.getenv("VOLCENGINE_ACCESS_TOKEN")

        self.speaker = speaker
        self.resource_id = resource_id
        self.url = url

        self.audio_format = audio_format
        self.sample_rate = sample_rate

        self.explicit_language = explicit_language
        self.latex_parser = latex_parser
        self.disable_markdown_filter = disable_markdown_filter
        self.enable_timestamp = enable_timestamp

        self.use_ssml = use_ssml
        self.uid = uid

        SpeechService.__init__(self, transcription_model=transcription_model, **kwargs)

    def _resolve_out_path(self, cache_dir: str, audio_path: str) -> Path:
        """Manim-voiceover expects `original_audio` to be a basename relative to cache_dir."""
        p = Path(audio_path)
        if p.is_absolute():
            return p
        return Path(cache_dir) / audio_path

    def generate_from_text(
        self, text: str, cache_dir: str = None, path: str = None, **kwargs
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # Remove manim-voiceover bookmarks so TTS doesn't speak them.
        input_text = remove_bookmarks(text)

        additions = {
            "explicit_language": self.explicit_language,
            "latex_parser": self.latex_parser,
            "disable_markdown_filter": bool(self.disable_markdown_filter),
            "enable_timestamp": bool(self.enable_timestamp),
        }

        input_data = {
            "input_text": input_text,
            "service": "bytedance",
            "config": {
                "speaker": self.speaker,
                "resource_id": self.resource_id,
                "url": self.url,
                "audio_format": self.audio_format,
                "sample_rate": self.sample_rate,
                "use_ssml": self.use_ssml,
                "additions": additions,
            },
        }

        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + f".{self.audio_format}"
        else:
            audio_path = path

        out_path = self._resolve_out_path(cache_dir, audio_path)

        # If user passed an absolute path, manim will NOT prepend cache_dir.
        # Still, we keep `original_audio` as provided so downstream can find it.
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Short-circuit if file already exists and is non-empty.
        if out_path.exists() and out_path.stat().st_size > 0:
            return {
                "input_text": text,
                "input_data": input_data,
                "original_audio": audio_path,
            }

        if self.app_id is None or self.access_token is None:
            create_dotenv_volcengine()

        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "Content-Type": "application/json",
            "Connection": "keep-alive",
        }

        req_params = {
            "speaker": self.speaker,
            "audio_params": {
                "format": self.audio_format,
                "sample_rate": self.sample_rate,
            },
            # API expects a JSON string here (per official demo).
            "additions": json.dumps(additions, ensure_ascii=False),
        }

        if self.enable_timestamp:
            # some accounts accept enable_timestamp under audio_params, keep both for compatibility
            req_params["audio_params"]["enable_timestamp"] = True

        if self.use_ssml:
            req_params["ssml"] = input_text
        else:
            req_params["text"] = input_text

        payload = {"user": {"uid": self.uid}, "req_params": req_params}

        session = requests.Session()
        audio_data = bytearray()

        try:
            response = session.post(self.url, headers=headers, json=payload, stream=True)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP Error: {response.status_code} - {response.text}")

            # Helpful for debugging in case of authentication issues
            logid = response.headers.get("X-Tt-Logid")
            if logid:
                logger.debug(f"ByteDance TTS X-Tt-Logid: {logid}")

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except Exception:
                    # occasionally there could be an incomplete line; skip it
                    continue

                code = data.get("code", 0)

                # audio chunk
                if code == 0 and data.get("data"):
                    try:
                        audio_data.extend(base64.b64decode(data["data"]))
                    except Exception:
                        # ignore bad chunk
                        continue
                    continue

                # sentence / timestamp metadata
                if code == 0 and data.get("sentence"):
                    # keep quiet; users can turn on logging if needed
                    continue

                # terminal message (usage, etc.)
                if code == 20000000:
                    break

                # any other error code
                if code and code != 0:
                    raise RuntimeError(f"API error: {data}")

            if not audio_data:
                raise RuntimeError(
                    "No audio data received. Please check your credentials, resource_id, and speaker."
                )

            with open(out_path, "wb") as f:
                f.write(audio_data)

            try:
                os.chmod(out_path, 0o644)
            except Exception:
                pass

        finally:
            try:
                response.close()
            except Exception:
                pass
            session.close()

        json_dict = {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }
        return json_dict
