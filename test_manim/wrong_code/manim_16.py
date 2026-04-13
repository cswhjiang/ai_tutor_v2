from manim import *
import math

# --- Optional TTS Support ---
# If manim_voiceover is installed, it will generate audio.
# If not, it falls back to a silent run with wait times.
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    VOICEOVER_AVAILABLE = True
except ImportError:
    VOICEOVER_AVAILABLE = False
    # Fallback mock class to prevent errors
    class VoiceoverScene(Scene):
        def set_speech_service(self, service): pass
        def voiceover(self, text=None):
            class Context:
                def __enter__(ctx): return ctx
                def __exit__(ctx, exc_type, exc_val, exc_tb): pass
            return Context()

    class GTTSService:
        def __init__(self, lang="zh-CN"): pass

# --- Narration Script (Aligned with Storyboard) ---
NARRATION = [
    {
        "id": "S1",
        "text": "如果把25个人放在一起，不用知道他们具体属相，你能保证：至少会有多少人属相相同吗？",
        "duration": 7
    },
    {
        "id": "S2",
        "text": "在传统文化里，属相一共有12种：鼠牛虎兔龙蛇马羊猴鸡狗猪。每个人按出生年份，只会对应其中一种，也就是说，这是把人分成12个类别。",
        "duration": 10
    },
    {
        "id": "S3",
        "text": "这类问题用到一个经典工具：抽屉原理。直觉版是：物体比抽屉多，总有一个抽屉会被挤得更满。比如12个盒子里先平均放2个，已经放了24个，还剩下的那个球，不管放哪儿，都会让某个盒子变成3个。",
        "duration": 14
    },
    {
        "id": "S4",
        "text": "正式一点说：把n个物体放进m个抽屉里，至少有一个抽屉里不少于上取整n除以m个。等价写法是：n等于q乘m加余数r；只要余数r大于0，就一定有一个抽屉会达到q加1个。",
        "duration": 14
    },
    {
        "id": "S5",
        "text": "回到题目：抽屉就是12种生肖，物体就是25个人。每个人必然且只能属于一个生肖类别，所以完全符合抽屉原理的使用条件。",
        "duration": 10
    },
    {
        "id": "S6",
        "text": "现在算一算：25除以12等于2余1，也就是25等于12乘2加1。意思是：就算每个生肖都先分到2个人，也只能放下24个人，还剩下1个人必须落到某个生肖里，于是至少有一个生肖会有3个人。",
        "duration": 15
    },
    {
        "id": "S7",
        "text": "注意这里说的是‘至少3人’：这是无论怎么分都躲不开的最低保证。实际情况下，同属相的人可能更多，但一定能保证出现3个同属相。",
        "duration": 10
    },
    {
        "id": "S8",
        "text": "最后送一个可迁移的结论：只要有N个对象、分成S类，就能保证至少有N除以S向上取整，也就是⌈N/S⌉个落在同一类。本题就是⌈25/12⌉等于3。以后遇到‘同月份、同分组’这类问题，也能用同样的思路秒解。",
        "duration": 15
    }
]

class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # --- Setup Voiceover ---
        if VOICEOVER_AVAILABLE:
            self.set_speech_service(GTTSService(lang="zh-CN"))

        # --- Helper for getting text ---
        def get_text(sid):
            for item in NARRATION:
                if item["id"] == sid:
                    return item["text"]
            return ""

        # =========================================================
        # S1: 开场设问
        # =========================================================
        
        # Visuals
        title = Text("25个人中，至少有多少人属相相同？", font_size=40)
        title.to_edge(UP, buff=1.0)
        
        # Create simplified "people" icons (just dots/circles)
        people_group = VGroup(*[Circle(radius=0.15, color=WHITE, fill_opacity=1) for _ in range(25)])
        people_group.arrange_in_grid(rows=5, cols=5, buff=0.2)
        people_group.move_to(ORIGIN)
        
        self.play(Write(title))
        self.play(FadeIn(people_group, lag_ratio=0.05))
        
        with self.voiceover(text=get_text("S1")):
            self.wait(2)
            # Highlight question mark idea
            q_mark = Text("?", font_size=96, color=YELLOW).move_to(people_group.get_center())
            self.play(people_group.animate.set_opacity(0.3), FadeIn(q_mark))
            self.wait(1)

        self.play(FadeOut(people_group), FadeOut(q_mark), FadeOut(title))

        # =========================================================
        # S2: 生肖背景科普
        # =========================================================
        
        # Create Zodiac labels
        zodiac_names = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        zodiac_group = VGroup()
        for name in zodiac_names:
            # Box
            box = Square(side_length=1.2, color=BLUE)
            # Text
            lbl = Text(name, font_size=32)
            zodiac_group.add(VGroup(box, lbl))
        
        zodiac_group.arrange_in_grid(rows=2, cols=6, buff=0.2)
        
        classification_text = Text("12生肖 = 12个类别", font_size=36, color=YELLOW)
        classification_text.to_edge(UP)

        with self.voiceover(text=get_text("S2")):
            self.play(Create(zodiac_group, lag_ratio=0.1))
            self.play(Write(classification_text))
            self.wait(2)

        self.play(FadeOut(classification_text), FadeOut(zodiac_group))

        # =========================================================
        # S3: 抽屉原理直觉
        # =========================================================
        
        # Setup boxes again (generic drawers)
        drawers = VGroup(*[Square(side_length=1.0, color=WHITE) for _ in range(12)])
        drawers.arrange(RIGHT, buff=0.1)
        drawers.shift(DOWN * 1)
        
        # Setup 25 small balls
        balls = VGroup(*[Dot(radius=0.08, color=YELLOW) for _ in range(25)])
        balls.arrange(RIGHT, buff=0.05)
        balls.move_to(UP * 2)
        
        principle_title = Text("抽屉原理（鸽巢原理）", font_size=40).to_edge(UP)

        with self.voiceover(text=get_text("S3")):
            self.play(Write(principle_title))
            self.play(Create(drawers), FadeIn(balls))
            
            # Animation: Distribute 24 balls first (2 per drawer)
            anims = []
            for i in range(24):
                drawer_index = i % 12
                target_pos = drawers[drawer_index].get_center() + 
                             (LEFT * 0.25 if (i // 12) == 0 else RIGHT * 0.25)
                anims.append(balls[i].animate.move_to(target_pos))
            
            self.play(AnimationGroup(*anims, lag_ratio=0.05, run_time=3))
            
            # The 25th ball
            last_ball = balls[24]
            # Highlight it
            self.play(Indicate(last_ball, scale_factor=2))
            # Move to the first drawer (arbitrary choice)
            target_pos = drawers[0].get_center() + UP * 0.3
            self.play(last_ball.animate.move_to(target_pos))
            
            # Highlight the "full" drawer
            self.play(Indicate(drawers[0], color=RED))
            self.wait(1)

        self.play(FadeOut(drawers), FadeOut(balls), FadeOut(principle_title))

        # =========================================================
        # S4: 正式表述 & 公式
        # =========================================================
        
        formula_1 = MathTex(r"\lceil n / m \rceil")
        desc_1 = Text("至少有一个抽屉数量 ≥ ")
        group_1 = VGroup(desc_1, formula_1).arrange(RIGHT)
        
        formula_2 = MathTex(r"n = q \cdot m + r \quad (r > 0)")
        desc_2 = Text("结论：至少有一个抽屉 ≥ ")
        formula_2b = MathTex(r"q + 1")
        group_2 = VGroup(desc_2, formula_2b).arrange(RIGHT)
        
        everything = VGroup(group_1, formula_2, group_2).arrange(DOWN, buff=0.8)

        with self.voiceover(text=get_text("S4")):
            self.play(Write(group_1))
            self.play(Indicate(formula_1))
            self.wait(1)
            self.play(Write(formula_2))
            self.wait(1)
            self.play(Write(group_2))
            self.play(Indicate(formula_2b, color=YELLOW))
            self.wait(2)

        self.play(FadeOut(everything))

        # =========================================================
        # S5 & S6: 建模与计算
        # =========================================================
        
        # Visuals: Left (Model), Right (Math)
        
        # 1. Model Text
        model_t1 = Text("抽屉 = 12生肖", font_size=32, color=BLUE)
        model_t2 = Text("物体 = 25个人", font_size=32, color=YELLOW)
        model_group = VGroup(model_t1, model_t2).arrange(DOWN, aligned_edge=LEFT)
        model_group.to_edge(LEFT, buff=1)
        
        # 2. Math Calculation
        calc_eq1 = MathTex(r"25 \div 12 = 2 \dots 1")
        calc_eq2 = MathTex(r"25 = 12 \times 2 + 1")
        calc_group = VGroup(calc_eq1, calc_eq2).arrange(DOWN, aligned_edge=LEFT)
        calc_group.next_to(model_group, RIGHT, buff=2)
        
        # 3. Conclusion Box
        res_text = Text("至少有一类人数 ≥ ")
        res_math = MathTex(r"2 + 1 = 3")
        conclusion_group = VGroup(res_text, res_math).arrange(RIGHT)
        frame = SurroundingRectangle(conclusion_group, color=YELLOW, buff=0.2)
        final_res = VGroup(conclusion_group, frame).move_to(DOWN * 2)

        # Prepare Animation for S5
        with self.voiceover(text=get_text("S5")):
            self.play(Write(model_t1))
            self.play(Write(model_t2))
            self.wait(2)

        # Prepare Animation for S6
        with self.voiceover(text=get_text("S6")):
            self.play(Write(calc_eq1))
            self.wait(1)
            self.play(TransformMatchingTex(calc_eq1.copy(), calc_eq2))
            self.wait(2)
            
            # Visualize the logic again briefly using small icons below
            # 12 boxes (small)
            small_boxes = VGroup(*[Square(side_length=0.5, color=BLUE) for _ in range(12)]).arrange(RIGHT, buff=0.1)
            small_boxes.move_to(UP * 0.5)
            self.play(FadeIn(small_boxes))
            
            # Text: "Each has 2"
            two_txt = MathTex("2").scale(0.8)
            twos = VGroup(*[two_txt.copy().move_to(b.get_center()) for b in small_boxes])
            self.play(Write(twos))
            
            # The "+1"
            plus_one = MathTex("+1", color=RED).scale(0.8)
            plus_one.next_to(small_boxes[0], UP)
            self.play(FadeIn(plus_one))
            self.play(plus_one.animate.move_to(small_boxes[0].get_center() + UP*0.2))
            
            # Show final conclusion
            self.play(Write(final_res))
            self.wait(2)

        self.play(FadeOut(Group(model_group, calc_group, final_res, small_boxes, twos, plus_one, calc_eq1, calc_eq2)))

        # =========================================================
        # S7: 澄清误区
        # =========================================================
        
        warn_title = Text("注意：保证下界", color=RED, font_size=48).to_edge(UP)
        
        # Comparison
        col1 = VGroup(
            Text("最少情况", color=YELLOW),
            MathTex("3"),
            Text("一定发生")
        ).arrange(DOWN)
        
        col2 = VGroup(
            Text("可能情况"),
            MathTex("4, 5, \dots"),
            Text("也许发生")
        ).arrange(DOWN)
        
        comp_group = VGroup(col1, col2).arrange(RIGHT, buff=3)

        with self.voiceover(text=get_text("S7")):
            self.play(Write(warn_title))
            self.play(FadeIn(comp_group, shift=UP))
            self.play(Indicate(col1[1], scale_factor=1.5, color=RED))
            self.wait(2)

        self.play(FadeOut(warn_title), FadeOut(comp_group))

        # =========================================================
        # S8: 推广彩蛋
        # =========================================================
        
        gen_title = Text("通用公式", font_size=48).to_edge(UP)
        
        gen_eq = MathTex(r"\lceil N / S \rceil")
        gen_desc = Text("N个对象，S个分类").next_to(gen_eq, UP)
        
        # Example
        ex_eq = MathTex(r"\lceil 25 / 12 \rceil = 3")
        ex_desc = Text("本题：").next_to(ex_eq, LEFT)
        ex_group = VGroup(ex_desc, ex_eq).arrange(RIGHT)
        
        final_stack = VGroup(gen_desc, gen_eq, ex_group).arrange(DOWN, buff=1)

        with self.voiceover(text=get_text("S8")):
            self.play(Write(gen_title))
            self.play(Write(gen_desc), Write(gen_eq))
            self.wait(1)
            self.play(FadeIn(ex_group, shift=UP))
            self.play(Circumscribe(ex_eq))
            self.wait(3)

        # End scene
        self.play(FadeOut(Group(gen_title, final_stack)))
        self.wait(1)
