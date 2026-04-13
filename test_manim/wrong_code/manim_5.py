from manim import *
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    HAS_VOICEOVER = True
except ImportError:
    HAS_VOICEOVER = False
    class VoiceoverScene(Scene):
        class VoiceoverContext:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        def voiceover(self, text=None): return self.VoiceoverContext()
        def set_speech_service(self, service): pass

class SolveClassProblem(VoiceoverScene):
    def construct(self):
        if HAS_VOICEOVER:
            self.set_speech_service(GTTSService(lang="zh-CN"))

        title = Text("分数应用题：走了几分之几", font_size=42, color=BLUE)
        title.to_edge(UP, buff=0.8)
        
        with self.voiceover(text="这道题考的是走了几分之几之后，剩下多少，用方程把人数关系写清楚就能解出来"):
            self.play(Write(title))
        
        problem_lines = [
            "一班有56人，女生走了1/3，男生走了1/4。",
            "还剩40人，男女生各有多少人？"
        ]
        problem_text = VGroup(
            Text(problem_lines[0], font_size=28),
            Text(problem_lines[1], font_size=28)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        problem_text.next_to(title, DOWN, buff=0.5)
        
        with self.voiceover(text="全班56人。女生走了三分之一，男生走了四分之一，最后还剩40人。我们要求原来男生和女生各多少"):
            self.play(FadeIn(problem_text))
            self.wait(0.5)
            self.play(Indicate(problem_text, color=YELLOW))

        self.play(
            problem_text.animate.scale(0.8).to_edge(UP, buff=1.8),
            title.animate.scale(0.8).to_edge(UP, buff=0.2)
        )

        assume_text = Text("设男生 x 人，女生 y 人", font_size=32, color=YELLOW)
        assume_text.next_to(problem_text, DOWN, buff=0.8).to_edge(LEFT, buff=1)

        with self.voiceover(text="先设未知数。设男生有 x 人，女生有 y 人"):
            self.play(Write(assume_text))

        eq1 = MathTex(r"x + y = 56", font_size=48)
        eq1.next_to(assume_text, DOWN, buff=0.5).align_to(assume_text, LEFT)
        
        eq1_note = Text("总人数", font_size=24, color=GRAY).next_to(eq1, RIGHT, buff=0.5)

        with self.voiceover(text="因为全班一共56人，所以第一个方程是 x 加 y 等于 56"):
            self.play(Write(eq1))
            self.play(FadeIn(eq1_note))

        remain_info = VGroup(
            Text("男生剩: ", font_size=28),
            MathTex(r"1 - \frac{1}{4} = \frac{3}{4}", font_size=32),
            Text("女生剩: ", font_size=28),
            MathTex(r"1 - \frac{1}{3} = \frac{2}{3}", font_size=32)
        ).arrange(RIGHT, buff=0.4)
        remain_info.next_to(eq1, DOWN, buff=0.8).align_to(assume_text, LEFT)

        with self.voiceover(text="注意，走了四分之一，剩下就是四分之三。女生走了三分之一，剩下三分之二"):
            self.play(FadeIn(remain_info))

        eq2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=48)
        eq2.next_to(remain_info, DOWN, buff=0.5).align_to(assume_text, LEFT)
        
        eq2_note = Text("剩下人数", font_size=24, color=GRAY).next_to(eq2, RIGHT, buff=0.5)

        with self.voiceover(text="因为剩下的人一共是40，所以男生剩下的四分之三x，加上女生剩下的三分之二y，等于40"):
            self.play(Write(eq2))
            self.play(FadeIn(eq2_note))

        group_equations = VGroup(eq1, eq2)
        
        self.play(
            FadeOut(assume_text),
            FadeOut(remain_info),
            FadeOut(eq1_note),
            FadeOut(eq2_note),
            group_equations.animate.move_to(UP * 2)
        )

        step1 = MathTex(r"x = 56 - y", color=BLUE)
        step1.next_to(group_equations, DOWN, buff=0.5)

        with self.voiceover(text="现在解这个方程组。先由第一式得到，x 等于 56 减 y"):
            self.play(Write(step1))

        step2 = MathTex(r"\frac{3}{4}(56 - y) + \frac{2}{3}y = 40")
        step2.next_to(step1, DOWN, buff=0.4)

        with self.voiceover(text="把 x 换成 56减y，代入第二式"):
            self.play(Write(step2))

        step3 = MathTex(r"42 - \frac{3}{4}y + \frac{2}{3}y = 40")
        step3.next_to(step2, DOWN, buff=0.4)

        with self.voiceover(text="四分之三乘以56等于42，再减去四分之三 y，加上三分之二 y，等于40"):
            self.play(Write(step3))

        step4 = MathTex(r"42 - \frac{1}{12}y = 40")
        step4.next_to(step3, DOWN, buff=0.4)
        
        hint = MathTex(r"-\frac{9}{12} + \frac{8}{12} = -\frac{1}{12}", font_size=30, color=YELLOW)
        hint.next_to(step4, RIGHT, buff=0.5)

        with self.voiceover(text="合并 y 的系数。四分之三是十二分之九，三分之二是十二分之八，合并后是负的十二分之一 y"):
            self.play(Write(step4))
            self.play(FadeIn(hint))
            self.wait(1)

        step5 = MathTex(r"\frac{1}{12}y = 2 \quad \Rightarrow \quad y = 24")
        step5.next_to(step4, DOWN, buff=0.4)

        with self.voiceover(text="移项整理，得到十二分之一 y 等于 2，所以 y 等于 24"):
            self.play(Write(step5))
            self.play(Indicate(step5[-4:], color=GREEN))

        step6 = MathTex(r"x = 56 - 24 = 32")
        step6.next_to(step5, DOWN, buff=0.4)

        with self.voiceover(text="再算出 x，56 减 24 等于 32"):
            self.play(Write(step6))
            self.play(Indicate(step6[-2:], color=GREEN))

        self.play(
            FadeOut(title), FadeOut(problem_text), 
            FadeOut(group_equations), FadeOut(step1), 
            FadeOut(step2), FadeOut(step3), 
            FadeOut(step4), FadeOut(step5), 
            FadeOut(step6), FadeOut(hint)
        )

        final_answer = Text("答案：男生 32 人，女生 24 人", font_size=48, color=YELLOW)
        final_answer.move_to(UP * 0.5)
        
        check_box = VGroup(
            Text("验算:", font_size=32, color=BLUE),
            Text("男生走: 32 × 1/4 = 8 (剩24)", font_size=28),
            Text("女生走: 24 × 1/3 = 8 (剩16)", font_size=28),
            Text("总剩下: 24 + 16 = 40 (正确)", font_size=28, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        check_box.next_to(final_answer, DOWN, buff=1)

        with self.voiceover(text="答案是：男生32人，女生24人"):
            self.play(Write(final_answer))
        
        with self.voiceover(text="最后验算一下：男生32人走四分之一是8人剩24人；女生24人走三分之一也是8人剩16人；总共剩下40人，完全正确"):
            self.play(FadeIn(check_box))
            self.wait(2)