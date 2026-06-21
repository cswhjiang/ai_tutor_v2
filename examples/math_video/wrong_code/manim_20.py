from manim import *
from manim_voiceover import VoiceoverScene
from bytedance import ByteDanceService


class MathExplanation(VoiceoverScene):
    def construct(self):
        # --- Configuration ---
        self.set_speech_service(ByteDanceService())

        # --- Helper Functions ---
        def get_safe_text(content, font_size=36, color=WHITE):
            return Text(content, font_size=font_size, color=color, font="Sans")

        # print('cache_dir', self.speech_service.cache_dir)
        # --- Step 1: Opening & Problem Description ---
        # Narration: "甲乙两人从两地同时出发相对而行，4小时后相遇，并且相遇点离中点4千米。甲更快，问甲每小时比乙快多少千米？"
        with self.voiceover(
                text="甲乙两人从两地同时出发相对而行，4小时后相遇，并且相遇点离中点4千米。甲更快，问甲每小时比乙快多少千米？"):
            title = get_safe_text("奥数相遇题：中点偏移模型", font_size=48).to_edge(UP)

            info_group = VGroup(
                get_safe_text("甲乙相对而行", font_size=32),
                get_safe_text("4小时相遇", font_size=32),
                get_safe_text("相遇点距中点4km", font_size=32),
                get_safe_text("求：甲每小时比乙快多少？", font_size=36, color=YELLOW)
            ).arrange(DOWN, buff=0.5).next_to(title, DOWN, buff=1.0)

            self.play(Write(title))
            self.play(FadeIn(info_group, shift=UP))
            self.wait(1)

        self.play(FadeOut(info_group))

        # --- Step 2: Draw Line Segment & Midpoint ---
        # Narration: "先用线段图表示两地间的路程，A是甲出发点，B是乙出发点。把正中间标出来，这个点就是中点M。"
        with self.voiceover(text="先用线段图表示两地间的路程，A是甲出发点，B是乙出发点。把正中间标出来，这个点就是中点M。"):
            # Define coordinates
            LEFT_X = -5
            RIGHT_X = 5
            MID_X = 0
            LINE_Y = 1.5

            point_A = np.array([LEFT_X, LINE_Y, 0])
            point_B = np.array([RIGHT_X, LINE_Y, 0])
            point_M = np.array([MID_X, LINE_Y, 0])

            line_AB = Line(point_A, point_B, color=WHITE)

            label_A = get_safe_text("A (甲)", font_size=24).next_to(point_A, UP)
            label_B = get_safe_text("B (乙)", font_size=24).next_to(point_B, UP)

            dot_M = Dot(point_M, color=BLUE)
            label_M = get_safe_text("M (中点)", font_size=24).next_to(dot_M, UP)

            self.play(Create(line_AB), Write(label_A), Write(label_B))
            self.play(FadeIn(dot_M, scale=0.5), Write(label_M))
            self.wait(0.5)

        # --- Step 3: Mark Meeting Point P ---
        # Narration: "题目说相遇点离中点4千米。因为甲更快，所以相遇点会更靠近乙的出发点B，也就是在中点M向乙那边偏4千米的位置。"
        with self.voiceover(
                text="题目说相遇点离中点4千米。因为甲更快，所以相遇点会更靠近乙的出发点B，也就是在中点M向乙那边偏4千米的位置。"):
            # P is to the right of M because Jia (starts at A) is faster.
            # Let's map 4km to visual units. Let visual length AB = 10 units.
            # We don't know total length, but let's assume visual offset is noticeable, e.g., 1.5 units.
            OFFSET_VISUAL = 1.5
            point_P = np.array([MID_X + OFFSET_VISUAL, LINE_Y, 0])

            dot_P = Dot(point_P, color=RED)
            label_P = get_safe_text("P (相遇点)", font_size=24).next_to(dot_P, DOWN)

            # Arrow indicating distance
            brace_PM = BraceBetweenPoints(point_M, point_P, direction=UP, buff=0.05)
            text_PM = MathTex(r"4\text{ km}", font_size=24).next_to(brace_PM, UP, buff=0.1)

            self.play(TransformFromCopy(dot_M, dot_P))
            self.play(Write(label_P))
            self.play(GrowFromCenter(brace_PM), FadeIn(text_PM))
            self.wait(0.5)

        # --- Step 4: Visualizing the Distance Difference ---
        # Narration: "中点的意义是：从A到M、从B到M距离相等。设它们都是L。相遇点P比中点向乙那边偏了4千米，那么甲走到P就是L加4，乙走到P就是L减4。两人路程差就是(L+4)-(L-4)=8千米，也就是偏了4，路程差是它的2倍。"
        with self.voiceover(
                text="中点的意义是：从A到M、从B到M距离相等。设它们都是L。相遇点P比中点向乙那边偏了4千米，那么甲走到P就是L加4，乙走到P就是L减4。两人路程差就是 L 加 4 减去 L 减 4 等于 8 千米，也就是偏了4，路程差是它的2倍。"):
            # Visual Braces for AM and MB
            brace_AM = BraceBetweenPoints(point_A, point_M, direction=DOWN, buff=0.5)
            label_L1 = MathTex("L", font_size=28).next_to(brace_AM, DOWN)

            brace_MB = BraceBetweenPoints(point_M, point_B, direction=DOWN, buff=0.5)
            label_L2 = MathTex("L", font_size=28).next_to(brace_MB, DOWN)

            self.play(Create(brace_AM), Write(label_L1), Create(brace_MB), Write(label_L2))
            self.wait(0.5)

            # Visualize AP = L + 4
            # Shift label L1 and brace slightly to indicate AP is AM + MP
            line_AP = Line(point_A, point_P, color=YELLOW, stroke_width=6).shift(DOWN * 0.1)
            text_AP = MathTex(r"AP = L + 4", color=YELLOW, font_size=32).move_to(LEFT * 3 + DOWN * 1.5)

            line_BP = Line(point_B, point_P, color=GREEN, stroke_width=6).shift(DOWN * 0.1)
            text_BP = MathTex(r"BP = L - 4", color=GREEN, font_size=32).next_to(text_AP, DOWN, aligned_edge=LEFT)

            self.play(Create(line_AP), Write(text_AP))
            self.play(Create(line_BP), Write(text_BP))
            self.wait(0.5)

            # Show the difference math
            diff_eq = MathTex(r"AP - BP", r"=", r"(L+4) - (L-4)", r"=", r"8", font_size=36)
            diff_eq.next_to(text_BP, DOWN, aligned_edge=LEFT, buff=0.5)

            self.play(Write(diff_eq[0]))  # AP - BP
            self.play(Write(diff_eq[1:]))  # Calculation
            self.play(Indicate(diff_eq[-1], color=RED, scale_factor=1.5))  # Highlight 8
            self.wait(1)

            # Clean up diagram for next step
            elements_to_fade = VGroup(brace_AM, label_L1, brace_MB, label_L2, text_AP, text_BP, diff_eq, line_AP,
                                      line_BP)
            self.play(FadeOut(elements_to_fade))

        # --- Step 5: Calculate Speed Difference ---
        # Narration: "相遇说明两个人走的时间相同，都是4小时。速度差等于路程差除以时间：8除以4，得到2千米每小时。"
        with self.voiceover(
                text="相遇说明两个人走的时间相同，都是4小时。速度差等于路程差除以时间：8除以4，得到2千米每小时。"):
            # Keep the diagram at the top
            diagram_group = VGroup(line_AB, label_A, label_B, dot_M, label_M, dot_P, label_P, brace_PM, text_PM)

            # Formula section
            formula_group = VGroup(
                get_safe_text("时间 = 4 小时", font_size=32),
                MathTex(r"\Delta v = \frac{\Delta S}{t}", font_size=40),
                MathTex(r"v_\text{甲} - v_\text{乙} = \frac{8}{4} = 2\text{ km/h}", font_size=40)
            ).arrange(DOWN, buff=0.6).next_to(diagram_group, DOWN, buff=1.0)

            self.play(FadeIn(formula_group[0]))
            self.play(Write(formula_group[1]))
            self.wait(0.5)
            self.play(Write(formula_group[2]))
            self.play(Circumscribe(formula_group[2], color=YELLOW))
            self.wait(1)

        # --- Step 6: Conclusion ---
        # Narration: "所以甲每小时比乙快2千米。记住这个小规律：相遇点偏离中点多少，路程差就是它的2倍，再用路程差除以相遇时间就得到速度差。"
        with self.voiceover(
                text="所以甲每小时比乙快2千米。记住这个小规律：相遇点偏离中点多少，路程差就是它的2倍，再用路程差除以相遇时间就得到速度差。"):
            self.play(FadeOut(formula_group), FadeOut(diagram_group))

            final_text = get_safe_text("答案：甲每小时比乙快 2 千米", font_size=48, color=YELLOW)
            rule_text_1 = get_safe_text("规律：偏离中点 d", font_size=32)
            rule_arrow_1 = MathTex(r"\rightarrow", font_size=32)
            rule_text_2 = get_safe_text("路程差 2d", font_size=32)
            rule_arrow_2 = MathTex(r"\rightarrow", font_size=32)
            rule_text_3 = MathTex(r"\Delta v = \frac{2d}{t}", font_size=36)

            rule_group = VGroup(rule_text_1, rule_arrow_1, rule_text_2, rule_arrow_2, rule_text_3).arrange(RIGHT,
                                                                                                           buff=0.2)
            rule_group.next_to(final_text, DOWN, buff=1.0)

            self.play(Write(final_text))
            self.wait(0.5)
            self.play(FadeIn(rule_group, shift=UP))
            self.wait(3)

# manim -pqh your_file.py MathExplanation