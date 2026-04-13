from manim import *

CN_TEMPLATE = TexTemplate(
    tex_compiler="xelatex",
    output_format=".xdv",
)
CN_TEMPLATE.add_to_preamble(r"""
\usepackage{ctex}
\usepackage{amsmath,amssymb}
\setCJKmainfont{PingFang SC}
""")

class CNMathTexDemo(Scene):
    def construct(self):
        eq = MathTex(
            r"v_{\text{甲}}-v_{\text{乙}}=\frac{8}{4}=2\ \text{km/h}",
            tex_template=CN_TEMPLATE
        ).scale(1.0)
        self.play(Write(eq))
        self.wait(2)
