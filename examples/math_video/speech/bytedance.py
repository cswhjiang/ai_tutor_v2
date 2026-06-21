import os
import time
import json
import base64
import requests
from pathlib import Path
import wave
import subprocess

from manim import logger
from manim_voiceover.services.base import SpeechService
from manim_voiceover.helper import remove_bookmarks


class ByteDanceService(SpeechService):
    """
    字节跳动语音合成服务 (Volcengine TTS)
    参考: https://www.volcengine.com/docs/6561/71081
    """

    def __init__(
            self, speed_ratio: float = 1.0, **kwargs):
        """
        Args:
            app_id (str): 火山引擎 APPID
            access_token (str): 火山引擎 Access Token (Bearer Token)
            speaker (str): 发音人 ID
            resource_id (str): 资源场景 ID
            speed_ratio (float): 语速，范围 [0.2, 3.0]，默认为 1.0
        """
        app_id: str = None
        access_token: str = None
        speaker: str = "zh_female_yingyujiaoyu_mars_bigtts"
        resource_id: str = "seed-tts-1.0"

        self.app_id = app_id or os.getenv("VOLCENGINE_APPID")
        self.access_token = access_token or os.getenv("VOLCENGINE_ACCESS_TOKEN")
        self.speaker = speaker
        self.resource_id = resource_id
        self.speed_ratio = speed_ratio
        self.url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

        if not self.app_id or not self.access_token:
            raise ValueError("需要提供 VOLCENGINE_APPID 和 VOLCENGINE_ACCESS_TOKEN 环境变量")

        super().__init__(**kwargs)

    def generate_from_text(
            self, text: str, cache_dir: str = None, path: str = None, **kwargs
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir

        # Manim-voiceover 默认会传入书签，字节跳动 SSML 处理前需清理或转换
        input_text = remove_bookmarks(text)

        # 构造缓存 key 的数据结构
        input_data = {
            "input_text": input_text,
            "service": "bytedance",
            "config": {
                "speaker": self.speaker,
                "resource_id": self.resource_id,
                "speed_ratio": self.speed_ratio,
            },
        }

        # 1. 检查缓存
        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        # 2. 确定音频存储路径
        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".wav"
        else:
            audio_path = path

        full_path = Path(cache_dir) / audio_path
        logger.info(f"full_path: {full_path}")

        # 3. 构造请求参数
        headers = {
            "X-Api-App-Id": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "Content-Type": "application/json",
        }

        # 识别是否为 SSML
        is_ssml = input_text.strip().startswith("<speak>")

        payload = {
            "user": {"uid": "manim_user"},
            "req_params": {
                "speaker": self.speaker,
                "audio_params": {
                    "format": "pcm",
                    "sample_rate": 24000,
                    "enable_timestamp": True
                },
                # 使用 demo 中的 additions 配置以支持 LaTeX
                "additions": json.dumps({
                    "explicit_language": "zh-cn",
                    "latex_parser": "v2",
                    "disable_markdown_filter": True,
                    "enable_timestamp": True
                }),
            }
        }

        if is_ssml:
            payload["req_params"]["ssml"] = input_text
        else:
            payload["req_params"]["text"] = input_text

        # 4. 执行请求
        logger.info(f"正在通过字节跳动合成语音: '{input_text}...'")
        response = requests.post(self.url, headers=headers, json=payload, stream=True)
        # print(response)

        if response.status_code != 200:
            raise Exception(f"HTTP Error: {response.status_code} - {response.text}")

        audio_data = bytearray()
        total_audio_size = 0
        for line in response.iter_lines():
            if not line:
                continue

            # print(f"DEBUG RECEIVE: {line}\n")
            try:
                resp_json = json.loads(line)
                if resp_json.get("code", 0) == 0 and "data" in resp_json and resp_json["data"]:
                    # temp_data = resp_json["data"]
                    # print(f"DEBUG RECEIVE data: {temp_data}\n")
                    chunk_audio = base64.b64decode(resp_json["data"])
                    audio_size = len(chunk_audio)
                    total_audio_size += audio_size
                    audio_data.extend(chunk_audio)
                    continue
                # if resp_json.get("code", 0) == 0 and "sentence" in resp_json and resp_json["sentence"]:
                #     print("sentence_data:", resp_json)
                #     continue
                if resp_json.get("code", 0) == 20000000:
                    if 'usage' in resp_json:
                        logger.info("usage:", resp_json['usage'])
                    break
                if resp_json.get("code", 0) > 0:
                    logger.info(f"error response:{resp_json}")
                    break

            except Exception as e:
                logger.warning(f"解析响应行失败: {e}")

        if not audio_data:
            raise Exception("未接收到音频数据，请检查配置或额度。")

        # 5. 写入文件
        # with open(full_path, "wb") as f:
        #     f.write(audio_data)
        with wave.open(str(full_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(24000)
            wf.writeframes(audio_data)

        wav_path = full_path
        mp3_path = wav_path.with_suffix(".mp3")
        # print('mp3_path: ' + str(mp3_path))

        subprocess.run(
            [
                "ffmpeg",
                "-y",  # 覆盖输出
                "-v", "error",  # 只显示错误
                "-i", str(wav_path),
                "-ac", "1",  # 单声道
                "-ar", "24000",  # 采样率
                "-b:a", "64k",  # 比特率（可改 64k / 96k）
                str(mp3_path),
            ],
            check=True,
        )

        # 6. 返回结果字典
        logger.info(f"done with: {input_text}, mp3path: {str(mp3_path)}, audio size: {total_audio_size}.")
        # mp3_path = str(mp3_path.suffix)
        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": mp3_path.name,
            "final_audio": mp3_path.name
        }