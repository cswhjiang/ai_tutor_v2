from manim import *
import numpy as np

# ----------------------------------------------------------------------------
#  NARRATION SCRIPT (For TTS / RenderAgent)
# ----------------------------------------------------------------------------
NARRATION = [
    {
        "id": "Shot 1",
        "text": "2点刚过，分针在12，时针在2。它们第一次重合，到底是2点10分多，还是2点11分？我们用一个追及问题，算出精确到分数秒的答案。",
        "hint": "展示钟面，时间快速流逝"
    },
    {
        "id": "Shot 2",
        "text": "把钟面看成360度的圆。2点整时，分针在0度，时针在2点位置，也就是60度，所以初始差距就是60度——这就是追及距离。",
        "hint": "标记初始角度差60度"
    },
    {
        "id": "Shot 3",
        "text": "分针每分钟走6度，因为一小时360度；时针每分钟走0.5度，因为12小时走360度。两根针同向运动，典型追及问题。",
        "hint": "显示角速度数值"
    },
    {
        "id": "Shot 4",
        "text": "追及问题只看相对速度。分针相对时针每分钟多追5.5度，也就是每分钟把差距缩小5.5度。",
        "hint": "计算相对速度 6 - 0.5 = 5.5"
    },
    {
        "id": "Shot 5",
        "text": "重合就是分针追上时针，追上这60度差距所需时间：t等于60除以5.5。",
        "hint": "列出公式 t = 距离/速度"
    },
    {
        "id": "Shot 6",
        "text": "5.5等于二分之十一，所以60除以二分之十一，等于十一分之一百二十分钟，大约10.909分钟——直觉上也合理：比10分钟长一点。",
        "hint": "化简分数到 120/11"
    },
    {
        "id": "Shot 7",
        "text": "把120/11分钟拆成10分钟加11分之10分钟。11分之10分钟乘60，得到11分之600秒，也就是54又11分之6秒。所以第一次重合在2点10分54又11分之6秒，约等于2点10分55秒。",
        "hint": "单位换算演示"
    },
    {
        "id": "Shot 8",
        "text": "我们把钟拨到2点10分54点5秒左右，你会看到两根针在同一条射线上——这就是追及模型的直接验证。",
        "hint": "钟面动画验证重合"
    },
    {
        "id": "Shot 9",
        "text": "你可能见过“2点10分11分之10秒”这种写法，但那是不对的。正确的单位是“11分之10分钟”，换成钟表时间就是2点10分54又11分之6秒。",
        "hint": "纠正单位错误"
    },
    {
        "id": "Shot 10",
        "text": "一句话总结：距离60度，速度差5.5度每分钟，时间就是60除以5.5。答案：2点10分54又11分之6秒，约2点10分55秒。",
        "hint": "总结页"
    }
]

class ClockChaseProblem(Scene):
    def construct(self):
        # --------------------------------------------------------------------
        # Helper: Create Clock Mobject
        # --------------------------------------------------------------------
        def create_clock():
            circle = Circle(radius=3, color=WHITE)
            ticks = VGroup()
            numbers = VGroup()
            
            for i in range(12):
                angle = -i * 30 * DEGREES + 90 * DEGREES
                # Hour ticks
                start = circle.get_center() + np.array([np.cos(angle), np.sin(angle), 0]) * 2.7
                end = circle.get_center() + np.array([np.cos(angle), np.sin(angle), 0]) * 3.0
                tick = Line(start, end, color=WHITE, stroke_width=4)
                ticks.add(tick)
                
                # Numbers
                num_pos = circle.get_center() + np.array([np.cos(angle), np.sin(angle), 0]) * 2.3
                num_str = str(i) if i != 0 else "12"
                num = Text(num_str, font_size=24).move_to(num_pos)
                numbers.add(num)
            
            center_dot = Dot(radius=0.1, color=RED)
            clock_group = VGroup(circle, ticks, numbers, center_dot)
            return clock_group

        # --------------------------------------------------------------------
        # Shot 1: 开场钩子 (Intro)
        # --------------------------------------------------------------------
        # Visual: Clock at 2:00, fast forward
        title = Text("2点后时针分针何时第一次重合？", font_size=36).to_edge(UP)
        self.play(Write(title))

        clock = create_clock()
        clock.shift(DOWN * 0.5)
        
        # Define Hands
        minute_hand = Line(ORIGIN, UP * 2.0, color=BLUE, stroke_width=4)
        hour_hand = Line(ORIGIN, UP * 1.3, color=YELLOW, stroke_width=6)
        
        # Initial Position: 2:00
        # Minute at 12 (0 deg deviation), Hour at 2 (-60 deg deviation)
        minute_hand.rotate(0, about_point=ORIGIN)
        hour_hand.rotate(-60 * DEGREES, about_point=ORIGIN)
        
        hands = VGroup(hour_hand, minute_hand).move_to(clock[3].get_center())
        # Note: move_to aligns center, but we want pivot at ORIGIN relative to clock center
        # Let's group correctly: Hands pivot is their start, move start to clock center
        minute_hand.put_start_and_end_on(clock[3].get_center(), clock[3].get_center() + UP*2.0)
        hour_hand.put_start_and_end_on(clock[3].get_center(), clock[3].get_center() + rotate_vector(UP*1.3, -60*DEGREES))

        self.play(FadeIn(clock), FadeIn(hands))
        self.wait(1)

        # Animation: Fast forward slightly to show movement
        # Rotate hands for visual effect (not precise yet)
        self.play(
            Rotate(minute_hand, angle=-70*DEGREES, about_point=clock[3].get_center()),
            Rotate(hour_hand, angle=(-70/12)*DEGREES, about_point=clock[3].get_center()),
            run_time=3, rate_func=linear
        )
        self.wait(1)
        self.play(FadeOut(clock), FadeOut(hands), FadeOut(title))

        # --------------------------------------------------------------------
        # Shot 2: 建立模型 (Model Setup)
        # --------------------------------------------------------------------
        # Visual: Simplified Circle, Angles 0 and 60
        
        # Re-create simplified view
        simple_circle = Circle(radius=2.5, color=GREY)
        center = simple_circle.get_center()
        
        line_12 = Line(center, center + UP*2.5, color=GREY_B)
        line_2 = Line(center, center + rotate_vector(UP*2.5, -60*DEGREES), color=GREY_B)
        
        lbl_0 = MathTex(r"0^\circ").next_to(line_12.get_end(), UP)
        lbl_60 = MathTex(r"60^\circ").next_to(line_2.get_end(), RIGHT)
        
        arc_gap = Arc(radius=0.8, start_angle=90*DEGREES, angle=-60*DEGREES, color=RED)
        lbl_gap = MathTex(r"\Delta \theta_0 = 60^\circ", color=RED).move_to(center + UR*1.0)
        
        model_group = VGroup(simple_circle, line_12, line_2, lbl_0, lbl_60, arc_gap, lbl_gap)
        model_group.shift(LEFT * 2)
        
        text_model = Text("追及距离", font_size=32, color=RED).next_to(lbl_gap, UP)
        
        self.play(Create(simple_circle))
        self.play(Create(line_12), Write(lbl_0))
        self.play(Create(line_2), Write(lbl_60))
        self.play(Create(arc_gap), Write(lbl_gap))
        self.play(Write(text_model))
        self.wait(2)
        
        # Clean up for next shot
        self.play(FadeOut(model_group), FadeOut(text_model))

        # --------------------------------------------------------------------
        # Shot 3 & 4: 角速度与相对速度 (Velocities)
        # --------------------------------------------------------------------
        # Visual: Text Comparison
        
        v_title = Text("角速度对比", font_size=40).to_edge(UP)
        
        # Left side: Minute Hand
        t_min = Text("分针", font_size=32, color=BLUE)
        eq_min = MathTex(r"\omega_m = 6^\circ / \text{min}", color=BLUE)
        g_min = VGroup(t_min, eq_min).arrange(DOWN)
        
        # Right side: Hour Hand
        t_hr = Text("时针", font_size=32, color=YELLOW)
        eq_hr = MathTex(r"\omega_h = 0.5^\circ / \text{min}", color=YELLOW)
        g_hr = VGroup(t_hr, eq_hr).arrange(DOWN)
        
        comparison = VGroup(g_min, g_hr).arrange(RIGHT, buff=2)
        
        self.play(Write(v_title))
        self.play(FadeIn(comparison))
        self.wait(1)
        
        # Relative Speed Calculation
        arrow_down = Arrow(UP, DOWN, color=WHITE).next_to(comparison, DOWN)
        rel_text = Text("相对角速度 (追及速度)", font_size=32).next_to(arrow_down, DOWN)
        
        rel_math = MathTex(
            r"\omega_{rel} = ", r"6", r"-", r"0.5", r"=", r"5.5^\circ / \text{min}"
        ).scale(1.5).next_to(rel_text, DOWN)
        
        # Highlight 5.5
        rect = SurroundingRectangle(rel_math[-1], color=GREEN)
        
        self.play(GrowArrow(arrow_down), Write(rel_text))
        self.play(Write(rel_math))
        self.play(Create(rect))
        self.wait(2)
        
        self.play(FadeOut(v_title), FadeOut(comparison), FadeOut(arrow_down), FadeOut(rel_text), FadeOut(rel_math), FadeOut(rect))

        # --------------------------------------------------------------------
        # Shot 5 & 6: 公式求解 (Formula & Calc)
        # --------------------------------------------------------------------
        # Visual: Equation solving
        
        step_title = Text("计算追及时间", font_size=36).to_edge(UP)
        self.play(Write(step_title))
        
        # Line 1: Formula
        eq1 = MathTex(r"t", r"=", r"\frac{\text{距离}}{\text{速度}}", r"=", r"\frac{60}{5.5}")
        eq1.shift(UP * 1.5)
        
        # Line 2: Fraction simplification
        eq2 = MathTex(r"=", r"\frac{60}{11/2}", r"=", r"\frac{120}{11}", r"\text{ min}")
        eq2.next_to(eq1, DOWN, aligned_edge=LEFT)
        # align equals
        # Manual adjustment to align the first '=' of eq2 with second '=' of eq1
        eq2.next_to(eq1[3], DOWN)
        eq2.align_to(eq1[3], LEFT)
        
        # Line 3: Decimal approx
        eq3 = MathTex(r"\approx", r"10.909...", r"\text{ min}")
        eq3.next_to(eq2, DOWN, aligned_edge=LEFT)
        
        self.play(Write(eq1[0:3])) # t = dist/speed
        self.wait(1)
        self.play(Write(eq1[3:])) # = 60/5.5
        self.wait(1)
        self.play(Write(eq2))
        self.wait(1)
        self.play(Write(eq3))
        self.wait(2)
        
        self.play(FadeOut(step_title), FadeOut(eq1), FadeOut(eq2), FadeOut(eq3))

        # --------------------------------------------------------------------
        # Shot 7: 单位换算 (Unit Conversion)
        # --------------------------------------------------------------------
        # Visual: Breakdown 120/11
        
        conv_title = Text("精确时间计算", font_size=36).to_edge(UP)
        self.play(FadeIn(conv_title))
        
        # Step A: Split
        tex_split = MathTex(r"\frac{120}{11} \text{ min} = ", r"10 \text{ min}", r" + ", r"\frac{10}{11} \text{ min}")
        tex_split.shift(UP * 1)
        
        # Step B: Convert Fraction part
        tex_sec = MathTex(r"\frac{10}{11} \text{ min} \times 60 = ", r"\frac{600}{11} \text{ s}")
        tex_sec.next_to(tex_split, DOWN, buff=0.5)
        
        # Step C: Mixed Number
        tex_mixed = MathTex(r"\frac{600}{11} \text{ s} = ", r"54 \frac{6}{11} \text{ s}")
        tex_mixed.next_to(tex_sec, DOWN, buff=0.5)
        
        # Final Result Box
        final_res = VGroup(
            Text("最终时间点：", font_size=28),
            MathTex(r"2:10:54\frac{6}{11}", color=YELLOW, font_size=48),
            Text("(约 2:10:55)", font_size=24, color=GREY)
        ).arrange(RIGHT, buff=0.2)
        final_res.next_to(tex_mixed, DOWN, buff=1.0)
        box = SurroundingRectangle(final_res, color=YELLOW)
        
        self.play(Write(tex_split))
        self.wait(1)
        self.play(Write(tex_sec))
        self.wait(1)
        self.play(Write(tex_mixed))
        self.wait(1)
        self.play(FadeIn(final_res), Create(box))
        self.wait(3)
        
        self.play(FadeOut(conv_title), FadeOut(tex_split), FadeOut(tex_sec), FadeOut(tex_mixed), FadeOut(final_res), FadeOut(box))

        # --------------------------------------------------------------------
        # Shot 8: 动画验证 (Animation Verification)
        # --------------------------------------------------------------------
        # Visual: Precise Clock Simulation
        
        # Setup Clock again
        clock_v = create_clock()
        clock_v.to_edge(LEFT, buff=1)
        
        center_point = clock_v[3].get_center()
        
        # Hands using ValueTracker
        # t in minutes past 2:00
        t_tracker = ValueTracker(0)
        
        # Angles from UP (12 o'clock)
        # Minute: -6 * t
        # Hour: -60 - 0.5 * t
        
        def get_minute_vector():
            t = t_tracker.get_value()
            angle = (90 - 6 * t) * DEGREES
            return np.array([np.cos(angle), np.sin(angle), 0]) * 2.0

        def get_hour_vector():
            t = t_tracker.get_value()
            angle = (90 - (60 + 0.5 * t)) * DEGREES
            return np.array([np.cos(angle), np.sin(angle), 0]) * 1.3

        m_hand_v = Line(center_point, center_point + UP*2.0, color=BLUE, stroke_width=4)
        h_hand_v = Line(center_point, center_point + rotate_vector(UP*1.3, -60*DEGREES), color=YELLOW, stroke_width=6)
        
        m_hand_v.add_updater(lambda m: m.put_start_and_end_on(center_point, center_point + get_minute_vector()))
        h_hand_v.add_updater(lambda m: m.put_start_and_end_on(center_point, center_point + get_hour_vector()))
        
        # Info Panel on Right
        info_panel = VGroup(
            Text("时间 t (min):", font_size=24),
            DecimalNumber(0, num_decimal_places=2).scale(0.8),
            Text("分针角度:", font_size=24),
            DecimalNumber(0, num_decimal_places=1, unit="^\circ").scale(0.8),
            Text("时针角度:", font_size=24),
            DecimalNumber(60, num_decimal_places=1, unit="^\circ").scale(0.8)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(clock_v, RIGHT, buff=2)
        
        # Updaters for numbers
        info_panel[1].add_updater(lambda d: d.set_value(t_tracker.get_value()))
        info_panel[3].add_updater(lambda d: d.set_value(6 * t_tracker.get_value()))
        info_panel[5].add_updater(lambda d: d.set_value(60 + 0.5 * t_tracker.get_value()))
        
        target_time = 120/11 # approx 10.90909
        
        self.play(FadeIn(clock_v), FadeIn(m_hand_v), FadeIn(h_hand_v), FadeIn(info_panel))
        
        # Animate to overlap
        self.play(t_tracker.animate.set_value(target_time), run_time=4, rate_func=linear)
        
        # Highlight overlap
        flash_circle = Circle(color=WHITE, radius=2.2).move_to(center_point)
        self.play(ShowPassingFlash(flash_circle))
        
        ver_text = Text("验证成功：角度相等", color=GREEN, font_size=32).next_to(clock_v, DOWN)
        self.play(Write(ver_text))
        self.wait(2)
        
        # Cleanup updaters to prevent memory leak issues or errors on fadeout
        m_hand_v.clear_updaters()
        h_hand_v.clear_updaters()
        info_panel[1].clear_updaters()
        info_panel[3].clear_updaters()
        info_panel[5].clear_updaters()
        
        self.play(FadeOut(clock_v), FadeOut(m_hand_v), FadeOut(h_hand_v), FadeOut(info_panel), FadeOut(ver_text))

        # --------------------------------------------------------------------
        # Shot 9: 温和纠错 (Common Mistake)
        # --------------------------------------------------------------------
        mistake_title = Text("常见的单位误区", font_size=36, color=RED).to_edge(UP)
        
        # Wrong
        wrong_group = VGroup(
            Text("错误写法：", color=RED, font_size=28),
            MathTex(r"2:10:\frac{10}{11}", color=RED),
            Text("(把10/11分钟当成了秒)", font_size=20, color=GREY)
        ).arrange(RIGHT)
        
        # Right
        right_group = VGroup(
            Text("正确写法：", color=GREEN, font_size=28),
            MathTex(r"2:10:54\frac{6}{11}", color=GREEN),
            Text("(10/11分钟 = 54.54...秒)", font_size=20, color=GREY)
        ).arrange(RIGHT)
        
        comparison_mistake = VGroup(wrong_group, right_group).arrange(DOWN, buff=1.0)
        
        cross = Cross(wrong_group, color=RED)
        check = Text("✔", color=GREEN, font_size=48).next_to(right_group, RIGHT)
        
        self.play(Write(mistake_title))
        self.play(FadeIn(comparison_mistake))
        self.wait(1)
        self.play(Create(cross))
        self.play(Write(check))
        self.wait(2)
        
        self.play(FadeOut(mistake_title), FadeOut(comparison_mistake), FadeOut(cross), FadeOut(check))

        # --------------------------------------------------------------------
        # Shot 10: 总结 (Summary)
        # --------------------------------------------------------------------
        summary_title = Text("一句话总结", font_size=40).to_edge(UP)
        
        lines = VGroup(
            Text("1. 初始距离：60度"),
            Text("2. 追及速度：5.5度/分"),
            VGroup(Text("3. 公式："), MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \text{ min}")).arrange(RIGHT),
            VGroup(Text("4. 答案："), MathTex(r"2:10:54\frac{6}{11}")).arrange(RIGHT)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        
        self.play(Write(summary_title))
        for line in lines:
            self.play(FadeIn(line, shift=UP*0.2))
            self.wait(0.5)
        
        self.wait(3)
        self.play(FadeOut(summary_title), FadeOut(lines))

# To render:
# manim -pqh your_filename.py ClockChaseProblem
