from manim import *

# ---- XeLaTeX + 中文支持模板（ctex + fontspec）----
CN_TEMPLATE = TexTemplate(
    tex_compiler="xelatex",
    output_format=".xdv",  # xelatex 走 xdv 更稳
)
CN_TEMPLATE.add_to_preamble(r"""
\usepackage{ctex}          % 中文支持
\usepackage{amsmath,amssymb}
\setCJKmainfont{PingFang SC}  % mac 默认有（也可以换成 Songti SC / Heiti SC）
""")

class MeetMidpoint(Scene):
    def construct(self):
        # ---------- Style helpers ----------
        def label_up(mobj, text, buff=0.15, scale=0.5):
            t = Text(text, font="Microsoft YaHei").scale(scale)
            t.next_to(mobj, UP, buff=buff)
            return t

        def label_down(mobj, tex, buff=0.15, scale=0.7):
            t = MathTex(tex).scale(scale)
            t.next_to(mobj, DOWN, buff=buff)
            return t

        # ---------- Shot 1: Title ----------
        title = Text("相向而行｜相遇点偏离中点", font="Microsoft YaHei").scale(0.9)
        subtitle = Text("求：甲每小时比乙快多少千米？", font="Microsoft YaHei").scale(0.6).next_to(title, DOWN)
        self.play(Write(title), FadeIn(subtitle, shift=DOWN))
        self.wait(1.5)
        self.play(FadeOut(title), FadeOut(subtitle))

        # ---------- Shot 2: Build segment AB with midpoint M ----------
        line = Line(LEFT*5, RIGHT*5)
        A = Dot(line.get_left())
        B = Dot(line.get_right())
        M = Dot(line.get_center())

        A_lab = label_up(A, "A（甲出发地）")
        B_lab = label_up(B, "B（乙出发地）")
        M_lab = label_up(M, "M（中点）", scale=0.55)

        self.play(Create(line))
        self.play(FadeIn(A), FadeIn(B), FadeIn(M))
        self.play(FadeIn(A_lab), FadeIn(B_lab), FadeIn(M_lab))
        self.wait(0.8)

        # ---------- Shot 3: Meeting point P, 4km from midpoint ----------
        # Since 甲 faster, meeting point closer to 乙: place P to the right of M
        P = Dot(M.get_center() + RIGHT*2.0)  # visual placement, not to scale
        P_lab = label_up(P, "P（相遇点）", scale=0.55)

        mp_brace = Brace(Line(M.get_center(), P.get_center()), UP, buff=0.1)
        mp_text = Text("4 km", font="Microsoft YaHei").scale(0.55).next_to(mp_brace, UP, buff=0.1)

        self.play(FadeIn(P), FadeIn(P_lab))
        self.play(GrowFromCenter(mp_brace), FadeIn(mp_text))
        self.wait(1.2)

        # ---------- Shot 4: Mark halves and expressions ----------
        # Braces for AM, MP, PB
        AM_brace = Brace(Line(A.get_center(), M.get_center()), DOWN, buff=0.1)
        PB_brace = Brace(Line(P.get_center(), B.get_center()), DOWN, buff=0.1)

        am_text = MathTex(r"\frac{D}{2}", tex_template=CN_TEMPLATE).scale(0.7).next_to(AM_brace, DOWN, buff=0.1)
        pb_text = MathTex(r"\frac{D}{2}-4", tex_template=CN_TEMPLATE).scale(0.7).next_to(PB_brace, DOWN, buff=0.1)

        # Also show AP and BP formulas
        ap_formula = MathTex(r"AP=\frac{D}{2}+4", tex_template=CN_TEMPLATE).scale(0.8).to_edge(UP).shift(LEFT*2)
        bp_formula = MathTex(r"BP=\frac{D}{2}-4", tex_template=CN_TEMPLATE).scale(0.8).to_edge(UP).shift(RIGHT*2)

        # Animate segment braces
        self.play(GrowFromCenter(AM_brace), FadeIn(am_text))
        self.play(GrowFromCenter(PB_brace), FadeIn(pb_text))
        self.wait(0.5)

        # Move MP label slightly to avoid clutter
        self.play(mp_brace.animate.shift(UP*0.25), mp_text.animate.shift(UP*0.25))

        self.play(Write(ap_formula), Write(bp_formula))
        self.wait(1.2)

        # ---------- Shot 5: Key difference 8 km ----------
        diff_eq = MathTex(r"( \frac{D}{2}+4 )-( \frac{D}{2}-4 )=8\ \text{km}", tex_template=CN_TEMPLATE).scale(0.85)
        diff_eq.next_to(line, DOWN, buff=1.3)

        # Highlight "4 km" then show difference
        highlight_rect = SurroundingRectangle(mp_text, buff=0.08)
        self.play(Create(highlight_rect))
        self.wait(0.4)
        self.play(Write(diff_eq))
        self.wait(1.2)
        self.play(FadeOut(highlight_rect))

        # ---------- Shot 6: Convert to speed difference using time 4h ----------
        time_text = Text("相遇用时：4 小时", font="Microsoft YaHei").scale(0.6)
        time_text.next_to(diff_eq, DOWN, buff=0.35)

        speed_eq = MathTex(r"v_{\text{甲}}-v_{\text{乙}}=\frac{8}{4}=2\ \text{km/h}", tex_template=CN_TEMPLATE).scale(0.9)
        speed_eq.next_to(time_text, DOWN, buff=0.35)

        self.play(FadeIn(time_text, shift=DOWN*0.2))
        self.play(Write(speed_eq))
        self.wait(1.0)


        # ---------- Ending ----------
        answer = Text("结论：甲每小时比乙快 2 千米", font="Microsoft YaHei").scale(0.85)
        answer.to_edge(DOWN)

        self.play(Transform(time_text, answer))
        self.wait(2)

        # Clean end (optional)
        self.play(FadeOut(VGroup(
            line, A, B, M, P,
            A_lab, B_lab, M_lab, P_lab,
            AM_brace, PB_brace, mp_brace,
            am_text, pb_text, mp_text,
            ap_formula, bp_formula, diff_eq, speed_eq, time_text
        )))
