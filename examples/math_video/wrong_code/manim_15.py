from manim import *
import json

# --- TTS Support Setup (Optional Dependency) ---
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    HAS_VOICEOVER = True
except ImportError:
    HAS_VOICEOVER = False
    # Fallback class if manim_voiceover is not installed
    class VoiceoverScene(Scene):
        def voiceover(self, text=None, **kwargs):
            # Create a dummy context manager
            from contextlib import contextmanager
            @contextmanager
            def dummy():
                yield
            return dummy()
        def set_speech_service(self, service):
            pass
    GTTSService = None

# --- Narration Script ---
NARRATION = [
    {
        "id": "S1",
        "text": "今天用一个直观的小动画理解抽屉原理：在 25 个人里，至少有 3 个人的属相相同。",
        "hint": "Intro"
    },
    {
        "id": "S2",
        "text": "先建模：把 12 个属相看成 12 个抽屉，也就是 12 个分类。",
        "hint": "Show Drawers"
    },
    {
        "id": "S3",
        "text": "再把 25 个人看成要放进抽屉的 25 个物品。接下来我们真的把他们放进去。",
        "hint": "Show People"
    },
    {
        "id": "S4",
        "text": "如果我们想避免出现 3 个同属相，就必须让每个属相最多只有 2 个人。那最多能装下多少人呢？我们先给每个抽屉放 2 个点。",
        "hint": "Distribute 24"
    },
    {
        "id": "S5",
        "text": "现在你会发现：抽屉都放到每个 2 人了，一共只有 24 人。但我们有 25 人，还剩下最后 1 人无处可去。",
        "hint": "Highlight last one"
    },
    {
        "id": "S6",
        "text": "这最后 1 人必然要进入某个属相的抽屉。于是那个抽屉里就会从 2 个人变成 3 个人——这就是“至少有 3 人属相相同”。",
        "hint": "Move last one"
    },
    {
        "id": "S7",
        "text": "用一句话总结这个必然性：二十五等于十二乘二再加一。十二个属相每个最多放两人，只能放到二十四；多出的这一人一定会把某个属相推到三人。",
        "hint": "Equation"
    },
    {
        "id": "S8",
        "text": "所以不管怎么分，在 25 个人里一定至少有 3 个人属相相同。这就是抽屉原理的经典用法。",
        "hint": "Conclusion"
    }
]

class Succession(VoiceoverScene):
    def construct(self):
        # --- Setup Voiceover ---
        if HAS_VOICEOVER:
            self.set_speech_service(GTTSService(lang="zh-CN", global_speed=1.15))
        
        # --- Helper for checking Narration ---
        def get_narr(step_id):
            for n in NARRATION:
                if n["id"] == step_id:
                    return n["text"]
            return ""

        # =====================================================================
        # S1: Intro
        # =====================================================================
        # Visuals: Title + Subtitle
        title = Text("抽屉原理").scale(1.2)
        subtitle = Text("25 人中至少 3 人属相相同").scale(0.8)
        
        title_group = VGroup(title, subtitle).arrange(DOWN, buff=0.5)
        
        with self.voiceover(text=get_narr("S1")):
            self.play(FadeIn(title_group))
            self.wait(1)

        # =====================================================================
        # S2: 12 Drawers (Categories)
        # =====================================================================
        # Transition: Shrink title
        self.play(
            title_group.animate.scale(0.6).to_edge(UP).to_edge(LEFT)
        )

        # Visuals: 12 Rectangles with Labels
        drawer_labels_text = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        drawers = VGroup()
        
        # Layout: 2 rows of 6
        # Create individual drawer units
        for i in range(12):
            rect = RoundedRectangle(corner_radius=0.1, height=1.5, width=1.2, color=WHITE)
            # NOTE: Text strictly without font parameter
            label = Text(drawer_labels_text[i]).scale(0.5)
            label.next_to(rect, UP, buff=0.1)
            drawer_unit = VGroup(rect, label)
            drawers.add(drawer_unit)
            
        # Arrange in grid
        drawers.arrange_in_grid(rows=2, cols=6, buff=0.3)
        drawers.shift(DOWN * 0.5 + RIGHT * 1.5)  # Move slightly right to leave space for dots

        with self.voiceover(text=get_narr("S2")):
            self.play(Create(drawers), run_time=3)
            explanation_s2 = Text("抽屉：12 个属相").scale(0.6).next_to(title_group, DOWN, aligned_edge=LEFT)
            self.play(FadeIn(explanation_s2))

        # =====================================================================
        # S3: 25 People (Dots)
        # =====================================================================
        # Visuals: 25 Dots on the left
        people = VGroup(*[Dot(color="#4CC9F0", radius=0.12) for _ in range(25)])
        people.arrange_in_grid(rows=5, cols=5, buff=0.15)
        people.to_edge(LEFT, buff=1.0)
        people.shift(DOWN * 0.5)

        people_label = Text("物品：25 个人").scale(0.6).next_to(people, UP, buff=0.3)

        with self.voiceover(text=get_narr("S3")):
            self.play(ShowIncreasingSubsets(people), run_time=2)
            self.play(FadeIn(people_label))
            self.wait(0.5)

        # =====================================================================
        # S4: Distribute 24 People (2 per drawer)
        # =====================================================================
        # Logic: Move first 24 dots to the drawers.
        # The slots in each drawer: [LEFT_SIDE, RIGHT_SIDE] relative to drawer center?
        # Or maybe UP/DOWN. Let's do UP/DOWN inside the rect to be safe.
        
        distribute_text_1 = Text("假设每个属相最多 2 人").scale(0.5)
        distribute_text_2 = Text("先放入 24 人：每个抽屉 2 人").scale(0.5)
        distribute_group = VGroup(distribute_text_1, distribute_text_2).arrange(DOWN, aligned_edge=LEFT)
        distribute_group.next_to(explanation_s2, DOWN, aligned_edge=LEFT)

        with self.voiceover(text=get_narr("S4")):
            self.play(FadeIn(distribute_group))
            
            animations = []
            # We process 24 dots
            for i in range(24):
                drawer_index = i % 12
                # Determine position inside drawer
                # Even index -> Left/Top, Odd index -> Right/Bottom? 
                # Let's put them side-by-side inside the drawer width
                # Drawer width is 1.2. 
                offset_x = -0.3 if (i // 12) == 0 else 0.3 # This logic is wrong for "filling up".
                # We want 2 dots per drawer.
                # The first time we visit a drawer (i < 12), put it Left.
                # The second time we visit a drawer (12 <= i < 24), put it Right.
                
                target_drawer_rect = drawers[drawer_index][0]
                
                # Calculate position
                is_second_dot = (i >= 12)
                offset = RIGHT * 0.25 if is_second_dot else LEFT * 0.25
                target_pos = target_drawer_rect.get_center() + offset
                
                # Create animation
                anim = people[i].animate.move_to(target_pos)
                animations.append(anim)
            
            # Play animations in batches for better rhythm
            self.play(AnimationGroup(*animations, lag_ratio=0.08), run_time=5)
            
            # Flash drawers to confirm they are "full" (visually)
            self.play(
               *[Flash(d[0], color=YELLOW, line_length=0.1, flash_radius=0.7, run_time=0.5) for d in drawers]
            )

        # =====================================================================
        # S5: Emphasize the last one
        # =====================================================================
        last_person = people[24]
        
        with self.voiceover(text=get_narr("S5")):
            self.play(
                last_person.animate.scale(1.5).set_color("#EF476F")
            )
            self.play(Indicate(last_person))
            
            remain_text = Text("还剩 1 人").scale(0.5).next_to(last_person, UP)
            self.play(Write(remain_text))
            self.wait(1)

        # =====================================================================
        # S6: Move to a drawer -> 3 people
        # =====================================================================
        # Target: Drawer 0 (The first one, for simplicity)
        target_drawer_idx = 0
        target_drawer_rect = drawers[target_drawer_idx][0]
        # Position: Center, slightly above the other two or overlapping
        # Let's put it UP relative to center to form a triangle shape
        final_pos = target_drawer_rect.get_center() + UP * 0.3

        with self.voiceover(text=get_narr("S6")):
            # Move the dot
            self.play(
                last_person.animate.move_to(final_pos),
                FadeOut(remain_text)
            )
            
            # Highlight the drawer
            highlight_box = SurroundingRectangle(target_drawer_rect, color="#FFD166", buff=0.1, stroke_width=6)
            at_least_3_text = Text("至少 3 人").scale(0.5).next_to(highlight_box, DOWN)
            
            self.play(
                Create(highlight_box),
                Write(at_least_3_text)
            )
            self.wait(1)

        # =====================================================================
        # S7: Equation
        # =====================================================================
        # Formula: 25 = 12 * 2 + 1
        equation = MathTex(r"25 = 12 \cdot 2 + 1").scale(1.2)
        equation.to_edge(DOWN, buff=1.0)
        
        explanation_s7 = Text("多出的 1 人必挤进某个属相").scale(0.6)
        explanation_s7.next_to(equation, DOWN, buff=0.3)

        with self.voiceover(text=get_narr("S7")):
            self.play(Write(equation))
            self.play(FadeIn(explanation_s7))
            self.wait(2)

        # =====================================================================
        # S8: Conclusion
        # =====================================================================
        final_conclusion = Text("因此至少有一个属相有 3 个人").scale(0.9).set_color(YELLOW)
        # Overlay on screen center, slightly separate background
        bg_rect = BackgroundRectangle(final_conclusion, fill_opacity=0.8, buff=0.2)
        final_group = VGroup(bg_rect, final_conclusion).move_to(ORIGIN)

        with self.voiceover(text=get_narr("S8")):
            self.play(FadeIn(final_group))
            self.wait(3)
        
        # Fade out everything
        self.play(FadeOut(Group(*self.mobjects)))
        self.wait(0.5)

# To render this scene:
# manim -pqh succession.py Succession
