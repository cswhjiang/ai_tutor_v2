# Manim 代码生成：避免 LaTeX/MathTex 中文编译错误（可直接加入 Prompt）

> 目标：避免生成会触发 `ValueError: latex error converting to dvi` 的 Manim 代码。  
> 常见根因：`MathTex/Tex` 默认走 LaTeX（如 latex/pdflatex）编译链，**直接包含中文会编译失败**。

---

## ✅ 必须加入的约束（建议原样粘贴进 Prompt）

### 1) MathTex/Tex **禁止出现中文**
- **不要**在 `MathTex(...)` / `Tex(...)` / `\text{...}` 中输出任何中文字符（包括“距离、速度、分针、时针、分钟、秒”等）。
- 公式中需要中文解释时：  
  - 公式部分用 **英文/符号**（`distance/speed`, `min`, `s`, `deg` 等）；  
  - 中文解释用 `Text(...)`（Pango 渲染）放在公式旁边。

**示例（推荐做法）**
```py
eq = MathTex(r"t=\frac{d}{v}=\frac{60}{5.5}")
cn = Text("（距离/速度）", font_size=24).next_to(eq, RIGHT)
```

### 2) 若必须在公式里显示中文：必须显式配置 XeLaTeX + xeCJK（并写出字体）
- 只有在用户明确要求“公式里也要中文”时才这样做。
- 必须：
  1) 用 `TexTemplate(tex_compiler="xelatex")`  
  2) 在 preamble 加 `xeCJK/fontspec`  
  3) 指定一个本机存在的中文字体（mac 常用 `PingFang SC`，也可让用户自行替换）

**示例（可选方案）**
```py
from manim.utils.tex import TexTemplate
CJK = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
CJK.add_to_preamble(r"""
\usepackage{fontspec}
\usepackage{xeCJK}
\setCJKmainfont{PingFang SC}
""")
eq = MathTex(r"t=\frac{\text{距离}}{\text{速度}}", tex_template=CJK)
```

---

## ✅ 生成时的自检清单（让智能体在输出前执行）

在输出代码前，检查并确保：
- [ ] 所有 `MathTex(...)` / `Tex(...)` 的字符串 **不包含任何中文字符**
- [ ] 中文说明全部用 `Text(...)`（或 `MarkupText(...)`）渲染
- [ ] 单位用英文缩写：`min`, `s`, `deg`，或纯符号
- [ ] 如果用了中文公式模板（XeLaTeX），代码里明确写出 `TexTemplate` 配置和字体名

---

## ✅ 可直接追加到你现有 Prompt 的“硬规则块”（短版）

把下面这段直接粘贴到智能体的系统/开发者/用户 prompt 里即可：

- **Hard rule:** Never put Chinese characters inside `MathTex` or `Tex` (including `\text{...}`), because Manim’s LaTeX compilation will fail (`latex error converting to dvi`).  
- If Chinese explanation is needed, render it with `Text(...)` (Pango) next to the math.  
- Only if the user explicitly requires Chinese inside equations, configure `TexTemplate` with `xelatex + xeCJK` and set an existing system CJK font.

---
