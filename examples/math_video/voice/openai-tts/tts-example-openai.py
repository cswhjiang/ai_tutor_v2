from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.openai import OpenAIService


class OpenAITTSExample(VoiceoverScene):
    def construct(self):
        # 设置 OpenAI TTS
        self.set_speech_service(
            OpenAIService(
                model="gpt-4o-mini-tts",
                voice="alloy",
                language="en"
            )
        )

        circle = Circle()
        square = Square().shift(2 * RIGHT)

        with self.voiceover(text="This circle is drawn as I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)

        with self.voiceover(text="Let's shift it to the left two units.") as tracker:
            self.play(circle.animate.shift(2 * LEFT), run_time=tracker.duration)

        with self.voiceover(text="Now, let's transform it into a square.") as tracker:
            self.play(Transform(circle, square), run_time=tracker.duration)

        with self.voiceover(text="Thank you for watching."):
            self.play(Uncreate(circle))

        self.wait()
