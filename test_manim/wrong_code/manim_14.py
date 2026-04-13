from manim import *
import os

# --- 旁白文本配置 (用于生成 TTS 或 字幕) ---
NARRATION = [
    {"id": "S1", "text": "我们用抽屉原理证明：25个人里，必然至少有3个人属相相同。"},
    {"id": "S2", "text": "把12个属相看成12个抽屉，把25个人当作要放进去的物品。"},
    {"id": "S3", "text": "如果我们想彻底避免出现三个人同属相，那每个属相最多只能放两个人。这样12个抽屉总共最多放下12乘2等于24个人。"},
    {"id": "S4", "text": "可现实是有25个人。因为25大于24，第25个人无论放进哪里，必然会把某个属相的数量从2推到3。"},
    {"id": "S5", "text": "所以我们得到结论：在25个人中，必然至少有3个人的属相相同。"},
    {"id": "S6", "text": "你可以把它当作一个通用模板：如果总人数超过“抽屉数乘以每个抽屉最多容纳的人数”，就一定会有某个抽屉超出限制，这里就从2变成3。"},
    {"id": "S7", "text": "最后提醒制作细节：MathTex 只放数学，中文一律用 Text。渲染前全局搜一遍 MathTex 和 Tex 的内容，就能避免 Unicode 编译错误再次出现。"}
]

# --- 可选语音合成支持 ---
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    VOICEOVER_AVAILABLE = True
except ImportError:
    VOICEOVER_AVAILABLE = False
    # 降级方案：创建一个伪造的 VoiceoverScene 类
    class VoiceoverScene(Scene):
        def set_speech_service(self, service): pass
        def voiceover(self, text=None, **kwargs):
            # 返回一个上下文管理器，模拟 with 语句
            class DummyContext:
                def __init__(self, scene, text):
                    self.scene = scene
                    self.text = text
                def __enter__(self):
                    if self.text:
                        print(f"[旁白模拟] {self.text}")
                def __exit__(self, exc_type, exc_val, exc_tb):
                    # 根据文本长度简单的估算等待时间
                    wait_time = len(self.text) * 0.2 if self.text else 1
                    self.scene.wait(wait_time)
            return DummyContext(self, text)


class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # 1. 语音服务初始化
        if VOICEOVER_AVAILABLE:
            self.set_speech_service(GTTSService(lang="zh-CN"))

        # 2. 通用样式配置
        # 尝试使用系统中可能存在的字体，保证中文显示。若无，Manim 会尝试默认字体。
        # 注意：若您的系统完全没有中文字体，Text 可能显示方块。
        cn_font = None # 不强制指定，依赖 Manim Pango 自动查找系统字体
        text_color = WHITE
        
        # ------------------------------------------------------------
        # 镜头 S1: 开场标题
        # ------------------------------------------------------------
        # 旁白：我们用抽屉原理证明：25个人里，必然至少有3个人属相相同。
        with self.voiceover(text=NARRATION[0]["text"]):
            title = Text("抽屉原理：25人中至少3人属相相同", font_size=40, font=cn_font)
            subtitle = Text("（关键：证明“至少3人同属相”）", font_size=26, color=GRAY, font=cn_font)
            
            title_group = VGroup(title, subtitle).arrange(DOWN)
            self.play(Write(title_group))
        
        self.wait(0.5)
        self.play(title_group.animate.to_edge(UP).scale(0.8))

        # ------------------------------------------------------------
        # 镜头 S2: 建模（抽屉与物品）
        # ------------------------------------------------------------
        # 旁白：把12个属相看成12个抽屉，把25个人当作要放进去的物品。
        with self.voiceover(text=NARRATION[1]["text"]):
            # 创建说明文字
            model_text_1 = Text("建模：12个属相 = 12个抽屉", font_size=30, font=cn_font)
            model_text_2 = Text("25个人 = 25个物品", font_size=30, font=cn_font)
            model_group = VGroup(model_text_1, model_text_2).arrange(DOWN).next_to(title_group, DOWN, buff=0.5)
            
            self.play(Write(model_group))
            self.wait(0.5)
            
            # 创建12个抽屉 (2行6列)
            drawers = VGroup()
            for i in range(12):
                d = Rectangle(width=1.5, height=1.5, color=BLUE)
                # 标签数字 (纯数字可以用 Text 或 MathTex，这里用 Text 统一风格)
                label = Text(str(i+1), font_size=20).next_to(d, UP, buff=0.1)
                drawer_unit = VGroup(d, label)
                drawers.add(drawer_unit)
            
            drawers.arrange_in_grid(rows=2, cols=6, buff=0.3)
            drawers.to_edge(DOWN, buff=1.0)
            
            self.play(Create(drawers))
        
        # 清理说明文字，保留抽屉
        self.play(FadeOut(model_group))

        # ------------------------------------------------------------
        # 镜头 S3: 最坏情况设定
        # ------------------------------------------------------------
        # 旁白：如果我们想彻底避免出现三个人同属相，那每个属相最多只能放两个人。
        #      这样12个抽屉总共最多放下12乘2等于24个人。
        
        dots_group = VGroup()
        
        with self.voiceover(text=NARRATION[2]["text"]):
            # 文字说明
            assumption = Text("假设：想避免出现“3人同属相”", font_size=28, color=YELLOW, font=cn_font)
            assumption.next_to(title_group, DOWN)
            
            limit_text = Text("则每个抽屉最多 2 人", font_size=28, font=cn_font)
            limit_text.next_to(assumption, DOWN)
            
            self.play(Write(assumption), Write(limit_text))
            
            # 动画：向每个抽屉放入2个点
            anims = []
            for drawer_unit in drawers:
                rect = drawer_unit[0]
                # 在矩形内放2个点
                d1 = Dot(color=YELLOW).move_to(rect.get_center() + LEFT*0.3)
                d2 = Dot(color=YELLOW).move_to(rect.get_center() + RIGHT*0.3)
                dots_group.add(d1, d2)
                anims.append(FadeIn(d1, run_time=0.1))
                anims.append(FadeIn(d2, run_time=0.1))
            
            self.play(AnimationGroup(*anims, lag_ratio=0.05))
            
            # 数学计算
            # 严禁中文入 MathTex
            calc_eq = MathTex(r"12 \times 2 = 24", font_size=48)
            calc_eq.to_edge(RIGHT).shift(UP)
            
            calc_desc = Text("最多容纳", font_size=24, font=cn_font)
            calc_desc.next_to(calc_eq, UP)
            
            self.play(Write(calc_eq), FadeIn(calc_desc))

        # ------------------------------------------------------------
        # 镜头 S4: 第25个人触发
        # ------------------------------------------------------------
        # 旁白：可现实是有25个人。因为25大于24，第25个人无论放进哪里，必然会把某个属相的数量从2推到3。
        with self.voiceover(text=NARRATION[3]["text"]):
            # 强调 25 > 24
            ineq = MathTex(r"25 > 24", font_size=60, color=RED)
            ineq.next_to(calc_eq, DOWN, buff=0.8)
            
            but_text = Text("实际有 25 人", font_size=32, color=RED, font=cn_font)
            but_text.next_to(ineq, RIGHT)
            
            self.play(Write(ineq), Write(but_text))
            
            # 第25个点出现
            extra_dot = Dot(color=RED, radius=0.15)
            extra_dot.move_to(ineq.get_center())
            self.play(FadeIn(extra_dot))
            
            # 移动到第一个抽屉（或者随机一个）
            target_drawer = drawers[0][0]
            target_pos = target_drawer.get_center() + UP*0.3 # 放在上方形成三角形
            
            self.play(extra_dot.animate.move_to(target_pos))
            
            # 高亮该抽屉
            self.play(
                Indicate(drawers[0], color=RED),
                Flash(target_pos, color=RED)
            )
            
            # 添加第3个点进组，方便后续清理
            dots_group.add(extra_dot)

        # ------------------------------------------------------------
        # 镜头 S5: 结论展示 (VGroup 混排)
        # ------------------------------------------------------------
        # 旁白：所以我们得到结论：在25个人中，必然至少有3个人的属相相同。
        with self.voiceover(text=NARRATION[4]["text"]):
            # 清理旧元素，腾出空间展示结论
            self.play(
                FadeOut(assumption), FadeOut(limit_text), 
                FadeOut(calc_eq), FadeOut(calc_desc),
                FadeOut(ineq), FadeOut(but_text),
                drawers.animate.set_opacity(0.3),
                dots_group.animate.set_opacity(0.3)
            )
            
            # 核心修复点：不要把“至少”写进 MathTex
            # 构建句子： [因此] [至少] [3] [个人属相相同]
            t_therefore = Text("因此", font_size=36, font=cn_font)
            t_atleast = Text("至少", font_size=36, color=YELLOW, weight=BOLD, font=cn_font)
            m_three = MathTex(r"3", font_size=48, color=YELLOW)
            t_rest = Text("个人属相相同", font_size=36, font=cn_font)
            
            conclusion_group = VGroup(t_therefore, t_atleast, m_three, t_rest)
            conclusion_group.arrange(RIGHT, buff=0.2)
            conclusion_group.move_to(ORIGIN)
            
            self.play(Write(conclusion_group))
            
            # 框选强调
            box = SurroundingRectangle(VGroup(t_atleast, m_three), color=YELLOW, buff=0.15)
            self.play(Create(box))
            self.wait(1)

        # ------------------------------------------------------------
        # 镜头 S6: 模板化总结
        # ------------------------------------------------------------
        # 旁白：你可以把它当作一个通用模板：如果总人数超过“抽屉数乘以每个抽屉最多容纳的人数”，就一定会有某个抽屉超出限制，这里就从2变成3。
        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(FadeOut(conclusion_group), FadeOut(box))
            
            # 标题
            template_title = Text("抽屉原理（直觉版）", font_size=32, weight=BOLD, font=cn_font)
            template_title.to_edge(UP, buff=2.0)
            
            # 逻辑链
            # 1. 25 > 12 * 2
            logic1 = MathTex(r"25 > 12 \times 2", font_size=40)
            # 2. => 2 + 1 = 3
            logic2 = MathTex(r"\Rightarrow 2 + 1 = 3", font_size=40)
            
            logic_group = VGroup(logic1, logic2).arrange(DOWN, buff=0.5)
            logic_group.next_to(template_title, DOWN, buff=0.8)
            
            self.play(Write(template_title))
            self.play(Write(logic1))
            self.wait(0.5)
            self.play(Write(logic2))
            
            # 解释
            t_exp1 = Text("一旦超过平均上限", font_size=24, color=GRAY, font=cn_font)
            t_exp1.next_to(logic1, RIGHT, buff=0.5)
            
            t_exp2 = Text("必有抽屉达到 3", font_size=24, color=GRAY, font=cn_font)
            t_exp2.next_to(logic2, RIGHT, buff=0.5)
            
            self.play(FadeIn(t_exp1), FadeIn(t_exp2))

        # ------------------------------------------------------------
        # 镜头 S7: 制作避坑提示
        # ------------------------------------------------------------
        # 旁白：最后提醒制作细节：MathTex 只放数学，中文一律用 Text。渲染前全局搜一遍 MathTex 和 Tex 的内容，就能避免 Unicode 编译错误再次出现。
        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(
                FadeOut(template_title), FadeOut(logic_group),
                FadeOut(t_exp1), FadeOut(t_exp2),
                FadeOut(drawers), FadeOut(dots_group)
            )
            
            tip_title = Text("Manim 制作避坑指南", font_size=36, weight=BOLD, color=RED, font=cn_font)
            tip_title.to_edge(UP, buff=1.5)
            
            tip_1 = Text("❌ 错误：MathTex(\"至少 3 人\")", font_size=28, color=RED_B, font=cn_font)
            tip_2 = Text("✅ 正确：Text(\"至少\"), MathTex(\"3\"), Text(\"人\")", font_size=28, color=GREEN, font=cn_font)
            
            tips = VGroup(tip_1, tip_2).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
            tips.next_to(tip_title, DOWN, buff=0.8)
            
            self.play(Write(tip_title))
            self.play(FadeIn(tips[0]))
            self.wait(0.5)
            self.play(FadeIn(tips[1]))
        
        # 结尾定格
        self.wait(2)

# 运行提示：
# manim -pqh your_script.py ZodiacPigeonhole
