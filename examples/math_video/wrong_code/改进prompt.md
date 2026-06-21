# Manim Agent 安全生成 Prompt（完整版）

> 本文档用于约束 Agent 自动生成 **Manim Community v0.19.2** 代码，  
> 目标是：**最大程度避免运行期错误、API 不兼容、文本渲染错误（如 `<br>`）、以及 Manim 常见坑点**。

---

## 一、运行环境约束（强制）

- **Manim 版本**：Manim Community **v0.19.2**
- **Python 版本**：Python 3.11
- 生成的代码必须在上述环境中 **可直接运行**
- 禁止使用：
  - 已废弃 API
  - 仅在 Manim 新版本中存在的特性
  - 未经验证的第三方 hack 写法

---

## 二、文本渲染规则（强制）

### 2.1 `MarkupText` 使用规范

- `MarkupText` **不是 HTML**
- 仅支持 **Pango markup 子集**
- **禁止使用任何 HTML 标签**，包括但不限于：
  - `<br>`
  - `<p>`
  - `<div>`
  - `<font>`
- 若使用 `MarkupText`：
  - **只能使用 `<span ...>` 标签**
  - 不得出现任何其他标签
  - 不得假设 HTML 行为（如自动换行）

### 2.2 换行规则（强制）

- **所有文本换行必须使用 `\n`**
- **严禁使用 `<br>` 或其他 HTML 换行标签**

✅ 正确示例：
```python
Text("第一行\n第二行")
```

❌ 错误示例：
```python
MarkupText("第一行<br>第二行")
```

---

## 三、推荐文本写法（稳定优先）

### 3.1 默认方案（强烈推荐）

- 题目描述、说明性文字：
  - 使用 `Text`
  - 使用 `\n` 换行
  - 使用 `t2c` 进行颜色高亮
  - 避免 `MarkupText`，除非必要

```python
Text(
    "一班有56人，\n女生走了1/3，男生走了1/4。\n还剩40人。",
    font_size=32,
    line_spacing=1.2,
    t2c={
        "56": YELLOW,
        "1/3": RED,
        "1/4": BLUE,
        "40": GREEN,
    }
)
```

### 3.2 使用 `MarkupText` 的唯一允许条件

仅在以下条件 **全部满足** 时允许使用：

- `Text + t2c` 无法满足排版需求
- 只使用 `<span>` 标签
- 不包含任何 HTML 结构或换行标签
- 已人工确认 Pango markup 合法

---

## 四、图形与样式常见坑（强制规避）

### 4.1 虚线 / 虚线描边

- ❌ 禁止使用：
```python
set_stroke(style=DASHED_LINES)
```

- ✅ 正确方式：
```python
DashedVMobject(mobject)
```

或使用 `DashedLine` / `DashedVMobject` 明确构造。

---

### 4.2 字体选择（中文环境）

- 禁止硬编码不存在字体（如 `SimHei`）
- 推荐：
  - macOS / Linux：`Noto Sans CJK SC`
  - Windows：`SimHei`（需确认已安装）
- 推荐做法：
  - 若指定字体，必须在注释中说明环境依赖
  - 否则使用 Manim 默认字体

---

## 五、代码展示（`Code` mobject）规范

- `Code()` 依赖 pygments
- 避免假装“真实运行输出”

### 禁止行为：
- 写死运行结果却暗示是实时执行

❌ 错误示例：
```python
Text("{x: 32, y: 24}")
```

### 推荐：
- 明确说明为“示意结果”
- 或通过 Python 变量生成文本

---

## 六、数值与题目参数管理（强烈建议）

- 禁止在多处硬编码关键数字（如 56、40、1/3、1/4）
- 推荐集中参数化：

```python
TOTAL = 56
REMAIN = 40
BOY_LEFT = Fraction(3, 4)
GIRL_LEFT = Fraction(2, 3)
```

- 所有公式、文本、语音统一来源于这些参数

---

## 七、输出前自检清单（必须满足）

在输出最终代码前，必须确认：

- [ ] 代码中 **不存在以下字符串**：
  - `"<br"`
  - `"<p"`
  - `"<div"`
  - `"<font"`
- [ ] 若出现 `<` 字符，仅用于合法的 `<span>` Pango markup
- [ ] 所有多行文本均使用 `\n`
- [ ] 未使用 Manim v0.19.2 不支持的参数
- [ ] 未假装代码执行结果

---

## 八、推荐代码头部注释（建议）

```python
# Compatible with Manim Community v0.19.2
# Text rules:
# - Use '\n' for line breaks
# - Do NOT use <br> or HTML tags in MarkupText
# - Prefer Text + t2c for colored text
```

---

## 九、设计目标说明

本 Prompt 的目标是：

- ✅ 防止低级运行期错误（如 `<br>` 导致的 ValueError）
- ✅ 降低 Manim API 版本不兼容风险
- ✅ 提高 Agent 生成代码的可运行性与可维护性
- ✅ 在安全前提下，保留动画与教学设计自由度

---

**推荐用法**

- 将本文档内容作为：
  - system prompt
  - developer prompt
  - 或 Agent 的固定 safety rules
- 放置于所有 Manim 自动生成任务之前
