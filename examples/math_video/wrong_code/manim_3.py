from manim import *
import math

# -----------------------------------------------------------------------------
# 旁白与字幕配置 (TTS Fallback Strategy)
# -----------------------------------------------------------------------------
# 每个步骤对应的旁白文本与估算时长
NARRATION = [
    {
        "id": "S1", 
        "text": "现在是2点整：分针在12，时针在2。问题是——2点过后，它们第一次重合，会发生在什么时候？", 
        "duration": 8
    },
    {
        "id": "S2", 
        "text": "先看起点。2点整时，时针在“2”这个刻度，比分针领先2格。每格30度，所以一开始就差了60度。", 
        "duration": 10
    },
    {
        "id": "S3", 
        "text": "把钟表当作匀速转动：分针1小时转一圈，所以是6度每分钟；时针12小时转一圈，所以是0.5度每分钟。", 
        "duration": 12
    },
    {
        "id": "S4", 
        "text": "关键在相对运动。分针追时针，追赶速度等于两者角速度之差：6减0.5，得到5.5度每分钟。", 
        "duration": 12
    },
    {
        "id": "S5", 
        "text": "首次重合就是差距变成0：需要追完60度。用追及公式：60等于5.5乘t，所以t等于60除以5.5，也就是120/11分钟。", 
        "duration": 12
    },
    {
        "id": "S6", 
        "text": "把120/11分钟换成我们熟悉的分秒：等于10又10/11分钟。10/11分钟乘60，得到54又6/11秒。", 
        "duration": 10
    },
    {
        "id": "S7", 
        "text": "现在用动画验证：从2点整开始，差距从60度以每分钟5.5度的速度缩小。到t等于120/11分钟这一刻，两根指针完全重合。", 
        "duration": 15
    },
    {
        "id": "S8", 
        "text": "再用公式核对一次：分针角度是6t，时针角度是60加0.5t。代入t等于120/11，它们确实在同一位置。", 
        "duration": 10
    },
    {
        "id": "S9", 
        "text": "总结一下：2点整差60度；相对速度5.5度每分钟；追完60度需要120/11分钟，即2点10分54又6/11秒。", 
        "duration": 12
    },
]

class ClockOverlapSolution(Scene):
    def construct(self):
        # ---------------------------------------------------------------------
        # S1: Hook - 引入问题
        # ---------------------------------------------------------------------
        self.next_section("S1_Hook")
        
        # 1. 创建钟面 VGroup
        clock_radius = 2.2
        clock_face = self.create_clock_face(radius=clock_radius)
        
        # 2. 创建指针 (初始化在 2:00:00)
        # Manim坐标系中，0度向右，90度向上(12点)
        # 分针指向12 -> 90度
        # 时针指向2 -> 90 - 2*30 = 30度
        m_hand = self.create_hand(length=clock_radius*0.85, angle_deg=90, color=BLUE, stroke_width=4)
        h_hand = self.create_hand(length=clock_radius*0.55, angle_deg=30, color=RED, stroke_width=6)
        center_dot = Dot(color=WHITE, radius=0.08)
        
        hands_group = VGroup(h_hand, m_hand, center_dot)
        full_clock = VGroup(clock_face, hands_group).move_to(ORIGIN)
        
        # 3. 标题字幕
        title = Text("2点过后，时针和分针什么时候第一次重合？", font_size=36).to_edge(UP, buff=0.5)
        title_bg = BackgroundRectangle(title, color=BLACK, fill_opacity=0.7)
        
        self.play(FadeIn(full_clock), FadeIn(title_bg), Write(title))
        self.play_narration("S1")
        
        # 悬念微动：分针快速晃动一下
        self.play(Rotate(m_hand, angle=-15*DEGREES, about_point=ORIGIN, rate_func=there_and_back, run_time=0.8))
        
        # ---------------------------------------------------------------------
        # S2: 设定背景 - 初始夹角
        # ---------------------------------------------------------------------
        self.next_section("S2_Background")
        
        # 钟面左移，腾出右侧空间
        self.play(full_clock.animate.scale(0.85).to_edge(LEFT, buff=1.0))
        
        # 绘制60度夹角弧线 (从2点到12点，即30度到90度)
        gap_arc = Arc(radius=0.8, start_angle=30*DEGREES, angle=60*DEGREES, color=YELLOW)
        gap_label = MathTex(r"60^\circ", color=YELLOW).move_to(gap_arc.point_from_proportion(0.5) * 1.6).shift(full_clock.get_center())
        gap_arc.shift(full_clock.get_center())
        
        # 右侧说明文字
        text_group_s2 = VGroup(
            Text("2点整时：", font_size=28, color=GRAY),
            Text("时针领先分针 2 格", font_size=32),
            MathTex(r"2 \times 30^\circ = 60^\circ", font_size=40, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT, buff=1.5).shift(UP*1.5)
        
        self.play(Create(gap_arc), Write(gap_label))
        self.play(Write(text_group_s2))
        self.play_narration("S2")
        
        # ---------------------------------------------------------------------
        # S3: 速度模型
        # ---------------------------------------------------------------------
        self.next_section("S3_SpeedModel")
        
        # 替换右侧文字
        speed_info = VGroup(
            Text("分针角速度：", font_size=28),
            MathTex(r"\omega_m = 360^\circ / 60\text{min} = 6^\circ / \text{min}", color=BLUE),
            Text("时针角速度：", font_size=28).shift(UP*0.2),
            MathTex(r"\omega_h = 360^\circ / 720\text{min} = 0.5^\circ / \text{min}", color=RED)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to(text_group_s2.get_center())
        
        self.play(FadeOut(text_group_s2), FadeIn(speed_info))
        self.play_narration("S3")
        
        # ---------------------------------------------------------------------
        # S4: 相对速度与追及条
        # ---------------------------------------------------------------------
        self.next_section("S4_RelativeSpeed")
        
        # 相对速度公式
        rel_speed_info = VGroup(
            Text("相对角速度 (追及速度)：", font_size=28),
            MathTex(r"\omega_{rel} = 6 - 0.5 = 5.5^\circ / \text{min}", color=GREEN),
            Text("需追及路程：", font_size=28).shift(UP*0.2),
            MathTex(r"\Delta \theta = 60^\circ", color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to(speed_info.get_center())
        
        # 差值条 UI
        bar_bg = Rectangle(width=4, height=0.2, color=WHITE, fill_opacity=0.2)
        bar_fill = Rectangle(width=4, height=0.2, color=YELLOW, fill_opacity=0.8)
        bar_fill.align_to(bar_bg, LEFT)
        bar_label = Text("差距 Δ(t)", font_size=20).next_to(bar_bg, LEFT)
        bar_group = VGroup(bar_label, bar_bg, bar_fill).next_to(full_clock, DOWN, buff=0.5)
        
        self.play(FadeOut(speed_info), FadeIn(rel_speed_info), FadeIn(bar_group))
        # 演示条稍微缩短一点示意
        self.play(bar_fill.animate.stretch_to_fit_width(3.5, about_edge=LEFT), run_time=1.5)
        self.play_narration("S4")
        
        # ---------------------------------------------------------------------
        # S5: 解方程
        # ---------------------------------------------------------------------
        self.next_section("S5_Equation")
        
        # 板书推导
        equation_steps = VGroup(
            Text("追及方程：", font_size=28, color=GRAY),
            MathTex(r"\text{相对速度} \times t = \text{路程}"),
            MathTex(r"5.5 \times t = 60"),
            MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \, \text{min}", color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).to_edge(RIGHT, buff=2)
        
        # 高亮框
        frame = SurroundingRectangle(equation_steps[-1], color=YELLOW, buff=0.15)
        
        self.play(FadeOut(rel_speed_info), Write(equation_steps[0]))
        self.play(Write(equation_steps[1]))
        self.play(TransformMatchingTex(equation_steps[1].copy(), equation_steps[2]))
        self.play(TransformMatchingTex(equation_steps[2].copy(), equation_steps[3]))
        self.play(Create(frame))
        self.play_narration("S5")
        
        # ---------------------------------------------------------------------
        # S6: 时间换算
        # ---------------------------------------------------------------------
        self.next_section("S6_Conversion")
        
        convert_group = VGroup(
            MathTex(r"t = \frac{120}{11} \text{min} = 10 \text{min} + \frac{10}{11} \text{min}"),
            MathTex(r"\frac{10}{11} \text{min} = \frac{10}{11} \times 60 \text{s} = \frac{600}{11} \text{s}"),
            MathTex(r"= 54 \text{s} + \frac{6}{11} \text{s}"),
            Text("时刻：2:10:54 6/11", font_size=36, color=GOLD)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to(equation_steps.get_center())
        
        self.play(FadeOut(equation_steps), FadeOut(frame), FadeIn(convert_group[0]))
        self.wait(0.5)
        self.play(FadeIn(convert_group[1]))
        self.play(FadeIn(convert_group[2]))
        self.play(FadeIn(convert_group[3]), Indicate(convert_group[3]))
        self.play_narration("S6")
        
        # ---------------------------------------------------------------------
        # S7: 动态演示 (核心)
        # ---------------------------------------------------------------------
        self.next_section("S7_DynamicDemo")
        
        # 清理屏幕，将钟表移回中央并放大
        self.play(
            FadeOut(convert_group),
            FadeOut(bar_group),
            FadeOut(gap_arc), FadeOut(gap_label),
            FadeOut(title), FadeOut(title_bg),
            full_clock.animate.scale(1.2).move_to(ORIGIN)
        )
        
        # 计时器组件
        timer_val = DecimalNumber(0, num_decimal_places=2, include_sign=False)
        timer_label = MathTex(r"t =").next_to(timer_val, LEFT)
        timer_unit = MathTex(r"\text{min}").next_to(timer_val, RIGHT)
        timer_group = VGroup(timer_label, timer_val, timer_unit).to_corner(UR, buff=1)
        
        self.play(FadeIn(timer_group))
        
        # 动画变量
        t_tracker = ValueTracker(0)
        target_t = 120 / 11  # ~10.90909...
        
        # 定义Updater: 根据 t 更新指针角度
        # t 是分钟数。 
        # 分针角度：90 - 6t
        # 时针角度：30 - 0.5t
        # (Manim中0度是右边，12点是90度，顺时针旋转需减角度)
        
        def update_minute_hand(m):
            val = t_tracker.get_value()
            angle = (90 - 6 * val) * DEGREES
            # 指针起点始终在钟表中心 (此时是 ORIGIN)
            # 终点根据角度计算
            # 注意 m_hand 原始长度，需要保持
            length = 2.2 * 0.85 * 1.2 * 0.85 # 之前有过多次scale，重新计算比较乱，不如直接取当前长度
            # 更稳妥：始终以 center 为基准画线
            end_point = full_clock[0].get_center() + np.array([math.cos(angle), math.sin(angle), 0]) * (clock_radius * 0.85)
            m.put_start_and_end_on(full_clock[0].get_center(), end_point)

        def update_hour_hand(h):
            val = t_tracker.get_value()
            angle = (30 - 0.5 * val) * DEGREES
            end_point = full_clock[0].get_center() + np.array([math.cos(angle), math.sin(angle), 0]) * (clock_radius * 0.55)
            h.put_start_and_end_on(full_clock[0].get_center(), end_point)

        m_hand.add_updater(update_minute_hand)
        h_hand.add_updater(update_hour_hand)
        timer_val.add_updater(lambda d: d.set_value(t_tracker.get_value()))
        
        # 播放动画：前10分钟较快，最后一点减速
        self.play(t_tracker.animate.set_value(10), run_time=5, rate_func=linear)
        self.play(t_tracker.animate.set_value(target_t), run_time=4, rate_func=ease_out_cubic)
        
        # 停止更新
        m_hand.clear_updaters()
        h_hand.clear_updaters()
        timer_val.clear_updaters()
        
        # 重合高亮
        flash_location = m_hand.get_end()
        self.play(Flash(flash_location, color=WHITE, flash_radius=0.5))
        
        final_res_text = Text("2:10:54 6/11", font_size=48, color=YELLOW).next_to(full_clock, DOWN)
        self.play(Write(final_res_text))
        self.play_narration("S7")
        
        # ---------------------------------------------------------------------
        # S8: 验证 (Optional)
        # ---------------------------------------------------------------------
        self.next_section("S8_Verification")
        
        # 布局：左钟表，右公式
        group_demo = VGroup(full_clock, final_res_text)
        self.play(group_demo.animate.scale(0.7).to_edge(LEFT))
        self.play(FadeOut(timer_group))
        
        verify_text = MathTex(
            r"\theta_m &= 6 \times \frac{120}{11} = \frac{720}{11}^\circ \\",
            r"\theta_h &= 60 + 0.5 \times \frac{120}{11} \\",
            r"&= 60 + \frac{60}{11} = \frac{720}{11}^\circ"
        ).scale(0.85).to_edge(RIGHT, buff=1)
        
        self.play(Write(verify_text))
        self.play_narration("S8")
        
        # ---------------------------------------------------------------------
        # S9: 总结
        # ---------------------------------------------------------------------
        self.next_section("S9_Summary")
        
        self.play(FadeOut(group_demo), FadeOut(verify_text))
        
        summary_title = Text("本次计算总结", font_size=40).to_edge(UP, buff=1)
        summary_list = VGroup(
            Text("1. 初始差距：60° (2点整)", font_size=32),
            Text("2. 相对速度：5.5°/min", font_size=32),
            Text("3. 追及时间：120/11 min", font_size=32),
            Text("4. 最终时刻：2:10:54 6/11", font_size=32, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.6).next_to(summary_title, DOWN, buff=1)
        
        self.play(Write(summary_title), FadeIn(summary_list, shift=UP))
        self.play_narration("S9")
        
        self.wait(2)

    # --- Helper Functions ---

    def create_clock_face(self, radius=2.5):
        circle = Circle(radius=radius, color=WHITE, stroke_width=4)
        ticks = VGroup()
        numbers = VGroup()
        
        for i in range(12):
            # i=0 -> 12点(90度), i=1 -> 1点(60度)
            angle_deg = 90 - i * 30
            angle_rad = angle_deg * DEGREES
            
            # 刻度线
            start = np.array([math.cos(angle_rad), math.sin(angle_rad), 0]) * (radius * 0.9)
            end = np.array([math.cos(angle_rad), math.sin(angle_rad), 0]) * radius
            tick = Line(start, end, color=WHITE, stroke_width=2)
            ticks.add(tick)
            
            # 数字
            num_pos = np.array([math.cos(angle_rad), math.sin(angle_rad), 0]) * (radius * 0.75)
            t_str = str(i) if i != 0 else "12"
            num = Text(t_str, font_size=24).move_to(num_pos)
            numbers.add(num)
            
        return VGroup(circle, ticks, numbers)

    def create_hand(self, length, angle_deg, color, stroke_width):
        hand = Line(ORIGIN, RIGHT * length, color=color, stroke_width=stroke_width)
        # set_angle 在 Manim 中默认绕 center 旋转
        # Line(ORIGIN, RIGHT*L) 的 center 是 (L/2, 0, 0)
        # 所以要用 put_start_and_end_on 或者 about_point
        # 简单方法：先定好位置
        hand.set_angle(angle_deg * DEGREES)
        # 修正位置到原点
        # 但 set_angle 对于 Line 可能会导致位置偏移，最稳是直接重画
        start = ORIGIN
        end = np.array([math.cos(angle_deg*DEGREES), math.sin(angle_deg*DEGREES), 0]) * length
        hand.put_start_and_end_on(start, end)
        return hand

    def play_narration(self, step_id):
        """
        播放字幕并等待指定时间。
        如果有TTS库可在此集成。此处使用字幕+Wait降级方案。
        """
        item = next((x for x in NARRATION if x["id"] == step_id), None)
        if item:
            text = item["text"]
            duration = item.get("duration", 2)
            
            # 生成字幕对象
            subtitle = Text(text, font_size=24, color=WHITE).to_edge(DOWN, buff=0.8)
            # 宽度安全检查
            if subtitle.width > config.frame_width * 0.9:
                subtitle.scale(config.frame_width * 0.9 / subtitle.width)
                
            # 背景条 (增加可读性)
            bg = BackgroundRectangle(subtitle, color=BLACK, fill_opacity=0.6, buff=0.1)
            
            self.add(bg, subtitle)
            self.wait(duration)
            self.remove(bg, subtitle)
        else:
            self.wait(1)

# 运行提示：
# manim -pqh your_file.py ClockOverlapSolution
