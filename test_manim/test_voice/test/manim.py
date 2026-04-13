from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
from manim_voiceover.services.openai import OpenAIService
from manim_voiceover.services.openai import OpenAIService
from manim_voiceover.services.recorder import RecorderService
from manim_voiceover.services.azure import AzureService
from manim_voiceover.services.coqui import CoquiService

import numpy as np

class ClockOverlapAt2(VoiceoverScene):
    def construct(self):
        # Initialize Voiceover Service
        self.set_speech_service(GTTSService(lang="zh-CN"))

        # --- 1. Hook: Title & Clock Setup ---
        with self.voiceover(text="现在是2点整。我们要找：时针和分针第一次重合在什么时候？"):
            title = Text("2点开始：时针和分针第一次重合在什么时候？", font_size=32)
            title.to_edge(UP, buff=0.5)
            self.play(Write(title))

            # Draw Clock
            R = 2.4
            clock = Circle(radius=R, color=WHITE)
            center_dot = Dot(point=ORIGIN, radius=0.08, color=WHITE)

            ticks = VGroup()
            for i in range(60):
                ang = PI/2 - TAU * (i / 60)
                outer = R * np.array([np.cos(ang), np.sin(ang), 0.0])
                inner_len = 0.18 if i % 5 == 0 else 0.10
                inner = (R - inner_len) * np.array([np.cos(ang), np.sin(ang), 0.0])
                ticks.add(Line(inner, outer, stroke_width=3 if i % 5 == 0 else 1.5, color=WHITE))

            nums = VGroup(
                Text("12", font_size=24).move_to((R + 0.35) * UP),
                Text("3", font_size=24).move_to((R + 0.35) * RIGHT),
                Text("6", font_size=24).move_to((R + 0.35) * DOWN),
                Text("9", font_size=24).move_to((R + 0.35) * LEFT),
            )

            clock_group = VGroup(clock, ticks, nums, center_dot).shift(LEFT * 3)
            self.play(Create(clock), Create(ticks), FadeIn(nums), FadeIn(center_dot))

        # Initialize Hands (ValueTracker driver)
        t = ValueTracker(0.0) # minutes after 2:00

        def hand_endpoint(minutes, length, is_hour=False):
            if is_hour:
                hour = 2.0 + minutes / 60.0
                theta = TAU * (hour / 12.0)
            else:
                theta = TAU * (minutes / 60.0)
            ang = PI/2 - theta
            return length * np.array([np.cos(ang), np.sin(ang), 0.0])

        minute_hand = always_redraw(lambda: Line(
            clock_group.get_center(),
            clock_group.get_center() + hand_endpoint(t.get_value(), R * 0.9, is_hour=False),
            color=YELLOW, stroke_width=4
        ))
        hour_hand = always_redraw(lambda: Line(
            clock_group.get_center(),
            clock_group.get_center() + hand_endpoint(t.get_value(), R * 0.6, is_hour=True),
            color=BLUE, stroke_width=6
        ))
        self.add(hour_hand, minute_hand)
        self.wait(0.5)

        # --- 2. Model: 60 Grids ---
        with self.voiceover(text="把表盘等分成60个小格。2点整时，分针在0格，时针在10格，所以初始差距是10格"):
            model_title = Text("60小格模型", font_size=28, color=YELLOW).to_corner(UP + RIGHT).shift(LEFT*1)
            self.play(Write(model_title))
            
            grid_info = VGroup(
                Text("整圈 = 60格", font_size=24),
                Text("分针位置: 0格", font_size=24),
                Text("时针位置: 10格", font_size=24),
                Text("初始差距 = 10格", font_size=24, color=RED)
            ).arrange(DOWN, aligned_edge=LEFT).next_to(model_title, DOWN, buff=0.3)
            self.play(FadeIn(grid_info[0]), FadeIn(grid_info[1]), FadeIn(grid_info[2]))
            self.play(Indicate(grid_info[3]))

            # Visualize gap on clock
            gap_arc = Arc(radius=R*0.5, start_angle=PI/2, angle=-TAU*(10/60), color=RED, arc_center=clock_group.get_center())
            self.play(Create(gap_arc))
            self.wait(0.5)
            self.play(FadeOut(gap_arc))

        # --- 3. Speeds ---
        with self.voiceover(text="分针每分钟走1格；时针每分钟走十二分之一格"):
            speed_info = VGroup(
                Text("分针速度 = 1格/分", font_size=24),
                Text("时针速度 = 1/12格/分", font_size=24)
            ).arrange(DOWN, aligned_edge=LEFT).next_to(grid_info, DOWN, buff=0.3)
            self.play(Write(speed_info))
            
            # Demo 1 minute move (fast)
            self.play(t.animate.set_value(5), run_time=0.5) # Fast forward a bit to show movement
            self.play(t.animate.set_value(0), run_time=0.5) # Reset

        # --- 4. Relative Speed ---
        with self.voiceover(text="分针追时针的相对速度是：1减十二分之一，等于十二分之十一格每分钟"):
            rel_speed_text = MathTex(r"v_{rel} = 1 - \frac{1}{12} = \frac{11}{12}", font_size=32)
            rel_unit = Text("格/分", font_size=24).next_to(rel_speed_text, RIGHT)
            rel_group = VGroup(rel_speed_text, rel_unit).next_to(speed_info, DOWN, buff=0.4).align_to(speed_info, LEFT)
            self.play(Write(rel_group))

        # --- 5. Calculation ---
        with self.voiceover(text="追上所需时间等于差距除以相对速度：10除以十一分之十二，得到11分之120分钟"):
            calc_formula = MathTex(r"t = \frac{10}{11/12} = \frac{120}{11}", font_size=36)
            calc_unit = Text("分钟", font_size=24).next_to(calc_formula, RIGHT)
            calc_group = VGroup(calc_formula, calc_unit).next_to(rel_group, DOWN, buff=0.5).align_to(rel_group, LEFT)
            self.play(Write(calc_group))

        # --- 6. Conversion ---
        with self.voiceover(text="换算一下：11分之120分钟等于10分再加上11分之10分钟，也就是大约10分54.5秒"):
            convert_text = MathTex(r"\approx 10\text{ min } 54.5\text{ s}", font_size=36)
            convert_text.next_to(calc_group, DOWN, buff=0.2).align_to(calc_group, LEFT)
            self.play(Write(convert_text))

        # --- 7. Animation Conclusion ---
        with self.voiceover(text="所以第一次重合发生在：2点10分54.5秒"):
            final_time = Text("2:10:54.5", font_size=40, color=GREEN).next_to(clock_group, DOWN, buff=0.5)
            
            # Animate clock to exact overlap time (120/11 minutes)
            target_minutes = 120/11
            self.play(
                t.animate.set_value(target_minutes),
                run_time=4,
                rate_func=linear
            )
            self.play(FadeIn(final_time))
            self.play(Flash(clock_group.get_center(), color=GREEN, flash_radius=1))
            self.wait(2)
