from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.bytedance import ByteDanceService
import math

# 定义旁白脚本与分镜对齐数据
NARRATION = [
    {
        "id": "S1",
        "text": "现在是两点整。问题是：时针和分针第一次重合，会发生在什么时候？",
        "hint": "Title + Static Clock at 2:00"
    },
    {
        "id": "S2",
        "text": "两点整时，分针在0度的位置，时针在2点，也就是60度。也就是说，时针一开始领先60度。",
        "hint": "Show 60 degree gap"
    },
    {
        "id": "S3",
        "text": "接下来分针会追赶时针。关键是：两针的角度差会以固定的速度不断变小，直到变成零。",
        "hint": "Animation start, gap shrinking"
    },
    {
        "id": "S4",
        "text": "先算速度。分针60分钟转一圈360度，所以每分钟6度；时针12小时也就是720分钟转360度，所以每分钟0.5度。",
        "hint": "Split screen, speeds calculation"
    },
    {
        "id": "S5",
        "text": "设从两点整开始过了t分钟。分针转过的角度是6t；时针从60度出发，再走0.5t。所以时针角度是60加0.5t。两针重合，就是它们角度相等。",
        "hint": "Setup equation"
    },
    {
        "id": "S6",
        "text": "把它们设为相等：6t等于60加0.5t。移项得到5.5t等于60，所以t等于120/11分钟。",
        "hint": "Solve equation"
    },
    {
        "id": "S7",
        "text": "把120/11分钟换算成分秒：它等于10加10/11分钟。再把10/11分钟乘60，得到600/11秒，也就是54又6/11秒，大约54.55秒。",
        "hint": "Unit conversion"
    },
    {
        "id": "S8",
        "text": "回到模拟钟表：当时间来到两点十分钟五十四又六分之十一秒，两针第一次重合，角度差正好变成零。",
        "hint": "Animation freeze at overlap"
    },
    {
        "id": "S9",
        "text": "总结一下：两点整时针领先60度；分针每分钟比时针快5.5度，所以追上所需时间就是60除以5.5，得到120/11分钟，也就是两点十分钟五十四又六分之十一秒。",
        "hint": "Summary"
    }
]

class ClockOverlapProblem(VoiceoverScene):
    def construct(self):
        # 设置语音服务
        self.set_speech_service(ByteDanceService())

        # --- 资源初始化 ---
        # 字体回退机制
        def get_font():
            return "Microsoft YaHei" # Windows/Generic fallback

        font_name = get_font()

        # Helper: 创建带刻度的表盘
        def create_clock_face():
            clock_group = VGroup()
            circle = Circle(radius=2.5, color=WHITE, stroke_width=4)
            clock_group.add(circle)
            
            # 刻度
            for i in range(60):
                angle = 90 - i * 6
                p1 = circle.point_at_angle(angle * DEGREES)
                length = 0.2 if i % 5 == 0 else 0.1
                p2 = p1 * (1 - length / 2.5)
                tick = Line(p1, p2, color=WHITE)
                clock_group.add(tick)
            
            # 数字
            for i in range(1, 13):
                angle = 90 - i * 30
                pos = circle.point_at_angle(angle * DEGREES) * 0.85
                num = Text(str(i), font=font_name, font_size=24).move_to(pos)
                num.rotate(-angle*DEGREES + 90*DEGREES) # Keep upright? No, just move.
                # Actually standard clock numbers are upright. Let's fix position.
                # Re-calculate pos without rotation context for text object itself
                num.move_to(pos)
                clock_group.add(num)
            
            center_dot = Dot(radius=0.08, color=WHITE)
            clock_group.add(center_dot)
            return clock_group

        # Helper: 格式化时间
        def format_time(total_minutes):
            hours = 2 + int(total_minutes // 60)
            mins = int(total_minutes % 60)
            secs = (total_minutes * 60) % 60
            return f"{hours:02d}:{mins:02d}:{secs:05.2f}"

        # --- Scene Elements ---
        clock_face = create_clock_face().shift(LEFT * 3)
        
        # 指针 (Initial at 2:00)
        # Minute hand (long)
        m_hand = Line(ORIGIN, UP * 2.0, color="#2E7DFF", stroke_width=4)
        m_hand.move_to(clock_face[0].get_center(), aligned_edge=DOWN)
        # Hour hand (short), at 2 o'clock (angle -60 deg from UP)
        h_hand = Line(ORIGIN, UP * 1.4, color="#FF6A2E", stroke_width=6)
        h_hand.rotate(-60 * DEGREES, about_point=ORIGIN)
        h_hand.move_to(clock_face[0].get_center() + h_hand.get_vector()/2)
        # Re-center logic: Rotate about center of clock
        # Correct approach:
        m_hand = Line(ORIGIN, UP*1.8, color="#2E7DFF", stroke_width=4).shift(UP*0.9)
        h_hand = Line(ORIGIN, UP*1.2, color="#FF6A2E", stroke_width=6).shift(UP*0.6)
        
        hand_group = VGroup(m_hand, h_hand).move_to(clock_face[0].get_center())
        # Reset to 12:00 position relative to group center, then rotate
        # Actually easier to just rotate logical lines.
        
        # 重新定义指针，确保旋转中心正确
        center_point = clock_face[0].get_center()
        m_hand = Line(center_point, center_point + UP * 1.9, color="#2E7DFF", stroke_width=4)
        h_hand = Line(center_point, center_point + UP * 1.2, color="#FF6A2E", stroke_width=6)
        
        # 初始位置：2:00
        # 分针指向12 (90deg in manim polar)
        # 时针指向2 (30deg in manim polar)
        # Manim angles: 0 is Right, 90 is Up. 
        # Clock 12 -> 90deg, Clock 2 -> 30deg.
        h_hand.rotate(-60 * DEGREES, about_point=center_point)

        clock_group = VGroup(clock_face, m_hand, h_hand)

        # 标题
        title = Text("现在是2点，什么时候时针和分针第一次重合？", font=font_name, font_size=36)
        title.to_edge(UP)

        # 数字时间
        digital_time = Text("02:00:00.00", font="Monospace", font_size=36).next_to(clock_face, UP)

        # 状态变量
        t_val = ValueTracker(0) # Minutes passed since 2:00

        # -----------------------------------------------------------------
        # S1: 片头/题目展示
        # -----------------------------------------------------------------
        with self.voiceover(text=NARRATION[0]["text"]):
            self.play(FadeIn(title), FadeIn(clock_group))
            self.play(FadeIn(digital_time))
            self.wait(1)

        # -----------------------------------------------------------------
        # S2: 建立直觉：谁追谁 (Show 60 deg gap)
        # -----------------------------------------------------------------
        # 弧线表示角度差
        gap_arc = Arc(radius=0.8, start_angle=90*DEGREES, angle=-60*DEGREES, arc_center=center_point, color="#7A4DFF")
        gap_label = MathTex(r"60^\circ").next_to(gap_arc, UR, buff=0.1).scale(0.8)
        gap_label.set_color("#7A4DFF")

        h_text = Text("时针 (60°)", font=font_name, font_size=20, color="#FF6A2E").next_to(h_hand.get_end(), RIGHT, buff=0.2)
        m_text = Text("分针 (0°)", font=font_name, font_size=20, color="#2E7DFF").next_to(m_hand.get_end(), UP, buff=0.2)

        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(Create(gap_arc), Write(gap_label))
            self.play(FadeIn(h_text), FadeIn(m_text))
            self.wait(2)
        
        self.play(FadeOut(h_text), FadeOut(m_text))

        # -----------------------------------------------------------------
        # S3: 动态追及演示
        # -----------------------------------------------------------------
        # 右侧仪表盘与公式
        right_panel = VGroup().arrange(DOWN, buff=0.5).to_edge(RIGHT, buff=1.0)
        gap_title = Text("角度差 Δ(t)", font=font_name, font_size=28)
        gap_formula = MathTex(r"\Delta(t) = 60 - 5.5t", color="#7A4DFF")
        
        # 进度条背景
        bar_bg = Rectangle(width=3, height=0.3, color=GRAY, fill_opacity=0.3)
        bar_fill = Rectangle(width=3, height=0.3, color="#7A4DFF", fill_opacity=1)
        bar_fill.align_to(bar_bg, LEFT)
        bar_group = VGroup(bar_bg, bar_fill).arrange(ORIGIN, buff=0)
        # Re-align
        bar_fill.align_to(bar_bg, LEFT)
        
        right_panel.add(gap_title, gap_formula, bar_group)
        right_panel.shift(UP * 0.5)

        # Updaters
        def update_clock(mob):
            t = t_val.get_value()
            # Minute hand: -6t degrees from 12 o'clock (90 deg)
            # Hour hand: -(60 + 0.5t) degrees from 12 o'clock (90 deg)
            # But h_hand started at -60 deg relative to 12. 
            # So we rotate relative to initial.
            
            # Easier: set angle directly
            # 12 o'clock = 90 degrees
            m_angle = 90 - 6 * t
            h_angle = 90 - (60 + 0.5 * t)
            
            # Set m_hand
            m_hand.put_start_and_end_on(center_point, 
                center_point + np.array([math.cos(m_angle*DEGREES), math.sin(m_angle*DEGREES), 0]) * 1.9)
            # Set h_hand
            h_hand.put_start_and_end_on(center_point, 
                center_point + np.array([math.cos(h_angle*DEGREES), math.sin(h_angle*DEGREES), 0]) * 1.2)

        def update_arc(mob):
            t = t_val.get_value()
            current_gap = 60 - 5.5 * t
            if current_gap < 0: current_gap = 0
            # Start angle is minute hand angle: 90 - 6t
            # Span is -gap (clockwise)
            start_a = (90 - 6 * t) * DEGREES
            angle_a = -current_gap * DEGREES
            
            # Re-generate arc path
            mob.become(Arc(radius=0.8, start_angle=start_a, angle=angle_a, arc_center=center_point, color="#7A4DFF"))

        def update_bar(mob):
            t = t_val.get_value()
            current_gap = 60 - 5.5 * t
            if current_gap < 0: current_gap = 0
            ratio = current_gap / 60.0
            target_width = 3 * ratio
            if target_width < 0.01: target_width = 0.001
            # Create new bar
            new_bar = Rectangle(width=target_width, height=0.3, color="#7A4DFF", fill_opacity=1)
            new_bar.align_to(bar_bg, LEFT)
            mob.become(new_bar)

        def update_digital_time(mob):
            t = t_val.get_value()
            mob.become(Text(format_time(t), font="Monospace", font_size=36).move_to(digital_time.get_center()))

        # Attach updaters
        # Notice: we don't attach to m_hand/h_hand directly to avoid accumulation errors if we used rotate.
        # Instead we use a dummy Mobject or add_updater to scene (or careful Mobject updater).
        # Here we manually update in scene loop or attach to Mobjects.
        
        m_hand.add_updater(lambda m: update_clock(m))
        # h_hand updated by same function effectively if we split logic, but here let's attach to m_hand just once or create a dedicated updater
        # Let's separate logic to be safe
        h_hand.add_updater(lambda m: None) # Passive, updated by the shared logic above inside m_hand updater? No, bad practice.
        
        # Let's do it cleanly:
        m_hand.remove_updater(lambda m: update_clock(m))
        
        # Clean updaters
        m_hand.add_updater(lambda m: m.put_start_and_end_on(center_point, center_point + np.array([math.cos((90 - 6 * t_val.get_value())*DEGREES), math.sin((90 - 6 * t_val.get_value())*DEGREES), 0]) * 1.9))
        h_hand.add_updater(lambda m: m.put_start_and_end_on(center_point, center_point + np.array([math.cos((90 - (60 + 0.5 * t_val.get_value()))*DEGREES), math.sin((90 - (60 + 0.5 * t_val.get_value()))*DEGREES), 0]) * 1.2))
        
        gap_arc.add_updater(update_arc)
        bar_fill.add_updater(update_bar)
        digital_time.add_updater(update_digital_time)
        # Label follows arc? Let's just fade out label for movement
        self.play(FadeOut(gap_label))

        # Animation: Play for 5 minutes of sim time (simulating chase start)
        with self.voiceover(text=NARRATION[2]["text"]):
            self.play(FadeIn(right_panel))
            self.play(t_val.animate.set_value(5), run_time=5, rate_func=linear)

        # -----------------------------------------------------------------
        # S4: 速度来源 (板书1)
        # -----------------------------------------------------------------
        # Shift clock to left to make space for board
        # It is already at LEFT*3.
        
        board_group = VGroup().arrange(DOWN, aligned_edge=LEFT, buff=0.4).to_edge(RIGHT, buff=1.0).shift(UP)
        # Clear previous right panel
        self.play(FadeOut(right_panel))
        
        t1 = Text("分针速度：", font=font_name, font_size=28)
        m1 = MathTex(r"360^\circ / 60\,\text{min} = 6^\circ/\text{min}")
        t2 = Text("时针速度：", font=font_name, font_size=28)
        m2 = MathTex(r"360^\circ / 720\,\text{min} = 0.5^\circ/\text{min}")
        
        # Align text and math
        line1 = VGroup(t1, m1).arrange(RIGHT)
        line2 = VGroup(t2, m2).arrange(RIGHT)
        
        board_group.add(line1, line2)
        board_group.arrange(DOWN, aligned_edge=LEFT, buff=0.6)
        board_group.move_to(RIGHT * 3.5)

        with self.voiceover(text=NARRATION[3]["text"]):
            self.play(Write(line1))
            self.play(Write(line2))
            self.play(Indicate(m1), Indicate(m2))

        # -----------------------------------------------------------------
        # S5: 建立追及方程 (板书2)
        # -----------------------------------------------------------------
        # Move lines up
        self.play(FadeOut(board_group), run_time=0.5)
        
        eq_group = VGroup()
        # Text objects
        txt_setup = Text("设经过 t 分钟", font=font_name, font_size=32, color=YELLOW)
        eq_m = MathTex(r"\theta_m = 6t")
        eq_h = MathTex(r"\theta_h = 60 + 0.5t")
        txt_condition = Text("重合条件：", font=font_name, font_size=28)
        eq_main = MathTex(r"\theta_m = \theta_h")
        
        eq_group.add(txt_setup, eq_m, eq_h, txt_condition, eq_main)
        eq_group.arrange(DOWN, buff=0.4).move_to(RIGHT * 3.5)

        with self.voiceover(text=NARRATION[4]["text"]):
            self.play(Write(txt_setup))
            self.play(FadeIn(eq_m), FadeIn(eq_h))
            self.play(FadeIn(txt_condition), Write(eq_main))

        # -----------------------------------------------------------------
        # S6: 解方程求t (板书3)
        # -----------------------------------------------------------------
        solve_group = VGroup()
        eq1 = MathTex(r"6t = 60 + 0.5t")
        eq2 = MathTex(r"5.5t = 60")
        eq3 = MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \,\text{min}")
        
        solve_group.add(eq1, eq2, eq3).arrange(DOWN, buff=0.5).move_to(RIGHT * 3.5)

        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(ReplacementTransform(eq_group, solve_group[0])) # transform prev equations to first line
            self.play(TransformMatchingTex(solve_group[0].copy(), solve_group[1]))
            self.play(TransformMatchingTex(solve_group[1].copy(), solve_group[2]))
            self.play(Indicate(solve_group[2]))

        # -----------------------------------------------------------------
        # S7: 单位换算 (板书4)
        # -----------------------------------------------------------------
        # We need to keep t=120/11 visible
        self.play(FadeOut(solve_group[0]), FadeOut(solve_group[1]), solve_group[2].animate.to_edge(UP))
        
        calc_group = VGroup()
        # 120/11 = 10 + 10/11
        step1 = MathTex(r"\frac{120}{11} = 10 + \frac{10}{11} \,\text{min}")
        # 10/11 * 60 = 600/11
        step2 = MathTex(r"\frac{10}{11} \times 60 = \frac{600}{11} \,\text{s}")
        # 600/11 = 54 + 6/11
        step3 = MathTex(r"\frac{600}{11} = 54 + \frac{6}{11} \approx 54.55 \,\text{s}")
        
        calc_group.add(step1, step2, step3).arrange(DOWN, buff=0.5).next_to(solve_group[2], DOWN, buff=1.0)

        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(Write(step1))
            self.play(Write(step2))
            self.play(Write(step3))

        # 同时让左侧时钟慢慢逼近
        target_t = 120.0 / 11.0
        # Current t is 5. We need to go to target_t
        # S7 narration is about 15s. 
        # Let's animate clock to near target
        self.play(t_val.animate.set_value(target_t - 0.1), run_time=4)

        # -----------------------------------------------------------------
        # S8: 回到动画：重合瞬间定格
        # -----------------------------------------------------------------
        # Clear board
        self.play(FadeOut(calc_group), FadeOut(solve_group[2]))
        
        # Make clock central again (visually)
        # We can move clock group to center or just focus on it
        # Let's move clock group to center for dramatic effect
        # Be careful with updaters when moving groups with updaters attached to children
        # Safest is to shift the Scene camera or shift elements carefully.
        # Let's just shift elements.
        
        # Center position shift vector
        shift_vec = RIGHT * 3
        
        # We need to update the points the updaters reference (center_point).
        # But center_point is a fixed variable. 
        # If we move the clock_face, the updaters will still draw hands at old center_point.
        # FIX: We need to redefine updaters or move everything including definition of center.
        # EASIER STRATEGY: Don't move clock. Just show large text below it.
        
        final_time_text = Text("02:10:54 6/11", font=font_name, font_size=48, color=YELLOW)
        final_time_approx = Text("(≈ 02:10:54.55)", font=font_name, font_size=36, color=YELLOW)
        final_group = VGroup(final_time_text, final_time_approx).arrange(DOWN).next_to(clock_face, RIGHT, buff=1.5)

        with self.voiceover(text=NARRATION[7]["text"]):
            # Finish the last bit of movement to exact overlap
            self.play(t_val.animate.set_value(target_t), run_time=2, rate_func=ease_out_cubic)
            self.wait(0.5)
            # Gap becomes 0, arc should be gone (updater handles width=0 arc often by making it invisible or dot, let's explicit fade out if needed)
            self.play(FadeOut(gap_arc))
            self.play(Write(final_group))
            self.wait(1.5)

        # -----------------------------------------------------------------
        # S9: 总结
        # -----------------------------------------------------------------
        # Clean up scene for summary card
        summary_bg = RoundedRectangle(corner_radius=0.2, height=4, width=6, color=BLUE, fill_opacity=0.2)
        summary_bg.to_edge(RIGHT)
        
        s_title = Text("要点回顾", font=font_name, font_size=32, weight=BOLD).next_to(summary_bg, UP, direction=DOWN, buff=-0.8)
        s_p1 = Text("1) 初始领先：60°", font=font_name, font_size=24).next_to(s_title, DOWN, aligned_edge=LEFT, buff=0.4)
        s_p2 = Text("2) 追及速度：5.5°/分", font=font_name, font_size=24).next_to(s_p1, DOWN, aligned_edge=LEFT, buff=0.2)
        s_p3 = Text("3) 时间：t = 120/11 分", font=font_name, font_size=24).next_to(s_p2, DOWN, aligned_edge=LEFT, buff=0.2)
        s_ans = Text("答案：2:10:54.55", font=font_name, font_size=28, color=YELLOW).next_to(s_p3, DOWN, aligned_edge=LEFT, buff=0.4)
        
        summary_content = VGroup(s_title, s_p1, s_p2, s_p3, s_ans).move_to(summary_bg.get_center())
        
        with self.voiceover(text=NARRATION[8]["text"]):
            self.play(FadeOut(final_group))
            self.play(FadeIn(summary_bg), Write(summary_content))
            self.wait(2)
        
        # Clean up handlers
        m_hand.clear_updaters()
        h_hand.clear_updaters()
        digital_time.clear_updaters()
        bar_fill.clear_updaters()

        self.wait(2)
