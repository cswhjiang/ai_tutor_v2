import platform as _platform_mod
from manim import *

# ── TTS: try to import manim_voiceover + ByteDanceService ──
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.bytedance import ByteDanceService
    HAS_VOICEOVER = True
except ImportError:
    HAS_VOICEOVER = False

# ── Narration script (fallback / reference) ──
NARRATION = [
    {
        "id": "S1",
        "text": "来看一道相向而行的行程题：甲和乙分别从两地同时出发，迎面走。4小时后相遇，相遇点离中点4千米。已知甲更快，问甲每小时比乙快多少千米？",
        "hint": "题目文字 + 数轴 A/M/B + 甲乙圆点"
    },
    {
        "id": "S2",
        "text": "先建立一个参照：如果甲乙速度相同，同时出发、相对而行，那么相遇点一定在两地的中点M。这就是后面要用的中点对称思想。",
        "hint": "甲乙同时移动到M，再返回"
    },
    {
        "id": "S3",
        "text": "题目说相遇点P离中点M有4千米，而且甲比乙快。相向而行时，相遇点一定偏向慢的一方，所以P会更靠近乙这一侧。",
        "hint": "标出P点和4km花括号，甲乙移动到P"
    },
    {
        "id": "S4",
        "text": "把中点相遇当成基准。现在相遇点从M偏到了P：对甲来说，比走到中点多走了4千米；对乙来说，比走到中点少走了4千米。两者合起来，甲在4小时内比乙多走了4加4等于8千米。",
        "hint": "高亮M-P段，显示路程差公式"
    },
    {
        "id": "S5",
        "text": "两人走的时间相同，都是4小时。速度差就等于路程差除以时间：八除以四等于二。所以甲每小时比乙快2千米。",
        "hint": "速度差公式 + 结论框"
    },
    {
        "id": "S6",
        "text": "总结一下：相向而行从两端同时出发，同速就在中点相遇。相遇点离中点4千米，就对应快者多走4、慢者少走4，所以路程差是8千米。再用路程差除以时间，得到速度差2千米每小时。",
        "hint": "总结要点列表"
    }
]

# ── CJK TeX template (for MathTex containing Chinese via xelatex) ──
def _get_cjk_font():
    p = _platform_mod.system().lower()
    if "win" in p:
        return "Microsoft YaHei"
    elif "darwin" in p:
        return "PingFang SC"
    return "Noto Sans CJK SC"

_cjk_font = _get_cjk_font()
CJK = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
CJK.add_to_preamble(
    r"\usepackage{fontspec}" + "\n"
    r"\usepackage{xeCJK}" + "\n"
    r"\setCJKmainfont{" + _cjk_font + "}\n"
)

# ── Colours ──
C_JIA      = "#4FC3F7"   # 甲
C_YI       = "#FFB74D"   # 乙
C_MID      = "#A5D6A7"   # 中点
C_HIGH     = "#FF5252"   # 强调
C_TEXT     = "#EDEDED"   # 一般文本

# ── Helper: create a labelled dot (icon) ──
def _make_icon(label_str: str, color: str, point):
    """Return a VGroup(Dot, Text) centred at *point*."""
    d = Dot(point=point, radius=0.15, color=color)
    t = Text(label_str, font_size=26, color=color).next_to(d, UP, buff=0.15)
    return VGroup(d, t)

# ── Helper: subtitle bar at the bottom ──
def _make_subtitle(txt: str, max_width: float = 12.0):
    """Semi‑transparent subtitle at bottom of frame."""
    st = Text(txt, font_size=28, color=WHITE).set_max_width(max_width)
    bg = BackgroundRectangle(st, color=BLACK, fill_opacity=0.6, buff=0.15)
    grp = VGroup(bg, st).to_edge(DOWN, buff=0.25)
    return grp

# ====================================================================
# Main Scene
# ====================================================================
BaseClass = VoiceoverScene if HAS_VOICEOVER else Scene

class MathExplanation(BaseClass):
    def construct(self):
        # ── TTS service ──
        if HAS_VOICEOVER:
            self.set_speech_service(ByteDanceService())

        # ============================================================
        # Geometry constants for the "road" number line
        # ============================================================
        ROAD_Y   = -0.3          # vertical centre of the road
        A_X      = -6.0          # left endpoint
        B_X      =  6.0          # right endpoint
        M_X      =  0.0          # midpoint
        P_X      =  2.0          # meeting point (towards B / Yi)

        A_PT = np.array([A_X, ROAD_Y, 0])
        B_PT = np.array([B_X, ROAD_Y, 0])
        M_PT = np.array([M_X, ROAD_Y, 0])
        P_PT = np.array([P_X, ROAD_Y, 0])

        # ==========================================================
        # S1 – Title & problem restatement
        # ==========================================================
        s1_text = (
            "奥数题：甲乙二人从两地同时相对而行，\n"
            "4小时后在距离中点4千米处相遇。\n"
            "甲比乙快，甲每小时比乙快多少千米？"
        )
        problem_txt = Text(s1_text, font_size=30, color=C_TEXT, line_spacing=1.3)
        problem_txt.set_max_width(12).to_edge(UP, buff=0.35)

        # Road line
        road_line = Line(A_PT, B_PT, color=WHITE, stroke_width=3)

        # Endpoint labels
        label_A = Text("A", font_size=30, color=WHITE).next_to(A_PT, DOWN, buff=0.25)
        label_B = Text("B", font_size=30, color=WHITE).next_to(B_PT, DOWN, buff=0.25)
        label_M = Text("M", font_size=30, color=C_MID).next_to(M_PT, DOWN, buff=0.25)
        tick_M  = Line(M_PT + UP*0.15, M_PT + DOWN*0.15, color=C_MID, stroke_width=3)

        road_group = VGroup(road_line, label_A, label_B, label_M, tick_M)

        # Icons (甲 at A, 乙 at B)
        jia_icon = _make_icon("甲", C_JIA, A_PT)
        yi_icon  = _make_icon("乙", C_YI,  B_PT)

        # S1 voiceover text
        s1_vo = (
            '<speak> '
            '来看一道相向而行的行程题。 <break time="400ms"/> '
            '甲和乙分别从两地同时出发，迎面走。 <break time="300ms"/> '
            '4小时后相遇，相遇点离中点4千米。 <break time="300ms"/> '
            '已知甲更快，问甲每小时比乙快多少千米？ '
            '</speak>'
        )

        if HAS_VOICEOVER:
            with self.voiceover(text=s1_vo) as tracker:
                self.play(Write(problem_txt), run_time=2.5)
                self.play(Create(road_group), run_time=1.5)
                self.play(FadeIn(jia_icon), FadeIn(yi_icon), run_time=0.8)
                # subtitle
                sub1 = _make_subtitle(NARRATION[0]["text"])
                self.play(FadeIn(sub1), run_time=0.4)
                self.wait_until_bookmark("end") if tracker.duration > 6 else self.wait(1)
                self.play(FadeOut(sub1), run_time=0.3)
        else:
            self.play(Write(problem_txt), run_time=2.5)
            self.play(Create(road_group), run_time=1.5)
            self.play(FadeIn(jia_icon), FadeIn(yi_icon), run_time=0.8)
            sub1 = _make_subtitle(NARRATION[0]["text"])
            self.play(FadeIn(sub1), run_time=0.4)
            self.wait(2)
            self.play(FadeOut(sub1), run_time=0.3)

        # ==========================================================
        # S2 – Equal‑speed → meet at midpoint
        # ==========================================================
        hint_txt = Text(
            '关键：以"中点"为基准做对称比较',
            font_size=30, color=C_TEXT
        ).set_max_width(7).to_corner(UL, buff=0.4)

        meet_label = Text(
            '若速度相同 → 在 M 相遇',
            font_size=26, color=C_MID
        ).next_to(M_PT, UP, buff=0.55)

        # Positions for the dots' centres (first element of VGroup)
        jia_dot = jia_icon[0]  # Dot mob
        yi_dot  = yi_icon[0]
        jia_lbl = jia_icon[1]
        yi_lbl  = yi_icon[1]

        s2_vo = (
            '<speak> '
            '先建立一个参照。 <break time="300ms"/> '
            '如果甲乙速度相同，同时出发、相对而行，'
            '那么相遇点一定在两地的中点 $M$。 <break time="400ms"/> '
            '这就是后面要用的中点对称思想。 '
            '</speak>'
        )

        # Fade out problem text to make room
        self.play(FadeOut(problem_txt), run_time=0.5)

        if HAS_VOICEOVER:
            with self.voiceover(text=s2_vo) as tracker:
                sub2 = _make_subtitle(NARRATION[1]["text"])
                self.play(Write(hint_txt), run_time=1.0)
                self.play(Indicate(tick_M, color=YELLOW), run_time=0.8)
                self.play(FadeIn(meet_label), run_time=0.6)
                self.play(FadeIn(sub2), run_time=0.3)
                # Move both dots to M
                self.play(
                    jia_dot.animate.move_to(M_PT),
                    jia_lbl.animate.move_to(M_PT + UP*0.45),
                    yi_dot.animate.move_to(M_PT),
                    yi_lbl.animate.move_to(M_PT + UP*0.45),
                    run_time=2.0
                )
                self.wait(0.5)
                # Return to start
                self.play(
                    jia_dot.animate.move_to(A_PT),
                    jia_lbl.animate.move_to(A_PT + UP*0.45),
                    yi_dot.animate.move_to(B_PT),
                    yi_lbl.animate.move_to(B_PT + UP*0.45),
                    run_time=1.2
                )
                self.play(FadeOut(sub2), run_time=0.3)
        else:
            sub2 = _make_subtitle(NARRATION[1]["text"])
            self.play(Write(hint_txt), run_time=1.0)
            self.play(Indicate(tick_M, color=YELLOW), run_time=0.8)
            self.play(FadeIn(meet_label), run_time=0.6)
            self.play(FadeIn(sub2), run_time=0.3)
            self.play(
                jia_dot.animate.move_to(M_PT),
                jia_lbl.animate.move_to(M_PT + UP*0.45),
                yi_dot.animate.move_to(M_PT),
                yi_lbl.animate.move_to(M_PT + UP*0.45),
                run_time=2.0
            )
            self.wait(0.8)
            self.play(
                jia_dot.animate.move_to(A_PT),
                jia_lbl.animate.move_to(A_PT + UP*0.45),
                yi_dot.animate.move_to(B_PT),
                yi_lbl.animate.move_to(B_PT + UP*0.45),
                run_time=1.2
            )
            self.play(FadeOut(sub2), run_time=0.3)

        # Clean up S2 temporary labels
        self.play(FadeOut(hint_txt), FadeOut(meet_label), run_time=0.5)

        # ==========================================================
        # S3 – Show meeting point P offset 4 km towards Yi
        # ==========================================================
        # P marker
        tick_P = Line(P_PT + UP*0.15, P_PT + DOWN*0.15, color=C_HIGH, stroke_width=3)
        label_P = Text("P", font_size=30, color=C_HIGH).next_to(P_PT, DOWN, buff=0.25)
        p_sub_label = Text("(相遇点)", font_size=22, color=C_HIGH).next_to(label_P, DOWN, buff=0.08)
        p_group = VGroup(tick_P, label_P, p_sub_label)

        # Brace between M and P
        brace_mp = BraceBetweenPoints(M_PT + DOWN*0.45, P_PT + DOWN*0.45, direction=DOWN, color=C_HIGH)
        brace_label = Text("4 km", font_size=26, color=C_HIGH).next_to(brace_mp, DOWN, buff=0.1)
        brace_group = VGroup(brace_mp, brace_label)

        direction_note = Text(
            '甲更快 → 相遇点偏向乙这边',
            font_size=28, color=C_TEXT
        ).set_max_width(7).to_corner(DL, buff=0.5)

        s3_vo = (
            '<speak> '
            '题目说相遇点 $P$ 离中点 $M$ 有4千米， <break time="300ms"/> '
            '而且甲比乙快。 <break time="200ms"/> '
            '相向而行时，相遇点一定偏向慢的一方， '
            '所以 $P$ 会更靠近乙这一侧。 '
            '</speak>'
        )

        if HAS_VOICEOVER:
            with self.voiceover(text=s3_vo) as tracker:
                sub3 = _make_subtitle(NARRATION[2]["text"])
                self.play(Create(p_group), run_time=0.8)
                self.play(Create(brace_group), run_time=1.0)
                self.play(Write(direction_note), run_time=0.8)
                self.play(FadeIn(sub3), run_time=0.3)
                # Move dots to P
                self.play(
                    jia_dot.animate.move_to(P_PT),
                    jia_lbl.animate.move_to(P_PT + UP*0.45),
                    yi_dot.animate.move_to(P_PT),
                    yi_lbl.animate.move_to(P_PT + UP*0.45 + LEFT*0.5),
                    run_time=2.2
                )
                self.wait(0.6)
                self.play(FadeOut(sub3), run_time=0.3)
        else:
            sub3 = _make_subtitle(NARRATION[2]["text"])
            self.play(Create(p_group), run_time=0.8)
            self.play(Create(brace_group), run_time=1.0)
            self.play(Write(direction_note), run_time=0.8)
            self.play(FadeIn(sub3), run_time=0.3)
            self.play(
                jia_dot.animate.move_to(P_PT),
                jia_lbl.animate.move_to(P_PT + UP*0.45),
                yi_dot.animate.move_to(P_PT),
                yi_lbl.animate.move_to(P_PT + UP*0.45 + LEFT*0.5),
                run_time=2.2
            )
            self.wait(1.0)
            self.play(FadeOut(sub3), run_time=0.3)

        # ==========================================================
        # S4 – Compare to midpoint: +4 / −4 → distance diff 8 km
        # ==========================================================
        # Highlight segment M→P for 甲 "extra"
        seg_jia = Line(M_PT, P_PT, color=C_JIA, stroke_width=8)
        seg_jia_label = Text(
            '甲多走 4 km', font_size=24, color=C_JIA
        ).next_to(seg_jia, UP, buff=0.6)

        # Highlight segment P→M for 乙 "less"
        seg_yi = Line(P_PT, M_PT, color=C_YI, stroke_width=8).shift(DOWN*0.08)  # slight offset to see both
        seg_yi_label = Text(
            '乙少走 4 km', font_size=24, color=C_YI
        ).next_to(seg_yi, UP, buff=0.25)

        # Distance diff equation (no Chinese inside MathTex!)
        eq_dist = MathTex(
            r"\Delta s", "=", "4", "+", "4", "=", "8", r"\text{ km}",
            font_size=44
        ).to_edge(RIGHT, buff=1.0).shift(UP*1.5)
        # colour the numbers
        eq_dist[2].set_color(C_JIA)   # first 4
        eq_dist[4].set_color(C_YI)    # second 4
        eq_dist[6].set_color(C_HIGH)  # 8

        s4_vo = (
            '<speak> '
            '把中点相遇当成基准。 <break time="300ms"/> '
            '现在相遇点从 $M$ 偏到了 $P$： <break time="200ms"/> '
            '对甲来说，比走到中点多走了4千米；'
            '对乙来说，比走到中点少走了4千米。 <break time="400ms"/> '
            '两者合起来，甲在4小时内比乙多走了 $4+4=8$ 千米。 '
            '</speak>'
        )

        if HAS_VOICEOVER:
            with self.voiceover(text=s4_vo) as tracker:
                sub4 = _make_subtitle(NARRATION[3]["text"][:60] + "…")
                self.play(FadeIn(sub4), run_time=0.3)
                self.play(FadeIn(seg_jia), FadeIn(seg_jia_label), run_time=0.8)
                self.play(FadeIn(seg_yi), FadeIn(seg_yi_label), run_time=0.8)
                self.play(Write(eq_dist), run_time=1.2)
                self.play(Indicate(brace_group, color=YELLOW), run_time=0.9)
                self.wait(1.0)
                self.play(FadeOut(sub4), run_time=0.3)
        else:
            sub4 = _make_subtitle(NARRATION[3]["text"][:60] + "…")
            self.play(FadeIn(sub4), run_time=0.3)
            self.play(FadeIn(seg_jia), FadeIn(seg_jia_label), run_time=0.8)
            self.play(FadeIn(seg_yi), FadeIn(seg_yi_label), run_time=0.8)
            self.play(Write(eq_dist), run_time=1.2)
            self.play(Indicate(brace_group, color=YELLOW), run_time=0.9)
            self.wait(1.5)
            self.play(FadeOut(sub4), run_time=0.3)

        # ==========================================================
        # S5 – Compute speed difference
        # ==========================================================
        # Fade out road decorations to focus on formula
        fade_targets = VGroup(
            road_group, p_group, brace_group, direction_note,
            jia_icon, yi_icon, seg_jia, seg_jia_label, seg_yi, seg_yi_label
        )
        self.play(FadeOut(fade_targets), run_time=0.8)

        # Move eq_dist to upper‑centre
        self.play(eq_dist.animate.move_to(UP*2), run_time=0.6)

        eq_speed = MathTex(
            r"\Delta v", "=", r"\frac{\Delta s}{t}", "=",
            r"\frac{8}{4}", "=", "2", r"\text{ km/h}",
            font_size=52
        ).move_to(ORIGIN)
        eq_speed[6].set_color(YELLOW)

        # Conclusion box
        conclusion_txt = Text(
            '结论：甲每小时比乙快 2 千米',
            font_size=38, color=WHITE
        ).set_max_width(10)
        conclusion_box = SurroundingRectangle(
            conclusion_txt, color=C_HIGH, buff=0.25, corner_radius=0.1
        )
        conclusion_group = VGroup(conclusion_box, conclusion_txt).next_to(eq_speed, DOWN, buff=0.8)

        s5_vo = (
            '<speak> '
            '两人走的时间相同，都是4小时。 <break time="300ms"/> '
            '速度差就等于路程差除以时间： <break time="200ms"/> '
            '$\\frac{8}{4}=2$。 <break time="400ms"/> '
            '所以甲每小时比乙快2千米。 '
            '</speak>'
        )

        if HAS_VOICEOVER:
            with self.voiceover(text=s5_vo) as tracker:
                sub5 = _make_subtitle(NARRATION[4]["text"])
                self.play(FadeIn(sub5), run_time=0.3)
                self.play(
                    ReplacementTransform(eq_dist, eq_speed),
                    run_time=1.2
                )
                self.wait(0.5)
                self.play(FadeIn(conclusion_group, shift=UP*0.3), run_time=0.8)
                self.wait(1.0)
                self.play(FadeOut(sub5), run_time=0.3)
        else:
            sub5 = _make_subtitle(NARRATION[4]["text"])
            self.play(FadeIn(sub5), run_time=0.3)
            self.play(
                ReplacementTransform(eq_dist, eq_speed),
                run_time=1.2
            )
            self.wait(0.8)
            self.play(FadeIn(conclusion_group, shift=UP*0.3), run_time=0.8)
            self.wait(1.5)
            self.play(FadeOut(sub5), run_time=0.3)

        # ==========================================================
        # S6 – Summary bullets
        # ==========================================================
        self.play(FadeOut(eq_speed), FadeOut(conclusion_group), run_time=0.6)

        bullet_1 = Text('1. 相向而行同时出发：同速必在中点相遇', font_size=30, color=C_TEXT)
        bullet_2 = Text('2. 偏离中点 4 km：快者多 4、慢者少 4 → 路程差 8 km', font_size=30, color=C_TEXT)
        bullet_3_parts = VGroup(
            Text('3. 速度差 = 8 ÷ 4 = ', font_size=30, color=C_TEXT),
            Text('2 km/h', font_size=32, color=YELLOW, weight=BOLD)
        ).arrange(RIGHT, buff=0.1)

        summary = VGroup(bullet_1, bullet_2, bullet_3_parts).arrange(
            DOWN, aligned_edge=LEFT, buff=0.45
        ).set_max_width(12).move_to(ORIGIN)

        summary_title = Text('总结', font_size=38, color=YELLOW, weight=BOLD).next_to(summary, UP, buff=0.5)

        s6_vo = (
            '<speak> '
            '总结一下。 <break time="400ms"/> '
            '相向而行从两端同时出发，同速就在中点相遇。 <break time="400ms"/> '
            '相遇点离中点4千米，就对应快者多走4、慢者少走4，'
            '所以路程差是8千米。 <break time="400ms"/> '
            '再用路程差除以时间，得到速度差 $2$ 千米每小时。 '
            '</speak>'
        )

        if HAS_VOICEOVER:
            with self.voiceover(text=s6_vo) as tracker:
                sub6 = _make_subtitle(NARRATION[5]["text"][:55] + "…")
                self.play(Write(summary_title), run_time=0.6)
                self.play(FadeIn(sub6), run_time=0.3)
                self.play(Write(bullet_1), run_time=1.0)
                self.play(Write(bullet_2), run_time=1.0)
                self.play(Write(bullet_3_parts), run_time=1.0)
                self.wait(1.5)
                self.play(FadeOut(sub6), run_time=0.3)
        else:
            sub6 = _make_subtitle(NARRATION[5]["text"][:55] + "…")
            self.play(Write(summary_title), run_time=0.6)
            self.play(FadeIn(sub6), run_time=0.3)
            self.play(Write(bullet_1), run_time=1.0)
            self.play(Write(bullet_2), run_time=1.0)
            self.play(Write(bullet_3_parts), run_time=1.0)
            self.wait(2.5)
            self.play(FadeOut(sub6), run_time=0.3)

        # Final hold
        self.wait(2)

# manim -pqh math_explanation.py MathExplanation
