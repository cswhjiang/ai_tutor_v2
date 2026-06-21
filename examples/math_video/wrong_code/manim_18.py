from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# 定义旁白脚本，确保与分镜严格对齐
NARRATION = [
    {
        "id": "S01",
        "text": "25个人里，至少有多少人的属相一定相同？答案听起来像猜谜，但其实只用一个非常经典的数学工具：抽屉原理。",
        "hint": "标题展示"
    },
    {
        "id": "S02",
        "text": "把12个生肖当作12个抽屉，把25个人当作要放进抽屉的25个物体。每个人按自己的属相，必须放进对应的那个抽屉里。",
        "hint": "12个生肖盒子出现"
    },
    {
        "id": "S03",
        "text": "抽屉原理说：如果有n个物体放进m个抽屉，只要n大于m，就一定存在一个抽屉，里面至少有天花板函数n除以m个物体。这里n等于25，m等于12。",
        "hint": "公式展示"
    },
    {
        "id": "S04",
        "text": "先做个极限假设：如果每个生肖都最多只有2个人，那么12个生肖加起来，最多也就12乘2等于24个人。",
        "hint": "24个点放入"
    },
    {
        "id": "S05",
        "text": "但现在有25个人。注意这个分解：25等于12乘2再加1。也就是说，在“每个抽屉最多2人”的情况下只能放到24人，第25个人无论属什么，都必须落进某个生肖抽屉里，把那个抽屉的人数从2推到3。",
        "hint": "第25人导致变色"
    },
    {
        "id": "S06",
        "text": "所以结论是：25个人中，至少有3个人属相相同。注意，这个结论不需要告诉你具体是哪三个，只证明“必然存在”就够了。",
        "hint": "结论总结"
    },
    {
        "id": "S07",
        "text": "如果你用Manim复现这个动画，常见坑是：把VGroup当成带有.box属性的对象去访问，比如drawer点box，会直接触发AttributeError。正确方式是按索引取子对象：drawer等于VGroup(矩形, 文字)，那矩形就是drawer[0]，文字就是drawer[1]。",
        "hint": "代码提示"
    }
]

class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # 设置 TTS 服务
        self.set_speech_service(GTTSService(lang="zh-CN", tld="com"))

        # --- S01: 标题抛出问题 ---
        with self.voiceover(text=NARRATION[0]["text"]):
            title = Text("25个人中至少有多少人属相相同？", font_size=36)
            subtitle = Text("抽屉原理 + 12生肖", font_size=28, color=BLUE).next_to(title, DOWN)
            
            self.play(Write(title), run_time=1.5)
            self.play(FadeIn(subtitle, shift=DOWN), run_time=1)
            self.wait(0.5)
            
            # 标题上移
            header_group = VGroup(title, subtitle)
            self.play(header_group.animate.to_edge(UP).scale(0.8))

        # --- S02: 建立“抽屉=生肖、物体=人”的模型 ---
        zodiacs = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        drawers = VGroup()
        
        # 创建12个生肖盒子，每个是 VGroup(Rectangle, Text)
        # 索引 0: Rectangle, 索引 1: Text
        for name in zodiacs:
            box = Rectangle(width=1.0, height=1.2, color=WHITE)
            label = Text(name, font_size=24).move_to(box.get_center() + DOWN*0.35)
            drawer_unit = VGroup(box, label)
            drawers.add(drawer_unit)
        
        drawers.arrange_in_grid(rows=2, cols=6, buff=0.2)
        drawers.move_to(DOWN * 0.5)

        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(LaggedStart(*[FadeIn(d) for d in drawers], lag_ratio=0.1))
            
            # 映射说明
            map_text_1 = Text("12个生肖 = 12个抽屉", font_size=24, color=YELLOW)
            map_text_2 = Text("25个人 = 25个物体", font_size=24, color=YELLOW)
            map_group = VGroup(map_text_1, map_text_2).arrange(DOWN, aligned_edge=LEFT)
            map_group.to_edge(LEFT).shift(UP*0.5)
            
            self.play(Write(map_group))

        # --- S03: 抽屉原理的标准表述 ---
        with self.voiceover(text=NARRATION[2]["text"]):
            # 清理左侧映射文字，换成原理公式
            self.play(FadeOut(map_group))
            
            # 稍微移动抽屉组给公式腾位置
            self.play(drawers.animate.scale(0.9).to_edge(DOWN, buff=1.0))
            
            formula_tex = MathTex(r"\lceil n/m \rceil", color=BLUE, font_size=48)
            text_principle = Text("抽屉原理核心公式", font_size=24).next_to(formula_tex, UP)
            
            params = MathTex(r"n=25, m=12", font_size=36).next_to(formula_tex, DOWN)
            
            principle_group = VGroup(text_principle, formula_tex, params).arrange(DOWN)
            principle_group.to_edge(UP).shift(DOWN*1.2)
            
            self.play(Write(principle_group))
            self.play(Indicate(formula_tex))

        # --- S04: 用“每个抽屉最多2人”的反证式直观铺垫 ---
        people_dots = VGroup()
        # 准备24个点
        for i in range(12):
            # 这里的 drawers[i] 是 VGroup(box, label)
            # drawers[i][0] 是 Rectangle
            rect = drawers[i][0] 
            
            # 计算两个点的位置
            center = rect.get_center()
            p1 = Dot(point=center + LEFT*0.2 + UP*0.2, color=YELLOW, radius=0.06)
            p2 = Dot(point=center + RIGHT*0.2 + UP*0.2, color=YELLOW, radius=0.06)
            people_dots.add(p1, p2)
            
        with self.voiceover(text=NARRATION[3]["text"]):
            # 移除上方的公式组，腾出空间显示推导
            self.play(FadeOut(principle_group))
            
            assump_text = Text("假设每个生肖最多 2 人", font_size=30, color=YELLOW)
            assump_text.to_edge(UP).shift(DOWN*1.5)
            
            eq_24 = MathTex(r"12 \times 2 = 24").next_to(assump_text, DOWN)
            
            self.play(Write(assump_text))
            self.play(LaggedStart(*[GrowFromCenter(p) for p in people_dots], lag_ratio=0.03))
            self.play(Write(eq_24))

        # --- S05: 第25人出现：必然挤进某个生肖 ---
        with self.voiceover(text=NARRATION[4]["text"]):
            # 定义第25人
            p25 = Dot(color=RED, radius=0.08)
            p25_label = Text("第25人", font_size=20, color=RED).next_to(p25, UP)
            extra_group = VGroup(p25, p25_label).to_edge(LEFT).shift(UP)
            
            self.play(FadeIn(extra_group))
            
            # 推导公式更新
            eq_25 = MathTex(r"25 = 12 \times 2 + 1", color=RED).next_to(eq_24, DOWN)
            self.play(TransformMatchingTex(eq_24.copy(), eq_25))
            
            # 移动到第1个抽屉（鼠）
            target_drawer_index = 0
            target_rect = drawers[target_drawer_index][0] # 索引访问 Rectangle
            target_text = drawers[target_drawer_index][1] # 索引访问 Text
            
            target_pos = target_rect.get_center() + DOWN*0.1
            
            self.play(p25.animate.move_to(target_pos), FadeOut(p25_label))
            
            # 高亮
            self.play(
                target_rect.animate.set_stroke(color=RED, width=6),
                target_text.animate.set_color(RED),
                p25.animate.scale(1.2)
            )

        # --- S06: 落地总结 ---
        with self.voiceover(text=NARRATION[5]["text"]):
            # 清理多余文字
            self.play(FadeOut(assump_text), FadeOut(eq_24))
            
            conclusion_text = Text("结论：至少有 3 人属相相同", font_size=40, color=RED)
            conclusion_text.next_to(eq_25, DOWN, buff=0.8)
            
            sub_conclusion = Text("必然存在", font_size=24, color=GREY).next_to(conclusion_text, DOWN)
            
            self.play(Write(conclusion_text))
            self.play(FadeIn(sub_conclusion))
            self.wait(1)

        # --- S07: 工程彩蛋 (代码提示) ---
        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(
                *[FadeOut(m) for m in self.mobjects], 
                run_time=1
            )
            
            code_title = Text("Manim 代码避坑指南", font_size=32).to_edge(UP)
            
            # 错误示例
            wrong_code = Text("drawer.box", font="Monospace", color=RED)
            cross = Text("×", color=RED, font_size=48).next_to(wrong_code, RIGHT)
            wrong_group = VGroup(wrong_code, cross).shift(LEFT*3 + UP)
            
            # 正确示例
            correct_code_1 = Text("drawer[0]  # Rectangle", font="Monospace", color=GREEN, font_size=24)
            correct_code_2 = Text("drawer[1]  # Text", font="Monospace", color=GREEN, font_size=24)
            check = Text("✓", color=GREEN, font_size=48).next_to(correct_code_1, RIGHT)
            
            correct_group = VGroup(correct_code_1, correct_code_2).arrange(DOWN, aligned_edge=LEFT)
            correct_full = VGroup(correct_group, check).shift(RIGHT*3 + UP)
            
            note = Text("VGroup(Rectangle, Text) 需使用索引访问子对象", font_size=24, color=GREY).next_to(code_title, DOWN, buff=1)
            
            self.play(Write(code_title), FadeIn(note))
            self.play(FadeIn(wrong_group))
            self.wait(0.5)
            self.play(FadeIn(correct_full))
            self.wait(2)
