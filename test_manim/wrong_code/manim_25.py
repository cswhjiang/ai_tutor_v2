from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.bytedance import ByteDanceService
import platform

# --- 字体配置 helper ---
def get_cjk_font_by_platform():
    if platform.system() == "Windows":
        return "Microsoft YaHei"
    elif platform.system() == "Darwin":
        return "PingFang SC"
    else:
        return "Noto Sans CJK SC"

cjk_font = get_cjk_font_by_platform()

# --- Manim 场景类 ---
class EngineeringProblemSolverCorrected(VoiceoverScene):
    def construct(self):
        # 1. 设置语音服务
        self.set_speech_service(ByteDanceService())

        # 2. 调用各个分镜函数
        self.scene_01_intro()
        self.scene_02_model_setup()
        self.scene_03_equation_logic()
        self.scene_04_simplification()
        self.scene_05_solve_equation()
        self.scene_06_check_and_summary()

    # --- 辅助函数：清除屏幕除标题外的元素 ---
    def clear_scene(self, exclude_mobjects=None):
        if exclude_mobjects is None:
            exclude_mobjects = []
        
        # 筛选出当前场景中的所有对象
        mobjects_to_remove = [m for m in self.mobjects if m not in exclude_mobjects]
        
        if mobjects_to_remove:
            # 使用 Group 而不是 VGroup，以兼容 ImageMobject
            self.play(FadeOut(Group(*mobjects_to_remove)))

    # --- S01: 开场 + 题目展示 ---
    def scene_01_intro(self):
        # 标题
        title = Text("工程问题：合作与效率", font=cjk_font, font_size=40).to_edge(UP)
        self.play(FadeIn(title))
        self.title_mobj = title # 保存以便后续保留

        # 题目截图 (右侧)
        img_name = "20260213100043_1.png"
        try:
            problem_img = ImageMobject(img_name).scale_to_fit_width(6)
            # 手动布局
            problem_img.to_edge(RIGHT, buff=0.5).shift(DOWN*0.5)
            
            img_label = Text("题目截图", font=cjk_font, font_size=20, color=GRAY)
            img_label.next_to(problem_img, DOWN)
            
            # 使用 Group 来组合 ImageMobject 和 Text
            img_group = Group(problem_img, img_label)
        except:
            # fallback
            problem_img = Rectangle(width=6, height=3, color=BLUE)
            img_label = Text("题目截图(未找到)", font=cjk_font, font_size=20).move_to(problem_img)
            img_group = Group(problem_img, img_label).to_edge(RIGHT, buff=0.5).shift(DOWN*0.5)

        # 题目文本 (左侧)
        # 使用 VGroup 包装 Paragraph 以便布局
        problem_text = Paragraph(
            "甲队单独做：恰好如期完成",
            "乙队单独做：要超过规定日期3天完成",
            "若先甲乙合作2天，再由乙队单独做，",
            "也恰好如期完成。",
            "问：规定日期为几天？",
            font=cjk_font, 
            font_size=24,
            line_spacing=1.0
        ).to_edge(LEFT, buff=0.5).shift(DOWN*0.5)

        with self.voiceover(text="我们先把题目复述一遍：甲队单独做刚好按期完成；乙队单独做会晚三天；如果先甲乙合作两天，再由乙队单独做，也能按期完成。问规定工期是几天？"):
            self.play(Write(problem_text))
            # 修正：使用 FadeIn + shift 代替 SlideIn
            self.play(FadeIn(img_group, shift=LEFT))
            self.wait(0.8)

        self.clear_scene(exclude_mobjects=[title])

    # --- S02: 建立模型 ---
    def scene_02_model_setup(self):
        # 进度条
        bar_bg = Rectangle(width=6.0, height=0.6, stroke_color=WHITE, stroke_width=2).to_edge(LEFT, buff=1.0).shift(UP*1.5)
        bar_label = Text("工程总量 = 1", font=cjk_font, font_size=24, color="#6A5ACD").next_to(bar_bg, UP)
        
        # 变量设定
        setup_text = VGroup(
            Text("设规定日期为", font=cjk_font, font_size=32),
            MathTex(r"x", font_size=36),
            Text("天，工程总量记为", font=cjk_font, font_size=32),
            MathTex(r"1", font_size=36)
        ).arrange(RIGHT).to_edge(RIGHT, buff=1.0).shift(UP*2)

        # 效率卡片
        card_a = VGroup(
            RoundedRectangle(corner_radius=0.2, width=4, height=1.5, fill_color="#2E86FF", fill_opacity=0.2, stroke_color="#2E86FF"),
            VGroup(
                Text("甲队效率", font=cjk_font, font_size=24),
                MathTex(r"a = \frac{1}{x}")
            ).arrange(DOWN)
        )
        
        card_b = VGroup(
            RoundedRectangle(corner_radius=0.2, width=4, height=1.5, fill_color="#FF6B2E", fill_opacity=0.2, stroke_color="#FF6B2E"),
            VGroup(
                Text("乙队效率", font=cjk_font, font_size=24),
                MathTex(r"b = \frac{1}{x+3}")
            ).arrange(DOWN)
        )
        
        # 布局卡片
        card_a.next_to(setup_text, DOWN, buff=1.0).align_to(setup_text, LEFT)
        card_b.next_to(card_a, DOWN, buff=0.5)

        with self.voiceover(text="工程题用“总量等于 1”的模型最方便。设规定工期为 $x$ 天。甲队 $x$ 天完成，所以甲队效率是每天做 1 比 $x$。乙队要比规定多 3 天，也就是 $x+3$ 天完成，所以乙队效率是 1 比 $x+3$。"): 
            self.play(Create(bar_bg), FadeIn(bar_label))
            self.play(Write(setup_text))
            self.wait(0.5)
            # 修正：使用 FadeIn + shift 代替 SlideIn
            self.play(FadeIn(card_a, shift=RIGHT), FadeIn(card_b, shift=LEFT))
            
            # 高亮效率部分
            rect_a = SurroundingRectangle(card_a[1][1], color=YELLOW)
            rect_b = SurroundingRectangle(card_b[1][1], color=YELLOW)
            self.play(Create(rect_a), Create(rect_b))
            self.wait(1)
            self.play(FadeOut(rect_a), FadeOut(rect_b))

        self.clear_scene(exclude_mobjects=[self.title_mobj])

    # --- S03: 建立方程 ---
    def scene_03_equation_logic(self):
        # 时间轴
        axis = NumberLine(x_range=[0, 10, 1], length=10, include_numbers=False)
        axis_label_0 = Text("0", font=cjk_font, font_size=20).next_to(axis.n2p(0), DOWN)
        axis_label_2 = Text("2天(合作)", font=cjk_font, font_size=20).next_to(axis.n2p(2), DOWN)
        axis_label_x = Text("x天(规定日期)", font=cjk_font, font_size=20).next_to(axis.n2p(8), DOWN) 
        
        timeline = VGroup(axis, axis_label_0, axis_label_2, axis_label_x).to_edge(UP, buff=1.5)
        dot_2 = Dot(axis.n2p(2), color=RED)
        dot_x = Dot(axis.n2p(8), color=RED)

        # 进度条分段
        bar_full = Rectangle(width=10, height=0.8, stroke_color=WHITE).next_to(timeline, DOWN, buff=1)
        
        # 第一段: 0-2 
        bar_part1 = Rectangle(width=2, height=0.8, fill_color="#6A5ACD", fill_opacity=0.5, stroke_width=0).align_to(bar_full, LEFT).align_to(bar_full, UP)
        label_part1 = MathTex(r"2(a+b)", font_size=30).move_to(bar_part1)
        
        # 第二段: 2-x 
        bar_part2 = Rectangle(width=6, height=0.8, fill_color="#FF6B2E", fill_opacity=0.5, stroke_width=0).next_to(bar_part1, RIGHT, buff=0)
        label_part2 = MathTex(r"(x-2)b", font_size=30).move_to(bar_part2)
        
        # 方程
        eq = MathTex(r"2(a+b) + (x-2)b = 1", font_size=48).next_to(bar_full, DOWN, buff=1)

        with self.voiceover(text="把“先合作两天，再乙队单独做”翻译成工作量。合作两天完成 2倍的a加b。剩下还有 $x-2$ 天由乙队做，完成 $x-2$ 乘 $b$。两段加起来等于总量 1，所以方程是：<break time='300ms'/> $2(a+b) + (x-2)b = 1$。"): 
            self.play(Create(axis), Write(axis_label_0), Write(axis_label_x))
            self.play(Create(dot_2), Write(axis_label_2))
            
            self.play(Create(bar_full))
            self.play(FadeIn(bar_part1), Write(label_part1))
            self.play(FadeIn(bar_part2), Write(label_part2))
            
            self.play(Indicate(eq), Write(eq))
            self.wait(1)

        self.clear_scene(exclude_mobjects=[self.title_mobj])

    # --- S04: 代入化简 ---
    def scene_04_simplification(self):
        # 步骤 1
        step1 = MathTex(r"2\left(\frac{1}{x}+\frac{1}{x+3}\right) + (x-2)\frac{1}{x+3} = 1", font_size=42)
        # 步骤 2
        step2 = MathTex(r"\frac{2}{x} + \frac{2 + (x-2)}{x+3} = 1", font_size=42)
        # 步骤 3
        step3 = MathTex(r"\frac{2}{x} + \frac{x}{x+3} = 1", font_size=42)
        
        # 布局
        group = VGroup(step1, step2, step3).arrange(DOWN, buff=0.8, aligned_edge=LEFT).move_to(ORIGIN)

        # 提示
        hint = Text("关键：2+(x-2)=x", font=cjk_font, font_size=24, color=YELLOW).to_edge(RIGHT, buff=1.0).align_to(step2, UP)

        with self.voiceover(text="把 $a$ 和 $b$ 代入：$a$ 等于 1 比 $x$，$b$ 等于 1 比 $x+3$。化简时关键是把同分母 $x+3$ 的部分合并，分子出现 2 加 $x-2$，正好等于 $x$，于是得到关键方程：<break time='300ms'/> 2 比 $x$ 加 $x$ 比 $x+3$ 等于 1。"): 
            self.play(Write(step1))
            self.wait(1)
            
            self.play(TransformMatchingTex(step1.copy(), step2))
            self.play(FadeIn(hint, shift=LEFT))
            self.wait(0.5)
            
            self.play(TransformMatchingTex(step2.copy(), step3))
            
            # 高亮最后结果
            box = SurroundingRectangle(step3, color=YELLOW)
            self.play(Create(box))
            self.wait(1)

        self.clear_scene(exclude_mobjects=[self.title_mobj, step3])
        self.last_eq = step3 

    # --- S05: 解方程 ---
    def scene_05_solve_equation(self):
        # 上一幕留下来的方程
        current_eq = self.last_eq
        target_pos = UP * 2.5
        
        self.play(current_eq.animate.move_to(target_pos))

        # 推导步骤
        eq1 = MathTex(r"\frac{2}{x} = 1 - \frac{x}{x+3}", font_size=42)
        eq2 = MathTex(r"\frac{2}{x} = \frac{3}{x+3}", font_size=42)
        eq3 = MathTex(r"2(x+3) = 3x", font_size=42)
        eq4 = MathTex(r"x = 6", font_size=56, color=YELLOW)
        
        steps = VGroup(eq1, eq2, eq3, eq4).arrange(DOWN, buff=0.6).next_to(current_eq, DOWN, buff=0.8)

        # 答案框
        ans_box = VGroup(
            RoundedRectangle(corner_radius=0.2, width=4, height=1.2, fill_color="#6A5ACD", fill_opacity=1, stroke_color=WHITE),
            Text("规定日期：6 天", font=cjk_font, font_size=32, color=WHITE)
        ).move_to(DOWN * 2.5)

        with self.voiceover(text="解这个方程：先移项得到 2 比 $x$ 等于 1 减 $x$ 比 $x+3$，通分后右边等于 3 比 $x+3$。交叉相乘得到 2 倍的 $x+3$ 等于 $3x$，解得 $x=6$，所以规定日期是 6 天。"): 
            self.play(Transform(current_eq.copy(), eq1))
            self.wait(0.5)
            
            self.play(Transform(eq1, eq2))
            self.wait(0.5)
            
            self.play(Transform(eq2, eq3))
            self.wait(0.5)
            
            self.play(Transform(eq3, eq4))
            self.play(eq4.animate.scale(1.2))
            self.wait(0.5)
            
            self.play(FadeIn(ans_box, shift=UP))
            self.wait(1)

        self.clear_scene(exclude_mobjects=[self.title_mobj])

    # --- S06: 检验与总结 ---
    def scene_06_check_and_summary(self):
        # 左侧表格
        table_vals = [
            ["x=6", ""],
            ["甲: 1/6", "乙: 1/9"],
            ["合作2天", "2(1/6+1/9)=5/9"],
            ["剩余4天乙做", "4·(1/9)=4/9"],
            ["合计", "1 (完成)"]
        ]
        
        rows = VGroup()
        for i, val in enumerate(table_vals):
            t1 = Text(val[0], font=cjk_font, font_size=24)
            t2 = Text(val[1], font=cjk_font, font_size=24)
            row = VGroup(t1, t2).arrange(RIGHT, buff=0.5)
            if i == 4: row.set_color(GREEN)
            rows.add(row)
            
        rows.arrange(DOWN, buff=0.5, aligned_edge=LEFT).to_edge(LEFT, buff=1.0)

        # 右侧总结
        bullets = VGroup(
            Text("• 工程总量设为 1", font=cjk_font, font_size=26),
            Text("• 效率 = 1 / 用时", font=cjk_font, font_size=26),
            Text("• 分段工作量相加 = 1", font=cjk_font, font_size=26),
            Text("• 解得 x = 6 天", font=cjk_font, font_size=26, color=YELLOW)
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT).to_edge(RIGHT, buff=1.5).shift(UP*0.5)

        with self.voiceover(text="最后检验：$x=6$ 时，合作两天完成 9 分之 5，剩余四天乙队完成 9 分之 4，合起来正好是 1，完全符合题意。总结一下：工程题常用总量设 1、效率等于 1 除以用时、再按分段工作量相加等于 1 来列方程。本题规定日期是 6 天。"): 
            self.play(LaggedStart(*[FadeIn(row, shift=RIGHT*0.2) for row in rows], lag_ratio=0.5))
            
            # 指向合计
            self.play(Indicate(rows[-1]))
            
            self.play(LaggedStart(*[FadeIn(line, shift=LEFT*0.2) for line in bullets], lag_ratio=0.5))
            
            self.wait(2)

# manim -pqh your_file.py EngineeringProblemSolverCorrected
