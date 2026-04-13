from manim import *
from manim_voiceover import VoiceoverScene
# from manim_voiceover.services.gtts import GTTSService
# from manim_voiceover.services.openai import OpenAIService
from manim_voiceover.services.bytedance import ByteDanceService

from sys import platform

def get_cjk_font_by_platform():
    print("Detected platform:", platform)
    if platform.startswith("win"):
        default_font = "Microsoft YaHei"
    elif platform.startswith("darwin"):  # macOS
        default_font = "PingFang SC"
    else:  # Linux / WSL / Docker (默认)
        default_font = "Noto Sans CJK SC"
    
    return default_font


cjk_font = get_cjk_font_by_platform()
# 解决中文编译问题
CJK = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
txt = r'''
\usepackage{fontspec}
\usepackage{xeCJK}
'''
txt += r"\setCJKmainfont{" + cjk_font + "}\n"
CJK.add_to_preamble(txt)

# 设置全局字体
config.font = cjk_font
# 设置全局字体
# config.font = "SimHei"  # Windows下常用黑体，Mac/Linux可改为 "Noto Sans SC"

# tts
# tts_server = GTTSService(lang="zh-CN")
voice = 'ash'
model = 'gpt-4o-mini-tts-2025-12-15'

# tts_server = OpenAIService(voice=voice, model=model, transcription_model=None)

class PeopleCountProblem(VoiceoverScene):
    def construct(self):
        # 1. 初始化语音服务 (中文)
        # self.set_speech_service(tts_server)
        self.set_speech_service(ByteDanceService())
        
        # 2. 调用各个分镜场景
        self.show_intro()
        self.setup_variables()
        self.show_first_equation()
        self.show_fraction_bars()
        self.solve_equations()
        self.show_result()
        self.verify_answer()
        self.show_code_verification()
        self.show_summary()

    # --- S1: 标题与题目 ---
    def show_intro(self):
        # 标题
        title = Text("走了多少人？用方程组秒解", font_size=48, color=YELLOW)
        title.to_edge(UP, buff=0.8)
        
        # 题目文本
        problem_text = MarkupText(
            "一班有<span fgcolor='#FFFF00'>56</span>人，\n"
            "女生走了<span fgcolor='#EB5757'>1/3</span>，男生走了<span fgcolor='#2F80ED'>1/4</span>。\n"
            "还剩<span fgcolor='#00FF00'>40</span>人，男女生各有多少人？",
            font_size=32, line_spacing=1.5
        )
        problem_text.next_to(title, DOWN, buff=1)

        with self.voiceover(text="这是一道典型的人数变化题：男生、女生各走了一部分，最后剩下40人。"):
            self.play(DrawBorderThenFill(title))
            self.play(FadeIn(problem_text))
        
        with self.voiceover(text="我们今天用方程组，把文字信息翻译成数学。"):
            self.play(Indicate(problem_text))
            self.wait(1)

        self.problem_text_obj = problem_text # 保存引用以便后续淡出
        self.title_obj = title

    # --- S2: 设未知数 ---
    def setup_variables(self):
        self.play(FadeOut(self.problem_text_obj))
        
        # 男生女生图标示意（用简单的圆和颜色代表）
        boy_group = VGroup(Dot(color=BLUE, radius=0.2), Text("男生", color=BLUE).scale(0.8)).arrange(RIGHT)
        girl_group = VGroup(Dot(color=RED, radius=0.2), Text("女生", color=RED).scale(0.8)).arrange(RIGHT)
        
        icons = VGroup(boy_group, girl_group).arrange(RIGHT, buff=2)
        icons.move_to(UP * 1.5)
        
        setup_text = MathTex(r"\text{设男生 } x \text{ 人，女生 } y \text{ 人}", color=WHITE, tex_template=CJK)
        setup_text.next_to(icons, DOWN, buff=0.5)

        with self.voiceover(text="因为题目里只有两类人，男生和女生，所以直接设男生是x人，女生是y人。"):
            self.play(FadeIn(icons))
            self.play(Write(setup_text))
        
        self.variables = setup_text
        self.icons = icons

    # --- S3: 第一个方程 ---
    def show_first_equation(self):
        eq1 = MathTex(r"x + y = 56", font_size=60)
        eq1.move_to(ORIGIN)
        
        label = Text("全班总人数", font_size=24, color=GRAY).next_to(eq1, DOWN)

        with self.voiceover(text="全班一共56人，就是男生加女生，所以第一个方程是x加y等于56。"):
            self.play(Write(eq1))
            self.play(FadeIn(label))
            self.wait(0.5)

        # 将方程1移到左上角备用
        self.eq1_group = VGroup(eq1, label)
        self.play(
            self.eq1_group.animate.scale(0.7).to_corner(UL, buff=1),
            FadeOut(self.variables), 
            FadeOut(self.icons)
        )
        self.eq1_ref = eq1 # 保存单纯的公式引用

    # --- S4: 剩下的人（可视化条形图） ---
    def show_fraction_bars(self):
        # 男生条形图
        boy_bar = Rectangle(width=4, height=0.6, color=BLUE, fill_opacity=0.5)
        boy_label = MathTex("x", color=BLUE).next_to(boy_bar, LEFT)
        
        # 将男生条分为4份
        boy_parts = VGroup(*[
            Rectangle(width=1, height=0.6, color=WHITE, stroke_width=1).move_to(boy_bar.get_left() + RIGHT * (0.5 + i))
            for i in range(4)
        ])
        
        boy_group = VGroup(boy_label, boy_bar, boy_parts).move_to(UP * 0.5 + LEFT * 2)

        # 女生条形图
        girl_bar = Rectangle(width=3, height=0.6, color=RED, fill_opacity=0.5)
        girl_label = MathTex("y", color=RED).next_to(girl_bar, LEFT)
        
        # 将女生条分为3份
        girl_parts = VGroup(*[
            Rectangle(width=1, height=0.6, color=WHITE, stroke_width=1).move_to(girl_bar.get_left() + RIGHT * (0.5 + i))
            for i in range(3)
        ])
        
        girl_group = VGroup(girl_label, girl_bar, girl_parts).move_to(DOWN * 1.5 + LEFT * 2.5)

        with self.voiceover(text="注意，走的是原来人数的分数。"):
            self.play(Create(boy_group), Create(girl_group))

        # 动画：切掉部分
        boy_removed = boy_parts[3] # 最后一份
        girl_removed = girl_parts[2] # 最后一份
        
        boy_remain_brace = Brace(boy_parts[0:3], UP)
        boy_remain_text = MathTex(r"\frac{3}{4}x").next_to(boy_remain_brace, UP)
        
        girl_remain_brace = Brace(girl_parts[0:2], UP)
        girl_remain_text = MathTex(r"\frac{2}{3}y").next_to(girl_remain_brace, UP)

        with self.voiceover(text="男生走了四分之一，剩下就是四分之三x"):
            self.play(
                boy_removed.animate.set_fill(BLACK, opacity=0.8).set_stroke(),
                FadeIn(boy_remain_brace), Write(boy_remain_text)
            )

        with self.voiceover(text="女生走了三分之一，剩下就是三分之二y"):
            self.play(
                girl_removed.animate.set_fill(BLACK, opacity=0.8).set_stroke(),
                FadeIn(girl_remain_brace), Write(girl_remain_text)
            )

        # 生成方程2
        eq2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=50)
        eq2.to_edge(RIGHT, buff=2)

        with self.voiceover(text="这两部分加起来等于40人，于是第二个方程是：四分之三x，加上三分之二y，等于40。"):
            self.play(TransformFromCopy(VGroup(boy_remain_text, girl_remain_text), eq2))
        
        self.wait(1)
        self.play(FadeOut(boy_group), FadeOut(girl_group), FadeOut(boy_remain_brace), 
                 FadeOut(boy_remain_text), FadeOut(girl_remain_brace), FadeOut(girl_remain_text))
        
        self.eq2_ref = eq2 # 保存引用

    # --- S5: 消元求解 ---
    def solve_equations(self):
        # 整理布局
        self.play(self.eq2_ref.animate.scale(0.9).next_to(self.eq1_group, DOWN, buff=0.5, aligned_edge=LEFT))
        
        # 步骤1: 变形
        step1 = MathTex(r"x = 56 - y", color=YELLOW).scale(0.8)
        step1.next_to(self.eq1_ref, RIGHT, buff=1)
        
        with self.voiceover(text="用消元法最方便。从第一个方程得到：x等于56减y。"):
            self.play(Indicate(self.eq1_ref))
            self.play(Write(step1))

        # 步骤2: 代入
        step2 = MathTex(r"\frac{3}{4}(56 - y) + \frac{2}{3}y = 40").scale(0.8)
        step2.move_to(ORIGIN)
        
        with self.voiceover(text="把它代入第二个方程，也就是把x换成56减y。"):
            self.play(Write(step2))

        # 步骤3: 展开
        step3 = MathTex(r"42 - \frac{3}{4}y + \frac{2}{3}y = 40").scale(0.8)
        step3.next_to(step2, DOWN, buff=0.4)
        
        with self.voiceover(text="接着一步步化简。四分之三乘以56等于42。"):
            self.play(TransformFromCopy(step2, step3))

        # 步骤4: 通分合并
        step4 = MathTex(r"42 + (-\frac{9}{12} + \frac{8}{12})y = 40").scale(0.8)
        step4.next_to(step3, DOWN, buff=0.4)
        
        with self.voiceover(text="再把y的系数通分到12。四分之三是十二分之九，三分之二是十二分之八。"):
            self.play(Write(step4))

        step5 = MathTex(r"42 - \frac{1}{12}y = 40").scale(0.8)
        step5.move_to(step4) # 原地替换

        with self.voiceover(text="合并后得到：42减去十二分之一y等于40。"):
            self.play(ReplacementTransform(step4, step5))

        # 步骤5: 解出y
        step6 = MathTex(r"-\frac{1}{12}y = -2 \quad \Rightarrow \quad y = 24", color=GREEN).scale(1)
        step6.next_to(step5, DOWN, buff=0.5)

        with self.voiceover(text="移项计算，最后算出y等于24。"):
            self.play(Write(step6))
            self.play(Indicate(step6))

        self.y_val = step6
        # 清理中间步骤，保留结果
        self.play(FadeOut(step2), FadeOut(step3), FadeOut(step5))
        self.play(self.y_val.animate.move_to(UP))

    # --- S6: 回代求x ---
    def show_result(self):
        x_calc = MathTex(r"x = 56 - 24 = 32", color=BLUE).scale(1)
        x_calc.next_to(self.y_val, DOWN, buff=0.5)

        with self.voiceover(text="把y等于24代回这一步，就得到x等于56减24，也就是32。"):
            self.play(Write(x_calc))
        
        final_box = SurroundingRectangle(VGroup(self.y_val, x_calc), color=YELLOW, buff=0.3)
        result_text = Text("答案: 男生32人，女生24人", font_size=36).next_to(final_box, DOWN)

        with self.voiceover(text="所以原来男生有32人，女生有24人。"):
            self.play(Create(final_box), FadeIn(result_text))
            self.wait(1)
        
        self.play(FadeOut(VGroup(self.y_val, x_calc, final_box, result_text, self.eq1_group, self.eq2_ref)))

    # --- S7: 检验 ---
    def verify_answer(self):
        title = Text("检验一下", font_size=40).to_edge(UP)
        self.play(Write(title))

        # 左右两列
        boy_check = Text("男生", color=BLUE).move_to(LEFT * 3 + UP)
        girl_check = Text("女生", color=RED).move_to(RIGHT * 3 + UP)

        b_line1 = Text("走 1/4: 32 × 1/4 = 8", font_size=28).next_to(boy_check, DOWN)
        b_line2 = Text("剩: 32 - 8 = 24", font_size=28).next_to(b_line1, DOWN)

        g_line1 = Text("走 1/3: 24 × 1/3 = 8", font_size=28).next_to(girl_check, DOWN)
        g_line2 = Text("剩: 24 - 8 = 16", font_size=28).next_to(g_line1, DOWN)

        total_check = MathTex(r"24 + 16 = 40 \quad \checkmark", color=GREEN, font_size=60)
        total_check.move_to(DOWN * 2)

        with self.voiceover(text="我们检验一下：男生走四分之一是8人，剩24人。"):
            self.play(FadeIn(boy_check), Write(b_line1))
            self.play(Write(b_line2))

        with self.voiceover(text="女生走三分之一也是8人，剩16人。"):
            self.play(FadeIn(girl_check), Write(g_line1))
            self.play(Write(g_line2))

        with self.voiceover(text="合起来24加16等于40，和题目完全一致，答案正确。"):
            self.play(Write(total_check))
            self.wait(1)

        self.play(FadeOut(VGroup(title, boy_check, girl_check, b_line1, b_line2, g_line1, g_line2, total_check)))

    # --- S8: 代码验证 ---
    def show_code_verification(self):
        # 模拟代码编辑器界面
        code_bg = Rectangle(width=10, height=6, color=DARK_GRAY, fill_opacity=0.9)
        header = Rectangle(width=10, height=0.5, color=BLACK, fill_opacity=1).align_to(code_bg, UP)
        buttons = VGroup(*[Dot(radius=0.1, color=c) for c in [RED, YELLOW, GREEN]]).arrange(RIGHT).move_to(header.get_left() + RIGHT*0.5)
        
        window = VGroup(code_bg, header, buttons)
        
        code_str = """
import sympy as sp
x, y = sp.symbols('x y')
eq1 = sp.Eq(x + y, 56)
eq2 = sp.Eq(3/4*x + 2/3*y, 40)
sol = sp.solve([eq1, eq2], [x, y])
print(sol)
        """
        code_text = Code(code_string=code_str, tab_width=4, background="window", language="python")
        # code_text.code.scale(0.8) # code只是类型声明，没法获取
        code_text.move_to(code_bg)
        
        output_text = Text("{x: 32.0, y: 24.0}", font="Monospace", font_size=32, color=GREEN)
        output_text.next_to(code_text, DOWN, buff=0.2)
        
        with self.voiceover(text="如果用Python代码验证也很简单，把两个方程交给计算机求解。"):
            self.play(FadeIn(window), FadeIn(code_text))
            self.wait(1)
        
        with self.voiceover(text="运行一下，结果也是x等于32，y等于24。"):
            self.play(Write(output_text))
            self.play(Indicate(output_text, color=YELLOW))
            self.wait(1)

        self.play(FadeOut(window), FadeOut(code_text), FadeOut(output_text))

    # --- S9: 结尾总结 ---
    def show_summary(self):
        title = Text("解题三步法", color=YELLOW, font_size=48).to_edge(UP)
        
        steps = VGroup(
            Text("1. 设未知数 (x, y)", font_size=36),
            Text("2. 列方程组 (总数, 剩余)", font_size=36),
            Text("3. 消元求解 + 检验", font_size=36)
        ).arrange(DOWN, buff=0.8).move_to(ORIGIN)
        
        for step in steps:
            step.align_to(steps[0], LEFT)

        with self.voiceover(text="最后总结一下这类题的三步走："):
            self.play(Write(title))
        
        with self.voiceover(text="第一步，设未知数。"):
            self.play(FadeIn(steps[0]))
            
        with self.voiceover(text="第二步，根据总数和剩余比例列出方程组。"):
            self.play(FadeIn(steps[1]))
            
        with self.voiceover(text="第三步，消元求解，并记得检验答案。"):
            self.play(FadeIn(steps[2]))
            self.wait(2)
