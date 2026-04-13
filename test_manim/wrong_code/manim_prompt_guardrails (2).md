# 避免 Manim/MathTex 下标越界错误：Prompt 增补模板

下面这些增补内容可以直接加到**生成 Manim 代码的 Prompt**里，用来约束智能体不要写出 `MathTex()[i]` 这类依赖内部拆分结构的脆弱代码，从而避免 `IndexError: list index out of range`。

---

## 1) 强制规则：禁止用下标给 MathTex/ Tex 上色或定位

> **必须**在提示词里明确写出“禁止使用 `eq[i]` 访问 MathTex 子对象”。

可直接粘贴：

- **禁止**通过 `MathTex(...)` / `Tex(...)` 的下标（如 `eq[0]`, `eq[2]`）来选择符号、变量或局部元素，因为不同 Manim/LaTeX 版本拆分结果不稳定，容易越界报错。  
- 需要上色/强调时，**必须**使用：
  - `set_color_by_tex("x", color)`  
  - 或 `set_color_by_tex_to_color_map({...})`  
  - 或 `get_part_by_tex("x") / get_parts_by_tex("x")` 后再 `.set_color(...)`  
- 如果确实需要下标访问（极少数情况），**必须先** `len(eq.submobjects)` 检查并提供兜底逻辑；默认不允许写下标访问。

---

## 2) 推荐写法：要求对变量/片段用 tex-matching API

可直接粘贴：

- 在公式中对 `x`、`y`、`\frac{3}{4}x`、`\frac{2}{3}y` 等局部片段的样式设置，必须用 tex-matching API，例如：  
  - `eq.set_color_by_tex_to_color_map({"x": BOY_COLOR, "y": GIRL_COLOR})`  
  - `eq.set_color_by_tex(r"\frac{3}{4}x", BOY_COLOR)`  
  - `eq.get_part_by_tex("y").set_color(GIRL_COLOR)`

---

## 3) 质量门槛：生成后必须自检“潜在越界点”

可直接粘贴：

- 在输出代码前，请进行静态自检：  
  - 搜索是否出现 `MathTex(` 或 `Tex(` 后紧跟 `[...]` 下标访问；若存在，必须改为 `set_color_by_tex*` / `get_part_by_tex*`。  
  - 搜索是否出现 `VGroup(...)[i]` / `Group(...)[i]` 对不确定长度对象的索引；若存在，需确保对象长度可推断或添加防御性检查。

---

## 4) 版本兼容性提示：要求使用稳定 API、避免依赖内部拆分

可直接粘贴：

- 代码必须兼容常见 Manim Community 版本差异（子 mobject 拆分粒度可能变化）。  
- 不得依赖 `MathTex` 内部 tokenization 结果（即“第 0 个一定是 x，第 2 个一定是 y”这种假设）。

---

## 5) 可选：提供一个“标准片段”让智能体照抄

你也可以把下面这段当作 Prompt 的“首选范例”，智能体会更倾向用正确写法：

```python
eq1 = MathTex(r"x + y = 56", font_size=48)
eq1.set_color_by_tex_to_color_map({"x": BOY_COLOR, "y": GIRL_COLOR})

eq2 = MathTex(r"\frac{3}{4}x + \frac{2}{3}y = 40", font_size=48)
eq2.set_color_by_tex_to_color_map({"x": BOY_COLOR, "y": GIRL_COLOR})
# 或更精确：对整段上色
eq2.set_color_by_tex(r"\frac{3}{4}x", BOY_COLOR)
eq2.set_color_by_tex(r"\frac{2}{3}y", GIRL_COLOR)
```

---

## 6) 最小可用的 Prompt 增补（精简版）

如果你只想加一句最关键的约束，用这一段就够了：

> **不要**对 `MathTex/Tex` 使用下标（如 `eq[2]`）来选中局部元素；上色/强调必须用 `set_color_by_tex*` 或 `get_part(s)_by_tex`，避免因 LaTeX 拆分变化导致 `IndexError`。

---
