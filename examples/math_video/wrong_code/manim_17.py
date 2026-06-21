from manim import *
import json

# --- TTS Configuration ---
# This script attempts to use manim_voiceover for TTS.
# If the library is missing or fails, it falls back to visual timing (wait).

# Narration script (Source of Truth)
NARRATION_DATA = {
    "S1": "如果把二十五个人按属相分组，至少会有多少个人属相相同？这个问题用一个非常经典的方法：抽屉原理。",
    "S2": "抽屉原理说：当物体比抽屉多时，至少有一个抽屉会更拥挤。更一般地，至少有一个抽屉里不少于，n除以m的上取整，这么多物体。",
    "S3": "在这道题里，抽屉就是十二生肖这十二类；物体就是二十五个人。每个人必然且只能属于其中一个生肖。",
    "S4": "关键拆分是：二十五等于十二乘二再加一。也可以用统一公式：至少有一类人数不少于十二分之二十五的上取整，也就是三。",
    "S5": "先做一个最平均的分配：让每个生肖里都有两个人。这样十二个生肖一共只能放下二十四人。",
    "S6": "现在加入第二十五个人。无论他属哪个生肖，都必须进入某一个抽屉，于是必然有一个生肖从两人变成三人。",
    "S7": "这就是抽屉原理的结论：在二十五个人里，至少有三个人属相相同。用公式表达就是：十二分之二十五的上取整等于三。",
    "S8": "以后遇到有限类别装更多对象的问题，都可以直接用 n除以m的上取整 来快速得到“至少多少个相同”的保证值。"
}

# Attempt imports
USE_VOICEOVER = False
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    USE_VOICEOVER = True
except ImportError:
    # Fallback class if library missing
    class VoiceoverScene(Scene):
        pass

class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # Initialize TTS Service if available
        if USE_VOICEOVER:
            try:
                # Using Google TTS (requires internet)
                self.set_speech_service(GTTSService(lang="zh-CN"))
            except Exception as e:
                print(f"TTS Init Failed: {e}, falling back to silent mode.")
                global USE_VOICEOVER
                USE_VOICEOVER = False

        # Helper to handle "Narration + Animation" block
        def play_sync(step_key, anim_func, fallback_wait=2.0):
            text = NARRATION_DATA.get(step_key, "")
            if USE_VOICEOVER:
                with self.voiceover(text=text) as tracker:
                    anim_func()
            else:
                anim_func()
                self.wait(fallback_wait)

        # --- Scene Content Starts Here ---

        # [S1] Title & Hook
        title = Text("25个人中至少有多少人属相相同？", font_size=36)
        subtitle = Text("抽屉原理（鸽巢原理） + 12生肖", font_size=24, color=GRAY)
        subtitle.next_to(title, DOWN)
        header_group = VGroup(title, subtitle).to_edge(UP, buff=0.8)

        def anim_s1():
            self.play(Write(title))
            self.play(FadeIn(subtitle, shift=DOWN))
        
        play_sync("S1", anim_s1, 4)

        # [S2] Principle Definition
        # Text: "抽屉原理：把 n 个物体放进 m 个抽屉"
        principle_text = Text("抽屉原理：把 n 个物体放进 m 个抽屉", font_size=28)
        
        # Formula Line: "=> 至少有一个抽屉 >= ceil(n/m) 个"
        # Split Text and MathTex to allow Chinese
        p_part1 = Text("至少有一个抽屉含有", font_size=28)
        p_math = MathTex(r"\ge \left\lceil n/m \right\rceil", font_size=36, color=YELLOW)
        p_part2 = Text("个物体", font_size=28)
        
        principle_formula = VGroup(p_part1, p_math, p_part2).arrange(RIGHT, buff=0.15)
        principle_group = VGroup(principle_text, principle_formula).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        principle_group.to_edge(UP, buff=1.0)

        def anim_s2():
            self.play(FadeOut(header_group, shift=UP))
            self.play(FadeIn(principle_group, shift=DOWN))
        
        play_sync("S2", anim_s2, 5)

        # [S3] Mapping: 12 Zodiac Boxes
        zodiac_chars = list("子丑寅卯辰巳午未申酉戌亥")
        boxes = VGroup()
        labels = VGroup()
        
        for char in zodiac_chars:
            box = Rectangle(width=1.2, height=1.2, color=WHITE, stroke_width=2)
            lbl = Text(char, font_size=24, color=LIGHT_GRAY)
            lbl.move_to(box.get_center())
            boxes.add(box)
            labels.add(lbl)
        
        grid = VGroup()
        for i in range(12):
            g = VGroup(boxes[i], labels[i])
            grid.add(g)
        
        grid.arrange_in_grid(rows=3, cols=4, buff=0.3)
        grid.to_edge(DOWN, buff=0.5)

        # Mapping explanation text
        map_t1 = Text("抽屉 = 12 个生肖（类别）", font_size=24, color=BLUE)
        map_t2 = Text("物体 = 25 个人", font_size=24, color=YELLOW)
        map_group = VGroup(map_t1, map_t2).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        map_group.next_to(principle_group, DOWN, buff=0.5).to_edge(LEFT, buff=1.0)

        def anim_s3():
            self.play(Create(boxes), FadeIn(labels))
            self.play(FadeIn(map_group, shift=RIGHT))
        
        play_sync("S3", anim_s3, 5)

        # [S4] Key Equations
        eq1 = MathTex(r"25 = 12 \times 2 + 1", font_size=38)
        eq2 = MathTex(r"\left\lceil 25/12 \right\rceil = 3", font_size=38)
        eq_group = VGroup(eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        # Position right of map group, roughly centered in remaining space
        eq_group.next_to(map_group, RIGHT, buff=2.0).align_to(map_group, UP)

        def anim_s4():
            self.play(Write(eq1))
            self.wait(0.5)
            self.play(Write(eq2))
        
        play_sync("S4", anim_s4, 5)

        # [S5] Animation: Fill 24 dots
        dots_group = VGroup()
        for i in range(12):
            c = boxes[i].get_center()
            d1 = Dot(c + UP * 0.25, radius=0.08, color=BLUE)
            d2 = Dot(c + DOWN * 0.25, radius=0.08, color=BLUE)
            dots_group.add(d1, d2)

        caption_24 = Text("每类先放 2 人：共 24 人", font_size=24, color=BLUE)
        caption_24.next_to(grid, UP, buff=0.2)

        def anim_s5():
            self.play(FadeIn(caption_24))
            self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots_group], lag_ratio=0.04))
        
        play_sync("S5", anim_s5, 6)

        # [S6] Add 25th Person
        # Add to first box (Index 0)
        c_target = boxes[0].get_center()
        extra_dot = Dot(c_target, radius=0.1, color=YELLOW)
        extra_label = Text("第25人", font_size=18, color=YELLOW)
        extra_label.next_to(extra_dot, RIGHT, buff=0.1)

        caption_25 = Text("第 25 人加入：必然有生肖变成 3 人", font_size=24, color=YELLOW)
        caption_25.move_to(caption_24.get_center())

        def anim_s6():
            self.play(FadeOut(caption_24), FadeIn(caption_25))
            self.play(FadeIn(extra_dot, scale=1.5), FadeIn(extra_label, shift=LEFT))
        
        play_sync("S6", anim_s6, 4)

        # [S7] Conclusion & Highlight
        highlight_rect = SurroundingRectangle(boxes[0], color=YELLOW, buff=0.1, stroke_width=4)
        
        final_text = Text("结论：至少 3 个人属相相同", font_size=32, color=YELLOW)
        final_text.move_to(principle_group.get_center())
        
        box_eq2 = SurroundingRectangle(eq2, color=YELLOW, buff=0.1)

        def anim_s7():
            self.play(Create(highlight_rect))
            self.play(FadeOut(principle_group), FadeIn(final_text))
            self.play(Create(box_eq2))
        
        play_sync("S7", anim_s7, 5)

        # [S8] Outro
        def anim_s8():
            self.play(
                FadeOut(grid),
                FadeOut(dots_group),
                FadeOut(extra_dot),
                FadeOut(extra_label),
                FadeOut(highlight_rect),
                FadeOut(map_group),
                FadeOut(eq1),
                FadeOut(caption_25),
                run_time=2
            )
        
        play_sync("S8", anim_s8, 3)
        self.wait(2)

# Run with: manim -pqh your_file.py ZodiacPigeonhole
