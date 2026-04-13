from sys import platform

from manim import *
import numpy as np

from manim.utils.tex import TexTemplate


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

CJK = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
txt = r'''
\usepackage{fontspec}
\usepackage{xeCJK}
'''
txt += r"\setCJKmainfont{" + cjk_font + "}\n"
CJK.add_to_preamble(txt)


class ClockChaseScene(Scene):
    def construct(self):
        # ---------------------------------------------------------
        # 0. Asset Preparation: The Clock
        # ---------------------------------------------------------
        # Create a clock face group
        clock_radius = 2.2
        clock_group = VGroup()
        clock_circle = Circle(radius=clock_radius, color=WHITE, stroke_width=4)
        clock_center = Dot(color=WHITE)
        
        ticks = VGroup()
        labels = VGroup()
        # Create ticks and numbers
        for i in range(12):
            # Angle: 12 is at 90 deg, moving CW by 30 deg per hour
            angle = -i * 30 * DEGREES + 90 * DEGREES
            
            # Ticks
            p1 = clock_circle.point_at_angle(angle)
            p2 = clock_circle.get_center() + (p1 - clock_circle.get_center()) * 0.9
            tick = Line(p1, p2, color=WHITE)
            ticks.add(tick)
            
            # Numbers
            num_pos = clock_circle.get_center() + (p1 - clock_circle.get_center()) * 0.78
            num_val = 12 if i == 0 else i
            label = Text(str(num_val), font_size=24).move_to(num_pos)
            labels.add(label)
            
        clock_group.add(clock_circle, ticks, labels, clock_center)
        clock_group.move_to(ORIGIN)

        # Define Hand Lengths
        h_hand_len = clock_radius * 0.5
        m_hand_len = clock_radius * 0.8

        # Create Hands (Lines)
        # Initial positions: Hour UP, Minute UP (will rotate later)
        hour_hand = Line(ORIGIN, UP * h_hand_len, color=BLUE, stroke_width=6)
        minute_hand = Line(ORIGIN, UP * m_hand_len, color=RED, stroke_width=4)
        hour_hand.set_z_index(10)
        minute_hand.set_z_index(10)
        
        # Add hands to group (indices: 0=circle, 1=ticks, 2=labels, 3=center, 4=hour, 5=minute)
        clock_group.add(hour_hand, minute_hand)

        # ---------------------------------------------------------
        # S1: Hook & Introduction
        # ---------------------------------------------------------
        title = Text("2点过后，分针第一次追上时针是什么时候？", font_size=32).to_edge(UP)
        self.play(Write(title))
        self.play(FadeIn(clock_group))
        
        # Set Clock to 2:00:00
        # Hour hand rotates 60 degrees CW (from 12)
        # Minute hand stays at 0 degrees (at 12)
        # Using Rotate about center
        self.play(
            Rotate(hour_hand, angle=-60*DEGREES, about_point=clock_group.get_center()),
            run_time=1.5
        )
        self.wait(0.5)

        start_label = Text("起点：2:00:00", font_size=24, color=YELLOW).next_to(clock_group, DOWN)
        self.play(Write(start_label))
        self.wait(1.5)
        self.play(FadeOut(start_label))

        # ---------------------------------------------------------
        # S2: Establish Coordinate System
        # ---------------------------------------------------------
        # Move clock to left to make space for formulas
        self.play(clock_group.animate.shift(LEFT * 3.5))
        
        # Add angle markers
        # 0 deg at 12 o'clock
        marker_0 = Text("0°", font_size=20, color=RED).next_to(clock_group.get_top(), UP, buff=0.1)
        
        # 60 deg at 2 o'clock
        # Position calculation: center + (radius+0.4) * angle_vector
        # 2 o'clock is 30 deg in standard math (90-60)
        pos_2 = clock_group.get_center() + (clock_radius + 0.6) * np.array([np.cos(30*DEGREES), np.sin(30*DEGREES), 0])
        marker_60 = Text("60°", font_size=20, color=BLUE).move_to(pos_2)
        
        self.play(FadeIn(marker_0), FadeIn(marker_60))

        # Visualise Gap (Arc)
        gap_arc = Arc(
            radius=1.2,
            start_angle=90*DEGREES,
            angle=-60*DEGREES,
            color=YELLOW,
            arc_center=clock_group.get_center()
        )
        gap_text = Text("相差 60°", font_size=20, color=YELLOW).move_to(
            clock_group.get_center() + 1.8 * np.array([np.cos(60*DEGREES), np.sin(60*DEGREES), 0])
        )
        
        self.play(Create(gap_arc), Write(gap_text))
        self.wait(1)

        # Info Panel on the Right
        info_start_y = 2.5
        info_x = 2.5
        
        t_init = VGroup(
            Text("初始状态 (t=0):", font_size=26, color=YELLOW),
            VGroup(Text("分针角度: ", font_size=24), MathTex(r"\theta_m(0) = 0^\circ", color=RED)).arrange(RIGHT),
            VGroup(Text("时针角度: ", font_size=24), MathTex(r"\theta_h(0) = 60^\circ", color=BLUE)).arrange(RIGHT)
        ).arrange(DOWN, aligned_edge=LEFT).move_to(RIGHT * info_x + UP * info_start_y)
        
        self.play(Write(t_init))
        self.wait(2)

        # ---------------------------------------------------------
        # S3: Speeds & S4: Equations
        # ---------------------------------------------------------
        self.play(FadeOut(gap_arc), FadeOut(gap_text))

        t_speed = VGroup(
            Text("角速度：", font_size=26, color=YELLOW),
            MathTex(r"\omega_m = 6^\circ / \text{min}", color=RED),
            MathTex(r"\omega_h = 0.5^\circ / \text{min}", color=BLUE)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(t_init, DOWN, buff=0.5, aligned_edge=LEFT)

        self.play(Write(t_speed))
        self.wait(1)

        t_eq = VGroup(
            Text("t 分钟后的角度：", font_size=26, color=YELLOW),
            MathTex(r"\theta_m(t) = 6t", color=RED),
            MathTex(r"\theta_h(t) = 60 + 0.5t", color=BLUE)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(t_speed, DOWN, buff=0.5, aligned_edge=LEFT)

        self.play(Write(t_eq))
        self.wait(2)

        # ---------------------------------------------------------
        # S5 & S6: Solving for t
        # ---------------------------------------------------------
        # Clear previous text to make room for calculation
        self.play(FadeOut(t_init), FadeOut(t_speed), FadeOut(t_eq))

        solve_group = VGroup()
        # Step 1: Condition
        s1 = VGroup(Text("重合条件：", font_size=28), MathTex(r"\theta_m(t) = \theta_h(t)")).arrange(RIGHT)
        # Step 2: Equation
        s2 = MathTex(r"6t = 60 + 0.5t")
        # Step 3: Simplify
        s3 = MathTex(r"5.5t = 60")
        # Step 4: Solve
        s4 = MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \, \text{min}")
        # Step 5: Convert
        s5 = VGroup(Text("换算为时间：", font_size=28), MathTex(r"10\text{分} + \frac{10}{11}\text{分}", tex_template=CJK)).arrange(RIGHT)
        s6 = Text("= 10分 54.55秒", font_size=28, color=GREEN)

        solve_group.add(s1, s2, s3, s4, s5, s6)
        solve_group.arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        solve_group.move_to(RIGHT * 2 + UP * 0.5)

        for item in solve_group:
            self.play(FadeIn(item, shift=UP*0.2), run_time=0.8)
            self.wait(0.5)
        
        self.wait(2)

        # ---------------------------------------------------------
        # S7: The Chase Animation
        # ---------------------------------------------------------
        self.play(
            FadeOut(solve_group), 
            FadeOut(marker_0), 
            FadeOut(marker_60),
            FadeOut(title)
        )

        # Re-center and scale up clock
        self.play(
            clock_group.animate.move_to(ORIGIN).scale(1.2),
            run_time=1.5
        )

        # HUD Elements
        hud_bg = RoundedRectangle(corner_radius=0.2, width=5, height=2.2, color=GRAY, fill_opacity=0.2)
        hud_bg.to_corner(UR)
        
        hud_time_label = Text("当前时间:", font_size=24).move_to(hud_bg.get_top() + DOWN*0.6 + LEFT*1.2)
        hud_time_val = Text("02:00:00.00", font_size=24, font="Monospace", color=YELLOW).next_to(hud_time_label, RIGHT)
        
        hud_diff_label = Text("两针夹角:", font_size=24).next_to(hud_time_label, DOWN, buff=0.4, aligned_edge=LEFT)
        hud_diff_val = DecimalNumber(60.00, num_decimal_places=2, unit="^\circ").next_to(hud_diff_label, RIGHT)
        
        hud_group = VGroup(hud_bg, hud_time_label, hud_time_val, hud_diff_label, hud_diff_val)
        self.play(FadeIn(hud_group))

        # Animation Logic
        target_t = 120/11 # minutes
        animation_duration = 10 # seconds for the chase
        t_tracker = ValueTracker(0)

        # Access hands from group (indices might change if not careful, but add order is preserved)
        # hour_hand is clock_group[4], minute_hand is clock_group[5]
        h_hand_obj = clock_group[4]
        m_hand_obj = clock_group[5]
        
        # Define dynamic update functions
        def update_hour_hand(mob):
            t = t_tracker.get_value()
            # Angle in degrees CW from 12 o'clock
            angle_cw = 60 + 0.5 * t
            # Convert to math angle: 90 - angle_cw
            math_angle = (90 - angle_cw) * DEGREES
            
            c = clock_group.get_center()
            # Current scaled length
            length = h_hand_len * 1.2 # Scaled by 1.2
            
            end_point = c + length * np.array([np.cos(math_angle), np.sin(math_angle), 0])
            mob.put_start_and_end_on(c, end_point)

        def update_minute_hand(mob):
            t = t_tracker.get_value()
            angle_cw = 6 * t
            math_angle = (90 - angle_cw) * DEGREES
            
            c = clock_group.get_center()
            length = m_hand_len * 1.2
            end_point = c + length * np.array([np.cos(math_angle), np.sin(math_angle), 0])
            mob.put_start_and_end_on(c, end_point)

        def update_hud_time(mob):
            t = t_tracker.get_value()
            total_sec = t * 60
            mins = int(total_sec // 60)
            secs = int(total_sec % 60)
            # hundredths of second
            hunds = int((total_sec - int(total_sec)) * 100)
            new_text = f"02:{mins:02d}:{secs:02d}.{hunds:02d}"
            mob.become(Text(new_text, font_size=24, font="Monospace", color=YELLOW).move_to(mob.get_center()))

        def update_hud_diff(mob):
            t = t_tracker.get_value()
            theta_m = 6 * t
            theta_h = 60 + 0.5 * t
            diff = max(0, theta_h - theta_m) # Avoid negative just in case
            mob.set_value(diff)

        # Attach updaters
        h_hand_obj.add_updater(update_hour_hand)
        m_hand_obj.add_updater(update_minute_hand)
        hud_time_val.add_updater(update_hud_time)
        hud_diff_val.add_updater(update_hud_diff)

        # Run Animation
        self.play(
            t_tracker.animate.set_value(target_t),
            run_time=animation_duration,
            rate_func=linear
        )

        # ---------------------------------------------------------
        # S8: Freeze & Verification
        # ---------------------------------------------------------
        # Remove updaters to freeze state
        h_hand_obj.remove_updater(update_hour_hand)
        m_hand_obj.remove_updater(update_minute_hand)
        hud_time_val.remove_updater(update_hud_time)
        hud_diff_val.remove_updater(update_hud_diff)
        
        self.wait(1)

        # Flash overlap point
        overlap_angle_cw = 65.4545
        overlap_math_angle = (90 - overlap_angle_cw) * DEGREES
        tip_pos = clock_group.get_center() + (m_hand_len * 1.2) * np.array([np.cos(overlap_math_angle), np.sin(overlap_math_angle), 0])
        
        self.play(Flash(tip_pos, color=YELLOW, flash_radius=0.5))
        
        # Show verification box
        verify_box = VGroup(
            Text("最终验证", font_size=24, color=YELLOW),
            MathTex(r"\theta_m = 6 \times \frac{120}{11} \approx 65.45^\circ"),
            MathTex(r"\theta_h = 60 + 0.5 \times \frac{120}{11} \approx 65.45^\circ")
        ).arrange(DOWN, aligned_edge=LEFT).to_corner(DR).shift(LEFT*0.5 + UP*0.5)
        
        # Add background to box
        verify_bg = BackgroundRectangle(verify_box, color=BLACK, fill_opacity=0.8, buff=0.2)
        
        self.play(FadeIn(verify_bg), Write(verify_box))
        self.wait(3)

        # ---------------------------------------------------------
        # S9: Summary
        # ---------------------------------------------------------
        self.play(
            FadeOut(verify_bg), FadeOut(verify_box),
            FadeOut(hud_group),
            clock_group.animate.scale(0.7).to_edge(LEFT)
        )

        summary = VGroup(
            Text("总结", font_size=36, color=YELLOW, weight=BOLD),
            Text("1. 分针比时针每分钟快 5.5°", font_size=28),
            Text("2. 追平 60° 差距需 120/11 分钟", font_size=28),
            Text("3. 答案：2点10分54.55秒", font_size=32, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).next_to(clock_group, RIGHT, buff=1.5)

        self.play(Write(summary))
        self.wait(4)

# manim -pqh your_filename.py ClockChaseScene

# agent 1 视频生成失败Expecting ',' delimiter: line 2 column 9007 (char 9008)