from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class ClassBoysGirlsSolve(VoiceoverScene):
    def construct(self):
        # 初始化语音服务
        self.set_speech_service(GTTSService(lang="zh-CN"))

        # ==========================================
        # 1. 题目引入
        # ==========================================
        # 标题
        title = Text("一元一次方程组应用题：男女人数", font_size=40, color=BLUE)
        title.to_edge(UP, buff=0.5)
        
        # 题目内容 (使用 Text + \n 避免 MarkupText 的 <br> 问题)
        problem_str = "题目：一班有56人。\n女生走了1/3，男生走了1/4。\n还剩40人，男女生各有多少人？"
        problem = Text(problem_str, font_size=28, line_spacing=1.2, t2c={"56": YELLOW, "40": YELLOW})
        problem.to_edge(LEFT, buff=1.0).shift(UP * 1.5)

        with self.voiceover(text="这道题的关键是：总人数是五十六人，但女生走了三分之一，男生走了四分之一，最后还剩四十人。我们要求原来男生女生各多少人。"):
            self.play(Write(title))
            self.play(FadeIn(problem))
            self.wait(1)

        # ==========================================
        # 2. 设未知数
        # ==========================================
        # 变量定义
        var_text = Text("设：男生 x 人，女生 y 人", font_size=32, color=GREEN)
        var_text.next_to(problem, DOWN, buff=0.8).align_to(problem, LEFT)

        with self.voiceover(text="先设男生有 x 人，女生有 y 人。这样题目里的每一句话都能翻译成方程。"):
            self.play(Write(var_text))
            self.wait(0.5)

        # ==========================================
        # 3. 列第一条方程 (总人数)
        # ==========================================
        # 右侧解题区域起始点
        work_area_start = UP * 1.5 + RIGHT * 0.5
        
        eq1 = MathTex(r"x + y = 56", font_size=48)
        eq1.move_to(work_area_start)

        with self.voiceover(text="全班一共五十六人，所以第一条方程就是：x 加 y 等于五十六。"):
            # 高亮题目中的56
            self.play(Indicate(problem[6:8], color=YELLOW, scale_factor=1.5))
            self.play(Write(eq1))

        # ==========================================
        # 4. 分析剩余比例
        # ==========================================
        # 辅助分析文本
        analysis_text1 = Text("女生剩: 1 - 1/3 = 2/3", font_size=26, color=TEAL)
        analysis_text2 = Text("男生剩: 1 - 1/4 = 3/4", font_size=26, color=TEAL)
        
        analysis_group = VGroup(analysis_text1, analysis_text2).arrange(DOWN, aligned_edge=LEFT)
        analysis_group.next_to(var_text, DOWN, buff=0.8).align_to(var_text, LEFT)

        with self.voiceover(text="女生走了三分之一，表示女生只剩下三分之二，所以女生剩余人数是三分之二乘以 y。"):
            self.play(FadeIn(analysis_text1))
            # 展示对应的代数项
            term_girls = MathTex(r"\frac{2}{3}y", font_size=40, color=TEAL)
            term_girls.next_to(eq1, DOWN, buff=1.0).shift(LEFT * 1.5)
            self.play(Write(term_girls))

        with self.voiceover(text="男生走了四分之一，表示男生剩下四分之三，所以男生剩余人数是四分之三乘以 x。"):
            self.play(FadeIn(analysis_text2))
            # 展示对应的代数项
            term_boys = MathTex(r"\frac{3}{4}x", font_size=40, color=TEAL)
            term_boys.next_to(term_girls, LEFT, buff=0.5)
            self.play(Write(term_boys))

        # ==========================================
        # 5. 列第二条方程 (剩余人数)
        # ==========================================
        # 组合成完整方程
        eq2_part = MathTex(r"+", font_size=40)
        eq2_part.next_to(term_boys, RIGHT, buff=0.2)
        # term_girls 需要调整位置到加号右边
        
        eq2_result = MathTex(r"= 40", font_size=40)
        
        # 这里为了动画流畅，重新构建第二行方程
        eq2_full = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=48)
        eq2_full.move_to(term_boys.get_center() + RIGHT * 1.5) # 大致位置

        with self.voiceover(text="剩下的总人数是四十人，所以把男生剩余和女生剩余相加：四分之三 x 加三分之二 y 等于四十。"):
            self.play(
                ReplacementTransform(VGroup(term_boys, term_girls), eq2_full),
                Indicate(problem.get_parts_by_text("40"))
            )
            self.wait(1)

        # ==========================================
        # 6. 代入法准备
        # ==========================================
        step_arrow = MathTex(r"\Downarrow", font_size=36)
        step_arrow.next_to(eq1, RIGHT, buff=0.5)
        
        sub_expr = MathTex(r"y = 56 - x", font_size=40, color=YELLOW)
        sub_expr.next_to(step_arrow, RIGHT, buff=0.3)

        with self.voiceover(text="接着用代入法。由 x 加 y 等于五十六，我们把 y 表达出来：y 等于五十六减 x。"):
            self.play(Write(step_arrow))
            self.play(Write(sub_expr))

        # ==========================================
        # 7. 代入求解
        # ==========================================
        # 替换方程2
        eq3 = MathTex(r"\frac{3}{4}x + \frac{2}{3}(56-x) = 40", font_size=44)
        eq3.next_to(eq2_full, DOWN, buff=0.8)

        with self.voiceover(text="把 y 用五十六减 x 替换，第二个方程就变成：四分之三 x 加上三分之二乘以括号五十六减 x，等于四十。"):
            self.play(Write(eq3))
            self.play(Circumscribe(eq3, color=YELLOW, fade_out=True))

        # ==========================================
        # 8. 通分
        # ==========================================
        hint_mul = Text("× 12", font_size=36, color=RED)
        hint_mul.next_to(eq3, RIGHT, buff=0.5)
        
        eq4 = MathTex(r"9x + 8(56-x) = 480", font_size=44)
        eq4.next_to(eq3, DOWN, buff=0.6)

        with self.voiceover(text="为了去掉分母，我们让等式两边同乘十二。这样四分之三变成九，三分之二变成八，右边四十变成四百八十。"):
            self.play(Write(hint_mul))
            self.play(TransformFromCopy(eq3, eq4))

        # ==========================================
        # 9. 展开与求解 X
        # ==========================================
        eq5 = MathTex(r"9x + 448 - 8x = 480", font_size=44)
        eq5.next_to(eq4, DOWN, buff=0.5)
        
        eq6 = MathTex(r"x + 448 = 480", font_size=44)
        eq6.move_to(eq5)
        
        eq7 = MathTex(r"x = 32", font_size=48, color=YELLOW)
        eq7.next_to(eq5, DOWN, buff=0.5)

        with self.voiceover(text="展开括号：八乘五十六是四百四十八，同时还有减八 x。"):
            self.play(Write(eq5))
        
        with self.voiceover(text="九 x 减八 x 就剩一个 x，所以得到 x 加四百四十八等于四百八十，解得 x 等于三十二。"):
            self.play(ReplacementTransform(eq5, eq6))
            self.wait(0.5)
            self.play(Write(eq7))

        # ==========================================
        # 10. 求解 Y 与总结
        # ==========================================
        # 清理上面的计算过程，腾出空间展示结论
        final_group = VGroup(eq7)
        
        with self.voiceover(text="再回到 y 等于五十六减 x，代入 x 等于三十二，得到 y 等于二十四。"):
            # 淡出中间步骤
            self.play(
                FadeOut(eq3), FadeOut(hint_mul), FadeOut(eq4), FadeOut(eq6), 
                FadeOut(eq2_full), FadeOut(eq1), FadeOut(step_arrow), FadeOut(sub_expr),
                eq7.animate.move_to(work_area_start + DOWN * 1)
            )
            
            eq_y = MathTex(r"y = 56 - 32 = 24", font_size=48, color=YELLOW)
            eq_y.next_to(eq7, DOWN, buff=0.5)
            self.play(Write(eq_y))

        # 最终答案
        answer_box = Rectangle(width=6, height=2, color=YELLOW)
        answer_text = Text("答案：\n男生 32 人\n女生 24 人", font_size=36, line_spacing=1.5)
        answer_group = VGroup(answer_box, answer_text).move_to(DOWN * 2 + RIGHT * 2)
        
        with self.voiceover(text="所以男生有三十二人，女生有二十四人。"):
            self.play(Create(answer_box), Write(answer_text))

        # ==========================================
        # 11. 验算 (可选)
        # ==========================================
        check_text1 = MathTex(r"\frac{3}{4} \times 32 = 24", font_size=32)
        check_text2 = MathTex(r"\frac{2}{3} \times 24 = 16", font_size=32)
        check_text3 = MathTex(r"24 + 16 = 40", font_size=32)
        
        check_group = VGroup(check_text1, check_text2, check_text3).arrange(RIGHT, buff=0.5)
        check_group.to_edge(DOWN, buff=0.5)

        with self.voiceover(text="简单验算一下：男生剩二十四人，女生剩十六人，加起来正好等于四十，结果正确。"):
            self.play(Write(check_group))
            self.play(Indicate(check_text3, color=GREEN))

        self.wait(2)