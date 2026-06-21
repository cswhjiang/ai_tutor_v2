# Prompt 补充建议：避免 Manim `MathTex`/LaTeX 中文编译错误

下面这段内容可以直接追加到你用来生成 Manim 代码的 prompt 末尾（或作为“硬性约束/检查清单”），用于避免生成包含中文的 `MathTex` 导致 LaTeX 报 `Unicode character` 的问题。

---

## 必须遵守的约束（关键）

- **禁止在 `MathTex` / `Tex` 的 LaTeX 字符串中出现任何中文或其他非 ASCII 字符**（例如：`\text{相对速度}`、`\text{路程}` 都不允许）。
- **所有中文说明必须使用 `Text`（或 `MarkupText`）渲染**，公式只用 `MathTex`。
- **在输出最终代码前，必须自检**：扫描所有 `MathTex(`、`Tex(`、`MathTex(r"..."`、`Tex(r"...")` 的内容，确保其中 **不包含中文字符**（可用简单规则：出现 `\u4e00-\u9fff` 范围字符则判定失败）。

---

## 推荐的 prompt 追加段落（可直接复制）

> 生成 Manim 代码时请严格遵守：  
> 1. 任何 `MathTex`/`Tex` 的 LaTeX 字符串 **只能包含数学符号、数字、英文、常见 LaTeX 命令**，不得包含中文或其他 Unicode 文本（例如禁止 `\text{相对速度}`）。  
> 2. 中文解释、标题、旁白字幕一律用 `Text`（或 `MarkupText`）实现，公式单独用 `MathTex`。  
> 3. 如果需要在公式旁显示中文含义，请使用 `VGroup(Text("中文说明"), MathTex("..."))` 的组合方式。  
> 4. 输出代码前请自检：所有 `MathTex`/`Tex` 参数里不能出现中文字符；如有，必须改为英文或拆分成 `Text + MathTex`。

---

## 示例（正确做法）

```python
eq = VGroup(
    Text("追及方程：", font_size=28),
    Text("相对速度 × t = 路程", font_size=28),
    MathTex(r"\omega_{rel} t = \Delta\theta"),
).arrange(DOWN, aligned_edge=LEFT)
```

## 反例（会触发你遇到的错误）

```python
# ❌ LaTeX 不支持中文 Unicode（默认模板/编译器）
MathTex(r"\text{相对速度} \times t = \text{路程}")
```

---

## 可选增强（如果确实要 `MathTex` 支持中文）

只有在你明确要用 XeLaTeX/LuaLaTeX 并配置 `TexTemplate` + `xeCJK` + 中文字体时才允许在 `MathTex` 中出现中文。  
否则默认一律按“禁止中文进 MathTex”处理。
