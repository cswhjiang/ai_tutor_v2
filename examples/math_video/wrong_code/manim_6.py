from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# 定义通用颜色
BOY_COLOR = BLUE
GIRL_COLOR = PINK
TEXT_COLOR = WHITE
HIGHLIGHT_COLOR = YELLOW

class MathEquationSolver(VoiceoverScene):
    def construct(self):
        # 初始化语音服务
        self.set_speech_service(GTTSService(lang="zh-CN"))
        
        # --- 镜头0：标题页 ---
        with self.voiceover(text="这道题用设未知数，再列方程组的方法，一步一步就能算出男生女生各多少"):
            title = Text("方程应用题：走了一部分，还剩多少？", font_size=48, color=HIGHLIGHT_COLOR)
            subtitle = Text("关键方法：设未知数 + 列方程组", font_size=32)
            
            title.to_edge(UP, buff=1.5)
            subtitle.next_to(title, DOWN, buff=0.5)
            
            self.play(Write(title), FadeIn(subtitle))
            self.wait(1)

        self.play(FadeOut(title), FadeOut(subtitle))

        # --- 镜头1：题目呈现 ---
        # 预先定义字幕位置
        captions = VGroup()
        
        with self.voiceover(text="题目是：一班有五十六人，女生走了三分之一，男生走了四分之一，最后还剩四十人，求原来男生和女生分别多少人"):
            problem_text = Text(
                "一班有56人，女生走了1/3，男生走了1/4。\n还剩40人，男女生各有多少人？",
                font_size=32,
                line_spacing=1.5,
                t2c={"56": YELLOW, "1/3": GIRL_COLOR, "1/4": BOY_COLOR, "40": YELLOW}
            )
            problem_text.to_edge(UP, buff=0.5)
            self.play(Write(problem_text))

        # --- 镜头2：信息提炼 ---
        with self.voiceover(text="先把关键信息提炼出来：总人数是五十六；男生走了四分之一，等会儿要用到剩下四分之三；女生走了三分之一，剩下三分之二；最后总共剩四十人"):
            info_group = VGroup(
                Text("已知：总人数 56", font_size=28),
                Text("已知：男生走 1/4 → 剩 3/4", font_size=28, color=BOY_COLOR),
                Text("已知：女生走 1/3 → 剩 2/3", font_size=28, color=GIRL_COLOR),
                Text("已知：剩余总人数 40", font_size=28)
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
            
            info_group.next_to(problem_text, DOWN, buff=0.5)
            info_group.to_edge(LEFT, buff=1)
            self.play(FadeIn(info_group, shift=RIGHT))

        # --- 镜头3：设未知数 ---
        with self.voiceover(text="因为题目问两类人数，我们就设：男生人数是 x，女生人数是 y"):
            var_def = VGroup(
                Text("设：男生人数 =", font_size=36),
                MathTex(r"x", color=BOY_COLOR, font_size=48),
                Text("设：女生人数 =", font_size=36),
                MathTex(r"y", color=GIRL_COLOR, font_size=48)
            ).arrange_in_grid(rows=2, cols=2, buff=0.2, col_alignments="lr")
            
            var_def.next_to(info_group, RIGHT, buff=1.5)
            self.play(Write(var_def))

        # --- 镜头4：列方程(1) ---
        with self.voiceover(text="全班一共五十六人，所以第一条关系很直接：x 加 y 等于五十六"):
            eq1_label = Text("方程(1)", font_size=24, color=YELLOW)
            eq1 = MathTex(r"x + y = 56", font_size=48)
            eq1[0].set_color(BOY_COLOR) # x
            eq1[2].set_color(GIRL_COLOR) # y
            
            eq1_group = VGroup(eq1_label, eq1).arrange(DOWN, buff=0.2)
            eq1_group.move_to(ORIGIN).shift(DOWN * 1)
            
            self.play(Write(eq1_group))
            self.play(eq1_group.animate.scale(0.8).to_corner(UL, buff=1).shift(DOWN*1.5))
        
        # 清理这一步不需要的元素，保留方程1
        self.play(FadeOut(info_group), FadeOut(var_def))

        # --- 镜头5：分数转化可视化 ---
        # 这是一个关键难点，用图形演示
        with self.voiceover(text="关键点在这里：题目给的是走了，但方程要用剩下。男生走了四分之一"):
            # 男生条
            bar_boy = Rectangle(width=4, height=0.6, color=BOY_COLOR, fill_opacity=0.3)
            bar_boy.move_to(UP * 0.5)
            label_boy = Text("男生 x", font_size=24, color=BOY_COLOR).next_to(bar_boy, LEFT)
            
            # 分割线
            lines_boy = VGroup(*[Line(bar_boy.get_top() + RIGHT*(i-1.5), bar_boy.get_bottom() + RIGHT*(i-1.5)) for i in range(1, 4)])
            
            self.play(Create(bar_boy), Write(label_boy), Create(lines_boy))

        with self.voiceover(text="所以剩下的是一减四分之一，也就是四分之三，剩下男生是四分之三乘 x"):
            # 变暗第一块
            gone_part = Rectangle(width=1, height=0.6, color=GREY, fill_opacity=0.8).move_to(bar_boy.get_left() + RIGHT*0.5)
            self.play(FadeIn(gone_part))
            
            brace_boy = Brace(VGroup(gone_part, bar_boy), DOWN)
            text_remain_boy = MathTex(r"\frac{3}{4}x", color=BOY_COLOR).next_to(brace_boy, DOWN)
            self.play(Create(brace_boy), Write(text_remain_boy))

        with self.voiceover(text="女生同理，走了三分之一，剩下三分之二，所以剩下女生是三分之二乘 y"):
            # 女生条
            bar_girl = Rectangle(width=4, height=0.6, color=GIRL_COLOR, fill_opacity=0.3)
            bar_girl.next_to(text_remain_boy, DOWN, buff=1.0)
            label_girl = Text("女生 y", font_size=24, color=GIRL_COLOR).next_to(bar_girl, LEFT)
            
            # 分割线 (3份)
            step_width = 4/3
            lines_girl = VGroup(*[Line(bar_girl.get_top() + RIGHT*(i*step_width - 2), bar_girl.get_bottom() + RIGHT*(i*step_width - 2)) for i in range(1, 3)])
            
            self.play(Create(bar_girl), Write(label_girl), Create(lines_girl))
            
            # 变暗第一块
            gone_part_girl = Rectangle(width=step_width, height=0.6, color=GREY, fill_opacity=0.8).align_to(bar_girl, LEFT).align_to(bar_girl, UP)
            self.play(FadeIn(gone_part_girl))
            
            brace_girl = Brace(VGroup(gone_part_girl, bar_girl), DOWN)
            text_remain_girl = MathTex(r"\frac{2}{3}y", color=GIRL_COLOR).next_to(brace_girl, DOWN)
            self.play(Create(brace_girl), Write(text_remain_girl))

        # --- 镜头6：列方程(2) ---
        with self.voiceover(text="现在把剩下的男生和剩下的女生加起来，就是剩余总人数四十人，所以第二个方程是：四分之三 x 加三分之二 y 等于四十"):
            eq2_label = Text("方程(2)", font_size=24, color=YELLOW)
            eq2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=48)
            eq2[0].set_color(BOY_COLOR) # 3/4x part
            eq2[2].set_color(GIRL_COLOR) # 2/3y part
            
            eq2_group = VGroup(eq2_label, eq2).arrange(DOWN, buff=0.2)
            eq2_group.move_to(ORIGIN).shift(DOWN * 2) # 临时位置
            
            self.play(Write(eq2_group))
            
        # 清理图形，整理两个方程
        self.play(
            FadeOut(bar_boy), FadeOut(label_boy), FadeOut(lines_boy), FadeOut(gone_part), FadeOut(brace_boy), FadeOut(text_remain_boy),
            FadeOut(bar_girl), FadeOut(label_girl), FadeOut(lines_girl), FadeOut(gone_part_girl), FadeOut(brace_girl), FadeOut(text_remain_girl),
            eq2_group.animate.scale(0.8).next_to(eq1_group, DOWN, buff=0.5)
        )

        # --- 镜头7：解方程组 ---
        with self.voiceover(text="解这个方程组，我们用代入法。先由方程一得到 y 等于五十六减 x"):
            step1 = MathTex(r"\text{由(1)得: } y = 56 - x", font_size=36)
            step1.move_to(ORIGIN).shift(UP*0.5)
            self.play(Write(step1))

        with self.voiceover(text="把它代入方程二：四分之三 x 加三分之二乘括号五十六减 x，等于四十"):
            step2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}(56 - x) = 40", font_size=36)
            step2.next_to(step1, DOWN, buff=0.3)
            self.play(Write(step2))

        with self.voiceover(text="为了去掉分母，两边同乘十二，就变成：九 x 加八乘括号五十六减 x，等于四百八十"):
            # 提示动画
            hint = Text("× 12 去分母", font_size=24, color=RED).next_to(step2, RIGHT)
            self.play(FadeIn(hint, shift=LEFT))
            
            step3 = MathTex(r"9x + 8(56 - x) = 480", font_size=40, color=YELLOW)
            step3.next_to(step2, DOWN, buff=0.4)
            self.play(Write(step3))

        # --- 镜头8：求解 ---
        # 向上滚动，腾出空间
        group_process = VGroup(step1, step2, hint, step3)
        self.play(group_process.animate.to_edge(UP, buff=2.5).scale(0.8))

        with self.voiceover(text="展开括号：九 x 加四百四十八减八 x 等于四百八十"):
            step4 = MathTex(r"9x + 448 - 8x = 480", font_size=36)
            step4.next_to(group_process, DOWN, buff=0.3)
            self.play(Write(step4))

        with self.voiceover(text="合并同类项就是 x 加四百四十八等于四百八十，所以 x 等于三十二"):
            step5 = MathTex(r"x + 448 = 480", font_size=36)
            step5.next_to(step4, DOWN, buff=0.2)
            
            ans_x = MathTex(r"x = 32", font_size=48, color=BOY_COLOR)
            ans_x.next_to(step5, DOWN, buff=0.3)
            
            self.play(Write(step5))
            self.play(Indicate(ans_x))

        with self.voiceover(text="再代回去：y 等于五十六减三十二，得到二十四"):
            ans_y = MathTex(r"y = 56 - 32 = 24", font_size=48, color=GIRL_COLOR)
            ans_y.next_to(ans_x, RIGHT, buff=1)
            self.play(Write(ans_y))
            self.play(Circumscribe(VGroup(ans_x, ans_y)))

        # 清屏准备验证
        self.wait(1)
        self.play(FadeOut(group_process), FadeOut(step4), FadeOut(step5), FadeOut(eq1_group), FadeOut(eq2_group), FadeOut(problem_text))

        # --- 镜头9：检验 ---
        check_title = Text("检验:", font_size=36, color=YELLOW).to_corner(UL)
        
        with self.voiceover(text="最后检验一下：三十二加二十四确实等于五十六"):
            self.play(Write(check_title))
            check1 = MathTex(r"32 + 24 = 56", font_size=40).next_to(check_title, RIGHT, buff=0.5)
            check_mark1 = Text("✓", color=GREEN, font_size=32).next_to(check1, RIGHT)
            self.play(Write(check1), FadeIn(check_mark1))

        with self.voiceover(text="剩余人数：男生剩四分之三的三十二是二十四，女生剩三分之二的二十四是十六，加起来正好四十，完全符合题意"):
            check2_boy = MathTex(r"\text{男剩: } 32 \times \frac{3}{4} = 24", color=BOY_COLOR, font_size=36)
            check2_girl = MathTex(r"\text{女剩: } 24 \times \frac{2}{3} = 16", color=GIRL_COLOR, font_size=36)
            check2_sum = MathTex(r"24 + 16 = 40", color=YELLOW, font_size=36)
            
            check_group = VGroup(check2_boy, check2_girl, check2_sum).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
            check_group.next_to(check_title, DOWN, buff=1).align_to(check_title, LEFT)
            
            self.play(FadeIn(check2_boy))
            self.wait(0.5)
            self.play(FadeIn(check2_girl))
            self.wait(0.5)
            self.play(Write(check2_sum))
            
            check_mark2 = Text("✓", color=GREEN, font_size=32).next_to(check2_sum, RIGHT)
            self.play(FadeIn(check_mark2))

        # --- 镜头10：结论 ---
        self.play(FadeOut(check_group), FadeOut(check1), FadeOut(check_mark1), FadeOut(check_mark2), FadeOut(check_title))
        
        with self.voiceover(text="所以原来男生三十二人，女生二十四人。遇到走了一部分还剩多少的题，抓住两个方程就能稳稳解出来"):
            final_ans_box = VGroup(
                Text("答案:", font_size=48),
                Text("男生 32 人", color=BOY_COLOR, font_size=56),
                Text("女生 24 人", color=GIRL_COLOR, font_size=56)
            ).arrange(DOWN, buff=0.5)
            
            final_ans_box.move_to(ORIGIN)
            self.play(DrawBorderThenFill(final_ans_box))
            
            # 底部总结
            summary = Text("方法总结：设未知数 → 总人数方程 → 剩余人数方程", font_size=28, color=GREY_A)
            summary.to_edge(DOWN, buff=0.5)
            self.play(FadeIn(summary))
            
            self.wait(2)
