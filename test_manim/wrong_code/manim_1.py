from manim import *

# --- 旁白脚本配置 (TTS Fallback) ---
# 如果无法使用 manim-voiceover，RenderAgent 可根据此列表生成语音
NARRATION = [
    {"id": "S01", "text": "从2点整开始，分针和时针什么时候第一次重合？这是一个经典的追及问题：分针转得更快，追上时针需要多久。"},
    {"id": "S02", "text": "2点整时，分针在12点方向，时针在2点方向。两者的初始夹角是60度。"},
    {"id": "S03", "text": "分针每分钟转6度，时针每分钟转0.5度。所以分针追赶时针的相对角速度是6减0.5，也就是每分钟5.5度。"},
    {"id": "S04", "text": "第一次重合时，分针相对时针追上的角度，正好等于最初的60度。所以有：相对角速度乘时间等于初始夹角。"},
    {"id": "S05", "text": "解这个方程：时间t等于60除以6减0.5，最后得到精确值是一百二十分之十一，也就是120/11分钟。"},
    {"id": "S06", "text": "把120/11分钟拆开：等于10分钟再加10/11分钟。10/11分钟乘60，得到600/11秒，也就是54又6/11秒。所以重合发生在2点10分54又6/11秒。"},
    {"id": "S07", "text": "现在用动画直观看一下：分针以更快的速度追赶时针，经过120/11分钟，两针第一次重合。"},
    {"id": "S08", "text": "总结一下：初始夹角60度，相对角速度5.5度每分钟，所以时间就是60除以5.5，得到120/11分钟，对应2点10分54又6/11秒。"}
]

class ClockOverlapScene(Scene):
    def construct(self):
        # ---------------------------------------------------------------------
        # S01_hook: 开场标题
        # ---------------------------------------------------------------------
        # Narration: 从2点整开始，分针和时针什么时候第一次重合？...
        
        title = Text("2点后时针和分针第一次重合", font_size=48)
        subtitle = Text("经典追及问题", font_size=32, color=GREY).next_to(title, DOWN)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(3) # 阅读时间
        
        self.play(
            FadeOut(subtitle),
            title.animate.scale(0.8).to_edge(UP)
        )
        self.wait(1)

        # ---------------------------------------------------------------------
        # S02_setup_clock_200: 2:00 时刻设置
        # ---------------------------------------------------------------------
        # Narration: 2点整时，分针在12点方向，时针在2点方向...

        # 创建时钟组件
        clock_radius = 2.0
        clock_circle = Circle(radius=clock_radius, color=WHITE)
        clock_center = Dot(point=ORIGIN)
        
        # 简单的刻度 (12, 3, 6, 9)
        ticks = VGroup()
        for i in range(12):
            angle = i * 30 * DEGREES
            tick_len = 0.2 if i % 3 == 0 else 0.1
            p1 = rotate_vector(UP * clock_radius, -angle)
            p2 = rotate_vector(UP * (clock_radius - tick_len), -angle)
            ticks.add(Line(p1, p2, color=GREY))

        clock_group = VGroup(clock_circle, clock_center, ticks)
        clock_group.shift(LEFT * 2.5 + DOWN * 0.5) # 预先放置在左侧，留出右侧给公式

        # 指针
        # 分针指向12点 (UP)
        hand_minute = Line(ORIGIN, UP * 1.6, color=BLUE, stroke_width=6).move_to(clock_group.get_center(), aligned_edge=DOWN)
        # 时针指向2点 (UP 旋转 -60度)
        hand_hour = Line(ORIGIN, UP * 1.0, color=YELLOW, stroke_width=8).move_to(clock_group.get_center(), aligned_edge=DOWN)
        hand_hour.rotate(-60 * DEGREES, about_point=clock_group.get_center())

        self.play(Create(clock_group))
        self.play(Create(hand_minute), Create(hand_hour))

        # 标注 60度
        # 弧度：从 90度 (12点) 到 30度 (2点)
        angle_arc = Arc(radius=0.8, start_angle=90*DEGREES, angle=-60*DEGREES, arc_center=clock_group.get_center(), color=RED)
        angle_label = MathTex(r"\Delta\theta_0 = 60^\circ", color=RED).next_to(angle_arc, UR, buff=0.1)
        
        self.play(Create(angle_arc), Write(angle_label))
        self.wait(4)

        # ---------------------------------------------------------------------
        # S03_speeds: 速度参数展示
        # ---------------------------------------------------------------------
        # Narration: 分针每分钟转6度，时针每分钟转0.5度...

        # 右侧区域布局
        info_start_point = UP * 2 + RIGHT * 1.5
        
        # 使用 VGroup + arrange 对齐文本和公式
        # 行1：分针
        row1_text = Text("分针速度", font_size=28, color=BLUE)
        row1_math = MathTex(r"\omega_m = 6\,\mathrm{deg/min}", color=BLUE, font_size=32)
        row1 = VGroup(row1_text, row1_math).arrange(RIGHT, buff=0.5)
        
        # 行2：时针
        row2_text = Text("时针速度", font_size=28, color=YELLOW)
        row2_math = MathTex(r"\omega_h = 0.5\,\mathrm{deg/min}", color=YELLOW, font_size=32)
        row2 = VGroup(row2_text, row2_math).arrange(RIGHT, buff=0.5)

        # 行3：相对速度
        row3_text = Text("相对速度", font_size=28, color=GREEN)
        row3_math = MathTex(r"\omega_{rel} = 5.5\,\mathrm{deg/min}", color=GREEN, font_size=32)
        row3 = VGroup(row3_text, row3_math).arrange(RIGHT, buff=0.5)

        # 整体排列
        speed_info = VGroup(row1, row2, row3).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        speed_info.move_to(RIGHT * 3.5 + UP * 1.5)

        self.play(FadeIn(speed_info))
        self.wait(5)

        # ---------------------------------------------------------------------
        # S04_equation_chase: 追及方程
        # ---------------------------------------------------------------------
        # Narration: 第一次重合时... 相对角速度乘时间等于初始夹角。

        eq_text = Text("追及条件：", font_size=32).next_to(speed_info, DOWN, buff=0.8, aligned_edge=LEFT)
        eq_formula = MathTex(r"(\omega_m - \omega_h)t = \Delta\theta_0", font_size=38)
        eq_formula.next_to(eq_text, RIGHT)
        
        eq_sub = MathTex(r"5.5 t = 60", font_size=38).next_to(eq_formula, DOWN, buff=0.3, aligned_edge=LEFT)

        self.play(Write(eq_text), Write(eq_formula))
        self.wait(2)
        self.play(Write(eq_sub))
        self.wait(3)

        # ---------------------------------------------------------------------
        # S05_solve_t: 求解 t
        # ---------------------------------------------------------------------
        # Narration: 解这个方程... 120/11分钟。

        eq_sol = MathTex(r"t = \frac{60}{5.5} = \frac{120}{11}\,\mathrm{min}", font_size=38)
        eq_sol.next_to(eq_sub, DOWN, buff=0.4, aligned_edge=LEFT)
        
        rect = SurroundingRectangle(eq_sol, color=GREEN, buff=0.1)
        
        self.play(Write(eq_sol))
        self.play(Create(rect))
        self.wait(4)

        # ---------------------------------------------------------------------
        # S06_convert_to_hms: 换算时分秒
        # ---------------------------------------------------------------------
        # Narration: 把120/11分钟拆开...
        
        # 清理上面的部分内容，腾出空间，或者直接在下方写
        # 这里的空间可能有点挤，我们将 speed_info 淡出，把方程上移
        
        move_group = VGroup(eq_text, eq_formula, eq_sub, eq_sol, rect)
        self.play(
            FadeOut(speed_info),
            move_group.animate.shift(UP * 2.5)
        )

        # 换算过程
        conv_step1 = MathTex(r"\frac{120}{11}\,\mathrm{min} = 10\,\mathrm{min} + \frac{10}{11}\,\mathrm{min}", font_size=36)
        conv_step1.next_to(move_group, DOWN, buff=0.6, aligned_edge=LEFT)
        
        conv_step2 = MathTex(r"\frac{10}{11}\,\mathrm{min} \times 60 = \frac{600}{11}\,\mathrm{s} = 54\,\mathrm{s} + \frac{6}{11}\,\mathrm{s}", font_size=36)
        conv_step2.next_to(conv_step1, DOWN, buff=0.4, aligned_edge=LEFT)
        
        final_text = Text("重合时间：2点10分54又6/11秒", font_size=36, color=YELLOW)
        final_text.next_to(conv_step2, DOWN, buff=0.8)

        self.play(Write(conv_step1))
        self.wait(3)
        self.play(Write(conv_step2))
        self.wait(4)
        self.play(Write(final_text))
        self.wait(3)

        # ---------------------------------------------------------------------
        # S07_animation_verify: 动画验证
        # ---------------------------------------------------------------------
        # Narration: 现在用动画直观看一下...

        # 清空右侧公式，只保留结论和时钟
        self.play(
            FadeOut(move_group), 
            FadeOut(conv_step1), 
            FadeOut(conv_step2),
            FadeOut(angle_arc),  # 移除初始角度标注
            FadeOut(angle_label),
            final_text.animate.to_edge(DOWN),
            clock_group.animate.move_to(ORIGIN), # 时钟移回中间
            hand_minute.animate.move_to(ORIGIN, aligned_edge=DOWN).shift(UP*0.0), # 修正可能的位移误差
            hand_hour.animate.move_to(ORIGIN, aligned_edge=DOWN).shift(UP*0.0)
        )
        
        # 重新确保指针中心正确
        # 注意：Move animate 可能导致旋转中心丢失，最好重置一下位置
        # 简单起见，我们直接 rotate Vobject，假设 center 在 ORIGIN (因为 clock_group 移到了 ORIGIN)
        
        # 计算旋转角度
        # t = 120/11 min
        # 分针转动：6 deg/min * 120/11 min = 720/11 deg
        # 时针转动：0.5 deg/min * 120/11 min = 60/11 deg
        # Manim Rotate angle 是弧度，顺时针为负
        
        t_val = 120/11
        angle_m = - (6 * t_val) * DEGREES
        angle_h = - (0.5 * t_val) * DEGREES

        # 添加一个计时器显示 (MathTex)
        timer_label = MathTex(r"t = 0.00\,\mathrm{min}", font_size=40).to_corner(UR)
        self.play(FadeIn(timer_label))

        # 使用 ValueTracker 做计时动画
        t_tracker = ValueTracker(0)

        def update_hands(mob):
            t = t_tracker.get_value()
            # 分针当前角度：从初始 90度 (UP) 开始，顺时针转 6t 度
            # 时针当前角度：从初始 30度 (2点) 开始，顺时针转 0.5t 度
            # 重置指针并旋转
            
            # 分针更新
            hand_minute.put_start_and_end_on(ORIGIN, UP * 1.6)
            hand_minute.rotate(-6 * t * DEGREES, about_point=ORIGIN)
            
            # 时针更新
            hand_hour.put_start_and_end_on(ORIGIN, UP * 1.0)
            # 初始偏转 -60度 (指向2点)
            hand_hour.rotate(-60 * DEGREES, about_point=ORIGIN) 
            # 运动偏转
            hand_hour.rotate(-0.5 * t * DEGREES, about_point=ORIGIN)

        def update_timer(mob):
            val = t_tracker.get_value()
            mob.become(MathTex(rf"t = {val:.2f}\,\mathrm{{min}}", font_size=40).to_corner(UR))

        # 将更新函数绑定
        hand_minute.add_updater(lambda m: update_hands(m))
        # hand_hour 也在同一个 update_hands 里更新了，不需要单独加
        # 但是为了逻辑清晰，最好分开，或者只加给 Scene 的 update
        # 这里由于 hand_minute 的 updater 实际上修改了两个指针，有点副作用，但能工作。
        # 更规范的做法是：
        hand_minute.remove_updater(lambda m: update_hands(m))
        
        # 重新定义规范的 Updater
        def update_min_hand(m):
            t = t_tracker.get_value()
            m.put_start_and_end_on(ORIGIN, UP * 1.6)
            m.rotate(-6 * t * DEGREES, about_point=ORIGIN)
            
        def update_hour_hand(m):
            t = t_tracker.get_value()
            m.put_start_and_end_on(ORIGIN, UP * 1.0)
            m.rotate((-60 - 0.5 * t) * DEGREES, about_point=ORIGIN)

        hand_minute.add_updater(update_min_hand)
        hand_hour.add_updater(update_hour_hand)
        timer_label.add_updater(update_timer)

        self.play(t_tracker.animate.set_value(120/11), run_time=6, rate_func=linear)
        
        hand_minute.clear_updaters()
        hand_hour.clear_updaters()
        timer_label.clear_updaters()

        # 闪烁高亮重合
        flash_circle = Circle(radius=1.8, color=YELLOW).move_to(ORIGIN)
        self.play(ShowPassingFlash(flash_circle, time_width=0.5, run_time=1))
        
        final_time_tex = MathTex(r"t = \frac{120}{11}\,\mathrm{min}", color=GREEN).next_to(timer_label, DOWN)
        self.play(Write(final_time_tex))
        self.wait(3)

        # ---------------------------------------------------------------------
        # S08_outro_summary: 总结
        # ---------------------------------------------------------------------
        # Narration: 总结一下：初始夹角60度...
        
        self.play(
            FadeOut(clock_group), 
            FadeOut(hand_minute), 
            FadeOut(hand_hour), 
            FadeOut(timer_label), 
            FadeOut(final_time_tex),
            FadeOut(final_text)
        )

        summary_title = Text("要点总结", font_size=40).to_edge(UP)
        
        # 用 VGroup 垂直排列
        p1 = Text("1. 初始夹角 60°", font_size=32)
        p2 = Text("2. 相对角速度 5.5°/min", font_size=32)
        p3 = VGroup(Text("3. 追及时间 ", font_size=32), MathTex(r"\frac{120}{11}\,\mathrm{min}", font_size=36)).arrange(RIGHT)
        
        summary_list = VGroup(p1, p2, p3).arrange(DOWN, buff=0.8, aligned_edge=LEFT)
        
        self.play(Write(summary_title))
        self.play(FadeIn(summary_list, shift=UP))
        
        self.wait(5)

# 运行命令提示：
# manim -pqh your_file_name.py ClockOverlapScene
