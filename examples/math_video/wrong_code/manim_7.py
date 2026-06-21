from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class ClassCountSolve(VoiceoverScene):
    def construct(self):
        # 1. 初始化语音服务
        self.set_speech_service(GTTSService(lang="zh-CN"))

        # 2. 定义配色方案
        C_BOY = BLUE      # 男生
        C_GIRL = PINK     # 女生
        C_TOTAL = YELLOW  # 总数
        C_LEFT = GREEN    # 剩余
        
        # 通用上色函数(避免索引错误)
        def color_math(mobj):
            mobj.set_color_by_tex_to_color_map({
                "x": C_BOY,
                "y": C_GIRL,
                "56": C_TOTAL,
                "40": C_LEFT,
                "32": C_BOY,
                "24": C_GIRL,
                r"\frac{3}{4}": C_BOY,
                r"\frac{1}{4}": C_BOY,
                r"\frac{2}{3}": C_GIRL,
                r"\frac{1}{3}": C_GIRL,
            })
            return mobj

        # === S01: 标题 ===
        with self.voiceover(text="这节课用方程解决一个经典人数问题：走了一个分数，就等于剩下一减这个分数"):
            title = Text("方程应用题：人数问题", font_size=48, color=WHITE)
            subtitle = Text("走了分数 → 剩下 1-分数", font_size=32, color=GREY_A)
            header = VGroup(title, subtitle).arrange(DOWN)
            header.move_to(ORIGIN)
            self.play(Write(header))
            self.wait(0.5)
            self.play(header.animate.scale(0.8).to_edge(UP, buff=0.2))

        # === S02: 题目呈现 ===
        with self.voiceover(text="题目给出：全班56人；女生走了三分之一，男生走了四分之一；走后还剩40人。求原来男生和女生各多少"):
            # 使用 Text 避免复杂的中文排版问题
            t1 = Text("一班有56人", font_size=32)
            t2 = Text("女生走了1/3，男生走了1/4", font_size=32)
            t3 = Text("还剩40人", font_size=32)
            t4 = Text("求：男女生各多少人？", font_size=32)
            
            problem_group = VGroup(t1, t2, t3, t4).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
            problem_group.to_edge(LEFT, buff=0.5).shift(UP*0.5)
            
            # 关键数字染色
            t1[3:5].set_color(C_TOTAL) # 56
            t2[4:7].set_color(C_GIRL)  # 1/3
            t2[12:15].set_color(C_BOY) # 1/4
            t3[2:4].set_color(C_LEFT)  # 40

            self.play(FadeIn(problem_group, shift=RIGHT))
            self.wait(1)

        # === S03: 设未知数 ===
        with self.voiceover(text="先设未知数：男生是 x 人，女生是 y 人"):
            # 创建变量定义文本
            def_text = VGroup(
                Text("设男生 x 人", font_size=36, t2c={"x": C_BOY}),
                Text("设女生 y 人", font_size=36, t2c={"y": C_GIRL})
            ).arrange(DOWN, aligned_edge=LEFT)
            def_text.next_to(problem_group, DOWN, buff=0.8).align_to(problem_group, LEFT)
            
            self.play(Write(def_text))

        # === S04: 方程1 ===
        with self.voiceover(text="因为总人数是56，所以第一条方程很直接：x加y等于56"):
            eq1 = MathTex(r"x + y = 56", font_size=48)
            color_math(eq1)
            eq1.next_to(def_text, DOWN, buff=0.5).align_to(def_text, LEFT)
            self.play(Write(eq1))

        # === S05: 剩余比例逻辑 ===
        with self.voiceover(text="注意关键转换：走了四分之一，就剩下四分之三；走了三分之一，就剩下三分之二"):
            # 提示框
            hint1 = MathTex(r"\text{男生走}\frac{1}{4} \Rightarrow \text{剩}\frac{3}{4}", tex_template=TexTemplateLibrary.ctex, font_size=32)
            hint2 = MathTex(r"\text{女生走}\frac{1}{3} \Rightarrow \text{剩}\frac{2}{3}", tex_template=TexTemplateLibrary.ctex, font_size=32)
            
            hint_group = VGroup(hint1, hint2).arrange(DOWN, aligned_edge=LEFT)
            hint_group.next_to(eq1, DOWN, buff=0.5).align_to(eq1, LEFT)
            
            # 安全上色
            hint1.set_color_by_tex(r"\frac{1}{4}", C_BOY)
            hint1.set_color_by_tex(r"\frac{3}{4}", C_BOY)
            hint2.set_color_by_tex(r"\frac{1}{3}", C_GIRL)
            hint2.set_color_by_tex(r"\frac{2}{3}", C_GIRL)
            
            self.play(FadeIn(hint_group, shift=UP))

        # === S06: 方程2 ===
        with self.voiceover(text="走后剩下的人数等于剩下的男生加剩下的女生，所以第二条方程是：四分之三x加三分之二y等于40"):
            eq2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=48)
            color_math(eq2)
            eq2.next_to(hint_group, DOWN, buff=0.5).align_to(hint_group, LEFT)
            self.play(Write(eq2))

        # === S07: 布局调整 (为解题腾出空间) ===
        with self.voiceover(text="接下来解这个方程组。我们用代入法，把未知数变成一个"):
            # 将题目淡出，方程组移到左上角
            system_group = VGroup(eq1, eq2)
            self.play(
                FadeOut(problem_group),
                FadeOut(def_text),
                FadeOut(hint_group),
                system_group.animate.scale(0.8).to_edge(UL, buff=1).shift(DOWN*1)
            )
            
            # 右侧标题
            solve_title = Text("解方程组", font_size=40).to_edge(UR, buff=2).shift(DOWN*1)
            self.play(Write(solve_title))
            
            # 分隔线
            line = Line(UP*2, DOWN*2).next_to(system_group, RIGHT, buff=0.5)
            self.play(Create(line))

        # === S08: 变形 ===
        with self.voiceover(text="由第一式得到 y等于56减x"):
            step1 = MathTex(r"y = 56 - x", font_size=40)
            color_math(step1)
            step1.next_to(solve_title, DOWN, buff=0.6).align_to(solve_title, LEFT)
            self.play(Write(step1))

        # === S09: 代入 ===
        with self.voiceover(text="把 y用56减x替换进第二式，得到：四分之三x加三分之二乘以括号里的56减x，等于40"):
            step2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}(56-x) = 40", font_size=40)
            color_math(step2)
            step2.next_to(step1, DOWN, buff=0.5).align_to(step1, LEFT)
            self.play(Write(step2))

        # === S10: 去分母 ===
        with self.voiceover(text="为了去掉分母，两边同乘12。分别化简后得到：9x加8倍的56减x等于480"):
            # 显示 x12 提示
            times_12 = MathTex(r"\times 12", color=RED, font_size=32)
            times_12.next_to(step2, RIGHT)
            self.play(FadeIn(times_12))
            
            step3 = MathTex(r"9x + 8(56-x) = 480", font_size=40)
            color_math(step3)
            step3.set_color_by_tex("480", C_LEFT)
            step3.next_to(step2, DOWN, buff=0.5).align_to(step2, LEFT)
            self.play(ReplacementTransform(step2.copy(), step3))
            self.wait(1)

        # === S11: 展开合并 ===
        with self.voiceover(text="展开括号：8乘56是448，8乘负x是负8x，合并同类项得到：x加448等于480"):
            step4 = MathTex(r"9x + 448 - 8x = 480", font_size=40)
            color_math(step4)
            step4.set_color_by_tex("448", C_TOTAL)
            step4.next_to(step3, DOWN, buff=0.4).align_to(step3, LEFT)
            self.play(Write(step4))
            self.wait(0.5)
            
            step5 = MathTex(r"x + 448 = 480", font_size=40)
            color_math(step5)
            step5.set_color_by_tex("448", C_TOTAL)
            step5.next_to(step4, DOWN, buff=0.4).align_to(step4, LEFT)
            self.play(TransformMatchingTex(step4, step5))

        # === S12: 解出 x ===
        with self.voiceover(text="两边同时减448，就得到 x等于32，也就是男生32人"):
            res_x = MathTex(r"x = 32", font_size=50)
            color_math(res_x)
            res_x.next_to(step5, DOWN, buff=0.5).align_to(step5, LEFT)
            self.play(Write(res_x))
            self.play(Indicate(res_x, color=C_BOY))

        # === S13: 解出 y ===
        with self.voiceover(text="再把x=32代回去：y等于56减32等于24，也就是女生24人"):
            res_y = MathTex(r"y = 56 - 32 = 24", font_size=50)
            color_math(res_y)
            res_y.next_to(res_x, DOWN, buff=0.5).align_to(res_x, LEFT)
            self.play(Write(res_y))
            self.play(Indicate(res_y, color=C_GIRL))

        # === S14: 检验与总结 ===
        # 清空屏幕，显示最终结论
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            run_time=1
        )

        with self.voiceover(text="检验一下：男生走四分之一，32的四分之一是8，剩24；女生走三分之一，24的三分之一也是8，剩16；24加16正好等于40"):
            check_g = VGroup(
                MathTex(r"\text{男生剩: } 32 \times \frac{3}{4} = 24", tex_template=TexTemplateLibrary.ctex),
                MathTex(r"\text{女生剩: } 24 \times \frac{2}{3} = 16", tex_template=TexTemplateLibrary.ctex),
                MathTex(r"\text{总剩余: } 24 + 16 = 40", tex_template=TexTemplateLibrary.ctex)
            ).arrange(DOWN, aligned_edge=LEFT)
            check_g.to_edge(UP, buff=1.5)
            
            # 手动上色
            check_g[0].set_color(C_BOY)
            check_g[1].set_color(C_GIRL)
            check_g[2].set_color(C_LEFT)
            
            self.play(Write(check_g))
            self.wait(2)

        with self.voiceover(text="所以答案是：男生32人，女生24人"):
            final_box = RoundedRectangle(corner_radius=0.5, height=3, width=6, color=YELLOW)
            ans_text = VGroup(
                Text("答 案", font_size=48),
                Text("男生：32人", font_size=40, color=C_BOY),
                Text("女生：24人", font_size=40, color=C_GIRL)
            ).arrange(DOWN, buff=0.4)
            
            ans_group = VGroup(final_box, ans_text).move_to(DOWN*1.5)
            self.play(Create(final_box), Write(ans_text))
            self.wait(3)