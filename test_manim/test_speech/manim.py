from manim import *
import numpy as np

class ClockOverlap(Scene):
    def construct(self):
        # --- 全局配置 ---
        # 颜色定义
        COLOR_MIN = BLUE      # 分针颜色
        COLOR_HOUR = RED      # 时针颜色
        COLOR_GAP = ORANGE    # 夹角/强调色
        
        # 字体配置
        TEXT_FONT = "Sans"    # 无衬线字体更适合科普
        
        # --- 1. 场景搭建：绘制时钟 ---
        # 创建表盘
        clock_group = VGroup()
        clock_face = Circle(radius=2.5, color=WHITE, stroke_width=4)
        clock_group.add(clock_face)
        
        # 添加刻度与数字
        for i in range(12):
            # 角度：从12点钟(90度)开始，顺时针每格30度
            angle = 90 * DEGREES - i * 30 * DEGREES
            # 刻度
            tick = Line(UP * 2.2, UP * 2.5, color=WHITE).rotate(angle - 90*DEGREES, about_point=ORIGIN)
            clock_group.add(tick)
            # 数字 (12, 1, 2...)
            num_val = 12 if i == 0 else i
            num = Text(str(num_val), font_size=24, font=TEXT_FONT).move_to(
                np.array([np.cos(angle), np.sin(angle), 0]) * 1.9
            )
            clock_group.add(num)
            
        # 创建指针 (初始状态 2:00:00)
        # 分针：指向12点 (90度)
        m_hand = Line(ORIGIN, UP * 1.8, color=COLOR_MIN, stroke_width=6).set_z_index(10)
        # 时针：指向2点 (30度)
        h_hand = Line(ORIGIN, UP * 1.2, color=COLOR_HOUR, stroke_width=8).set_z_index(9)
        h_hand.rotate(-60 * DEGREES, about_point=ORIGIN) # 从12点顺时针转60度到2点
        
        center_dot = Dot(color=WHITE, radius=0.08).set_z_index(11)
        clock_group.add(m_hand, h_hand, center_dot)
        
        # 布局：时钟放左侧
        clock_group.shift(LEFT * 3.5)
        
        # --- S1: 问题引入 ---
        title = Text("时针分针何时重合？", font_size=42, font=TEXT_FONT).to_edge(UP)
        subtitle = Text("起始时间：2点00分", font_size=32, color=GRAY, font=TEXT_FONT).next_to(title, DOWN)
        
        self.play(FadeIn(clock_group), Write(title))
        self.play(FadeIn(subtitle))
        self.wait(2)
        
        # --- S2: 初始状态分析 ---
        # 右侧信息面板
        info_group = VGroup().to_edge(RIGHT, buff=1.0)
        
        # 速度信息
        v_title = Text("角速度", font_size=32, font=TEXT_FONT, color=YELLOW)
        v_min = VGroup(Text("分针: ", font=TEXT_FONT, font_size=28), MathTex(r"6^\circ / \text{min}", color=COLOR_MIN)).arrange(RIGHT)
        v_hour = VGroup(Text("时针: ", font=TEXT_FONT, font_size=28), MathTex(r"0.5^\circ / \text{min}", color=COLOR_HOUR)).arrange(RIGHT)
        
        v_group = VGroup(v_title, v_min, v_hour).arrange(DOWN, aligned_edge=LEFT).move_to(RIGHT * 3 + UP * 1.5)
        
        self.play(Write(v_group))
        
        # 标注60度初始夹角
        # Arc angle: start=90deg (12点), angle=-60deg (顺时针到2点)
        initial_arc = Arc(radius=1.0, start_angle=90*DEGREES, angle=-60*DEGREES, color=COLOR_GAP)
        arc_label = Text("初始夹角 60°", font_size=24, color=COLOR_GAP, font=TEXT_FONT).next_to(initial_arc, UR, buff=0.1)
        
        self.play(Create(initial_arc), FadeIn(arc_label))
        self.wait(1.5)
        
        # --- S3: 追及模型 ---
        # 移除部分旧UI，腾出空间
        self.play(FadeOut(subtitle), FadeOut(arc_label))
        
        calc_group = VGroup().move_to(RIGHT * 3 + DOWN * 1.5)
        
        # 相对速度
        step1_txt = Text("追及速度 (相对速度):", font_size=28, font=TEXT_FONT, color=YELLOW)
        step1_math = MathTex(r"\omega_{rel} = 6 - 0.5 = 5.5^\circ / \text{min}")
        
        step1 = VGroup(step1_txt, step1_math).arrange(DOWN).align_to(v_group, LEFT)
        
        self.play(Write(step1))
        self.wait(2)
        
        # --- S4: 求解时间 ---
        self.play(FadeOut(step1))
        
        # 公式推导
        step2_txt = Text("追及时间 = 路程 ÷ 速度", font_size=28, font=TEXT_FONT, color=YELLOW)
        step2_math = MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \, \text{min}")
        
        step2 = VGroup(step2_txt, step2_math).arrange(DOWN).align_to(v_group, LEFT)
        self.play(Write(step2))
        self.wait(2)
        
        # 换算部分 (关键难点)
        step3_math = MathTex(
            r"\frac{120}{11} \text{min} &= 10\text{min} + \frac{10}{11}\text{min} \\",
            r"&= 10\text{min} + (\frac{10}{11} \times 60)\text{s} \\",
            r"&\approx 10\text{min} \, 54.55\text{s}"
        ).scale(0.8)
        step3_math.next_to(step2, DOWN, buff=0.5)
        
        self.play(Write(step3_math))
        self.wait(3)
        
        # --- S5: 动态演示 (Visual Proof) ---
        # 清理右侧，准备显示计时器
        self.play(
            FadeOut(v_group),
            FadeOut(step2),
            FadeOut(step3_math),
            FadeOut(initial_arc),
            clock_group.animate.move_to(ORIGIN).scale(1.2)
        )
        
        # HUD 时间显示
        # 位置：右上角
        timer_bg = Rectangle(width=4.5, height=1.2, color=GRAY, fill_opacity=0.2).to_edge(UR)
        timer_label = Text("当前时间", font_size=24, font=TEXT_FONT).next_to(timer_bg, UP, buff=0.1).align_to(timer_bg, LEFT)
        
        # 动态数字变量
        # 格式 2:MM:SS.ss
        # t 是分钟数，从0开始
        t_tracker = ValueTracker(0)
        target_t = 120/11  # 约 10.90909...
        
        # 创建小数点数对象
        def get_time_text():
            curr_min = t_tracker.get_value()
            total_seconds = curr_min * 60
            m = int(total_seconds // 60)
            s = int(total_seconds % 60)
            ms = int((total_seconds % 1) * 100)
            return Text(
                f"2:{m:02d}:{s:02d}.{ms:02d}", 
                font="Monospace", 
                font_size=48, 
                color=WHITE
            ).move_to(timer_bg)
            
        timer_display = always_redraw(get_time_text)
        
        self.add(timer_bg, timer_display, timer_label)
        
        # 指针更新器
        # 初始: 分针90度(12点), 时针30度(2点)
        # 运动: 顺时针为负
        # Angle = Initial - Speed * t
        def update_hands(mob):
            t = t_tracker.get_value()
            # 分针: 90 - 6t
            m_angle = (90 - 6 * t) * DEGREES
            # 时针: 30 - 0.5t
            h_angle = (30 - 0.5 * t) * DEGREES
            
            # 重新定位线段
            # 分针
            m_hand.put_start_and_end_on(ORIGIN, UP * 1.8)
            m_hand.rotate(m_angle - 90*DEGREES, about_point=ORIGIN)
            # 时针
            h_hand.put_start_and_end_on(ORIGIN, UP * 1.2)
            h_hand.rotate(h_angle - 90*DEGREES, about_point=ORIGIN)

        # 添加 updater
        m_hand.add_updater(lambda m: update_hands(m))
        
        # 播放动画：模拟追及过程
        # 15秒内跑完 10.9分钟
        self.play(
            t_tracker.animate.set_value(target_t),
            run_time=12,
            rate_func=linear
        )
        
        # --- S6: 结论定格 ---
        # 移除 updater 以便定格
        m_hand.clear_updaters()
        
        # 强调重合
        flash_circle = Circle(radius=1.8, color=YELLOW, stroke_width=8).move_to(ORIGIN)
        self.play(ShowPassingFlash(flash_circle))
        
        # 最终结论框
        final_box = RoundedRectangle(corner_radius=0.2, fill_color=BLACK, fill_opacity=0.8, width=7, height=2.5)
        final_text = VGroup(
            Text("第一次重合时间", font_size=36, color=YELLOW, font=TEXT_FONT),
            MathTex(r"t = \frac{120}{11} \, \text{min}", font_size=48),
            Text("约 2点10分54.55秒", font_size=40, font=TEXT_FONT)
        ).arrange(DOWN)
        final_group = VGroup(final_box, final_text).move_to(DOWN * 2)
        
        self.play(FadeIn(final_group))
        self.wait(3)
