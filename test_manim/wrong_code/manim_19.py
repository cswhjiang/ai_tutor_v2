from manim import *
from manim_voiceover import VoiceoverScene
from bytedance import ByteDanceService
# from bytedance_modified import ByteDanceService

# --- Narration Data ---
# Providing a fallback for narration in case voiceover service fails or for reference.
NARRATION = [
    {
        "id": "S1_hook",
        "text": "2点整开始，分针在12，时针在2。问题是：它们第一次重合，究竟是2点10分整，还是更晚？",
        "hint": "Show 2:00 clock"
    },
    {
        "id": "S2_intuition",
        "text": "直觉上分针会追上时针，但关键在于：时针并不是静止的，它也在慢慢往前走。",
        "hint": "Fast forward clock"
    },
    {
        "id": "S3_define_angles",
        "text": "建立模型：从2点整开始过了t分钟。2点位置是60度，所以初始角度差delta theta 0等于60度。分针每分钟转6度，时针每分钟转0.5度。",
        "hint": "Show variables"
    },
    {
        "id": "S4_relative_speed_equation",
        "text": "因为两根针都在动，用相对角速度最省事：分针相对时针每分钟追近6减0.5，也就是5.5度。重合就是把60度的差距追到0，所以有方程5.5t等于60。",
        "hint": "Derive equation"
    },
    {
        "id": "S5_solve_and_convert",
        "text": "解出来t等于60除以5.5，也就是11分之120分钟。它等于10又11分之10分钟，而11分之10分钟换算成秒是约54.55秒。所以第一次重合时间是2点10分54.55秒。",
        "hint": "Solve t"
    },
    {
        "id": "S6_clock_slowmo_meet",
        "text": "看动画就更直观了：到了2点10分，分针还没追上，因为时针已经往前挪了一点点。直到2点10分54.55秒，才第一次重合。",
        "hint": "Slow motion check"
    },
    {
        "id": "S7_quick_check",
        "text": "最后做个一致性校验：分针转到11分之720度，时针是原来的60度再走11分之60度，也正好是11分之720度。两针角度相同，结果正确。",
        "hint": "Verification"
    }
]

class ClockScene(VoiceoverScene):
    def construct(self):
        # --- Setup Voiceover ---
        self.set_speech_service(ByteDanceService())

        # --- Assets Construction ---
        # Clock Face Group
        clock_radius = 2.2
        clock_group = VGroup()
        circle = Circle(radius=clock_radius, color=WHITE)
        clock_group.add(circle)
        
        # Ticks
        ticks = VGroup()
        for i in range(12):
            angle = i * PI / 6
            start = circle.get_center() + np.array([np.sin(angle), np.cos(angle), 0]) * (clock_radius - 0.2)
            end = circle.get_center() + np.array([np.sin(angle), np.cos(angle), 0]) * clock_radius
            line = Line(start, end, color=WHITE)
            ticks.add(line)
            
            # Numbers
            num_angle = (i if i != 0 else 12) * PI / 6
            # Manim angles start from Right (0), go CCW. Clock starts Up, goes CW.
            # 12 is at 90 deg (PI/2), 3 is at 0, 6 is at -90, 9 is at 180.
            # Position for number `val`: 90 - (val * 30)
            val = i if i != 0 else 12
            pos_angle = (90 - val * 30) * DEGREES
            num_pos = circle.get_center() + np.array([np.cos(pos_angle), np.sin(pos_angle), 0]) * (clock_radius - 0.5)
            num = Text(str(val), font_size=24).move_to(num_pos)
            ticks.add(num)
        clock_group.add(ticks)
        
        # Hands
        # Hour hand length
        h_len = clock_radius * 0.5
        m_len = clock_radius * 0.8
        
        hour_hand = Line(ORIGIN, UP * h_len, color=BLUE, stroke_width=6)
        minute_hand = Line(ORIGIN, UP * m_len, color=RED, stroke_width=4)
        center_dot = Dot(color=WHITE)
        
        hands_group = VGroup(hour_hand, minute_hand, center_dot)
        clock_full = VGroup(clock_group, hands_group).move_to(LEFT * 3)

        # Helper to set time
        def set_clock_time(h, m, s):
            # Total minutes from 12:00
            total_min = h * 60 + m + s / 60
            # Hour hand: 0.5 deg per min
            h_angle = -0.5 * total_min * DEGREES
            # Minute hand: 6 deg per min
            m_angle = -6 * total_min * DEGREES
            
            hour_hand.set_angle(h_angle + 90*DEGREES) # +90 because Manim 0 is Right
            minute_hand.set_angle(m_angle + 90*DEGREES)

        # Initial State: 2:00:00
        set_clock_time(2, 0, 0)
        
        # Digital Time Display
        time_label = Text("2:00:00", font="Monospace", font_size=36).next_to(clock_full, DOWN)
        
        # Title
        title = Text("2点后，时针和分针第一次重合在什么时候？", font_size=36)
        title.to_edge(UP)

        # --- S1_hook ---
        # Shot: Close up on clock, question appears
        self.add(title, clock_full, time_label)
        
        # Visual: Arc for 60 degrees
        # 2:00 -> Hour at 2 (30*2=60 deg from 12), Min at 12 (0 deg)
        # Arc from 90 deg to 30 deg (in Manim coords)
        arc_60 = Arc(radius=1.0, start_angle=90*DEGREES, angle=-60*DEGREES, color=YELLOW)
        arc_label = Text("60°", color=YELLOW, font_size=24).next_to(arc_60.point_from_proportion(0.5), UR, buff=0.1)
        
        with self.voiceover(text=NARRATION[0]['text']) as tracker:
            self.play(Create(arc_60), Write(arc_label))
            self.wait(1)

        # --- S2_intuition ---
        # Shot: Fast animation
        # Animate from 2:00:00 to 2:10:00 roughly to show chasing
        
        speed_label = Text("分针更快：在“追”时针", font_size=24, color=RED).next_to(clock_full, UP, buff=0.2)
        moving_label = Text("时针也在走！", font_size=24, color=BLUE).next_to(hour_hand.get_end(), RIGHT, buff=0.1)

        # ValueTracker for time animation
        # Let t go from 0 to 10.9 (just before overlap)
        # Overlap is at ~10.909 min
        t_tracker = ValueTracker(0)
        
        def update_clock(mob):
            t = t_tracker.get_value()
            # time string
            total_sec = t * 60
            m = int(total_sec // 60)
            s = int(total_sec % 60)
            ms = int((total_sec - int(total_sec)) * 100)
            mob.text = f"2:{m:02d}:{s:02d}.{ms:02d}"
            # hands
            set_clock_time(2, 0, total_sec)

        time_label.add_updater(update_clock)
        moving_label.add_updater(lambda m: m.next_to(hour_hand.get_end(), RIGHT, buff=0.1))

        with self.voiceover(text=NARRATION[1]['text']) as tracker:
            self.play(FadeIn(speed_label), FadeOut(arc_60), FadeOut(arc_label))
            self.play(FadeIn(moving_label))
            # Fast forward to ~10 mins
            self.play(t_tracker.animate.set_value(10.0), run_time=tracker.duration * 0.7, rate_func=linear)
            self.wait(0.5)

        time_label.remove_updater(update_clock)
        moving_label.remove_updater(lambda m: m.next_to(hour_hand.get_end(), RIGHT, buff=0.1))
        self.play(FadeOut(speed_label), FadeOut(moving_label))

        # Reset clock for derivation logic presentation
        # Move clock to right side to make space for formula
        self.play(
            clock_full.animate.scale(0.8).to_edge(RIGHT),
            time_label.animate.next_to(clock_full, DOWN).shift(RIGHT*2 + DOWN*0.5).scale(0.8),
            FadeOut(time_label) # Hide time label during formula, bring back later
        )
        
        # Reset hands to 2:00 visually for static definition
        set_clock_time(2, 0, 0)
        # Redraw arc
        arc_60 = Arc(radius=0.8, start_angle=90*DEGREES, angle=-60*DEGREES, color=YELLOW).move_to(clock_full[0].get_center() + UR*0.3)
        # A bit hacky positioning for the arc relative to the moved clock
        # Re-calculate arc position based on clock center
        c_center = clock_full[0].get_center()
        arc_60 = Arc(arc_center=c_center, radius=0.8, start_angle=90*DEGREES, angle=-60*DEGREES, color=YELLOW)
        arc_label = Text("60°", color=YELLOW, font_size=24).next_to(arc_60.point_from_proportion(0.5), UR, buff=0.1)
        
        self.play(Create(arc_60), Write(arc_label))

        # --- S3_define_angles ---
        # Formula section on LEFT
        step1_group = VGroup(
            Text("设从2:00起经过 t 分钟", font_size=28),
            MathTex(r"\Delta \theta_0 = 60^\circ", color=YELLOW),
            MathTex(r"\omega_m = 6^\circ / \min", color=RED),
            MathTex(r"\omega_h = 0.5^\circ / \min", color=BLUE)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(LEFT).shift(UP)

        with self.voiceover(text=NARRATION[2]['text']) as tracker:
            self.play(Write(step1_group[0]))
            self.play(Write(step1_group[1]))
            self.play(Write(step1_group[2]), Write(step1_group[3]))
            self.play(Indicate(step1_group[1]))

        # --- S4_relative_speed_equation ---
        step2_group = VGroup(
            VGroup(Text("相对角速度：", font_size=28), MathTex(r"\omega_{rel} = 6 - 0.5 = 5.5^\circ/\min")).arrange(RIGHT),
            VGroup(Text("重合条件：", font_size=28), MathTex(r"\omega_{rel} \cdot t = \Delta \theta_0")).arrange(RIGHT),
            MathTex(r"5.5 t = 60", color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(step1_group, DOWN, buff=0.5).align_to(step1_group, LEFT)

        with self.voiceover(text=NARRATION[3]['text']) as tracker:
            self.play(Write(step2_group[0]))
            self.play(Write(step2_group[1]))
            self.play(TransformMatchingTex(step2_group[1].copy(), step2_group[2]))
            self.wait(1)

        # --- S5_solve_and_convert ---
        # Clear previous formulas to make space for calculation
        self.play(FadeOut(step1_group), FadeOut(step2_group[0]), FadeOut(step2_group[1]), 
                  step2_group[2].animate.to_edge(TOP).shift(LEFT))
        
        calc_eq = step2_group[2]
        
        solve_steps = VGroup(
            MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \, \text{min}"),
            MathTex(r"\frac{120}{11} = 10 + \frac{10}{11} \, \text{min}"),
            VGroup(Text("秒数：", font_size=28), MathTex(r"\frac{10}{11} \times 60 = \frac{600}{11} \approx 54.55 \, \text{s}")).arrange(RIGHT),
            Text("第一次重合时间：", font_size=32, color=YELLOW),
            Text("2:10:54.55", font_size=40, color=YELLOW, weight=BOLD)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(calc_eq, DOWN, buff=0.4).align_to(calc_eq, LEFT)

        with self.voiceover(text=NARRATION[4]['text']) as tracker:
            self.play(Write(solve_steps[0]))
            self.wait(0.5)
            self.play(Write(solve_steps[1]))
            self.wait(0.5)
            self.play(Write(solve_steps[2]))
            self.wait(0.5)
            self.play(Write(solve_steps[3]), Write(solve_steps[4]))
            self.play(Indicate(solve_steps[4]))

        # --- S6_clock_slowmo_meet ---
        # Bring back clock focus
        # Visual: Clock time jumps to 2:10:40 then slows down
        
        # Remove formula, center clock
        self.play(FadeOut(solve_steps), FadeOut(calc_eq), FadeOut(arc_60), FadeOut(arc_label))
        
        # Time label back
        time_label.next_to(clock_full, DOWN).scale(1.25) # Reset scale
        time_label.text = "2:10:40.00"
        self.play(clock_full.animate.scale(1.25).move_to(ORIGIN), FadeIn(time_label))
        
        # Update hands to 2:10:40
        # 10 min 40 sec = 10 + 40/60 = 10.666 min
        t_start = 10 + 40/60
        set_clock_time(2, 0, t_start * 60)

        # Target time: 120/11 min = 10.90909... min
        t_target = 120/11
        
        t_tracker.set_value(t_start)
        time_label.add_updater(update_clock)

        with self.voiceover(text=NARRATION[5]['text']) as tracker:
            # Slow motion animation to target
            self.play(t_tracker.animate.set_value(t_target), run_time=6, rate_func=linear)
            
            # Highlight overlap
            flash = Circle(radius=0.3, color=YELLOW).move_to(hour_hand.get_end())
            self.play(ShowPassingFlash(flash))
        
        time_label.remove_updater(update_clock)
        
        # --- S7_quick_check ---
        # Move clock left, show verification on right
        self.play(clock_full.animate.to_edge(LEFT), time_label.animate.next_to(clock_full, DOWN).shift(LEFT*2))
        
        verify_group = VGroup(
            Text("校验：", font_size=32),
            VGroup(Text("分针角度：", font_size=24), MathTex(r"6 \times \frac{120}{11} = \frac{720}{11}^\circ")).arrange(RIGHT),
            VGroup(Text("时针角度：", font_size=24), MathTex(r"60 + 0.5 \times \frac{120}{11} = \frac{720}{11}^\circ")).arrange(RIGHT),
            Text("结论一致 ✅", font_size=32, color=GREEN)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT).shift(LEFT*1)

        with self.voiceover(text=NARRATION[6]['text']) as tracker:
            self.play(Write(verify_group[0]))
            self.play(Write(verify_group[1]))
            self.play(Write(verify_group[2]))
            self.play(Indicate(verify_group[1][1]), Indicate(verify_group[2][1]))
            self.play(Write(verify_group[3]))
        
        self.wait(2)
