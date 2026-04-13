from manim import *
from manim_voiceover import VoiceoverScene
# from bytedance import ByteDanceService

from manim_voiceover.services.bytedance import ByteDanceService

class ByteDanceExample(VoiceoverScene):
    def construct(self):
        # 初始化你写的 Service
        self.set_speech_service(
            ByteDanceService(
                # speaker="zh_female_yingyujiaoyu_mars_bigtts",
                # 如果没设置环境变量，可以手动传入：
                # app_id="你的ID",
                # access_token="你的Token"
            )
        )

        with self.voiceover(text="已知函数 $f(x)$ 的定义域是全体实数，且满足方程 $\delta = 0.618$。") as tracker:
            tex = MathTex("f(x)", r"\rightarrow", r"\delta = 0.618")
            self.play(Write(tex))

        self.wait(1)