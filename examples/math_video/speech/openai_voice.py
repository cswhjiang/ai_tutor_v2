# coding: utf-8
import dotenv
from pathlib import Path
import openai
from tqdm import tqdm
import time

dotenv.load_dotenv()

voices = 'ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse, marin, cedar'.split(', ')
model = 'gpt-4o-mini-tts-2025-12-15'
text = '这是一道典型的人数变化题：男生、女生各走了一部分，最后剩下40人。我们今天用方程组，把文字信息翻译成数学。'
for voice in tqdm(voices):
    speech_file_path = Path('./openai_voice') / f"{voice.strip()}.mp3"
    if not speech_file_path.exists():
        with openai.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice.strip(),
            input=text
            ) as response:
            response.stream_to_file(speech_file_path)
        time.sleep(10)  # 避免请求过快
