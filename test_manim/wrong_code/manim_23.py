from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.bytedance import ByteDanceService
import platform


# --- 字体配置 helper ---
def get_cjk_font_by_platform():
    if platform.system() == "Windows":
        return "Microsoft YaHei"
    elif platform.system() == "Darwin":
        return "PingFang SC"
    else:
        return "Noto Sans CJK SC"


cjk_font = get_cjk_font_by_platform()


# --- Manim 场景类 ---
class ClockChaseProblem(VoiceoverScene):
    def construct(self):
        # 1. 配置 TTS 服务
        self.set_speech_service(ByteDanceService())

        # --- 资源准备：钟面与指针 ---
        # 钟面背景
        clock_radius = 2.2
        clock_group = VGroup()
        clock_face = Circle(radius=clock_radius, color=WHITE, stroke_width=4)
        clock_group.add(clock_face)

        # 刻度
        ticks = VGroup()
        for i in range(12):
            angle = i * 30 * DEGREES
            start = clock_radius * np.array([np.sin(angle), np.cos(angle), 0])
            end = (clock_radius - 0.2) * np.array([np.sin(angle), np.cos(angle), 0])
            ticks.add(Line(start, end, color=WHITE))
        # 数字 (3, 6, 9, 12)
        nums = VGroup()
        nums.add(Text("12", font=cjk_font).move_to((clock_radius - 0.5) * UP))
        nums.add(Text("3", font=cjk_font).move_to((clock_radius - 0.5) * RIGHT))
        nums.add(Text("6", font=cjk_font).move_to((clock_radius - 0.5) * DOWN))
        nums.add(Text("9", font=cjk_font).move_to((clock_radius - 0.5) * LEFT))
        nums.add(Text("2", font=cjk_font).move_to(
            (clock_radius - 0.5) * (np.cos(30 * DEGREES) * RIGHT + np.sin(30 * DEGREES) * UP)))

        clock_group.add(ticks, nums)
        clock_group.shift(LEFT * 3)  # 钟面放在左侧

        # 指针 (单独创建以便旋转)
        # 初始时刻 2:00 => 分针0度(指向12), 时针-60度(指向2, 注意Manim角度逆时针为正，顺时针旋转需处理)
        # Manim坐标系：0度在右(3点)，90度在上(12点)
        # 分针指向12点 -> 90度
        # 时针指向2点 -> 30度
        minute_hand = Line(ORIGIN, UP * (clock_radius - 0.4), color="#2D9CDB", stroke_width=6)
        hour_hand = Line(ORIGIN, (UP * (clock_radius * 0.6)).rotate(-60 * DEGREES, about_point=ORIGIN), color="#EB5757",
                         stroke_width=8)
        center_dot = Dot(radius=0.08, color=WHITE)

        # 指针组 (初始位置 2:00)
        hands_group = VGroup(minute_hand, hour_hand, center_dot).move_to(clock_group.get_center())

        # --- Step 1: 开场与问题抛出 ---
        title = Text("2点钟时针和分针何时第一次重合？", font=cjk_font, font_size=36).to_edge(UP)

        with self.voiceover(text="我们从2点整开始：分针在12点方向，时针在2点方向。问题是——它们第一次重合发生在什么时候？"):
            self.play(FadeIn(title))
            self.play(Create(clock_group), Create(hands_group))
            self.wait(1)

        # --- Step 2: 初始夹角 ---
        # 弧线表示 60度 (从分针到时针)
        # 角度：分针90度，时针30度。差60度。
        arc_angle = Arc(radius=0.8, start_angle=90 * DEGREES, angle=-60 * DEGREES, color="#F2C94C",
                        arc_center=clock_group.get_center())
        angle_label = MathTex(r"\Delta\theta_0 = 60^\circ").next_to(arc_angle, UP, buff=0.1).set_color("#F2C94C")
        angle_text = Text("初始夹角", font=cjk_font, font_size=24, color="#F2C94C").next_to(angle_label, UP, buff=0.1)

        angle_group = VGroup(arc_angle, angle_label, angle_text)

        with self.voiceover(text="2点整时，时针领先分针2个小时刻度。每个刻度是30度，所以初始角差是六十度。"):
            self.play(Create(arc_angle))
            self.play(FadeIn(angle_label), FadeIn(angle_text))
            self.play(Indicate(angle_label))

        # --- Step 3: 角速度对比 ---
        # 右侧显示速度信息
        speed_info_group = VGroup()
        v_m_tex = MathTex(r"\omega_m = 6^\circ / \text{min}", color="#2D9CDB")
        v_h_tex = MathTex(r"\omega_h = 0.5^\circ / \text{min}", color="#EB5757")
        speed_info_group.add(v_m_tex, v_h_tex)
        speed_info_group.arrange(DOWN, aligned_edge=LEFT, buff=0.5).next_to(clock_group, RIGHT, buff=1.5).shift(UP)

        with self.voiceover(
                text="分针60分钟转一圈，也就是每分钟6度。时针12小时转一圈，换算到每分钟是0.5度。接下来用同一单位做相对运动。"):
            self.play(Write(v_m_tex))
            self.play(Write(v_h_tex))
            self.wait(1)

        # --- Step 4: 追及模型与相对速度 ---
        # 在钟面上显示追及箭头 (示意)
        chase_arc = Arrow(
            start=clock_group.get_center() + UP * 1.2,
            end=clock_group.get_center() + (UP * 1.2).rotate(-30 * DEGREES, about_point=ORIGIN),
            color=BLUE, buff=0, path_arc=-30 * DEGREES
        )
        chase_text = Text("追及", font=cjk_font, font_size=20, color=BLUE).next_to(chase_arc, RIGHT, buff=0.1)

        # 右侧公式更新
        v_rel_tex = MathTex(r"\omega_{rel} = 6 - 0.5 = 5.5^\circ / \text{min}", color=YELLOW)
        v_rel_tex.next_to(speed_info_group, DOWN, buff=0.5).align_to(speed_info_group, LEFT)

        with self.voiceover(
                text="两针同方向转动，分针要追上时针，关键看它每分钟能缩小多少差距：相对角速度等于六减零点五，也就是每分钟追上五点五度。"):
            self.play(FadeIn(chase_arc), FadeIn(chase_text))
            self.play(Write(v_rel_tex))
            self.play(Indicate(v_rel_tex))
            self.wait(1)

        # 清理画面，准备计算
        self.play(FadeOut(chase_arc), FadeOut(chase_text), FadeOut(angle_group))

        # --- Step 5: 核心公式计算 ---
        # 保留钟面，右侧计算
        # 移除旧的速度公式，把相对速度移上去，或者重新排列
        calc_group = VGroup()
        formula_1 = MathTex(r"t = \frac{\text{路程差}}{\text{速度差}} = \frac{\Delta\theta_0}{\omega_{rel}}")
        # 手动替换中文部分
        formula_1_viz = VGroup(
            MathTex(r"t = "),
            MathTex(r"\frac{\Delta\theta_0}{\omega_{rel}}")
        ).arrange(RIGHT)

        formula_2 = MathTex(r"t = \frac{60}{5.5} = \frac{120}{11} \, \text{min}")

        calc_group.add(formula_1_viz, formula_2)
        calc_group.arrange(DOWN, aligned_edge=LEFT, buff=0.5).next_to(clock_group, RIGHT, buff=1.0).shift(UP)

        with self.voiceover(
                text="追及问题直接用：时间等于路程差除以速度差。这里路程差是六十度，速度差是每分钟五点五度，所以时间是六十除以五点五，等于十一分之一百二十。"):
            # 移除旧的
            self.play(FadeOut(speed_info_group), FadeOut(v_rel_tex))
            self.play(Write(formula_1_viz))
            self.wait(0.5)
            self.play(TransformMatchingTex(formula_1_viz.copy(), formula_2))
            self.wait(1)

        # --- Step 6: 结果换算 ---
        formula_3 = MathTex(r"\frac{120}{11} \, \text{min} = 10 \, \text{min} + \frac{10}{11} \, \text{min}")
        formula_4 = MathTex(r"\frac{10}{11} \times 60 \, \text{s} \approx 54.55 \, \text{s}")
        formula_5 = Text("首次重合：2点10分54.55秒", font=cjk_font, color=YELLOW, font_size=32)

        convert_group = VGroup(formula_3, formula_4, formula_5).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        convert_group.next_to(formula_2, DOWN, buff=0.6).align_to(formula_2, LEFT)

        with self.voiceover(text="把十一分之一百二十换成分秒：等于十分钟加上十一分之十分钟，也就是大约五十四点五五秒。"):
            self.play(Write(formula_3))
            self.wait(0.5)
            self.play(Write(formula_4))
            self.wait(0.5)
            self.play(Write(formula_5))
            self.play(Indicate(formula_5))

        # --- Step 7: 动画演示 ---
        # 清理右侧计算过程，准备全屏/专注演示
        # 保留 formula_5 作为结论在底部
        self.play(
            FadeOut(calc_group),
            FadeOut(formula_3),
            FadeOut(formula_4),
            formula_5.animate.to_edge(DOWN).scale(1.1)
        )
        # 移动钟面到中心
        self.play(clock_group.animate.move_to(ORIGIN), hands_group.animate.move_to(ORIGIN))

        # 定义动画更新函数
        # t_total = 120/11 min
        total_min = 120 / 11

        # ValueTracker 用于驱动时间
        t_tracker = ValueTracker(0)

        # 计时器 HUD
        timer_text = DecimalNumber(0, num_decimal_places=2, unit=" min", font_size=36, color=WHITE)
        timer_label = Text("经过时间 t =", font=cjk_font, font_size=24).next_to(timer_text, LEFT)
        timer_group = VGroup(timer_label, timer_text).to_corner(UL)

        # 初始角度 (弧度制)
        # 分针初始 90度 (PI/2)
        # 时针初始 30度 (PI/6)
        # 速度: 分针 6度/min = 6 * PI / 180 rad/min = PI/30 rad/min
        # 速度: 时针 0.5度/min = 0.5 * PI / 180 rad/min = PI/360 rad/min

        initial_m_angle = 90 * DEGREES
        initial_h_angle = 30 * DEGREES

        def update_hands(mob):
            t = t_tracker.get_value()
            # 计算转过的角度 (注意Manim中顺时针旋转，角度减小)
            # 分针转过: 6 * t 度
            delta_m = 6 * t * DEGREES
            # 时针转过: 0.5 * t 度
            delta_h = 0.5 * t * DEGREES

            # 更新指针位置
            # 分针
            new_m_vec = (UP * (clock_radius - 0.4)).rotate(-delta_m)
            minute_hand.put_start_and_end_on(ORIGIN, new_m_vec)
            # 时针
            new_h_vec = (UP * (clock_radius * 0.6)).rotate(-60 * DEGREES).rotate(-delta_h)
            hour_hand.put_start_and_end_on(ORIGIN, new_h_vec)

        def update_timer(mob):
            mob.set_value(t_tracker.get_value())

        hands_group.add_updater(update_hands)
        timer_text.add_updater(update_timer)

        # 动态角度差弧线
        diff_arc = always_redraw(lambda: Arc(
            radius=1.0,
            start_angle=(90 - 6 * t_tracker.get_value()) * DEGREES,
            angle=-(60 - 5.5 * t_tracker.get_value()) * DEGREES,
            color=YELLOW,
            arc_center=ORIGIN
        ))

        self.add(timer_group, diff_arc)

        with self.voiceover(
                text="现在把推导变成动画：从2点整开始，分针以更快的速度追赶时针。到2点10分54点55秒，差角变为零，两针第一次重合。"):
            # 播放动画，从 t=0 到 t=120/11
            # 实际播放时长缩短为8秒
            self.play(t_tracker.animate.set_value(total_min), run_time=8, rate_func=linear)

        # 冻结并强调
        hands_group.remove_updater(update_hands)
        timer_text.remove_updater(update_timer)
        diff_arc.clear_updaters()

        # 显示“重合”字样
        match_text = Text("重合！", font=cjk_font, color=RED, font_size=48).move_to(
            clock_group.get_center() + DOWN * 0.5 + RIGHT * 0.5)
        self.play(ScaleInPlace(match_text, 1.2))
        self.wait(1)

        # --- Step 8: 结论回扣 ---
        summary_text_1 = Text("每分钟追上 5.5°", font=cjk_font, font_size=24, color=GRAY)
        summary_text_2 = MathTex(r"\text{追完 } 60^\circ \text{ 需要 } \frac{120}{11} \text{ min}",
                                 tex_template=TexTemplateLibrary.ctex, font_size=24, color=GRAY)
        # 注意：TexTemplateLibrary.ctex 可能不存在于纯净环境，改为 VGroup 拼凑
        summary_text_2_safe = VGroup(
            Text("追完 60° 需要 ", font=cjk_font, font_size=24, color=GRAY),
            MathTex(r"\frac{120}{11} \text{ min}", font_size=28, color=GRAY)
        ).arrange(RIGHT)

        summary_group = VGroup(summary_text_1, summary_text_2_safe).arrange(DOWN).next_to(formula_5, UP, buff=0.5)

        with self.voiceover(
                text="记住方法：分针每分钟比时针多走五点五度，追上六十度就需要十一分之一百二十，所以第一次重合是2点10分54点55秒左右。"):
            self.play(FadeIn(summary_group))
            self.play(Circumscribe(formula_5, color=YELLOW))
            self.wait(2)

        # 清理
        self.play(FadeOut(Group(*self.mobjects)))
        self.wait(1)
