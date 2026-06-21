from manim import *
import math

# --- TTS / Narration Configuration ---
# This list provides the fallback narration script if manim-voiceover is not installed or fails.
# Each item corresponds to a step in the animation.
NARRATION = [
    {
        "id": "S01",
        "text": "如果随便找来二十五个人，不管他们怎么分布，至少会有几个人属相相同？这题用一个经典工具：抽屉原理。",
        "hint": "Title and Problem Statement"
    },
    {
        "id": "S02",
        "text": "先把问题翻译成抽屉语言：二十五个人是要放进去的物品；十二个属相是十二个抽屉，也就是十二个类别。",
        "hint": "Visualizing People vs Drawers"
    },
    {
        "id": "S03",
        "text": "抽屉原理常用结论是：把n个物品放进m个抽屉，至少有一个抽屉里的数量不小于向上取整的n除以m。",
        "hint": "Formula Introduction"
    },
    {
        "id": "S04",
        "text": "代入本题：n等于二十五，m等于十二。二十五除以十二等于二余一，所以向上取整得到三。",
        "hint": "Calculation"
    },
    {
        "id": "S05",
        "text": "为了看得更直观，我们先假设一个最平均的情况：每个属相最多两个人。十二个属相，每个放两人，一共也只能放下二十四人。",
        "hint": "Visual Distribution of first 24"
    },
    {
        "id": "S06",
        "text": "现在关键来了：第25个人无论属相是什么，都必须落进这十二个抽屉里的某一个。可每个抽屉刚才都已经到2了，所以必然有一个抽屉变成3个人。",
        "hint": "The 25th Person"
    },
    {
        "id": "S07",
        "text": "所以答案是：至少有三个人的属相相同。记住抽屉原理的核心直觉：平均分完，多出来的那一个，一定会把某个抽屉挤到更高的数量。",
        "hint": "Conclusion"
    }
]

# Try importing manim-voiceover, otherwise define a dummy class for compatibility
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.pyttsx3 import Pyttsx3Service
    VO_AVAILABLE = True
except ImportError:
    VO_AVAILABLE = False
    # Dummy class to prevent errors if library is missing
    class VoiceoverScene(Scene):
        def voiceover(self, text=None, **kwargs):
            # Returns a context manager that does nothing but wait
            class DummyContext:
                def __enter__(self): pass
                def __exit__(self, exc_type, exc_val, exc_tb): pass
            return DummyContext()


class PigeonholePrinciple(VoiceoverScene if VO_AVAILABLE else Scene):
    def construct(self):
        # --- Setup Voiceover if available ---
        if VO_AVAILABLE:
            self.set_speech_service(Pyttsx3Service(voice=None, rate=1.1))
        
        # --- Helper for Text to avoid font issues ---
        def create_text(content, size=24, color=WHITE, weight=NORMAL):
            return Text(content, font_size=size, color=color, weight=weight)

        # ==========================================================================
        # S01: 标题与抛题
        # ==========================================================================
        # Visuals: Simple Title and Problem Text
        title = create_text("抽屉原理：25个人里至少有几个人属相相同？", size=40, weight=BOLD)
        title.to_edge(UP, buff=0.8)
        
        problem_box = VGroup(
            create_text("任意25个人中", size=32),
            create_text("至少有几个人的属相相同？", size=32)
        ).arrange(DOWN, buff=0.3)
        
        tag = create_text("抽屉原理", size=20, color=BLUE)
        tag.to_corner(DR, buff=0.5)

        with self.voiceover(text=NARRATION[0]["text"]):
            self.play(Write(title))
            self.play(FadeIn(problem_box, shift=UP))
            self.play(FadeIn(tag))
            self.wait(1)

        # ==========================================================================
        # S02: 建立对应：物品与抽屉
        # ==========================================================================
        # Visuals: Split screen. Left: 25 dots. Right: 12 Squares.
        
        # Cleanup S01
        self.play(
            FadeOut(problem_box),
            title.animate.scale(0.7).to_edge(UP, buff=0.2),
            FadeOut(tag)
        )

        # Create Objects
        # Left: People (Dots)
        people_group = VGroup(*[Dot(radius=0.1, color=YELLOW) for _ in range(25)])
        people_group.arrange_in_grid(rows=5, cols=5, buff=0.2)
        people_label = create_text("物品：25个人", size=24, color=YELLOW)
        people_label.next_to(people_group, UP)
        left_section = VGroup(people_label, people_group).to_edge(LEFT, buff=1.5)

        # Right: Drawers (Squares)
        zodiac_names = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
        drawers = VGroup()
        for z in zodiac_names:
            sq = Square(side_length=1.2, color=BLUE_C, fill_opacity=0.2, fill_color=BLUE_E)
            txt = create_text(z, size=24)
            # Position text at bottom of square
            txt.move_to(sq.get_bottom() + UP*0.25)
            drawer_unit = VGroup(sq, txt)
            drawers.add(drawer_unit)
        
        drawers.arrange_in_grid(rows=3, cols=4, buff=0.3)
        drawer_label = create_text("抽屉：12个属相", size=24, color=BLUE)
        drawer_label.next_to(drawers, UP)
        right_section = VGroup(drawer_label, drawers).to_edge(RIGHT, buff=1.0)

        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(FadeIn(left_section, shift=RIGHT))
            self.play(FadeIn(right_section, shift=LEFT))
            self.wait(2)

        # ==========================================================================
        # S03: 给出抽屉原理结论（公式版）
        # ==========================================================================
        # Transition: Fade out visual elements to focus on math
        
        self.play(FadeOut(left_section), FadeOut(right_section))

        formula_text_1 = create_text("若 n 个物品放入 m 个抽屉", size=32)
        formula_text_2 = create_text("至少有一个抽屉内数量", size=32)
        
        # LaTeX formula: ceil(n/m)
        formula_math = MathTex(r"\ge \left\lceil \frac{n}{m} \right\rceil", color=YELLOW, font_size=48)
        
        formula_group = VGroup(formula_text_1, formula_text_2, formula_math).arrange(DOWN, buff=0.4)
        
        explanation = VGroup(
            MathTex(r"\lceil x \rceil", color=YELLOW),
            create_text("表示向上取整", size=24)
        ).arrange(RIGHT).next_to(formula_group, DOWN, buff=1.0)

        with self.voiceover(text=NARRATION[2]["text"]):
            self.play(Write(formula_text_1))
            self.play(FadeIn(formula_text_2))
            self.play(TransformMatchingShapes(formula_text_2.copy(), formula_math))
            self.play(FadeIn(explanation))
            self.wait(1)

        # ==========================================================================
        # S04: 代入数据计算
        # ==========================================================================
        
        calc_step1 = MathTex(r"n=25, \quad m=12").move_to(formula_text_1)
        
        # Division visualization
        calc_step2 = VGroup(
            MathTex(r"25 \div 12 = 2 \dots 1"),
            MathTex(r"\left\lceil \frac{25}{12} \right\rceil = 3", color=YELLOW)
        ).arrange(DOWN, buff=0.5).move_to(formula_group)

        with self.voiceover(text=NARRATION[3]["text"]):
            self.play(ReplacementTransform(formula_text_1, calc_step1))
            self.play(
                FadeOut(formula_text_2),
                ReplacementTransform(formula_math, calc_step2[1]),
                FadeIn(calc_step2[0], shift=UP)
            )
            self.play(Indicate(calc_step2[1], color=RED))
            self.wait(1.5)
            
        # Cleanup math for visual proof
        self.play(FadeOut(calc_step1), FadeOut(calc_step2), FadeOut(explanation))

        # ==========================================================================
        # S05: 可视化分配：先塞满到24
        # ==========================================================================
        # Bring back the drawers, centered
        drawers.move_to(ORIGIN).scale(1.1)
        
        # Counters for each drawer
        counters = VGroup()
        for d in drawers:
            # d is VGroup(Square, Text)
            # Add a counter number to top right corner
            c = Integer(0, color=YELLOW).scale(0.6)
            c.move_to(d[0].get_corner(UR) + DL*0.3)
            counters.add(c)
            d.add(c) # Group it so it moves together if needed

        # Info Panel at bottom
        info_panel = VGroup(
            create_text("假设最平均分配：每格2人", size=24, color=GREY_A),
            create_text("已放入：0 / 25", size=24)
        ).arrange(DOWN).to_edge(DOWN, buff=0.5)
        info_counter = info_panel[1]

        with self.voiceover(text=NARRATION[4]["text"]):
            self.play(FadeIn(drawers))
            self.play(FadeIn(info_panel))
            
            # Animation: Fill 24 dots (2 per drawer)
            # To save time and keep pacing, we animate in batches of 12 (1 per drawer)
            
            # Batch 1: 1-12
            dots_batch_1 = VGroup()
            anims_1 = []
            for i in range(12):
                d = Dot(color=YELLOW)
                # Start from left off screen
                d.move_to(LEFT_SIDE)
                target = drawers[i][0].get_center() + UL*0.2 # Offset slightly
                dots_batch_1.add(d)
                anims_1.append(d.animate.move_to(target))
            
            self.add(dots_batch_1)
            self.play(
                *anims_1, 
                *[c.animate.set_value(1) for c in counters],
                run_time=2
            )
            
            # Batch 2: 13-24
            dots_batch_2 = VGroup()
            anims_2 = []
            for i in range(12):
                d = Dot(color=YELLOW)
                d.move_to(LEFT_SIDE)
                target = drawers[i][0].get_center() + DR*0.2 # Offset different corner
                dots_batch_2.add(d)
                anims_2.append(d.animate.move_to(target))
                
            self.add(dots_batch_2)
            self.play(
                *anims_2, 
                *[c.animate.set_value(2) for c in counters],
                run_time=2
            )
            
            # Update total text manually for simplicity in logic
            new_info_text = create_text("已放入：24 / 25", size=24).move_to(info_counter)
            self.play(Transform(info_counter, new_info_text))
            
            full_text = create_text("12 × 2 = 24 (已满)", color=RED, size=24).next_to(info_panel, UP)
            self.play(FadeIn(full_text))
            self.wait(1)

        # ==========================================================================
        # S06: 第25人出现：必然挤出3
        # ==========================================================================
        
        pigeon = Dot(color=RED, radius=0.15)
        pigeon.move_to(UP*3.5)
        
        question_mark = Text("?", color=RED).next_to(pigeon, UP, buff=0.1)
        
        # Target Drawer (Let's say the 6th one, index 5, "Snake")
        target_index = 5
        target_drawer = drawers[target_index]
        target_pos = target_drawer[0].get_center()
        target_counter = counters[target_index]

        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(FadeIn(pigeon), FadeIn(question_mark))
            self.wait(0.5)
            
            # Animate falling into drawer
            self.play(
                pigeon.animate.move_to(target_pos),
                FadeOut(question_mark),
                run_time=1.5
            )
            
            # Counter goes to 3
            self.play(
                target_counter.animate.set_value(3).set_color(RED).scale(1.5),
                target_drawer[0].animate.set_stroke(RED, width=6),
                Flash(target_drawer, color=RED, flash_radius=1.5)
            )
            self.wait(1)

        # ==========================================================================
        # S07: 结论与一句话记忆
        # ==========================================================================
        
        # Fade everything slightly back
        dark_rect = FullScreenRectangle(fill_opacity=0.8, color=BLACK)
        
        # Focus on the result
        conclusion_group = VGroup(
            create_text("结论：至少有 3 个人属相相同", size=36, color=YELLOW, weight=BOLD),
            MathTex(r"\lceil 25 / 12 \rceil = 3", font_size=40),
            create_text("核心原理：", size=28, color=BLUE),
            create_text("多出来的那个人(第25人)", size=24),
            create_text("一定会把某个抽屉挤到3个", size=24, color=RED)
        ).arrange(DOWN, buff=0.4)
        
        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(FadeIn(dark_rect))
            self.play(Write(conclusion_group))
            self.wait(3)

        # End
        self.play(FadeOut(Group(*self.mobjects)))
        self.wait(1)

# Run with: manim -pqh filename.py PigeonholePrinciple