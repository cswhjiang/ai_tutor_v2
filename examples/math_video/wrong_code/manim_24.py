from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.bytedance import ByteDanceService

# --- 字体配置 helper ---
import platform
def get_cjk_font_by_platform():
    if platform.system() == "Windows":
        return "Microsoft YaHei"
    elif platform.system() == "Darwin":
        return "PingFang SC"
    else:
        return "Noto Sans CJK SC"

CJK_FONT = get_cjk_font_by_platform()

class DifferenceMultipleProblem(VoiceoverScene):
    def construct(self):
        # 设置语音服务
        self.set_speech_service(ByteDanceService())

        # --- S01: 复述问题与已知条件 ---
        # 画面布局：上方标题，左侧题干
        title = Text("差倍问题：桌子和椅子各多少元？", font=CJK_FONT, font_size=40, weight=BOLD)
        title.to_edge(UP)

        q_line1 = Text("已知：桌子价钱是椅子的 10 倍", font=CJK_FONT, font_size=32)
        q_line2 = Text("且：桌子比椅子多 288 元", font=CJK_FONT, font_size=32)
        q_line3 = Text("求：桌子、椅子各多少元？", font=CJK_FONT, font_size=32)

        question_group = VGroup(q_line1, q_line2, q_line3).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        question_group.to_edge(LEFT, buff=1.0).shift(UP*0.5)

        with self.voiceover(text="这道题是典型的差倍问题：桌子是椅子的十倍，而且桌子比椅子贵二百八十八元，问两者各多少钱。"):
            self.play(Write(title))
            self.play(FadeIn(question_group, shift=RIGHT))
        self.wait(0.5)

        # --- S02: 建立“份数”模型 ---
        # 左侧保留题干，右侧建立条形图
        
        # 文字说明
        model_text_1 = Text("把椅子看作 1 份", font=CJK_FONT, font_size=30)
        model_text_2 = Text("桌子就是 10 份", font=CJK_FONT, font_size=30)
        model_text_group = VGroup(model_text_1, model_text_2).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        model_text_group.next_to(question_group, DOWN, buff=1.0).align_to(question_group, LEFT)

        # 条形图绘制
        # 椅子：1个方块
        chair_block = Square(side_length=0.6, fill_opacity=0.8, fill_color=BLUE, stroke_width=2)
        chair_label = Text("椅子 (1份)", font=CJK_FONT, font_size=24).next_to(chair_block, LEFT)
        
        # 桌子：10个方块
        table_blocks = VGroup(*[Square(side_length=0.6, fill_opacity=0.8, fill_color=ORANGE, stroke_width=2) for _ in range(10)])
        table_blocks.arrange(RIGHT, buff=0)
        table_label = Text("桌子 (10份)", font=CJK_FONT, font_size=24).next_to(table_blocks, LEFT)

        diagram_group = VGroup(VGroup(chair_label, chair_block), VGroup(table_label, table_blocks))
        diagram_group.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        diagram_group.to_edge(RIGHT, buff=1.0).shift(UP*0.5)

        with self.voiceover(text="先用份数来建模：把椅子当作一份，那么桌子就是十份。这样倍数关系就变成了直观的十个小格对一个小格。"):
            self.play(Write(model_text_group))
            self.play(DrawBorderThenFill(chair_block), Write(chair_label))
            self.play(DrawBorderThenFill(table_blocks), Write(table_label))
        self.wait(0.5)

        # --- S03: 强调“差”对应的份数 ---
        # 在桌子10格中，高亮除去与椅子同样的1格，剩余9格
        
        # 复制一份 table blocks 用于操作颜色
        diff_brace = Brace(table_blocks[1:], UP)
        diff_text = Text("差 = 9份", font=CJK_FONT, font_size=28, color=YELLOW).next_to(diff_brace, UP)
        
        # 公式推导
        calc_diff_group = VGroup(
            Text("桌子比椅子多：", font=CJK_FONT, font_size=30),
            MathTex(r"10 - 1 = 9"),
            Text("（份）", font=CJK_FONT, font_size=30)
        ).arrange(RIGHT, buff=0.1)
        calc_diff_group.next_to(model_text_group, DOWN, buff=0.5).align_to(model_text_group, LEFT)

        with self.voiceover(text="桌子比椅子多的，就是十份减去一份，剩下九份。题目给出的二百八十八元，正对应这九份的价钱。"):
            self.play(Indicate(table_blocks[1:], color=YELLOW, scale_factor=1.05))
            self.play(GrowFromCenter(diff_brace), Write(diff_text))
            self.play(Write(calc_diff_group))
        self.wait(0.5)

        # --- S04: 建立等量关系 ---
        # 9份对应288元
        
        eq_text_group = VGroup(
            Text("已知：", font=CJK_FONT, font_size=30),
            Text("9 份", font=CJK_FONT, font_size=30, color=YELLOW, weight=BOLD),
            Text("对应", font=CJK_FONT, font_size=30),
            MathTex(r"288"),
            Text("元", font=CJK_FONT, font_size=30)
        ).arrange(RIGHT, buff=0.1)
        eq_text_group.next_to(calc_diff_group, DOWN, buff=0.5).align_to(calc_diff_group, LEFT)

        diff_value_label = MathTex(r"= 288", color=YELLOW).next_to(table_blocks, RIGHT)
        diff_unit = Text("元", font=CJK_FONT, font_size=24, color=YELLOW).next_to(diff_value_label, RIGHT, buff=0.1)
        
        # 箭头指向
        arrow = Arrow(start=diff_text.get_right(), end=diff_value_label.get_top(), color=YELLOW, buff=0.1)

        with self.voiceover(text="把信息对齐：九份的总价就是二百八十八元。接下来只要把二百八十八平均分成九份，就能得到一份多少钱。"):
            self.play(Write(eq_text_group))
            self.play(Write(diff_value_label), Write(diff_unit))
            self.play(Create(arrow))
        self.wait(0.5)

        # --- Clean up for calculation scene ---
        self.play(
            FadeOut(question_group), 
            FadeOut(model_text_group),
            FadeOut(calc_diff_group),
            FadeOut(eq_text_group),
            FadeOut(arrow),
            diagram_group.animate.to_edge(UP).scale(0.8),
            diff_brace.animate.shift(UP*1.5 + RIGHT*0.5).scale(0.8), # 简单调整位置
            diff_text.animate.shift(UP*1.5 + RIGHT*0.5).scale(0.8),
            diff_value_label.animate.shift(UP*1.5 + LEFT*0.3).scale(0.8),
            diff_unit.animate.shift(UP*1.5 + LEFT*0.3).scale(0.8)
        )

        # --- S05: 计算1份 ---
        # 1份 = 288 / 9 = 32
        
        calc_one_unit = VGroup(
            Text("1 份 = ", font=CJK_FONT, font_size=40),
            MathTex(r"288 \div 9 = 32", font_size=50),
            Text("元", font=CJK_FONT, font_size=40)
        ).arrange(RIGHT, buff=0.2)
        calc_one_unit.move_to(ORIGIN)

        with self.voiceover(text="计算一份的价钱：二百八十八除以九等于三十二。所以，椅子这一份就是三十二元。"):
            self.play(Write(calc_one_unit))
            # 视觉演示：每个方格显示32
            nums = VGroup()
            # Chair
            c_num = MathTex(r"32", font_size=20, color=WHITE).move_to(chair_block)
            nums.add(c_num)
            # Table
            for block in table_blocks:
                t_num = MathTex(r"32", font_size=20, color=WHITE).move_to(block)
                nums.add(t_num)
            
            self.play(Write(nums), run_time=2)
        self.wait(0.5)

        # --- S06: 得出最终结果 ---
        
        self.play(calc_one_unit.animate.to_edge(UP, buff=2.0).scale(0.7))

        res_chair = VGroup(
            Text("椅子：", font=CJK_FONT, font_size=36),
            MathTex(r"32", font_size=48),
            Text("元", font=CJK_FONT, font_size=36)
        ).arrange(RIGHT, buff=0.15)

        res_table = VGroup(
            Text("桌子：", font=CJK_FONT, font_size=36),
            MathTex(r"10 \times 32 = 320", font_size=48),
            Text("元", font=CJK_FONT, font_size=36)
        ).arrange(RIGHT, buff=0.15)

        final_res_group = VGroup(res_chair, res_table).arrange(RIGHT, buff=1.0)
        final_res_group.next_to(calc_one_unit, DOWN, buff=1.0)

        final_box = SurroundingRectangle(final_res_group, color=GREEN, buff=0.3)

        with self.voiceover(text="椅子是一份，所以椅子是三十二元。桌子是十份，用十乘三十二，得到三百二十元。"):
            self.play(Write(res_chair))
            self.play(Write(res_table))
            self.play(Create(final_box))
        self.wait(1.0)

        # --- S07: 验算 ---
        
        self.play(FadeOut(calc_one_unit), FadeOut(diagram_group), FadeOut(diff_brace), FadeOut(diff_text), FadeOut(diff_value_label), FadeOut(diff_unit), FadeOut(nums))
        self.play(final_res_group.animate.to_edge(UP), final_box.animate.to_edge(UP))

        check_title = Text("验算", font=CJK_FONT, font_size=40, weight=BOLD).next_to(final_box, DOWN, buff=0.8)
        
        check_1 = MathTex(r"320 - 32 = 288", font_size=48)
        check_2 = MathTex(r"320 \div 32 = 10", font_size=48)
        
        check_group = VGroup(check_1, check_2).arrange(RIGHT, buff=1.5)
        check_group.next_to(check_title, DOWN, buff=0.5)

        check_pass = Text("两条条件都满足", font=CJK_FONT, font_size=34, color=GREEN).next_to(check_group, DOWN, buff=0.5)

        with self.voiceover(text="验算一下：三百二十减三十二等于二百八十八；三百二十除以三十二等于十。两条条件都满足。"):
            self.play(Write(check_title))
            self.play(Write(check_1))
            self.play(Write(check_2))
            self.play(Write(check_pass))
        self.wait(1.0)

        # --- S08: 总结 ---
        
        self.play(FadeOut(Group(*self.mobjects)))

        summary_title = Text("方法总结（差倍问题）", font=CJK_FONT, font_size=44, weight=BOLD)
        summary_title.to_edge(UP, buff=1.0)

        s_p1 = Text("1) 小的看作 1 份，大的是 n 份", font=CJK_FONT, font_size=32)
        s_p2 = Text("2) 差 = (n-1) 份 → 求 1 份 = 差 ÷ (n-1)", font=CJK_FONT, font_size=32)
        s_p3 = Text("3) 再求 n 份的价钱", font=CJK_FONT, font_size=32)

        summary_points = VGroup(s_p1, s_p2, s_p3).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        summary_points.next_to(summary_title, DOWN, buff=0.8)

        tip = Text("制作提示：中文用 Text，公式用 MathTex（只写数字和符号）", font=CJK_FONT, font_size=24, color=GRAY)
        tip.to_corner(DR)

        with self.voiceover(text="总结一下：差倍问题先用份数建模，把小的当一份，大的是n份；差就是n减一份，用差除以份数差求出一份，再求出n份。做动画时记得：中文用Text，MathTex里只放数字和数学符号。"):
            self.play(Write(summary_title))
            self.play(FadeIn(summary_points, shift=UP))
            self.play(Write(tip))
        
        self.wait(2)
