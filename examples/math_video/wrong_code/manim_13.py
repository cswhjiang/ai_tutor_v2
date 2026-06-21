from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# 定义旁白脚本列表，用于降级模式（如果 Voiceover 模块不可用）
NARRATION = [
    {"id": "S1_hook", "text": "你敢信吗？不管怎么挑，25个人里一定至少有3个人属相相同。这不是统计概率，而是一个必然的数学结论：抽屉原理。"},
    {"id": "S2_define_mapping", "text": "先做一个翻译：把12个属相当作12个抽屉；把每个人当作一个物品。问题就变成：把25个物品放进12个抽屉里，会发生什么？"},
    {"id": "S3_show_25_items", "text": "现在有25个人，也就是25个小球。我们把这些球一个个放进代表属相的12个抽屉里。"},
    {"id": "S4_division_core", "text": "核心就在一个除法：25除以12等于2余1。意思是：如果每个属相都尽量平均，12个抽屉每个先放2个人，总共放了24个人。还剩下1个人，不管他是谁，都必须再进入某一个抽屉。"},
    {"id": "S5_pigeonhole_conclusion", "text": "因为多出来的那1个人必然落在某个抽屉里，于是那个抽屉里至少就有2加1等于3个人。翻译回原问题：至少有3个人属相相同。这就是抽屉原理。"},
    {"id": "S6_debug_fix", "text": "制作上一次失败的原因也很简单：Manim里动画类名应该是 Succession，但被误写成了 Successession，于是直接触发 NameError。把拼写统一改回 Succession，就能正常渲染，内容逻辑不需要改。"},
    {"id": "S7_outro", "text": "总结一句：12个属相就是12个抽屉，25个人放进去，必然挤出一个抽屉装下至少3个人。抽屉原理就是这么直接而有力。"}
]

class ZodiacPigeonholeScene(VoiceoverScene):
    def construct(self):
        # 设置 TTS 服务
        self.set_speech_service(GTTSService(lang="zh-CN", tld="com"))

        # --- Step 1: 标题 + 问题抛出 (S1_hook) ---
        # 旁白：你敢信吗？不管怎么挑，25个人里一定至少有3个人属相相同...
        with self.voiceover(text=NARRATION[0]["text"]):
            title = Text("抽屉原理：25人中至少3人属相相同", font_size=36, weight=BOLD)
            subtitle = Text("真的一定会重复到3个吗？", font_size=28, color=YELLOW)
            
            title.to_edge(UP, buff=1.0)
            subtitle.next_to(title, DOWN, buff=0.5)
            
            self.play(Write(title))
            self.play(FadeIn(subtitle))
            self.wait(2)
            
            # 清理副标题，标题上移
            self.play(
                FadeOut(subtitle),
                title.animate.to_edge(UP, buff=0.5)
            )

        # --- Step 2: 建立“抽屉/物品”对应 (S2_define_mapping) ---
        # 旁白：先做一个翻译：把12个属相当作12个抽屉；把每个人当作一个物品...
        with self.voiceover(text=NARRATION[1]["text"]):
            # 12个抽屉的标签
            drawers_label = Text("12个属相 = 12个抽屉", font_size=30).to_edge(LEFT, buff=1.0).shift(UP*1.5)
            self.play(FadeIn(drawers_label))

            # 创建12个方框表示抽屉 (3行4列)
            drawers = VGroup(*[Square(side_length=0.8, color=BLUE_C) for _ in range(12)])
            drawers.arrange_in_grid(rows=3, cols=4, buff=0.2)
            drawers.next_to(drawers_label, DOWN, buff=0.5, aligned_edge=LEFT)
            
            # 给抽屉加编号
            drawer_nums = VGroup(*[
                Text(str(i+1), font_size=20).move_to(drawers[i]) for i in range(12)
            ])

            # 显示抽屉和编号
            self.play(LaggedStart(*[Create(sq) for sq in drawers], lag_ratio=0.05), run_time=1.5)
            self.play(LaggedStart(*[FadeIn(t) for t in drawer_nums], lag_ratio=0.05), run_time=1.0)

            # 25个物品的标签
            people_label = Text("25个人 = 25个物品", font_size=30)
            people_label.next_to(drawers, DOWN, buff=1.0, aligned_edge=LEFT)
            self.play(FadeIn(people_label))

        # --- Step 3: 展示25个物品并准备“放入抽屉” (S3_show_25_items) ---
        # 旁白：现在有25个人，也就是25个小球。我们把这些球一个个放进代表属相的12个抽屉里。
        with self.voiceover(text=NARRATION[2]["text"]):
            balls = VGroup(*[Dot(radius=0.1, color=RED) for _ in range(25)])
            balls.arrange_in_grid(rows=5, cols=5, buff=0.15)
            balls.next_to(people_label, DOWN, buff=0.3, aligned_edge=LEFT)
            
            self.play(LaggedStart(*[FadeIn(b) for b in balls], lag_ratio=0.02), run_time=2.0)
            
            # 箭头指向
            arrow = Arrow(start=balls.get_right(), end=drawers.get_bottom(), buff=0.5, color=WHITE)
            self.play(GrowArrow(arrow))
            self.wait(1)

        # --- Step 4: 关键计算：25除以12 (S4_division_core) ---
        # 旁白：核心就在一个除法：25除以12等于2余1...
        with self.voiceover(text=NARRATION[3]["text"]):
            # 右侧区域显示公式
            math_group = VGroup()
            
            # 公式
            formula = MathTex(r"25 \div 12 = 2 \dots 1", font_size=48)
            
            # 解释文字
            expl1 = Text("平均每个抽屉放 2 人", font_size=24, color=GRAY_A)
            expl2 = Text("共用掉 24 人", font_size=24, color=GRAY_A)
            expl3 = Text("还剩 1 人 (余数)", font_size=24, color=RED_A)
            expl4 = Text("必须再进某个抽屉", font_size=24, color=RED)
            
            # 组合布局
            math_group.add(formula, expl1, expl2, expl3, expl4)
            math_group.arrange(DOWN, buff=0.4, aligned_edge=LEFT)
            math_group.to_edge(RIGHT, buff=1.5).shift(UP*0.5)
            
            self.play(Write(formula))
            self.wait(1)
            self.play(FadeIn(expl1))
            self.play(FadeIn(expl2))
            self.wait(1)
            self.play(FadeIn(expl3))
            self.play(Indicate(expl3))
            self.play(FadeIn(expl4))

        # --- Step 5: 推出“至少3人同属相”的结论 (S5_pigeonhole_conclusion) ---
        # 旁白：因为多出来的那1个人必然落在某个抽屉里，于是那个抽屉里至少就有2加1等于3个人...
        with self.voiceover(text=NARRATION[4]["text"]):
            # 结论公式
            conclusion_tex = MathTex(r"\Rightarrow \text{至少 } 2 + 1 = 3 \text{ 人}", font_size=42, color=YELLOW)
            conclusion_text = Text("属相相同", font_size=36, color=YELLOW)
            
            conclusion_group = VGroup(conclusion_tex, conclusion_text).arrange(RIGHT, buff=0.2)
            conclusion_group.next_to(math_group, DOWN, buff=0.8)
            
            # 动画：高亮抽屉 -> 显示结论
            # 修正点：使用正确的 Succession 类
            self.play(
                Succession(
                    Indicate(drawers, color=YELLOW, scale_factor=1.05),
                    Write(conclusion_group),
                    lag_ratio=0.2
                )
            )
            
            # 模拟：在一个抽屉上多显示一个点，示意 2+1=3
            # 选取第5个抽屉演示
            target_drawer = drawers[4]
            demo_dots = VGroup(*[Dot(radius=0.08, color=YELLOW) for _ in range(3)])
            demo_dots.arrange(RIGHT, buff=0.05)
            demo_dots.move_to(target_drawer.get_center())
            
            # 隐藏原来的数字，显示3个点
            self.play(
                FadeOut(drawer_nums[4]),
                FadeIn(demo_dots),
                target_drawer.animate.set_fill(YELLOW, opacity=0.2)
            )
            self.wait(1)

        # --- Step 6: 修复说明 (S6_debug_fix) ---
        # 旁白：制作上一次失败的原因也很简单：Manim里动画类名应该是 Succession...
        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(
                FadeOut(drawers), FadeOut(drawer_nums), FadeOut(balls), FadeOut(arrow),
                FadeOut(drawers_label), FadeOut(people_label),
                FadeOut(demo_dots), FadeOut(math_group), FadeOut(conclusion_group)
            )
            
            # 显示代码修复卡片
            code_bg = Rectangle(width=10, height=5, fill_color=BLACK, fill_opacity=0.8, stroke_color=WHITE)
            error_text = Text("错误写法: Successession(...)", color=RED, font_size=32, font="Consolas")
            correct_text = Text("正确写法: Succession(...)", color=GREEN, font_size=32, font="Consolas")
            
            code_group = VGroup(error_text, correct_text).arrange(DOWN, buff=0.5)
            code_group.move_to(code_bg)
            
            title_fix = Text("Debug Note: NameError 修复", font_size=24, color=GRAY).next_to(code_bg, UP, buff=0.2)
            
            self.play(Create(code_bg), Write(title_fix))
            self.play(FadeIn(error_text))
            self.wait(0.5)
            
            # 叉号和勾号
            cross = Text("❌", font_size=32).next_to(error_text, LEFT)
            check = Text("✅", font_size=32).next_to(correct_text, LEFT)
            
            self.play(Write(cross), run_time=0.5)
            self.play(TransformFromCopy(error_text, correct_text), Write(check))
            self.wait(2)
            
            self.play(FadeOut(code_bg), FadeOut(code_group), FadeOut(title_fix), FadeOut(cross), FadeOut(check))

        # --- Step 7: 总结 (S7_outro) ---
        # 旁白：总结一句：12个属相就是12个抽屉，25个人放进去，必然挤出一个抽屉装下至少3个人...
        with self.voiceover(text=NARRATION[6]["text"]):
            summary_1 = Text("12个抽屉 + 25个物品", font_size=36)
            summary_arrow = MathTex(r"\Rightarrow", font_size=48)
            summary_2 = Text("至少有一抽屉 ≥ 3", font_size=36, color=YELLOW)
            
            summary_line = VGroup(summary_1, summary_arrow, summary_2).arrange(RIGHT, buff=0.3)
            summary_line.move_to(ORIGIN)
            
            self.play(FadeIn(summary_line))
            self.play(Circumscribe(summary_2))
            
            final_text = Text("抽屉原理", font_size=60, weight=BOLD, color=BLUE).next_to(summary_line, UP, buff=1.0)
            self.play(Write(final_text))
            
            self.wait(3)
            self.play(FadeOut(summary_line), FadeOut(final_text), FadeOut(title))

# manim -pqh zodiac_pigeonhole.py ZodiacPigeonholeScene
