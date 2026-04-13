from manim import *
import math

# -----------------------------------------------------------------------------
# 旁白脚本配置 (Fallback data if TTS is not active)
# -----------------------------------------------------------------------------
NARRATION = [
    {
        "id": "S1-1",
        "text": "如果有二十五个人，按十二个属相来分组，能不能保证至少有三个人属相相同？"
    },
    {
        "id": "S1-2",
        "text": "答案是能。关键只需要一个非常直观的原理：抽屉原理。"
    },
    {
        "id": "S2-1",
        "text": "把十二个属相想成十二个抽屉，把二十五个人想成二十五个要放进去的球。"
    },
    {
        "id": "S2-2",
        "text": "如果你想尽办法避免出现三个人同属相，那每个属相最多只能放两个人。"
    },
    {
        "id": "S3-1",
        "text": "用除法把信息说得更精确：二十五除以十二，商是二，余一。"
    },
    {
        "id": "S3-2",
        "text": "商二表示每个抽屉至少能放到两个人还不一定超标；但余下的那一个人，必然会让某个抽屉从二变三。"
    },
    {
        "id": "S4-1",
        "text": "我们来做最坏情况模拟：第一轮，给每个属相都放进一个人。"
    },
    {
        "id": "S4-2",
        "text": "第二轮再来一遍。放到第二十四个人为止，你可以做到每个抽屉都正好两个人——仍然没有任何抽屉达到三人。"
    },
    {
        "id": "S5-1",
        "text": "现在关键来了：第25个人不管你放进哪个属相抽屉，都只能挤进一个已经有两个人的抽屉里。"
    },
    {
        "id": "S5-2",
        "text": "于是某个属相的人数从2变成3。这就证明了：二十五个人里，至少有三个人属相相同。"
    }
]

# -----------------------------------------------------------------------------
# TTS Setup (Optional)
# -----------------------------------------------------------------------------
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.pyttsx3 import PyTTSX3Service
    HAS_VOICEOVER = True
except ImportError:
    HAS_VOICEOVER = False
    # Fallback class if library is missing
    class VoiceoverScene(Scene):
        def voiceover(self, text=None):
            # Dummy context manager that acts like wait
            class DummyContext:
                def __enter__(ctx):
                    pass
                def __exit__(ctx, exc_type, exc_val, exc_tb):
                    self.wait(len(text) * 0.15 if text else 1)
            return DummyContext()

# -----------------------------------------------------------------------------
# Main Scene
# -----------------------------------------------------------------------------
class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # TTS Service Config
        if HAS_VOICEOVER:
            self.set_speech_service(PyTTSX3Service(voice_name="zh-CN", rate=180))

        # =====================================================================
        # 1. Title & Intro
        # =====================================================================
        # S1-1
        title = Text("25个人中至少有3个人属相相同？", font_size=42, weight=BOLD)
        subtitle = Text("抽屉原理 + 最坏情况模拟", font_size=28, color=BLUE).next_to(title, DOWN)
        
        with self.voiceover(text=NARRATION[0]["text"]):
            self.play(Write(title), FadeIn(subtitle))
            self.wait(0.5)

        # S1-2
        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(title.animate.to_edge(UP).scale(0.8), FadeOut(subtitle))
            self.wait(0.5)

        # =====================================================================
        # 2. Drawers Setup (Flattened Structure)
        # =====================================================================
        # S2-1
        zodiacs = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
        
        # Explicit lists to avoid nested VGroup indexing issues
        self.drawer_boxes = []
        self.drawer_labels = []
        self.drawer_slots = []
        
        # Master VGroup for layout only
        layout_group = VGroup()
        
        # Grid params
        cols = 6
        box_width = 1.8
        box_height = 2.0
        buff_x = 0.3
        buff_y = 0.8

        for i, z_name in enumerate(zodiacs):
            # Create Box
            box = RoundedRectangle(width=box_width, height=box_height, corner_radius=0.2, color=WHITE)
            box.set_fill(color=BLACK, opacity=0.5)
            
            # Create Label
            label = Text(z_name, font_size=24, color=YELLOW)
            label.next_to(box, UP, buff=0.1)
            
            # Create Slot Container (Empty VGroup for tokens)
            slot_group = VGroup()
            
            # Positioning
            r = i // cols
            c = i % cols
            
            # Group for initial placement
            unit = VGroup(box, label, slot_group)
            
            # Store references in FLAT lists (Critical for logic)
            self.drawer_boxes.append(box)
            self.drawer_labels.append(label)
            self.drawer_slots.append(slot_group)
            
            layout_group.add(unit)

        # Arrange the whole grid
        layout_group.arrange_in_grid(rows=2, cols=6, buff=(buff_x, buff_y))
        layout_group.shift(DOWN * 0.5) # Shift down a bit to leave room for title

        with self.voiceover(text=NARRATION[2]["text"]):
            self.play(LaggedStart(
                *[Create(b) for b in self.drawer_boxes],
                lag_ratio=0.05,
                run_time=2
            ))
            self.play(LaggedStart(
                *[Write(l) for l in self.drawer_labels],
                lag_ratio=0.05,
                run_time=1
            ))

        # S2-2 Explanation Rule
        rule_text = Text("避免3人同属相 → 每个抽屉最多放2人", font_size=24, color=RED)
        rule_text.to_corner(UL).shift(DOWN*1.2)
        
        with self.voiceover(text=NARRATION[3]["text"]):
            self.play(FadeIn(rule_text))
            # Visual hint: show "Max 2" over a couple of boxes temporarily
            self.play(Indicate(self.drawer_boxes[0], color=RED), Indicate(self.drawer_boxes[1], color=RED))

        # =====================================================================
        # 3. Math Logic
        # =====================================================================
        # S3-1
        math_bg = BackgroundRectangle(VGroup(), fill_opacity=0.8, fill_color=BLACK)
        eq1 = MathTex(r"25 \div 12 = 2 \cdots 1").scale(1.2)
        eq2 = MathTex(r"2 + 1 = 3").scale(1.2)
        
        math_group = VGroup(eq1, eq2).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        math_group.to_corner(DR).shift(UP*0.5 + LEFT*0.5)
        math_bg.match_height(math_group).match_width(math_group).scale(1.2).move_to(math_group)
        
        with self.voiceover(text=NARRATION[4]["text"]):
            self.play(FadeIn(math_bg), Write(eq1))
            # Highlight "2"
            self.play(Indicate(eq1[0][6], color=YELLOW, scale_factor=1.5))

        # S3-2
        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(Write(eq2))
            # Highlight remainder logic
            self.play(Indicate(eq1[0][8], color=RED)) # The "1" in remainder
            self.play(Indicate(eq2[0][0], color=YELLOW), Indicate(eq2[0][2], color=RED)) # 2 + 1

        # =====================================================================
        # 4. Simulation: Worst Case
        # =====================================================================
        
        # Helper functions
        def create_person(k):
            # Create a token
            token = VGroup()
            bg = Circle(radius=0.18, color=WHITE, stroke_width=2)
            bg.set_fill(color=BLUE_E, opacity=1)
            lbl = Text(f"P{k}", font_size=14, color=WHITE)
            token.add(bg, lbl)
            return token

        def place_person(k, drawer_idx, run_time=0.2):
            token = create_person(k)
            # Start from center screen
            token.move_to(ORIGIN)
            self.add(token)
            
            # Calculate Target
            box = self.drawer_boxes[drawer_idx]
            slots = self.drawer_slots[drawer_idx]
            
            # Stack logic: Bottom up inside the box
            # Box bottom center
            base_pos = box.get_bottom() + UP * 0.3
            stack_offset = UP * 0.4
            current_count = len(slots)
            
            target_pos = base_pos + (stack_offset * current_count)
            
            self.play(token.animate.move_to(target_pos), run_time=run_time)
            
            # Add to logical slot structure
            slots.add(token)

        # Counter Display
        count_val = Integer(0)
        count_label = Text("已放入人数: ", font_size=28)
        counter_group = VGroup(count_label, count_val).arrange(RIGHT).to_corner(DL).shift(UP*0.5)
        self.play(FadeIn(counter_group))

        # S4-1: First Round (0-12)
        with self.voiceover(text=NARRATION[6]["text"]):
            for i in range(12):
                person_num = i + 1
                count_val.set_value(person_num)
                place_person(person_num, i, run_time=0.25)

        # S4-2: Second Round (13-24)
        with self.voiceover(text=NARRATION[7]["text"]):
            for i in range(12):
                person_num = 12 + i + 1
                count_val.set_value(person_num)
                place_person(person_num, i, run_time=0.25)
        
        # Highlight that all are full with 2
        self.play(Flash(layout_group, color=YELLOW, flash_radius=4))

        # =====================================================================
        # 5. The 25th Person & Conclusion
        # =====================================================================
        
        # S5-1: The indecisive 25th person
        p25 = create_person(25)
        p25.move_to(UP * 2.5) # Start high
        self.add(p25)
        count_val.set_value(25)

        with self.voiceover(text=NARRATION[8]["text"]):
            # Animate hovering over a few drawers
            path_points = [
                self.drawer_boxes[0].get_top() + UP,
                self.drawer_boxes[5].get_top() + UP,
                self.drawer_boxes[8].get_top() + UP,
                self.drawer_boxes[0].get_top() + UP
            ]
            self.play(p25.animate.move_to(path_points[1]), run_time=0.5)
            self.play(p25.animate.move_to(path_points[2]), run_time=0.5)
            self.play(p25.animate.move_to(path_points[3]), run_time=0.5)

        # S5-2: Landing and Conclusion
        target_idx = 0 # Choose the first one (Rat) as the target
        
        with self.voiceover(text=NARRATION[9]["text"]):
            # 1. Highlight target drawer box
            self.play(self.drawer_boxes[target_idx].animate.set_stroke(YELLOW, width=6))
            
            # 2. Move person in
            # Calculate final pos manually for p25
            box = self.drawer_boxes[target_idx]
            slots = self.drawer_slots[target_idx]
            base_pos = box.get_bottom() + UP * 0.3
            stack_offset = UP * 0.4
            current_count = len(slots)
            target_pos = base_pos + (stack_offset * current_count)
            
            self.play(p25.animate.move_to(target_pos))
            self.drawer_slots[target_idx].add(p25)

            # 3. Highlight the group of 3
            group_of_3 = self.drawer_slots[target_idx]
            self.play(Indicate(group_of_3, color=PURE_RED, scale_factor=1.2))

            # 4. Final Text Conclusion
            final_text = Text("结论：25人中至少有3人属相相同", font_size=36, color=YELLOW)
            final_text.add_background_rectangle()
            final_text.move_to(ORIGIN)
            
            self.play(FadeIn(final_text))
            self.wait(2)

# manim -pqh zodiac_pigeonhole.py ZodiacPigeonhole