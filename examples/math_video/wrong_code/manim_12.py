from manim import *
import random

# --- TTS Configuration ---
# 尝试导入 manim_voiceover，如果失败则使用伪造类以保证代码可运行
USE_TTS = False
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    USE_TTS = True
except ImportError:
    # Fallback if library is missing
    class VoiceoverScene(Scene):
        def voiceover(self, text=None, **kwargs):
            class Context:
                def __enter__(ctx):
                    # 根据字数估算时长，中文约每秒4-5字
                    duration = len(text) / 4.5 if text else 1.0
                    return duration
                def __exit__(ctx, exc_type, exc_value, traceback):
                    pass
            return Context()
        def set_speech_service(self, service):
            pass

    class GTTSService:
        def __init__(self, lang="zh-CN", **kwargs): pass

# --- 旁白脚本配置 ---
NARRATION = [
    {
        "id": "S1",
        "text": "如果我说，随便找来25个人，不用统计、不用抽样，你就能保证：至少有3个人属相相同。你信吗？"
    },
    {
        "id": "S2",
        "text": "先把前提说清楚：属相按十二生肖分成12类。每个人一定、也只能属于其中一个属相。"
    },
    {
        "id": "S3",
        "text": "这就是典型的抽屉原理：把25个人当作25个物品，把12个生肖当作12个抽屉。每个人必须放进且只能放进自己属相对应的那个抽屉。"
    },
    {
        "id": "S4",
        "text": "现在做个最极端的设想：如果我们想尽量避免出现“某个属相有3个人”，最好的办法就是平均分，让每个属相最多放2个人。那12个抽屉最多能装下多少人？12乘2等于24。"
    },
    {
        "id": "S5",
        "text": "问题来了：第25个人也必须属于这12个属相之一。可前24个人已经把每个抽屉都放到了2个人。现在再来一个人，他不可能创造“第13个属相”，只能挤进某个抽屉——于是那个抽屉立刻从2变成3。"
    },
    {
        "id": "S6",
        "text": "所以结论不是“可能”，而是“必然”：25个人里，至少有3个人属相相同。"
    },
    {
        "id": "S7",
        "text": "用公式一句话总结：把n个物品放进m个抽屉，必有一个抽屉至少有向上取整的n除以m个。本题n等于25，m等于12，所以25除以12向上取整等于3。"
    },
    {
        "id": "S8",
        "text": "留个小问题：如果有37个人，至少会有几个人属相相同？用同一个公式就能秒算。"
    }
]

class PigeonholePrinciple(VoiceoverScene):
    def construct(self):
        # 1. 设置 TTS 服务
        if USE_TTS:
            self.set_speech_service(GTTSService(lang="zh-CN"))

        # 字体回退列表，防止中文乱码
        # Manim Community 默认尝试寻找系统字体，这里不强制指定 font 参数以增加兼容性
        # 若必须指定，建议使用 font="SimHei" 或 font="Microsoft YaHei"
        
        # --- Scene 1: 开场钩子 ---
        # 画面：左侧25个小人，右侧12个抽屉
        title = Text("25人中至少3人属相相同？", font_size=36, weight=BOLD).to_edge(UP)
        subtitle = Text("必然事件", font_size=24, color=YELLOW).next_to(title, DOWN)
        
        people_group = VGroup(*[Circle(radius=0.15, color=BLUE, fill_opacity=1) for _ in range(25)])
        people_group.arrange_in_grid(rows=5, cols=5, buff=0.1).to_edge(LEFT, buff=1.5)
        
        drawers_outline = VGroup(*[Square(side_length=0.8, color=WHITE) for _ in range(12)])
        drawers_outline.arrange_in_grid(rows=4, cols=3, buff=0.2).to_edge(RIGHT, buff=1.5)
        
        self.play(Write(title))
        
        with self.voiceover(text=NARRATION[0]["text"]):
            self.play(
                FadeIn(people_group, shift=RIGHT),
                FadeIn(drawers_outline, shift=LEFT),
                run_time=2
            )
            self.play(Write(subtitle))
            self.wait(1)

        self.play(FadeOut(people_group), FadeOut(drawers_outline), FadeOut(subtitle))

        # --- Scene 2: 前提澄清 ---
        # 画面：12生肖图标/名字
        zodiac_names = [
            "鼠", "牛", "虎", "兔", 
            "龙", "蛇", "马", "羊", 
            "猴", "鸡", "狗", "猪"
        ]
        zodiac_texts = VGroup(*[Text(name, font_size=32) for name in zodiac_names])
        zodiac_texts.arrange_in_grid(rows=3, cols=4, buff=1.5)
        
        # 加个框表示分类
        rects = VGroup(*[SurroundingRectangle(t, color=BLUE, buff=0.3) for t in zodiac_texts])
        
        rule_text = Text("每个人必属于且只属于一类", font_size=24, color=YELLOW).to_edge(DOWN)

        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(LaggedStart(FadeIn(zodiac_texts), Create(rects), lag_ratio=0.1))
            self.play(Write(rule_text))
            self.wait(1)

        self.play(FadeOut(zodiac_texts), FadeOut(rects), FadeOut(rule_text))

        # --- Scene 3: 建立抽屉模型 ---
        # 画面：25个人 = 物品， 12生肖 = 抽屉
        left_label = VGroup(
            Text("25个人", font_size=48),
            MathTex(r"\downarrow"),
            Text("25个物品", font_size=36, color=BLUE)
        ).arrange(DOWN).shift(LEFT * 3)

        right_label = VGroup(
            Text("12个生肖", font_size=48),
            MathTex(r"\downarrow"),
            Text("12个抽屉", font_size=36, color=ORANGE)
        ).arrange(DOWN).shift(RIGHT * 3)

        with self.voiceover(text=NARRATION[2]["text"]):
            self.play(Write(left_label[0]), Write(right_label[0]))
            self.wait(0.5)
            self.play(
                TransformFromCopy(left_label[0], left_label[2]),
                Write(left_label[1]),
                TransformFromCopy(right_label[0], right_label[2]),
                Write(right_label[1])
            )
            self.wait(1)

        self.play(FadeOut(left_label), FadeOut(right_label), FadeOut(title))

        # --- Scene 4: 极端构造演示 ---
        # 核心动画：12个抽屉，放入小球
        
        # 创建12个抽屉 (Box + Counter)
        drawers = VGroup()
        counters = VGroup()
        drawer_capacity = [] # List to track count logic internally

        for i in range(12):
            box = Square(side_length=1.5, color=WHITE)
            # 抽屉编号/生肖名 (简略)
            label = Text(zodiac_names[i], font_size=20, color=GRAY).next_to(box, UP, buff=0.1)
            # 计数器
            num = Integer(0, font_size=48, color=YELLOW).move_to(box.get_center())
            
            group = VGroup(box, label, num)
            drawers.add(group)
            counters.add(num)
            drawer_capacity.append(0)

        drawers.arrange_in_grid(rows=3, cols=4, buff=0.5).shift(DOWN * 0.5)
        
        # 总人数计数器
        total_counter_label = Text("已放入人数:", font_size=28).to_corner(UL)
        total_counter_num = Integer(0, font_size=36, color=BLUE).next_to(total_counter_label, RIGHT)
        total_counter_group = VGroup(total_counter_label, total_counter_num)

        # 解释文字
        strategy_text = Text("极端情况：尽可能平均分配", font_size=32, color=ORANGE).next_to(total_counter_group, DOWN, aligned_edge=LEFT)

        self.add(total_counter_group)
        self.play(FadeIn(drawers))
        
        # 动画过程
        with self.voiceover(text=NARRATION[3]["text"]):
            self.play(Write(strategy_text))
            
            # 第一轮：放12个人
            animations1 = []
            for i in range(12):
                drawer_capacity[i] += 1
                # 创建一个小球飞入
                dot = Circle(radius=0.1, color=BLUE, fill_opacity=1)
                dot.move_to(total_counter_num)
                target = drawers[i][0].get_center()
                # 动画：小球飞入 -> 消失 -> 数字+1
                anim = Successession(
                    FadeIn(dot, run_time=0.1),
                    ApplyMethod(dot.move_to, target, run_time=0.3),
                    FadeOut(dot, run_time=0.1),
                    ChangeDecimalToValue(counters[i], drawer_capacity[i]),
                    ChangeDecimalToValue(total_counter_num, i + 1)
                )
                animations1.append(anim)
            
            # 快速播放第一轮
            self.play(LaggedStart(*animations1, lag_ratio=0.1, run_time=3))
            
            # 第二轮：再放12个人 (total 24)
            animations2 = []
            for i in range(12):
                drawer_capacity[i] += 1
                dot = Circle(radius=0.1, color=BLUE, fill_opacity=1)
                dot.move_to(total_counter_num)
                target = drawers[i][0].get_center()
                anim = Successession(
                    FadeIn(dot, run_time=0.1),
                    ApplyMethod(dot.move_to, target, run_time=0.3),
                    FadeOut(dot, run_time=0.1),
                    ChangeDecimalToValue(counters[i], drawer_capacity[i]),
                    ChangeDecimalToValue(total_counter_num, 12 + i + 1)
                )
                animations2.append(anim)

            self.play(LaggedStart(*animations2, lag_ratio=0.1, run_time=3))
            
            # 此时全部是2
            self.wait(0.5)
            check_text = Text("所有抽屉都只有2人", font_size=36, color=RED).move_to(ORIGIN)
            self.play(FadeIn(check_text, run_time=0.5))
            self.wait(1)
            self.play(FadeOut(check_text))

        # --- Scene 5: 第25个人 ---
        with self.voiceover(text=NARRATION[4]["text"]):
            # 创建第25人
            p25 = Circle(radius=0.2, color=RED, fill_opacity=1).move_to(UP * 2.5)
            p25_label = Text("第25人", font_size=24, color=RED).next_to(p25, UP)
            
            self.play(FadeIn(p25), Write(p25_label))
            self.play(ChangeDecimalToValue(total_counter_num, 25))
            
            # 犹豫动画
            self.play(p25.animate.shift(LEFT*0.5), run_time=0.3)
            self.play(p25.animate.shift(RIGHT*1), run_time=0.3)
            self.play(p25.animate.shift(LEFT*0.5), run_time=0.3)
            
            # 随机选一个抽屉 (比如第5个，中间位置视觉好)
            target_idx = 4
            target_drawer = drawers[target_idx]
            target_center = target_drawer[0].get_center()
            
            self.play(p25.animate.move_to(target_center), run_time=0.8)
            self.play(FadeOut(p25), FadeOut(p25_label))
            
            # 数字变3
            drawer_capacity[target_idx] += 1
            new_count = Integer(3, font_size=60, color=RED, weight=BOLD).move_to(target_center)
            
            self.play(
                ReplacementTransform(counters[target_idx], new_count),
                Indicate(target_drawer[0], color=RED, scale_factor=1.2)
            )
            counters[target_idx] = new_count # 更新引用

        # --- Scene 6: 结论 ---
        with self.voiceover(text=NARRATION[5]["text"]):
            # 淡化其他抽屉，高亮目标
            other_drawers = VGroup(*[d for i, d in enumerate(drawers) if i != target_idx])
            self.play(other_drawers.animate.set_opacity(0.3))
            
            conclusion_text = Text("结论：至少3人属相相同", font_size=40, color=YELLOW).to_edge(UP)
            nature_text = Text("（必然发生）", font_size=30, color=WHITE).next_to(conclusion_text, DOWN)
            
            self.play(Write(conclusion_text), FadeIn(nature_text))
            self.wait(2)

        self.play(FadeOut(drawers), FadeOut(total_counter_group), FadeOut(strategy_text), FadeOut(conclusion_text), FadeOut(nature_text), FadeOut(other_drawers), FadeOut(counters[target_idx]))

        # --- Scene 7: 公式压轴 ---
        # 公式：ceil(n/m)
        formula_title = Text("抽屉原理公式", font_size=36, color=BLUE).to_edge(UP)
        
        # 使用 MathTex 组合公式，避免中文进入 MathTex
        # Formula: ceil(n/m)
        f1 = MathTex(r"\left\lceil \frac{n}{m} \right\rceil")
        desc = Text("n个物品，m个抽屉", font_size=24, color=GRAY).next_to(f1, DOWN)
        
        f2_pre = MathTex(r"n=25, m=12")
        f2 = MathTex(r"\left\lceil \frac{25}{12} \right\rceil = 3")
        
        group_math = VGroup(f1, desc, f2_pre, f2).arrange(DOWN, buff=0.8)

        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(Write(formula_title))
            self.play(Write(f1), FadeIn(desc))
            self.wait(1)
            self.play(
                ReplacementTransform(f1.copy(), f2_pre),
                FadeOut(desc)
            )
            self.wait(0.5)
            self.play(Write(f2))
            self.play(Indicate(f2, color=YELLOW))
            self.wait(2)

        self.play(FadeOut(group_math), FadeOut(formula_title))

        # --- Scene 8: 结尾思考 ---
        q_title = Text("思考题", font_size=40, color=YELLOW).to_edge(UP, buff=2)
        q_text = Text("如果有 37 个人，至少有几人属相相同？", font_size=32).next_to(q_title, DOWN, buff=0.5)
        
        hint_group = VGroup(
            Text("提示：", font_size=28, color=GRAY),
            MathTex(r"\left\lceil \frac{37}{12} \right\rceil = ?")
        ).arrange(RIGHT).next_to(q_text, DOWN, buff=1)

        with self.voiceover(text=NARRATION[7]["text"]):
            self.play(Write(q_title))
            self.play(Write(q_text))
            self.play(FadeIn(hint_group))
            self.wait(3)
        
        # End
        self.play(FadeOut(q_title), FadeOut(q_text), FadeOut(hint_group))
        self.wait(1)
