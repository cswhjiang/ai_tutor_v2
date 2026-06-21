from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.bytedance import ByteDanceService
import math


# 配置中文环境（确保公式不含中文，中文只在Text中）
# 这里的模板配置是标准的，用于处理潜在的中文显示需求，但在本脚本中主要依赖 Text 对象

class ClockOverlapProblem(VoiceoverScene):
    def construct(self):
        # --- 初始化语音服务 ---
        self.set_speech_service(ByteDanceService())

        # --- 场景 1: 开场与问题定义 ---
        # story: 钟表居中，时间显示牌：2:00:00，标题条出现

        # 创建钟表盘面（简化版）
        clock_radius = 2.0
        clock_circle = Circle(radius=clock_radius, color=WHITE)
        clock_nums = VGroup()
        for i in range(12):
            angle = (3 - (i if i != 0 else 12)) * 30 * DEGREES
            num = Text(str(i if i != 0 else 12), font_size=24)
            num.move_to(
                clock_circle.get_center() + 0.85 * clock_radius * np.array([math.cos(angle), math.sin(angle), 0]))
            clock_nums.add(num)

        clock_group = VGroup(clock_circle, clock_nums).shift(DOWN * 0.5)

        # 指针
        # 2:00 -> 分针在12(90度), 时针在2(30度)
        # Manim的角度是逆时针为正，0度在右边。我们需要转换。
        # 12点=90deg, 1点=60deg, 2点=30deg.

        m_hand = Line(ORIGIN, UP * 1.5, color=BLUE, stroke_width=4).move_to(clock_group.get_center(), aligned_edge=DOWN)
        h_hand = Line(ORIGIN, UP * 1.0, color=RED, stroke_width=6).move_to(clock_group.get_center(), aligned_edge=DOWN)
        # 初始位置：2:00
        m_hand.rotate(0, about_point=clock_group.get_center())
        h_hand.rotate(-60 * DEGREES, about_point=clock_group.get_center())  # 12点方向顺时针转60度

        center_dot = Dot(clock_group.get_center(), color=WHITE)

        # 时间显示
        time_label = Text("02:00:00", font_size=36, font="Monospace").next_to(clock_group, UP)

        # 标题
        title = Text("2点后，时针和分针第一次重合的时刻？", font_size=36).to_edge(UP)

        with self.voiceover(
                text="从两点整开始，分针在12，时针在2。接下来分针会追上时针——它们第一次重合到底发生在几点几分几秒？"):
            self.play(FadeIn(clock_group), FadeIn(center_dot), FadeIn(m_hand), FadeIn(h_hand))
            self.play(Write(time_label))
            self.play(Write(title))
            self.wait(1)

        # --- 场景 2: 建立角度直觉（初始差角） ---
        # story: 叠加角度环，标注60度

        # 角度标注
        # 12点方向是90度，2点方向是30度。画弧线。
        angle_arc = Arc(
            radius=0.8,
            start_angle=90 * DEGREES,
            angle=-60 * DEGREES,
            color=YELLOW
        ).move_arc_center_to(clock_group.get_center())

        angle_label = MathTex(r"\Delta \theta_0 = 60^\circ", color=YELLOW).next_to(angle_arc, UR, buff=0.1)

        text_s2 = VGroup(
            Text("2:00:00 时：分针=0°", font_size=24),
            Text("时针 = 2×30° = 60°", font_size=24),
            Text("初始差角：60°", font_size=24, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(LEFT).shift(UP)

        with self.voiceover(
                text="先看两点整的夹角。每个小时刻度是30度，时针在2点方向，也就是从12点起算60度。此时是时针领先分针60度。"):
            self.play(Create(angle_arc), Write(angle_label))
            self.play(FadeIn(text_s2))
            self.wait(1)

        # 清理S2的部分文字，保留钟表
        self.play(FadeOut(text_s2), FadeOut(title))

        # --- 场景 3: 计算角速度 ---
        # story: 左侧钟面，右侧卡片写速度

        # 移动钟表到左侧
        clock_full = VGroup(clock_group, m_hand, h_hand, center_dot, angle_arc, angle_label, time_label)

        target_clock_pos = LEFT * 3.5

        card_s3 = VGroup(
            Text("分针角速度", font_size=28, color=BLUE),
            MathTex(r"\omega_m = \frac{360^\circ}{60\,\text{min}} = 6^\circ/\text{min}", color=BLUE),
            Text("时针角速度", font_size=28, color=RED),
            MathTex(r"\omega_h = \frac{360^\circ}{720\,\text{min}} = 0.5^\circ/\text{min}", color=RED)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).to_edge(RIGHT).shift(LEFT * 1)

        with self.voiceover(
                text="接着比较两根指针的转动速度。分针一小时转一圈，所以每分钟6度。时针12小时转一圈，也就是720分钟转360度，因此每分钟0.5度。"):
            self.play(clock_full.animate.scale(0.8).move_to(target_clock_pos))
            self.play(Write(card_s3))
            self.wait(1)

        # --- 场景 4: 相对角速度 ---
        # story: 相对速度公式

        rel_speed_text = Text("相对角速度（追及速度）", font_size=28, color=GREEN)
        rel_speed_math = MathTex(r"\omega_{rel} = \omega_m - \omega_h", font_size=36)
        rel_speed_calc = MathTex(r"= 6 - 0.5 = 5.5^\circ/\text{min}", font_size=36, color=GREEN)

        group_s4 = VGroup(rel_speed_text, rel_speed_math, rel_speed_calc).arrange(DOWN).next_to(card_s3, DOWN, buff=0.8)

        with self.voiceover(
                text="因为两根针都在动，最省事的方法是看相对角速度：分针比时针每分钟多转6减0.5，也就是5.5度。差角就会以每分钟5.5度的速度减少。"):
            self.play(Write(group_s4))
            self.play(Indicate(rel_speed_calc))
            self.wait(1)

        # 清除右侧计算过程，为下一步腾空间
        self.play(FadeOut(card_s3), FadeOut(group_s4))

        # --- 场景 5: 追及时间公式 ---
        # story: t = delta / omega_rel

        calc_group = VGroup(
            MathTex(r"t = \frac{\Delta \theta_0}{\omega_{rel}}"),
            MathTex(r"t = \frac{60}{5.5}"),
            MathTex(r"t = \frac{120}{11} \, \text{min}")
        ).arrange(DOWN, buff=0.5).to_edge(RIGHT).shift(LEFT * 2)

        with self.voiceover(
                text="分针要追上时针，需要补上这60度的差角。而它每分钟能缩小5.5度，所以追及时间就是六十除以五点五，得到一百二十分之十一分钟。"):
            self.play(Write(calc_group[0]))
            self.wait(0.5)
            self.play(TransformMatchingTex(calc_group[0].copy(), calc_group[1]))
            self.wait(0.5)
            self.play(TransformMatchingTex(calc_group[1].copy(), calc_group[2]))
            self.wait(1)

        # --- 场景 6: 分钟转分秒 ---
        # story: 120/11 -> 10 + 10/11 -> 54.55s

        # 我们把上面的公式移上去或者淡出，换成具体的换算
        self.play(FadeOut(calc_group[0]), FadeOut(calc_group[1]))
        self.play(calc_group[2].animate.to_edge(UP).shift(RIGHT * 1))

        convert_steps = VGroup(
            MathTex(r"\frac{120}{11} \, \text{min} = 10 + \frac{10}{11} \, \text{min}"),
            MathTex(r"\frac{10}{11} \, \text{min} = \frac{10}{11} \times 60 \, \text{s}"),
            MathTex(r"= \frac{600}{11} \, \text{s} \approx 54.55 \, \text{s}"),
            Text("结果：10分54.55秒", color=YELLOW, font_size=32)
        ).arrange(DOWN, aligned_edge=LEFT).next_to(calc_group[2], DOWN, buff=0.5)

        with self.voiceover(
                text="把一百二十分之十一分钟换成更直观的分秒：它等于10分钟再加上十除以十一分钟。十除以十一分钟乘以60，就是大约54.55秒。"):
            self.play(Write(convert_steps[0]))
            self.wait(1)
            self.play(Write(convert_steps[1]))
            self.play(Write(convert_steps[2]))
            self.wait(1)
            self.play(Write(convert_steps[3]))

        # --- 场景 7: 动态演示 ---
        # story: 从2:00追到重合

        # 清理右侧，准备全屏动画
        self.play(FadeOut(convert_steps), FadeOut(calc_group[2]))
        # 把钟表移回中间并放大
        self.play(clock_full.animate.scale(1.25).move_to(ORIGIN))

        # 移除静态标注
        self.play(FadeOut(angle_arc), FadeOut(angle_label))

        # 准备动态变量
        # t 从 0 到 120/11
        target_time = 120 / 11
        t_tracker = ValueTracker(0)

        # 动态更新函数
        # 时针角度：-60度 (2点) - 0.5 * t
        # 分针角度：90度 (12点) - 6 * t
        # 注意Manim角度：12点是90deg, 顺时针转动是减角度

        def update_hands(mob):
            t = t_tracker.get_value()
            # 分针：初始在90度 (12点), 每分钟走6度
            m_angle = 90 - 6 * t
            # 时针：初始在30度 (2点, 也就是90-60), 每分钟走0.5度
            h_angle = 30 - 0.5 * t

            # 更新指针位置
            # 需要重新设置Line的角度，这里直接用 rotate absolute set比较麻烦
            # 简单的办法是 redraw
            pass  # 实际在下面用 always_redraw

        # 使用 always_redraw 来动态绘制指针
        # 分针
        vector_center = clock_group.get_center()

        moving_m_hand = always_redraw(lambda: Line(
            ORIGIN, UP * 1.5 * 0.8 * 1.25, color=BLUE, stroke_width=4
        ).rotate((90 - 6 * t_tracker.get_value()) * DEGREES).shift(vector_center))

        # 时针
        moving_h_hand = always_redraw(lambda: Line(
            ORIGIN, UP * 1.0 * 0.8 * 1.25, color=RED, stroke_width=6
        ).rotate((30 - 0.5 * t_tracker.get_value()) * DEGREES).shift(vector_center))

        # 差角显示
        delta_text = always_redraw(lambda: MathTex(
            r"\Delta \theta = " + "{:.1f}".format(max(0, 60 - 5.5 * t_tracker.get_value())) + r"^\circ",
            color=YELLOW
        ).next_to(clock_group, DOWN))

        # 时间显示格式化
        def get_time_str(t_val):
            total_seconds = t_val * 60
            mins = int(total_seconds // 60)
            secs = total_seconds % 60
            # 2点 + t
            return f"02:{mins:02d}:{secs:05.2f}"

        time_display = always_redraw(lambda: Text(
            get_time_str(t_tracker.get_value()), font="Monospace", font_size=36
        ).next_to(clock_group, UP))

        # 替换旧的指针和标签
        self.remove(m_hand, h_hand, time_label)
        self.add(moving_m_hand, moving_h_hand, time_display, delta_text)

        with self.voiceover(
                text="现在把计算变成直观看得见的动画：差角从60度开始，按每分钟5.5度匀速缩小。你会看到分针不断逼近时针，差角读数一路降到零。"):
            self.play(t_tracker.animate.set_value(target_time), run_time=8, rate_func=linear)

        # --- 场景 8: 重合瞬间定格+最终答案 ---
        # story: 2:10:54.55 定格

        final_text = VGroup(
            Text("第一次重合时刻", font_size=32),
            Text("2:10:54.55", font_size=48, color=YELLOW)
        ).arrange(DOWN).move_to(clock_group.get_center()).shift(DOWN * 3.5)

        # 高亮重合处
        flash_spot = Dot(color=YELLOW, radius=0.15).move_to(moving_m_hand.get_end())

        with self.voiceover(
                text="当差角第一次变成零的瞬间，就是第一次重合。对应的时间是两点十分钟五十四点五五秒，也就是大约两点十分钟五十五秒。"):
            self.play(FadeIn(final_text), Flash(flash_spot))
            self.wait(2)

        # --- 场景 9: 回顾总结 ---
        # story: 总结页

        # 整理屏幕：保留钟表在左侧，右侧显示总结
        summary_group = VGroup(
            Text("总结：", font_size=36),
            MathTex(r"\text{初始差角 } \Delta \theta_0 = 60^\circ"),
            MathTex(r"\text{相对速度 } \omega_{rel} = 5.5^\circ/\text{min}"),
            MathTex(r"\text{追及时间 } t = \frac{60}{5.5} \approx 10\text{min }54.55\text{s}")
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT).shift(LEFT)

        # 重新构建静态钟表放在左边（因为value tracker已经到了终点，可以直接用当前状态）
        # 为简单起见，直接把全屏内容移到左边

        everything = VGroup(clock_group, moving_m_hand, moving_h_hand, time_display, delta_text)

        with self.voiceover(
                text="总结一下：两点整初始差角60度；分针相对时针每分钟多走5.5度；所以用六十除以五点五得到追及时间，最终落在2点10分54.55秒。"):
            self.play(FadeOut(final_text))
            self.play(everything.animate.scale(0.7).to_edge(LEFT))
            self.play(Write(summary_group))
            self.wait(2)

        # 结束
        self.play(FadeOut(Group(*self.mobjects)))
        self.wait(1)

# manim -pqh your_filename.py ClockOverlapProblem
